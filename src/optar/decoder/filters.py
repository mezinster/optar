# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Dust filter and blur: process_minmax, max, min and blur_copy (unoptar.c).

Both return a new array and leave their input untouched (C works in place).
"""

from __future__ import annotations

import math

import numpy as np

from optar.decoder.options import DecodeOptions


def _minmax_passes(geom, opts: DecodeOptions) -> int:
    # C: float npix = sqrt(...); npix *= minmax_filter (double); npix = floor(npix).
    npix = np.float32(math.sqrt(geom.vpixel * geom.hpixel))
    npix = np.float32(float(npix) * opts.minmax_filter)
    return int(math.floor(npix))


def minmax(img: np.ndarray, geom, opts: DecodeOptions) -> np.ndarray:
    """n passes of max() then n passes of min(): removes dark specks below n pixels.

    max(): each pixel takes the maximum with its original left neighbour, then
    with the (horizontally processed) pixel above. min(): minimum with the
    original right neighbour, then with the pixel below. The first column and
    row (max) or last column and row (min) only feed their neighbours.
    """
    a = np.array(img, np.uint8, copy=True)
    n = _minmax_passes(geom, opts)
    for _ in range(n):
        a[:, 1:] = np.maximum(a[:, 1:], a[:, :-1])
        a[1:] = np.maximum(a[1:], a[:-1])
    for _ in range(n):
        a[:, :-1] = np.minimum(a[:, :-1], a[:, 1:])
        a[:-1] = np.minimum(a[:-1], a[1:])
    return a


def blur(img: np.ndarray, geom, opts: DecodeOptions) -> np.ndarray:
    """Passes of the 1 2 1 / 2 4 2 / 1 2 1 kernel, (sum + 8) >> 4, edges copied."""
    cycles = math.floor(geom.vpixel * geom.hpixel * opts.pixel_blur * opts.pixel_blur + 0.5)
    a = np.array(img, np.uint8, copy=True)
    if cycles <= 0 or a.shape[0] < 3 or a.shape[1] < 3:
        return a
    s = a.astype(np.uint16)  # 16 * 255 + 8 fits
    for _ in range(cycles):
        mid = s[1:-1]
        acc = mid[:, 1:-1] << 2
        sides = mid[:, :-2] + mid[:, 2:]
        sides += s[:-2, 1:-1]
        sides += s[2:, 1:-1]
        sides <<= 1
        acc += sides
        del sides
        acc += s[:-2, :-2]
        acc += s[:-2, 2:]
        acc += s[2:, :-2]
        acc += s[2:, 2:]
        acc += 8
        acc >>= 4
        s[1:-1, 1:-1] = acc  # acc is a fresh array, so every term read the previous cycle
        del acc
    return s.astype(np.uint8)
