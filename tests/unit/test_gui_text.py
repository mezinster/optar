# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The wording the window shows, kept in one module with no Qt."""

import pytest

from optar import cli
from optar.tag import make_tag
from optar_gui import text
from optar_gui.document import (
    SIZE_MISMATCH,
    DocState,
    Document,
    Health,
    PageOutcome,
    PageView,
    ScanInfo,
    Summary,
)

A = "0-65-93-24-3-1-2-24"
PAGE = 1000


def page(number, health, repaired=0, lost=0, histogram=None, scan_id=1):
    return PageView(number, health, scan_id, (), repaired, lost, histogram)


def document(pages, tag, name="doc.tar"):
    """Pages are (data, lost) or None for a page with no scan."""
    doc = Document()
    for number, item in enumerate(pages, 1):
        if item is None:
            continue
        scan_id = doc.add_scan(f"/scans/{number}.png")
        doc.set_identified(scan_id, ScanInfo(A, len(pages), number, name, tag))
        data, lost = item
        doc.set_outcome(scan_id, PageOutcome(data, (1000, 0, 0, 0), lost))
    return doc


S, D = Summary, DocState
DATA = bytes(range(256)) * 19  # 4864 bytes: five pages of 1000


def five_pages():
    padded = DATA.ljust(5 * PAGE, b"\0")
    return [(padded[i * PAGE:(i + 1) * PAGE], 0) for i in range(5)]


def test_health_labels():
    assert text.health_label(page(1, Health.GOOD)) == "Good"
    assert text.health_label(page(1, Health.REPAIRED, repaired=198)) == "Repaired · 198"
    assert text.health_label(page(1, Health.REPAIRED, repaired=1234)) == "Repaired · 1,234"
    assert text.health_label(page(1, Health.DAMAGED, repaired=9, lost=37)) == "Damaged · 37 lost"
    assert text.health_label(page(1, Health.UNREADABLE)) == "Not readable"
    assert text.health_label(page(1, Health.MISSING, scan_id=None)) == "Missing"
    assert text.health_label(page(1, Health.WAITING)) == "Waiting"
    assert text.health_label(page(1, Health.WORKING)) == "Working…"


@pytest.mark.parametrize(
    "summary, line",
    [
        (S(D.EMPTY, 0, 0, 0, 0, 0, None), ""),
        (S(D.WORKING, 1, 0, 0, 0, 2, 9), "Working…"),
        (
            S(D.INCOMPLETE, 2, 1, 1, 0, 1, 9),
            "3 of 5 pages good (1 repaired) · 1 damaged · 1 missing",
        ),
        (S(D.INCOMPLETE, 3, 0, 1, 0, 1, 9), "3 of 5 pages good · 1 damaged · 1 missing"),
        (
            S(D.INCOMPLETE, 0, 0, 2, 3, 1200, None),
            "0 of 1,205 pages good · 2 damaged · 3 not readable · 1,200 missing",
        ),
        (S(D.INCOMPLETE, 0, 0, 0, 0, 1, None), "0 of 1 page good · 1 missing"),
        (S(D.VERIFIED, 4, 1, 0, 0, 0, 2481152), "Verified · 2,481,152 bytes"),
        (S(D.VERIFIED, 1, 0, 0, 0, 0, 1), "Verified · 1 byte"),
        (S(D.MISMATCH, 5, 0, 0, 0, 0, 9), "Does not match the fingerprint on the paper"),
        (
            S(D.UNVERIFIABLE, 3, 2, 0, 0, 0, None),
            "All 5 pages read · cannot be verified (no tag)",
        ),
        (S(D.UNVERIFIABLE, 1, 0, 0, 0, 0, None), "1 page read · cannot be verified (no tag)"),
    ],
)
def test_summary_line(summary, line):
    assert text.summary_line(summary) == line


