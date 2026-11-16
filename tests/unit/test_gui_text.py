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
    Fit,
    GroupView,
    Health,
    PageOutcome,
    PageView,
    ScanInfo,
    ScanView,
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


# --- The reading tab ------------------------------------------------------------


def group(title="doc.tar", total=5, fmt=A, tag=None, scan_ids=(1,)):
    return GroupView(scan_ids[0], title, total, fmt, tag, scan_ids)


def test_paper_names():
    assert text.paper_name(A) == "A4"
    assert text.paper_name("0-67-87-24-3-1-2-24") == "US Letter"
    assert text.paper_name("0-1-2-3-4-5-6-7") == "0-1-2-3-4-5-6-7"


def test_document_title():
    assert text.document_title(group()) == "doc.tar · A4 · 5 pages"
    assert text.document_title(group(total=1)) == "doc.tar · A4 · 1 page"
    assert text.document_title(group(total=0)) == "doc.tar · A4 · 1 page"  # empty file
    assert text.document_title(group(title="", total=1205)) == (
        "(no name) · A4 · 1,205 pages"
    )


def test_list_rows():
    assert text.page_row(page(3, Health.GOOD)) == "Page 3 · Good"
    assert text.page_row(page(1205, Health.DAMAGED, lost=37)) == "Page 1,205 · Damaged · 37 lost"
    assert text.other_group_row(group(total=3, scan_ids=(4, 9))) == (
        "doc.tar · A4 · 3 pages · 2 scans"
    )
    assert text.unreadable_row(ScanView(3, "/x/blank.png", "unreadable", None, None,
                                        "no page found")) == (
        "blank.png · No optar page found in this image"
    )


def test_unreadable_detail():
    view = ScanView(3, "/x/blank.png", "unreadable", None, None, "label unreadable")
    assert text.unreadable_detail(view) == (
        "blank.png",
        "The label at the bottom of the page could not be read",
    )


def test_other_group_detail():
    assert text.other_group_detail(group(total=3, scan_ids=(4, 9))) == (
        "doc.tar · A4 · 3 pages",
        "2 scans of another printout, not part of this file",
    )


def test_caution():
    tag = make_tag(DATA)
    assert text.caution(Document()) is None
    assert text.caution(document(five_pages(), tag)) is None
    assert text.caution(document(five_pages(), None)) == text.untagged_caution()
    doc = Document()
    doc.start_by_hand(A, 3)
    assert text.caution(doc) == text.by_hand_caution()
    assert "by hand" in text.by_hand_caution()


def test_summary_line_while_checking():
    assert text.summary_line(S(D.CHECKING, 5, 0, 0, 0, 0, 9)) == (
        "Checking the fingerprint…"
    )


def test_save_warning_while_checking_uses_the_given_summary():
    doc = document(five_pages(), make_tag(DATA))
    checking = doc.summary(verify=False)
    assert checking.state == D.CHECKING
    assert text.save_warning(doc, checking) == (
        "The fingerprint is still being checked, so it is not yet known whether the "
        "recovered file is the original."
    )
    assert text.save_warning(doc, doc.summary()) is None


def test_bar_and_save_messages():
    assert text.summary_bar("Verified · 9 bytes", "") == "Verified · 9 bytes"
    assert text.summary_bar("Verified · 9 bytes", "Saved") == "Verified · 9 bytes — Saved"
    assert text.saved_message("/out/doc.tar", 250_000) == "Saved 250,000 bytes to doc.tar"
    assert text.save_failed("cannot write /x: Permission denied") == (
        "The file could not be saved: cannot write /x: Permission denied"
    )


def test_captions_and_filter():
    for caption in (text.ADD_SCANS, text.REMOVE_SCAN, text.SAVE_FILE, text.READ_TAB,
                    text.WINDOW_TITLE, text.ADD_SCANS_TITLE, text.SAVE_TITLE,
                    text.CONFIRM_SAVE_TITLE, text.ERROR_TITLE):
        assert caption.strip()
    assert text.scan_filter() == (
        "Scans (*.png *.tif *.tiff *.bmp *.pgm *.ppm *.jpg *.jpeg);;All files (*)"
    )


def test_detail_text_counts_pages_with_thousands_separators():
    assert text.detail_text(page(1205, Health.MISSING, scan_id=None), None, 9999)[0] == (
        "Page 1,205 of 9,999"
    )


