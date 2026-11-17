# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Scans being read: their rows, their progress bars and the bottom bar, off-screen."""

import os
import threading
import time

import numpy as np
import pytest
from PySide6.QtCore import QRect, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPalette
from PySide6.QtWidgets import QStyle, QStyleOptionViewItem

import optar.errors
import optar_gui.work as work
from optar_gui import text
from optar_gui.document import Row, ScanState
from optar_gui.read_tab import FRACTION_ROLE, ReadController, ReadTab
from optar_gui.work import (
    STEP_FIND,
    STEP_IDENTIFY,
    STEP_OPEN,
    STEP_READ,
    Cancelled,
    Progress,
    ScanWork,
    process_scan,
)
from tests.helpers import save_scan

TIMEOUT = 60_000  # ms


@pytest.fixture
def make_tab(qtbot):
    controllers = []

    def make(process, **kw):
        controller = ReadController(process=process, **kw)
        controllers.append(controller)
        tab = ReadTab(controller)
        qtbot.addWidget(tab)
        return tab

    yield make
    for controller in controllers:
        controller.shutdown(TIMEOUT)


STEPS = [
    Progress(STEP_OPEN, 0, 1, 0.0),
    Progress(STEP_FIND, 0, 1, 0.05),
    Progress(STEP_IDENTIFY, 1, 4, 0.275),
    Progress(STEP_READ, 0, 1, 0.5),
]
WORDS = ["Opening the file", "Finding the page", "Identifying the page", "Reading the data"]


class Stepper:
    """A ``process`` that reports STEPS one at a time, each when ``advance(name)``
    lets it, then (one more ``advance``) finds no page."""

    def __init__(self):
        self.lock = threading.Lock()
        self.gates = {}
        self.started = []
        self.cancelled = []

    def gate(self, name):
        with self.lock:
            return self.gates.setdefault(name, threading.Semaphore(0))

    def advance(self, name):
        self.gate(name).release()

    def __call__(self, path, cancelled=lambda: False, on_progress=None):
        name = os.path.basename(path)
        with self.lock:
            self.started.append(name)
        for progress in [*STEPS, None]:
            while not self.gate(name).acquire(timeout=0.01):
                if cancelled():
                    with self.lock:
                        self.cancelled.append(name)
                    raise Cancelled()
            if progress is None:
                break
            on_progress(progress)
        return ScanWork(None, "no page found", None, 0, None, (10, 10))


def fraction_of(tab, scan_id):
    model = tab.page_list.model()
    row = model.row_of((Row.BEING_READ, scan_id))
    return None if row is None else model.index(row).data(FRACTION_ROLE)


def scan_id(tab, name):
    return next(s.id for s in tab.controller.document.scans() if s.path.endswith(name))


def test_each_scan_is_listed_with_its_step_until_it_is_read(qtbot, make_tab):
    stepper = Stepper()
    tab = make_tab(stepper, max_workers=1)
    tab.controller.add_paths(["/scans/a.png", "/scans/b.png"])
    rows = tab.rows()
    assert rows[rows.index(text.BEING_READ_SECTION) + 1:] == ["a.png · Waiting", "b.png · Waiting"]
    assert tab.summary.text() == "Working… 0 of 2 scans read"
    a, b = scan_id(tab, "a.png"), scan_id(tab, "b.png")
    assert fraction_of(tab, a) == fraction_of(tab, b) == 0.0
    qtbot.waitUntil(lambda: stepper.started == ["a.png"], timeout=TIMEOUT)

    for progress, words in zip(STEPS, WORDS, strict=True):
        stepper.advance("a.png")
        qtbot.waitUntil(lambda w=words: f"a.png · {w}" in tab.rows(), timeout=TIMEOUT)
        assert fraction_of(tab, a) == progress.fraction
        assert "b.png · Waiting" in tab.rows()

    # The selected row's detail follows its step.
    tab.select_row(tab.rows().index("a.png · Reading the data"))
    assert tab.detail.text().splitlines() == ["a.png", "Reading the data."]
    assert tab.remove_button.isEnabled()

    # Removing a scan that waits: its row goes and it is never read.
    tab.select_row(tab.rows().index("b.png · Waiting"))
    assert tab.remove_button.isEnabled()
    tab.remove_button.click()
    assert not any(r.startswith("b.png") for r in tab.rows())
    assert tab.summary.text() == "Working… 0 of 1 scan read"

    tab.controller.add_paths(["/scans/c.png"])
    assert tab.summary.text() == "Working… 0 of 2 scans read"
    stepper.advance("a.png")  # a finds no page
    qtbot.waitUntil(lambda: stepper.started == ["a.png", "c.png"], timeout=TIMEOUT)
    qtbot.waitUntil(
        lambda: tab.summary.text() == "Working… 1 of 2 scans read", timeout=TIMEOUT
    )
    assert f"a.png · {text.unreadable_reason('no page found')}" in tab.rows()
    assert fraction_of(tab, a) is None

    # Removing a scan being read cancels its reading.
    stepper.advance("c.png")
    qtbot.waitUntil(lambda: "c.png · Opening the file" in tab.rows(), timeout=TIMEOUT)
    tab.select_row(tab.rows().index("c.png · Opening the file"))
    tab.remove_button.click()
    assert text.BEING_READ_SECTION not in tab.rows()
    qtbot.waitUntil(lambda: stepper.cancelled == ["c.png"], timeout=TIMEOUT)
    qtbot.waitUntil(lambda: tab.controller.runner.active == 0, timeout=TIMEOUT)
    assert stepper.started == ["a.png", "c.png"]
    assert not tab.summary.text().startswith("Working")


