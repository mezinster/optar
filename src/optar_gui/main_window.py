# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The application window: one tab per task, reading from paper first."""

from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget

from optar_gui import text
from optar_gui.read_tab import ReadController, ReadTab

__all__ = ["MainWindow"]


class MainWindow(QMainWindow):
    """A tab widget holding the reading tab (``readTab``); later tabs use ``add_tab``."""

    def __init__(
        self, controller: ReadController | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(text.WINDOW_TITLE)
        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)
        self.read_tab = ReadTab(controller)
        self.add_tab(self.read_tab, text.READ_TAB)
        self.resize(1000, 700)

    def add_tab(self, widget: QWidget, title: str) -> None:
        self.tabs.addTab(widget, title)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        # Cancels all work and waits a bounded time; never asks anything.
        self.read_tab.controller.shutdown()
        event.accept()
