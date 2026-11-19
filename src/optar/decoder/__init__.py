# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Decoder for scanned optar pages (port of unoptar.c).

decode_page runs the stages in process_file order, in two halves:
locate_page finds the page and its crosses (a PageGrid), decode_located
samples and decodes the bits. decode_pages runs decode_page over a sequence
of scans; decode concatenates the pages' payload bits into one
stream with BitPacker, as C's static accumulator in read_payload_bit does,
and drops a trailing partial byte.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass

import numpy as np

from optar.decoder.crosses import sync_crosses
from optar.decoder.dirt import isolate_page
from optar.decoder.filters import blur, minmax
from optar.decoder.geometry import Geometry, compute_geometry, find_corners
from optar.decoder.levels import Levels, analyze_levels
from optar.decoder.options import DecodeOptions
from optar.decoder.sample import _cell, _cell_point, sample_bits
from optar.errors import DecodeError, error
from optar.fec import decode_symbols, encode_symbols
from optar.format import PageFormat

__all__ = [
    "BitPacker",
    "DecodeOptions",
    "DecodeResult",
    "PageGrid",
    "PageResult",
    "PageStats",
    "decode",
    "decode_located",
    "decode_page",
    "decode_pages",
    "locate_page",
    "page_to_scan",
]

_HISTOGRAM_SIZE = 4  # symbols with 0, 1, 2, 3 corrected bits


@dataclass(frozen=True)
class PageStats:
    symbols: int
    error_histogram: tuple[int, ...]  # symbols with 0, 1, 2, 3 corrected bits
    uncorrectable: int

    @property
    def max_corrected(self) -> int:
        nonzero = [i for i, n in enumerate(self.error_histogram) if n]
        return nonzero[-1] if nonzero else 0


@dataclass(frozen=True, eq=False)
class PageGrid:
    """A located page: everything sampling and label reading need."""

    fmt: PageFormat
    options: DecodeOptions
    cleaned: np.ndarray  # the scan after border dirt removal
    levels: Levels
    geometry: Geometry
    positions: np.ndarray  # cross centres (xcrosses, ycrosses, 2), integers at pixel corners
    cutlevels: np.ndarray  # per-cross cut levels (xcrosses, ycrosses) float32


@dataclass(frozen=True)
class PageResult:
    bits: np.ndarray  # uint8 0/1, length fmt.net_bits
    stats: PageStats
    debug_image: np.ndarray | None
    # The following are None unless decoded with detail=True.
    corrected_bits: np.ndarray | None = None  # int64 channel positions error correction changed
    lost_symbols: np.ndarray | None = None  # int64 indices of uncorrectable symbols
    grid: PageGrid | None = None


@dataclass(frozen=True)
class DecodeResult:
    data: bytes
    pages: tuple[PageStats, ...]

    @property
    def uncorrectable(self) -> int:
        return sum(p.uncorrectable for p in self.pages)


def _check_image(image: np.ndarray, fmt: PageFormat) -> np.ndarray:
    image = np.asarray(image)
    if image.ndim != 2 or image.dtype != np.uint8:
        raise error(
            DecodeError, "err.scan_not_grey",
            "scan must be a 2-D uint8 grey image, got shape {shape} dtype {dtype}",
            shape=image.shape, dtype=image.dtype,
        )
    if image.size == 0:
        raise error(DecodeError, "err.scan_empty", "scan is empty")
    h, w = image.shape
    if w < fmt.width or h < fmt.height:
        raise error(
            DecodeError, "err.scan_too_small",
            "scan of {width} x {height} pixels is smaller than the page format's "
            "{page_width} x {page_height}",
            width=w, height=h, page_width=fmt.width, page_height=fmt.height,
        )
    return image


def _debug_image(filtered: np.ndarray, positions: np.ndarray) -> np.ndarray:
    """The filtered image with C's mark() at each cross centre."""
    out = filtered.copy()
    h, w = out.shape
    for x, y in positions.reshape(-1, 2):
        xu, yu = math.floor(x + 0.5), math.floor(y + 0.5)
        for px, py, value in ((xu, yu, 255), (xu - 1, yu - 1, 255), (xu - 1, yu, 0),
                              (xu, yu - 1, 0)):  # fmt: skip
            if 0 <= px < w and 0 <= py < h:
                out[py, px] = value
    return out


def _symbols_to_bits(channel_bits: np.ndarray, fmt: PageFormat, *, detail: bool = False):
    """De-interleave, decode the symbols and return (payload bits, errors, corrected).

    corrected is None unless detail: then the ascending int64 channel
    positions of every bit the correction changed.
    """
    syms, large, small = fmt.fec_syms, fmt.fec_largebits, fmt.fec_smallbits
    # Bit b (0 = most significant) of symbol s is at channel position s + b * syms.
    matrix = channel_bits[: fmt.used_bits].reshape(large, syms).astype(np.uint32)
    shifts = np.arange(large - 1, -1, -1, dtype=np.uint32)
    codewords = (matrix << shifts[:, None]).sum(axis=0, dtype=np.uint32)
    words, errors = decode_symbols(codewords, fmt)
    out_shifts = np.arange(small - 1, -1, -1, dtype=np.uint32)
    bits = ((words[:, None] >> out_shifts[None, :]) & 1).astype(np.uint8).ravel()
    corrected = None
    if detail:
        fixed = np.flatnonzero(errors > 0)
        changed = codewords[fixed] ^ encode_symbols(words[fixed], fmt)
        b, i = np.nonzero((changed[None, :] >> shifts[:, None]) & 1)
        corrected = np.sort(fixed[i] + b.astype(np.int64) * syms)
    return bits, errors, corrected


