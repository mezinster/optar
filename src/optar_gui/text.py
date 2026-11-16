# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Every user-visible string of the application, so the widgets hold no wording.

Plain Python, no Qt and no numpy. Plain language: a "block" is one
error-correction codeword; blocks are "repaired" or "lost". Counts carry
thousands separators and agree in number with their noun.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from optar_gui.document import (
    SCAN_EXTENSIONS,
    DocState,
    Fit,
    GroupView,
    Health,
    PageView,
    ScanView,
    Summary,
)

if TYPE_CHECKING:
    from optar.container import Unwrapped
    from optar.format import Layout
    from optar_gui.document import Document

# Same wording as the command line's (optar.cli.ACTUAL_SIZE).
ACTUAL_SIZE = 'Print at actual size (100%), not "fit to page".'

# Titles of the sections of the list of scans.
NOT_PART_OF_THIS_FILE = "Not part of this file"
NOT_READABLE = "Not readable"

# The window, its tabs, buttons and dialogs.
WINDOW_TITLE = "optar"
READ_TAB = "Read from paper"
ADD_SCANS = "+ Add scans…"
REMOVE_SCAN = "Remove"
SAVE_FILE = "Save file…"
ADD_SCANS_TITLE = "Add scans"
SAVE_TITLE = "Save the recovered file"
CONFIRM_SAVE_TITLE = "Save anyway?"
ERROR_TITLE = "Could not save"

# The actions on the selected row and their dialogs.
REPLACE_SCAN = "Replace scan…"
USE_SPARE = "Use this scan"
SWITCH_DOCUMENT = "Switch to this document"
ASSIGN_PAGE = "Assign to page…"
START_BY_HAND = "Start a document by hand…"
REPLACE_REJECTED_TITLE = "Scan not used"
ASSIGN_TITLE = "Assign to a page"
PAGE_FIELD = "Page:"
START_BY_HAND_TITLE = "Start a document by hand"
START_BY_HAND_PROMPT = (
    "No scan could be identified. Give the paper and the number of pages of the "
    "printout, then assign each scan to its page."
)
TOTAL_FIELD = "Pages:"

# Asked when the window is closed while a file is being written.
STILL_WRITING_TITLE = "Still writing a file"
STILL_WRITING = (
    "A file is still being written. Wait until it is finished? If you close now, "
    "it may not be written."
)

# Why a save cannot start (programming errors, never shown in a dialog).
SAVE_RUNNING = "a save is already running"
SAVE_AFTER_CLOSE = "the window has been closed, so nothing more can be saved"

# The "Put on paper" tab.
WRITE_TAB = "Put on paper"
FILE_FIELD = "File:"
PAPER_FIELD = "Paper:"
NAME_FIELD = "Name:"
PRINTS_AS_FIELD = "Prints as:"
CHOOSE_FILE = "Choose…"
CHOOSE_FILE_TITLE = "Choose a file to put on paper"
CREATE_PDF = "Create PDF…"
CREATE_TITLE = "Save the PDF"
PDF_FILTER = "PDF (*.pdf);;All files (*)"
PREPARING = "Reading the file…"
CREATING = "Creating the PDF…"
# Why a PDF is not created over the file being put on paper.
DEST_IS_SOURCE = "the PDF would replace the file being put on paper; choose another name"
# The choices of how the file is put on paper.
DOTS_FIELD = "Dot size:"
PROTECT_FIELD = "Protection:"
COMPATIBLE = "Compatible with optar 0.2 and the C tool"

# What a document without a name is called.
NO_NAME = "(no name)"

# Paper names as the window shows them, by the paper's name in optar.format.
_PAPER_NAMES = {"a4": "A4", "letter": "US Letter"}

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
    "page count out of range": "The label's page count is not possible",
    "page size does not match this document": (
        "This scan is of a different paper size than the document"
    ),
    "decoded for another page format": (
        "This scan was decoded for a different paper size than the document"
    ),
}

