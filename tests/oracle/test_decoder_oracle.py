# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Cross-decoding with the C tools: C unoptar reads Python pages, the Python
decoder reads C optar pages, and both decoders agree byte for byte on the
degraded scans."""

import subprocess

import numpy as np
import pytest
from PIL import Image

from optar import PageFormat, decode, encode, read_scan
from tests.helpers import DEGRADED, fake_scan, save_scan, seeded_bytes

pytestmark = pytest.mark.oracle

A4 = PageFormat(65, 93)
BIG = 300_000  # bytes: two A4 or Letter pages

# (id, optar.h overrides, format, input size). The Hamming orders use inputs
# just over one page, so every variant decodes two pages.
VARIANTS = [
    ("a4", {}, A4, BIG),
    ("letter", {"XCROSSES": 67, "YCROSSES": 87}, PageFormat(67, 87), BIG),
    *[
        (f"fec{n}", {"FEC_ORDER": n}, PageFormat(65, 93, fec_order=n), None)
        for n in (2, 3, 4, 5)
    ],
]
PARAMS = [pytest.param(*v[1:], id=v[0]) for v in VARIANTS]


def _size(fmt, size):
    return size if size is not None else fmt.net_bits // 8 + 2000


def _unoptar(c_build, overrides):
    build = c_build(overrides)
    if build.unoptar is None:
        pytest.skip("libpng headers not available")
    return build


def _run_unoptar(build, fmt, workdir, base="scan") -> bytes:
    r = subprocess.run(
        [build.unoptar, fmt.to_string(), base], cwd=workdir, check=False, capture_output=True
    )
    assert r.returncode == 0, f"unoptar failed ({r.returncode}): {r.stderr[-2000:].decode()}"
    return r.stdout


@pytest.mark.parametrize("overrides,fmt,size", PARAMS)
def test_c_decodes_python_pages(c_build, tmp_path, overrides, fmt, size):
    build = _unoptar(c_build, overrides)
    data = seeded_bytes(21, _size(fmt, size))
    pages = list(encode(data, fmt))
    assert len(pages) == 2
    for page in pages:
        save_scan(tmp_path / f"scan_{page.number:04d}.png", fake_scan(page.pixels, scale=1))
    out = _run_unoptar(build, fmt, tmp_path)
    assert len(out) == 2 * fmt.net_bits // 8
    assert out[: len(data)] == data


@pytest.mark.parametrize("overrides,fmt,size", PARAMS)
def test_python_decodes_c_pages(c_build, tmp_path, overrides, fmt, size):
    build = c_build(overrides)
    data = seeded_bytes(22, _size(fmt, size))
    (tmp_path / "in.bin").write_bytes(data)
    r = subprocess.run([build.optar, "in.bin"], cwd=tmp_path, check=False, capture_output=True)
    assert r.returncode == 0, f"optar failed ({r.returncode}): {r.stderr[-2000:].decode()}"
    files = sorted(tmp_path.glob("optar_out_*.pgm"))
    assert len(files) == 2

    def scans():
        for f in files:
            with Image.open(f) as im:
                yield fake_scan(np.asarray(im, np.uint8), scale=1)

    res = decode(scans(), fmt)
    assert len(res.data) == 2 * fmt.net_bits // 8
    assert res.data[: len(data)] == data and res.uncorrectable == 0


DEGRADED_DATA = seeded_bytes(11, 150000)


@pytest.fixture(scope="module")
def degraded_page():
    return next(encode(DEGRADED_DATA, A4)).pixels


@pytest.mark.parametrize("name", list(DEGRADED))
def test_degraded_decodes_like_c(c_build, tmp_path, degraded_page, name):
    build = _unoptar(c_build, {})
    path = tmp_path / "scan_0001.png"
    save_scan(path, fake_scan(degraded_page, seed=1, fmt=A4, **DEGRADED[name]))
    c_out = _run_unoptar(build, A4, tmp_path)
    res = decode([read_scan(path)], A4)
    assert len(res.data) == A4.net_bits // 8
    assert c_out == res.data
    assert res.data[: len(DEGRADED_DATA)] == DEGRADED_DATA
    assert res.uncorrectable == 0 and res.pages[0].max_corrected <= 2


@pytest.mark.parametrize(
    "overrides,fmt",
    [
        pytest.param({}, A4, id="a4"),
        pytest.param({"FEC_ORDER": 2}, PageFormat(65, 93, fec_order=2), id="fec2"),
        pytest.param({"FEC_ORDER": 5}, PageFormat(65, 93, fec_order=5), id="fec5"),
    ],
)
def test_uncorrectable_symbols_decode_like_c(c_build, tmp_path, overrides, fmt):
    # Heavy noise far beyond the margin gives corrections of every weight and
    # uncorrectable symbols, which must come out exactly as C writes them.
    build = _unoptar(c_build, overrides)
    page = next(encode(seeded_bytes(23, fmt.net_bits // 8), fmt)).pixels
    path = tmp_path / "scan_0001.png"
    save_scan(path, fake_scan(page, scale=3, noise=60, seed=2))
    c_out = _run_unoptar(build, fmt, tmp_path)
    res = decode([read_scan(path)], fmt)
    assert res.uncorrectable > 0
    assert c_out == res.data
