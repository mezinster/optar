# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The decoder's seven magic constants (unoptar.c "MAGIC CONSTANTS")."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DecodeOptions:
    unsharp_mask: float = 7.0
    unsharp_dist: float = 1.0  # 1: sample the neighbouring pixels
    sync_white_cut: float = 0.10  # cut used for positioning (C float)
    white_cut: float = 0.06  # cut used for quantisation (C float)
    minmax_filter: float = 0.5  # dust/scratch filter, times input pixel size
    pixel_blur: float = 0.25  # blur blot width in input pixels
    cross_trim: float = 0.75  # input pixels trimmed from a cross for fine search
