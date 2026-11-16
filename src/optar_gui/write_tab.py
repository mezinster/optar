# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The "Put on paper" tab: choose a file, see how it will print, create a PDF.

Nothing here reads the chosen file on the interface thread. Choosing a file
starts ``work.prepare_file`` in the background (it reads and hashes the whole
file for the tag); until it returns the tab shows ``text.PREPARING`` and cannot
create. Page count, what protection allows, whether the file is too large and
the printed label follow from the file's size and tag with ``work.print_plan``,
``work.name_preview`` and ``work.name_only_preview``, which are cheap, so they
change at once with the paper, the dot size, the protection or the name.
Creating runs ``work.encode_to_pdf`` in the background.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from optar.format import PARITY
from optar_gui import text
from optar_gui.jobs import JobRunner
from optar_gui.work import (
    FileFacts,
    PrintPlan,
    dot_choices,
    encode_to_pdf,
    name_only_preview,
    name_preview,
    native_path,
    prepare_file,
    print_plan,
    same_file,
)

__all__ = ["WriteTab"]

# How long closing the window waits for running work to stop.
SHUTDOWN_MS = 3000

# The suggested PDF name for a source that is itself a PDF: never the source.
_PDF_OF_PDF_SUFFIX = "-optar.pdf"

# The choices "Compatible" sets: today's printout.
_COMPATIBLE_DOTS = "standard"
_COMPATIBLE_PROTECT = "none"
# The choices a new tab starts with.
_DEFAULT_DOTS = "standard"
_DEFAULT_PROTECT = "standard"

# Job ids on the tab's runner.
_PREPARE_JOB = 1
_CREATE_JOB = 2


def _select(box: QComboBox, value: str) -> None:
    box.setCurrentIndex(box.findData(value))


def _plain_label(name: str) -> QLabel:
    label = QLabel(objectName=name)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    return label


