# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import time

import numpy as np
import pytest

from optar.decoder.dirt import isolate_page, remove_border_dirt
from optar.decoder.geometry import compute_geometry, find_corners
from optar.decoder.levels import analyze_levels
from optar.decoder.options import DecodeOptions
from optar.encoder import encode
from optar.errors import DecodeError
from optar.format import PageFormat
from optar.layout import channel_xy
from tests.helpers import fake_scan, reference_remove_border_dirt, save_scan, seeded_bytes

F = PageFormat(65, 93)
OPTS = DecodeOptions()


@pytest.fixture(scope="module")
def page():
    return next(encode(seeded_bytes(5, 20000), F)).pixels


def test_options_defaults():
    o = DecodeOptions()
    assert (o.unsharp_mask, o.unsharp_dist, o.sync_white_cut, o.white_cut) == (7.0, 1.0, 0.10, 0.06)
    assert (o.minmax_filter, o.pixel_blur, o.cross_trim) == (0.5, 0.25, 0.75)


def test_levels_on_black_and_white_image(page):
    lv = analyze_levels(fake_scan(page), OPTS)
    assert 0 < lv.cut < lv.fill_cut < 255
    assert lv.fill_cut in (127, 128)
    # Pure 0/255 image: black=0, white=255, cut=floor(25.5+0.5), fill=floor(127.5+0.5).
    assert (lv.cut, lv.fill_cut) == (26, 128)


def test_levels_average_rounds():
    img = np.array([[0, 0, 255]], np.uint8)
    assert analyze_levels(img, OPTS).average == 85
    img = np.array([[0, 1]], np.uint8)
    assert analyze_levels(img, OPTS).average == 1  # (1 + 1) // 2


def test_levels_grey_image_float32_sums():
    rng = np.random.default_rng(1)
    img = np.clip(rng.normal(180, 40, (200, 300)), 0, 255).astype(np.uint8)
    img[50:120, 60:200] = np.clip(rng.normal(40, 15, (70, 140)), 0, 255).astype(np.uint8)
    lv = analyze_levels(img, OPTS)
    assert lv == _reference_levels(img, OPTS)


@pytest.mark.parametrize("value", [0, 255, 100])
def test_levels_one_sided_image_is_quiet(value, recwarn):
    lv = analyze_levels(np.full((20, 30), value, np.uint8), OPTS)
    assert (lv.average, lv.cut, lv.fill_cut) == (value, 0, 0)
    assert len(recwarn) == 0


def _reference_levels(img, opts):
    """Literal float32 port of calc_histogram / analyze_cutlevel."""
    from optar.decoder.levels import Levels

    f32 = np.float32
    hist = [int(v) for v in np.bincount(img.ravel(), minlength=256)]
    n = img.size
    avg = (sum(i * h for i, h in enumerate(hist)) + (n >> 1)) // n
    cut = fill = avg
    swc = f32(opts.sync_white_cut)
    for _ in range(32):
        last = cut
        wr = br = f32(0)
        bp = wp = 0
        for i in range(cut):
            br = f32(br + f32(f32(f32(hist[i]) * f32(cut - i)) * f32(cut - i)))
            bp += hist[i]
        for i in range(cut + 1, 256):
            wr = f32(wr + f32(f32(f32(hist[i]) * f32(i - cut)) * f32(i - cut)))
            wp += hist[i]
        wr = f32(np.sqrt(np.float64(f32(wr / f32(wp)))))
        br = f32(np.sqrt(np.float64(f32(br / f32(bp)))))
        white = f32(f32(cut) + wr)
        black = f32(f32(cut) - br)
        cut = int(np.floor(float(f32(f32(white * swc) + f32(black * f32(f32(1) - swc)))) + 0.5))
        fill = int(np.floor(float(white) * 0.5 + float(black) * 0.5 + 0.5))
        if cut == last:
            break
    return Levels(average=avg, cut=cut, fill_cut=fill)


def test_corners_scale_3_with_margin(page):
    scan = fake_scan(page, scale=3, margin=60)
    c = find_corners(scan, analyze_levels(scan, OPTS).cut)
    assert c.dtype == np.int64
    assert c.tolist() == [
        [60, 60],
        [60 + 1546 * 3, 60],
        [60, 60 + 2242 * 3],
        [60 + 1546 * 3, 60 + 2242 * 3],
    ]
    g = compute_geometry(c, F, OPTS)
    assert g.hpixel == pytest.approx(3.0) and g.vpixel == pytest.approx(3.0)
    assert g.ph == pytest.approx((1, 0)) and g.pv == pytest.approx((0, 1))
    assert (g.chalf, g.chalf_fine) == (4, 6)


def test_blank_image_raises():
    with pytest.raises(DecodeError, match="upper left corner"):
        find_corners(np.full((400, 300), 255, np.uint8), 128)


