# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The reading tab's small dialogs: which page a scan is, and starting a document by hand.

They only collect values; what is allowed is decided by the document and the
controller before a dialog is opened. All wording comes from ``text``.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from optar.format import PAPERS
from optar_gui import text
from optar_gui.document import MAX_TOTAL_PAGES

__all__ = ["AssignPageDialog", "StartByHandDialog"]


def _buttons(dialog: QDialog) -> QDialogButtonBox:
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    return buttons


def _prompt(words: str) -> QLabel:
    label = QLabel(words)
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
