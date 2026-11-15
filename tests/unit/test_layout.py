# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import numpy as np

from optar.format import PageFormat
from optar.layout import channel_xy, is_cross

F = PageFormat(65, 93)


def test_every_bit_has_a_distinct_data_pixel():
    x, y = channel_xy(F)
    assert len(x) == len(y) == F.total_bits == 3196368
    assert x.min() == 0 and y.min() == 0
    assert x.max() == F.data_width - 1 and y.max() == F.data_height - 1
    assert not is_cross(F, x, y).any()
    assert len(np.unique(y.astype(np.int64) * F.data_width + x)) == F.total_bits


def test_data_pixels_plus_cross_pixels_fill_the_data_area():
    cross_pixels = F.xcrosses * F.ycrosses * (2 * F.chalf) ** 2
    assert F.total_bits + cross_pixels == F.data_width * F.data_height


def test_first_positions_match_seq2xy():
    x, y = channel_xy(F)
    assert (x[0], y[0]) == (6, 0)  # first gap, after the first cross
    assert (x[17], y[17]) == (23, 0) and (x[18], y[18]) == (30, 0)  # jumps the next cross
    n = F.narrow_pixels
    assert (x[n], y[n]) == (0, 6)  # first wide strip starts at the left edge


def test_arrays_are_read_only():
    x, _ = channel_xy(F)
    assert not x.flags.writeable
