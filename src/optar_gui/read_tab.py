# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The "Read from paper" tab: adding scans, the pages and their health, saving.

``ReadController`` coordinates, with no widgets: it owns the ``Document``, runs
each scan through ``work.process_scan`` on a ``JobRunner``, applies the results
and tells the view when to redraw. ``ReadTab`` is the view: it shows what the
document says through ``text`` and passes the user's actions to the controller.

Responsiveness.

- Background results only mark the view stale: the controller redraws from a
  single-shot timer (``REFRESH_MS``) that a result starts if it is not already
  pending, so a burst of results costs one redraw (a redraw reads the document,
  which costs time linear in the number of scans). User actions redraw at once.
- Checking a complete tagged document against its fingerprint hashes the whole
  file, which is never done on the interface thread: the controller shows
  ``CHECKING`` and runs the document's ``VerdictJob`` (a snapshot of the pages)
  in the background, then hands the verdict back with
  ``Document.accept_verdict``. A job that fails is not retried for the same
  pages; the bar says the check failed.
- A version-1 document is repaired and checked the same way: whenever the
  document offers a ``RepairJob`` (``Document.repair_job``), the controller runs
  it in the background, shows ``text.REPAIRING`` meanwhile, and hands the result
  to ``Document.accept_repair`` (or the error to ``Document.fail_repair``, which
  stops it being offered again for the same pages). Saving is offered when
  ``Document.can_save_anyway`` and writes ``Document.save_chunks()``: the
  repaired file, or, when the repair could not give it, what was recovered,
  after the warning says so.
- Saving streams ``Document.chunks()`` (a snapshot taken together with the
  warning, before the user confirms it) through ``optar.fileio.replacing`` in the background,
  so an existing file is untouched by a failed save and a large file never
  freezes the window.
- Scans are read and decoded only by background jobs. Saving and checking run on
  a second runner, so they never wait behind scans being decoded.
- The preview loads the selected scan on a third runner the controller owns
  (``preview_runner``), so closing stops it with everything else.
- Closing cancels every scan, check and preview load, lets a running save
  finish, and waits for all of it within one time budget; a save still running
  when the budget runs out is told to stop and leaves no file. The window asks
  first whether to wait for a running save (``MainWindow.closeEvent``).

Working by hand. Which actions apply to the selected row comes from
``Document.actions``; the tab only enables the buttons it names. Replacing a
page adds the new scan and decides once it has been read
(``Document.replacement_fit``): it becomes the page's scan in use, or
``replace_rejected`` says what it is instead. Only the latest choice for a page
counts, whichever job finishes last. In a document started by hand, Replace
assigns the file to the page instead (no label to go by). A scan assigned to a
page that ``Document.needs_decoding`` says must be decoded (no decoded page, or
one decoded in another format) is decoded with ``work.process_unlabelled`` in the
document's format, on the scan runner; if that cancels the scan's own (labelled)
reading before it reported, the scan is read again once the decode has reported,
so it is never left neither identified nor unreadable. Every action clears the
"Saved …" note, and does nothing once the controller is closed; so does any
background result that changes the document (a finished fingerprint check does
not).

