# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Border dirt removal: remove_dirt_from_border (unoptar.c).

The C code flood-fills pixel by pixel. Here the same 4-connected
reachability is computed on horizontal runs: a breadth-first search over
runs, where two runs in adjacent rows are neighbours when they share a
column. Each BFS level is a handful of vectorised numpy calls.
"""

from __future__ import annotations

import numpy as np


def _reach(allowed: np.ndarray, seeds) -> np.ndarray:
    """Pixels of allowed that are 4-connected to an allowed seed (x, y)."""
    h, w = allowed.shape
    w1 = w + 1  # one False column per row keeps every run inside its row
    flat = np.zeros(h * w1 + 1, bool)  # flat[1 + p] is padded pixel p
    flat[1:].reshape(h, w1)[:, :w] = allowed
    edges = np.flatnonzero(flat[1:] != flat[:-1])
    starts = edges[0::2]  # first pixel of each run, as y * w1 + x
    ends = edges[1::2]  # one past the last pixel

    seed_runs = [
        np.searchsorted(starts, y * w1 + x, "right") - 1 for x, y in seeds if allowed[y, x]
    ]
    visited = np.zeros(starts.size, bool)
    frontier = np.unique(np.array(seed_runs, np.int64))
    visited[frontier] = True
    while frontier.size:
        s = starts[frontier]
        e = ends[frontier]
        # Runs in the row below (+w1) and above (-w1) that overlap [s, e).
        lo = np.concatenate(
            (np.searchsorted(ends, s + w1, "right"), np.searchsorted(ends, s - w1, "right"))
        )
        hi = np.concatenate(
            (np.searchsorted(starts, e + w1, "left"), np.searchsorted(starts, e - w1, "left"))
        )
        count = np.maximum(hi - lo, 0)
        total = int(count.sum())
        if total == 0:
            break
        offsets = np.cumsum(count) - count
        neighbours = np.repeat(lo - offsets, count) + np.arange(total)
        frontier = np.unique(neighbours[~visited[neighbours]])
        visited[frontier] = True

    marks = np.zeros(h * w1 + 1, np.int8)
    marks[starts[visited]] = 1
    marks[ends[visited]] = -1
    return np.cumsum(marks, dtype=np.int8)[: h * w1].reshape(h, w1)[:, :w].view(bool)


# A scan is this many times longer than the narrowest white passage that
# still counts as the white around the page (see _reach_wide), and the passage
# is never narrower than _MIN_PASSAGE pixels.
_PASSAGE_DIVISOR = 250
_MIN_PASSAGE = 5
# The page holds nearly everything that is not white border. When the area
# found from the centre is less than this share of it, the white outside has
# leaked into the page and cut it into pieces.
_PAGE_SHARE = 0.5


def _box_sum(mask: np.ndarray, r: int, fill: bool) -> np.ndarray:
    """For each pixel, how many pixels of mask lie in the (2r+1) square around
    it; pixels outside the image count as `fill`."""
    h, w = mask.shape
    padded = np.pad(mask, r, constant_values=fill).astype(np.int32)
    c = np.zeros((h + 2 * r + 1, w + 2 * r + 1), np.int32)
    np.cumsum(padded, axis=0, out=c[1:, 1:])
    np.cumsum(c[1:, 1:], axis=1, out=c[1:, 1:])
    k = 2 * r + 1
    return c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]


def _reach_wide(white: np.ndarray, seeds, r: int) -> np.ndarray:
    """The white reachable from the seeds through passages at least 2r+1 wide.

    The white between the dots of a page is narrower than that, so a gap in
    the page's frame does not let the white around the page into its data.
    """
    k = 2 * r + 1
    roomy = _box_sum(white, r, True) == k * k  # white all around, r pixels each way
    reached = _reach(roomy, seeds)
    return white & (_box_sum(reached, r, False) > 0)


def _whole(border: np.ndarray, data: np.ndarray) -> bool:
    """True if the area found from the centre is most of what is not border."""
    inside = int(data.sum())
    return inside > 0 and inside >= _PAGE_SHARE * (border.size - int(border.sum()))


def _seeds(h: int, w: int) -> list[tuple[int, int]]:
    return [
        (0, 0), (w >> 1, 0), (w - 1, 0), (0, h >> 1),
        (0, h - 1), (w - 1, h - 1), (w - 1, h >> 1), (w >> 1, h - 1),
    ]  # fmt: skip


def _whitened(img: np.ndarray, border: np.ndarray, data: np.ndarray) -> np.ndarray:
    out = img.copy()
    out[~(border | data)] = 0xFF
    return out


def remove_border_dirt(img: np.ndarray, fill_cut: int) -> np.ndarray:
    """Whiten everything that is neither white border nor the data area (as C)."""
    h, w = img.shape
    border = _reach(img >= fill_cut, _seeds(h, w))
    data = _reach(~border, [(w >> 1, h >> 1)])
    return _whitened(img, border, data)


def isolate_page(img: np.ndarray, fill_cut: int) -> np.ndarray:
    """remove_border_dirt for scans whose page frame may have a gap.

    The white border is everything connected to the edges of the scan, which
    needs the page's black frame to be whole: where a printer clipped an edge
    of the page, the border runs on into the page between its dots, the page
    falls into pieces and none is found. For such a scan only, the border is
    taken as what is reachable through wide passages (_reach_wide), which the
    frame's gap is and the white between dots is not. Every other scan gets
    exactly remove_border_dirt.
    """
    h, w = img.shape
    seeds, centre = _seeds(h, w), [(w >> 1, h >> 1)]
    white = img >= fill_cut
    border = _reach(white, seeds)
    data = _reach(~border, centre)
    if not _whole(border, data):
        passage = max(_MIN_PASSAGE, max(h, w) // _PASSAGE_DIVISOR)
        wide = _reach_wide(white, seeds, passage // 2)
        wide_data = _reach(~wide, centre)
        if _whole(wide, wide_data):
            border, data = wide, wide_data
    return _whitened(img, border, data)
