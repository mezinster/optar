# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Byte-for-byte comparison of the Python encoder with the C optar tool."""

import subprocess

import pytest

from optar.encoder import encode
from optar.format import PageFormat
from optar.imageio import pgm_bytes
from tests.helpers import seeded_bytes

pytestmark = pytest.mark.oracle

VARIANTS = [
    ("a4", {}, PageFormat(65, 93)),
    ("letter", {"XCROSSES": 67, "YCROSSES": 87}, PageFormat(67, 87)),
    *[
        (f"fec{n}", {"FEC_ORDER": n}, PageFormat(65, 93, fec_order=n))
        for n in (2, 3, 4, 5)
    ],
]


@pytest.mark.parametrize("overrides,fmt", [v[1:] for v in VARIANTS], ids=[v[0] for v in VARIANTS])
def test_encoder_matches_c(c_build, tmp_path, overrides, fmt):
    build = c_build(overrides)
    net_bytes = fmt.net_bits // 8
    for seed, size in enumerate([0, 1, 777, 2 * net_bytes + 5]):
        data = seeded_bytes(seed, size)
        work = tmp_path / f"case{seed}"
        work.mkdir()
        (work / "in.bin").write_bytes(data)
        subprocess.run([build.optar, "in.bin"], cwd=work, check=True, capture_output=True)
        c_files = sorted(work.glob("optar_out_*.pgm"))
        py_pages = list(encode(data, fmt))
        assert len(py_pages) == len(c_files), f"size {size}"
        for page, c_file in zip(py_pages, c_files, strict=True):
            assert pgm_bytes(page.pixels) == c_file.read_bytes(), f"size {size} {c_file.name}"
