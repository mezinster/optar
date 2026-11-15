# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Cross positions and cut levels against an instrumented copy of the C decoder.

The C unoptar prints nothing about the crosses, so this builds a copy whose
process_file dumps crosses[][] and cutlevels[][] right after sync_crosses()
and exits. The repo's C sources are never touched.
"""

import os
import shlex
import subprocess

import numpy as np
import pytest

from optar.decoder.crosses import sync_crosses
from optar.decoder.dirt import remove_border_dirt
from optar.decoder.geometry import compute_geometry, find_corners
from optar.decoder.levels import analyze_levels
from optar.decoder.options import DecodeOptions
from optar.encoder import encode
from optar.format import PageFormat
from optar.imageio import read_scan
from tests import cbuild
from tests.helpers import fake_scan, save_scan, seeded_bytes

pytestmark = pytest.mark.oracle

F, OPTS = PageFormat(65, 93), DecodeOptions()

_HOOK = "\tsync_crosses();\n"
_DUMP = r"""	sync_crosses();
	{
		unsigned dcx, dcy;
		FILE *dump=fopen("crosses.txt", "w");
		for (dcy=0;dcy<YCROSSES;dcy++)
			for (dcx=0;dcx<XCROSSES;dcx++)
				fprintf(dump, "%a %a %a\n", crosses[dcx][dcy][0],
					crosses[dcx][dcy][1], (double)cutlevels[dcx][dcy]);
		fclose(dump);
		exit(0);
	}
"""


@pytest.fixture(scope="module")
def dumping_unoptar(c_build):
    build = c_build()
    if build.unoptar is None:
        pytest.skip("libpng headers not available")
    src = build.dir / "unoptar.c"
    text = src.read_text()
    assert text.count(_HOOK) == 1
    patched = build.dir / "unoptar_dump.c"
    patched.write_text(text.replace(_HOOK, _DUMP))
    cc = cbuild.compiler()
    flags = cbuild._png_flags()
    ld = shlex.split(os.environ.get("OPTAR_TEST_LDFLAGS", ""))
    subprocess.run(
        [cc, *cbuild.CFLAGS, *flags, "-o", "unoptar_dump", "unoptar_dump.c",
         "common.o", "golay_codes.o", "parity.o", *ld, "-lm", "-lpng", "-lz"],
        cwd=build.dir, check=True, capture_output=True,
    )  # fmt: skip
    return build.dir / "unoptar_dump"


@pytest.mark.parametrize(
    "kw",
    [dict(scale=3), dict(scale=3, margin=120, rotate=0.4, blur=1.0, noise=8.0, seed=3)],
    ids=["clean", "degraded"],
)
def test_crosses_match_c(dumping_unoptar, tmp_path, kw):
    page = next(encode(seeded_bytes(5, 20000), F)).pixels
    save_scan(tmp_path / "scan_0001.png", fake_scan(page, **kw))
    subprocess.run(
        [dumping_unoptar, F.to_string(), "scan"], cwd=tmp_path, check=True, capture_output=True
    )
    rows = [
        [float.fromhex(v) for v in line.split()]
        for line in (tmp_path / "crosses.txt").read_text().splitlines()
    ]
    c = np.array(rows).reshape(F.ycrosses, F.xcrosses, 3).transpose(1, 0, 2)

    img = read_scan(tmp_path / "scan_0001.png")
    lv = analyze_levels(img, OPTS)
    img = remove_border_dirt(img, lv.fill_cut)
    geom = compute_geometry(find_corners(img, lv.cut), F, OPTS)
    pos, cuts = sync_crosses(img, geom, F, lv, OPTS)

    assert np.abs(pos - c[..., :2]).max() == 0
    assert np.abs(cuts - c[..., 2].astype(np.float32)).max() == 0
