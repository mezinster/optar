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
    Progress,
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
        (S(D.VERIFIED, 4, 1, 0, 0, 0, 2481152), "File recovered and verified · 2,481,152 bytes"),
        (S(D.VERIFIED, 1, 0, 0, 0, 0, 1), "File recovered and verified · 1 byte"),
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
    assert text.DAMAGE_REPAIRED.endswith("losing a whole page loses the file")
    assert "C tool" not in text.COMPATIBLE and "0.2" in text.COMPATIBLE
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
    assert "It fits" not in protect and "It fits" not in pages  # nothing else would take it
    assert (TOO_MANY_PAGES, TOO_LARGE_TO_PROTECT) == (
        text.TOO_MANY_PAGES, text.TOO_LARGE_TO_PROTECT)


def test_too_large_names_the_choices_that_would_take_the_file():
    base = text.too_large(text.TOO_LARGE_TO_PROTECT, 1_343)
    assert text.too_large(text.TOO_LARGE_TO_PROTECT, 1_343, True) == (
        f"{base} It fits without protection.")
    pages = text.too_large(text.TOO_MANY_PAGES, 9_999)
    assert text.too_large(text.TOO_MANY_PAGES, 9_999, False, "big") == (
        f"{pages} It fits with Big dots.")
    assert text.too_large(text.TOO_MANY_PAGES, 9_999, True, "medium") == (
        f"{pages} It fits without protection, or with Medium dots.")


def test_name_warning_of_pages_that_identify_themselves():
    old = text.name_warning("é", True)
    assert old == (
        "These characters are not in the label font and are not printed: é. The name is "
        "too long for the page and is cut. The printed name is what identifies the pages later."
    )
    new = text.name_warning("é", True, stored=True)
    assert new.startswith(old[: old.index(" The printed name")])
    assert new.endswith("The pages do not need it: the full name is kept with the file.")
    assert "identifies" not in new
    none = text.name_warning("é", True, stored=True, printed=False)
    assert none == (
        "The label of this dot size has no room for the name, so it is not printed. "
        "The pages do not need it: the full name is kept with the file."
    )
    assert text.name_warning("", False, stored=True) is None
    assert text.name_warning("", False, stored=True, printed=False) is None
    # A name of characters the font lacks prints nothing either, for that reason.
    assert text.name_warning("от", False, stored=True, printed=False) == (
        "These characters are not in the label font and are not printed: о т. "
        "The pages do not need it: the full name is kept with the file."
    )


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
        f"File recovered and verified · 49,119 bytes · {text.repair_line(u)}"
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


def test_a_page_repaired_by_the_protection_does_not_read_as_damaged():
    p = page(7, Health.DAMAGED, repaired=27233, lost=121, histogram=(49249, 21441, 4994, 798))
    assert text.health_label(p) == "Damaged · 121 lost"
    assert text.health_label(p, restored=True) == "Repaired · 121 by the document's protection"
    assert text.page_row(p, restored=True) == (
        "Page 7 · Repaired · 121 by the document's protection"
    )
    assert text.detail_text(p, "s.png", 7, restored=True)[1] == (
        "76,603 blocks · 27,233 repaired · 121 repaired by the document's protection"
    )
    assert text.detail_text(p, "s.png", 7)[1] == "76,603 blocks · 27,233 repaired · 121 lost"
    clean = page(1, Health.GOOD, histogram=(10, 0, 0, 0))
    assert text.detail_text(clean, "s.png", 7, restored=True)[1] == (
        "10 blocks · 0 repaired · 0 lost"
    )


