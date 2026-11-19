# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Every user-visible string of the application, so the widgets hold no wording.

Plain Python, no Qt and no numpy. The wording itself lives in the catalogues
(``optar/locale/<language>.toml``, tables ``gui`` and ``count``); this module is
the window's one door to them. A constant such as ``text.READ_TAB`` is looked up
in the current language each time it is read. Templates are whole sentences or
whole phrases, and a count that changes their wording chooses a plural form;
only finished phrases are joined here (with " · ", "; " or " — ").

Plain language: a "block" is one error-correction codeword; blocks are
"repaired" or "lost". Counts carry the language's thousands separators and
agree in number with their noun.
"""

from __future__ import annotations

import logging
import math
import os
from typing import TYPE_CHECKING

from optar_gui.document import (
    COUNT_OUT_OF_RANGE,
    FORMAT_MISMATCH,
    LABEL_UNREADABLE,
    NO_PAGE,
    NOT_DECODABLE,
    OUT_OF_RANGE,
    SCAN_EXTENSIONS,
    SIZE_MISMATCH,
    DocState,
    Fit,
    GroupView,
    Health,
    PageView,
    Progress,
    ScanView,
    Summary,
)

if TYPE_CHECKING:
    from optar.container import Unwrapped
    from optar.format import Layout
    from optar_gui.document import Document

log = logging.getLogger(__name__)

# Loading the optar package loads numpy, which importing this module must not:
# optar.i18n (and the rest of optar) is imported inside the functions below.


def _t(key: str, /, **values: object) -> str:
    from optar import i18n

    return i18n.t(key, **values)


def _n(key: str, count: int, /, **values: object) -> str:
    """A plural entry: the form for ``count``, with ``{n}`` the count as shown."""
    from optar import i18n

    return i18n.n(key, count, **values)


def _num(value: int) -> str:
    """An integer with the language's thousands separator."""
    from optar import i18n

    return i18n.number(value)


def _dec(value: float, places: int) -> str:
    """A number with ``places`` decimals, in the language's way (``8.3``)."""
    from optar import i18n

    return i18n.decimal(value, places)


def _missing(e: KeyError, key: str) -> bool:
    """Whether ``e`` says that ``key`` is in no catalogue (not that its
    translation names a placeholder that is not given, which must surface)."""
    return e.args == (key,)


def _name(key: str, default: str) -> str:
    """The catalogue's name under ``key``, or ``default`` for a name it lacks."""
    try:
        return _t(key)
    except KeyError as e:
        if not _missing(e, key):
            raise
        return default


def error_text(e: BaseException) -> str:
    """A library error's message in the current language (``optar.errors``: the
    message of its key, filled with its values), else its text. A translation that
    cannot be filled (it names a placeholder the error does not give) is logged
    once and the English text shown: the one such fallback of the window."""
    from optar import i18n

    try:
        return i18n.error_text(e)
    except KeyError:
        key = getattr(e, "key", None)
        if key not in _BROKEN:
            _BROKEN.add(key)
            # Not wording (this module holds none): a note for the log.
            log.exception("untranslatable:%r", e)
        return str(e)


# The keys of errors whose translation could not be filled, logged once each.
_BROKEN: set[object] = set()


class _KeptError:
    """What the window keeps of an error to word it later: its kind, key, values
    and English text (or the ``Words`` of a window error), never the exception and
    its traceback. ``error_text`` reads it as it reads an error."""

    __slots__ = ("kind", "optar", "key", "values", "english", "words")

    def __init__(self, e: BaseException) -> None:
        from optar.errors import OptarError

        self.kind = type(e).__name__
        self.optar = isinstance(e, OptarError)
        self.key = getattr(e, "key", None)
        self.values = dict(getattr(e, "values", None) or {})
        self.words = getattr(e, "words", None)
        self.english = "" if self.words is not None else str(e)

    def __str__(self) -> str:
        return str(self.words) if self.words is not None else self.english

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _KeptError):
            return NotImplemented
        return all(getattr(self, a) == getattr(other, a) for a in self.__slots__)

    __hash__ = None  # type: ignore[assignment]

    def __repr__(self) -> str:
        """Its kind, key and English text (or ``Words``): for the log."""
        what = self.words if self.words is not None else self.english
        return f"{type(self).__name__}{(self.kind, self.key, what)!r}"


def _error_message(kept: _KeptError) -> str:
    return error_text(kept)