# A save warning names at most this many runs of pages, then counts the rest.
MAX_RUNS = 10

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
    """The document's state for the bottom bar.

    For a version-1 document an accepted repair result adds what the repair did
    (``repair_line``); one that could not give the file says which pages to add
    or rescan (``rescan_advice``).
    """
    pages = s.good + s.repaired + s.damaged + s.unreadable + s.missing
    repair = s.repair
    if s.state == DocState.EMPTY:
        return ""
    if s.state == DocState.WORKING:
        return "Working…"
    if s.state == DocState.CHECKING:
        return "Checking the fingerprint…"
    if s.state == DocState.VERIFIED:
        line = f"Verified · {count(s.size, 'byte')}"
        return f"{line} · {repair_line(repair)}" if repair is not None else line
    if s.state == DocState.RECOVERABLE:
        missing = _page_numbers(s.missing_pages)
        if repair is None:
            return f"Recoverable: {missing} missing, can be repaired from the others"
        return (
            f"Recoverable: {missing} missing, repaired from the others · matches the "
            f"fingerprint · {count(s.size, 'byte')} · {repair_line(repair)}"
        )
    if s.state == DocState.MISMATCH:
        line = "Does not match the fingerprint on the paper"
        return f"{line} · {repair_line(repair)}" if repair is not None else line
    if s.repair_error:
        return repair_failed(s.repair_error)
    if repair is not None:
        return f"{rescan_advice(repair)} ({repair_line(repair)})"
    if s.state == DocState.UNVERIFIABLE:
        read = f"All {count(pages, 'page')}" if pages > 1 else count(pages, "page")
        return f"{read} read · cannot be verified (no tag)"
    good = f"{s.good + s.repaired:,} of {count(pages, 'page')} good"
    if s.repaired:
        good += f" ({s.repaired:,} repaired)"
    parts = [good]
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


def save_warning(doc: Document, summary: Summary | None = None) -> str | None:
    """What saving must confirm first; None when the file is verified.

    ``summary`` is the document's summary if the caller has it (it may be
    ``CHECKING``); otherwise ``doc.summary()`` is used, which may hash the file.
    A version-1 document whose repair could not give the file is saved as far as
    it was recovered, which may be wrong in parts.
    """
    s = summary if summary is not None else doc.summary()
    state = s.state
    if state == DocState.VERIFIED:
        return None
    if state == DocState.RECOVERABLE and s.repair is not None and s.repair.verified:
        return None  # repaired, and the fingerprint matches
    if state == DocState.INCOMPLETE and s.repair is not None and s.repair.data is None:
        return (
            f"{rescan_advice(s.repair)} If you save now, the saved file is only what "
            "could be recovered and may contain wrong parts."
        )
    if state == DocState.CHECKING:
        return (
            "The fingerprint is still being checked, so it is not yet known whether the "
            "recovered file is the original."
        )
    if state == DocState.EMPTY:
        return "There is nothing to save."
    if state == DocState.MISMATCH:
        return (
            "The recovered file does not match the fingerprint printed on the paper: "
            "some data was decoded wrongly, so this is not the original file."
        )
    if state == DocState.UNVERIFIABLE and doc.by_hand:
        return (
            "This document was put together by hand, so the file cannot be verified "
            "and will be padded with zeros to a whole page."
        )
    if state == DocState.UNVERIFIABLE:
        return (
            "These pages carry no tag, so the file cannot be verified and will be "
            "padded with zeros to a whole page."
        )
    runs = _runs(doc.pages())
    shown = [_run_text(*run) for run in runs[:MAX_RUNS]]
    rest = sum(last - first + 1 for first, last, _ in runs[MAX_RUNS:])
    if rest:
        shown.append(f"and {rest:,} more {'page' if rest == 1 else 'pages'} missing or damaged")
    return f"The saved file will be incomplete: {'; '.join(shown)}."


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
    """The detail panel's lines for one page of a document of ``pages`` pages.

    ``reason`` defaults to the page's own reason for being unreadable.
    """
    reason = reason or page.reason
    title = f"Page {page.number:,} of {pages:,}"
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


def by_hand_caution() -> str:
    return (
        "This document was put together by hand, so it cannot be confirmed that the "
        "pages belong to the same printout or that the file is complete. The saved "
        "file will be padded with zeros."
    )


def caution(doc: Document) -> str | None:
    """The standing caution over the current document, or None when it has a tag
    or is a version-1 document (its pages say what they are in their data)."""
    cur = doc.current
    if cur is None or cur.tag is not None or cur.header is not None:
        return None
    return by_hand_caution() if doc.by_hand else untagged_caution()


def paper_name(format: str) -> str:
    """The paper a page format string belongs to, with its dot size unless the dots
    are standard ("A4", "A4, Large dots"), or the string itself."""
    # Imported here: loading the optar package loads numpy, which importing this
    # module must not.
    from optar.format import LAYOUTS, PAPERS, PageFormat

    for key, paper in PAPERS.items():
        if PageFormat.for_paper(paper).to_string() == format:
            return _PAPER_NAMES.get(key, paper.name)
    for (key, dots), layout in LAYOUTS.items():
        if layout.fmt.to_string() == format:
            return f"{_PAPER_NAMES.get(key, key)}, {_DOT_NAMES.get(dots, dots)} dots"
    return format


