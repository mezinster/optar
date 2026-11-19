# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Corner finding and page geometry: diag_scan and find_corners (unoptar.c)."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from optar.decoder.options import DecodeOptions
from optar.errors import DecodeError, error
from optar.format import PageFormat


def _diag_scan(img: np.ndarray, cut: int, from_right: bool, from_bottom: bool):
    """First pixel below cut in C's diag_scan order, or None.

    In coordinates mirrored so the starting corner is (0, 0), diag_scan visits
    diagonal k = x' + y' for k = 0, 1, ... and walks each one from y' = 0
    downwards. Its loop bound xbegin < MIN(width, height) limits k to
    k < MIN(width, height); a scan starting at x = width-1 runs only when
    width <= height.
    """
    h, w = img.shape
    m = min(w, h)
    if from_right and w > h:
        return None
    view = img[:: -1 if from_bottom else 1, :: -1 if from_right else 1]
    size = 64
    while True:
        size = min(size, m)
        ys, xs = np.nonzero(view[:size, :size] < cut)
        k = xs + ys
        sel = k < size
        if sel.any():
            ys, k = ys[sel], k[sel]
            best = np.lexsort((ys, k))[0]
            yp, xp = int(ys[best]), int(k[best] - ys[best])
            x = w - 1 - xp if from_right else xp
            y = h - 1 - yp if from_bottom else yp
            return x, y
        if size == m:
            return None
        size *= 2


def _no_corner(name: str) -> DecodeError:
    """A corner that is not found; each message is whole, to be translated whole."""
    if name == "upper left":
        return error(DecodeError, "err.no_corner.upper_left", "cannot find upper left corner")
    if name == "upper right":
        return error(DecodeError, "err.no_corner.upper_right", "cannot find upper right corner")
    if name == "lower left":
        return error(DecodeError, "err.no_corner.lower_left", "cannot find lower left corner")
    return error(DecodeError, "err.no_corner.lower_right", "cannot find lower right corner")


def find_corners(img: np.ndarray, cut: int) -> np.ndarray:
    """Corners UL, UR, LL, LR as (x, y), integers at pixel upper left corners."""
    corners = np.zeros((4, 2), np.int64)
    scans = [
        ("upper left", False, False, 0, 0),
        ("upper right", True, False, 1, 0),
        ("lower left", False, True, 0, 1),
        ("lower right", True, True, 1, 1),
    ]
    for i, (name, from_right, from_bottom, ax, ay) in enumerate(scans):
        found = _diag_scan(img, cut, from_right, from_bottom)
        if found is None:
            raise _no_corner(name)
        corners[i] = (found[0] + ax, found[1] + ay)
    return corners


@dataclass(frozen=True)
class Geometry:
    corners: tuple[tuple[int, int], ...]  # UL, UR, LL, LR as (x, y)
    hpixel: float  # input pixels per page pixel, horizontally
    vpixel: float  # and vertically
    ph: tuple[float, float]  # unit vector along a page row
    pv: tuple[float, float]  # unit vector along a page column
    chalf: int  # cross half size for coarse sync, in input pixels
    chalf_fine: int  # trimmed cross half size for fine sync


def _normalize(x: float, y: float) -> tuple[float, float]:
    length = math.sqrt(x * x + y * y)
    return x / length, y / length


def compute_geometry(corners, fmt: PageFormat, opts: DecodeOptions) -> Geometry:
    c = tuple((int(x), int(y)) for x, y in corners)
    # C quirk kept: corner 0's x is subtracted twice (corner 2's x never).
    hpixel = (c[1][0] + c[3][0] - c[0][0] - c[0][0]) / 2.0 / fmt.width
    vpixel = (c[2][1] + c[3][1] - c[0][1] - c[1][1]) / 2.0 / fmt.height

    # Take only half to avoid resyncing to an edge of the cross.
    chalf = min(int(hpixel * fmt.chalf * 0.5), int(vpixel * fmt.chalf * 0.5))
    chalf_fine = min(
        int(hpixel * (fmt.chalf - opts.cross_trim)), int(vpixel * (fmt.chalf - opts.cross_trim))
    )

    ph = _normalize(
        (float(c[1][0]) + float(c[3][0]) - float(c[0][0]) - float(c[2][0])) / 2,
        (float(c[1][1]) + float(c[3][1]) - float(c[0][1]) - float(c[2][1])) / 2,
    )
    pv = _normalize(
        (float(c[2][0]) + float(c[3][0]) - float(c[0][0]) - float(c[1][0])) / 2,
        (float(c[2][1]) + float(c[3][1]) - float(c[0][1]) - float(c[1][1])) / 2,
    )
    return Geometry(c, hpixel, vpixel, ph, pv, chalf, chalf_fine)