def _error_line(kept: _KeptError) -> str:
    """The first line of an error's message; another error than an optar one is
    named by its kind before it."""
    message = error_text(kept)
    line = next((part.strip() for part in message.splitlines() if part.strip()), "")
    if kept.optar and line:
        return line
    return " ".join((f"{kept.kind}:", line)) if line else kept.kind


def _constant(name: str) -> str:
    return __getattr__(name)


class Words:
    """A sentence kept as what it says, worded in the current language each time it
    is shown: ``str(words)`` calls ``fn(*args)`` (a function of this module) then,
    with any ``Words`` among the arguments worded first. The window keeps these, not
    finished sentences, wherever it shows something again later, so that a change
    of language re-words it; a Qt signal that carries one must be ``Signal(object)``.

    Two are equal when they say the same thing. It cannot be hashed: what it says
    changes with the language, so it is no key of a dict or a set. Read as a string
    (equal to one, ``in``, ``startswith`` and the other methods of ``str``), it is
    the string it says now; that is for tests and for code that only reads what is
    shown: the program never compares one with a worded sentence to decide anything.
    """

    __slots__ = ("fn", "args")

    def __init__(self, fn, *args: object) -> None:
        self.fn = fn
        self.args = args

    @classmethod
    def constant(cls, name: str) -> Words:
        """A constant of this module such as ``NO_PAGE_DATA``."""
        return cls(_constant, name)

    @classmethod
    def error(cls, e: BaseException) -> Words:
        """An error's message (``error_text``)."""
        return cls(_error_message, _KeptError(e))

    @classmethod
    def error_line(cls, e: BaseException) -> Words:
        """The first line of an error's message, named by its kind unless it is an
        optar error: what a failed background job reports."""
        return cls(_error_line, _KeptError(e))

    def __str__(self) -> str:
        return self.fn(*(str(a) if isinstance(a, Words) else a for a in self.args))

    def __format__(self, spec: str) -> str:
        return format(str(self), spec)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Words):
            return self.fn is other.fn and self.args == other.args
        if isinstance(other, str):
            return str(self) == other
        return NotImplemented

    __hash__ = None  # type: ignore[assignment]

    def __contains__(self, part: str) -> bool:
        return part in str(self)

    def __getattr__(self, name: str):
        """The methods of ``str`` (``startswith``, ``strip``…), on what it says now."""
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(str(self), name)

    def __repr__(self) -> str:
        return f"{type(self).__name__}{(self.fn, *self.args)!r}"


def __getattr__(name: str) -> str:
    """The public constants (``READ_TAB`` and so on), in the current language."""
    if name.isupper() and not name.startswith("_"):
        # Same wording as the command line's (optar.cli.ACTUAL_SIZE).
        key = "cli.ACTUAL_SIZE" if name == "ACTUAL_SIZE" else f"gui.{name}"
        try:
            return _t(key)
        except KeyError as e:
            if not _missing(e, key):
                raise
    raise AttributeError(name)


def button(name: str) -> str:
    """A dialog button's caption: ``ok``, ``cancel``, ``save``, ``yes`` or ``no``."""
    return _name(f"gui.button.{name}", name)


# Why a file cannot be put on paper with the chosen dot size and protection
# (``work.PrintPlan.too_large``): more pages than a printout may have, or more
# than a protected one may have. Codes compared by value and never shown, so
# they do not change with the language.
TOO_MANY_PAGES = "too many pages"
TOO_LARGE_TO_PROTECT = "too large to protect"

# The catalogue's key for each health a page row shows by name.
_HEALTH_KEYS = {
    Health.GOOD: "good",
    Health.UNREADABLE: "unreadable",
    Health.MISSING: "missing",
    Health.WAITING: "waiting",
    Health.WORKING: "working",
}

# A save warning names at most this many runs of pages, then counts the rest.
MAX_RUNS = 10

# What a page that spoils the saved file is, in a warning (the catalogue's key
# under ``gui.run``); waiting and working pages read the same.
_PROBLEMS = {
    Health.MISSING: "missing",
    Health.DAMAGED: "damaged",
    Health.UNREADABLE: "unreadable",
    Health.WAITING: "reading",
    Health.WORKING: "reading",
}


def count(n: int, noun: str) -> str:
    """``1 page``, ``2 pages``, ``1,205 pages``; ``noun`` is ``page``, ``byte``,
    ``block``, ``dot`` or ``scan``."""
    return _n(f"count.{noun}", n)


