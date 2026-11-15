# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import numpy as np
import pytest

from optar.decoder.crosses import interp, sync_crosses
from optar.decoder.geometry import compute_geometry, find_corners
from optar.decoder.levels import analyze_levels
from optar.decoder.options import DecodeOptions
from optar.encoder import encode
from optar.format import PageFormat
from tests.helpers import fake_scan, seeded_bytes

F, OPTS = PageFormat(65, 93), DecodeOptions()


def prepared(**kw):
    scan = fake_scan(next(encode(seeded_bytes(5, 20000), F)).pixels, **kw)
    lv = analyze_levels(scan, OPTS)
    return scan, lv, compute_geometry(find_corners(scan, lv.cut), F, OPTS)


def test_interp_edges():
    img = np.array([[0, 100], [200, 50]], dtype=np.uint8)
    assert interp(img, np.array([0.5]), np.array([0.0]))[0] == pytest.approx(50)
    assert interp(img, np.array([-3.0]), np.array([0.0]))[0] == pytest.approx(-300)  # extrapolated
    assert interp(img, np.array([1.5]), np.array([0.0]))[0] == pytest.approx(177.5)  # 100 and 255


def test_interp_keeps_shape_and_dtype():
    img = np.array([[0, 100], [200, 50]], dtype=np.uint8)
    x = np.array([[0.0, 0.5], [1.0, 0.25]])
    y = np.array([[0.0, 0.5], [1.0, 0.75]])
    v = interp(img, x, y)
    assert v.shape == (2, 2) and v.dtype == np.float32
    assert v[0, 0] == 0 and v[0, 1] == pytest.approx(87.5)
    assert v[1, 0] == 50  # weights 0: only the upper left neighbour counts
    # 0.25, 0.75: u = 100*.25 + 0*.75 = 25, l = 50*.25 + 200*.75 = 162.5
    assert v[1, 1] == pytest.approx(25 * 0.25 + 162.5 * 0.75)


@pytest.mark.parametrize("scale", [1, 3])
def test_crosses_on_clean_scan(scale):
    scan, lv, g = prepared(scale=scale, margin=60)
    pos, cuts = sync_crosses(scan, g, F, lv, OPTS)
    assert pos.shape == (65, 93, 2) and cuts.shape == (65, 93) and cuts.dtype == np.float32
    assert pos.dtype == np.float64
    cx, cy = np.meshgrid(np.arange(65), np.arange(93), indexing="ij")
    want_x = 60 + (2 + 3 + 24 * cx) * scale
    want_y = 60 + (2 + 3 + 24 * cy) * scale
    assert np.abs(pos[..., 0] - want_x).max() <= 0.25
    assert np.abs(pos[..., 1] - want_y).max() <= 0.25


def test_cutlevels_on_clean_scan():
    scan, lv, g = prepared(scale=3, margin=60)
    _, cuts = sync_crosses(scan, g, F, lv, OPTS)
    # Pure 0/255 samples around an exact cross: white = cut + (255 - cut),
    # black = cut - cut, so the cut level is 255 * white_cut (C float).
    want = np.float32(np.float32(255) * np.float32(OPTS.white_cut))
    assert np.all(cuts == want)


def test_crosses_follow_a_small_rotation():
    scan, lv, g = prepared(scale=3, margin=120, rotate=0.4)
    pos, _ = sync_crosses(scan, g, F, lv, OPTS)
    step = np.diff(pos, axis=0)
    assert np.allclose(np.hypot(step[..., 0], step[..., 1]), 72, atol=0.6)