def locate_page(
    image: np.ndarray, fmt: PageFormat, options: DecodeOptions | None = None
) -> PageGrid:
    """Find the page in a scan: grey levels, dirt removal, corners, crosses."""
    opts = options or DecodeOptions()
    image = _check_image(image, fmt)

    levels = analyze_levels(image, opts)
    cleaned = isolate_page(image, levels.fill_cut)
    corners = find_corners(cleaned, levels.cut)
    try:
        geom = compute_geometry(corners, fmt, opts)
    except ZeroDivisionError:
        raise error(
            DecodeError, "err.corners_coincide", "page corners are degenerate (they coincide)"
        ) from None
    if geom.chalf <= 0:
        raise error(
            DecodeError, "err.page_too_small",
            "page found in the scan is too small to locate its crosses",
        )
    positions, cutlevels = sync_crosses(cleaned, geom, fmt, levels, opts)
    return PageGrid(fmt, opts, cleaned, levels, geom, positions, cutlevels)


def decode_located(grid: PageGrid, *, debug: bool = False, detail: bool = False) -> PageResult:
    """Sample and decode a located page into its fmt.net_bits payload bits."""
    fmt, opts, geom = grid.fmt, grid.options, grid.geometry
    filtered = blur(minmax(grid.cleaned, geom, opts), geom, opts)
    channel_bits = sample_bits(filtered, grid.positions, grid.cutlevels, geom, fmt, opts)

    bits, errors, corrected_bits = _symbols_to_bits(channel_bits, fmt, detail=detail)
    corrected = errors[errors >= 0]
    histogram = np.bincount(corrected, minlength=_HISTOGRAM_SIZE)
    stats = PageStats(
        symbols=fmt.fec_syms,
        error_histogram=tuple(int(n) for n in histogram),
        uncorrectable=int(np.count_nonzero(errors < 0)),
    )
    debug_image = _debug_image(filtered, grid.positions) if debug else None
    if not detail:
        return PageResult(bits=bits, stats=stats, debug_image=debug_image)
    return PageResult(
        bits=bits,
        stats=stats,
        debug_image=debug_image,
        corrected_bits=corrected_bits,
        lost_symbols=np.flatnonzero(errors < 0).astype(np.int64),
        grid=grid,
    )


def decode_page(
    image: np.ndarray,
    fmt: PageFormat,
    options: DecodeOptions | None = None,
    *,
    debug: bool = False,
    detail: bool = False,
) -> PageResult:
    """Decode one scanned page into its fmt.net_bits payload bits.

    With detail, the result also carries the corrected bit positions, the
    uncorrectable symbols and the PageGrid.
    """
    return decode_located(locate_page(image, fmt, options), debug=debug, detail=detail)


def page_to_scan(grid: PageGrid, x, y) -> tuple[np.ndarray, np.ndarray]:
    """Scan coordinates (integers at pixel centres) of page coordinates x, y.

    x, y are as layout.channel_xy (relative to the top-left cross, without
    the border), scalars or arrays of any shape, and may be fractional or lie
    outside the cross grid: they are interpolated, or extrapolated from the
    nearest cell, between the cross centres as the sampler does. They must
    be finite.
    """
    x, y = np.broadcast_arrays(np.asarray(x), np.asarray(y))
    shape = x.shape
    xd, yd = _cell_point(grid.positions, *_cell(x.ravel(), y.ravel(), grid.fmt))
    return xd.reshape(shape), yd.reshape(shape)


def decode_pages(
    images: Iterable[np.ndarray],
    fmt: PageFormat,
    options: DecodeOptions | None = None,
    *,
    debug: bool = False,
) -> Iterator[PageResult]:
    """Decode scans one at a time, yielding a PageResult per image.

    Images are taken from the iterable only as results are requested. A
    DecodeError raised for a page has its `page` attribute set to the page's
    1-based number.
    """
    for number, image in enumerate(images, start=1):
        try:
            result = decode_page(image, fmt, options, debug=debug)
        except DecodeError as e:
            e.page = number
            raise
        yield result


class BitPacker:
    """Packs a bit stream fed in chunks into bytes, most significant bit first.

    Each feed returns the bytes completed so far and keeps the leftover bits
    for the next chunk; a trailing partial byte is never emitted.
    """

    def __init__(self) -> None:
        self._carry = np.zeros(0, np.uint8)

    def feed(self, bits: np.ndarray) -> bytes:
        stream = np.concatenate((self._carry, np.asarray(bits, np.uint8)))
        whole = stream.size - stream.size % 8
        self._carry = stream[whole:].copy()
        return np.packbits(stream[:whole]).tobytes()


def decode(
    images: Iterable[np.ndarray],
    fmt: PageFormat,
    options: DecodeOptions | None = None,
    *,
    progress: Callable[[int, PageStats], None] | None = None,
) -> DecodeResult:
    """Decode pages in order into bytes, most significant bit first.

    The pages' payload bits form one stream; trailing bits that do not fill
    a byte are dropped, as C does. Pages are consumed one at a time.
    """
    packer = BitPacker()
    chunks: list[bytes] = []
    pages: list[PageStats] = []
    for number, result in enumerate(decode_pages(images, fmt, options), start=1):
        chunks.append(packer.feed(result.bits))
        pages.append(result.stats)
        if progress is not None:
            progress(number, result.stats)
    return DecodeResult(data=b"".join(chunks), pages=tuple(pages))
