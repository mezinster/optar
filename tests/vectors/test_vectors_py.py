"""Check today's Reed-Solomon code, container and tag against frozen vectors (no compiler needed).

The vectors were made by `python -m tests.vectors.py.make`; its functions
recompute each result from the inputs stored in the files.
"""

import pytest

from tests.vectors.load import load
from tests.vectors.py import make

RS = load("py/reed_solomon")
CONTAINER = load("py/container")
TAG = load("py/tag")


@pytest.mark.parametrize(
    "case", RS["cases"]["parity"], ids=lambda c: f'{c["parity"]}-{c["message"]}'
)
def test_reed_solomon_parity(case):
    assert make.parity_case(case["parity"], case["message"]) == case


@pytest.mark.parametrize(
    "case", RS["cases"]["repairs"], ids=lambda c: f'{c["parity"]}-{c["what"]}'
)
def test_reed_solomon_repairs(case):
    outcome = make.repair_outcome(case)
    assert outcome == case["outcome"]
    if outcome["ok"]:
        assert outcome["words_sha256"] == outcome["original_sha256"]
    else:
        assert outcome["words_sha256"] == outcome["received_sha256"]


def test_header_bytes():
    case = CONTAINER["cases"]["header"]
    assert make.header_hex(case["args"]) == case["hex"]


def test_padding_stream():
    case = CONTAINER["cases"]["padding"]
    assert make.padding_hex(case["args"]) == case["hex"]


STREAMS = CONTAINER["cases"]["streams"]


def test_container_cases_cover_every_layout_and_parity():
    assert [(c["layout"], c["parity"]) for c in STREAMS] == [
        (n, p) for n in make.layout_names() for p in make.CONTAINER_PARITIES
    ]


@pytest.mark.parametrize("case", STREAMS, ids=lambda c: f'{c["layout"]}-{c["parity"]}')
def test_container_streams(case):
    got = make.stream_case(case["layout"], case["parity"])
    for key in ("format", "size", "pages", "codewords", "stream_bytes", "stream_sha256"):
        assert got[key] == case[key], key


@pytest.mark.parametrize("case", STREAMS, ids=lambda c: f'{c["layout"]}-{c["parity"]}')
def test_spread_positions(case):
    got = make.stream_case(case["layout"], case["parity"])
    assert got["positions"] == case["positions"]


@pytest.mark.parametrize("case", TAG["cases"]["tags"], ids=lambda c: c["input"]["name"])
def test_tags(case):
    assert make.tag_case(case["input"]) == case
