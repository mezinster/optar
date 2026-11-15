# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Grey-level analysis: calc_histogram and analyze_cutlevel (unoptar.c)."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from optar.decoder.options import DecodeOptions

_MAXITER = 32
_f32 = np.float32


@dataclass(frozen=True)
class Levels:
    average: int  # rounded mean pixel value
    cut: int  # global_cutlevel, used for positioning
    fill_cut: int  # fill_global_cutlevel, halfway between black and white


def analyze_levels(img: np.ndarray, opts: DecodeOptions) -> Levels:
    hist = [int(v) for v in np.bincount(img.ravel(), minlength=256)]
    n = img.size
    total = sum(i * h for i, h in enumerate(hist))
    average = (total + (n >> 1)) // n

    swc = _f32(opts.sync_white_cut)
    one_minus_swc = _f32(_f32(1) - swc)
    cut = fill_cut = average
    for _ in range(_MAXITER):
        last = cut
        # Sums accumulate in C float, bin by bin, in this order.
        black_rms = white_rms = _f32(0)
        black_pixels = white_pixels = 0
        for i in range(cut):
            d = _f32(cut - i)
            black_rms = _f32(black_rms + _f32(_f32(_f32(hist[i]) * d) * d))
            black_pixels += hist[i]
        for i in range(cut + 1, 256):
            d = _f32(i - cut)
            white_rms = _f32(white_rms + _f32(_f32(_f32(hist[i]) * d) * d))
            white_pixels += hist[i]

        if black_pixels == 0 or white_pixels == 0:
            # C divides 0 by 0 here: white or black becomes NaN, so both
            # cut levels are NaN converted to unsigned char, which x86 makes 0.
            cut = fill_cut = 0
        else:
            white_rms = _f32(math.sqrt(float(_f32(white_rms / _f32(white_pixels)))))
            black_rms = _f32(math.sqrt(float(_f32(black_rms / _f32(black_pixels)))))
            white = _f32(_f32(cut) + white_rms)
            black = _f32(_f32(cut) - black_rms)
            cut = math.floor(float(_f32(_f32(white * swc) + _f32(black * one_minus_swc))) + 0.5)
            fill_cut = math.floor(float(white) * 0.5 + float(black) * 0.5 + 0.5)
        if cut == last:
            break
    return Levels(average=average, cut=cut, fill_cut=fill_cut)
