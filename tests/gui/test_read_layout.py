# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Room for the Read tab's list: its share of the window, rows that are elided and
not scrolled, each row's full text as a plain-text tooltip, the step of a scan being
read, off-screen.

Every test runs under the platform's own font and under a "wide" one of a fixed
width in pixels (what the Windows job measured), and no bound is a pixel count
measured with one font. ``OPTAR_TEST_FONT_SCALE`` (tests/gui/conftest.py) widens the
platform's font first: the rehearsal on Linux of a platform whose font is wider.
"""

import threading

import pytest
from PySide6.QtCore import QModelIndex, QRect, Qt
from PySide6.QtGui import QFont, QFontMetrics, QTextDocument
from PySide6.QtGui import Qt as GuiQt
from PySide6.QtWidgets import QPushButton, QStyle, QStyleOptionViewItem

from optar import i18n
from optar_gui import text
from optar_gui.document import Progress
from optar_gui.main_window import MainWindow
from optar_gui.read_tab import ReadController, _plain_tooltip
from optar_gui.work import Cancelled, ScanWork, process_scan
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
DEFAULT_SIZE = (1000, 700)  # MainWindow's size at start
SMALL_SCREEN = (1366, 768)
# The list's share of the splitter at the default size (read_tab.LIST_SHARE is 38). It
# may take more only as far as its own widest button needs (see list_share_ok).
SHARE = (0.36, 0.40)


# The Windows job's log (tests/gui/test_read_layout.py at 2a73506) measured this
# string, 41 characters, at 492 px in the list's font: 12 px a character, about 1.9
# times the Linux off-screen font. The "wide" variant is that width, and no wider.
REFERENCE = "Slower reader: pass 4 of 5Slower reader: "
WIDE_CHARACTER = 492 / len(REFERENCE)  # px


def character_width(font: QFont) -> float:
    """The average width of a character of REFERENCE in ``font``, in pixels."""
    return QFontMetrics(font).horizontalAdvance(REFERENCE) / len(REFERENCE)


def font_of_width(font: QFont, target: float) -> QFont:
    """``font`` at the largest size whose characters are no wider than ``target``;
    ``font`` itself when it is already that wide or wider (never shrunk)."""
    if character_width(font) >= target:
        return font
    wider = QFont(font)
    for _ in range(6):  # the width does not follow the size exactly (hinting)
        wider.setPointSizeF(wider.pointSizeF() * target / character_width(wider))
    while character_width(wider) > target:
        wider.setPointSizeF(wider.pointSizeF() - 0.05)
    return wider if character_width(wider) > character_width(font) else font


@pytest.fixture(params=["own", "wide"], ids=["font-own", "font-wide"])
def font_scale(request, qapp):
    """The platform's own font, and a font with characters WIDE_CHARACTER px wide (the
    guard for Windows and macOS); on a platform whose font is that wide already the
    two are the same."""
    font = QFont(qapp.font())
    if request.param == "wide":
        qapp.setFont(font_of_width(font, WIDE_CHARACTER))
    yield character_width(qapp.font())
    qapp.setFont(font)


@pytest.fixture
def make_window(qtbot, font_scale):
    controllers = []

    def make(process, language=None, tab=0):
        """The window, shown, in ``language`` (chosen before it is shown) with tab ``tab``
        current at first."""
        controller = ReadController(process=process, max_workers=1)
        controllers.append(controller)
        window = MainWindow(controller)
        qtbot.addWidget(window)
        if language is not None:
            choose(window, language)
        window.tabs.setCurrentIndex(tab)
        window.show()
        qtbot.waitExposed(window)
        return window

    yield make
    for controller in controllers:
        controller.shutdown(TIMEOUT)


def list_share_ok(tab):
    """(share, whether it is right): SHARE, or more only as far as the list's pane
    needs for its own widest button under a wide font."""
    first, second = tab.splitter.sizes()
    share = first / (first + second)
    needs = tab.splitter.widget(0).minimumSizeHint().width() / (first + second)
    return share, SHARE[0] <= share <= max(SHARE[1], needs + 0.005)


def tooltips(tab):
    model = tab.page_list.model()
    return [model.index(i).data(Qt.ItemDataRole.ToolTipRole) for i in range(model.rowCount())]


@quiet
def test_the_list_gets_about_two_fifths_of_the_window_and_neither_pane_can_vanish(make_window):
    window = make_window(Stepper())
    splitter = window.read_tab.splitter
    first, second = splitter.sizes()
    share, ok = list_share_ok(window.read_tab)
    assert ok, share
    assert window.read_tab.page_list.viewport().width() >= 0.9 * first  # the list fills it
    assert not splitter.childrenCollapsible()
    assert splitter.count() == 2 and splitter.handle(1).isEnabled()  # the user can move it
    splitter.setSizes([0, 1000])
    assert min(splitter.sizes()) > 0
    splitter.setSizes([1000, 0])
    assert min(splitter.sizes()) > 0


@quiet
def test_the_list_has_its_share_at_the_default_size_in_every_language(make_window):
    assert tuple(i18n.languages()) == i18n.ORDER
    for code in i18n.ORDER:
        window = make_window(Stepper(), language=code)
        first, second = window.read_tab.splitter.sizes()
        share, ok = list_share_ok(window.read_tab)
        viewport = window.read_tab.page_list.viewport().width()
        assert (window.width(), window.height()) == DEFAULT_SIZE
        assert ok, (code, share)
        assert viewport >= 0.9 * first, (code, viewport, first)
        buttons = window.read_tab.splitter.widget(1).findChildren(QPushButton)
        pane = window.read_tab.splitter.widget(1).rect()
        for button in buttons:  # nothing clipped or hanging out of the pane at default size
            assert pane.contains(button.geometry()), (code, button.text())


@quiet
def test_the_buttons_wrap_instead_of_fixing_the_panes_width_and_keep_their_order(make_window):
    window = make_window(Stepper(), language="ru")
    tab = window.read_tab
    buttons = [
        tab.replace_button,
        tab.use_spare_button,
        tab.switch_button,
        tab.assign_button,
        tab.remove_button,
    ]
    placed = sorted(buttons, key=lambda b: (b.geometry().top(), b.geometry().left()))
    assert placed == buttons  # reading order is the order of controls
    assert len({b.geometry().top() for b in buttons}) >= 2  # wrapped in Russian
    pane = tab.splitter.widget(1)
    for button in buttons:  # nothing clipped or overlapping
        assert pane.rect().contains(button.geometry()), button.text()
        others = [b for b in buttons if b is not button]
        assert not any(button.geometry().intersects(b.geometry()) for b in others)
    # The pane's minimum is no wider than its widest button needs (the row wraps as far
    # as one button a line), and leaves the list its share at the default size.
    widest = max(b.sizeHint().width() for b in buttons)
    margins = pane.layout().contentsMargins()
    assert pane.minimumSizeHint().width() <= widest + margins.left() + margins.right()
    assert pane.minimumSizeHint().width() <= (1 - SHARE[1]) * DEFAULT_SIZE[0]


@quiet
def test_the_minimum_size_of_the_window_is_within_its_default_size(make_window):
    """In every language the window can be made no smaller than it starts, so its
    start size and a small screen always hold it."""
    for code in i18n.ORDER:
        hint = make_window(Stepper(), language=code).minimumSizeHint()
        assert hint.width() <= DEFAULT_SIZE[0] and hint.height() <= DEFAULT_SIZE[1], (code, hint)


@quiet
def test_a_saved_file_note_does_not_widen_the_window(qtbot, make_window):
    """The summary wraps: neither a translation nor a long file name (untrusted, and
    shown in full as plain text in the tooltip) raises the window's minimum width."""
    long_name = "n" * 196 + ".tar"
    for code in i18n.ORDER:
        window = make_window(Stepper(), language=code)
        tab = window.read_tab
        before = window.minimumSizeHint().width()
        for name in ("doc.tar", long_name, "<b>x.tar"):
            tab.controller.note = text.Words(text.saved_message, f"/home/u/{name}", 250_000)
            tab.refresh()
            qtbot.wait(1)
            assert name in tab.summary.text(), (code, name)
            assert window.minimumSizeHint().width() <= before, (code, name)
            assert tab.summary.textFormat() == Qt.TextFormat.PlainText
            tooltip = tab.summary.toolTip()
            assert tooltip == _plain_tooltip(tab.summary.text()), (code, name)


