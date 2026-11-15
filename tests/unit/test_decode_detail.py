# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""locate_page / decode_located, corrected-bit detail and page_to_scan."""

import numpy as np
import pytest

from optar import PageFormat, decode_page, encode
from optar.decoder import PageGrid, decode_located, locate_page, page_to_scan
from optar.decoder.sample import _bit_coord
from optar.errors import DecodeError
from optar.layout import channel_xy
from tests.helpers import fake_scan, seeded_bytes

F = PageFormat(65, 93)
H = PageFormat(65, 93, fec_order=3)


@pytest.fixture(scope="module")
def page():
    return next(encode(seeded_bytes(21, 150000), F)).pixels


@pytest.fixture(scope="module")
def hamming_page():
    return next(encode(seeded_bytes(22, 150000), H)).pixels


def flipped_scan(page, positions, fmt=F):
    x, y = channel_xy(fmt)
    p = page.copy()
    p[y[positions] + fmt.border, x[positions] + fmt.border] ^= 255
    return fake_scan(p, scale=1, margin=40)


def test_detail_reports_exactly_the_flipped_bits(page):
    rng = np.random.default_rng(5)
    pos = np.sort(rng.choice(F.used_bits, 150, replace=False))
    r = decode_page(flipped_scan(page, pos), F, detail=True)
    assert r.stats.uncorrectable == 0
    assert np.array_equal(r.corrected_bits, pos) and r.corrected_bits.dtype == np.int64
    assert len(r.lost_symbols) == 0 and r.lost_symbols.dtype == np.int64
    assert isinstance(r.grid, PageGrid)


def test_corrected_count_matches_the_histogram(page):
    rng = np.random.default_rng(6)
    # Up to three wrong bits in each of 200 symbols.
    syms = rng.choice(F.fec_syms, 200, replace=False)
    pos = np.concatenate([
        s + rng.choice(F.fec_largebits, rng.integers(1, 4), replace=False) * F.fec_syms
        for s in syms
    ])
    r = decode_page(flipped_scan(page, pos), F, detail=True)
    assert r.stats.uncorrectable == 0
    assert len(r.corrected_bits) == sum(i * n for i, n in enumerate(r.stats.error_histogram))
    assert np.array_equal(r.corrected_bits, np.sort(pos))


def test_detail_reports_lost_symbols(page):
    # Four wrong bits in one Golay codeword (minimum distance 8): every other
    # codeword is at least 4 away, so the decoder never corrects, only detects.
    s = 777
    pos = s + np.arange(4) * F.fec_syms
    r = decode_page(flipped_scan(page, pos), F, detail=True)
    assert r.stats.uncorrectable == 1
    assert r.lost_symbols.tolist() == [s] and len(r.corrected_bits) == 0


def test_hamming_single_flips_are_reported(hamming_page):
    rng = np.random.default_rng(7)
    syms = np.sort(rng.choice(H.fec_syms, 100, replace=False))
    # One wrong bit per symbol, including the overall parity bit (the least
    # significant, b = fec_largebits - 1) which Hamming corrects as "parity only".
    bits = rng.integers(0, H.fec_largebits, syms.size)
    bits[:5] = H.fec_largebits - 1
    pos = np.sort(syms + bits * H.fec_syms)
    r = decode_page(flipped_scan(hamming_page, pos, H), H, detail=True)
    assert r.stats.uncorrectable == 0 and r.stats.error_histogram[1] == 100
    assert np.array_equal(r.corrected_bits, pos)


def test_default_result_is_unchanged(page):
    scan = fake_scan(page, scale=1, margin=40)
    a, b = decode_page(scan, F), decode_page(scan, F, detail=True)
    assert a.corrected_bits is None and a.lost_symbols is None and a.grid is None
    assert np.array_equal(a.bits, b.bits) and a.stats == b.stats


def test_locate_then_decode_equals_decode_page(page):
    scan = fake_scan(page, scale=3, margin=60)
    grid = locate_page(scan, F)
    assert grid.fmt == F and grid.cleaned.shape == scan.shape
    assert grid.positions.shape == (F.xcrosses, F.ycrosses, 2)
    a, b = decode_located(grid, debug=True), decode_page(scan, F, debug=True)
    assert np.array_equal(a.bits, b.bits) and a.stats == b.stats
    assert np.array_equal(a.debug_image, b.debug_image)


def test_locate_page_raises_decode_errors():
    with pytest.raises(DecodeError):
        locate_page(np.full((10, 10), 255, np.uint8), F)
    with pytest.raises(DecodeError):
        locate_page(np.full((F.height + 50, F.width + 50), 255, np.uint8), F)


def test_page_to_scan_maps_data_pixels(page):
    grid = locate_page(fake_scan(page, scale=3, margin=60), F)
    sx, sy = page_to_scan(grid, np.array([0, 10]), np.array([0, 20]))
    # page pixel (x, y) is at scan (60 + 3*(border + x) + 1, 60 + 3*(border + y) + 1)
    assert sx == pytest.approx([60 + 3 * 2 + 1, 60 + 3 * 12 + 1], abs=0.3)
    assert sy == pytest.approx([60 + 3 * 2 + 1, 60 + 3 * 22 + 1], abs=0.3)


def test_page_to_scan_matches_the_sampler(page):
    grid = locate_page(fake_scan(page, scale=3, margin=60), F)
    x, y = channel_xy(F)
    x, y = x[::97].astype(np.int64), y[::97].astype(np.int64)
    xd, yd, _ = _bit_coord(x, y, grid.positions, grid.cutlevels.astype(np.float32), F)
    sx, sy = page_to_scan(grid, x, y)
    assert np.array_equal(sx, xd) and np.array_equal(sy, yd)


def test_page_to_scan_shapes(page):
    grid = locate_page(fake_scan(page, scale=3, margin=60), F)
    sx, sy = page_to_scan(grid, 10, 20)
    assert sx.shape == () and sy.shape == ()
    gx, gy = np.meshgrid(np.arange(4), np.arange(3))
    sx, sy = page_to_scan(grid, gx, gy)
    assert sx.shape == (3, 4) and sy.shape == (3, 4)
    assert sx[1, 2] == pytest.approx(60 + 3 * (2 + 2) + 1, abs=0.3)
    # Fractional page coordinates interpolate between pixel centres.
    fx, _ = page_to_scan(grid, 10.5, 20)
    assert fx == pytest.approx(60 + 3 * 12.5 + 1, abs=0.3)


def test_page_to_scan_extrapolates_below_the_crosses(page):
    grid = locate_page(fake_scan(page, scale=3, margin=60), F)
    x = np.array([0, 100, F.data_width - 1])
    last = np.full(3, F.data_height - 1)
    _, sy_last = page_to_scan(grid, x, last)
    sx, sy = page_to_scan(grid, x, last + 11)  # page row data_height + 10
    assert sy - sy_last == pytest.approx(np.full(3, 3 * 11), abs=0.5)
    assert sy == pytest.approx(np.full(3, 60 + 3 * (F.border + F.data_height + 10) + 1), abs=0.5)
    assert sx == pytest.approx(60 + 3 * (F.border + x) + 1, abs=0.5)
