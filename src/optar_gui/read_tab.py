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
- Saving streams ``Document.chunks()`` (a snapshot taken when the user has
  confirmed the warning) through ``optar.fileio.replacing`` in the background,
  so an existing file is untouched by a failed save and a large file never
  freezes the window.
- Scans are read and decoded only by background jobs. Saving and checking run on
  a second runner, so they never wait behind scans being decoded.
- Closing cancels every scan and check, lets a running save finish, and waits
  for all of it within one time budget; a save still running when the budget
  runs out is told to stop and leaves no file.
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
    QFileDialog,
    QFrame,
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
from optar_gui import text
from optar_gui.document import DocState, Document, Summary, expand_paths
from optar_gui.jobs import JobRunner
from optar_gui.work import Cancelled, ScanWork, process_scan

__all__ = ["REFRESH_MS", "SHUTDOWN_MS", "ReadController", "ReadTab"]

# How long background results are gathered before the view is redrawn.
REFRESH_MS = 100
# How long closing the window waits for running work to stop.
SHUTDOWN_MS = 3000

# Job ids on the controller's second runner (scan jobs use the scan ids).
_VERDICT_JOB = 1
_SAVE_JOB = 2


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
    """

    changed = Signal()
    save_finished = Signal(str, int)
    save_failed = Signal(str)

    def __init__(
        self,
        parent: QObject | None = None,
        process: Callable[..., ScanWork] = process_scan,
        max_workers: int | None = None,
    ) -> None:
        super().__init__(parent)
        self._doc = Document()
        self._process = process
        self._runner = JobRunner(self, max_workers)
        self._runner.started.connect(self._on_started)
        self._runner.finished.connect(self._on_finished)
        self._runner.failed.connect(self._on_failed)
        self._tasks = JobRunner(self, max_workers=2)  # saving and checking
        self._tasks.finished.connect(self._on_task_finished)
        self._tasks.failed.connect(self._on_task_failed)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self.refresh)
        self._works: dict[int, ScanWork] = {}
        self._summary = self._doc.summary()
        self._verdict_key: tuple | None = None  # what the running verdict job hashes
        self._verdict_error: tuple[tuple, str] | None = None  # (key, message) of a failed job
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
    def summary(self) -> Summary:
        """The document's summary as of the last redraw; never hashes on its own."""
        return self._summary

    @property
    def checking(self) -> bool:
        """Whether a fingerprint check is running in the background."""
        return self._verdict_key is not None

    @property
    def check_error(self) -> str:
        """Why the check of the current pages failed, or ""."""
        return self._verdict_error[1] if self._verdict_error is not None else ""

    def summary_text(self) -> str:
        """The bottom bar's text."""
        if self._summary.state == DocState.CHECKING and self.check_error:
            line = text.check_failed(self.check_error)
        else:
            line = text.summary_line(self._summary)
        return text.summary_bar(line, self.note)

    @property
    def saving(self) -> bool:
        return self._save_path is not None

    @property
    def can_save(self) -> bool:
        return self._doc.can_save and not self.saving and not self._closed

    def work_for(self, scan_id: int) -> ScanWork | None:
        """The last processing result of a scan (its outcome is in the document)."""
        return self._works.get(scan_id)

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
                self._runner.submit(scan_id, partial(self._process, path))
        self.refresh()

    def remove(self, scan_id: int) -> None:
        self._runner.cancel(scan_id)
        self._doc.remove_scan(scan_id)
        self.note = ""
        self._works.pop(scan_id, None)
        self.refresh()

    def snapshot(self) -> Iterator[bytes]:
        """The recovered file as it is now, for ``save``; later changes do not affect it.

        Raises ValueError when no page has been decoded.
        """
        return self._doc.chunks()

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
        """Cancels the scans and the check, lets a running save finish, and waits for
        all of it within ``timeout_ms`` in all. A save still running then is told to
        stop (it leaves no file). Returns whether everything stopped in time."""
        deadline = time.monotonic() + max(0, timeout_ms) / 1000
        self._closed = True
        self._timer.stop()
        self._runner.cancel_all()  # every scan stops at its next check from now on
        self._tasks.cancel(_VERDICT_JOB)  # the save ignores cancelling: see _write_chunks

        def left() -> int:
            return max(0, int((deadline - time.monotonic()) * 1000))

        tasks_done = self._tasks.shutdown(left())
        if not tasks_done:
            self._save_stop.set()
        scans_done = self._runner.shutdown(left())
        return tasks_done and scans_done

    # --- Redrawing ---------------------------------------------------------------

    def refresh(self) -> None:
        """Brings the summary up to date and emits ``changed`` now."""
        self._timer.stop()
        if self._closed:
            return
        self._summary = self._safe_summary()
        self.refreshes += 1
        self.changed.emit()

    def _schedule(self) -> None:
        """A background result changed the document: redraw soon, once per burst."""
        self.note = ""
        if not self._closed and not self._timer.isActive():
            self._timer.start()

    def _safe_summary(self) -> Summary:
        """The summary, never hashing here: a needed check runs in the background."""
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

    # --- Background results ------------------------------------------------------

    def _on_started(self, scan_id: int) -> None:
        try:
            self._doc.set_working(scan_id)
        except KeyError:
            return
        self._schedule()

    def _on_finished(self, scan_id: int, work: ScanWork) -> None:
        try:
            self._apply(scan_id, work)
        except KeyError:
            return  # the scan was removed
        self._works[scan_id] = dataclasses.replace(work, outcome=None)
        self._schedule()

    def _apply(self, scan_id: int, work: ScanWork) -> None:
        doc = self._doc
        doc.scan(scan_id)  # KeyError for a removed scan, before anything changes
        if work.info is None:
            doc.set_unreadable(scan_id, work.reason)
            return
        doc.set_identified(scan_id, work.info)
        if work.outcome is not None:
            doc.set_outcome(scan_id, work.outcome)
        else:
            doc.set_unreadable(scan_id, work.reason)

    def _on_failed(self, scan_id: int, message: str) -> None:
        try:
            self._doc.set_unreadable(scan_id, message)
        except KeyError:
            return
        self._schedule()

    def _on_task_finished(self, job: int, result: object) -> None:
        if job == _VERDICT_JOB:
            self._verdict_key = None
            self._doc.accept_verdict(result)
            self._schedule()
            return
        path, self._save_path = self._save_path, None
        self.note = text.saved_message(path, result)
        self.refresh()
        self.save_finished.emit(path, result)

    def _on_task_failed(self, job: int, message: str) -> None:
        if job == _VERDICT_JOB:
            if self._verdict_key is not None:
                self._verdict_error = (self._verdict_key, message)  # not retried
            self._verdict_key = None
            self._schedule()
            return
        self._save_path = None
        self.refresh()
        self.save_failed.emit(message)