@pytest.mark.parametrize("used,budget,want", [
    (0, 64, "the worst spot used 0% of its repair capacity (0 of 64): a wide margin"),
    (11, 64, "the worst spot used 18% of its repair capacity (11 of 64): a wide margin"),
    (32, 64, "the worst spot used 50% of its repair capacity (32 of 64): a wide margin"),
    (33, 64, "the worst spot used 52% of its repair capacity (33 of 64): a moderate margin"),
    (52, 64, "the worst spot used 82% of its repair capacity (52 of 64): close to the limit"),
    (63, 64, "the worst spot used 99% of its repair capacity (63 of 64): close to the limit"),
    (64, 64, "the worst spot used 100% of its repair capacity (64 of 64): close to the limit"),
])
def test_margin_line_says_how_close_the_repair_came_to_failing(used, budget, want):
    assert text.margin_line(used, budget) == want


# --- The slower reader for coarse scans --------------------------------------------


def slow_page(number=2, corrected=265_112, dots=3_196_368):
    return PageView(number, Health.GOOD, 1, (), 0, 0, (0, 0, 0, 0), slow=True,
                    dots=dots, corrected_dots=corrected)  # fmt: skip


def test_a_page_read_by_the_slower_reader_counts_its_corrected_dots():
    p = slow_page(3)
    # Before the document is verified: the dots that reader corrected.
    row = "Page 3 · Read by the slower reader · 265,112 dots corrected"
    assert text.page_row(p) == row
    assert text.page_row(p, restored=True) == row  # no figure from the repair given
    assert text.health_label(p) == "Read by the slower reader · 265,112 dots corrected"
    lines = text.detail_text(p, "coarse.png", 3)
    assert lines[0] == "Page 3 of 3 · coarse.png"
    assert lines[1] == "Read by the slower reader for coarse scans."
    assert lines[2] == "Dots corrected within the page: 265,112 of 3,196,368 (8.3%)."
    assert "once the document is verified" in lines[3]
    for line in lines[1:]:
        plain(line)
    # Neither good nor blocks: that reader decides symbols, not blocks, and finds
    # none beyond repair.
    detail = " ".join(lines[1:]).lower()
    assert "good" not in detail and "block" not in detail and "lost" not in detail
    assert text.spare_row(p, "coarse.png") == (
        "    Spare · coarse.png · Read by the slower reader · 265,112 dots corrected"
    )
    # An ordinary page is unchanged.
    assert text.health_label(page(1, Health.GOOD)) == "Good"


def test_a_slow_page_once_verified_says_how_many_bytes_the_protection_repaired():
    p = slow_page(3)
    assert text.page_row(p, True, 6912) == (
        "Page 3 · Read by the slower reader · 265,112 dots corrected"
        " · 6,912 bytes repaired by the document's protection"
    )
    lines = text.detail_text(p, "coarse.png", 3, restored=True, repaired_bytes=6912)
    assert lines[1:] == (
        "Read by the slower reader for coarse scans.",
        "Dots corrected within the page: 265,112 of 3,196,368 (8.3%).",
        "After verification: 6,912 of this page's bytes were wrong and were repaired "
        "by the document's protection.",
    )
    assert "by the document's protection" in text.health_label(p, True, 1)
    assert text.health_label(p, True, 1).endswith("1 byte repaired by the document's protection")
    assert text.detail_text(p, None, 3, repaired_bytes=1)[-1] == (
        "After verification: 1 of this page's bytes was wrong and was repaired by the "
        "document's protection."
    )
    # Nothing to repair: the row says nothing more, the detail says so.
    assert text.page_row(p, True, 0) == text.page_row(p)
    assert text.detail_text(p, None, 3, repaired_bytes=0)[-1] == (
        "After verification: none of this page's bytes were wrong."
    )


def test_the_corrected_share_of_a_slow_page_is_shown_sensibly():
    def share(corrected, dots):
        return text.detail_text(slow_page(1, corrected, dots), None, 1)[2]

    assert share(1, 1) == "Dots corrected within the page: 1 of 1 (100.0%)."
    assert share(0, 1000) == "Dots corrected within the page: 0 of 1,000 (0.0%)."
    assert share(1, 1_000_000) == "Dots corrected within the page: 1 of 1,000,000 (under 0.1%)."
    assert share(5, 0) == "Dots corrected within the page: 5."
    assert text.page_row(slow_page(1, 1, 9)) == (
        "Page 1 · Read by the slower reader · 1 dot corrected"
    )