The preview's rotation and marks are kept per scan and per page format: a scan
decoded for a document in another format shows, back in its own document, its
own reading.
"""

from __future__ import annotations

import dataclasses
import os
import threading
import time
from collections.abc import Callable, Iterable, Iterator
from functools import partial

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListView,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from optar.fileio import replacing
from optar.format import PAPERS, PageFormat, get_paper
from optar_gui import text
from optar_gui.dialogs import AssignPageDialog, StartByHandDialog, ask
from optar_gui.document import (
    NO_ACTIONS,
    Actions,
    DocState,
    Document,
    Fit,
    Row,
    Summary,
    expand_paths,
    paper_for_size,
)
from optar_gui.jobs import JobRunner
from optar_gui.preview import ScanPreview
from optar_gui.work import (
    Cancelled,
    ScanWork,
    native_path,
    process_scan,
    process_unlabelled,
    too_coarse,
)

__all__ = ["REFRESH_MS", "SHUTDOWN_MS", "ReadController", "ReadTab"]

# How long background results are gathered before the view is redrawn.
REFRESH_MS = 100
# How long closing the window waits for running work to stop.
SHUTDOWN_MS = 3000

# Job ids on the controller's second runner (scan jobs use the scan ids).
_VERDICT_JOB = 1
_SAVE_JOB = 2
_REPAIR_JOB = 3


def _write_chunks(
    path: str, chunks: Iterator[bytes], stop: threading.Event, _cancelled: Callable[[], bool]
) -> int:
    """Writes the chunks to ``path`` through a temporary file; returns the bytes written.

    Stops, leaving no file, when ``stop`` is set. The runner's own cancellation is
    ignored, so that closing the window lets a running save finish.
    """
    written = 0
    with replacing(path) as temp, open(temp, "wb") as f:
        for chunk in chunks:
            if stop.is_set():
                raise Cancelled()
            f.write(chunk)
            written += len(chunk)
    return written


class ReadController(QObject):
    """The document, its background work, redrawing and saving; no widgets.

    ``changed`` is emitted after the document changed (coalesced for background
    results), with ``summary`` already brought up to date. ``save_finished(path,
    bytes)`` and ``save_failed(message)`` report a save started with ``save``.
    ``replace_rejected(message)`` says why a scan chosen with ``replace`` was not
    used. ``process`` and ``unlabelled`` are ``work.process_scan`` and
    ``work.process_unlabelled`` unless tests replace them.
    """

    changed = Signal()
    save_finished = Signal(str, int)
    save_failed = Signal(str)
    replace_rejected = Signal(str)

    def __init__(
        self,
        parent: QObject | None = None,
        process: Callable[..., ScanWork] = process_scan,
        max_workers: int | None = None,
        unlabelled: Callable[..., ScanWork] = process_unlabelled,
    ) -> None:
        super().__init__(parent)
        self._doc = Document()
        self._process = process
        self._unlabelled = unlabelled
        # page -> the scan last chosen to replace it, until that scan has been read
        self._replacing: dict[int, int] = {}
        self._decoding_in: dict[int, str] = {}  # scan -> format of its unlabelled decode
        self._reading: set[int] = set()  # scans whose labelled reading has not reported
        self._read_again: set[int] = set()  # scans to read once their decode reports
        self._runner = JobRunner(self, max_workers)
        self._runner.started.connect(self._on_started)
        self._runner.finished.connect(self._on_finished)
        self._runner.failed.connect(self._on_failed)
        self._tasks = JobRunner(self, max_workers=2)  # saving and checking
        self._tasks.finished.connect(self._on_task_finished)
        self._tasks.failed.connect(self._on_task_failed)
        self._previews = JobRunner(self, max_workers=1)  # the preview's image loads
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self.refresh)
        # (scan, format of a decode without its label, or None) -> what it gave
        self._works: dict[tuple[int, str | None], ScanWork] = {}
        self._summary = self._doc.summary()
        self._verdict_key: tuple | None = None  # what the running verdict job hashes
        self._verdict_error: tuple[tuple, str] | None = None  # (key, message) of a failed job
        self._repair_key: tuple | None = None  # what the running repair job repairs
        self._save_path: str | None = None  # while a save runs
        self._save_stop = threading.Event()
        self._closed = False
        self.note = ""  # what the last save did, until the document changes
        self.refreshes = 0  # for tests: how often ``changed`` was emitted

    # --- Reading -----------------------------------------------------------------

    @property
    def document(self) -> Document:
        return self._doc

    @property
    def runner(self) -> JobRunner:
        """The runner that reads and decodes scans."""
        return self._runner

    @property
    def preview_runner(self) -> JobRunner:
        """The runner the preview loads images on; ``shutdown`` stops it."""
        return self._previews

    @property
    def summary(self) -> Summary:
        """The document's summary as of the last redraw; never hashes on its own."""
        return self._summary

    @property
    def checking(self) -> bool:
        """Whether a fingerprint check, or a repair and check, is running in the
        background."""
        return self._verdict_key is not None or self._repair_key is not None

    @property
    def check_error(self) -> str:
        """Why the check of the current pages failed, or ""."""
        return self._verdict_error[1] if self._verdict_error is not None else ""

    def summary_text(self) -> str:
        """The bottom bar's text."""
        s = self._summary
        if s.state == DocState.CHECKING and self.check_error:
            line = text.check_failed(self.check_error)
        elif self._repair_key is not None and s.repair is None and s.state != DocState.WORKING:
            line = text.REPAIRING
        else:
            line = text.summary_line(self._summary)
        return text.summary_bar(line, self.note)

    @property
    def saving(self) -> bool:
        return self._save_path is not None

    @property
    def can_save(self) -> bool:
        """Whether saving can start: the document has something to save
        (``Document.can_save_anyway``) and no save runs."""
        return self._doc.can_save_anyway and not self.saving and not self._closed

    def work_for(self, scan_id: int, format: str | None = None) -> ScanWork | None:
        """The last processing result of a scan (its outcome is in the document): of
        its decode in ``format`` if there is one, else of its own reading."""
        if format is not None and (scan_id, format) in self._works:
            return self._works[(scan_id, format)]
        return self._works.get((scan_id, None))

    def scan_note(self, work: ScanWork | None) -> str | None:
        """The note on an identified scan made too coarsely for its dots, or None.
        (An unreadable scan that is too coarse says so in its reason.)"""
        if work is None or work.info is None or not too_coarse(work.scan_dpi, work.layout):
            return None
        return text.coarse_scan(work.scan_dpi, work.layout)

    def save_warning(self) -> str | None:
        """What saving must confirm first, from an up-to-date summary."""
        if self._timer.isActive():
            self.refresh()
        return text.save_warning(self._doc, self._summary)

    # --- User actions ------------------------------------------------------------

    def add_paths(self, paths: Iterable[str]) -> None:
        """Adds the scans (folders give the images directly inside them) and starts them."""
        if self._closed:
            return
        self.note = ""
        for path in expand_paths(paths):
            scan_id = self._doc.add_scan(path)
            if scan_id is not None:
                self._read(scan_id, path)
        self.refresh()

    def remove(self, scan_id: int) -> None:
        if self._closed:
            return
        self._runner.cancel(scan_id)
        self._doc.remove_scan(scan_id)
        self.note = ""
        self._works = {k: w for k, w in self._works.items() if k[0] != scan_id}
        self._decoding_in.pop(scan_id, None)
        self._reading.discard(scan_id)
        self._read_again.discard(scan_id)
        self._replacing = {p: s for p, s in self._replacing.items() if s != scan_id}
        self.refresh()

    def replace(self, page: int, path: str) -> None:
        """Adds the scan at ``path`` for page ``page``. Once it has been read, it
        becomes the page's scan in use if it is that page of the current document
        and gives usable data where the page has some; otherwise
        ``replace_rejected`` says why and the page keeps its scan. A file already
        added is judged as it is (at once, if it has been read).

        Only the latest choice for a page counts: a later ``replace`` of the page,
        ``use_spare`` or ``assign`` for it, ``switch_document`` and ``start_by_hand``
        drop a replacement still being read, whose scan simply stays added.

        In a document started by hand there are no labels to go by: the file is
        assigned to the page and decoded without its label, then judged the same way.
        Once that decode has reported, a file added this way is also read with its
        label, so it is listed where it belongs if the document is left.
        A scan is judged only once its reading for this document has reported
        (the document counts a decode as pending from the moment it is queued);
        until then the page keeps the scan it uses.
        """
        if self._closed:
            return
        self.note = ""
        doc = self._doc
        scan_id = doc.add_scan(path)
        added = scan_id is not None
        if not added:
            scan_id = doc.scan_id_of(path)
        self._drop_pending(page, scan_id)
        if doc.by_hand:
            if added:  # read with its label too, after the decode, for other documents
                self._read_again.add(scan_id)
            doc.assign_page(scan_id, page)
            if doc.needs_decoding(scan_id):
                self._decode_for_document(scan_id)
        elif added:
            self._read(scan_id, path)
        self._settle_replacement(scan_id, page)
        self.refresh()

    def use_spare(self, scan_id: int) -> None:
        """Makes a spare the scan in use for its page."""
        if self._closed:
            return
        self._replacing.pop(self._doc.page_with(scan_id).number, None)
        self._doc.use_scan(scan_id)
        self.note = ""
        self.refresh()

    def switch_document(self, key: object) -> None:
        """Makes the group with this key (listed as not part of the file) the document."""
        if self._closed:
            return
        self._doc.switch_to(key)
        self._replacing.clear()
        self.note = ""
        self.refresh()

    def assign(self, scan_id: int, page: int) -> bool:
        """Puts the scan into page ``page`` of the current document by hand; a scan
        that needs it (``Document.needs_decoding``) is then decoded without its
        label, in the document's format. Returns False, doing nothing, when the
        document no longer has that page or no longer takes the scan by hand (it
        may have changed while the user was choosing: ``Document.can_assign``)."""
        doc = self._doc
        if self._closed or not doc.can_assign(scan_id, page):
            return False
        self._drop_pending(page, scan_id)
        doc.assign_page(scan_id, page)
        if doc.needs_decoding(scan_id):
            self._decode_for_document(scan_id)
        self.note = ""
        self.refresh()
        return True

    def start_by_hand(self, paper_name: str, total: int) -> None:
        """Starts a document of ``total`` pages on the paper named as in ``optar.format``."""
        if self._closed:
            return
        self._doc.start_by_hand(PageFormat.for_paper(get_paper(paper_name)).to_string(), total)
        self._replacing.clear()
        self.note = ""
        self.refresh()

    def suggested_paper(self, scan_id: int | None = None) -> str:
        """The paper to offer for a document started by hand, by the shape of the
        given scan, else of the first unreadable scan that was read as an image."""
        candidates = [s.id for s in self._doc.unreadable()]
        if scan_id is not None:
            candidates.insert(0, scan_id)
        for candidate in candidates:
            work = self.work_for(candidate)
            paper = paper_for_size(work.size) if work is not None else None
            if paper is not None:
                return paper
        return next(iter(PAPERS))

    def _drop_pending(self, page: int, scan_id: int) -> None:
        """A new choice for ``page`` or for the scan: earlier pending ones no longer count."""
        self._replacing = {
            p: s for p, s in self._replacing.items() if p != page and s != scan_id
        }

    def _read(self, scan_id: int, path: str) -> None:
        """Starts the scan's own reading (``process``): identifying and decoding it."""
        self._reading.add(scan_id)
        self._runner.submit(scan_id, partial(self._process, path))

    def _decode_for_document(self, scan_id: int) -> None:
        """Decodes the scan without its label, in the current document's format; the
        document knows it is pending from now, before a worker starts it. A labelled
        reading this cancels is done again once the decode has reported."""
        doc = self._doc
        fmt = doc.current.format
        if scan_id in self._reading:
            self._reading.discard(scan_id)
            self._read_again.add(scan_id)
        self._runner.cancel(scan_id)  # required before submitting the id again
        earlier = self._decoding_in.pop(scan_id, None)
        if earlier is not None:
            doc.set_decoding(scan_id, earlier, False)  # cancelled: it will never report
        self._decoding_in[scan_id] = fmt
        doc.set_decoding(scan_id, fmt, True)
        self._runner.submit(scan_id, partial(self._unlabelled, doc.scan(scan_id).path, fmt))

    def _settle_replacement(self, scan_id: int, page: int) -> None:
        """Judges a replacement now, or waits (``Fit.PENDING``) until the scan's reading
        for this document reports."""
        doc = self._doc
        fit = doc.replacement_fit(scan_id, page)
        if fit == Fit.PENDING:
            self._replacing[page] = scan_id
        elif fit == Fit.THIS_PAGE:
            doc.use_scan(scan_id)
        else:
            message = text.replace_rejected(
                page, fit, doc.scan(scan_id), doc.page_in_current(scan_id)
            )
            self.replace_rejected.emit(message)

    def snapshot(self) -> Iterator[bytes]:
        """The recovered file as it is now, for ``save``; later changes do not affect it.

        It is ``Document.save_chunks()``: for a version-1 document that could not
        be repaired, what was recovered, which may be wrong in parts (the save
        warning says so). Raises ValueError when there is nothing to save.
        """
        return self._doc.save_chunks()

    def save(self, path: str, chunks: Iterator[bytes] | None = None) -> None:
        """Starts writing ``chunks`` (default: a snapshot taken now) to ``path`` in the
        background.

        Raises RuntimeError while another save runs or after ``shutdown``, and
        ValueError when no page has been decoded.
        """
        if self._closed:
            raise RuntimeError(text.SAVE_AFTER_CLOSE)
        if self.saving:
            raise RuntimeError(text.SAVE_RUNNING)
        if chunks is None:
            chunks = self.snapshot()
        self._save_path = path
        self._tasks.submit(_SAVE_JOB, partial(_write_chunks, path, chunks, self._save_stop))
        self.refresh()

    def shutdown(self, timeout_ms: int = SHUTDOWN_MS) -> bool:
        """Cancels the scans, the check and the preview's load, lets a running save
        finish, and waits for all of it within ``timeout_ms`` in all. A save still
        running then is told to stop (it leaves no file). Returns whether everything
        stopped in time."""
        deadline = time.monotonic() + max(0, timeout_ms) / 1000
        self._closed = True
        self._timer.stop()
        self._runner.cancel_all()  # every scan stops at its next check from now on
        self._previews.cancel_all()
        self._tasks.cancel(_VERDICT_JOB)  # the save ignores cancelling: see _write_chunks
        self._tasks.cancel(_REPAIR_JOB)

        def left() -> int:
            return max(0, int((deadline - time.monotonic()) * 1000))

        tasks_done = self._tasks.shutdown(left())
        if not tasks_done:
            self._save_stop.set()
        scans_done = self._runner.shutdown(left())
        previews_done = self._previews.shutdown(left())
        return tasks_done and scans_done and previews_done

    # --- Redrawing ---------------------------------------------------------------

    def refresh(self) -> None:
        """Brings the summary up to date and emits ``changed`` now."""
        self._timer.stop()
        if self._closed:
            return
        self._summary = self._safe_summary()
        self.refreshes += 1
        self.changed.emit()

    def _schedule(self, changed: bool = True) -> None:
        """A background result arrived: redraw soon, once per burst. One that
        ``changed`` the document clears the "Saved …" note."""
        if changed:
            self.note = ""
        if not self._closed and not self._timer.isActive():
            self._timer.start()

    def _safe_summary(self) -> Summary:
        """The summary, never hashing or repairing here: a needed check or repair
        runs in the background."""
        self._start_repair()
        job = self._doc.verdict_job()
        if job is None:
            self._verdict_error = None
            return self._doc.summary()  # nothing to hash
        failed = self._verdict_error is not None and self._verdict_error[0] == job.key
        if not failed and job.key != self._verdict_key:
            self._verdict_error = None
            self._tasks.cancel(_VERDICT_JOB)
            self._verdict_key = job.key
            self._tasks.submit(_VERDICT_JOB, job)
        return self._doc.summary(verify=False)

    def _start_repair(self) -> None:
        """Runs the repair the document offers, unless it is running already. A
        repair for other pages still running is cancelled: its result would be
        ignored. The document offers no repair again once one failed for the same
        pages, so nothing is retried."""
        job = self._doc.repair_job()
        if job is None or job.key == self._repair_key:
            return
        self._tasks.cancel(_REPAIR_JOB)
        self._repair_key = job.key
        self._tasks.submit(_REPAIR_JOB, job)

    # --- Background results ------------------------------------------------------

    def _on_started(self, scan_id: int) -> None:
        try:
            self._doc.set_working(scan_id)
        except KeyError:
            return
        self._schedule()

    def _on_finished(self, scan_id: int, work: ScanWork) -> None:
        fmt = self._decoding_in.get(scan_id)  # None: the scan's own reading
        try:
            self._apply(scan_id, work)
        except KeyError:
            return  # the scan was removed
        if work.info is not None or work.outcome is not None or self.work_for(
            scan_id, fmt
        ) is None:
            # A decode for a document that failed keeps the preview of what was read.
            # The page's data is in the document: it is not kept twice.
            self._works[(scan_id, fmt)] = dataclasses.replace(work, outcome=None, payload=None)
        self._schedule()
        self._reported(scan_id, fmt)
        self._settle_pending(scan_id)

    def _reported(self, scan_id: int, fmt: str | None) -> None:
        """A job for the scan reported: its own reading (``fmt`` None) is done, and
        after a decode a reading that the decode cancelled starts again."""
        if fmt is None:
            self._reading.discard(scan_id)
        elif scan_id in self._read_again and scan_id not in self._decoding_in:
            self._read_again.discard(scan_id)
            self._read(scan_id, self._doc.scan(scan_id).path)

    def _settle_pending(self, scan_id: int) -> None:
        """Judges the replacements still waiting for this scan to be read."""
        for page in [p for p, s in self._replacing.items() if s == scan_id]:
            del self._replacing[page]
            self._settle_replacement(scan_id, page)

    def _apply(self, scan_id: int, work: ScanWork) -> None:
        doc = self._doc
        doc.scan(scan_id)  # KeyError for a removed scan, before anything changes
        doc.set_working(scan_id, False)
        fmt = self._decoding_in.pop(scan_id, None)
        if fmt is not None:  # decoded without its label for a document: per format
            doc.set_decoding(scan_id, fmt, False)
            if work.outcome is not None:
                doc.set_outcome(scan_id, work.outcome, fmt)
            else:
                doc.set_unreadable(scan_id, work.reason, fmt)
            return
        if work.info is None:
            doc.set_unreadable(scan_id, work.reason)
            return
        doc.set_identified(scan_id, work.info)
        if work.outcome is None:
            doc.set_unreadable(scan_id, work.reason)
            return
        if work.header is not None and work.info.tag is None:  # a version-1 page
            if work.payload is None:
                doc.set_unreadable(scan_id, work.reason or text.NO_PAGE_DATA)
                return
            doc.set_payload(scan_id, work.payload)
        doc.set_outcome(scan_id, work.outcome)

    def _on_failed(self, scan_id: int, message: str) -> None:
        fmt = self._decoding_in.pop(scan_id, None)
        try:
            self._doc.set_working(scan_id, False)
            if fmt is not None:
                self._doc.set_decoding(scan_id, fmt, False)
            self._doc.set_unreadable(scan_id, message, fmt)
        except KeyError:
            return
        self._schedule()
        self._reported(scan_id, fmt)
        self._settle_pending(scan_id)

    def _on_task_finished(self, job: int, result: object) -> None:
        if job == _REPAIR_JOB:
            self._repair_key = None
            self._doc.accept_repair(result)  # ignored unless for the pages in use
            self._schedule(changed=False)  # a repair does not change the pages
            return
        if job == _VERDICT_JOB:
            self._verdict_key = None
            self._doc.accept_verdict(result)
            self._schedule(changed=False)  # a verdict does not change the pages
            return
        path, self._save_path = self._save_path, None
        self.note = text.saved_message(path, result)
        self.refresh()
        self.save_finished.emit(path, result)

    def _on_task_failed(self, job: int, message: str) -> None:
        if job == _REPAIR_JOB:
            key, self._repair_key = self._repair_key, None
            if key is not None:
                self._doc.fail_repair(key, message)  # not offered again for these pages
            self._schedule(changed=False)
            return
        if job == _VERDICT_JOB:
            if self._verdict_key is not None:
                self._verdict_error = (self._verdict_key, message)  # not retried
            self._verdict_key = None
            self._schedule(changed=False)
            return
        self._save_path = None
        self.refresh()
        self.save_failed.emit(message)