def test_a_file_name_with_markup_is_shown_as_plain_text(qtbot, make_tab):
    stepper = Stepper()
    tab = make_tab(stepper, max_workers=1)
    tab.controller.add_paths(["/scans/<b>bold&amp;<i>.png"])
    row = "<b>bold&amp;<i>.png · Waiting"
    assert row in tab.rows()
    tab.select_row(tab.rows().index(row))
    assert tab.detail.text().splitlines() == ["<b>bold&amp;<i>.png", "Waiting."]
    stepper.advance("<b>bold&amp;<i>.png")
    qtbot.waitUntil(lambda: "<b>bold&amp;<i>.png · Opening the file" in tab.rows(), timeout=TIMEOUT)
    tab.controller.remove(scan_id(tab, "<b>bold&amp;<i>.png"))


def test_a_file_that_is_not_an_image_ends_as_not_readable(qtbot, make_tab, tmp_path):
    path = tmp_path / "notes.png"
    path.write_bytes(b"not an image")
    reason = process_scan(str(path)).reason
    tab = make_tab(process_scan)
    tab.controller.add_paths([str(path)])
    qtbot.waitUntil(lambda: tab.controller.runner.active == 0, timeout=TIMEOUT)
    tab.controller.refresh()
    rows = tab.rows()
    assert text.BEING_READ_SECTION not in rows
    shown = f"notes.png · {text.unreadable_reason(reason)}"
    assert rows[rows.index(text.NOT_READABLE) + 1] == shown


def render(tab, row, *, selected=False, width=480):
    """The list's delegate painting a row into an image of its own."""
    view = tab.page_list
    index = view.model().index(row)
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, width, 24)
    option.widget = view
    option.palette = view.palette()
    option.font = view.font()
    option.fontMetrics = view.fontMetrics()
    option.state = QStyle.StateFlag.State_Enabled
    if selected:
        option.state |= QStyle.StateFlag.State_Selected
    image = QImage(width, 24, QImage.Format.Format_ARGB32)
    image.fill(view.palette().color(QPalette.ColorRole.Base))
    painter = QPainter(image)
    try:
        view.itemDelegate().paint(painter, option, index)
    finally:
        painter.end()
    return image


def pixels(image):
    ptr = image.constBits()
    return np.frombuffer(ptr, np.uint8).reshape(image.height(), image.bytesPerLine()).copy()