def test_landscape_image_cannot_find_upper_right():
    # diag_scan's bound xbegin < MIN(width, height): scans starting at
    # x = width-1 never run when width > height.
    img = np.full((30, 40), 255, np.uint8)
    img[10:20, 10:30] = 0
    with pytest.raises(DecodeError, match="upper right corner"):
        find_corners(img, 128)


def _diag_scan_c(img, cut, xin, yin, dx, dy):
    h, w = img.shape
    xbegin, length = xin, 1
    while 0 <= xbegin < min(w, h):
        x, y = xbegin, yin
        for _ in range(length):
            if 0 <= x < w and 0 <= y < h and img[y, x] < cut:
                return x, y
            x -= dx
            y += dy
        xbegin += dx
        length += 1
    return None


@pytest.mark.parametrize("seed", range(12))
def test_corners_match_literal_diag_scan(seed):
    rng = np.random.default_rng(seed)
    h, w = int(rng.integers(5, 90)), int(rng.integers(5, 90))
    h = max(h, w)  # portrait or square so every scan runs
    img = np.where(rng.random((h, w)) < rng.uniform(0.001, 0.05), 0, 255).astype(np.uint8)
    img[rng.integers(0, h), rng.integers(0, w)] = 0
    found = [
        _diag_scan_c(img, 128, 0, 0, 1, 1),
        _diag_scan_c(img, 128, w - 1, 0, -1, 1),
        _diag_scan_c(img, 128, 0, h - 1, 1, -1),
        _diag_scan_c(img, 128, w - 1, h - 1, -1, -1),
    ]
    if any(f is None for f in found):
        with pytest.raises(DecodeError):
            find_corners(img, 128)
        return
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = found
    expect = [[x0, y0], [x1 + 1, y1], [x2, y2 + 1], [x3 + 1, y3 + 1]]
    assert find_corners(img, 128).tolist() == expect


def test_geometry_hpixel_quirk():
    c = np.array([[10, 12], [110, 14], [14, 212], [116, 210]])
    g = compute_geometry(c, F, OPTS)
    assert g.hpixel == (110 + 116 - 10 - 10) / 2.0 / F.width
    assert g.vpixel == (212 + 210 - 12 - 14) / 2.0 / F.height
    hx, hy = (110 + 116 - 10 - 14) / 2, (14 + 210 - 12 - 212) / 2
    n = (hx * hx + hy * hy) ** 0.5
    assert g.ph == (hx / n, hy / n)
    assert g.corners == ((10, 12), (110, 14), (14, 212), (116, 210))


def test_dirt_in_margin_removed_page_untouched(page):
    clean = fake_scan(page, margin=60)
    dirty = fake_scan(page, margin=60, specks=25, seed=3)
    assert (clean != dirty).any()
    assert np.array_equal(remove_border_dirt(dirty, 128), clean)


def test_dirt_removal_matches_reference_flood_fill():
    rng = np.random.default_rng(0)
    img = np.where(rng.random((60, 70)) < 0.45, 0, 255).astype(np.uint8)
    img[20:40, 20:50] = 0
    assert np.array_equal(remove_border_dirt(img, 128), reference_remove_border_dirt(img, 128))


@pytest.mark.parametrize("seed", range(20))
def test_dirt_removal_random_images_match_reference(seed):
    rng = np.random.default_rng(100 + seed)
    h, w = int(rng.integers(1, 50)), int(rng.integers(1, 50))
    img = rng.integers(0, 256, (h, w)).astype(np.uint8)
    cut = int(rng.integers(1, 256))
    out = remove_border_dirt(img, cut)
    assert out is not img
    assert np.array_equal(out, reference_remove_border_dirt(img, cut))


@pytest.mark.parametrize("density", [0.3, 0.38, 0.42, 0.5, 0.6])
def test_dirt_removal_binary_noise_matches_reference(density):
    rng = np.random.default_rng(int(density * 100))
    img = np.where(rng.random((80, 64)) < density, 0, 255).astype(np.uint8)
    out = remove_border_dirt(img, 128)
    assert np.array_equal(out, reference_remove_border_dirt(img, 128))


def _spiral(n):
    img = np.full((n, n), 255, np.uint8)
    lo, hi, k = 1, n - 2, 0
    while lo < hi:
        img[lo, lo:hi + 1] = 0
        img[lo:hi + 1, hi] = 0
        img[hi, lo:hi + 1] = 0
        img[lo + 2:hi + 1, lo] = 0
        img[lo + 2, lo:lo + 2] = 0 if k % 2 else 255
        lo, hi, k = lo + 2, hi - 2, k + 1
    return img