@quiet
def test_the_list_has_its_share_when_the_read_tab_is_not_shown_first(qtbot, make_window):
    window = make_window(Stepper(), language="ru", tab=1)
    window.tabs.setCurrentIndex(0)
    qtbot.waitUntil(lambda: window.read_tab._shared, timeout=TIMEOUT)
    first, second = window.read_tab.splitter.sizes()
    share, ok = list_share_ok(window.read_tab)
    assert ok, share
    assert window.read_tab.page_list.viewport().width() >= 0.9 * first
    # And once the user has moved the splitter, switching tabs does not undo it.
    step = (first + second) // 10
    window.read_tab.splitter.setSizes([first + step, second - step])
    moved = window.read_tab.splitter.sizes()
    assert moved[0] > first
    window.tabs.setCurrentIndex(1)
    window.tabs.setCurrentIndex(0)
    assert window.read_tab.splitter.sizes() == moved


@quiet
def test_the_window_still_fits_a_small_screen(make_window):
    window = make_window(Stepper())
    hint = window.minimumSizeHint()
    assert hint.width() <= SMALL_SCREEN[0] and hint.height() <= SMALL_SCREEN[1]
    assert (window.width(), window.height()) == DEFAULT_SIZE


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
    # The 63-character row really is too long for the list, and elision shortens it to fit.
    row = next(r for r in tab.rows() if LONG in r)
    metrics = view.fontMetrics()
    assert metrics.horizontalAdvance(row) > view.viewport().width()
    shown = metrics.elidedText(row, view.textElideMode(), view.viewport().width() - 8)
    assert shown != row and "\u2026" in shown
    assert metrics.horizontalAdvance(shown) <= view.viewport().width()