def dark_palette():
    palette = QPalette()
    for role, colour in [
        (QPalette.ColorRole.Window, "#202124"), (QPalette.ColorRole.Base, "#181818"),
        (QPalette.ColorRole.Text, "#e8eaed"), (QPalette.ColorRole.WindowText, "#e8eaed"),
        (QPalette.ColorRole.Button, "#303134"), (QPalette.ColorRole.ButtonText, "#e8eaed"),
        (QPalette.ColorRole.Highlight, "#8ab4f8"), (QPalette.ColorRole.HighlightedText, "#202124"),
    ]:  # fmt: skip
        palette.setColor(role, QColor(colour))
    return palette


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_bar_is_drawn_fuller_for_a_larger_fraction(qtbot, make_tab, theme):
    stepper = Stepper()
    tab = make_tab(stepper, max_workers=1)
    if theme == "dark":
        tab.page_list.setPalette(dark_palette())
    tab.controller.add_paths(["/scans/a.png"])
    doc = tab.controller.document
    a = scan_id(tab, "a.png")
    row = tab.rows().index("a.png · Waiting")

    def drawn(fraction, **kw):
        doc.set_progress(a, Progress(STEP_READ, 0, 1, fraction))
        tab.refresh()
        assert fraction_of(tab, a) == fraction
        return pixels(render(tab, row, **kw))

    empty = drawn(0.0)
    filled = [int(np.count_nonzero(drawn(f) != empty)) for f in (0.2, 0.5, 0.9)]
    assert 0 < filled[0] < filled[1] < filled[2], filled
    # Selected, the row is still drawn, with its bar, and highlighted: it differs
    # from the same row unselected.
    selected_empty = drawn(0.0, selected=True)
    assert np.count_nonzero(drawn(0.9, selected=True) != selected_empty) > 0
    assert np.count_nonzero(selected_empty != empty) > 0
    assert np.count_nonzero(drawn(0.5, selected=True) != drawn(0.5)) > 0
    # Another row is drawn as the list always draws it.
    assert render(tab, tab.rows().index(text.BEING_READ_SECTION)) is not None
    tab.controller.remove(a)


def test_many_scans_at_once_stay_responsive(qtbot, make_tab, tmp_path, monkeypatch):
    """30 scans whose reader reports as often as it can: each scan's reports are
    limited, every scan ends as its row, and the window keeps up."""

    def chatty(image, *, cancelled, on_slow, on_progress):
        # Thousands of reports a second. Between them the reader lets go of the
        # interpreter, as the real one does in its numpy work: a loop of pure
        # Python in three threads holds up any interface thread for 0.15 to 0.3 s
        # at a time (measured), whatever the window does.
        start = time.monotonic()
        while time.monotonic() - start < 0.3:
            on_progress(work.STEP_IDENTIFY, 0, 2)
            on_progress(work.STEP_IDENTIFY, 1, 2)
            time.sleep(0.0002)
        raise optar.errors.IdentifyError("no page found")

    monkeypatch.setattr(work, "identify_any", chatty)
    paths = []
    for n in range(30):
        path = tmp_path / f"scan-{n:02}.png"
        save_scan(path, np.full((40, 30), 255, np.uint8))
        paths.append(str(path))
    tab = make_tab(process_scan, max_workers=3)
    reports = []
    tab.controller.runner.progress.connect(lambda scan, p: reports.append((scan, p)))
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(time.monotonic()))
    timer.start(20)
    start = time.monotonic()
    tab.controller.add_paths(paths)
    assert len([r for r in tab.rows() if r.endswith(" · Waiting")]) == 30
    qtbot.waitUntil(lambda: tab.controller.runner.active == 0, timeout=TIMEOUT)
    elapsed = time.monotonic() - start
    timer.stop()
    tab.controller.refresh()
    assert text.BEING_READ_SECTION not in tab.rows()
    assert len([r for r in tab.rows() if r.startswith("scan-")]) == 30
    assert all(s.state == ScanState.UNREADABLE for s in tab.controller.document.scans())
    # Per scan: opening, finding nothing more, and about ten a second of identifying.
    per_scan = {}
    for scan, _ in reports:
        per_scan[scan] = per_scan.get(scan, 0) + 1
    assert len(per_scan) == 30
    assert max(per_scan.values()) <= 2 + 0.3 / work.PROGRESS_INTERVAL_S + 2
    # Redraws are gathered, not one per report.
    assert tab.controller.refreshes <= 5 + elapsed * 1000 / 100 * 1.5
    # The event loop keeps turning: a 20 ms timer is never held up long. Measured
    # on the development machine: the longest gap about 0.02 s.
    gaps = np.diff(ticks)
    assert len(gaps) and gaps.max() < 0.3, gaps.max()