class WriteTab(QWidget):
    """The view and its small amount of state; all wording comes from ``text``.

    ``prepare`` and ``encode`` are the background functions (tests replace them).
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        prepare: Callable[..., FileFacts] = prepare_file,
        encode: Callable[..., int] = encode_to_pdf,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("writeTab")
        self._prepare = prepare
        self._encode = encode
        self._runner = JobRunner(self, max_workers=2)
        self._runner.finished.connect(self._on_finished)
        self._runner.failed.connect(self._on_failed)
        self._path: str | None = None
        self._facts: FileFacts | None = None
        self._read_error: str | None = None
        self._preparing = False
        self._dest: str | None = None  # while a PDF is being created
        self._closed = False

        self.file_edit = QLineEdit(objectName="fileEdit")
        self.file_edit.setReadOnly(True)
        self.choose_button = QPushButton(text.CHOOSE_FILE, objectName="chooseButton")
        self.choose_button.clicked.connect(self._on_choose)
        self.paper_a4 = QRadioButton(text.paper_label("a4"), objectName="paperA4")
        self.paper_letter = QRadioButton(text.paper_label("letter"), objectName="paperLetter")
        self.paper_a4.setChecked(True)
        self._papers = QButtonGroup(self)
        self._papers.addButton(self.paper_a4)
        self._papers.addButton(self.paper_letter)
        self.paper_a4.toggled.connect(self.refresh)
        self.dots_box = QComboBox(objectName="dotsBox")
        for dots, scan_dpi in dot_choices():
            self.dots_box.addItem(text.dot_size_label(dots, scan_dpi), dots)
        _select(self.dots_box, _DEFAULT_DOTS)
        self.dots_box.currentIndexChanged.connect(self.refresh)
        self.protect_box = QComboBox(objectName="protectBox")
        for protect in PARITY:
            self.protect_box.addItem(text.protection_label(protect), protect)
        _select(self.protect_box, _DEFAULT_PROTECT)
        self.protect_box.currentIndexChanged.connect(self.refresh)
        self.compatible_box = QCheckBox(text.COMPATIBLE, objectName="compatibleBox")
        self.compatible_box.toggled.connect(self._on_compatible)
        self._chosen = (_DEFAULT_DOTS, _DEFAULT_PROTECT)  # restored when Compatible is cleared
        self.name_edit = QLineEdit(objectName="nameEdit")
        self.name_edit.textChanged.connect(self.refresh)
        self.prints_as = _plain_label("printsAsLabel")
        self.prints_as.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.warning = _plain_label("warningLabel")
        self.warning.hide()
        self.info = _plain_label("infoLabel")
        self.create_button = QPushButton(text.CREATE_PDF, objectName="createButton")
        self.create_button.clicked.connect(self._on_create)
        self.status = _plain_label("statusLabel")
        self.reminder = _plain_label("reminderLabel")
        self.reminder.setText(text.ACTUAL_SIZE)

        file_row = QHBoxLayout()
        file_row.addWidget(self.file_edit, 1)
        file_row.addWidget(self.choose_button)
        paper_row = QHBoxLayout()
        paper_row.addWidget(self.paper_a4)
        paper_row.addWidget(self.paper_letter)
        paper_row.addStretch(1)
        form = QFormLayout()
        form.addRow(text.FILE_FIELD, file_row)
        form.addRow(text.PAPER_FIELD, paper_row)
        form.addRow(text.DOTS_FIELD, self.dots_box)
        form.addRow(text.PROTECT_FIELD, self.protect_box)
        form.addRow("", self.compatible_box)
        form.addRow(text.NAME_FIELD, self.name_edit)
        form.addRow(text.PRINTS_AS_FIELD, self.prints_as)
        create_row = QHBoxLayout()
        create_row.addWidget(self.create_button)
        create_row.addStretch(1)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.warning)
        layout.addWidget(self.info)
        layout.addLayout(create_row)
        layout.addWidget(self.status)
        layout.addWidget(self.reminder)
        layout.addStretch(1)

        self.setAcceptDrops(True)
        self.refresh()

    # --- Interaction points tests replace -------------------------------------------

    def ask_open_path(self) -> str | None:
        path, _ = QFileDialog.getOpenFileName(self, text.CHOOSE_FILE_TITLE)
        return native_path(path) or None

    def ask_save_path(self, suggested: str) -> str | None:
        path, _ = QFileDialog.getSaveFileName(
            self, text.CREATE_TITLE, suggested, text.PDF_FILTER
        )
        return native_path(path) or None

    # --- State ---------------------------------------------------------------------

    @property
    def paper(self) -> str:
        return "letter" if self.paper_letter.isChecked() else "a4"

    @property
    def dots(self) -> str:
        """The chosen dot size, by its name in optar.format."""
        return self.dots_box.currentData()

    @property
    def protect(self) -> str:
        """The chosen protection, by its name in optar.format."""
        return self.protect_box.currentData()

    @property
    def compatible(self) -> bool:
        return self.compatible_box.isChecked()

    @property
    def prepared(self) -> bool:
        """A file is chosen and what it holds is known (or that it cannot be read)."""
        return self._path is not None and not self._preparing

    @property
    def creating(self) -> bool:
        return self._dest is not None

    def set_file(self, path: str) -> None:
        """Chooses the file to put on paper and starts reading it in the background."""
        if self._closed:
            return
        self._runner.cancel(_PREPARE_JOB)
        self._path = path
        self._facts = None
        self._read_error = None
        self._preparing = True
        self.status.setText("")
        self.file_edit.setText(path)
        self.name_edit.setText(os.path.basename(path))
        self._runner.submit(_PREPARE_JOB, partial(self._prepare, path))
        self.refresh()

    def cancel(self) -> None:
        """Cancels all work without waiting; the tab does nothing more afterwards."""
        self._closed = True
        self._runner.cancel_all()

    def shutdown(self, timeout_ms: int = SHUTDOWN_MS) -> bool:
        """Cancels all work and waits up to ``timeout_ms`` for it to stop."""
        self.cancel()
        return self._runner.shutdown(timeout_ms)

    # --- Showing -------------------------------------------------------------------

    def _plan(self) -> PrintPlan | None:
        """How the chosen file prints with the current choices; None until it is known."""
        if self._preparing or self._facts is None:
            return None
        return print_plan(
            self._facts.size,
            self.name_edit.text(),
            self.paper,
            self.dots,
            self.protect,
            self.compatible,
        )

    def refresh(self, *_args) -> None:
        facts = self._facts
        plan = self._plan()
        info = prints = ""
        warning = None
        if self._preparing:
            info = text.PREPARING
        elif plan is not None and plan.too_large is not None:
            info = text.too_large(plan.too_large, plan.limit)
        elif plan is not None:
            info = text.print_summary(plan.total, facts.size, plan.promised, plan.protected)
            name = self.name_edit.text()
            preview = None
            if not self.compatible:
                preview = name_only_preview(self.paper, self.dots, name, plan.total)
            elif facts.tag is not None:
                preview = name_preview(self.paper, facts.tag, name)
            if preview is not None:
                prints = preview.printed
                warning = text.name_warning(preview.dropped, preview.cut)
        self.info.setText(info)
        self.prints_as.setText(prints)
        self.warning.setText(warning or "")
        self.warning.setVisible(warning is not None)
        too_large = plan is not None and plan.too_large is not None
        self.create_button.setEnabled(
            self.prepared and not self.creating and not self._closed and not too_large
        )

    # --- User actions --------------------------------------------------------------

    def _on_compatible(self, checked: bool) -> None:
        if checked:
            self._chosen = (self.dots, self.protect)
            _select(self.dots_box, _COMPATIBLE_DOTS)
            _select(self.protect_box, _COMPATIBLE_PROTECT)
        else:
            _select(self.dots_box, self._chosen[0])
            _select(self.protect_box, self._chosen[1])
        self.dots_box.setEnabled(not checked)
        self.protect_box.setEnabled(not checked)
        self.refresh()

    def _on_choose(self) -> None:
        path = self.ask_open_path()
        if path:
            self.set_file(path)

    def _on_create(self) -> None:
        if not self.prepared or self.creating or self._closed:
            return
        if self._read_error is not None:
            self.status.setText(text.file_unreadable(self._read_error))
            return
        plan = self._plan()
        if plan is None or plan.too_large is not None:
            if plan is not None:
                self.status.setText(text.too_large(plan.too_large, plan.limit))
            return
        paper = self.paper
        name = self.name_edit.text()
        choices = {"dots": self.dots, "protect": self.protect, "compatible": self.compatible}
        src = self._path
        base = os.path.basename(src)
        stem = os.path.splitext(base)[0] or "optar"
        suggested = stem + ".pdf"
        if os.path.normcase(suggested) == os.path.normcase(base):
            suggested = stem + _PDF_OF_PDF_SUFFIX
        dest = self.ask_save_path(os.path.join(os.path.dirname(src), suggested))
        if not dest or self.creating or self._closed:
            return
        if same_file(src, dest):
            self.status.setText(text.create_failed(text.DEST_IS_SOURCE))
            return
        self._dest = dest
        self.status.setText(text.CREATING)
        self._runner.submit(_CREATE_JOB, partial(self._encode, src, dest, paper, name, **choices))
        self.refresh()

    # --- Background results --------------------------------------------------------

    def _on_finished(self, job: int, result: object) -> None:
        if job == _PREPARE_JOB:
            self._preparing = False
            self._facts = result
        else:
            dest, self._dest = self._dest, None
            self.status.setText(text.created_message(dest, result))
        self.refresh()

    def _on_failed(self, job: int, message: str) -> None:
        if job == _PREPARE_JOB:
            self._preparing = False
            self._read_error = message
            self.status.setText(text.file_unreadable(message))
        else:
            self._dest = None
            self.status.setText(text.create_failed(message))
        self.refresh()

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
            self.set_file(paths[0])
