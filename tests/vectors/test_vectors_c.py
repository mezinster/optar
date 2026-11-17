"""Check the Python code against results recorded from the C tools (no compiler needed)."""

import pytest

from optar.encoder import encode
from optar.fec import golay_table, serialize_table
from optar.format import PageFormat
from optar.imageio import pgm_bytes
from optar.layout import channel_xy
from tests.helpers import seeded_bytes
from tests.vectors.load import digest, load

GOLAY = load("c/golay")
PLACEMENT = load("c/bit_placement")
PAGES = load("c/encoder_pages")


def test_golay_table():
    assert digest(serialize_table(golay_table())) == GOLAY["cases"]["golay_sha256"]


@pytest.mark.parametrize("fmt", PLACEMENT["cases"])
def test_bit_placement(fmt):
    x, y = channel_xy(PageFormat.parse(fmt))
    for seq, cx, cy in PLACEMENT["cases"][fmt]:
        assert (x[seq], y[seq]) == (cx, cy)


@pytest.mark.parametrize("case", PAGES["cases"], ids=lambda c: f'{c["name"]}-{c["format"]}')
def test_encoder_pages(case):
    fmt = PageFormat.parse(case["format"])
    pages = encode(seeded_bytes(case["seed"], case["size"]), fmt, case["label"])
    assert [digest(pgm_bytes(p.pixels)) for p in pages] == case["sha256"]
