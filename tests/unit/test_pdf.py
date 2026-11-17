# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import numpy as np
import pytest

from optar.encoder import encode
from optar.errors import FormatError, OptarError
from optar.format import PAPERS, PageFormat, get_layout
from optar.pdf import write_pdf
from tests.helpers import parse_pdf, seeded_bytes


@pytest.mark.parametrize("name,cm", [
    ("a4", (556.56, 0, 0, 807.12, 19.20, 17.40)),
    ("letter", (573.84, 0, 0, 755.28, 19.08, 18.36)),
])
def test_pdf_page_geometry_and_pixels(tmp_path, name, cm):
    paper = PAPERS[name]
    fmt = PageFormat.for_paper(paper)
    pages = [p.pixels for p in encode(seeded_bytes(1, fmt.net_bits // 8 + 10), fmt)]
    assert write_pdf(tmp_path / "o.pdf", iter(pages), paper) == 2
    raw = (tmp_path / "o.pdf").read_bytes()
    assert raw.startswith(b"%PDF-1.") and raw.rstrip().endswith(b"%%EOF")
    assert b"DCTDecode" not in raw
    parsed = parse_pdf(tmp_path / "o.pdf")
    assert len(parsed) == 2
    for got, want in zip(parsed, pages, strict=True):
        assert got["mediabox"] == pytest.approx((0, 0, paper.width_pt, paper.height_pt), abs=0.01)
        assert got["cm"] == pytest.approx(cm, abs=0.01)
        assert (got["width"], got["height"], got["bits"]) == (fmt.width, fmt.height, 1)
        assert got["filter"] == "FlateDecode" and got["interpolate"] is False
        assert np.array_equal(got["pixels"], want)


def test_xref_offsets_point_at_objects(tmp_path):
    fmt = PageFormat.for_paper(PAPERS["a4"])
    write_pdf(tmp_path / "o.pdf", (p.pixels for p in encode(b"x", fmt)), PAPERS["a4"])
    raw = (tmp_path / "o.pdf").read_bytes()
    start = int(raw[raw.rindex(b"startxref") + 9:].split()[0])
    assert raw[start:start + 4] == b"xref"
    lines = raw[start:].split(b"\n")
    count = int(lines[1].split()[1])
    for n, line in enumerate(lines[3:2 + count], start=1):
        off = int(line[:10])
        assert raw[off:].startswith(b"%d 0 obj" % n)


def test_write_pdf_rejects_image_that_would_be_clipped(tmp_path):
    a4 = PAPERS["a4"]
    fmt = PageFormat.parse("0-65-95-24-3-1-2-24")
    page = np.full((fmt.height, fmt.width), 255, np.uint8)
    with pytest.raises(FormatError, match="margin"):
        write_pdf(tmp_path / "o.pdf", iter([page]), a4)
    assert not (tmp_path / "o.pdf").exists()


def test_write_pdf_rejects_zero_pages(tmp_path):
    with pytest.raises(OptarError, match="no pages"):
        write_pdf(tmp_path / "o.pdf", iter([]), PAPERS["a4"])
    assert not (tmp_path / "o.pdf").exists()


@pytest.mark.parametrize(
    "page,error",
    [
        (np.full((100, 100), 255, np.int64), TypeError),
        ([[255, 255], [255, 255]], TypeError),
        (np.full((10, 10, 3), 255, np.uint8), ValueError),
        (np.zeros((0, 10), np.uint8), ValueError),
    ],
)
def test_write_pdf_rejects_bad_pages(tmp_path, page, error):
    good = np.full((100, 100), 255, np.uint8)
    with pytest.raises(error):
        write_pdf(tmp_path / "first.pdf", iter([page]), PAPERS["a4"])
    assert not (tmp_path / "first.pdf").exists()
    with pytest.raises(error):
        write_pdf(tmp_path / "second.pdf", iter([good, page]), PAPERS["a4"])
    assert not (tmp_path / "second.pdf").exists()


@pytest.mark.parametrize("dots,printer_dots", [("large", 6), ("medium", 4)])
def test_pdf_places_page_at_its_layout(tmp_path, dots, printer_dots):
    layout = get_layout("a4", dots)
    fmt = layout.fmt
    page = np.full((fmt.height, fmt.width), 255, np.uint8)
    page[::7, ::5] = 0
    assert write_pdf(tmp_path / "o.pdf", iter([page]), layout) == 1
    (got,) = parse_pdf(tmp_path / "o.pdf")
    a4 = PAPERS["a4"]
    assert got["mediabox"] == pytest.approx((0, 0, a4.width_pt, a4.height_pt), abs=0.01)
    w = fmt.width * 72 * printer_dots / 600
    h = fmt.height * 72 * printer_dots / 600
    want = (w, 0, 0, h, layout.offset_x_pt, layout.offset_y_pt)
    assert got["cm"] == pytest.approx(want, abs=0.01)
    assert np.array_equal(got["pixels"], page)


def test_write_pdf_refuses_image_that_is_not_the_layout_page(tmp_path):
    layout = get_layout("a4", "large")
    page = np.full((layout.fmt.height, layout.fmt.width + 1), 255, np.uint8)
    with pytest.raises(FormatError, match="layout"):
        write_pdf(tmp_path / "o.pdf", iter([page]), layout)
    assert not (tmp_path / "o.pdf").exists()


@pytest.mark.parametrize("dots,printer_dots", [("large", 6), ("medium", 4), ("xlarge", 9)])
def test_pdf_prints_the_label_strip_over_the_label_band(tmp_path, dots, printer_dots):
    from optar.font import fine_label

    layout = get_layout("a4", dots)
    fmt = layout.fmt
    (page,) = encode(b"x", fmt, "name.bin")
    strip = fine_label(layout, 1, 1, "name.bin")
    assert write_pdf(tmp_path / "o.pdf", iter([(page.pixels, strip)]), layout) == 1
    (got,) = parse_pdf(tmp_path / "o.pdf")
    top = fmt.border + fmt.data_height
    band = (slice(top, top + fmt.text_height), slice(fmt.border, fmt.border + fmt.data_width))
    # The page's own label is printed black; everything else is as encoded.
    assert not got["pixels"][band].any()
    want = page.pixels.copy()
    want[band] = 0
    assert np.array_equal(got["pixels"], want)
    assert np.array_equal(got["band"], strip)
    # One strip pixel is a standard dot (1/200 inch), whatever the layout.
    w, _, _, h, x, y = got["band_cm"]
    assert (w, h) == pytest.approx((strip.shape[1] * 0.36, 24 * 0.36), abs=0.01)
    unit = 72 * printer_dots / 600
    assert x == pytest.approx(layout.offset_x_pt + fmt.border * unit, abs=0.01)
    bottom = layout.offset_y_pt + (fmt.height - top - fmt.text_height) * unit
    height = fmt.text_height * unit
    assert y == pytest.approx(bottom + (height - h) / 2, abs=0.01)
    # The strip lies inside the band.
    assert y >= bottom and y + h <= bottom + height + 0.01
    assert x + w <= layout.offset_x_pt + (fmt.border + fmt.data_width) * unit + 0.01


def test_pdf_without_a_strip_is_unchanged_by_a_none(tmp_path):
    layout = get_layout("a4", "large")
    (page,) = encode(b"x", layout.fmt, "n")
    write_pdf(tmp_path / "a.pdf", iter([page.pixels]), layout)
    write_pdf(tmp_path / "b.pdf", iter([(page.pixels, None)]), layout)
    assert (tmp_path / "a.pdf").read_bytes() == (tmp_path / "b.pdf").read_bytes()


def test_write_pdf_refuses_a_strip_it_cannot_place(tmp_path):
    layout = get_layout("a4", "large")
    (page,) = encode(b"x", layout.fmt, "n")
    too_tall = np.zeros((49, 10), np.uint8)
    too_wide = np.zeros((24, layout.fmt.data_width * 2 + 1), np.uint8)
    for strip in (too_tall, too_wide):
        with pytest.raises(FormatError):
            write_pdf(tmp_path / "o.pdf", iter([(page.pixels, strip)]), layout)
        assert not (tmp_path / "o.pdf").exists()
    (standard,) = encode(b"x", PageFormat(65, 93), "n")
    with pytest.raises(FormatError):
        write_pdf(tmp_path / "o.pdf", iter([(standard.pixels, too_wide)]), PAPERS["a4"])
    with pytest.raises(TypeError):
        write_pdf(tmp_path / "o.pdf", iter([(page.pixels, [[0]])]), layout)
