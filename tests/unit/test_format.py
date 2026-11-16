# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
from fractions import Fraction

import pytest

from optar.errors import FormatError
from optar.format import (
    DOT_SIZES,
    LAYOUTS,
    MIN_MARGIN_PT,
    PAPERS,
    PARITY,
    PageFormat,
    get_layout,
    get_paper,
    layout_for_format,
)

A4 = "0-65-93-24-3-1-2-24"


def test_a4_derived_sizes():
    f = PageFormat.for_paper(PAPERS["a4"])
    assert f.to_string() == A4
    assert (f.width, f.height) == (1546, 2242)
    assert (f.total_bits, f.fec_syms, f.net_bits) == (3196368, 133182, 1598184)
    assert (f.fec_largebits, f.fec_smallbits) == (24, 12)


def test_letter_derived_sizes():
    f = PageFormat.for_paper(get_paper("Letter"))
    assert f.to_string() == "0-67-87-24-3-1-2-24"
    assert (f.width, f.height, f.total_bits, f.net_bits) == (1594, 2098, 3081456, 1540728)


@pytest.mark.parametrize("order,net", [(2, 799092), (3, 1598184), (4, 2197503), (5, 2597036)])
def test_hamming_net_bits(order, net):
    assert PageFormat(65, 93, fec_order=order).net_bits == net


def test_parse_round_trip_and_hashable():
    f = PageFormat.parse(A4)
    assert f == PageFormat.for_paper(PAPERS["a4"]) and hash(f) == hash(PageFormat.parse(A4))
    assert PageFormat.parse(f.to_string()) == f


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "0-65-93",
        "1-65-93-24-3-1-2-24",
        "0-65-93-24-3-6-2-24",
        "0-1-93-24-3-1-2-24",
        "0-65-93-6-3-1-2-24",
        "0-a-93-24-3-1-2-24",
        "0-65-93-24-3-1-2-24-1",
        "0-65-93-24-3-1-2--24",
        "0-65-93-24-3-1-2-+24",
        " 0-65-93-24-3-1-2-24",
    ],
)
def test_bad_format_rejected(bad):
    with pytest.raises(FormatError):
        PageFormat.parse(bad)


def test_paper_placement_and_fit():
    a4 = PAPERS["a4"]
    placement = (a4.width_pt, a4.height_pt, a4.offset_x_pt, a4.offset_y_pt)
    assert placement == (595.28, 841.89, 19.20, 17.40)
    assert PageFormat.for_paper(a4).fits(a4)
    assert PageFormat.for_paper(PAPERS["letter"]).fits(PAPERS["letter"])
    assert not PageFormat(80, 93).fits(a4)
    with pytest.raises(FormatError):
        get_paper("legal")


CLIPPED = "0-65-95-24-3-1-2-24"  # 0.09 pt top margin on A4


def test_fits_requires_minimum_margins():
    a4 = PAPERS["a4"]
    assert not PageFormat.parse(CLIPPED).fits(a4)
    for name, paper in PAPERS.items():
        fmt = PageFormat.for_paper(paper)
        margins = paper.margins_for(fmt.width, fmt.height)
        assert min(margins) >= MIN_MARGIN_PT, name
        assert paper.fits_image(fmt.width, fmt.height)


def test_margins_for_a4_preset():
    a4 = PAPERS["a4"]
    fmt = PageFormat.for_paper(a4)
    left, bottom, right, top = a4.margins_for(fmt.width, fmt.height)
    assert (left, bottom) == (19.20, 17.40)
    assert right == pytest.approx(595.28 - 19.20 - 556.56)  # 19.52
    assert top == pytest.approx(841.89 - 17.40 - 807.12)  # 17.37
    clipped = PageFormat.parse(CLIPPED)
    assert a4.margins_for(clipped.width, clipped.height)[3] == pytest.approx(0.09, abs=1e-6)


def _on_600_dpi_grid(points: float) -> bool:
    dots = points * 600 / 72
    return abs(dots - round(dots)) < 1e-9


@pytest.mark.parametrize("name", list(PAPERS))
def test_placement_is_on_the_600_dpi_device_grid(name):
    # Each data pixel prints as exactly 3 x 3 dots only if the image edges
    # fall on device-pixel boundaries at 600 dpi.
    paper = PAPERS[name]
    fmt = PageFormat.for_paper(paper)
    assert _on_600_dpi_grid(paper.offset_x_pt) and _on_600_dpi_grid(paper.offset_y_pt)
    assert _on_600_dpi_grid(fmt.width * 72 / 200) and _on_600_dpi_grid(fmt.height * 72 / 200)


