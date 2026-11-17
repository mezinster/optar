# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""A second, slower reader for scans too coarse for the ordinary one.

The ordinary reader decides every dot by one blurred sample against a cut
level. At about half the advised resolution neighbouring dots bleed into
each other and that decision fails for a large share of the symbols. This
reader learns, from the symbols the ordinary reader did get right, how dots
bleed in each part of the page, and decides each symbol as a whole:

1. Read the page the ordinary way. Symbols decoded with at most
   SEED_ERRORS corrected bits are taken as known.
2. Sample the scan around every dot at the SAMPLE_OFFSETS grid (in dots,
   both axes) and subtract the samples' mean.
3. For each of REGIONS regions of the page fit, by ridge-regularised least
   squares (RIDGE), a linear filter from those samples, the squares of the
   centre nine and a constant to the known dots (+1 dark, -1 light).
4. Apply the filters to every dot: a signed confidence for each dot.
5. For each symbol choose the codeword whose bits fit its confidences best
   (every codeword is tried); the gap to the second best is the symbol's
   confidence.
6. Take the more confident KEEP share of the symbols as known and repeat
   from 3, ROUNDS fits in all.

The scan is first enlarged (Lanczos) so that a dot is about ENLARGE_TO
pixels wide, then the page is located with the ordinary code.

Nothing here changes the ordinary reader: its results are pinned by the test
vectors. The numbers below are reader tuning, not format, and were measured
on one owner's scans of a High-protection, Standard-dot A4 document at about
290 dpi (see the module tests and the task report).
"""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np
from PIL import Image

from optar import identify
from optar.container import page_payload, read_header
from optar.decoder import PageGrid, PageResult, PageStats, locate_page, page_to_scan
from optar.decoder.filters import blur, minmax
from optar.decoder.options import DecodeOptions
from optar.decoder.sample import sample_bits
from optar.errors import DecodeError, IdentifyError
from optar.fec import decode_symbols, encode_symbols
from optar.format import Layout, PageFormat
from optar.layout import channel_xy

__all__ = [
    "ENLARGE_STEP",
    "ENLARGE_TO",
    "KEEP",
    "MIN_KNOWN",
    "REGIONS",
    "RIDGE",
    "ROUNDS",
    "SAMPLE_OFFSETS",
    "SEED_ERRORS",
    "Stopped",
    "identify_coarse",
    "read_soft",
]

# Scan pixels per data dot aimed at by the enlargement; the factor is rounded
# to the nearest multiple of ENLARGE_STEP (never below 1), so the owner's
# 286 dpi Standard-dot scans (1.43 pixels a dot) are enlarged exactly 3 times,
# as in the experiment.
ENLARGE_TO = 4.3
ENLARGE_STEP = 0.25
# Sample points around a dot's centre, in dots, on both axes: 7 x 7 points
# half a dot apart. They must be evenly spaced, symmetric about 0 and a whole
# number of steps per dot.
SAMPLE_OFFSETS = (-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5)
# The page's data area is cut into this many regions across and down; each
# gets its own filter.
REGIONS = (16, 22)
# Fits, the first from the ordinary reader's known symbols. On the owner's six
# scans the document needed (repaired bytes, worst block of 64) 53039/54
# after one fit, 42455/40 after two, 41705/40 after three and 41495/40 after
# five. A fit costs about 1.7 s of an A4 Standard page, so the five of the
# experiment are kept.
ROUNDS = 5
# Share of symbols, the most confident, that the next fit learns from.
KEEP = 0.6
# Ridge weight, per known dot.
RIDGE = 1e-2
# Ordinary-read symbols with at most this many corrected bits seed the first fit.
SEED_ERRORS = 1
# identify_coarse skips a located candidate whose ordinary read gives fewer
# known symbols than this share. A grid laid on noise gives about 0.6% (the
# share of 24-bit words within one bit of a Golay codeword, 4096 * 25 / 2**24);
# the owner's coarse scans gave about 30%.
MIN_KNOWN = 0.05
# Dots a region needs to fit its own filter; a region with fewer uses the
# filter fitted on the whole page.
_MIN_FIT_DOTS = 200
# The squares of the centre samples are scaled by this, to keep them near the
# size of the linear terms (grey levels are 0..255).
_SQUARE_SCALE = 1 / 128
# Codewords scored at once: bounds the symbols x codewords score matrix.
_SCORE_CHUNK = 4096
# Rows of the sample grid computed at once: bounds page_to_scan's temporaries.
_GRID_ROWS = 128
# The enlarged scan is kept below this many pixels (an A4 page at ENLARGE_TO
# pixels a dot is about 75 million): the factor is lowered to fit.
_MAX_ENLARGED_PIXELS = 160_000_000
# A soft decision tries every codeword, so the data word must be short.
_MAX_DATA_BITS = 12


class Stopped(Exception):
    """The caller's cancelled() returned True."""


