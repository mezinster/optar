# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The reading tab and the slower reader for coarse scans, off-screen."""

import os
import threading
import time

import pytest

import optar.identify
from optar import PAPERS
from optar_gui import text
from optar_gui.document import DocState, Row, ScanState
from optar_gui.read_tab import ReadController, ReadTab
from optar_gui.work import (
    STEP_SLOW_FIT,
    STEP_SLOW_SAMPLE,
    Cancelled,
    Progress,
    ScanWork,
    process_scan,
)
from tests.helpers import save_linear_scan, simulate_scan

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

    def __call__(self, path, cancelled=lambda: False, on_progress=None):
        on_progress(Progress(STEP_SLOW_FIT, 3, 5, 0.7))
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
    row = "coarse.png · Slower reader: pass 4 of 5"
    qtbot.waitUntil(lambda: row in tab.rows(), timeout=TIMEOUT)
    qtbot.waitUntil(lambda: "other.png · Slower reader: pass 4 of 5" in tab.rows(),
                    timeout=TIMEOUT)  # fmt: skip
    assert text.BEING_READ_SECTION in tab.rows()
    tab.select_row(tab.rows().index(row))
    assert tab.detail.text().splitlines() == [
        "coarse.png", "Slower reader: pass 4 of 5.", f"{text.READING_COARSE}."
    ]
    assert "about a minute" in tab.detail.text()
    assert tab.remove_button.isEnabled()

    # Removing the other scan cancels its reading.
    tab.select_row(tab.rows().index("other.png · Slower reader: pass 4 of 5"))
    tab.remove_button.click()
    qtbot.waitUntil(lambda: fake.cancelled == ["/scans/other.png"], timeout=TIMEOUT)
    assert not any(r.startswith("other.png") for r in tab.rows())

    # The reader fails: the scan is unreadable, saying the slower reader was tried.
    fake.gate.set()
    wait_settled(qtbot, tab)
    assert text.BEING_READ_SECTION not in tab.rows()
    unreadable = [r for r in tab.rows() if r.startswith("coarse.png")]
    assert len(unreadable) == 1 and unreadable[0].endswith(text.SLOW_TRIED)
    assert "too coarse to read" in unreadable[0]


def test_removing_a_scan_stops_the_slower_reader(qtbot, make_tab, coarse_scans):
    _, paths = coarse_scans
    tab = make_tab(process_scan, max_workers=1)
    tab.controller.add_paths(paths[1:])
    doc = tab.controller.document

    def reading_slowly():
        listed = doc.being_read()
        slow = (STEP_SLOW_SAMPLE, STEP_SLOW_FIT)
        return listed and listed[0][1] is not None and listed[0][1].step in slow

    qtbot.waitUntil(reading_slowly, timeout=TIMEOUT)
    name = os.path.basename(paths[1])
    qtbot.waitUntil(lambda: any(r.startswith(f"{name} · Slower reader: ") for r in tab.rows()),
                    timeout=TIMEOUT)  # fmt: skip
    scan_id = doc.being_read()[0][0].id
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
    # Page 2 scanned coarser still (measured: about 5% of its dots corrected and
    # some 50 bytes wrong), so that the document's protection has bytes to repair.
    save_linear_scan(paths[1], simulate_scan(case.document()[2][1], case.LAYOUT, 240,
                                             blur=2.0, seed=2))  # fmt: skip
    tab = make_tab(process_scan, max_workers=2)
    tab.controller.add_paths(paths)
    wait_settled(qtbot, tab)
    assert tab.controller.summary.state == DocState.VERIFIED
    assert tab.summary.text().startswith(text.VERIFIED)
    summary = tab.controller.summary
    damage = summary.repair.page_damage
    assert damage.get(2, 0) > 0  # the protection repaired bytes of page 2
    doc = tab.controller.document
    for number in (1, 2):
        page = doc.pages()[number - 1]
        work = tab.controller.work_for(page.scan_id, doc.current.format)
        repaired = damage.get(number, 0)
        assert summary.repaired_bytes(number) == repaired
        row = f"Page {number} · Read by the slower reader · {page.corrected_dots:,} dots corrected"
        if repaired:
            row += f" · {repaired:,} bytes repaired by the document's protection"
        assert row in tab.rows()
        tab.select_row(tab.rows().index(row))
        lines = tab.detail.text().splitlines()
        assert lines[1] == "Read by the slower reader for coarse scans."
        share = f"{100 * page.corrected_dots / page.dots:.1f}%"
        assert lines[2] == (
            f"Dots corrected within the page: {page.corrected_dots:,} of {page.dots:,} ({share})."
        )
        if repaired:
            assert lines[3] == (
                f"After verification: {repaired:,} of this page's bytes were wrong and were "
                "repaired by the document's protection."
            )
        else:
            assert lines[3] == "After verification: none of this page's bytes were wrong."
        assert not any("Repairs:" in line for line in lines)
        # The dots that reader corrected are marked on the scan.
        assert 0 < page.corrected_dots == len(work.marks)
        qtbot.waitUntil(lambda: not tab.preview.loading, timeout=TIMEOUT)
        assert tab.preview.mark_count == len(work.marks)
        assert work.dot > 1 and tab.preview._dot == work.dot  # drawn one dot wide
    assert tab.controller.document.actions(Row.PAGE, 1).remove is not None
    assert tab.controller.document.save_bytes() == case.document()[0]
