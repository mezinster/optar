# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Bit layout: which pixel each channel bit goes to (port of common.c)."""

from __future__ import annotations

from functools import cache

import numpy as np

from optar.format import PageFormat


def is_cross(fmt: PageFormat, x, y) -> np.ndarray:
    """True where (x, y) lies on a cross; coordinates exclude the border."""
    x = np.asarray(x)
    y = np.asarray(y)
    return ((x % fmt.cpitch) < 2 * fmt.chalf) & ((y % fmt.cpitch) < 2 * fmt.chalf)


@cache
def channel_xy(fmt: PageFormat) -> tuple[np.ndarray, np.ndarray]:
    """Pixel x, y (int32, read-only) of every channel bit, as seq2xy."""
    seq = np.arange(fmt.total_bits, dtype=np.int64)
    rep, s = np.divmod(seq, fmt.rep_pixels)
    y = fmt.rep_height * rep

    wide = s >= fmt.narrow_pixels
    # Wide strip: full-width rows.
    sw = s - fmt.narrow_pixels
    yw, xw = np.divmod(sw, fmt.wide_width)
    # Narrow strip: rows of gaps between crosses.
    yn, sn = np.divmod(s, fmt.narrow_width)
    gap, sg = np.divmod(sn, fmt.gap_width)
    xn = 2 * fmt.chalf + gap * fmt.cpitch + sg

    y = y + np.where(wide, fmt.narrow_height + yw, yn)
    x = np.where(wide, xw, xn)
    xs = x.astype(np.int32)
    ys = y.astype(np.int32)
    xs.flags.writeable = False
    ys.flags.writeable = False
    return xs, ys