def _group_line(group: GroupView) -> str:
    pages = max(group.total, 1)  # an empty file prints one page labelled 1/0
    name = group.title.rstrip(" ") or NO_NAME
    return f"{name} · {paper_name(group.format)} · {count(pages, 'page')}"


def document_title(group: GroupView) -> str:
    """The first row of the list: name, paper and page count."""
    return _group_line(group)


def page_row(page: PageView) -> str:
    return f"Page {page.number:,} · {health_label(page)}"


def other_group_row(group: GroupView) -> str:
    """A row under "Not part of this file": what the group says it is, and its scans."""
    return f"{_group_line(group)} · {count(len(group.scan_ids), 'scan')}"


def other_group_detail(group: GroupView) -> tuple[str, ...]:
    return (
        _group_line(group),
        f"{count(len(group.scan_ids), 'scan')} of another printout, not part of this file",
    )


def spare_row(page: PageView, scan_name: str) -> str:
    """A row under its page: a spare scan, shown with the health it would give."""
    return f"    Spare · {scan_name} · {health_label(page)}"


def spare_detail(page: PageView, scan_name: str, pages: int) -> tuple[str, ...]:
    """The detail panel for a spare; ``page`` is the page as it would be with it in use."""
    lines = detail_text(page, scan_name, pages)
    return (f"{lines[0]} · spare", *lines[1:], "Not in use: the page uses another scan")


def replace_title(page: int) -> str:
    return f"Choose a scan of page {page:,}"


def _sentence(words: str) -> str:
    words = words.rstrip()
    return words if words.endswith(".") else f"{words}."


def replace_rejected(
    page: int, fit: str, scan: ScanView, other_page: int | None = None
) -> str:
    """Why a scan chosen to replace ``page`` was not used; ``fit`` is a ``Fit``.

    ``other_page`` is the page of this document the scan is on, for ``OTHER_PAGE``
    (by default the page its label names).
    """
    name = os.path.basename(scan.path)
    info = scan.info
    if fit == Fit.UNUSABLE:
        why = f" ({unreadable_reason(scan.reason)})" if scan.reason else ""
        return (
            f"{name} was not used for page {page:,}: it could not be read{why}, "
            f"so page {page:,} keeps the scan it has."
        )
    if fit == Fit.OTHER_PAGE and (other_page is not None or info is not None):
        where = other_page if other_page is not None else info.page
        return (
            f"{name} was not used for page {page:,}: it is page {where:,} of this "
            "document and is listed there."
        )
    if fit == Fit.OTHER_DOCUMENT and info is not None:
        printout = (
            f"{info.name.rstrip(' ') or NO_NAME} · {paper_name(info.format)} · "
            f"{count(max(info.total, 1), 'page')}"
        )
        return (
            f"{name} was not used for page {page:,}: it is page {info.page:,} of another "
            f"printout, {printout}."
        )
    why = unreadable_reason(scan.reason) if scan.reason.strip() else "It could not be read"
    return f"{name} was not used for page {page:,}. {_sentence(why)}"


def assign_prompt(scan_name: str) -> str:
    return f"Which page of this document is {scan_name}?"


def of_pages(total: int) -> str:
    """After the page number in the page field: how many pages there are."""
    return f" of {total:,}"


def unreadable_row(scan: ScanView) -> str:
    return f"{os.path.basename(scan.path)} · {unreadable_reason(scan.reason)}"


def unreadable_detail(scan: ScanView) -> tuple[str, ...]:
    return (os.path.basename(scan.path), unreadable_reason(scan.reason))


def summary_bar(line: str, note: str) -> str:
    """The bottom bar: the document's state and, after a save, what was saved."""
    return f"{line} — {note}" if note else line


def saved_message(path: str, size: int) -> str:
    return f"Saved {count(size, 'byte')} to {os.path.basename(path)}"


def check_failed(message: str) -> str:
    """The bar when the fingerprint check itself failed (not a mismatch)."""
    return f"The fingerprint could not be checked: {message}"


def save_failed(message: str) -> str:
    return f"The file could not be saved: {message}"


def paper_label(paper: str) -> str:
    """A paper's name as the window shows it, by its name in optar.format."""
    return _PAPER_NAMES.get(paper, paper)