# The share of its repair capacity that the worst spot of a document used, up
# to which the margin is called wide, and up to which moderate.
WIDE_MARGIN = 0.5
MODERATE_MARGIN = 0.8


def health_label(
    page: PageView, restored: bool = False, repaired_bytes: int | None = None
) -> str:
    """``restored``: the document's protection repaired what its pages lost
    (``Summary.restored``), so a damaged page is not a problem any more. A page
    read by the slower reader says so and how many dots that reader corrected
    (it counts no repairs of blocks), then, once the document is verified,
    ``repaired_bytes``: how many of its bytes the document's protection repaired
    (``Summary.repaired_bytes``; None before, and nothing is said of it when it
    is 0)."""
    if page.slow and page.health in (Health.GOOD, Health.REPAIRED):
        parts = [
            _t("gui.READ_SLOWLY_ROW"),
            _n("gui.health.dots_corrected", page.corrected_dots),
        ]
        if repaired_bytes:
            parts.append(_n("gui.health.bytes_repaired", repaired_bytes))
        return " · ".join(parts)
    if page.health == Health.REPAIRED:
        return _n("gui.health.repaired", page.repaired)
    if page.health == Health.DAMAGED:
        if restored:
            return _n("gui.health.restored", page.lost)
        return _n("gui.health.damaged", page.lost)
    return _t(f"gui.health.{_HEALTH_KEYS[page.health]}")


def summary_line(s: Summary) -> str:
    """The document's state for the bottom bar.

    For a version-1 document an accepted repair result adds what the repair did
    (``repair_line``); one that could not give the file says which pages to add
    or rescan (``rescan_advice``). While scans are being read the count of those
    read is added after the state (``with_reading``).
    """
    return with_reading(_state_line(s), s)


def with_reading(line: str, s: Summary) -> str:
    """``line`` (the document's state) with, while scans are being read, how many of
    them are read after it; when the line says nothing more than that the document
    is empty or being worked on, the count alone (``reading_line``)."""
    if not s.reading:
        return line
    if line in ("", _t("gui.WORKING")):
        return reading_line(s.reading, s.batch)
    return f"{line} · {scans_read(s.reading, s.batch)}"


def _state_line(s: Summary) -> str:
    pages = s.good + s.repaired + s.damaged + s.unreadable + s.missing
    repair = s.repair
    if s.state == DocState.EMPTY:
        return ""
    if s.state == DocState.WORKING:
        return _t("gui.WORKING")
    if s.state == DocState.CHECKING:
        return _t("gui.state.checking")
    if s.state == DocState.VERIFIED:
        parts = [_t("gui.VERIFIED"), count(s.size, "byte")]
        if repair is not None:
            parts.append(repair_line(repair))
        return " · ".join(parts)
    if s.state == DocState.RECOVERABLE:
        many, missing = _page_list(s.missing_pages)
        if repair is None:
            return _n("gui.state.recoverable", many, pages=missing)
        return " · ".join((
            _n("gui.state.recovered", many, pages=missing),
            _t("gui.state.matches"),
            count(s.size, "byte"),
            repair_line(repair),
        ))  # fmt: skip
    if s.state == DocState.MISMATCH:
        line = _t("gui.state.mismatch")
        return " · ".join((line, repair_line(repair))) if repair is not None else line
    if s.repair_error:
        return repair_failed(str(s.repair_error))
    if repair is not None:
        return _t(
            "gui.state.advice_with_repair",
            advice=rescan_advice(repair),
            repair=repair_line(repair),
        )
    if s.state == DocState.UNVERIFIABLE:
        read = _n("gui.state.all_read" if pages > 1 else "gui.state.read", pages)
        return " · ".join((read, _t("gui.state.no_tag")))
    # A page read by the slower reader is not called good: that reader cannot
    # say how much of the page it got wrong.
    good = _n("gui.state.good", pages, good=_num(s.good + s.repaired - s.slow))
    if s.repaired:
        repaired = _n("gui.state.repaired", s.repaired)
        good = _t("gui.state.good_with_repaired", good=good, repaired=repaired)
    parts = [good]
    if s.slow:
        parts.append(_n("gui.state.slow", s.slow))
    for n, what in ((s.damaged, "damaged"), (s.unreadable, "unreadable"), (s.missing, "missing")):
        if n:
            parts.append(_n(f"gui.state.{what}", n))
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
    # Page numbers in a run are shown without thousands separators.
    if first == last:
        return _t(f"gui.run.{problem}.single", first=first)
    if last == first + 1:
        return _t(f"gui.run.{problem}.pair", first=first, last=last)
    return _t(f"gui.run.{problem}.range", first=first, last=last)