def test_check_failed_and_save_refusals():
    assert text.check_failed("MemoryError") == (
        "The fingerprint could not be checked: MemoryError"
    )
    assert text.SAVE_RUNNING == "a save is already running"
    assert "closed" in text.SAVE_AFTER_CLOSE


def test_preview_messages():
    assert text.preview_failed("cannot identify image file") == (
        "This scan cannot be shown: cannot identify image file"
    )
    assert text.too_large_to_show(700_000_000, 600_000_000) == (
        "700,000,000 pixels is more than the 600,000,000 a scan may have"
    )
    assert text.PREVIEW_LOADING == "Loading…"
    assert text.size_changed() == "the image's size changed while it was loading"


def test_spare_row_and_detail():
    spare = PageView(2, Health.DAMAGED, 7, (3,), 9, 22, (1000, 9, 0, 0))
    assert text.spare_row(spare, "page-2.png") == "    Spare · page-2.png · Damaged · 22 lost"
    assert text.spare_detail(spare, "page-2.png", 3) == (
        "Page 2 of 3 · page-2.png · spare",
        "1,031 blocks · 9 repaired · 22 lost",
        "Repairs: 9 one-bit, 0 two-bit, 0 three-bit",
        "Not in use: the page uses another scan",
    )


def test_replace_rejected_says_what_the_scan_is():
    def scan(info, reason=""):
        return ScanView(4, "/x/new.png", "done", info, None, reason)

    other = ScanInfo(A, 1, 1, "other.tar", make_tag(b"x"))
    assert text.replace_rejected(2, Fit.OTHER_DOCUMENT, scan(other)) == (
        "new.png was not used for page 2: it is page 1 of another printout, "
        "other.tar · A4 · 1 page."
    )
    mine = ScanInfo(A, 3, 1, "doc.tar", None)
    assert text.replace_rejected(2, Fit.OTHER_PAGE, scan(mine)) == (
        "new.png was not used for page 2: it is page 1 of this document and is listed there."
    )
    assert text.replace_rejected(2, Fit.UNUSABLE, scan(mine, "decoding failed")) == (
        "new.png was not used for page 2: it could not be read (decoding failed), "
        "so page 2 keeps the scan it has."
    )
    assert text.replace_rejected(2, Fit.UNUSABLE, scan(mine)) == (
        "new.png was not used for page 2: it could not be read, "
        "so page 2 keeps the scan it has."
    )
    from optar_gui.document import FORMAT_MISMATCH

    assert text.unreadable_reason(FORMAT_MISMATCH) == (
        "This scan was decoded for a different paper size than the document"
    )
    assert text.replace_rejected(2, Fit.UNREADABLE, scan(None, "label unreadable")) == (
        "new.png was not used for page 2. "
        "The label at the bottom of the page could not be read."
    )
    assert text.replace_rejected(1_205, Fit.UNREADABLE, scan(None, "bad file.")) == (
        "new.png was not used for page 1,205. bad file."
    )


def test_action_captions_and_dialog_wording():
    for caption in (text.REPLACE_SCAN, text.USE_SPARE, text.SWITCH_DOCUMENT,
                    text.ASSIGN_PAGE, text.START_BY_HAND, text.REPLACE_REJECTED_TITLE,
                    text.ASSIGN_TITLE, text.PAGE_FIELD, text.START_BY_HAND_TITLE,
                    text.START_BY_HAND_PROMPT, text.TOTAL_FIELD):
        assert caption.strip()
    assert text.replace_title(1_205) == "Choose a scan of page 1,205"
    assert text.assign_prompt("scan 7.png") == "Which page of this document is scan 7.png?"
    assert text.of_pages(1_205) == " of 1,205"


def test_replace_rejected_for_a_scan_on_another_page_without_a_label():
    unlabelled = ScanView(4, "/x/new.png", "done", None, None, "")
    assert text.replace_rejected(1, Fit.OTHER_PAGE, unlabelled, other_page=2) == (
        "new.png was not used for page 1: it is page 2 of this document and is listed there."
    )
    assigned = ScanView(4, "/x/new.png", "done", None, None, "label unreadable")
    assert text.replace_rejected(2, Fit.OTHER_PAGE, assigned, other_page=5) == (
        "new.png was not used for page 2: it is page 5 of this document and is listed there."
    )
    # The page it is on, when given, wins over what its label says.
    labelled = ScanView(4, "/x/new.png", "done", ScanInfo(A, 3, 1, "doc.tar", None), None, "")
    assert text.replace_rejected(2, Fit.OTHER_PAGE, labelled, other_page=3).endswith(
        "it is page 3 of this document and is listed there."
    )


