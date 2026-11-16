# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The scan simulator in tests/helpers.py."""

import numpy as np

from optar import decode_page, encode
from optar.format import get_layout
from tests.helpers import seeded_bytes, simulate_scan


def _page(paper, dots="standard"):
    layout = get_layout(paper, dots)
    data = seeded_bytes(7, layout.fmt.net_bits // 8 + 16)
    page = next(iter(encode(data, layout.fmt)))
    return layout, data, page.pixels


def _check(layout, data, scan):
    r = decode_page(scan, layout.fmt)
    assert r.stats.uncorrectable == 0
    want = np.unpackbits(np.frombuffer(data, np.uint8))[: layout.fmt.net_bits]
    assert np.array_equal(r.bits, want)


def test_standard_a4_at_600_dpi_decodes():
    layout, data, px = _page("a4")
    _check(layout, data, simulate_scan(px, layout, 600))


def test_large_a4_at_300_dpi_decodes():
    layout, data, px = _page("a4", "large")
    _check(layout, data, simulate_scan(px, layout, 300))


def test_output_size():
    layout, data, px = _page("a4", "large")
    dpi = 300
    scan = simulate_scan(px, layout, dpi)
    d = layout.dots.printer_dots
    assert scan.ndim == 2 and scan.dtype == np.uint8
    for got, n in ((scan.shape[0], px.shape[0]), (scan.shape[1], px.shape[1])):
        want = (n * d / 600 + 0.4) * dpi
        assert abs(got - want) <= 0.02 * want


def test_seed_determinism():
    layout, data, px = _page("a4", "large")
    px = px[:200, :200]
    a = simulate_scan(px, layout, 300, seed=3)
    assert np.array_equal(a, simulate_scan(px, layout, 300, seed=3))
    assert not np.array_equal(a, simulate_scan(px, layout, 300, seed=4))


def test_quarter_turns_are_undone_by_rot90():
    layout, data, px = _page("a4", "large")
    scan = simulate_scan(px, layout, 300, quarter_turns=1)
    _check(layout, data, np.rot90(scan, 1))


def test_large_a4_at_300_dpi_survives_blur_2():
    # Standard pages stop decoding near blur 2.0; Large pages still decode.
    layout, data, px = _page("a4", "large")
    _check(layout, data, simulate_scan(px, layout, 300, blur=2.0))