def save_warning(doc: Document, summary: Summary | None = None) -> str | None:
    """What saving must confirm first; None when the file is verified.

    ``summary`` is the document's summary if the caller has it (it may be
    ``CHECKING``); otherwise ``doc.summary()`` is used, which may hash the file.
    A version-1 document saves what its repair gave (``Summary.repair``), whatever
    else is going on (another scan of a page may be being read): the warning is
    about that result. One that could not give the file is saved as far as it was
    recovered, which may be wrong in parts.
    """
    s = summary if summary is not None else doc.summary()
    state = s.state
    if state == DocState.VERIFIED:
        return None
    if s.repair is not None and s.repair.verified:
        return None  # repaired, and the fingerprint matches
    if s.repair is not None and s.repair.data is None:
        return _t("gui.save.unrepaired", advice=rescan_advice(s.repair))
    if s.repair is not None:
        state = DocState.MISMATCH  # the file as repaired, which is not the original
    if state == DocState.CHECKING:
        return _t("gui.save.checking")
    if state == DocState.EMPTY:
        return _t("gui.save.empty")
    if state == DocState.MISMATCH:
        return _t("gui.save.mismatch")
    if state == DocState.UNVERIFIABLE and doc.by_hand:
        return _t("gui.save.by_hand")
    if state == DocState.UNVERIFIABLE:
        return _t("gui.save.untagged")
    runs = _runs(doc.pages())
    shown = [_run_text(*run) for run in runs[:MAX_RUNS]]
    rest = sum(last - first + 1 for first, last, _ in runs[MAX_RUNS:])
    if rest:
        shown.append(_n("gui.save.more", rest))
    return _t("gui.save.incomplete", runs="; ".join(shown))


def untagged_caution() -> str:
    return _t("gui.caution.untagged")


def _reason_key(reason: str | Words) -> str | None:
    """The catalogue's key (under ``gui.reason``) for a reason the program gives as
    a code (the library's English constants, never shown as they are)."""
    if not isinstance(reason, str):
        return None  # a reason that words itself
    return {
        NO_PAGE: "no_page",
        LABEL_UNREADABLE: "label_unreadable",
        OUT_OF_RANGE: "page_number",
        COUNT_OUT_OF_RANGE: "page_count",
        SIZE_MISMATCH: "size_mismatch",
        FORMAT_MISMATCH: "format_mismatch",
        NOT_DECODABLE: "not_decodable",
    }.get(reason)


def unreadable_reason(reason: str | Words) -> str:
    """Why a scan is unreadable, in plain words: a code the program gives, worded
    by the catalogue, or a reason that words itself (``Words``)."""
    key = _reason_key(reason)
    return str(reason) if key is None else _t(f"gui.reason.{key}")


def detail_text(
    page: PageView,
    scan_name: str | None,
    pages: int,
    reason: str = "",
    restored: bool = False,
    repaired_bytes: int | None = None,
) -> tuple[str, ...]:
    """The detail panel's lines for one page of a document of ``pages`` pages.

    ``reason`` defaults to the page's own reason for being unreadable.
    ``restored`` and ``repaired_bytes`` are as for ``health_label``.
    """
    reason = reason or page.reason
    title = _t("gui.detail.title", page=_num(page.number), total=_num(pages))
    if scan_name:
        title = f"{title} · {scan_name}"
    if page.histogram is not None and page.slow:
        return (title, *slow_reader_detail(page, repaired_bytes))
    if page.histogram is not None:
        blocks = sum(page.histogram) + page.lost
        if restored and page.lost:
            lost = _n("gui.detail.restored", page.lost)
        else:
            lost = _n("gui.detail.lost", page.lost)
        repaired = _n("gui.detail.repaired", page.repaired)
        lines = [title, " · ".join((count(blocks, "block"), repaired, lost))]
        if page.repaired:
            one, two, three = page.histogram[1:]
            lines.append(_t("gui.detail.repairs", one=_num(one), two=_num(two), three=_num(three)))
        return tuple(lines)
    if page.health == Health.MISSING:
        return (title, _t("gui.detail.missing"))
    if page.health == Health.WAITING:
        return (title, _t("gui.detail.waiting"))
    if page.health == Health.UNREADABLE:
        return (title, unreadable_reason(reason) if reason else _t("gui.detail.unreadable"))
    return (title, _t("gui.detail.reading"))