def test_a_slow_page_does_not_hide_that_it_is_unreadable_or_missing():
    p = PageView(2, Health.UNREADABLE, 1, (), 0, 0, None, "label unreadable", slow=True)
    assert text.health_label(p) == "Not readable"


def test_a_coarse_scan_being_read_says_it_takes_about_a_minute():
    scan = ScanView(4, "/scans/coarse.png", "working", None, None, "")
    for progress in (Progress("slow-sample", 0, 1, 0.3), Progress("slow-fit", 2, 5, 0.6)):
        detail = text.being_read_detail(scan, progress)
        assert detail[0] == "coarse.png"
        assert "about a minute" in plain(detail[-1])
        assert "coarse scan" in detail[-1] and "slower reader" in detail[-1]
    # An ordinary reading says nothing of the kind.
    detail = text.being_read_detail(scan, Progress("find", 0, 1, 0.1))
    assert detail == ("coarse.png", "Finding the page.")
    assert text.being_read_detail(scan, None) == ("coarse.png", "Waiting.")


def test_the_steps_of_a_scan_being_read():
    def step(key, done=0, of=1):
        return text.step_text(Progress(key, done, of, 0.5))

    assert text.step_text(None) == text.WAITING == "Waiting"
    assert step("open") == "Opening the file"
    assert step("find") == "Finding the page"
    assert step("identify", 3, 12) == "Identifying the page"
    assert step("read") == "Reading the data"
    assert step("slow-sample", 2, 9) == "Slower reader: sampling"
    assert step("slow-fit", 0, 5) == "Slower reader: pass 1 of 5"
    assert step("slow-fit", 3, 5) == "Slower reader: pass 4 of 5"
    assert step("slow-fit", 5, 5) == "Slower reader: pass 5 of 5"
    for key in ("open", "find", "identify", "read", "slow-sample", "slow-fit"):
        plain(step(key))
    plain(text.BEING_READ_SECTION)
    # A step with no words of its own is not passed off as another.
    assert step("something-new") == "Working"


def step_constants():
    """Every STEP_ constant the readers and the work define: (name, key)."""
    import optar.identify
    import optar_gui.work as work

    found = {}
    for module in (optar.identify, work):
        for name in dir(module):
            if name.startswith("STEP_") and isinstance(getattr(module, name), str):
                found[name] = getattr(module, name)
    return found


def test_every_step_the_readers_report_has_its_words():
    constants = step_constants()
    assert {"STEP_OPEN", "STEP_READ", "STEP_FIND", "STEP_IDENTIFY", "STEP_SLOW_SAMPLE",
            "STEP_SLOW_FIT"} <= set(constants)  # fmt: skip
    keys = set(constants.values())
    words = {text.step_text(Progress(k, 0, 1, 0.0)) for k in keys}
    assert len(words) == len(keys)
    assert text.WAITING not in words and "Working" not in words


def test_the_row_of_a_scan_being_read_is_its_name_and_step():
    assert text.being_read_row("scan-3.png", None) == "scan-3.png · Waiting"
    row = text.being_read_row("<b>scan</b>.png", Progress("slow-fit", 3, 5, 0.7))
    assert row == "<b>scan</b>.png · Slower reader: pass 4 of 5"


def test_the_bar_counts_the_scans_read_while_scans_are_being_read():
    assert text.reading_line(3, 6) == "Working… 3 of 6 scans read"
    assert text.reading_line(1, 1) == "Working… 0 of 1 scan read"
    assert text.reading_line(1, 1205) == "Working… 1,204 of 1,205 scans read"
    # With nothing else to say, the count alone.
    for state in (D.EMPTY, D.WORKING):
        s = S(state, 1, 0, 0, 0, 0, 9, reading=3, batch=6)
        assert text.summary_line(s) == "Working… 3 of 6 scans read"
    assert text.summary_line(S(D.WORKING, 1, 0, 0, 0, 1, 9)) == "Working…"