class _RowModel(QAbstractListModel):
    """The rows of the page list: (kind, key, text), updated in place when it can be.

    Kinds: "title" and "section" rows are headings; the kinds of ``Row`` (a page,
    the spares under it, other groups and unreadable scans) can be selected.
    """

    SELECTABLE = (Row.PAGE, Row.SPARE, Row.OTHER, Row.UNREADABLE)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[tuple[str, object, str]] = []
        self._where: dict[tuple[str, object], int] = {}
        self._bold = QFont()
        self._bold.setBold(True)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008, N802
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        kind, _key, label = self._rows[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return label
        if role == Qt.ItemDataRole.FontRole and kind in ("title", "section"):
            return self._bold
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        if self._rows[index.row()][0] in self.SELECTABLE:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return Qt.ItemFlag.ItemIsEnabled

    def row_key(self, row: int) -> tuple[str, object]:
        kind, key, _ = self._rows[row]
        return (kind, key)

    def row_of(self, key: tuple[str, object]) -> int | None:
        return self._where.get(key)

    def texts(self) -> list[str]:
        return [label for _, _, label in self._rows]

    def set_rows(self, rows: list[tuple[str, object, str]]) -> bool:
        """Replaces the rows; returns True when the model was reset (not updated in place)."""
        old = self._rows
        if len(rows) == len(old) and all(
            a[0] == b[0] and a[1] == b[1] for a, b in zip(rows, old, strict=True)
        ):
            changed = [i for i, (a, b) in enumerate(zip(rows, old, strict=True)) if a[2] != b[2]]
            self._rows = rows
            if changed:
                self.dataChanged.emit(self.index(changed[0]), self.index(changed[-1]))
            return False
        self.beginResetModel()
        self._rows = rows
        self._where = {(kind, key): i for i, (kind, key, _) in enumerate(rows)}
        self.endResetModel()
        return True


class ReadTab(QWidget):
    """The view of the reading tab; all wording comes from ``text``."""

    def __init__(
        self, controller: ReadController | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("readTab")
        self.controller = controller if controller is not None else ReadController(self)
        self._selected: tuple[str, object] | None = None
        self.refreshes = 0  # for tests

        self.caution = QLabel(objectName="cautionLabel")
        self.caution.setTextFormat(Qt.TextFormat.PlainText)
        self.caution.setWordWrap(True)
        self.caution.hide()

        self._model = _RowModel(self)
        self.page_list = QListView(objectName="pageList")
        self.page_list.setModel(self._model)
        self.page_list.setUniformItemSizes(True)
        self.page_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.page_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.page_list.selectionModel().selectionChanged.connect(self._on_selection)
        self.add_button = QPushButton(text.ADD_SCANS, objectName="addButton")
        self.add_button.clicked.connect(self._on_add)

        self.preview = ScanPreview(self.controller.preview_runner)
        self.preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.detail = QLabel(objectName="detailLabel")
        self.detail.setTextFormat(Qt.TextFormat.PlainText)
        self.detail.setWordWrap(True)
        self.detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.remove_button = QPushButton(text.REMOVE_SCAN, objectName="removeButton")
        self.remove_button.clicked.connect(self._on_remove)
        self.replace_button = QPushButton(text.REPLACE_SCAN, objectName="replaceButton")
        self.replace_button.clicked.connect(self._on_replace)
        self.use_spare_button = QPushButton(text.USE_SPARE, objectName="useSpareButton")
        self.use_spare_button.clicked.connect(self._on_use_spare)
        self.switch_button = QPushButton(text.SWITCH_DOCUMENT, objectName="switchButton")
        self.switch_button.clicked.connect(self._on_switch)
        self.assign_button = QPushButton(text.ASSIGN_PAGE, objectName="assignButton")
        self.assign_button.clicked.connect(self._on_assign)
        self.start_by_hand_button = QPushButton(
            text.START_BY_HAND, objectName="startByHandButton"
        )
        self.start_by_hand_button.clicked.connect(self._on_start_by_hand)

        self.summary = QLabel(objectName="summaryLabel")
        self.summary.setTextFormat(Qt.TextFormat.PlainText)
        self.save_button = QPushButton(text.SAVE_FILE, objectName="saveButton")
        self.save_button.clicked.connect(self._on_save)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.page_list)
        left_layout.addWidget(self.add_button)
        left_layout.addWidget(self.start_by_hand_button)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.preview, 1)
        right_layout.addWidget(self.detail)
        buttons = QHBoxLayout()
        for button in (
            self.replace_button,
            self.use_spare_button,
            self.switch_button,
            self.assign_button,
            self.remove_button,
        ):
            buttons.addWidget(button)
        buttons.addStretch(1)
        right_layout.addLayout(buttons)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        bar = QHBoxLayout()
        bar.addWidget(self.summary, 1)
        bar.addWidget(self.save_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.caution)
        layout.addWidget(splitter, 1)
        layout.addLayout(bar)

        self.setAcceptDrops(True)
        self.controller.changed.connect(self.refresh)
        self.controller.save_failed.connect(self._on_save_failed)
        self.controller.replace_rejected.connect(self._on_replace_rejected)
        self.refresh()

    # --- Interaction points tests replace -------------------------------------------

    def ask_open_paths(self) -> list[str]:
        paths, _ = QFileDialog.getOpenFileNames(
            self, text.ADD_SCANS_TITLE, "", text.scan_filter()
        )
        return [native_path(p) for p in paths]

    def ask_save_path(self, suggested: str) -> str | None:
        path, _ = QFileDialog.getSaveFileName(self, text.SAVE_TITLE, suggested)
        return native_path(path) or None

    def confirm(self, message: str) -> bool:
        save, cancel = QMessageBox.StandardButton.Save, QMessageBox.StandardButton.Cancel
        clicked = ask(self, QMessageBox.Icon.Question, text.CONFIRM_SAVE_TITLE, message,
                      save | cancel, cancel)  # fmt: skip
        return clicked == save

    def show_error(self, message: str) -> None:
        ask(self, QMessageBox.Icon.Warning, text.ERROR_TITLE, message)

    def ask_replace_path(self, page: int) -> str | None:
        path, _ = QFileDialog.getOpenFileName(
            self, text.replace_title(page), "", text.scan_filter()
        )
        return native_path(path) or None

    def ask_page(self, total: int, suggested: int, scan_name: str) -> int | None:
        dialog = AssignPageDialog(total, suggested, scan_name, self)
        try:
            accepted = dialog.exec() == QDialog.DialogCode.Accepted
            return dialog.page() if accepted else None
        finally:
            dialog.deleteLater()

    def ask_start_by_hand(self, suggested_paper: str) -> tuple[str, int] | None:
        dialog = StartByHandDialog(suggested_paper, self)
        try:
            accepted = dialog.exec() == QDialog.DialogCode.Accepted
            return dialog.choice() if accepted else None
        finally:
            dialog.deleteLater()

    def show_notice(self, message: str) -> None:
        ask(self, QMessageBox.Icon.Information, text.REPLACE_REJECTED_TITLE, message)

    # --- Showing the document ------------------------------------------------------

    def rows(self) -> list[str]:
        """The page list's rows as shown."""
        return self._model.texts()

    def refresh(self) -> None:
        doc = self.controller.document
        rows: list[tuple[str, object, str]] = []
        cur = doc.current
        if cur is not None:
            rows.append(("title", None, text.document_title(cur)))
        self._pages = doc.pages()
        restored = self.controller.summary.restored
        for p in self._pages:
            rows.append((Row.PAGE, p.number, text.page_row(p, restored)))
            for spare in p.spare_ids:
                name = os.path.basename(doc.scan(spare).path)
                rows.append((Row.SPARE, spare, text.spare_row(doc.page_with(spare), name)))
        self._others = {g.key: g for g in doc.others()}
        if self._others:
            rows.append(("section", Row.OTHER, text.NOT_PART_OF_THIS_FILE))
            rows.extend((Row.OTHER, k, text.other_group_row(g)) for k, g in self._others.items())
        unreadable = doc.unreadable()
        if unreadable:
            rows.append(("section", Row.UNREADABLE, text.NOT_READABLE))
            rows.extend((Row.UNREADABLE, s.id, text.unreadable_row(s)) for s in unreadable)
        if self._model.set_rows(rows):
            self._reselect()

        caution = text.caution(doc)
        self.caution.setText(caution or "")
        self.caution.setVisible(caution is not None)
        self.summary.setText(self.controller.summary_text())
        self.save_button.setEnabled(self.controller.can_save)
        self.start_by_hand_button.setEnabled(doc.can_start_by_hand)
        self._show_selection()
        self.refreshes += 1

    def _reselect(self) -> None:
        """After the rows were replaced, selects the same page or scan again."""
        row = self._model.row_of(self._selected) if self._selected is not None else None
        selection = self.page_list.selectionModel()
        if row is None:
            self._selected = None
            selection.clearSelection()
            return
        index = self._model.index(row)
        selection.setCurrentIndex(index, selection.SelectionFlag.ClearAndSelect)

    def _on_selection(self, *_args) -> None:
        indexes = self.page_list.selectionModel().selectedIndexes()
        self._selected = self._model.row_key(indexes[0].row()) if indexes else None
        self._show_selection()

    def _actions(self) -> Actions:
        """What the buttons act on for the selected row (the document decides)."""
        if self._selected is None:
            return NO_ACTIONS
        return self.controller.document.actions(*self._selected)

    def _show_selection(self) -> None:
        lines: tuple[str, ...] = ()
        doc = self.controller.document
        scan_path, work = None, None  # the selected page's scan, for the preview
        restored = False  # whether the selected page's losses were all repaired
        actions = self._actions()
        if self._selected is not None:
            kind, key = self._selected
            if kind == Row.PAGE:
                page = self._pages[key - 1]
                name = None
                if page.scan_id is not None:
                    scan_path = doc.scan(page.scan_id).path
                    work = self.controller.work_for(page.scan_id, doc.current.format)
                    name = os.path.basename(scan_path)
                restored = self.controller.summary.restored
                lines = text.detail_text(page, name, len(self._pages), restored=restored)
                note = self.controller.scan_note(work)
                if note is not None:
                    lines = (*lines, note)
            elif kind == Row.SPARE and actions.use_spare is not None:
                scan_path = doc.scan(key).path
                work = self.controller.work_for(key, doc.current.format)
                lines = text.spare_detail(
                    doc.page_with(key), os.path.basename(scan_path), len(self._pages)
                )
                note = self.controller.scan_note(work)
                if note is not None:
                    lines = (*lines, note)
            elif kind == Row.OTHER:
                lines = text.other_group_detail(self._others[key])
            elif kind == Row.UNREADABLE:
                lines = text.unreadable_detail(doc.scan(key))
        self.detail.setText("\n".join(lines))
        if work is not None:
            self.preview.show_scan(scan_path, work.rotation, work.marks, restored)
        else:
            self.preview.show_scan(scan_path, 0, None)
        self.remove_button.setEnabled(actions.remove is not None)
        self.replace_button.setEnabled(actions.replace is not None)
        self.use_spare_button.setEnabled(actions.use_spare is not None)
        self.switch_button.setEnabled(actions.switch is not None)
        self.assign_button.setEnabled(actions.assign is not None)

    # --- User actions --------------------------------------------------------------

    def select_row(self, row: int) -> None:
        """Selects a row of the page list (as a click would)."""
        index = self._model.index(row)
        self.page_list.selectionModel().setCurrentIndex(
            index, self.page_list.selectionModel().SelectionFlag.ClearAndSelect
        )

    def _on_add(self) -> None:
        paths = self.ask_open_paths()
        if paths:
            self.controller.add_paths(paths)

    def _select(self, key: tuple[str, object]) -> None:
        """Selects the row with this key, if it is listed."""
        row = self._model.row_of(key)
        if row is not None:
            self.select_row(row)

    def _on_remove(self) -> None:
        scan_id = self._actions().remove
        if scan_id is not None:
            self.controller.remove(scan_id)

    def _on_replace(self) -> None:
        page = self._actions().replace
        if page is None:
            return
        path = self.ask_replace_path(page)
        if path:
            self.controller.replace(page, path)

    def _on_replace_rejected(self, message: str) -> None:
        self.show_notice(message)

    def _on_use_spare(self) -> None:
        scan_id = self._actions().use_spare
        if scan_id is None:
            return
        page = self.controller.document.page_with(scan_id).number
        self.controller.use_spare(scan_id)
        self._select((Row.PAGE, page))  # the page, now showing this scan

    def _on_switch(self) -> None:
        key = self._actions().switch
        if key is not None:
            self.controller.switch_document(key)

    def _on_assign(self) -> None:
        scan_id = self._actions().assign
        if scan_id is None:
            return
        doc = self.controller.document
        name = os.path.basename(doc.scan(scan_id).path)
        page = self.ask_page(len(doc.slots()), doc.suggested_page(scan_id), name)
        if page is not None and self.controller.assign(scan_id, page):
            self._select((Row.PAGE, page))

    def _on_start_by_hand(self) -> None:
        doc = self.controller.document
        if not doc.can_start_by_hand:
            return
        selected = None
        if self._selected is not None and self._selected[0] == Row.UNREADABLE:
            selected = self._selected[1]
        choice = self.ask_start_by_hand(self.controller.suggested_paper(selected))
        if choice is not None and doc.can_start_by_hand:
            self.controller.start_by_hand(*choice)

    def _on_save(self) -> None:
        controller = self.controller
        if not controller.can_save:
            return
        # The warning and the snapshot are taken together, before the dialog: its
        # event loop delivers background results, which may change the pages.
        warning = controller.save_warning()
        chunks = controller.snapshot()  # exactly what the warning describes
        if warning is not None and not self.confirm(warning):
            return
        path = self.ask_save_path(controller.document.suggested_name)
        if not path or not controller.can_save:
            return
        controller.save(path, chunks)

    def _on_save_failed(self, message: str) -> None:
        self.show_error(text.save_failed(message))

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        paths = [native_path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            event.acceptProposedAction()
            self.controller.add_paths(paths)