def by_hand_caution() -> str:
    return _t("gui.caution.by_hand")


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
            return _name(f"gui.paper.{key}", paper.name)
    for (key, dots), layout in LAYOUTS.items():
        if layout.fmt.to_string() == format:
            return _t(f"gui.paper_dots.{dots}", paper=_name(f"gui.paper.{key}", key))
    return format


def _group_line(group: GroupView) -> str:
    pages = max(group.total, 1)  # an empty file prints one page labelled 1/0
    name = group.title.rstrip(" ") or _t("gui.NO_NAME")
    return " · ".join((name, paper_name(group.format), count(pages, "page")))


def document_title(group: GroupView) -> str:
    """The first row of the list: name, paper and page count."""
    return _group_line(group)


def page_row(page: PageView, restored: bool = False, repaired_bytes: int | None = None) -> str:
    """A page's row; ``restored`` and ``repaired_bytes`` are as for ``health_label``."""
    number = _t("gui.row.page", page=_num(page.number))
    return " · ".join((number, health_label(page, restored, repaired_bytes)))


def other_group_row(group: GroupView) -> str:
    """A row under "Not part of this file": what the group says it is, and its scans."""
    return " · ".join((_group_line(group), count(len(group.scan_ids), "scan")))


def other_group_detail(group: GroupView) -> tuple[str, ...]:
    return (_group_line(group), _n("gui.row.other_printout", len(group.scan_ids)))


def spare_row(page: PageView, scan_name: str) -> str:
    """A row under its page: a spare scan, shown with the health it would give."""
    return f"    {_t('gui.row.spare')} · {scan_name} · {health_label(page)}"


def spare_detail(page: PageView, scan_name: str, pages: int) -> tuple[str, ...]:
    """The detail panel for a spare; ``page`` is the page as it would be with it in use."""
    lines = detail_text(page, scan_name, pages)
    title = f"{lines[0]} · {_t('gui.row.spare_tag')}"
    return (title, *lines[1:], _t("gui.row.spare_not_in_use"))


def replace_title(page: int) -> str:
    return _t("gui.dialog.replace_title", page=_num(page))


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
    page_shown = _num(page)
    if fit == Fit.UNUSABLE:
        if scan.reason:
            return _t("gui.rejected.unusable_reason", name=name, page=page_shown,
                      reason=unreadable_reason(scan.reason))  # fmt: skip
        return _t("gui.rejected.unusable", name=name, page=page_shown)
    if fit == Fit.OTHER_PAGE and (other_page is not None or info is not None):
        where = other_page if other_page is not None else info.page
        return _t("gui.rejected.other_page", name=name, page=page_shown, other=_num(where))
    if fit == Fit.OTHER_DOCUMENT and info is not None:
        printout = " · ".join((
            info.name.rstrip(" ") or _t("gui.NO_NAME"),
            paper_name(info.format),
            count(max(info.total, 1), "page"),
        ))  # fmt: skip
        return _t("gui.rejected.other_document", name=name, page=page_shown,
                  other=_num(info.page), printout=printout)  # fmt: skip
    why = unreadable_reason(scan.reason) if str(scan.reason).strip() else _t("gui.rejected.unread")
    return _t("gui.rejected.not_used", name=name, page=page_shown, why=_sentence(why))


def assign_prompt(scan_name: str) -> str:
    return _t("gui.dialog.assign_prompt", name=scan_name)


def of_pages(total: int) -> str:
    """After the page number in the page field: how many pages there are."""
    return _t("gui.dialog.of_pages", total=_num(total))


def unreadable_row(scan: ScanView) -> str:
    return f"{os.path.basename(scan.path)} · {unreadable_reason(scan.reason)}"


def unreadable_detail(scan: ScanView) -> tuple[str, ...]:
    return (os.path.basename(scan.path), unreadable_reason(scan.reason))


def summary_bar(line: str, note: str) -> str:
    """The bottom bar: the document's state and, after a save, what was saved."""
    return f"{line} — {note}" if note else line


def saved_message(path: str, size: int) -> str:
    return _n("gui.message.saved", size, name=os.path.basename(path))


def check_failed(message: str) -> str:
    """The bar when the fingerprint check itself failed (not a mismatch)."""
    return _t("gui.message.check_failed", message=message)


def save_failed(message: str) -> str:
    return _t("gui.message.save_failed", message=message)


