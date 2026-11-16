# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The project's claims, on simulated scans.

Each claim prints a document with Standard protection on A4, scans every page
with tests.helpers.simulate_scan (a different seed per page), identifies each
scan from scratch with identify_scan, unwraps the document and requires the
fingerprint to match. Every claim holds at blur 1.8 printer dots (the fit to
the owner's real scans, binding) and at blur 1.0 (milder).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from functools import cache

import pytest

from optar import PARITY, encode, get_layout, identify_scan, plan, plan_for, unwrap, wrap
from optar.errors import IdentifyError
from tests.helpers import seeded_bytes, simulate_scan

pytestmark = pytest.mark.slow

PROTECT = PARITY["standard"]
BLURS = {"binding": 1.8, "mild": 1.0}

# name: (dot size, scan dpi, pages, pages withheld)
CLAIMS = {
    "medium-300": ("medium", 300, 3, ()),
    "medium-200": ("medium", 200, 3, ()),
    "big-200": ("big", 200, 3, ()),
    "large-300": ("large", 300, 3, ()),
    "large-200": ("large", 200, 3, ()),
    "xlarge-200": ("xlarge", 200, 3, ()),
    "large-300-lost-page": ("large", 300, 12, (7,)),
}


@cache
def document(dots: str, pages: int, paper: str = "a4"):
    """(layout, data, page images) of a protected document of exactly `pages` pages."""
    layout = get_layout(paper, dots)
    fmt = layout.fmt
    name = "claim.bin"
    one = plan_for(1, fmt, PROTECT).data_bytes
    data = seeded_bytes(pages, (pages - 1) * one + one // 2)
    assert plan(len(data), name, fmt, PROTECT).total == pages
    stream = wrap(data, name, fmt, PROTECT)
    return layout, data, tuple(p.pixels for p in encode(stream, fmt, name))


@dataclass
class Outcome:
    uncorrectable: dict[int, int]  # page -> Golay symbols lost, for identified pages
    unidentified: list[int]  # pages whose scan identify_scan refused
    headerless: list[int]  # pages identified from their label alone, no header read
    misplaced: list[int]  # pages identified as another layout or page
    repaired_bytes: int | None
    worst_used: int | None
    budget: int | None
    verified: bool
    seconds: float


def run_claim(dots, dpi, pages, withheld=(), blur=1.8, paper="a4") -> Outcome:
    layout, data, images = document(dots, pages, paper)
    start = time.perf_counter()
    payloads, header = {}, None
    uncorrectable, unidentified, headerless, misplaced = {}, [], [], []
    for number, pixels in enumerate(images, start=1):
        if number in withheld:
            continue
        scan = simulate_scan(pixels, layout, dpi, blur=blur, seed=number)
        try:
            ident = identify_scan(scan)
        except IdentifyError:
            unidentified.append(number)
            continue
        if ident.layout is not layout or ident.page != number:
            misplaced.append(number)
        elif ident.header is None:
            headerless.append(number)
        else:
            header = ident.header
            payloads[number] = ident.payload
            uncorrectable[number] = ident.result.stats.uncorrectable
    seen = (uncorrectable, unidentified, headerless, misplaced)
    if header is None:
        return Outcome(*seen, None, None, None, False, time.perf_counter() - start)
    out = unwrap(header, layout.fmt, payloads)
    return Outcome(
        *seen, out.repaired_bytes, out.worst_used, out.budget,
        out.verified and out.data == data, time.perf_counter() - start,
    )


@pytest.mark.parametrize("blur", list(BLURS))
@pytest.mark.parametrize("claim", list(CLAIMS))
def test_claim(claim, blur):
    dots, dpi, pages, withheld = CLAIMS[claim]
    outcome = run_claim(dots, dpi, pages, withheld, BLURS[blur])
    assert not outcome.misplaced and not outcome.headerless, outcome
    assert outcome.verified, outcome


def test_standard_dots_at_300_dpi_are_not_recovered():
    # Not a claim: the limit the tools must report honestly. At the blur of
    # the owner's scans a third of a Standard-dot page's bytes are wrong. The
    # page is refused, or identified from its untagged label with no header
    # (measured: the latter), or its document does not verify.
    outcome = run_claim("standard", 300, 1, blur=BLURS["binding"])
    assert not outcome.misplaced
    assert not outcome.verified