def test_the_bar_keeps_the_documents_state_and_adds_the_count_while_scans_are_read():
    from dataclasses import replace

    count = " · 3 of 6 scans read"
    damaged = unwrapped(data=None, verified=False, failed=3, page_damage={2: 900},
                        worst_used=40, budget=32)  # fmt: skip
    states = [
        S(D.VERIFIED, 2, 0, 0, 0, 0, 1234, protection=32, repair=unwrapped()),
        S(D.VERIFIED, 2, 0, 0, 0, 0, 9),
        S(D.CHECKING, 2, 0, 0, 0, 0, 9),
        S(D.MISMATCH, 2, 0, 0, 0, 0, 9),
        S(D.MISMATCH, 2, 0, 0, 0, 0, 9, protection=32, repair=unwrapped(verified=False)),
        S(D.RECOVERABLE, 2, 0, 0, 0, 1, 9, protection=32, missing_pages=(3,)),
        S(D.INCOMPLETE, 2, 0, 0, 0, 1, 9, protection=32, repair_error="out of memory"),
        S(D.INCOMPLETE, 1, 0, 0, 0, 1, 9, protection=32, missing_pages=(2,), repair=damaged),
        S(D.INCOMPLETE, 5, 1, 0, 0, 1, 9),
        S(D.UNVERIFIABLE, 2, 0, 0, 0, 0, None),
    ]
    for s in states:
        alone = text.summary_line(s)
        assert alone and not alone.startswith("Working")
        assert text.summary_line(replace(s, reading=3, batch=6)) == alone + count
    verified = text.summary_line(replace(states[0], reading=3, batch=6))
    assert verified.startswith("File recovered and verified · ") and verified.endswith(count)
    # The lines the window makes itself (a failed check, a repair running) too.
    s = replace(states[2], reading=1, batch=2)
    assert text.with_reading(text.REPAIRING, s) == f"{text.REPAIRING} · 1 of 2 scans read"
    assert text.with_reading(text.REPAIRING, states[2]) == text.REPAIRING


def test_an_unreadable_coarse_scan_says_the_slower_reader_was_tried():
    tried = plain(text.coarse_scan(203.0, None, slow_tried=True))
    assert tried.startswith(text.coarse_scan(203.0, None) + " ")
    assert "too coarse to read" in tried and "slower reader" in tried and "tried" in tried
    assert "slower reader" not in text.coarse_scan(203.0, None)


def test_a_verified_document_of_slow_pages_still_reads_verified():
    s = Summary(DocState.VERIFIED, 2, 0, 0, 0, 0, 1234, protection=32, repair=unwrapped())
    assert text.summary_line(s).startswith("File recovered and verified")


def test_summary_line_does_not_call_slow_read_pages_good():
    from dataclasses import replace

    s = S(D.INCOMPLETE, 5, 1, 0, 0, 1, 9)
    assert text.summary_line(s) == "6 of 7 pages good (1 repaired) · 1 missing"
    assert text.summary_line(replace(s, slow=2)) == (
        "4 of 7 pages good (1 repaired) · 2 read by the slower reader · 1 missing"
    )
    every = replace(S(D.INCOMPLETE, 6, 0, 0, 0, 0, 9), slow=6)
    assert text.summary_line(every) == "0 of 6 pages good · 6 read by the slower reader"


# --- The wording through the catalogue --------------------------------------------