@pytest.mark.parametrize("n", [21, 40, 41])
def test_dirt_removal_spiral_and_enclosures(n):
    img = _spiral(n)
    img[3:6, 3:6] = 255  # enclosed white pockets
    img[0, n // 3] = 0  # dirt touching the edge
    img[n - 1, :3] = 0
    assert np.array_equal(remove_border_dirt(img, 128), reference_remove_border_dirt(img, 128))
    inv = 255 - img
    assert np.array_equal(remove_border_dirt(inv, 128), reference_remove_border_dirt(inv, 128))


def test_dirt_removal_black_seeds_and_white_centre():
    img = np.full((31, 41), 255, np.uint8)
    img[0, :] = 0
    img[:, 0] = 0
    img[10:20, 10:30] = 0
    img[15, 20] = 255  # centre in a black frame, unconnected to the border
    assert np.array_equal(remove_border_dirt(img, 128), reference_remove_border_dirt(img, 128))


def test_fake_scan_basics(page):
    s = fake_scan(page, scale=2, margin=10)
    assert s.dtype == np.uint8 and s.shape == (2242 * 2 + 20, 1546 * 2 + 20)
    assert (s[:10] == 255).all() and (s[:, -10:] == 255).all()
    assert np.array_equal(s[10:-10, 10:-10][::2, ::2], page)
    r = fake_scan(page, scale=1, margin=8, rotate=1.0, blur=1.0, noise=5.0, seed=4)
    assert r.dtype == np.uint8 and r.ndim == 2 and r.shape[0] > 2242 + 16
    assert np.array_equal(r, fake_scan(page, scale=1, margin=8, rotate=1.0, blur=1.0, noise=5.0,
                                       seed=4))


def test_fake_scan_flips_and_specks(page):
    clean = fake_scan(page, scale=2, margin=40)
    with pytest.raises(ValueError):
        fake_scan(page, scale=2, margin=40, flips=3)
    f = fake_scan(page, scale=2, margin=40, flips=7, seed=1, fmt=F)
    diff = np.argwhere(f != clean)
    assert len(diff) == 7 * 4
    cells = {((y - 40) // 2, (x - 40) // 2) for y, x in diff}
    xs, ys = channel_xy(F)
    bits = set(zip((ys + F.border).tolist(), (xs + F.border).tolist(), strict=True))
    assert len(cells) == 7 and cells <= bits
    s = fake_scan(page, scale=2, margin=40, specks=10, seed=2)
    d = s != clean
    assert d.sum() == 10 * 16
    ph, pw = page.shape[0] * 2, page.shape[1] * 2
    ys, xs = np.nonzero(d)
    assert (ys >= 8).all() and (xs >= 8).all()
    assert (ys < s.shape[0] - 8).all() and (xs < s.shape[1] - 8).all()
    inside = (ys >= 40 - 8) & (ys < 40 + ph + 8) & (xs >= 40 - 8) & (xs < 40 + pw + 8)
    assert not inside.any()


def test_save_scan_roundtrip(tmp_path):
    from PIL import Image

    a = np.arange(256, dtype=np.uint8).reshape(16, 16)
    save_scan(tmp_path / "s.png", a)
    im = Image.open(tmp_path / "s.png")
    assert im.mode == "L" and np.array_equal(np.asarray(im), a)


@pytest.mark.slow
def test_full_a4_scale_3_prepare_is_fast(page):
    scan = fake_scan(page, scale=3, margin=60)
    t0 = time.perf_counter()
    lv = analyze_levels(scan, OPTS)
    cleaned = remove_border_dirt(scan, lv.fill_cut)
    find_corners(cleaned, lv.cut)
    elapsed = time.perf_counter() - t0
    assert np.array_equal(cleaned, scan)
    assert elapsed < 10, elapsed


def _framed_page(gap: bool) -> np.ndarray:
    """A page of 2-pixel dots in a black frame, in a white margin, with white
    rows across it as the padding of a part-filled document prints them."""
    rng = np.random.default_rng(5)
    dots = np.where(rng.random((90, 70)) < 0.5, 0, 255).astype(np.uint8)
    dots[::9] = 255
    img = np.full((240, 200), 255, np.uint8)
    img[26:214, 26:174] = 0  # the frame, 4 pixels thick
    img[30:210, 30:170] = np.kron(dots, np.ones((2, 2), np.uint8))
    if gap:
        img[26:214, 170:174] = 255  # the printer clipped the right edge
    return img


def test_isolate_page_is_remove_border_dirt_for_a_whole_frame():
    img = _framed_page(gap=False)
    img[5:8, 5:8] = 0  # dirt in the margin
    assert np.array_equal(isolate_page(img, 128), remove_border_dirt(img, 128))
    assert isolate_page(img, 128)[6, 6] == 255


def test_isolate_page_keeps_a_page_whose_frame_has_a_gap():
    img = _framed_page(gap=True)
    # As in C, the white outside runs into the page and most of it is wiped.
    assert (remove_border_dirt(img, 128) != img).mean() > 0.05
    img[5:8, 5:8] = 0  # dirt in the margin
    out = isolate_page(img, 128)
    assert out[6, 6] == 255
    assert np.array_equal(out[26:214, 26:174], img[26:214, 26:174])
    corners = find_corners(out, 128)
    assert corners.tolist() == [[26, 26], [170, 26], [26, 214], [170, 214]]
