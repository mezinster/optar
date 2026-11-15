# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Whole-page decoding: round trips, degraded scans and non-pages."""

import numpy as np
import pytest

from optar import PAPERS, PageFormat, PageStats, decode, decode_page, encode
from optar.errors import DecodeError
from tests.helpers import DEGRADED, fake_scan, seeded_bytes

A4 = PageFormat.for_paper(PAPERS["a4"])
DEGRADED_DATA = seeded_bytes(11, 150000)


@pytest.fixture(scope="module")
def degraded_page():
    return next(encode(DEGRADED_DATA, A4)).pixels


@pytest.mark.parametrize("paper", ["a4", "letter"])
@pytest.mark.parametrize("size", [0, 1, 4321])
def test_round_trip_small(paper, size):
    fmt = PageFormat.for_paper(PAPERS[paper])
    data = seeded_bytes(size, size)
    res = decode((fake_scan(p.pixels, scale=1, margin=40) for p in encode(data, fmt)), fmt)
    assert res.data[:size] == data and not any(res.data[size:]) and res.uncorrectable == 0
    assert len(res.data) == fmt.net_bits // 8


def test_round_trip_two_pages_reports_progress():
    data = seeded_bytes(2, A4.net_bits // 8 + 999)
    seen = []
    res = decode(
        (fake_scan(p.pixels, scale=1) for p in encode(data, A4)),
        A4,
        progress=lambda n, st: seen.append(n),
    )
    assert res.data[: len(data)] == data and seen == [1, 2] and len(res.pages) == 2


@pytest.mark.parametrize("order", [2, 3, 4, 5])
def test_round_trip_hamming_two_pages(order):
    fmt = PageFormat(65, 93, fec_order=order)
    data = seeded_bytes(order, fmt.net_bits // 8 + 2000)
    res = decode((fake_scan(p.pixels, scale=1) for p in encode(data, fmt)), fmt)
    assert res.data[: len(data)] == data
    # Orders 2, 4 and 5 have net_bits not a multiple of 8: one bit stream over
    # the pages, and only the trailing partial byte is dropped.
    assert len(res.data) == 2 * fmt.net_bits // 8 and res.uncorrectable == 0


@pytest.mark.parametrize("name", list(DEGRADED))
def test_degraded_round_trip(degraded_page, name):
    r = decode_page(fake_scan(degraded_page, seed=1, fmt=A4, **DEGRADED[name]), A4)
    assert r.stats.uncorrectable == 0 and r.stats.max_corrected <= 2
    assert np.packbits(r.bits)[: len(DEGRADED_DATA)].tobytes() == DEGRADED_DATA


@pytest.mark.parametrize(
    "img",
    [
        np.zeros((0, 0), np.uint8),
        np.full((300, 200), 255, np.uint8),
        np.zeros((50, 50), np.uint8),
    ],
)
def test_non_pages_raise(img):
    with pytest.raises(DecodeError):
        decode_page(img, A4)


def test_wrong_paper_does_not_crash():
    letter = PageFormat.for_paper(PAPERS["letter"])
    page = next(encode(seeded_bytes(1, 50000), A4)).pixels
    try:
        r = decode_page(fake_scan(page, scale=1), letter)
    except DecodeError:
        return
    assert r.stats.uncorrectable > 0


def test_debug_image_only_on_request():
    scan = fake_scan(next(encode(b"abc", A4)).pixels, scale=1)
    assert decode_page(scan, A4).debug_image is None
    assert decode_page(scan, A4, debug=True).debug_image.shape == scan.shape


@pytest.mark.parametrize(
    "img",
    [np.zeros((2300, 1600, 3), np.uint8), np.zeros((2300, 1600), np.float32),
     np.zeros((2242, 1545), np.uint8)],
    ids=["rgb", "float", "one-column-short"],
)
def test_bad_arrays_raise(img):
    with pytest.raises(DecodeError):
        decode_page(img, A4)


def test_blank_full_size_image_raises():
    with pytest.raises(DecodeError, match="corner"):
        decode_page(np.full((A4.height, A4.width), 255, np.uint8), A4)


def test_tiny_page_in_large_image_raises():
    img = np.full((A4.height, A4.width), 255, np.uint8)
    img[800:1400, 500:1000] = 0  # covers the centre; under 2/3 scan pixel per page pixel
    with pytest.raises(DecodeError, match="too small"):  # chalf == 0
        decode_page(img, A4)


def test_page_stats_max_corrected():
    assert PageStats(10, (10, 0, 0, 0), 0).max_corrected == 0
    assert PageStats(10, (7, 2, 1, 0), 0).max_corrected == 2
    assert PageStats(10, (0, 0, 0, 0), 10).max_corrected == 0


def test_decode_no_pages():
    res = decode(iter(()), A4)
    assert res.data == b"" and res.pages == () and res.uncorrectable == 0