# Every public string constant of text.py as it was before its wording moved into
# the catalogue: the English must not change by a byte.
ENGLISH_CONSTANTS = {
    'ACTUAL_SIZE': 'Print at actual size (100%), not "fit to page".',
    'ADD_SCANS': '+ Add scans…',
    'ADD_SCANS_TITLE': 'Add scans',
    'ASSIGN_PAGE': 'Assign to page…',
    'ASSIGN_TITLE': 'Assign to a page',
    'BEING_READ_SECTION': 'Being read',
    'CHOOSE_FILE': 'Choose…',
    'CHOOSE_FILE_TITLE': 'Choose a file to put on paper',
    'COMPATIBLE': 'Compatible with optar 0.2 and the original optar',
    'CONFIRM_SAVE_TITLE': 'Save anyway?',
    'CREATE_PDF': 'Create PDF…',
    'CREATE_TITLE': 'Save the PDF',
    'CREATING': 'Creating the PDF…',
    'DAMAGE_REPAIRED': 'damage within pages is repaired, but losing a whole page loses the file',
    'DEST_IS_SOURCE': 'the PDF would replace the file being put on paper; choose another name',
    'DOTS_FIELD': 'Dot size:',
    'ERROR_TITLE': 'Could not save',
    'FILE_FIELD': 'File:',
    'NAME_FIELD': 'Name:',
    'NOT_PART_OF_THIS_FILE': 'Not part of this file',
    'NOT_READABLE': 'Not readable',
    'NO_NAME': '(no name)',
    'NO_PAGE_DATA': 'The data of this page could not be read',
    'PAGE_FIELD': 'Page:',
    'PAPER_FIELD': 'Paper:',
    'PDF_FILTER': 'PDF (*.pdf);;All files (*)',
    'PREPARING': 'Reading the file…',
    'PREVIEW_LOADING': 'Loading…',
    'PRINTS_AS_FIELD': 'Prints as:',
    'PROTECT_FIELD': 'Protection:',
    'READING_COARSE': 'Reading a coarse scan with the slower reader; this takes about a minute',
    'READ_SLOWLY': 'Read by the slower reader for coarse scans',
    'READ_SLOWLY_ROW': 'Read by the slower reader',
    'READ_TAB': 'Read from paper',
    'REMOVE_SCAN': 'Remove',
    'REPAIRING': 'Repairing and checking the fingerprint…',
    'REPLACE_REJECTED_TITLE': 'Scan not used',
    'REPLACE_SCAN': 'Replace scan…',
    'SAVE_AFTER_CLOSE': 'the window has been closed, so nothing more can be saved',
    'SAVE_FILE': 'Save file…',
    'SAVE_RUNNING': 'a save is already running',
    'SAVE_TITLE': 'Save the recovered file',
    'SLOW_TRIED': 'The slower reader for coarse scans was tried too, and could not read it.',
    'START_BY_HAND': 'Start a document by hand…',
    'START_BY_HAND_PROMPT': (
        'No scan could be identified. Give the paper and the number of pages of the '
        'printout, then assign each scan to its page.'
    ),
    'START_BY_HAND_TITLE': 'Start a document by hand',
    'STILL_WRITING': (
        'A file is still being written. Wait until it is finished? If you close now, '
        'it may not be written.'
    ),
    'STILL_WRITING_TITLE': 'Still writing a file',
    'SWITCH_DOCUMENT': 'Switch to this document',
    'TOO_LARGE_TO_PROTECT': 'too large to protect',
    'TOO_MANY_PAGES': 'too many pages',
    'TOTAL_FIELD': 'Pages:',
    'USE_SPARE': 'Use this scan',
    'VERIFIED': 'File recovered and verified',
    'WAITING': 'Waiting',
    'WINDOW_TITLE': 'optar',
    'WORKING': 'Working…',
    'WRITE_TAB': 'Put on paper',
}


def test_english_constants_are_unchanged():
    assert {name: getattr(text, name) for name in ENGLISH_CONSTANTS} == ENGLISH_CONSTANTS


def test_text_module_does_not_load_numpy():
    import subprocess
    import sys

    code = "import sys, optar_gui.text; print('numpy' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"