def file_info(total: int, size: int) -> str:
    """Pages and size of a file to put on paper; an empty file prints one page."""
    return f"{count(max(total, 1), 'page')} · {count(size, 'byte')}"


def name_warning(dropped: str, cut: bool) -> str | None:
    """Why the printed name differs from the name typed, or None when it does not."""
    parts = []
    if dropped:
        shown = " ".join(ch if ch.isprintable() else repr(ch)[1:-1] for ch in dropped)
        parts.append(f"These characters are not in the label font and are not printed: {shown}")
    if cut:
        parts.append("The name is too long for the page and is cut")
    if not parts:
        return None
    return ". ".join(parts) + ". The printed name is what identifies the pages later."


def not_regular_file(path: str) -> str:
    """Why a folder, a named pipe or a device is not read as a scan or a file to print."""
    return f"cannot read {path}: not a regular file (a folder, a pipe or a device)"


def file_unreadable(message: str) -> str:
    return f"The file could not be read: {message}"


def created_message(path: str, pages: int) -> str:
    return f"Created {os.path.basename(path)} · {count(max(pages, 1), 'page')}"


def create_failed(message: str) -> str:
    return f"The PDF could not be created: {message}"


def scan_filter() -> str:
    """The file dialog's filter for scans."""
    patterns = " ".join(f"*{ext}" for ext in SCAN_EXTENSIONS)
    return f"Scans ({patterns});;All files (*)"


PREVIEW_LOADING = "Loading…"


def size_changed() -> str:
    """The preview's reason when an image's size changed while it loaded."""
    return "the image's size changed while it was loading"


def preview_failed(message: str) -> str:
    """Shown in the preview instead of a scan it could not load."""
    return f"This scan cannot be shown: {message}"


def too_large_to_show(pixels: int, limit: int) -> str:
    return f"{pixels:,} pixels is more than the {limit:,} a scan may have"


# Dot sizes and protection levels as the window shows them, by their names in optar.format.
_DOT_NAMES = {
    "standard": "Standard",
    "medium": "Medium",
    "big": "Big",
    "large": "Large",
    "xlarge": "Extra large",
}
_PROTECTION_NAMES = {"none": "None", "standard": "Standard", "high": "High"}


def dot_size_label(dots: str, scan_dpi: int) -> str:
    """A dot size in its selector: its name and the scan resolution to use."""
    return f"{_DOT_NAMES.get(dots, dots)} (scan at {scan_dpi:,} dpi)"


def protection_label(protect: str) -> str:
    return _PROTECTION_NAMES.get(protect, protect)


def promise(promised: int, total: int) -> str:
    """How many of a protected printout's pages, any of them, may be lost
    without losing the file (``optar.container.pages_promised``)."""
    return f"can lose {count(promised, 'page')} of {total:,}"


DAMAGE_REPAIRED = "damage within pages is repaired, but no whole page may be lost"


def print_summary(total: int, size: int, promised: int, protected: bool) -> str:
    """Pages and size of a file to put on paper, and what its protection allows."""
    line = file_info(total, size)
    if promised > 0:
        return f"{line} · {promise(promised, total)}"
    if protected:
        return f"{line} · {DAMAGE_REPAIRED}"
    return line


def too_large(reason: str, limit: int) -> str:
    """Why a file cannot be put on paper with the chosen dot size and protection.

    ``reason`` is ``work.TOO_MANY_PAGES`` or ``work.TOO_LARGE_TO_PROTECT``;
    ``limit`` the most pages a printout of that kind may have.
    """
    # Imported here: the work module imports this one.
    from optar_gui.work import TOO_LARGE_TO_PROTECT

    if reason == TOO_LARGE_TO_PROTECT:
        return (
            "This file is too large to protect with this dot size: a protected "
            f"printout may have at most {count(limit, 'page')}."
        )
    return (
        "This file is too large to put on paper with these choices: a printout "
        f"may have at most {count(limit, 'page')}."
    )


# --- Documents that repair themselves, and coarse scans ---------------------------
#
# What the library calls parity, codewords and page headers is never named here:
# the window speaks of "protection", "repair" and the "fingerprint". Only the
# fingerprint proves the file is right; nothing below suggests otherwise.

# Why a page whose data says it repairs itself gave no data to repair with.
NO_PAGE_DATA = "The data of this page could not be read"

# The bar while a document is repaired and checked in the background.
REPAIRING = "Repairing and checking the fingerprint…"

