# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""A row of widgets that wraps onto further lines when it is too narrow.

The order is kept and the items start at the left. Its minimum width is the
narrowest that still fits all of them on two lines, so a narrow pane never asks
for the width of the whole row, and nothing is clipped at that width.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QLayoutItem, QWidget

_SPACING = 6


class FlowLayout(QLayout):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item: QLayoutItem) -> None:  # noqa: N802
        self._items.append(item)
        self.invalidate()

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self) -> Qt.Orientation:  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        margins = self.contentsMargins()
        inner = width - margins.left() - margins.right()
        return self._place(QRect(0, 0, inner, 0), apply=False) + margins.top() + margins.bottom()

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        margins = self.contentsMargins()
        self._place(rect.adjusted(margins.left(), margins.top(), -margins.right(), 0), apply=True)

    def sizeHint(self) -> QSize:  # noqa: N802
        """All of the items on one line."""
        sizes = [item.sizeHint() for item in self._items if not item.isEmpty()]
        width = sum(s.width() for s in sizes) + self._gap() * max(0, len(sizes) - 1)
        return self._with_margins(QSize(width, max((s.height() for s in sizes), default=0)))

    def minimumSize(self) -> QSize:  # noqa: N802
        """The narrowest width that fits the items on two lines, with two lines' height."""
        sizes = [item.minimumSize() for item in self._items if not item.isEmpty()]
        widths = [s.width() for s in sizes]
        gap = self._gap()
        best = sum(widths) + gap * max(0, len(widths) - 1)
        for k in range(1, len(widths)):
            first = sum(widths[:k]) + gap * (k - 1)
            rest = sum(widths[k:]) + gap * (len(widths) - k - 1)
            best = min(best, max(first, rest))
        line = max((s.height() for s in sizes), default=0)
        lines = 1 if len(widths) < 2 else 2
        return self._with_margins(QSize(best, lines * line + (lines - 1) * gap))

    def _gap(self) -> int:
        return self.spacing() if self.spacing() >= 0 else _SPACING

    def _with_margins(self, size: QSize) -> QSize:
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def _place(self, rect: QRect, *, apply: bool) -> int:
        """Lays the items out in ``rect`` from the left, wrapping; returns the height used."""
        gap = self._gap()
        x, y, line = rect.x(), rect.y(), 0
        for item in self._items:
            if item.isEmpty():
                continue
            size = item.sizeHint()
            if x > rect.x() and x + size.width() > rect.right() + 1:
                x, y, line = rect.x(), y + line + gap, 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), size))
            x += size.width() + gap
            line = max(line, size.height())
        return y + line - rect.y()
