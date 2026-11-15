# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Compare the Python encoder with fixtures recorded from the C tools (no compiler needed)."""

import hashlib
import json
from pathlib import Path

import pytest

from optar.encoder import encode
from optar.fec import golay_table, serialize_table
from optar.format import PageFormat
from optar.imageio import pgm_bytes
from optar.layout import channel_xy
from tests.helpers import seeded_bytes

FX = json.loads(Path(__file__).with_name("fixtures.json").read_text())


def test_golay_table_matches_c():
    assert hashlib.sha256(serialize_table(golay_table())).hexdigest() == FX["golay_sha256"]


@pytest.mark.parametrize("fmt", FX["seq2xy"])
def test_layout_matches_c(fmt):
    x, y = channel_xy(PageFormat.parse(fmt))
    for seq, cx, cy in FX["seq2xy"][fmt]:
        assert (x[seq], y[seq]) == (cx, cy)


@pytest.mark.parametrize("case", FX["pages"], ids=lambda c: f'{c["name"]}-{c["format"]}')
def test_pages_match_c(case):
    fmt = PageFormat.parse(case["format"])
    pages = encode(seeded_bytes(case["seed"], case["size"]), fmt, case["label"])
    got = [hashlib.sha256(pgm_bytes(p.pixels)).hexdigest() for p in pages]
    assert got == case["sha256"]