@quiet
def test_the_name_of_a_scan_being_read_is_elided_in_the_middle_to_fit(make_window):
    stepper = Stepper()
    window = make_window(stepper)
    tab = window.read_tab
    tab.controller.add_paths([f"/scans/{LONG}"])
    view = tab.page_list
    row = tab.rows().index(f"{LONG} · Waiting")
    index = view.model().index(row)
    area = view.visualRect(index).adjusted(2, 0, -2, 0)
    metrics = view.fontMetrics()
    name_rect, bar_rect, step_rect = view.itemDelegate().layout(area, metrics, LONG, 0)
    assert name_rect.width() < metrics.horizontalAdvance(LONG)  # so it is elided, in the middle
    assert metrics.elidedText(LONG, Qt.TextElideMode.ElideMiddle, name_rect.width()) != LONG
    assert name_rect.right() < bar_rect.left() and bar_rect.right() <= area.right()
    assert step_rect.top() > name_rect.bottom() and step_rect.width() == area.width()
    stepper.advance(LONG)
    tab.controller.remove(next(s.id for s in tab.controller.document.scans()))


@quiet
def test_every_row_gets_the_full_width_of_the_viewport(make_window):
    stepper = Stepper()
    window = make_window(stepper)
    tab = window.read_tab
    tab.controller.add_paths(["/scans/page.png"])
    view = tab.page_list
    for row in range(view.model().rowCount()):
        rect = view.visualRect(view.model().index(row))
        assert rect.width() == view.viewport().width(), (row, rect)
    stepper.advance("page.png")
    tab.controller.remove(next(s.id for s in tab.controller.document.scans()))


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
    for raw in (name, "<b>x</b> & y\nsecond  line"):  # shown literally, newline and spaces kept
        document = QTextDocument()
        document.setHtml(_plain_tooltip(raw))
        assert document.toPlainText() == raw
    assert "<b>" not in tip and "&lt;b&gt;x&lt;i&gt;&amp;amp;.png" in tip
    # Plain rows are the row itself and are shown as plain text.
    heading = tooltips(tab)[tab.rows().index(text.BEING_READ_SECTION)]
    assert heading == text.BEING_READ_SECTION and not GuiQt.mightBeRichText(heading)
    stepper.advance(name)
    tab.controller.remove(next(s.id for s in tab.controller.document.scans()))


def step_room(tab, row, step):
    """The rectangle the delegate gives ``step`` in ``row``, the rectangle of the row
    in the list, and the rectangle ``step`` needs wrapped at the step's width."""
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
    _name, _bar, step_rect = view.itemDelegate().layout(area, metrics, "scan.png", 0, step)
    flags = Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft
    need = metrics.boundingRect(QRect(0, 0, step_rect.width(), 0), flags, step)
    return QRect(step_rect), QRect(opt.rect), QRect(need)


