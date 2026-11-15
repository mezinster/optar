# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Decode real scans kept under tests/scans/<case>/ (see README.md)."""

from pathlib import Path

import pytest

from optar import PageFormat, decode, get_paper, read_scan

HERE = Path(__file__).resolve().parent
CASES = sorted(p for p in HERE.iterdir() if p.is_dir() and (p / "original.bin").is_file())
PARAMS = [pytest.param(p, id=p.name) for p in CASES] or [
    pytest.param(None, id="none", marks=pytest.mark.skip(reason="no real scans in tests/scans"))
]


@pytest.mark.parametrize("case", PARAMS)
def test_real_scan_decodes(case):
    original = (case / "original.bin").read_bytes()
    fmt = PageFormat.for_paper(get_paper((case / "paper.txt").read_text().strip()))
    scans = sorted(case.glob("scan_*.png"))
    assert scans, f"no scan_*.png in {case}"
    res = decode((read_scan(p) for p in scans), fmt)
    assert res.uncorrectable == 0
    assert res.data[: len(original)] == original