# ---- dot sizes and layouts ----

REFERENCE = [
    ("a4", "standard", "0-65-93-24-3-1-2-24", 199_773),
    ("a4", "medium", "0-50-70-24-3-1-2-24", 114_904),
    ("a4", "big", "0-40-56-24-3-1-2-24", 73_027),
    ("a4", "large", "0-33-46-24-3-1-2-24", 49_119),
    ("a4", "xlarge", "0-22-31-24-3-1-2-24", 21_606),
    ("letter", "standard", "0-67-87-24-3-1-2-24", 192_591),
    ("letter", "medium", "0-51-66-24-3-1-2-24", 110_463),
    ("letter", "big", "0-41-52-24-3-1-2-24", 69_463),
    ("letter", "large", "0-34-44-24-3-1-2-24", 48_403),
    ("letter", "xlarge", "0-23-29-24-3-1-2-24", 21_127),
]


def _layout_id(layout):
    return f"{layout.paper.name}-{layout.dots.name}"


@pytest.mark.parametrize(("paper", "dots", "fmt", "page_bytes"), REFERENCE)
def test_layout_reference_values(paper, dots, fmt, page_bytes):
    layout = get_layout(paper, dots)
    assert layout.fmt.to_string() == fmt
    assert layout.fmt.net_bits // 8 == page_bytes


@pytest.mark.parametrize("name", ["a4", "letter"])
def test_standard_layout_is_the_paper(name):
    layout = get_layout(name)
    paper = get_paper(name)
    assert layout.fmt == PageFormat.for_paper(paper)
    assert (layout.offset_x_pt, layout.offset_y_pt) == (paper.offset_x_pt, paper.offset_y_pt)


def test_dot_scales_and_resolutions():
    assert list(DOT_SIZES) == ["standard", "medium", "big", "large", "xlarge"]
    assert [d.printer_dots for d in DOT_SIZES.values()] == [3, 4, 5, 6, 9]
    assert [d.scale for d in DOT_SIZES.values()] == [1, Fraction(4, 3), Fraction(5, 3), 2, 3]
    assert [get_layout("a4", d).scan_dpi for d in DOT_SIZES] == [600, 450, 360, 300, 200]
    assert [get_layout("a4", d).pixels_per_inch for d in DOT_SIZES] == [200, 150, 120, 100, Fraction(200, 3)]
    assert PARITY == {"none": 0, "standard": 32, "high": 64}


@pytest.mark.parametrize("layout", LAYOUTS.values(), ids=_layout_id)
def test_layout_margins(layout):
    left, bottom, right, top = layout.margins()
    assert min(left, bottom, right, top) >= MIN_MARGIN_PT
    for offset in (layout.offset_x_pt, layout.offset_y_pt):
        dots = offset * 600 / 72
        assert abs(dots - round(dots)) < 1e-9
    if layout.dots.printer_dots > 3:
        assert abs(left - right) < 0.25
        assert abs(bottom - top) < 0.25


@pytest.mark.parametrize(
    "layout", [lay for lay in LAYOUTS.values() if lay.dots.printer_dots > 3], ids=_layout_id
)
def test_larger_grid_is_the_largest_that_fits(layout):
    unit = 72 * layout.dots.printer_dots / 600
    for dx, dy in ((1, 0), (0, 1)):
        bigger = PageFormat(xcrosses=layout.xcrosses + dx, ycrosses=layout.ycrosses + dy)
        free_x = layout.paper.width_pt - bigger.width * unit
        free_y = layout.paper.height_pt - bigger.height * unit
        assert min(free_x, free_y) / 2 < MIN_MARGIN_PT


def test_layout_for_format():
    assert layout_for_format("0-33-46-24-3-1-2-24").dots.name == "large"
    assert layout_for_format("0-65-93-24-3-1-2-24") is get_layout("a4")
    assert layout_for_format("0-1-2-3-4-1-2-24") is None


def test_layout_format_strings_are_distinct():
    assert len({lay.fmt.to_string() for lay in LAYOUTS.values()}) == 10


def test_get_layout_unknown_names():
    with pytest.raises(FormatError):
        get_layout("a4", "huge")
    with pytest.raises(FormatError):
        get_layout("a3")