def paper_label(paper: str) -> str:
    """A paper's name as the window shows it, by its name in optar.format."""
    return _name(f"gui.paper.{paper}", paper)


def file_info(total: int, size: int) -> str:
    """Pages and size of a file to put on paper; an empty file prints one page."""
    return " · ".join((count(max(total, 1), "page"), count(size, "byte")))


def name_warning(
    dropped: str, cut: bool, *, stored: bool = False, printed: bool = True
) -> str | None:
    """Why the printed name differs from the name typed, or None when it does not.

    ``stored`` is whether the pages carry the name in their data and identify
    themselves from it (every printout but a compatible one): the printed name
    is then only for people. ``printed`` is whether any of the name is printed
    at all; the label of the largest dots has no room for it.
    """
    sentences = []
    if dropped and (printed or not cut):
        shown = " ".join(ch if ch.isprintable() else repr(ch)[1:-1] for ch in dropped)
        sentences.append(_t("gui.name.dropped", chars=shown))
    if cut and not printed:
        sentences.append(_t("gui.name.no_room"))
    elif cut:
        sentences.append(_t("gui.name.cut"))
    if not sentences:
        return None
    sentences.append(_t("gui.name.stored" if stored else "gui.name.printed"))
    return " ".join(sentences)


def not_regular_file(path: str) -> str:
    """Why a folder, a named pipe or a device is not read as a scan or a file to print."""
    return _t("gui.message.not_regular_file", path=path)


def file_unreadable(message: str) -> str:
    return _t("gui.message.file_unreadable", message=message)


def created_message(path: str, pages: int) -> str:
    created = _t("gui.message.created", name=os.path.basename(path))
    return " · ".join((created, count(max(pages, 1), "page")))


def create_failed(message: str) -> str:
    return _t("gui.message.create_failed", message=message)


def scan_filter() -> str:
    """The file dialog's filter for scans."""
    patterns = " ".join(f"*{ext}" for ext in SCAN_EXTENSIONS)
    return _t("gui.dialog.scan_filter", patterns=patterns)


def size_changed() -> str:
    """The preview's reason when an image's size changed while it loaded."""
    return _t("gui.message.size_changed")


def preview_failed(message: str) -> str:
    """Shown in the preview instead of a scan it could not load."""
    return _t("gui.message.preview_failed", message=message)


def too_large_to_show(pixels: int, limit: int) -> str:
    return _n("gui.message.too_many_pixels", pixels, limit=_num(limit))


def _dots(dots: str) -> str:
    """A dot size's name as the window shows it, by its name in optar.format."""
    return _name(f"gui.dots.{dots}", dots)


def dot_size_label(dots: str, scan_dpi: int) -> str:
    """A dot size in its selector: its name and the scan resolution to use."""
    return _t("gui.write.dot_size", dots=_dots(dots), dpi=_num(scan_dpi))


def protection_label(protect: str) -> str:
    return _name(f"gui.protection.{protect}", protect)


def promise(promised: int, total: int) -> str:
    """How many of a protected printout's pages, any of them, may be lost
    without losing the file (``optar.container.pages_promised``)."""
    return _n("gui.write.promise", promised, total=_num(total))


def print_summary(total: int, size: int, promised: int, protected: bool) -> str:
    """Pages and size of a file to put on paper, and what its protection allows."""
    line = file_info(total, size)
    if promised > 0:
        return " · ".join((line, promise(promised, total)))
    if protected:
        return " · ".join((line, _t("gui.DAMAGE_REPAIRED")))
    return line


def too_large(
    reason: str, limit: int, unprotected_fits: bool = False, smaller_dots: str | None = None
) -> str:
    """Why a file cannot be put on paper with the chosen dot size and protection,
    and which other choice would take it.

    ``reason`` is ``TOO_MANY_PAGES`` or ``TOO_LARGE_TO_PROTECT``; ``limit`` the
    most pages a printout of that kind may have. ``unprotected_fits`` is whether
    the file fits at this dot size without protection; ``smaller_dots`` names
    the largest smaller dot size at which it fits with this protection, if any.
    """
    kind = "protect" if reason == TOO_LARGE_TO_PROTECT else "pages"
    why = _n(f"gui.too_large.{kind}", limit)
    if smaller_dots is not None:
        fits_key = "fits_either" if unprotected_fits else "fits_dots"
        return " ".join((why, _t(f"gui.too_large.{fits_key}.{smaller_dots}")))
    if unprotected_fits:
        return " ".join((why, _t("gui.too_large.fits_unprotected")))
    return why


