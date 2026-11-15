# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Render the PDF with Ghostscript at 600 dpi and decode it back.

The closest thing to a print-and-scan: full paper size, white margins, and each
data pixel becomes exactly 3 x 3 render pixels.
"""

import subprocess

import pytest
from PIL import Image

from optar.cli import main
from optar.decoder import decode_page
from optar.format import PAPERS, PageFormat
from optar.imageio import read_scan
from tests.helpers import seeded_bytes

pytestmark = pytest.mark.gs

SIZE = 250_000
RENDER_SIZES = {"a4": (4961, 7016), "letter": (5100, 6600)}


@pytest.mark.parametrize("paper", ["a4", "letter"])
def test_ghostscript_render_decodes(ghostscript, tmp_path, paper, capsys):
    data = seeded_bytes(7, SIZE)
    infile = tmp_path / "in.bin"
    infile.write_bytes(data)
    base = tmp_path / "doc"
    assert main(["encode", str(infile), "-o", str(base), "--paper", paper]) == 0

    proc = subprocess.run(
        [
            ghostscript,
            "-sDEVICE=pnggray",
            "-r600",
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

    pages = sorted(tmp_path.glob("r_*.png"))
    assert len(pages) == 2
    width, height = RENDER_SIZES[paper]
    for page in pages:
        w, h = Image.open(page).size
        assert abs(w - width) <= 1 and abs(h - height) <= 1, (page.name, w, h)

    out = tmp_path / "out.bin"
    capsys.readouterr()
    rc = main(["decode", str(tmp_path / "r"), "--paper", paper, "-o", str(out)])
    err = capsys.readouterr().err
    assert rc == 0, err
    assert out.read_bytes()[:SIZE] == data

    fmt = PageFormat.for_paper(PAPERS[paper])
    stats = decode_page(read_scan(pages[0]), fmt).stats
    assert stats.uncorrectable == 0
    assert sum(stats.error_histogram[1:]) == 0
