# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import numpy as np
import pytest

from optar.decoder.crosses import sync_crosses
from optar.decoder.filters import _minmax_passes, blur, minmax
from optar.decoder.geometry import compute_geometry, find_corners
from optar.decoder.levels import analyze_levels
from optar.decoder.options import DecodeOptions
from optar.decoder.sample import sample_bits
from optar.encoder import encode
from optar.format import PageFormat
from optar.layout import channel_xy
from tests.helpers import fake_scan, seeded_bytes

F, OPTS = PageFormat(65, 93), DecodeOptions()


class G:  # minimal stand-in for Geometry in filter tests
    def __init__(self, s):
        self.hpixel = self.vpixel = float(s)


def test_minmax_scale_3_removes_a_one_pixel_dark_speck():
    img = np.full((12, 12), 255, np.uint8)
    img[5:11, 5:11] = 0
    specked = img.copy()
    specked[2, 2] = 0
    assert np.array_equal(minmax(specked, G(3), OPTS), minmax(img, G(3), OPTS))  # 1 pass each
    assert np.array_equal(minmax(specked, G(1), OPTS), specked)  # floor(1*0.5) = 0 passes


def _c_max(ary, width, height):
    """Literal port of max() in unoptar.c: pointer walks over a flat array."""
    ptr = width * height
    for _ in range(height):
        linestart = ptr - width
        ptr -= 1
        while ptr > linestart:
            ary[ptr] = max(ary[ptr], ary[ptr - 1])
            ptr -= 1
    end = width
    ptr = width * height - 1
    while ptr >= end:
        ary[ptr] = max(ary[ptr], ary[ptr - width])
        ptr -= 1


def _c_min(ary, width, height):
    """Literal port of min() in unoptar.c."""
    ptr = 0
    for _ in range(height):
        end = ptr + width - 1
        while ptr < end:
            ary[ptr] = min(ary[ptr], ary[ptr + 1])
            ptr += 1
        ptr += 1
    end = width * (height - 1)
    ptr = 0
    while ptr < end:
        ary[ptr] = min(ary[ptr], ary[ptr + width])
        ptr += 1


@pytest.mark.parametrize("scale,passes", [(5, 2), (6, 3)])
def test_minmax_multi_pass_matches_literal_c_port(scale, passes):
    # process_minmax: npix = floor(sqrt(vpixel * hpixel) * 0.5) passes of max(), then of min().
    rng = np.random.default_rng(scale)
    height, width = 9, 13
    img = rng.integers(0, 256, (height, width), dtype=np.uint8)
    ary = [int(v) for v in img.ravel()]
    for _ in range(passes):
        _c_max(ary, width, height)
    for _ in range(passes):
        _c_min(ary, width, height)
    want = np.array(ary, np.uint8).reshape(height, width)
    assert _minmax_passes(G(scale), OPTS) == passes
    assert np.array_equal(minmax(img, G(scale), OPTS), want)


def test_minmax_one_pass_follows_c_neighbours():
    img = np.arange(16, dtype=np.uint8).reshape(4, 4)[::-1, ::-1].copy() * 10
    before = img.copy()
    out = minmax(img, G(3), OPTS)
    assert np.array_equal(img, before)  # input untouched
    mx = img.copy()
    mx[:, 1:] = np.maximum(img[:, 1:], img[:, :-1])
    mx[1:] = np.maximum(mx[1:], mx[:-1].copy())
    mn = mx.copy()
    mn[:, :-1] = np.minimum(mx[:, :-1], mx[:, 1:])
    mn[:-1] = np.minimum(mn[:-1], mn[1:].copy())
    assert np.array_equal(out, mn)


def test_blur_passes_and_edges():
    img = np.zeros((5, 5), np.uint8)
    img[2, 2] = 160
    assert np.array_equal(blur(img, G(1), OPTS), img)  # round(0.0625) = 0 passes
    out = blur(img, G(3), OPTS)  # round(0.5625) = 1 pass
    assert out[2, 2] == 40 and out[2, 1] == 20 and out[1, 1] == 10
    assert np.array_equal(img[2, 2], 160)  # input untouched
    edge = np.arange(25, dtype=np.uint8).reshape(5, 5)
    b = blur(edge, G(3), OPTS)
    assert np.array_equal(b[0], edge[0]) and np.array_equal(b[:, 0], edge[:, 0])
    assert np.array_equal(b[-1], edge[-1]) and np.array_equal(b[:, -1], edge[:, -1])


def test_blur_two_passes_feed_each_other():
    img = np.zeros((7, 7), np.uint8)
    img[3, 3] = 255
    once = blur(img, G(3), OPTS)
    twice = blur(img, G(5), OPTS)  # floor(25/16 + 0.5) = 2 passes
    assert np.array_equal(twice, blur(once, G(3), OPTS))


@pytest.mark.parametrize("scale", [1, 2, 3])
def test_sampled_bits_equal_the_page(scale):
    page = next(encode(seeded_bytes(9, 150000), F)).pixels
    scan = fake_scan(page, scale=scale, margin=60)
    lv = analyze_levels(scan, OPTS)
    g = compute_geometry(find_corners(scan, lv.cut), F, OPTS)
    pos, cuts = sync_crosses(scan, g, F, lv, OPTS)
    img = blur(minmax(scan, g, OPTS), g, OPTS)
    bits = sample_bits(img, pos, cuts, g, F, OPTS)
    x, y = channel_xy(F)
    assert bits.dtype == np.uint8 and len(bits) == F.total_bits
    assert np.array_equal(bits, (page[y + F.border, x + F.border] == 0).astype(np.uint8))