def test_save_warning_names_pages():
    pages = five_pages()
    pages[1] = None
    pages[3] = (pages[3][0], 37)
    doc = document(pages, make_tag(DATA))
    warning = text.save_warning(doc)
    assert "page 2" in warning and "page 4" in warning and "incomplete" in warning
    assert warning == "The saved file will be incomplete: page 2 is missing; page 4 is damaged."


def test_save_warning_groups_runs_of_pages():
    doc = Document()
    scans = {}
    for number in (1, 2, 6, 9):
        scans[number] = doc.add_scan(f"/scans/{number}.png")
        doc.set_identified(scans[number], ScanInfo(A, 10, number, "doc.tar", None))
    doc.set_outcome(scans[1], PageOutcome(bytes(PAGE), (1000, 0, 0, 0), 0))
    doc.set_outcome(scans[2], PageOutcome(bytes(PAGE), (1000, 0, 0, 0), 3))
    doc.set_outcome(scans[6], PageOutcome(bytes(PAGE), (1000, 0, 0, 0), 0))
    doc.set_unreadable(scans[9], "decoding failed")
    doc.assign_page(scans[9], 9)
    assert text.save_warning(doc) == (
        "The saved file will be incomplete: page 2 is damaged; pages 3-5 are missing; "
        "pages 7 and 8 are missing; page 9 is not readable; page 10 is missing."
    )


def test_save_warning_while_pages_are_still_being_read():
    doc = Document()
    first = doc.add_scan("/scans/1.png")
    second = doc.add_scan("/scans/2.png")
    doc.set_identified(first, ScanInfo(A, 2, 1, "doc.tar", None))
    doc.set_identified(second, ScanInfo(A, 2, 2, "doc.tar", None))
    doc.set_outcome(first, PageOutcome(bytes(PAGE), (1000, 0, 0, 0), 0))
    assert text.save_warning(doc) == (
        "The saved file will be incomplete: page 2 is still being read."
    )


def test_save_warning_none_when_verified():
    doc = document(five_pages(), make_tag(DATA))
    assert doc.summary().state == DocState.VERIFIED
    assert text.save_warning(doc) is None


def test_save_warning_when_the_fingerprint_does_not_match():
    pages = five_pages()
    pages[0] = (b"\x01" + pages[0][0][1:], 0)
    doc = document(pages, make_tag(DATA))
    assert text.save_warning(doc) == (
        "The recovered file does not match the fingerprint printed on the paper: "
        "some data was decoded wrongly, so this is not the original file."
    )


def test_save_warning_without_a_tag():
    doc = document(five_pages(), None)
    assert not doc.by_hand
    assert text.save_warning(doc) == (
        "These pages carry no tag, so the file cannot be verified and will be "
        "padded with zeros to a whole page."
    )


def test_save_warning_for_a_document_put_together_by_hand():
    doc = Document()
    doc.start_by_hand(A, 1)
    scan_id = doc.add_scan("/scans/1.png")
    doc.set_unreadable(scan_id, "label unreadable")
    doc.set_outcome(scan_id, PageOutcome(bytes(PAGE), (1000, 0, 0, 0), 0))
    doc.assign_page(scan_id, 1)
    assert doc.summary().state == DocState.UNVERIFIABLE
    assert text.save_warning(doc) == (
        "This document was put together by hand, so the file cannot be verified "
        "and will be padded with zeros to a whole page."
    )


def test_save_warning_names_at_most_ten_runs():
    doc = Document()
    for number in range(1, 10000, 2):  # every odd page of 9,999; the even ones missing
        scan_id = doc.add_scan(f"/scans/{number}.png")
        doc.set_identified(scan_id, ScanInfo(A, 9999, number, "doc.tar", None))
        doc.set_outcome(scan_id, PageOutcome(bytes(PAGE), (1000, 0, 0, 0), 0))
    warning = text.save_warning(doc)
    assert len(warning) < 1000
    assert warning == (
        "The saved file will be incomplete: page 2 is missing; page 4 is missing; "
        "page 6 is missing; page 8 is missing; page 10 is missing; page 12 is missing; "
        "page 14 is missing; page 16 is missing; page 18 is missing; page 20 is missing; "
        "and 4,989 more pages missing or damaged."
    )


