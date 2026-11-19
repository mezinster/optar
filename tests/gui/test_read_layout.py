# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Room for the Read tab's list: its share of the window, rows that are elided and
not scrolled, each row's full text as a plain-text tooltip, the step of a scan being
read, off-screen."""

import pytest
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtGui import Qt as GuiQt
from PySide6.QtWidgets import QStyle, QStyleOptionViewItem

from optar_gui import text
from optar_gui.document import Progress
from optar_gui.main_window import MainWindow
from optar_gui.read_tab import ReadController
from optar_gui.work import process_scan
from tests.gui.conftest import _OFFSCREEN_FONT_WARNINGS as OFFSCREEN_FONT_WARNINGS
from tests.gui.conftest import MARK
from tests.gui.test_language_switch import choose
from tests.gui.test_progress import Stepper

TIMEOUT = 60_000  # ms
# The conftest's own ignore marker would hide a module-level one; each test carries this.
quiet = pytest.mark.qt_log_ignore(
    "This plugin does not support propagateSizeHints", *OFFSCREEN_FONT_WARNINGS
)
LONG = "a-rather-long-file-name-for-the-archive-of-2026-and-then-some.png"  # 63 characters


@pytest.fixture
def make_window(qtbot):
    controllers = []

    def make(process):
        controller = ReadController(process=process, max_workers=1)
        controllers.append(controller)
        window = MainWindow(controller)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    yield make
    for controller in controllers:
        controller.shutdown(TIMEOUT)


def tooltips(tab):
    model = tab.page_list.model()
    return [model.index(i).data(Qt.ItemDataRole.ToolTipRole) for i in range(model.rowCount())]


@quiet
def test_the_list_gets_about_two_fifths_of_the_window_and_neither_pane_can_vanish(make_window):
    window = make_window(Stepper())
    splitter = window.read_tab.splitter
    first, second = splitter.sizes()
    assert 0.34 <= first / (first + second) <= 0.42
    assert window.read_tab.page_list.viewport().width() >= 340
    assert not splitter.childrenCollapsible()
    assert splitter.count() == 2 and splitter.handle(1).isEnabled()  # the user can move it
    splitter.setSizes([0, 1000])
    assert min(splitter.sizes()) > 0
    splitter.setSizes([1000, 0])
    assert min(splitter.sizes()) > 0


@quiet
def test_the_window_still_fits_a_small_screen(make_window):
    window = make_window(Stepper())
    hint = window.minimumSizeHint()
    assert hint.width() <= 1366 and hint.height() <= 768
    assert (window.width(), window.height()) == (1000, 700)


@quiet
def test_a_long_row_is_elided_and_not_scrolled(qtbot, make_window, tmp_path):
    bad = tmp_path / LONG
    bad.write_bytes(b"not an image")
    stepper = Stepper()
    window = make_window(stepper)
    tab = window.read_tab
    tab.controller.add_paths([f"/scans/{LONG}"])  # being read, in the stepper's hands
    view = tab.page_list
    assert any(LONG in r for r in tab.rows())
    assert view.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert not view.horizontalScrollBar().isVisible()
    assert view.horizontalScrollBar().maximum() == 0
    stepper.advance(LONG)
    tab.controller.remove(next(s.id for s in tab.controller.document.scans()))
    # An unreadable scan, a plain row.
    tab.controller._process = process_scan
    tab.controller.add_paths([str(bad)])
    qtbot.waitUntil(lambda: text.NOT_READABLE in tab.rows(), timeout=TIMEOUT)
    assert any(LONG in r for r in tab.rows())
    assert not view.horizontalScrollBar().isVisible()
    assert view.horizontalScrollBar().maximum() == 0
    assert view.textElideMode() == Qt.TextElideMode.ElideMiddle


@quiet
def test_each_row_has_its_full_text_as_a_tooltip(qtbot, make_window, tmp_path):
    bad = tmp_path / "notes.png"
    bad.write_bytes(b"not an image")
    window = make_window(process_scan)
    tab = window.read_tab
    tab.controller.add_paths([str(bad)])
    qtbot.waitUntil(lambda: text.NOT_READABLE in tab.rows(), timeout=TIMEOUT)
    assert tab.rows() == [text.NOT_READABLE, tab.rows()[1]]
    assert tooltips(tab) == tab.rows()  # the heading and the unreadable scan


@quiet
def test_the_tooltip_of_a_scan_being_read_is_its_row_and_markup_is_shown_literally(
    qtbot, make_window
):
    stepper = Stepper()
    window = make_window(stepper)
    tab = window.read_tab
    name = "<b>x<i>&amp;.png"
    tab.controller.add_paths([f"/scans/{name}"])
    row = f"{name} · Waiting"
    assert row in tab.rows()
    assert tooltips(tab) != tab.rows()  # escaped for display, so not the raw text
    tip = tooltips(tab)[tab.rows().index(row)]
    assert GuiQt.mightBeRichText(tip)  # declared rich, and the markup in it is escaped
    assert "<b>" not in tip and "&lt;b&gt;x&lt;i&gt;&amp;amp;.png" in tip
    # Plain rows are the row itself and are shown as plain text.
    heading = tooltips(tab)[tab.rows().index(text.BEING_READ_SECTION)]
    assert heading == text.BEING_READ_SECTION and not GuiQt.mightBeRichText(heading)
    stepper.advance(name)
    tab.controller.remove(next(s.id for s in tab.controller.document.scans()))


def step_room(tab, row, step):
    """The width the delegate gives the step of ``row``, and what ``step`` needs."""
    view = tab.page_list
    index = view.model().index(row)
    opt = QStyleOptionViewItem()
    opt.widget = view
    opt.font = view.font()
    opt.rect = view.visualRect(index)
    opt.state = QStyle.StateFlag.State_Enabled
    area = view.style().subElementRect(QStyle.SubElement.SE_ItemViewItemText, opt, view)
    area = area.adjusted(2, 0, -2, 0)
    metrics = QFontMetrics(view.font())
    _name, _bar, step_rect = view.itemDelegate().layout(area, metrics, "scan.png", 0)
    return step_rect.width(), metrics.horizontalAdvance(step)


def longest_english_step():
    names = ("open", "find", "identify", "read", "slow-sample", "other")
    steps = [text.step_text(None), text.step_text(Progress("slow-fit", 3, 5, 0.5))]
    steps += [text.step_text(Progress(name, 0, 1, 0.0)) for name in names]
    return max(steps, key=len)


@quiet
def test_the_step_of_a_scan_being_read_is_not_elided_at_the_default_size(make_window):
    stepper = Stepper()
    window = make_window(stepper)
    tab = window.read_tab
    tab.controller.add_paths(["/scans/page.png"])
    row = tab.rows().index("page.png · Waiting")
    longest = longest_english_step()
    assert len(longest) > 20
    for step in (longest, longest + longest[: int(len(longest) * 0.6)]):
        have, need = step_room(tab, row, step)
        assert have >= need, (step, have, need)
    stepper.advance("page.png")
    tab.controller.remove(next(s.id for s in tab.controller.document.scans()))


@quiet
def test_the_row_of_a_scan_being_read_is_two_lines_high(make_window):
    stepper = Stepper()
    window = make_window(stepper)
    tab = window.read_tab
    tab.controller.add_paths(["/scans/page.png"])
    view = tab.page_list
    model = view.model()
    row = tab.rows().index("page.png · Waiting")
    delegate = view.itemDelegate()
    option = QStyleOptionViewItem()
    option.font = view.font()
    heading = delegate.sizeHint(option, model.index(tab.rows().index(text.BEING_READ_SECTION)))
    being = delegate.sizeHint(option, model.index(row))
    assert being.height() >= 2 * QFontMetrics(view.font()).height()
    assert heading.height() < being.height()
    assert delegate.sizeHint(option, QModelIndex()).width() == 0
    stepper.advance("page.png")
    tab.controller.remove(next(s.id for s in tab.controller.document.scans()))


@quiet
def test_tooltips_are_worded_again_when_the_language_changes(qtbot, make_window, stub):
    stepper = Stepper()
    window = make_window(stepper)
    tab = window.read_tab
    tab.controller.add_paths(["/scans/page.png"])
    before = tooltips(tab)
    assert before == tab.rows() and MARK not in "".join(before)
    stepper.advance("page.png")
    qtbot.waitUntil(lambda: "page.png · Opening the file" in tab.rows(), timeout=TIMEOUT)
    choose(window, stub)
    after = tooltips(tab)
    assert after == tab.rows()
    assert all(MARK in tip for tip in after)
    assert any(tip.startswith("page.png · " + MARK) for tip in after)
    choose(window, None)
    assert tooltips(tab) == tab.rows() and MARK not in "".join(tooltips(tab))
    tab.controller.remove(next(s.id for s in tab.controller.document.scans()))