# How many of the most damaged pages the advice after a failed repair names.
RESCAN_PAGES = 3


def _about_dpi(dpi: float) -> str:
    """A measured resolution, rounded to the nearest 10: scans measure a few
    percent off (a printout scaled to 95% reads 286 dpi at 300)."""
    return f"about {int(round(dpi / 10)) * 10:,} dpi"


def coarse_scan(scan_dpi: float, layout: Layout | None) -> str:
    """A scan made at too low a resolution: for an identified page of ``layout``,
    the resolution its dots need; for an unreadable scan (``layout`` None), the
    resolution every dot size needs."""
    if layout is not None:
        return (
            f"Scanned too coarsely for this page: {_about_dpi(scan_dpi)}. "
            f"Scan it at {layout.scan_dpi:,} dpi."
        )
    # Imported here: loading the optar package loads numpy.
    from optar.format import DOT_SIZES, PAPERS, get_layout

    paper = next(iter(PAPERS))
    needs = [(_DOT_NAMES.get(d, d), get_layout(paper, d).scan_dpi) for d in DOT_SIZES]
    first, rest = needs[0], needs[1:]
    listed = ", ".join([f"{first[0]} {first[1]:,} dpi", *(f"{n} {dpi:,}" for n, dpi in rest)])
    return (
        f"Scanned too coarsely to read: {_about_dpi(scan_dpi)}. Scan it at the "
        f"resolution its dots need: {listed}."
    )


def _and(items: list[str]) -> str:
    """``a``, ``a and b``, ``a, b and c``."""
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def _page_numbers(numbers: tuple[int, ...] | list[int], in_order: bool = True) -> str:
    """``page 3``, ``pages 3 and 7``, ``pages 2-4 and 9``. ``in_order`` sorts the
    numbers and joins runs; else they are named in the order given. At most
    ``MAX_RUNS`` items are named, then the pages left are counted."""
    numbers = list(dict.fromkeys(numbers))
    if not numbers:
        return "no pages"
    spans: list[tuple[int, int]] = []  # (first, last) of each item named
    if in_order:
        for n in sorted(numbers):
            if spans and spans[-1][1] == n - 1:
                spans[-1] = (spans[-1][0], n)
            else:
                spans.append((n, n))
        # Two pages in a row are named apart: "pages 3 and 4".
        spans = [s for a, b in spans for s in ([(a, a), (b, b)] if b == a + 1 else [(a, b)])]
    else:
        spans = [(n, n) for n in numbers]
    items = [f"{a:,}" if a == b else f"{a:,}-{b:,}" for a, b in spans[:MAX_RUNS]]
    rest = sum(b - a + 1 for a, b in spans[MAX_RUNS:])
    if rest:
        items.append(f"{rest:,} more")
    return f"page {items[0]}" if len(numbers) == 1 else f"pages {_and(items)}"


def repair_line(u: Unwrapped) -> str:
    """What repairing a document did: the bytes it repaired, and how much of its
    capacity the worst spot used (``worst_used`` of ``budget``)."""
    if u.budget == 0:
        return "Printed without protection, so nothing could be repaired"
    fixed = f"{count(u.repaired_bytes, 'byte')} repaired"
    if u.worst_used > u.budget:
        return (
            f"{fixed} · the worst spot needed {u.worst_used:,} of {u.budget:,}: "
            "too much to repair"
        )
    return f"{fixed} · the worst spot used {u.worst_used:,} of {u.budget:,} of its repair capacity"


def rescan_advice(u: Unwrapped) -> str:
    """After a repair that could not give the file: the missing pages to add, and
    the ``RESCAN_PAGES`` pages with the most damage to rescan."""
    missing = set(u.missing)
    worst = sorted(
        (p for p in u.page_damage if p not in missing), key=lambda p: (-u.page_damage[p], p)
    )[:RESCAN_PAGES]
    parts = []
    if missing:
        parts.append(f"add {_page_numbers(sorted(missing))}")
    if worst:
        which = "which has" if len(worst) == 1 else "which have"
        parts.append(f"rescan {_page_numbers(worst, in_order=False)}, {which} the most damage")
    advice = "The file could not be fully repaired."
    if not parts:
        return f"{advice} Rescanning the pages may still improve it."
    return f"{advice} Adding or rescanning pages can still improve it: {' and '.join(parts)}."


def repair_failed(reason: str) -> str:
    """The bar when repairing the pages itself failed (an error, not damage)."""
    return f"The pages could not be repaired: {reason}"