# --- Documents that repair themselves, and coarse scans ---------------------------
#
# What the library calls parity, codewords and page headers is never named here:
# the window speaks of "protection", "repair" and the "fingerprint". Only the
# fingerprint proves the file is right; nothing below suggests otherwise.

# How many of the most damaged pages the advice after a failed repair names.
RESCAN_PAGES = 3


def _about_dpi(dpi: float) -> str:
    """A measured resolution, rounded to the nearest 10: scans measure a few
    percent off (a printout scaled to 95% reads 286 dpi at 300)."""
    return _num(int(round(dpi / 10)) * 10)


def coarse_scan(scan_dpi: float, layout: Layout | None, slow_tried: bool = False) -> str:
    """A scan made at too low a resolution: for an identified page of ``layout``,
    the resolution its dots need; for an unreadable scan (``layout`` None), the
    resolution every dot size needs, and, when ``slow_tried``, that the slower
    reader for coarse scans could not read it either."""
    measured = _about_dpi(scan_dpi)
    if layout is not None:
        return _t("gui.coarse.page", measured=measured, needed=_num(layout.scan_dpi))
    # Imported here: loading the optar package loads numpy.
    from optar.format import DOT_SIZES

    # Any image with a page outline has an estimate: this does not claim it is a page.
    needs = {name: _num(dots.scan_dpi) for name, dots in DOT_SIZES.items()}
    line = _t("gui.coarse.unreadable", measured=measured, **needs)
    return " ".join((line, _t("gui.SLOW_TRIED"))) if slow_tried else line


def _share(part: int, whole: int) -> str:
    """``8.3%``; ``under 0.1%`` for a small share that is not none."""
    share = 100 * part / whole
    if 0 < share < 0.05:
        return _t("gui.slow.share_small")
    return _t("gui.slow.share", share=_dec(share, 1))


def slow_reader_detail(page: PageView, repaired_bytes: int | None = None) -> tuple[str, ...]:
    """The detail lines of a page read by the slower reader, after its title: that
    it was, how many of its dots that reader corrected, and, once the document is
    verified (``repaired_bytes`` not None), how many of its bytes the document's
    protection repaired. That reader gives every symbol its likeliest value, so it
    finds no block beyond repair; what it got wrong is the protection's to repair."""
    dots = page.corrected_dots
    if page.dots:
        corrected = _t("gui.slow.corrected_of", dots=_num(dots), total=_num(page.dots),
                       share=_share(dots, page.dots))  # fmt: skip
    else:
        corrected = _t("gui.slow.corrected", dots=_num(dots))
    if repaired_bytes is None:
        after = _t("gui.slow.pending")
    elif repaired_bytes == 0:
        after = _t("gui.slow.none_wrong")
    else:
        after = _n("gui.slow.repaired", repaired_bytes)
    return (f"{_t('gui.READ_SLOWLY')}.", corrected, after)


# --- Scans being read --------------------------------------------------------------

# The steps of a scan's reading that have words of their own (under ``gui.step``),
# by their keys (``work.STEP_OPEN``, ``optar.identify.STEP_FIND`` and so on; a test
# checks that they match).
_STEPS = ("open", "find", "identify", "read", "slow-sample")
# The slower reader's fits, one of several.
_SLOW_FIT = "slow-fit"
_SLOW_STEPS = ("slow-sample", _SLOW_FIT)


def step_text(progress: Progress | None) -> str:
    """What a scan being read is doing: ``Waiting`` before it starts, then its step
    (``Slower reader: pass 4 of 5`` while the fourth of five fits runs)."""
    if progress is None:
        return _t("gui.WAITING")
    if progress.step == _SLOW_FIT:
        of = max(progress.of, 1)
        current = min(progress.done + 1, of)
        return _t("gui.step.slow-fit", current=_num(current), total=_num(of))
    if progress.step in _STEPS:
        return _t(f"gui.step.{progress.step}")
    return _t("gui.step.other")  # a step with no words of its own (none should be)


def reading_slowly(progress: Progress | None) -> bool:
    """Whether the slower reader for coarse scans is reading the scan."""
    return progress is not None and progress.step in _SLOW_STEPS


def being_read_row(name: str, progress: Progress | None) -> str:
    """The row of a scan being read, as plain text (the list draws a bar too)."""
    return f"{name} · {step_text(progress)}"