def test_constants_follow_the_language(catalogues):
    from optar import i18n

    catalogues.add("ru", {"gui": {"READ_TAB": "Чтение"}})
    i18n.set_language("ru")
    assert text.READ_TAB == "Чтение"
    assert text.WRITE_TAB == "Put on paper"  # a key the language lacks: English
    i18n.set_language("en")
    assert text.READ_TAB == "Read from paper"


def test_unknown_constant_is_an_attribute_error():
    with pytest.raises(AttributeError):
        text.NO_SUCH_NAME  # noqa: B018
    with pytest.raises(AttributeError):
        text.no_such_function  # noqa: B018
    assert not hasattr(text, "_PRIVATE")


def test_a_broken_constant_translation_names_its_key(catalogues):
    from optar import i18n

    catalogues.add("ru", {"gui": {"READ_TAB": "Чтение {oops}"}})
    i18n.set_language("ru")
    try:
        with pytest.raises(KeyError, match="gui.READ_TAB"):
            text.READ_TAB  # noqa: B018
    finally:
        i18n.set_language("en")


def test_a_broken_name_translation_names_its_key(catalogues):
    from optar import i18n

    catalogues.add("ru", {"gui": {"button": {"ok": "ОК {oops}"}}})
    i18n.set_language("ru")
    try:
        with pytest.raises(KeyError, match="gui.button.ok"):
            text.button("ok")
        assert text.button("odd") == "odd"  # a name the catalogues lack
    finally:
        i18n.set_language("en")


def test_a_share_uses_the_languages_decimal_separator(catalogues):
    from optar import i18n

    catalogues.add("it", {"language": {"name": "Italiano"},
                          "format": {"group": ".", "decimal": ","}})  # fmt: skip
    i18n.set_language("it")
    try:
        line = text.detail_text(slow_page(1, 83, 1000), None, 1)[2]
        assert "(8,3%)" in line
    finally:
        i18n.set_language("en")


def test_error_text_shows_a_library_error_in_the_language(catalogues):
    from optar import i18n
    from optar.errors import OptarError, error

    e = error(OptarError, "err.no_pages", "no pages to write")
    assert text.error_text(e) == "no pages to write"
    assert text.error_text(ValueError("x {y}")) == "x {y}"
    catalogues.add("ru", {"err": {"no_pages": "нет страниц"}})
    i18n.set_language("ru")
    try:
        assert text.error_text(e) == "нет страниц"
    finally:
        i18n.set_language("en")


def test_untrusted_names_with_braces():
    assert text.saved_message("/x/{0}.bin", 5) == "Saved 5 bytes to {0}.bin"
    assert "{name}.png" in text.assign_prompt("{name}.png")
    assert text.created_message("/x/{n}.pdf", 2) == "Created {n}.pdf · 2 pages"
    assert text.save_failed("{x} {0}") == "The file could not be saved: {x} {0}"
    assert text.unreadable_reason("odd {reason}") == "odd {reason}"


def test_buttons():
    names = ("ok", "cancel", "save", "yes", "no")
    assert [text.button(b) for b in names] == ["OK", "Cancel", "Save", "Yes", "No"]


def test_language_choice_wording():
    assert text.LANGUAGE_MENU == "Language"
    assert text.SYSTEM_LANGUAGE == "System default"


def test_every_paper_and_dot_size_has_its_words():
    from optar.format import DOT_SIZES, LAYOUTS, PAPERS

    assert text.paper_label("a5") == "a5"  # a name the window does not know
    for paper in PAPERS:
        assert text.paper_label(paper) != paper
    for (paper, _dots), layout in LAYOUTS.items():
        assert text.paper_name(layout.fmt.to_string()).startswith(text.paper_label(paper))
    base = text.too_large(text.TOO_MANY_PAGES, 9)
    for dots in DOT_SIZES:
        assert dots not in text.dot_size_label(dots, 600)
        for unprotected_fits in (False, True):
            fits = text.too_large(text.TOO_MANY_PAGES, 9, unprotected_fits, dots)
            assert fits.startswith(base + " ") and dots not in fits[len(base):]
    for protect in ("none", "standard", "high"):
        assert text.protection_label(protect) != protect