def test_replace_rejected_never_gives_an_empty_reason():
    for fit in (Fit.UNREADABLE, Fit.UNUSABLE, Fit.OTHER_DOCUMENT, Fit.PENDING):
        message = text.replace_rejected(2, fit, ScanView(4, "/x/new.png", "done", None, None, ""))
        assert ". ." not in message and not message.endswith(": .")
        assert "could not be read" in message


def test_putting_on_paper_choices_and_summary():
    assert text.dot_size_label("xlarge", 200) == "Extra large (scan at 200 dpi)"
    assert text.dot_size_label("standard", 600) == "Standard (scan at 600 dpi)"
    assert [text.protection_label(p) for p in ("none", "standard", "high")] == [
        "None", "Standard", "High"]
    assert text.print_summary(12, 2_000_000, 1, True) == (
        "12 pages · 2,000,000 bytes · can lose 1 page of 12")
    assert text.print_summary(40, 9_000_000, 3, True).endswith(" · can lose 3 pages of 40")
    assert text.print_summary(1, 10, 0, True) == f"1 page · 10 bytes · {text.DAMAGE_REPAIRED}"
    assert text.print_summary(0, 0, 0, False) == "1 page · 0 bytes"
    for words in (text.DOTS_FIELD, text.PROTECT_FIELD, text.COMPATIBLE, text.DAMAGE_REPAIRED,
                  text.print_summary(12, 1, 1, True)):
        assert "parity" not in words.lower() and "container" not in words.lower()


def test_too_large_gives_the_reason_and_the_limit():
    from optar_gui.work import TOO_LARGE_TO_PROTECT, TOO_MANY_PAGES

    protect = text.too_large(TOO_LARGE_TO_PROTECT, 1_343)
    assert "protect" in protect and "at most 1,343 pages" in protect
    pages = text.too_large(TOO_MANY_PAGES, 9_999)
    assert "protect" not in pages and "at most 9,999 pages" in pages


# --- Version-1 documents and coarse scans -----------------------------------------

JARGON = ("parity", "codeword", "container", "header")


def unwrapped(**kw):
    from optar.container import Unwrapped

    fields = dict(
        data=b"file", best_effort=b"file", name="doc.bin", verified=True,
        repaired_bytes=1234, worst_used=18, budget=32, failed=0, page_damage={}, missing=(),
    )
    fields.update(kw)
    return Unwrapped(**fields)


def plain(message):
    assert not any(word in message.lower() for word in JARGON), message
    return message


def test_coarse_scan_for_a_known_page():
    from optar import get_layout

    large = get_layout("a4", "large")
    message = plain(text.coarse_scan(286.4, large))
    assert "about 290 dpi" in message and "300 dpi" in message
    assert plain(text.coarse_scan(196, get_layout("a4"))) == (
        "Scanned too coarsely for this page: about 200 dpi. Scan it at 600 dpi."
    )


def test_coarse_scan_of_an_unreadable_scan_lists_every_dot_size():
    message = plain(text.coarse_scan(203.0, None))
    assert message == (
        "Scanned at about 200 dpi, which is too coarse to read. Scan at 600 dpi for "
        "Standard dots, 450 Medium, 360 Big, 300 Large, 200 Extra large."
    )
    assert "page" not in message  # any image with an outline gets an estimate


def test_repair_line_states_bytes_repaired_and_the_worst_use():
    line = plain(text.repair_line(unwrapped()))
    assert "1,234 bytes" in line and "18 of 32" in line
    assert "1 byte " in plain(text.repair_line(unwrapped(repaired_bytes=1)))
    over = plain(text.repair_line(unwrapped(data=None, verified=False, worst_used=33, failed=4)))
    assert "33 of 32" in over and "too much" in over
    # Whatever it says, it never claims the file is right: only the fingerprint does.
    for u in (unwrapped(), unwrapped(verified=False, failed=0, worst_used=0)):
        assert "verified" not in text.repair_line(u).lower()
        assert "correct" not in text.repair_line(u).lower()


def test_repair_line_without_protection():
    line = plain(text.repair_line(unwrapped(budget=0, worst_used=0, repaired_bytes=0)))
    assert "of 0" not in line and "without protection" in line
    failed = unwrapped(budget=0, worst_used=1, failed=3, data=None, verified=False)
    assert "without protection" in plain(text.repair_line(failed))