class _RowModel(QAbstractListModel):
    """The rows of the page list: (kind, key, text), updated in place when it can be.

    Kinds: "title" and "section" rows are headings; "page" (key: page number),
    "other" (key: group key) and "unreadable" (key: scan id) can be selected.
    """

    SELECTABLE = ("page", "other", "unreadable")

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

        self.preview = QFrame(objectName="previewPlaceholder")  # the preview goes here
        self.preview.setFrameShape(QFrame.Shape.StyledPanel)
        self.preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.detail = QLabel(objectName="detailLabel")
        self.detail.setTextFormat(Qt.TextFormat.PlainText)
        self.detail.setWordWrap(True)
        self.detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.remove_button = QPushButton(text.REMOVE_SCAN, objectName="removeButton")
        self.remove_button.clicked.connect(self._on_remove)

        self.summary = QLabel(objectName="summaryLabel")
        self.summary.setTextFormat(Qt.TextFormat.PlainText)
        self.save_button = QPushButton(text.SAVE_FILE, objectName="saveButton")
        self.save_button.clicked.connect(self._on_save)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.page_list)
        left_layout.addWidget(self.add_button)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.preview, 1)
        right_layout.addWidget(self.detail)
        buttons = QHBoxLayout()
        buttons.addWidget(self.remove_button)
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
        self.refresh()

    # --- Interaction points tests replace -------------------------------------------

    def ask_open_paths(self) -> list[str]:
        paths, _ = QFileDialog.getOpenFileNames(
            self, text.ADD_SCANS_TITLE, "", text.scan_filter()
        )
        return paths

    def ask_save_path(self, suggested: str) -> str | None:
        path, _ = QFileDialog.getSaveFileName(self, text.SAVE_TITLE, suggested)
        return path or None

    def confirm(self, message: str) -> bool:
        answer = QMessageBox.question(
            self,
            text.CONFIRM_SAVE_TITLE,
            message,
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return answer == QMessageBox.StandardButton.Save

    def show_error(self, message: str) -> None:
        QMessageBox.warning(self, text.ERROR_TITLE, message)

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
        rows.extend(("page", p.number, text.page_row(p)) for p in self._pages)
        self._others = {g.key: g for g in doc.others()}
        if self._others:
            rows.append(("section", "other", text.NOT_PART_OF_THIS_FILE))
            rows.extend(("other", k, text.other_group_row(g)) for k, g in self._others.items())
        unreadable = doc.unreadable()
        if unreadable:
            rows.append(("section", "unreadable", text.NOT_READABLE))
            rows.extend(("unreadable", s.id, text.unreadable_row(s)) for s in unreadable)
        if self._model.set_rows(rows):
            self._reselect()

        caution = text.caution(doc)
        self.caution.setText(caution or "")
        self.caution.setVisible(caution is not None)
        self.summary.setText(self.controller.summary_text())
        self.save_button.setEnabled(self.controller.can_save)
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

    def _selected_scan(self) -> int | None:
        """The scan the Remove button would remove."""
        if self._selected is None:
            return None
        kind, key = self._selected
        if kind == "page":
            return self._pages[key - 1].scan_id
        if kind == "unreadable":
            return key
        return None

    def _show_selection(self) -> None:
        lines: tuple[str, ...] = ()
        doc = self.controller.document
        if self._selected is not None:
            kind, key = self._selected
            if kind == "page":
                page = self._pages[key - 1]
                name = None
                if page.scan_id is not None:
                    name = os.path.basename(doc.scan(page.scan_id).path)
                lines = text.detail_text(page, name, len(self._pages))
            elif kind == "other":
                lines = text.other_group_detail(self._others[key])
            elif kind == "unreadable":
                lines = text.unreadable_detail(doc.scan(key))
        self.detail.setText("\n".join(lines))
        self.remove_button.setEnabled(self._selected_scan() is not None)

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

    def _on_remove(self) -> None:
        scan_id = self._selected_scan()
        if scan_id is not None:
            self.controller.remove(scan_id)

    def _on_save(self) -> None:
        controller = self.controller
        if not controller.can_save:
            return
        warning = controller.save_warning()
        if warning is not None and not self.confirm(warning):
            return
        chunks = controller.snapshot()  # what the warning described
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
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            event.acceptProposedAction()
            self.controller.add_paths(paths)
