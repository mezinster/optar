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


def remove_border_dirt(img: np.ndarray, fill_cut: int) -> np.ndarray:
    """Whiten everything that is neither white border nor the data area."""
    h, w = img.shape
    seeds = [
        (0, 0), (w >> 1, 0), (w - 1, 0), (0, h >> 1),
        (0, h - 1), (w - 1, h - 1), (w - 1, h >> 1), (w >> 1, h - 1),
    ]  # fmt: skip
    border = _reach(img >= fill_cut, seeds)
    data = _reach(~border, [(w >> 1, h >> 1)])
    out = img.copy()
    out[~(border | data)] = 0xFF
    return out