def _never() -> bool:
    return False


# Geometry of the sample grid, from SAMPLE_OFFSETS.
_STEP = SAMPLE_OFFSETS[1] - SAMPLE_OFFSETS[0]
_REACH = len(SAMPLE_OFFSETS) // 2
_PER_DOT = round(1 / _STEP)
assert len(SAMPLE_OFFSETS) % 2 == 1 and abs(_PER_DOT * _STEP - 1) < 1e-9
assert all(abs(o - (i - _REACH) * _STEP) < 1e-9 for i, o in enumerate(SAMPLE_OFFSETS))
_N = len(SAMPLE_OFFSETS)
_CENTRE = [(_REACH + j) * _N + (_REACH + i) for j in (-1, 0, 1) for i in (-1, 0, 1)]
_FEATURES = _N * _N + len(_CENTRE) + 1


def _bilinear(img: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """img (2-D) at x, y (integers at pixel centres), float32; clamped to the image."""
    h, w = img.shape
    x = np.clip(x, 0, w - 1.001)
    y = np.clip(y, 0, h - 1.001)
    xi = x.astype(np.intp)
    yi = y.astype(np.intp)
    fx = (x - xi).astype(np.float32)
    fy = (y - yi).astype(np.float32)
    a = img[yi, xi].astype(np.float32)
    b = img[yi, xi + 1].astype(np.float32)
    c = img[yi + 1, xi].astype(np.float32)
    d = img[yi + 1, xi + 1].astype(np.float32)
    top = a + (b - a) * fx
    return top + ((c + (d - c) * fx) - top) * fy


class _Reader:
    """One page's soft read, a round at a time (identify_coarse stops early)."""

    def __init__(self, grid: PageGrid, image: np.ndarray, cancelled: Callable[[], bool]):
        fmt = grid.fmt
        if fmt.fec_smallbits > _MAX_DATA_BITS:
            raise DecodeError(
                f"the slow reader needs data words of at most {_MAX_DATA_BITS} bits"
            )
        image = np.asarray(image)
        if image.ndim != 2 or image.dtype != np.uint8 or image.size == 0:
            raise DecodeError("scan must be a non-empty 2-D uint8 grey image")
        self.grid, self.fmt, self.cancelled = grid, fmt, cancelled
        self.syms, self.large = fmt.fec_syms, fmt.fec_largebits
        self.used = fmt.used_bits
        if self.used == 0:
            raise DecodeError("the page format holds no data")
        self._shifts = np.arange(self.large - 1, -1, -1, dtype=np.uint32)
        codebook = encode_symbols(np.arange(1 << fmt.fec_smallbits, dtype=np.uint32), fmt)
        self.codebook = codebook
        self._signs = (((codebook[:, None] >> self._shifts[None, :]) & 1).astype(np.float32)
                       * 2 - 1)  # fmt: skip
        self._stop()
        self._seed()
        self._stop()
        self._sample_grid(image)
        self._regions()
        self.rounds = 0
        self.words: np.ndarray | None = None
        self.margin: np.ndarray | None = None
        self.distance: np.ndarray | None = None

    def _stop(self) -> None:
        if self.cancelled():
            raise Stopped

    def _codewords(self, channel: np.ndarray) -> np.ndarray:
        matrix = channel[: self.used].reshape(self.large, self.syms).astype(np.uint32)
        return (matrix << self._shifts[:, None]).sum(axis=0, dtype=np.uint32)

    def _channel(self, codewords: np.ndarray) -> np.ndarray:
        return ((codewords[None, :] >> self._shifts[:, None]) & 1).astype(np.uint8).reshape(-1)

    def _seed(self) -> None:
        """The ordinary read: labels and known dots for the first fit."""
        g, fmt = self.grid, self.fmt
        filtered = blur(minmax(g.cleaned, g.geometry, g.options), g.geometry, g.options)
        raw = sample_bits(filtered, g.positions, g.cutlevels, g.geometry, fmt, g.options)
        del filtered
        words, errors = decode_symbols(self._codewords(raw), fmt)
        known = (errors >= 0) & (errors <= SEED_ERRORS)
        self.known_share = float(np.mean(known)) if known.size else 0.0
        self.labels = self._channel(encode_symbols(words, fmt))
        self.known = np.tile(known, self.large)

    def _sample_grid(self, image: np.ndarray) -> None:
        """The scan sampled at every SAMPLE_OFFSETS step over the data area.

        Entry [j, i] is at page x = (i - _REACH) * _STEP, y likewise, so the
        samples of dot (x, y) are entries [_PER_DOT * y + a, _PER_DOT * x + b]
        for a, b in range(len(SAMPLE_OFFSETS)): the same points as sampling
        around each dot, computed once.
        """
        fmt = self.fmt
        xs, ys = channel_xy(fmt)
        xs, ys = xs[: self.used], ys[: self.used]
        self.width = int(xs.max()) + 1
        self.height = int(ys.max()) + 1
        cols = _PER_DOT * (self.width - 1) + 2 * _REACH + 1
        rows = _PER_DOT * (self.height - 1) + 2 * _REACH + 1
        px = (np.arange(cols) - _REACH) * _STEP
        out = np.empty((rows, cols), np.float32)
        for start in range(0, rows, _GRID_ROWS):
            self._stop()
            py = (np.arange(start, min(start + _GRID_ROWS, rows)) - _REACH) * _STEP
            sx, sy = page_to_scan(self.grid, px[None, :], py[:, None])
            out[start : start + len(py)] = _bilinear(image, sx, sy)
        self.samples = out
        # windows[y, x] is the len(SAMPLE_OFFSETS)-square of samples of dot (x, y): a view.
        self.windows = np.lib.stride_tricks.sliding_window_view(out, (_N, _N))[
            ::_PER_DOT, ::_PER_DOT
        ]
        pagemap = np.full((self.height, self.width), -1, np.int64)
        pagemap[ys, xs] = np.arange(self.used)
        self.pagemap = pagemap

    def _regions(self) -> None:
        """Per region: its bounds, the mask of data dots and their channel indices."""
        across, down = REGIONS
        xb = [-(-t * self.width // across) for t in range(across + 1)]
        yb = [-(-t * self.height // down) for t in range(down + 1)]
        self.region_list = []
        for ty in range(down):
            for tx in range(across):
                y0, y1, x0, x1 = yb[ty], yb[ty + 1], xb[tx], xb[tx + 1]
                if y1 <= y0 or x1 <= x0:
                    continue
                block = self.pagemap[y0:y1, x0:x1]
                mask = block >= 0
                if mask.any():
                    self.region_list.append((y0, y1, x0, x1, mask, block[mask]))

    def _features(self, region) -> np.ndarray:
        """The region's dots' samples less their mean, centre squares and a constant."""
        y0, y1, x0, x1, mask, ids = region
        x = np.empty((len(ids), _FEATURES), np.float32)
        lin = x[:, : _N * _N]
        lin[:] = self.windows[y0:y1, x0:x1][mask].reshape(len(ids), _N * _N)
        lin -= lin.mean(axis=1, keepdims=True)
        x[:, _N * _N : -1] = lin[:, _CENTRE] ** 2 * np.float32(_SQUARE_SCALE)
        x[:, -1] = 1
        return x

    def _fit(self) -> np.ndarray:
        """One fit: a signed confidence (positive: dark) for every channel dot."""
        soft = np.zeros(self.used, np.float32)
        target = self.labels.astype(np.float32) * 2 - 1
        late = []
        total_g = np.zeros((_FEATURES, _FEATURES))
        total_b = np.zeros(_FEATURES)
        total_n = 0
        for region in self.region_list:
            self._stop()
            ids = region[5]
            x = self._features(region)
            known = self.known[ids]
            xk = x[known]
            g = (xk.T @ xk).astype(np.float64)
            b = (xk.T @ target[ids][known]).astype(np.float64)
            n = len(xk)
            total_g += g
            total_b += b
            total_n += n
            if n >= _MIN_FIT_DOTS:
                soft[ids] = _apply(x, _solve(g, b, n))
            else:
                late.append(region)
        if late:
            if total_n < _MIN_FIT_DOTS:
                raise DecodeError("too few known dots on the page to learn from")
            weights = _solve(total_g, total_b, total_n)
            for region in late:
                self._stop()
                soft[region[5]] = _apply(self._features(region), weights)
        return soft

    def _choose(self, soft: np.ndarray) -> None:
        """The best-fitting codeword of every symbol and its lead over the next."""
        scores = soft.reshape(self.large, self.syms).T
        best = np.empty(self.syms, np.int64)
        margin = np.empty(self.syms, np.float32)
        rows = np.arange(_SCORE_CHUNK)
        for s in range(0, self.syms, _SCORE_CHUNK):
            self._stop()
            fit = scores[s : s + _SCORE_CHUNK] @ self._signs.T
            r = rows[: len(fit)]
            top = fit.argmax(axis=1)
            first = fit[r, top]
            fit[r, top] = -np.inf
            best[s : s + _SCORE_CHUNK] = top
            margin[s : s + _SCORE_CHUNK] = first - fit.max(axis=1)
        chosen = self.codebook[best]
        hard = self._codewords((soft > 0).astype(np.uint8))
        flipped = self._channel(chosen ^ hard).reshape(self.large, self.syms)
        self.words, self.margin = best.astype(np.uint32), margin
        self.distance = flipped.sum(axis=0, dtype=np.int64)
        self.labels = self._channel(chosen)
        cut = np.quantile(margin, 1 - KEEP) if margin.size else 0.0
        self.known = np.tile(margin > cut, self.large)

    def step(self) -> None:
        self._choose(self._fit())
        self.rounds += 1

    def result(self) -> PageResult:
        """The page as read by the last fit; no symbol is marked lost.

        Marking the least confident symbols lost was measured on the owner's
        scans: 1% gave a worst block of 39 instead of 40 of 64, 3% 39, 6% 45,
        10% 54, 15% failed. Too little gain to be worth a tuning number.
        """
        out = np.arange(self.fmt.fec_smallbits - 1, -1, -1, dtype=np.uint32)
        bits = ((self.words[:, None] >> out[None, :]) & 1).astype(np.uint8).ravel()
        lost = np.zeros(0, np.int64)
        histogram = np.bincount(self.distance, minlength=4)
        stats = PageStats(
            symbols=self.syms,
            error_histogram=tuple(int(n) for n in histogram),
            uncorrectable=len(lost),
        )
        return PageResult(
            bits=bits, stats=stats, debug_image=None, corrected_bits=None,
            lost_symbols=lost, grid=self.grid,
        )  # fmt: skip


def _apply(x: np.ndarray, weights: np.ndarray) -> np.ndarray:
    # einsum, not x @ weights: OpenBLAS's threaded matrix-vector product took
    # 25 times as long on these small blocks.
    return np.einsum("ij,j->i", x, weights)


def _solve(g: np.ndarray, b: np.ndarray, n: int) -> np.ndarray:
    a = g + RIDGE * n * np.eye(len(g))
    return np.linalg.solve(a, b).astype(np.float32)


def read_soft(
    grid: PageGrid, image: np.ndarray, cancelled: Callable[[], bool] | None = None
) -> PageResult:
    """Read a located page with the blur-aware method (module docstring).

    image is the upright grey scan the grid was located on. The result has
    the shape decode_located(..., detail=True) returns: bits, stats (the
    histogram counts symbols by how many of their dots' signs the chosen
    codeword overrules, which may be more than 3), lost_symbols (empty: every
    symbol gets its best codeword), corrected_bits None and the grid.

    Raises DecodeError when the page has too little the ordinary reader
    trusts to learn from, Stopped as soon as cancelled() returns True.
    """
    reader = _Reader(grid, image, cancelled or _never)
    for _ in range(ROUNDS):
        reader.step()
    return reader.result()


def _enlargement(corners: np.ndarray, fmt: PageFormat) -> float:
    """The factor that makes a dot of fmt about ENLARGE_TO pixels wide, at least 1."""
    width = identify._size(corners)[0]
    if width <= 0:
        return 1.0
    factor = ENLARGE_TO / (width / fmt.width)
    return max(1.0, round(factor / ENLARGE_STEP) * ENLARGE_STEP)


def _enlarge(image: np.ndarray, factor: float) -> tuple[np.ndarray, float]:
    """image enlarged by factor (Lanczos), at most to _MAX_ENLARGED_PIXELS, and
    the factor actually applied (of the width)."""
    h, w = image.shape
    factor = min(factor, math.sqrt(_MAX_ENLARGED_PIXELS / (h * w)))
    if factor <= 1.0:
        return image, 1.0
    size = (max(1, round(w * factor)), max(1, round(h * factor)))
    big = Image.fromarray(image).resize(size, Image.Resampling.LANCZOS)
    return np.asarray(big), size[0] / w


def _header(result: PageResult, fmt: PageFormat):
    """The header in a read page if it fits fmt (identify._header_fits), else None."""
    header = read_header(page_payload(result, fmt).data)
    return header if header is not None and identify._header_fits(header, fmt) else None


def _try(
    upright: np.ndarray,
    rotation: int,
    layout: Layout,
    options: DecodeOptions | None,
    stop: Callable[[], bool],
) -> tuple[PageGrid, PageResult] | None:
    """A candidate's grid and soft read if it carries a header that fits, else None.

    Drops the candidate early when its grid is not regular, when the ordinary
    read gives fewer than MIN_KNOWN known symbols, or when the first fit
    shows no header that fits.
    """
    fmt = layout.fmt
    try:
        grid = locate_page(upright, fmt, options)
    except DecodeError:
        return None
    if not identify._regular(grid):
        return None
    if stop():
        raise Stopped
    try:
        reader = _Reader(grid, upright, stop)
        if reader.known_share < MIN_KNOWN:
            return None
        while reader.rounds < ROUNDS:
            reader.step()
            if reader.rounds == 1 and _header(reader.result(), fmt) is None:
                return None
        result = reader.result()
    except DecodeError:
        return None
    if _header(result, fmt) is None:
        return None
    return grid, result


def identify_coarse(
    image: np.ndarray,
    options: DecodeOptions | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> identify.ScanIdentity:
    """Identify a version-1 page with the slow reader, by its header only.

    The page outline is found on the scan as given; the candidate layouts
    and rotations are tried in identify_scan's order (papers closest in
    shape first, then identify._layouts_by_shape, each in every candidate
    rotation). For each, the scan is enlarged so that a dot of the layout is
    about ENLARGE_TO pixels wide (not at all if it already is), the page is
    located, read with read_soft and accepted by a header that fits the
    layout (identify._header_fits), from the final fit.

    The identity has reader "slow", the header, the payload and the result;
    its grid is located on the enlarged upright scan; scan_dpi is that of
    the scan as given; name is "" and tag None (a coarse scan's label is
    not read). Raises IdentifyError like identify_scan, Stopped when
    cancelled() returns True.
    """
    stop = cancelled or _never
    image = identify._check(image)
    rotations = identify.candidate_rotations(image)
    outlines = {r: identify._outline(identify._turn(image, r), options) for r in rotations}
    outline = next((c for r in rotations if (c := outlines[r]) is not None), None)
    if outline is None:
        raise IdentifyError(identify.NO_PAGE)
    enlarged: dict[float, tuple[np.ndarray, float]] = {}
    for paper in identify._papers_by_shape(outline):
        for layout in identify._layouts_by_shape(outline, paper):
            for rotation in rotations:
                corners = outlines[rotation]
                if corners is None:
                    continue
                if stop():
                    raise Stopped
                factor = _enlargement(corners, layout.fmt)
                if factor not in enlarged:
                    enlarged.clear()  # one enlarged scan at a time
                    enlarged[factor] = _enlarge(image, factor)
                big, applied = enlarged[factor]
                found = _try(identify._turn(big, rotation), rotation, layout, options, stop)
                if found is None:
                    continue
                grid, result = found
                payload = page_payload(result, layout.fmt)
                header = read_header(payload.data)
                return identify.ScanIdentity(
                    layout.paper, layout.fmt, rotation, header.page, header.total, None, "",
                    0.0, 0.0, grid, layout=layout, header=header, payload=payload,
                    result=result, scan_dpi=identify.scan_dpi(grid, layout) / applied,
                    reader="slow",
                )  # fmt: skip
    raise IdentifyError(identify.LABEL_UNREADABLE, scan_dpi=identify._outline_dpi(outline))