def longest_progress():
    """The progress whose step text is the longest in the current language."""
    names = ("open", "find", "identify", "read", "slow-sample", "other")
    choices = [None, Progress("slow-fit", 3, 5, 0.5), *(Progress(n, 0, 1, 0.0) for n in names)]
    return max(choices, key=lambda progress: len(text.step_text(progress)))


class ShowsOneStep:
    """A ``process`` that reports ``progress`` and then waits until ``release`` is set."""

    def __init__(self, progress):
        self.progress = progress
        self.release = threading.Event()

    def __call__(self, path, cancelled=lambda: False, on_progress=None):
        if self.progress is not None:
            on_progress(self.progress)
        while not self.release.wait(0.01):
            if cancelled():
                raise Cancelled()
        return ScanWork(None, "no page found", None, 0, None, (10, 10))


@quiet
def test_the_step_of_a_scan_being_read_is_not_elided_at_the_default_size(qtbot, make_window):
    """In every language a scan being read shows its longest step whole, measured in
    the font in use: on one line when it fits, wrapped onto more when it does not."""
    for code in i18n.ORDER:
        _check_the_longest_step(qtbot, make_window(Stepper(), language=code), code)


def _check_the_longest_step(qtbot, window, code):
    tab = window.read_tab
    progress = longest_progress()
    step = text.step_text(progress)
    assert len(step) > 20
    shows = ShowsOneStep(progress)
    tab.controller._process = shows
    tab.controller.add_paths(["/scans/page.png"])
    qtbot.waitUntil(lambda: any(r.endswith(step) for r in tab.rows()), timeout=TIMEOUT)
    qtbot.wait(10)  # the list lays the row out again for its new step
    row = next(i for i, r in enumerate(tab.rows()) if r.endswith(step))
    step_rect, row_rect, need = step_room(tab, row, step)
    assert need.width() <= step_rect.width(), (code, step, need, step_rect)
    assert need.height() <= step_rect.height(), (code, step, need, step_rect)
    assert row_rect.contains(step_rect), (code, step, row_rect, step_rect)
    shows.release.set()
    qtbot.waitUntil(lambda: not tab.controller.document.being_read(), timeout=TIMEOUT)


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


@quiet
def test_a_step_wraps_and_its_row_grows_when_the_list_is_made_narrow(qtbot, make_window):
    window = make_window(Stepper())
    tab = window.read_tab
    progress = longest_progress()
    step = text.step_text(progress)
    total = sum(tab.splitter.sizes())
    shows = ShowsOneStep(progress)
    tab.controller._process = shows
    tab.controller.add_paths(["/scans/page.png"])
    qtbot.waitUntil(lambda: any(r.endswith(step) for r in tab.rows()), timeout=TIMEOUT)
    row = next(i for i, r in enumerate(tab.rows()) if r.endswith(step))
    # The step's width in the narrowest list and in a list of 70% of the splitter, and a
    # list font in which the step is halfway between: one line wide, more narrow.
    tab.splitter.setSizes([1, total - 1])
    qtbot.wait(20)
    narrow_width = step_room(tab, row, step)[0].width()
    tab.splitter.setSizes([total * 7 // 10, total - total * 7 // 10])
    qtbot.wait(20)
    wide_width = step_room(tab, row, step)[0].width()
    assert narrow_width < wide_width
    big = QFont(tab.page_list.font())
    advance = QFontMetrics(big).horizontalAdvance(step)
    big.setPointSizeF(big.pointSizeF() * (narrow_width + wide_width) / 2 / advance)
    tab.page_list.setFont(big)
    qtbot.wait(20)
    wide = step_room(tab, row, step)
    line = QFontMetrics(big).height()
    assert wide[2].height() < 1.5 * line  # one line
    before = wide[1].height()
    tab.splitter.setSizes([1, total - 1])  # as narrow as the list may be
    qtbot.wait(20)
    step_rect, row_rect, need = step_room(tab, row, step)
    assert need.height() >= 1.5 * line  # it did wrap
    assert need.width() <= step_rect.width() and need.height() <= step_rect.height()
    assert row_rect.contains(step_rect) and row_rect.height() > before
    shows.release.set()
    qtbot.waitUntil(lambda: not tab.controller.document.being_read(), timeout=TIMEOUT)
