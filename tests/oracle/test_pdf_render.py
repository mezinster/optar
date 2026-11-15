# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Render the PDF with Ghostscript at 600 dpi and check it against the encoder.

For every rendered page of both papers this proves, on the rendered PNG itself:
the image rectangle (bounding box of the black pixels) is exactly 3 x the page
size, sits exactly where the paper's x offset puts it and within 1 pixel of
where its y offset puts it, everything outside it is pure white, and its
content equals the encoder's page replicated exactly 3 x 3 (so scale, position,
orientation and absence of smoothing). It also checks that Ghostscript prints
nothing, that the page count and render size are right,
that the CLI decodes the render with 0 corrected and 0 uncorrectable symbols on
every page, and that the decoded bytes equal the input.
"""

import re
import subprocess

import numpy as np
import pytest
from PIL import Image

from optar.cli import main
from optar.encoder import encode
from optar.format import PAPERS, PIXELS_PER_INCH, PageFormat
from tests.helpers import seeded_bytes

pytestmark = pytest.mark.gs

SIZE = 250_000
DPI = 600
LABEL = "render-check"
RENDER_SIZES = {"a4": (4961, 7016), "letter": (5100, 6600)}


def check_render_page(render: np.ndarray, expected_page: np.ndarray, paper, fmt) -> None:
    """Assert placement, exact replication and white surround of one render."""
    factor = DPI // PIXELS_PER_INCH
    height, _ = render.shape
    assert set(np.unique(render)) <= {0, 255}

    dark = np.argwhere(render < 128)
    top, left = dark.min(axis=0)
    bottom, right = dark.max(axis=0) + 1
    assert (right - left, bottom - top) == (factor * fmt.width, factor * fmt.height)

    image_height_pt = fmt.height * 72 / PIXELS_PER_INCH
    exp_left = round(paper.offset_x_pt * DPI / 72)
    exp_top = height - round((paper.offset_y_pt + image_height_pt) * DPI / 72)
    # The offsets are whole 600 dpi dots, so the left edge is exact. The top
    # edge is measured from the paper height, which is not a whole number of
    # dots for A4 (841.89 pt), so it depends on how the renderer rounds the
    # page height: allow 1 pixel there.
    assert left == exp_left, (left, exp_left)
    assert abs(top - exp_top) <= 1, (top, exp_top)

    outside = render.copy()
    outside[top:bottom, left:right] = 255
    assert (outside == 255).all()

    crop = render[top:bottom, left:right]
    replicated = np.kron(expected_page, np.ones((factor, factor), np.uint8))
    assert np.array_equal(crop, replicated)


@pytest.mark.parametrize("paper_name", ["a4", "letter"])
def test_ghostscript_render_decodes(ghostscript, tmp_path, paper_name, capsys):
    data = seeded_bytes(7, SIZE)
    infile = tmp_path / "in.bin"
    infile.write_bytes(data)
    base = tmp_path / "doc"
    argv = ["encode", str(infile), "-o", str(base), "--paper", paper_name, "--label", LABEL]
    assert main(argv) == 0

    proc = subprocess.run(
        [
            ghostscript,
            "-sDEVICE=pnggray",
            f"-r{DPI}",
            "-dNOPAUSE",
            "-dBATCH",
            "-dSAFER",
            "-q",
            f"-sOutputFile={tmp_path}/r_%04d.png",
            f"{base}.pdf",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    msg = f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert proc.returncode == 0, msg
    assert proc.stdout.strip() == "" and proc.stderr.strip() == "", msg

    paper = PAPERS[paper_name]
    fmt = PageFormat.for_paper(paper)
    expected = [p.pixels for p in encode(data, fmt, LABEL)]
    renders = sorted(tmp_path.glob("r_*.png"))
    assert len(renders) == len(expected) == 2
    width, height = RENDER_SIZES[paper_name]
    for path, page in zip(renders, expected, strict=True):
        with Image.open(path) as im:
            w, h = im.size
            assert abs(w - width) <= 1 and abs(h - height) <= 1, (path.name, w, h)
            check_render_page(np.array(im.convert("L")), page, paper, fmt)

    out = tmp_path / "out.bin"
    capsys.readouterr()
    rc = main(["decode", str(tmp_path / "r"), "--paper", paper_name, "-o", str(out)])
    err = capsys.readouterr().err
    assert rc == 0, err
    assert out.read_bytes()[:SIZE] == data
    lines = re.findall(r"page (\d+): (\d+) symbols, (\d+) corrected, (\d+) uncorrectable", err)
    assert len(lines) == 2, err
    for _, _, corrected, uncorrectable in lines:
        assert corrected == "0" and uncorrectable == "0", err