def being_read_detail(scan: ScanView, progress: Progress | None) -> tuple[str, ...]:
    """The detail of a scan being read; one the slower reader reads says that it
    takes about a minute."""
    lines = (os.path.basename(scan.path), f"{step_text(progress)}.")
    return (*lines, f"{_t('gui.READING_COARSE')}.") if reading_slowly(progress) else lines


def scans_read(reading: int, batch: int) -> str:
    """How many of a batch of scans are read: ``3 of 6 scans read``."""
    return _n("gui.scans_read", batch, done=_num(batch - reading))


def reading_line(reading: int, batch: int) -> str:
    """The bottom bar while scans are being read and the document has nothing else
    to say: ``Working… 3 of 6 scans read``."""
    return _n("gui.scans_read_working", batch, done=_num(batch - reading))


def _and(items: list[str]) -> str:
    """``a``, ``a and b``, ``a, b and c``."""
    if len(items) <= 1:
        return "".join(items)
    return _t("gui.list.and", items=_t("gui.list.comma").join(items[:-1]), last=items[-1])


def _page_list(numbers: tuple[int, ...] | list[int], in_order: bool = True) -> tuple[int, str]:
    """How many pages ``numbers`` names, and the list of them: ``3``, ``3 and 7``,
    ``2-4 and 9``. ``in_order`` sorts the numbers and joins runs; else they are
    named in the order given. At most ``MAX_RUNS`` items are named, then the
    pages left are counted."""
    numbers = list(dict.fromkeys(numbers))
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
    items = [_num(a) if a == b else f"{_num(a)}-{_num(b)}" for a, b in spans[:MAX_RUNS]]
    rest = sum(b - a + 1 for a, b in spans[MAX_RUNS:])
    if rest:
        items.append(_n("gui.list.more", rest))
    return len(numbers), _and(items)


def repair_line(u: Unwrapped) -> str:
    """What repairing a document did: the bytes it repaired, and how much of its
    capacity the worst spot used (``worst_used`` of ``budget``)."""
    if u.budget == 0:
        return _t("gui.repair.unprotected")
    fixed = _n("gui.repair.bytes", u.repaired_bytes)
    if u.worst_used > u.budget:
        too_much = _t("gui.repair.too_much", used=_num(u.worst_used), budget=_num(u.budget))
        return " · ".join((fixed, too_much))
    return " · ".join((fixed, margin_line(u.worst_used, u.budget)))


def margin_line(used: int, budget: int) -> str:
    """How close a repair came to failing: the share of its repair capacity
    that the worst spot of the document used. At 100% the file is lost."""
    share = used / budget
    if share <= WIDE_MARGIN:
        margin = "wide"
    elif share <= MODERATE_MARGIN:
        margin = "moderate"
    else:
        margin = "close"
    percent = min(math.ceil(100 * share), 100)  # never shown as less than it is
    return _t(f"gui.margin.{margin}", percent=percent, used=_num(used), budget=_num(budget))


def rescan_advice(u: Unwrapped) -> str:
    """After a repair that could not give the file: the missing pages to add, and
    the ``RESCAN_PAGES`` pages with the most damage to rescan."""
    missing = set(u.missing)
    worst = sorted(
        (p for p in u.page_damage if p not in missing), key=lambda p: (-u.page_damage[p], p)
    )[:RESCAN_PAGES]
    add = rescan = None
    if missing:
        many, pages = _page_list(sorted(missing))
        add = _n("gui.rescan.add", many, pages=pages)
    if worst:
        many, pages = _page_list(worst, in_order=False)
        rescan = _n("gui.rescan.worst", many, pages=pages)
    if add is None and rescan is None:
        return _t("gui.rescan.nothing")
    if add is not None and rescan is not None:
        what = _t("gui.rescan.both", add=add, rescan=rescan)
    else:
        what = add if add is not None else rescan
    return _t("gui.rescan.advice", what=what)


def repair_failed(reason: str) -> str:
    """The bar when repairing the pages itself failed (an error, not damage)."""
    return _t("gui.message.repair_failed", reason=reason)


# The terminal messages of optar-gui (``optar_gui.__main__``).


def missing_qt() -> str:
    """What optar-gui says when PySide6 is not installed."""
    return _t("gui.cli.missing_qt")


def cli_description() -> str:
    """The description in optar-gui's ``--help``."""
    return _t("gui.cli.description")


def cli_version_help() -> str:
    """The help line of optar-gui's ``--version``."""
    return _t("gui.cli.version_help")
