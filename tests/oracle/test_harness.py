# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import subprocess

import pytest

pytestmark = pytest.mark.oracle


def test_c_optar_builds_and_encodes(c_build, tmp_path):
    build = c_build()
    (tmp_path / "in.bin").write_bytes(b"hello")
    subprocess.run([build.optar, "in.bin", "page"], cwd=tmp_path, check=True)
    assert (tmp_path / "page_0001.pgm").read_bytes().startswith(b"P5\n1546 2242\n255\n")


def test_c_build_with_letter_override(c_build, tmp_path):
    build = c_build({"XCROSSES": 67, "YCROSSES": 87})
    (tmp_path / "in.bin").write_bytes(b"hello")
    subprocess.run([build.optar, "in.bin", "page"], cwd=tmp_path, check=True)
    assert (tmp_path / "page_0001.pgm").read_bytes().startswith(b"P5\n1594 2098\n255\n")


def test_unoptar_built_when_libpng_available(c_build):
    build = c_build()
    if build.unoptar is None:
        pytest.skip("png.h not available")
    assert build.unoptar.is_file()
    assert build.golay_codes_c.is_file()