def test_rescan_advice_names_the_most_damaged_pages():
    u = unwrapped(data=None, verified=False, failed=5, worst_used=40,
                  page_damage={1: 5, 2: 50, 3: 20, 4: 10, 6: 20})
    advice = plain(text.rescan_advice(u))
    assert "pages 2, 3 and 6" in advice  # most damage first, ties by page
    assert "page 4" not in advice and "page 1" not in advice
    one = plain(text.rescan_advice(unwrapped(data=None, page_damage={7: 3})))
    assert "rescan page 7" in one


def test_rescan_advice_asks_for_missing_pages_first():
    u = unwrapped(data=None, verified=False, failed=9, worst_used=99,
                  page_damage={3: 400, 4: 400, 5: 12}, missing=(3, 4))
    advice = plain(text.rescan_advice(u))
    assert "pages 3 and 4" in advice and "rescan page 5" in advice
    assert advice.index("pages 3 and 4") < advice.index("page 5")
    assert plain(text.rescan_advice(unwrapped(data=None)))  # nothing to name: still says it


def v1_summary(state, repair=None, missing_pages=(), error="", protection=32):
    return S(state, 3, 0, 0, 0, len(missing_pages), 49119, protection, missing_pages,
             repair, error)


def test_summary_line_of_version1_documents():
    u = unwrapped()
    assert text.summary_line(v1_summary(D.VERIFIED, u)) == (
        f"Verified · 49,119 bytes · {text.repair_line(u)}"
    )
    recoverable = plain(text.summary_line(v1_summary(D.RECOVERABLE, u, (3,))))
    assert recoverable.startswith("Recoverable: page 3 missing")
    assert text.repair_line(u) in recoverable
    waiting = plain(text.summary_line(v1_summary(D.RECOVERABLE, None, (3, 7))))
    assert waiting.startswith("Recoverable: pages 3 and 7 missing")
    assert "verified" not in waiting.lower()
    bad = unwrapped(data=None, verified=False, failed=2, worst_used=40, page_damage={2: 9})
    failed = plain(text.summary_line(v1_summary(D.INCOMPLETE, bad)))
    assert text.rescan_advice(bad) in failed and "verified" not in failed.lower()
    mismatch = unwrapped(verified=False)
    assert text.summary_line(v1_summary(D.MISMATCH, mismatch)).startswith(
        "Does not match the fingerprint on the paper"
    )
    error = text.summary_line(v1_summary(D.INCOMPLETE, None, error="ValueError: <b>x</b>"))
    assert error == text.repair_failed("ValueError: <b>x</b>")
    assert "<b>x</b>" in error


def test_save_warning_of_a_version1_document_is_about_what_its_repair_gave():
    # A further scan may be being read (the state is then WORKING) while the
    # result for the pages in use stands: saving writes that result.
    doc = Document()
    bad = unwrapped(data=None, verified=False, failed=2, worst_used=40, page_damage={2: 9})
    for state in (D.INCOMPLETE, D.WORKING):
        warning = text.save_warning(doc, v1_summary(state, bad))
        assert warning.startswith(text.rescan_advice(bad))
        assert "could not be fully repaired" in warning
        assert warning.endswith("may contain wrong parts.")
    for state in (D.VERIFIED, D.RECOVERABLE, D.WORKING):
        assert text.save_warning(doc, v1_summary(state, unwrapped())) is None
    for state in (D.MISMATCH, D.WORKING):
        warning = text.save_warning(doc, v1_summary(state, unwrapped(verified=False)))
        assert warning.startswith("The recovered file does not match the fingerprint")


def test_missing_pages_are_named_in_runs_and_counted_past_ten():
    line = text.summary_line(v1_summary(D.RECOVERABLE, None, (2, 3, 4, 7, 8, 12)))
    assert line.startswith("Recoverable: pages 2-4, 7, 8 and 12 missing")
    many = text.summary_line(v1_summary(D.RECOVERABLE, None, tuple(range(1, 40, 2))))
    assert "pages 1, 3, 5, 7, 9, 11, 13, 15, 17, 19 and 10 more missing" in many


def test_repairing_and_paper_names_of_version1_documents():
    from optar import get_layout

    plain(text.REPAIRING)
    assert text.paper_name(get_layout("a4", "large").fmt.to_string()) == "A4, Large dots"
    assert text.paper_name(get_layout("letter", "xlarge").fmt.to_string()) == (
        "US Letter, Extra large dots"
    )
    assert text.paper_name(A) == "A4"
