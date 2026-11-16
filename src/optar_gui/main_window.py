# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The application window: one tab per task, reading from paper first."""

from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow, QMessageBox, QTabWidget, QWidget

from optar_gui import text
from optar_gui.dialogs import ask
from optar_gui.read_tab import ReadController, ReadTab
from optar_gui.write_tab import WriteTab

__all__ = ["MainWindow"]


class MainWindow(QMainWindow):
    """A tab widget holding the reading tab (``readTab``) and the writing tab (``writeTab``)."""

    def __init__(
        self, controller: ReadController | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(text.WINDOW_TITLE)
        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)
        self.read_tab = ReadTab(controller)
        self.add_tab(self.read_tab, text.READ_TAB)
        self.write_tab = WriteTab()
        self.add_tab(self.write_tab, text.WRITE_TAB)
        self.resize(1000, 700)

    def add_tab(self, widget: QWidget, title: str) -> None:
        self.tabs.addTab(widget, title)

    def ask_wait(self) -> bool:
        """Asks whether to wait for a file still being written; True to wait."""
        yes, no = QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No
        clicked = ask(self, QMessageBox.Icon.Question, text.STILL_WRITING_TITLE,
                      text.STILL_WRITING, yes | no, yes)  # fmt: skip
        return clicked != no

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        # A recovered file being saved or a PDF being created would be stopped
        # (and not written) after the time budget: the user may wait instead, and
        # then everything keeps running.
        if (self.read_tab.controller.saving or self.write_tab.creating) and self.ask_wait():
            event.ignore()
            return
        # Hidden first: a running stage can take seconds to notice it was
        # cancelled, and the window must not look frozen meanwhile. Then all
        # work of both tabs is cancelled with a bounded wait; the writing tab's
        # is cancelled first so that it stops while the reading tab waits.
        self.hide()
        self.write_tab.cancel()
        self.read_tab.controller.shutdown()
        self.write_tab.shutdown()
        event.accept()
