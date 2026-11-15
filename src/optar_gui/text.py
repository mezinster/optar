# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Every user-visible string of the application, so the widgets hold no wording.

Plain Python, no Qt and no numpy. Plain language: a "block" is one
error-correction codeword; blocks are "repaired" or "lost". Counts carry
thousands separators and agree in number with their noun.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from optar_gui.document import DocState, Health, PageView, Summary

if TYPE_CHECKING:
    from optar_gui.document import Document

# Same wording as the command line's (optar.cli.ACTUAL_SIZE).
ACTUAL_SIZE = 'Print at actual size (100%), not "fit to page".'

# Titles of the sections of the list of scans.
NOT_PART_OF_THIS_FILE = "Not part of this file"
NOT_READABLE = "Not readable"

_HEALTH_LABELS = {
    Health.GOOD: "Good",
    Health.UNREADABLE: "Not readable",
    Health.MISSING: "Missing",
    Health.WAITING: "Waiting",
    Health.WORKING: "Working…",
}

_REASONS = {
    "no page found": "No optar page found in this image",
    "label unreadable": "The label at the bottom of the page could not be read",
    "page number out of range": "The label's page number does not fit this document",
}

# What a page that spoils the saved file is, in a warning; waiting and working
# pages read the same.
_PROBLEMS = {
    Health.MISSING: "missing",
    Health.DAMAGED: "damaged",
    Health.UNREADABLE: "not readable",
    Health.WAITING: "still being read",
    Health.WORKING: "still being read",
}


def count(n: int, noun: str) -> str:
    """``1 page``, ``2 pages``, ``1,205 pages``."""
    return f"{n:,} {noun}" if n == 1 else f"{n:,} {noun}s"


def health_label(page: PageView) -> str:
    if page.health == Health.REPAIRED:
        return f"Repaired · {page.repaired:,}"
    if page.health == Health.DAMAGED:
        return f"Damaged · {page.lost:,} lost"
    return _HEALTH_LABELS[page.health]


def summary_line(s: Summary) -> str:
    """The document's state for the bottom bar."""
    pages = s.good + s.repaired + s.damaged + s.unreadable + s.missing
    if s.state == DocState.EMPTY:
        return ""
    if s.state == DocState.WORKING:
        return "Working…"
    if s.state == DocState.VERIFIED:
        return f"Verified · {count(s.size, 'byte')}"
    if s.state == DocState.MISMATCH:
        return "Does not match the fingerprint on the paper"
    if s.state == DocState.UNVERIFIABLE:
        read = f"All {count(pages, 'page')}" if pages > 1 else count(pages, "page")
        return f"{read} read · cannot be verified (no tag)"
    parts = [f"{s.good + s.repaired:,} of {count(pages, 'page')} good"]
    for n, what in ((s.damaged, "damaged"), (s.unreadable, "not readable"), (s.missing, "missing")):
        if n:
            parts.append(f"{n:,} {what}")
    return " · ".join(parts)


def _runs(pages: tuple[PageView, ...]) -> list[tuple[int, int, str]]:
    """Consecutive pages with the same problem, as (first, last, problem)."""
    runs: list[tuple[int, int, str]] = []
    for p in pages:
        problem = _PROBLEMS.get(p.health)
        if problem is None:
            continue
        if runs and runs[-1][2] == problem and runs[-1][1] == p.number - 1:
            runs[-1] = (runs[-1][0], p.number, problem)
        else:
            runs.append((p.number, p.number, problem))
    return runs


def _run_text(first: int, last: int, problem: str) -> str:
    if first == last:
        return f"page {first} is {problem}"
    if last == first + 1:
        return f"pages {first} and {last} are {problem}"
    return f"pages {first}-{last} are {problem}"


def save_warning(doc: Document) -> str | None:
    """What saving must confirm first; None when the file is verified."""
    state = doc.summary().state
    if state == DocState.VERIFIED:
        return None
    if state == DocState.EMPTY:
        return "There is nothing to save."
    if state == DocState.MISMATCH:
        return (
            "The recovered file does not match the fingerprint printed on the paper, "
            "so it may be wrong."
        )
    if state == DocState.UNVERIFIABLE:
        return (
            "These pages carry no tag, so the recovered file cannot be verified. "
            "It will be padded with zeros to a whole page."
        )
    problems = "; ".join(_run_text(*run) for run in _runs(doc.pages()))
    return f"The saved file will be incomplete: {problems}."


def untagged_caution() -> str:
    return (
        "These pages carry no tag, so it cannot be confirmed that they belong to the "
        "same printout or that the file is complete. The saved file will be padded "
        "with zeros."
    )


def unreadable_reason(reason: str) -> str:
    """The library's reason for an unreadable scan, in plain words."""
    return _REASONS.get(reason, reason)


def detail_text(
    page: PageView, scan_name: str | None, pages: int, reason: str = ""
) -> tuple[str, ...]:
    """The detail panel's lines for one page of a document of ``pages`` pages."""
    title = f"Page {page.number} of {pages}"
    if scan_name:
        title += f" · {scan_name}"
    if page.histogram is not None:
        blocks = sum(page.histogram) + page.lost
        blocks_line = f"{count(blocks, 'block')} · {page.repaired:,} repaired · {page.lost:,} lost"
        lines = [title, blocks_line]
        if page.repaired:
            one, two, three = page.histogram[1:]
            lines.append(f"Repairs: {one:,} one-bit, {two:,} two-bit, {three:,} three-bit")
        return tuple(lines)
    if page.health == Health.MISSING:
        return (title, "No scan of this page has been added")
    if page.health == Health.WAITING:
        return (title, "Waiting to be read")
    if page.health == Health.UNREADABLE:
        return (title, unreadable_reason(reason) if reason else "This scan could not be read")
    return (title, "Being read…")
