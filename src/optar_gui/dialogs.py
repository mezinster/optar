# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The application's small dialogs: which page a scan is, starting a document by
hand, and plain-text message boxes.

They only collect values; what is allowed is decided by the document and the
controller before a dialog is opened. All wording comes from ``text``.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from optar.format import PAPERS
from optar_gui import text
from optar_gui.document import MAX_TOTAL_PAGES

__all__ = ["AssignPageDialog", "StartByHandDialog", "ask"]

# The standard buttons the application uses: Qt's name for each, and the name
# text.button knows it by.
_BUTTON_NAMES = {"Ok": "ok", "Cancel": "cancel", "Save": "save", "Yes": "yes", "No": "no"}


def _captions(box: QMessageBox | QDialogButtonBox) -> None:
    """Sets each standard button's text from the catalogue, not from Qt's own translation."""
    for qt_name, name in _BUTTON_NAMES.items():
        button = box.button(getattr(type(box).StandardButton, qt_name))
        if button is not None:
            button.setText(text.button(name))


def ask(
    parent: QWidget,
    icon: QMessageBox.Icon,
    title: str,
    message: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
) -> QMessageBox.StandardButton:
    """Shows a message box and returns the button clicked (``NoButton`` if none).

    The message is always plain text: it holds file names and label text read from
    scans, which Qt would otherwise take for rich text when they look like markup.
    """
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setTextFormat(Qt.TextFormat.PlainText)
    box.setText(message)
    box.setStandardButtons(buttons)
    _captions(box)
    if default != QMessageBox.StandardButton.NoButton:
        box.setDefaultButton(default)
    try:
        box.exec()
        clicked = box.clickedButton()
        if clicked is None:
            return QMessageBox.StandardButton.NoButton
        return box.standardButton(clicked)
    finally:
        box.deleteLater()


def _buttons(dialog: QDialog) -> QDialogButtonBox:
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    _captions(buttons)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    return buttons


def _prompt(words: str) -> QLabel:
    label = QLabel()
    label.setTextFormat(Qt.TextFormat.PlainText)  # it may hold a scan's file name
    label.setText(words)
    label.setWordWrap(True)
    return label


class AssignPageDialog(QDialog):
    """Asks which page, 1 to ``total``, a scan is; ``page()`` is the answer."""

    def __init__(
        self,
        total: int,
        suggested: int = 1,
        scan_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(text.ASSIGN_TITLE)
        self.spin = QSpinBox(objectName="pageSpin")
        self.spin.setRange(1, max(total, 1))
        self.spin.setSuffix(text.of_pages(max(total, 1)))
        self.spin.setValue(suggested)
        form = QFormLayout()
        form.addRow(text.PAGE_FIELD, self.spin)
        layout = QVBoxLayout(self)
        if scan_name:
            layout.addWidget(_prompt(text.assign_prompt(scan_name)))
        layout.addLayout(form)
        layout.addWidget(_buttons(self))

    def page(self) -> int:
        return self.spin.value()


class StartByHandDialog(QDialog):
    """Asks for the paper and the page count of a document started by hand;
    ``choice()`` is ``(paper name, total)``, the paper's name as in ``optar.format``."""

    def __init__(self, suggested_paper: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(text.START_BY_HAND_TITLE)
        self._papers = list(PAPERS)
        self.paper = QComboBox(objectName="paperCombo")
        self.paper.addItems([text.paper_label(name) for name in self._papers])
        if suggested_paper in self._papers:
            self.paper.setCurrentIndex(self._papers.index(suggested_paper))
        self.total = QSpinBox(objectName="totalSpin")
        self.total.setRange(1, MAX_TOTAL_PAGES)
        form = QFormLayout()
        form.addRow(text.PAPER_FIELD, self.paper)
        form.addRow(text.TOTAL_FIELD, self.total)
        layout = QVBoxLayout(self)
        layout.addWidget(_prompt(text.START_BY_HAND_PROMPT))
        layout.addLayout(form)
        layout.addWidget(_buttons(self))

    def choice(self) -> tuple[str, int]:
        return self._papers[self.paper.currentIndex()], self.total.value()