# Joiners of finished phrases: the only literals of text.py with a space that are
# not wording.
JOINERS = {" · ", "; ", " — ", " ", "    "}
# Codes compared by value (``work.PrintPlan.too_large``), never shown: they must
# not change with the language.
CODES = {"too many pages", "too large to protect"}


def test_text_source_holds_no_wording():
    import ast
    from pathlib import Path

    tree = ast.parse(Path(text.__file__).read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                docstrings.add(id(first.value))
    wording = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
        and " " in node.value
        and node.value not in JOINERS | CODES
    ]
    assert wording == []


# --- Templates other grammars can fill -------------------------------------------


def test_a_page_list_chooses_single_or_several_by_how_many_it_names(catalogues):
    """Not by the plural rule: in Russian the form for 1 also serves 21."""
    from optar import i18n

    catalogues.add("ru", {
        "language": {"name": "Русский"}, "format": {"group": " "},
        "gui": {
            "state": {"recoverable": {"single": "ОДНА {pages}", "several": "НЕСК {pages}"}},
            "rescan": {"add": {"single": "одна {pages}", "several": "неск {pages}"},
                       "advice": "{what}"},
        },
    })  # fmt: skip
    i18n.set_language("ru")
    try:
        assert text.summary_line(v1_summary(D.RECOVERABLE, None, (3,))) == "ОДНА 3"
        twenty_one = tuple(range(1, 43, 2))  # 21 pages, none in a row
        line = text.summary_line(v1_summary(D.RECOVERABLE, None, twenty_one))
        assert line.startswith("НЕСК 1, 3, ")
        assert text.rescan_advice(unwrapped(data=None, missing=twenty_one)).startswith("неск ")
        assert text.rescan_advice(unwrapped(data=None, missing=(21,))) == "одна 21"
    finally:
        i18n.set_language("en")


def test_a_range_of_pages_is_written_by_the_catalogue(catalogues):
    from optar import i18n

    assert plain(text.rescan_advice(unwrapped(data=None, missing=(2, 3, 4, 9)))).endswith(
        "add pages 2-4 and 9."
    )
    catalogues.add("ru", {"gui": {"list": {"range": "{first}–{last}"}}})
    i18n.set_language("ru")
    try:
        advice = text.rescan_advice(unwrapped(data=None, missing=(2, 3, 4, 9)))
        assert "2–4 and 9" in advice
    finally:
        i18n.set_language("en")


def test_a_sentence_ends_with_the_languages_full_stop(catalogues):
    from optar import i18n

    scan = ScanView(4, "/x/coarse.png", "working", None, None, "")
    catalogues.add("ka", {"gui": {"sentence": "{words}!", "rejected": {"unread": "Nope!"}}})
    i18n.set_language("ka")
    try:
        assert text.being_read_detail(scan, None) == ("coarse.png", "Waiting!")
        detail = text.being_read_detail(scan, Progress("slow-sample", 0, 1, 0.1))
        assert detail[-1].endswith("about a minute!")
        rejected = text.replace_rejected(2, Fit.UNREADABLE, scan)
        assert rejected.endswith("page 2. Nope!")  # already a sentence: not stopped twice
    finally:
        i18n.set_language("en")


def test_the_version_help_escapes_a_bare_percent_for_argparse(catalogues):
    from optar import i18n

    catalogues.add("ru", {"gui": {"cli": {"version_help": "100%"}}})
    i18n.set_language("ru")
    try:
        assert text.cli_version_help() == "100%%"
    finally:
        i18n.set_language("en")
    assert text.cli_version_help() == "print the version and exit"
