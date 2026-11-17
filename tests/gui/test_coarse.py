# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The reading tab and the slower reader for coarse scans, off-screen."""

import threading
import time

import pytest

import optar.identify
from optar import PAPERS
from optar_gui import text
from optar_gui.document import DocState, Row, ScanState
from optar_gui.read_tab import ReadController, ReadTab
from optar_gui.work import Cancelled, ScanWork, process_scan
from tests.helpers import save_linear_scan

TIMEOUT = 120_000  # ms


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


def wait_settled(qtbot, tab):
    controller = tab.controller

    def done():
        busy = any(s.state in (ScanState.WAITING, ScanState.WORKING)
                   for s in controller.document.scans())  # fmt: skip
        return not busy and controller.runner.active == 0

    qtbot.waitUntil(done, timeout=TIMEOUT)
    controller.refresh()
    qtbot.waitUntil(lambda: not controller.checking, timeout=TIMEOUT)
    controller.refresh()


class SlowFake:
    """A ``process`` that starts the slower reader and holds there until released
    (or cancelled), then finds nothing."""

    def __init__(self):
        self.gate = threading.Event()
        self.cancelled = []

    def __call__(self, path, cancelled=lambda: False, on_slow=None):
        on_slow()
        while not self.gate.wait(0.01):
            if cancelled():
                self.cancelled.append(path)
                raise Cancelled()
        reason = text.coarse_scan(290.0, None, slow_tried=True)
        return ScanWork(None, reason, None, 0, None, (100, 140), scan_dpi=290.0)


def test_a_coarse_scan_is_listed_while_the_slower_reader_reads_it(qtbot, make_tab):
    fake = SlowFake()
    tab = make_tab(fake, max_workers=2)
    tab.controller.add_paths(["/scans/coarse.png", "/scans/other.png"])
    row = f"coarse.png · {text.READING_COARSE}"
    qtbot.waitUntil(lambda: row in tab.rows(), timeout=TIMEOUT)
    qtbot.waitUntil(lambda: f"other.png · {text.READING_COARSE}" in tab.rows(), timeout=TIMEOUT)
    assert text.READING_COARSE_SECTION in tab.rows()
    assert "about a minute" in row
    tab.select_row(tab.rows().index(row))
    assert tab.detail.text().splitlines() == ["coarse.png", f"{text.READING_COARSE}."]
    assert tab.remove_button.isEnabled()

    # Removing the other scan cancels its reading.
    tab.select_row(tab.rows().index(f"other.png · {text.READING_COARSE}"))
    tab.remove_button.click()
    qtbot.waitUntil(lambda: fake.cancelled == ["/scans/other.png"], timeout=TIMEOUT)
    assert not any(r.startswith("other.png") for r in tab.rows())

    # The reader fails: the scan is unreadable, saying the slower reader was tried.
    fake.gate.set()
    wait_settled(qtbot, tab)
    assert text.READING_COARSE_SECTION not in tab.rows()
    unreadable = [r for r in tab.rows() if r.startswith("coarse.png")]
    assert len(unreadable) == 1 and unreadable[0].endswith(text.SLOW_TRIED)
    assert "too coarse to read" in unreadable[0]


def test_removing_a_scan_stops_the_slower_reader(qtbot, make_tab, coarse_scans):
    _, paths = coarse_scans
    tab = make_tab(process_scan, max_workers=1)
    tab.controller.add_paths(paths[1:])
    row = f"{paths[1].rsplit('/', 1)[-1]} · {text.READING_COARSE}"
    qtbot.waitUntil(lambda: row in tab.rows(), timeout=TIMEOUT)
    scan_id = tab.controller.document.reading_coarse()[0].id
    start = time.monotonic()
    tab.controller.remove(scan_id)
    qtbot.waitUntil(lambda: tab.controller.runner.active == 0, timeout=TIMEOUT)
    assert time.monotonic() - start < 10
    assert tab.rows() == []


@pytest.fixture
def coarse_scans(tmp_path, monkeypatch):
    """test_soft's two-page version-1 document, scanned too coarsely for the
    ordinary reader, as PNG files; identification tries its layout only."""
    from tests.unit import test_soft as case

    monkeypatch.setattr(optar.identify, "_papers_by_shape", lambda c: [PAPERS["a4"]])
    monkeypatch.setattr(optar.identify, "_layouts_by_shape", lambda c, p: [case.LAYOUT])
    paths = []
    for page in (1, 2):
        path = tmp_path / f"coarse-{page}.png"
        save_linear_scan(path, case.scan(**case.COARSER, page=page))
        paths.append(str(path))
    return case, paths


def test_a_document_read_by_the_slower_reader_says_so_and_verifies(qtbot, make_tab,
                                                                   coarse_scans):  # fmt: skip
    case, paths = coarse_scans
    tab = make_tab(process_scan, max_workers=2)
    tab.controller.add_paths(paths)
    wait_settled(qtbot, tab)
    assert tab.controller.summary.state == DocState.VERIFIED
    assert tab.summary.text().startswith(text.VERIFIED)
    for number in (1, 2):
        row = f"Page {number} · {text.READ_SLOWLY}"
        assert row in tab.rows()
        tab.select_row(tab.rows().index(row))
        lines = tab.detail.text().splitlines()
        assert lines[1] == text.read_by_slow_reader()
        assert not any("Repairs:" in line for line in lines)
        assert tab.preview.mark_count == 0
    assert tab.controller.document.actions(Row.PAGE, 1).remove is not None
    assert tab.controller.document.save_bytes() == case.document()[0]
