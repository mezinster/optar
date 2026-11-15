# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Speed targets for one full A4 page (run with -m slow)."""

import time

import pytest

from optar import PAPERS, PageFormat, decode_page, encode
from tests.helpers import fake_scan, seeded_bytes

pytestmark = pytest.mark.slow

A4 = PageFormat.for_paper(PAPERS["a4"])
DATA = seeded_bytes(4, A4.net_bits // 8)


def test_encode_full_page_under_5_seconds():
    t = time.perf_counter()
    pages = list(encode(DATA, A4))
    elapsed = time.perf_counter() - t
    assert len(pages) == 1
    assert elapsed < 5, f"encoding one page took {elapsed:.1f} s"


def test_decode_full_page_under_60_seconds():
    scan = fake_scan(next(encode(DATA, A4)).pixels, scale=3, margin=60)
    t = time.perf_counter()
    result = decode_page(scan, A4)
    elapsed = time.perf_counter() - t
    assert result.stats.uncorrectable == 0
    assert elapsed < 60, f"decoding one page took {elapsed:.1f} s"