def test_a_label_read_again_slowly_ends_as_its_page_without_going_back(
    qtbot, make_tab, scan_files, monkeypatch
):
    """identify_any's label-only path: the label is read, the slower reader reads
    the page again and finds nothing, and the label's page is decoded."""
    real = work.identify_any

    def label_then_slow(image, **kw):
        ident = real(image, **kw)
        report = kw["on_progress"]
        report(work.STEP_SLOW_SAMPLE, 0, 1)
        for done in range(3):
            report(work.STEP_SLOW_FIT, done, 5)
        return ident  # the slower reader found nothing: the label stands

    monkeypatch.setattr(work, "identify_any", label_then_slow)
    _, paths = scan_files(nbytes=1000)
    tab = make_tab(process_scan)
    reports = []
    tab.controller.runner.progress.connect(lambda scan, p: reports.append(p))
    tab.controller.add_paths(paths[:1])
    qtbot.waitUntil(lambda: tab.controller.runner.active == 0, timeout=TIMEOUT)
    tab.controller.refresh()
    fractions = [p.fraction for p in reports]
    assert fractions == sorted(fractions) and fractions[-1] == 1.0
    steps = [p.step for p in reports]
    assert work.STEP_SLOW_FIT in steps and steps[-1] == STEP_READ
    assert text.BEING_READ_SECTION not in tab.rows()
    assert tab.rows()[1] == "Page 1 · Good"


def test_the_bottom_bar_keeps_the_documents_state_while_more_scans_are_read(
    qtbot, make_tab, scan_files
):
    _, paths = scan_files(nbytes=1000)
    stepper = Stepper()

    def process(path, cancelled=lambda: False, on_progress=None):
        if os.path.basename(path).startswith("held"):
            return stepper(path, cancelled, on_progress)
        return process_scan(path, cancelled, on_progress=on_progress)

    tab = make_tab(process, max_workers=2)
    tab.controller.add_paths(paths)
    qtbot.waitUntil(lambda: tab.controller.runner.active == 0, timeout=TIMEOUT)
    tab.controller.refresh()
    qtbot.waitUntil(lambda: not tab.controller.checking, timeout=TIMEOUT)
    tab.controller.refresh()
    verdict = tab.summary.text()
    assert verdict.startswith(text.VERIFIED)

    tab.controller.add_paths(["/scans/held-1.png", "/scans/held-2.png"])
    assert tab.summary.text() == f"{verdict} · 0 of 2 scans read"
    for _ in range(len(STEPS) + 1):  # held-1 goes through its steps, finds no page
        stepper.advance("held-1.png")
    qtbot.waitUntil(lambda: tab.summary.text() == f"{verdict} · 1 of 2 scans read",
                    timeout=TIMEOUT)  # fmt: skip
    tab.controller.remove(scan_id(tab, "held-2.png"))
    qtbot.waitUntil(lambda: tab.controller.runner.active == 0, timeout=TIMEOUT)
    tab.controller.refresh()
    assert tab.summary.text() == verdict


def test_the_names_get_the_room_they_need_before_they_are_elided(qtbot, make_tab):
    from PySide6.QtGui import QFontMetrics

    stepper = Stepper()
    tab = make_tab(stepper, max_workers=1)
    long_name, short_name = "scan 2026-11-17 page 3.png", "a.png"
    tab.controller.add_paths([f"/scans/{long_name}", f"/scans/{short_name}"])
    doc = tab.controller.document
    rows = {name: tab.rows().index(f"{name} · Waiting") for name in (long_name, short_name)}
    needed = QFontMetrics(tab.page_list.font()).horizontalAdvance(long_name)

    def bar_left(name, width):
        """The first column the bar's filling changes, from empty to full."""
        sid = scan_id(tab, name)
        images = []
        for fraction in (0.0, 1.0):
            doc.set_progress(sid, Progress(STEP_READ, 0, 1, fraction))
            tab.refresh()
            images.append(pixels(render(tab, rows[name], width=width)))
        cols = np.flatnonzero((images[0] != images[1]).any(axis=0)) // 4
        assert len(cols)
        return int(cols.min())

    # A wide list: the whole long name, and the bars of both rows in one column.
    wide = [bar_left(n, 900) for n in (long_name, short_name)]
    assert wide[0] == wide[1]
    assert needed < wide[0] < needed + 40
    # A narrow list: the name column stops at 45% of the row, and the name is cut.
    narrow = [bar_left(n, 300) for n in (long_name, short_name)]
    assert narrow[0] == narrow[1] < needed
    assert 0.4 * 300 < narrow[0] <= 0.45 * 300 + 20
    for name in (long_name, short_name):
        tab.controller.remove(scan_id(tab, name))
