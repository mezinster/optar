# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Container streams on larger-dot layouts: the pages are exactly what C optar
makes of the same stream, and C unoptar built with the same grid reads them."""

import subprocess

import pytest

from optar import encode
from optar.container import wrap
from optar.format import get_layout
from optar.imageio import pgm_bytes
from tests.helpers import fake_scan, save_scan, seeded_bytes

pytestmark = pytest.mark.oracle

LABEL = "doc"
PARITY = 32
LAYOUTS = [
    pytest.param("a4", "large", id="a4-large"),
    pytest.param("letter", "medium", id="letter-medium"),
]


def _setup(c_build, paper, dots):
    fmt = get_layout(paper, dots).fmt
    build = c_build({"XCROSSES": fmt.xcrosses, "YCROSSES": fmt.ycrosses})
    data = seeded_bytes(31, 100_000)
    return build, fmt, wrap(data, "name.bin", fmt, PARITY)


def _c_pages(build, stream, workdir):
    (workdir / "in.bin").write_bytes(stream)
    r = subprocess.run(
        [build.optar, "in.bin", LABEL], cwd=workdir, check=False, capture_output=True
    )
    assert r.returncode == 0, f"optar failed ({r.returncode}): {r.stderr[-2000:].decode()}"
    return sorted(workdir.glob(f"{LABEL}_*.pgm"))


@pytest.mark.parametrize("paper,dots", LAYOUTS)
def test_container_pages_match_c(c_build, tmp_path, paper, dots):
    build, fmt, stream = _setup(c_build, paper, dots)
    c_files = _c_pages(build, stream, tmp_path)
    py_pages = list(encode(stream, fmt, LABEL))
    assert len(py_pages) == len(c_files) >= 1
    for page, c_file in zip(py_pages, c_files, strict=True):
        assert pgm_bytes(page.pixels) == c_file.read_bytes(), c_file.name


@pytest.mark.parametrize("paper,dots", LAYOUTS)
def test_c_unoptar_reads_container_pages(c_build, tmp_path, paper, dots):
    build, fmt, stream = _setup(c_build, paper, dots)
    if build.unoptar is None:
        pytest.skip("libpng headers not available")
    pages = list(encode(stream, fmt, LABEL))
    assert len(pages) > 1  # unoptar must go on from one page to the next
    for page in pages:
        save_scan(tmp_path / f"scan_{page.number:04d}.png", fake_scan(page.pixels, scale=1))
    r = subprocess.run(
        [build.unoptar, fmt.to_string(), "scan"], cwd=tmp_path, check=False, capture_output=True
    )
    assert r.returncode == 0, f"unoptar failed ({r.returncode}): {r.stderr[-2000:].decode()}"
    assert len(r.stdout) == len(pages) * fmt.net_bits // 8
    assert r.stdout[: len(stream)] == stream