def test_save_warning_counts_one_more_page():
    doc = Document()
    for number in range(1, 23, 2):  # of 22 pages, 2, 4, ..., 22 are missing: 11 runs
        scan_id = doc.add_scan(f"/scans/{number}.png")
        doc.set_identified(scan_id, ScanInfo(A, 22, number, "doc.tar", None))
        doc.set_outcome(scan_id, PageOutcome(bytes(PAGE), (1000, 0, 0, 0), 0))
    assert text.save_warning(doc).endswith(
        "; page 20 is missing; and 1 more page missing or damaged."
    )


def test_save_warning_with_nothing_to_save():
    assert text.save_warning(Document()) == "There is nothing to save."


def test_untagged_caution():
    assert text.untagged_caution() == (
        "These pages carry no tag, so it cannot be confirmed that they belong to the "
        "same printout or that the file is complete. The saved file will be padded "
        "with zeros."
    )


def test_actual_size_is_the_command_lines_wording():
    assert text.ACTUAL_SIZE == 'Print at actual size (100%), not "fit to page".'
    assert text.ACTUAL_SIZE == cli.ACTUAL_SIZE


def test_detail_text_of_a_decoded_page():
    p = page(4, Health.DAMAGED, repaired=512, lost=37, histogram=(132633, 480, 30, 2))
    assert text.detail_text(p, "scan_0004.png", 5) == (
        "Page 4 of 5 · scan_0004.png",
        "133,182 blocks · 512 repaired · 37 lost",
        "Repairs: 480 one-bit, 30 two-bit, 2 three-bit",
    )


def test_detail_text_of_a_good_page_has_no_repairs_line():
    p = page(1, Health.GOOD, histogram=(1, 0, 0, 0))
    assert text.detail_text(p, "a.png", 1) == (
        "Page 1 of 1 · a.png",
        "1 block · 0 repaired · 0 lost",
    )


def test_detail_text_uses_the_pages_own_reason():
    p = PageView(2, Health.UNREADABLE, 7, (), 0, 0, None, SIZE_MISMATCH)
    assert text.detail_text(p, "letter.png", 2) == (
        "Page 2 of 2 · letter.png",
        "This scan is of a different paper size than the document",
    )


def test_detail_text_of_pages_without_an_outcome():
    assert text.detail_text(page(5, Health.MISSING, scan_id=None), None, 5) == (
        "Page 5 of 5",
        "No scan of this page has been added",
    )
    assert text.detail_text(page(2, Health.WAITING), "b.png", 5) == (
        "Page 2 of 5 · b.png",
        "Waiting to be read",
    )
    assert text.detail_text(page(2, Health.WORKING), "b.png", 5)[1] == "Being read…"
    assert text.detail_text(page(2, Health.UNREADABLE), "b.png", 5)[1] == (
        "This scan could not be read"
    )
    assert text.detail_text(page(2, Health.UNREADABLE), "b.png", 5, "label unreadable")[1] == (
        "The label at the bottom of the page could not be read"
    )


@pytest.mark.parametrize(
    "reason, shown",
    [
        ("no page found", "No optar page found in this image"),
        ("label unreadable", "The label at the bottom of the page could not be read"),
        ("page number out of range", "The label's page number does not fit this document"),
        ("page count out of range", "The label's page count is not possible"),
        (
            "page size does not match this document",
            "This scan is of a different paper size than the document",
        ),
        ("cannot open file", "cannot open file"),
    ],
)
def test_unreadable_reasons(reason, shown):
    assert text.unreadable_reason(reason) == shown


def test_section_titles():
    assert text.NOT_PART_OF_THIS_FILE == "Not part of this file"
    assert text.NOT_READABLE == "Not readable"
