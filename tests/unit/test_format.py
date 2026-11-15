# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import pytest

from optar.errors import FormatError
from optar.format import MIN_MARGIN_PT, PAPERS, PageFormat, get_paper

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
    assert placement == (595.28, 841.89, 19.22, 17.44)
    assert PageFormat.for_paper(a4).fits(a4)
    assert PageFormat.for_paper(PAPERS["letter"]).fits(PAPERS["letter"])
    assert not PageFormat(80, 93).fits(a4)
    with pytest.raises(FormatError):
        get_paper("legal")


CLIPPED = "0-65-95-24-3-1-2-24"  # 0.05 pt top margin on A4


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
    assert (left, bottom) == (19.22, 17.44)
    assert right == pytest.approx(595.28 - 19.22 - 556.56)
    assert top == pytest.approx(841.89 - 17.44 - 807.12)
    clipped = PageFormat.parse(CLIPPED)
    assert a4.margins_for(clipped.width, clipped.height)[3] == pytest.approx(0.05, abs=1e-6)
