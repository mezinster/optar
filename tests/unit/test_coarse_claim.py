# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The slower reader's claim, on a simulated scan (see docs/evidence.md).

A two-page document with Standard dots and High protection on A4 is scanned
with tests.helpers.simulate_scan, each page identified with identify_any and
the document unwrapped. The claim: the ordinary reader identifies no page,
and with the slower reader the file is recovered and verified.

The settings are 290 and 300 dpi at blur 1.8 printer dots, not the simulator's
defaults (blur 1.0), because at the defaults the claim does not hold: the
ordinary reader alone reads such a page at 300 dpi with no lost symbol, so
the slower reader is never needed. Measured on the same document:

- 300 dpi, blur 1.0 (defaults): ordinary reader, no lost symbol, verified.
- 300 dpi, blur 1.8, 2.0 and 2.2: the ordinary reader accepts each page from
  its untagged label without a header. identify_any does not settle for
  that on a coarse scan and tries the slower reader; at blur 1.8 the file
  then verifies (this test's 300 dpi case). Before that rule the file was
  not recovered.
- 290 dpi, blur 1.6: the ordinary reader identifies each page from its
  header, but the repair fails (worst block 65 of 64).
- 290 dpi and 280 dpi, blur 1.8: the ordinary reader fails ("label
  unreadable"). At 290 dpi the slower reader reads both pages with no
  repaired byte, and the file verifies (this test's 290 dpi case).

Blur 1.8 is the blur fitted to the owner's earlier real 300 dpi scans (the
binding blur of test_claims.py); 290 dpi is close to the owner's six real
scans (about 286 dpi). The simulator is still not the owner's scanner: on
the real scans the ordinary reader failed at about 286 dpi, here it needs
both the lower resolution and the higher blur to fail; and the slower
reader needed no repair here, where the real document needed 41,495 bytes
repaired (worst block 40 of 64).
"""

from __future__ import annotations

import pytest

from optar import PARITY, encode, get_layout, plan, plan_for, unwrap, wrap
from optar.identify import identify_any
from tests.helpers import seeded_bytes, simulate_scan

pytestmark = pytest.mark.slow

BLUR = 1.8
PAGES = 2
NAME = "coarse.bin"


# 290: the ordinary reader identifies nothing. 300: it reads each page's
# untagged label but no header, which identify_any does not settle for on a
# scan this coarse.
@pytest.mark.parametrize("dpi", [290, 300])
def test_slower_reader_recovers_a_document_the_ordinary_reader_cannot_read(dpi):
    layout = get_layout("a4", "standard")
    fmt, protect = layout.fmt, PARITY["high"]
    one = plan_for(1, fmt, protect).data_bytes
    data = seeded_bytes(PAGES, (PAGES - 1) * one + one // 2)
    assert plan(len(data), NAME, fmt, protect).total == PAGES
    images = [p.pixels for p in encode(wrap(data, NAME, fmt, protect), fmt, NAME)]

    payloads, header = {}, None
    tried: list[int] = []  # pages handed to the slower reader
    for number, pixels in enumerate(images, start=1):
        scan = simulate_scan(pixels, layout, dpi, blur=BLUR, seed=number)
        # identify_any calls on_slow only after identify_scan has failed with
        # a page outline found, or has read no more than an untagged label,
        # so one call shows both halves of the claim: with the slower reader
        # off (slow=False, or optar decode --no-slow-reader) this page's
        # header would not be found.
        ident = identify_any(scan, on_slow=lambda n=number: tried.append(n))
        assert tried[-1:] == [number], f"page {number}: the ordinary reader was enough"
        assert ident.reader == "slow"
        assert ident.layout is layout and ident.page == number
        assert ident.header is not None
        header = ident.header
        payloads[number] = ident.payload

    out = unwrap(header, fmt, payloads)
    assert out.verified and out.data == data, out
    assert out.worst_used <= out.budget

