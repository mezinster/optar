# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Sampled channel bits against an instrumented copy of the C decoder.

The copy writes the raw bit passed to read_hamming_bit (pixval < local_cutlevel)
as one byte per bit in read_syms loop order, then exits after read_syms().
The repo's C sources are never touched.
"""

import subprocess

import numpy as np
import pytest

from optar.decoder.crosses import sync_crosses
from optar.decoder.dirt import remove_border_dirt
from optar.decoder.filters import blur, minmax
from optar.decoder.geometry import compute_geometry, find_corners
from optar.decoder.levels import analyze_levels
from optar.decoder.options import DecodeOptions
from optar.decoder.sample import sample_bits
from optar.encoder import encode
from optar.format import PageFormat
from optar.imageio import read_scan
from tests import cbuild
from tests.helpers import fake_scan, save_scan, seeded_bytes

pytestmark = pytest.mark.oracle

F, OPTS = PageFormat(65, 93), DecodeOptions()

_BIT = "read_hamming_bit(pixval<local_cutlevel, hamming_sym);"
_BIT_DUMP = (
    """{
				static FILE *bitdump;
				if (!bitdump) bitdump=fopen("bits.bin", "wb");
				fputc(pixval<local_cutlevel, bitdump);
			}
			"""
    + _BIT
)
_READ = "\tread_syms();\n"
_READ_EXIT = "\tread_syms();\n\texit(0);\n"


@pytest.fixture(scope="module")
def dumping_unoptar(c_build):
    build = c_build()
    if build.unoptar is None:
        pytest.skip("libpng headers not available")
    return cbuild.build_patched_unoptar(
        build, "unoptar_bits", [(_BIT, _BIT_DUMP), (_READ, _READ_EXIT)]
    )


@pytest.mark.parametrize(
    "kw",
    [dict(scale=3), dict(scale=3, margin=120, rotate=0.4, blur=1.0, noise=8.0, seed=3)],
    ids=["clean", "degraded"],
)
def test_sampled_bits_match_c(dumping_unoptar, tmp_path, kw):
    page = next(encode(seeded_bytes(5, 150000), F)).pixels
    save_scan(tmp_path / "scan_0001.png", fake_scan(page, **kw))
    subprocess.run(
        [dumping_unoptar, F.to_string(), "scan"], cwd=tmp_path, check=True, capture_output=True
    )
    raw = np.fromfile(tmp_path / "bits.bin", np.uint8)
    assert raw.size == F.used_bits
    # C loop: hamming_sym outer, bit inner, seq = hamming_sym + bit * fec_syms.
    c_bits = raw.reshape(F.fec_syms, F.fec_largebits).T.ravel()

    img = read_scan(tmp_path / "scan_0001.png")
    lv = analyze_levels(img, OPTS)
    img = remove_border_dirt(img, lv.fill_cut)
    geom = compute_geometry(find_corners(img, lv.cut), F, OPTS)
    pos, cuts = sync_crosses(img, geom, F, lv, OPTS)
    img = blur(minmax(img, geom, OPTS), geom, OPTS)
    bits = sample_bits(img, pos, cuts, geom, F, OPTS)

    assert int(np.count_nonzero(bits[: F.used_bits] != c_bits)) == 0
