# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import numpy as np
import pytest

from optar.encoder import encode
from optar.errors import FormatError, OptarError
from optar.format import PAPERS, PageFormat
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
