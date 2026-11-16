# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The window and its "Read from paper" tab, off-screen.

Decoding a scan takes seconds, so the printouts are written once per module and
most tests run them through ``cached_process``: the real ``process_scan``, with
each file's result remembered by path. The tests about responsiveness, closing
and removing while working use ``process_scan`` itself.
"""

import os
import shutil
import threading
import time

import pytest
from PySide6.QtCore import QMimeData, QPointF, Qt, QTimer, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication, QMessageBox

import optar_gui.document as document_module
from optar import PAPERS, PageFormat, encode
from optar.tag import make_tag, tagged_label
from optar_gui import text
from optar_gui.document import DocState, Document, PageOutcome, ScanInfo, ScanState
from optar_gui.main_window import MainWindow
from optar_gui.read_tab import ReadController, ReadTab
from optar_gui.work import process_scan
from tests.helpers import fake_scan, save_scan, seeded_bytes

TIMEOUT = 120_000  # ms: decoding is slow on a loaded machine
DECODE_TIMEOUT = 600_000  # ms: four real decodes, two rounds on three workers
A4 = PageFormat.for_paper(PAPERS["a4"])

_RESULTS = {}
_RESULTS_LOCK = threading.Lock()


def cached_process(path, cancelled=lambda: False):
    """``process_scan``, remembering each file's result by its path."""
    key = os.path.realpath(path)
    with _RESULTS_LOCK:
        if key in _RESULTS:
            return _RESULTS[key]
    work = process_scan(path, cancelled)
    with _RESULTS_LOCK:
        _RESULTS[key] = work
    return work


def _printout(folder, nbytes, name, seed, untagged=False):
    data = seeded_bytes(seed, nbytes)
    if untagged:
        label = name
    else:
        tag = make_tag(data)

        def label(page, total):
            return tagged_label(tag, name, page, total)

    folder.mkdir()
    paths = []
    for page in encode(data, A4, label):
        path = folder / f"page-{page.number}.png"
        save_scan(path, fake_scan(page.pixels))
        paths.append(str(path))
    return data, paths


@pytest.fixture(scope="module")
def printouts(tmp_path_factory):
    """Printouts as PNG scans: name -> (data, [page 1, page 2, ...])."""
    root = tmp_path_factory.mktemp("printouts")
    return {
        "two": _printout(root / "two", 250_000, "doc.tar", 1),  # 2 pages
        "three": _printout(root / "three", 450_000, "big.tar", 2),  # 3 pages
        "untagged": _printout(root / "untagged", 250_000, "old.tar", 3, untagged=True),
        "foreign": _printout(root / "foreign", 1000, "other.tar", 4),  # 1 page
    }


@pytest.fixture
def make_tab(qtbot):
    """make_tab(process=cached_process) -> ReadTab with its own controller."""
    controllers = []

    def make(process=cached_process, **kw):
        controller = ReadController(process=process, **kw)
        controllers.append(controller)
        tab = ReadTab(controller)
        qtbot.addWidget(tab)
        return tab

    yield make
    for controller in controllers:
        controller.shutdown(TIMEOUT)


def settled(tab):
    """Waits until no scan is waiting or being read and the view is up to date."""
    controller = tab.controller

    def done():
        busy = any(s.state in (ScanState.WAITING, ScanState.WORKING)
                   for s in controller.document.scans())
        return not busy and controller.runner.active == 0

    return done


def wait_settled(qtbot, tab, timeout=TIMEOUT):
    qtbot.waitUntil(settled(tab), timeout=timeout)
    tab.controller.refresh()


def find_row(tab, label):
    return tab.rows().index(label)


def blank_png(path):
    from PIL import Image

    Image.new("L", (800, 1100), 255).save(path)
    return str(path)


# --- Adding scans and the page list ---------------------------------------------------


def test_adding_scans_fills_the_page_list(qtbot, make_tab, printouts):
    data, (p1, p2) = printouts["two"]
    tab = make_tab()
    tab.controller.add_paths([p2, p1])
    wait_settled(qtbot, tab)
    assert tab.rows() == ["doc.tar · A4 · 2 pages", "Page 1 · Good", "Page 2 · Good"]
    assert tab.controller.summary.state == DocState.VERIFIED
    summary = tab.findChild(type(tab.summary), "summaryLabel")
    assert summary.text() == f"Verified · {len(data):,} bytes"
    assert tab.findChild(type(tab.save_button), "saveButton").isEnabled()
    # Selecting a page shows its details.
    tab.select_row(find_row(tab, "Page 2 · Good"))
    detail = tab.findChild(type(tab.detail), "detailLabel").text().splitlines()
    assert detail[0] == "Page 2 of 2 · page-2.png"
    assert detail[1].endswith("· 0 repaired · 0 lost")
    assert tab.remove_button.isEnabled()
    work = tab.controller.work_for(tab.controller.document.pages()[1].scan_id)
    assert work.rotation == 0 and work.size[0] > 0 and work.marks is not None


def test_missing_page_is_listed(qtbot, make_tab, printouts):
    _, (p1, p2, p3) = printouts["three"]
    tab = make_tab()
    tab.controller.add_paths([p2])
    wait_settled(qtbot, tab)
    assert tab.rows() == [
        "big.tar · A4 · 3 pages", "Page 1 · Missing", "Page 2 · Good", "Page 3 · Missing"
    ]
    assert tab.save_button.isEnabled()
    assert tab.summary.text() == "1 of 3 pages good · 2 missing"
    tab.select_row(1)
    assert tab.detail.text() == "Page 1 of 3\nNo scan of this page has been added"
    assert not tab.remove_button.isEnabled()


def test_non_page_and_non_image_files_are_not_readable(qtbot, make_tab, printouts, tmp_path):
    _, (p1, _) = printouts["two"]
    blank = blank_png(tmp_path / "blank.png")
    notes = tmp_path / "notes.txt"
    notes.write_text("not a scan")
    gif = tmp_path / "picture.gif"
    from PIL import Image

    Image.new("L", (100, 100), 255).save(gif)
    tab = make_tab()
    tab.controller.add_paths([p1, blank, str(notes), str(gif)])
    wait_settled(qtbot, tab)
    rows = tab.rows()
    assert rows[:3] == ["doc.tar · A4 · 2 pages", "Page 1 · Good", "Page 2 · Missing"]
    assert rows[3] == text.NOT_READABLE
    assert rows[4] == "blank.png · No optar page found in this image"
    assert rows[5] == (
        f"notes.txt · cannot read image {notes}: not a PNG, TIFF, BMP, PGM/PPM or JPEG image"
    )
    assert rows[6] == (
        f"picture.gif · cannot read image {gif}: not a PNG, TIFF, BMP, PGM/PPM or JPEG image"
    )
    assert len(rows) == 7
    tab.select_row(4)
    assert tab.detail.text() == "blank.png\nNo optar page found in this image"
    assert tab.remove_button.isEnabled()
    tab.remove_button.click()
    assert "blank.png · No optar page found in this image" not in tab.rows()
    assert len(tab.controller.document.scans()) == 3


def test_same_file_added_twice_is_listed_once(qtbot, make_tab, printouts):
    _, (p1, _) = printouts["two"]
    tab = make_tab()
    tab.controller.add_paths([p1, p1])
    tab.controller.add_paths([os.path.join(os.path.dirname(p1), ".", "page-1.png")])
    assert len(tab.controller.document.scans()) == 1
    wait_settled(qtbot, tab)
    assert tab.rows() == ["doc.tar · A4 · 2 pages", "Page 1 · Good", "Page 2 · Missing"]


def test_foreign_scan_is_listed_but_not_used(qtbot, make_tab, printouts):
    data, (p1, p2) = printouts["two"]
    _, (other,) = printouts["foreign"]
    tab = make_tab()
    tab.controller.add_paths([p1, other, p2])
    wait_settled(qtbot, tab)
    assert tab.rows() == [
        "doc.tar · A4 · 2 pages",
        "Page 1 · Good",
        "Page 2 · Good",
        text.NOT_PART_OF_THIS_FILE,
        "other.tar · A4 · 1 page · 1 scan",
    ]
    assert tab.controller.summary.state == DocState.VERIFIED
    assert tab.controller.summary.size == len(data)
    tab.select_row(4)
    assert tab.detail.text() == (
        "other.tar · A4 · 1 page\n1 scan of another printout, not part of this file"
    )
    assert not tab.remove_button.isEnabled()


def test_untagged_document_shows_caution(qtbot, make_tab, printouts):
    untagged = make_tab()
    untagged.controller.add_paths(printouts["untagged"][1])
    tagged = make_tab()
    tagged.controller.add_paths(printouts["two"][1])
    for tab in (untagged, tagged):
        assert tab.caution.isHidden()  # nothing identified yet
        wait_settled(qtbot, tab)
    caution = untagged.findChild(type(untagged.caution), "cautionLabel")
    assert not caution.isHidden()
    assert caution.text() == text.untagged_caution()
    assert untagged.rows()[:3] == ["old.tar · A4 · 2 pages", "Page 1 · Good", "Page 2 · Good"]
    assert untagged.controller.summary.state == DocState.UNVERIFIABLE
    assert tagged.caution.isHidden()


def test_selection_survives_a_refresh(qtbot, make_tab, printouts):
    _, (p1, p2) = printouts["two"]
    _, (other,) = printouts["foreign"]
    tab = make_tab()
    tab.controller.add_paths([p1])
    wait_settled(qtbot, tab)
    tab.select_row(find_row(tab, "Page 2 · Missing"))
    assert tab.detail.text().startswith("Page 2 of 2\n")
    tab.controller.add_paths([p2, other])  # the rows change: a section is added
    wait_settled(qtbot, tab)
    assert len(tab.rows()) == 5
    selected = tab.page_list.selectionModel().selectedIndexes()
    assert [i.row() for i in selected] == [find_row(tab, "Page 2 · Good")]
    assert tab.detail.text().startswith("Page 2 of 2 · page-2.png\n")
    assert tab.remove_button.isEnabled()


def test_remove_scan_updates_list(qtbot, make_tab, printouts):
    _, (p1, p2) = printouts["two"]
    tab = make_tab()
    tab.controller.add_paths([p1, p2])
    wait_settled(qtbot, tab)
    doc = tab.controller.document
    removed = doc.pages()[1].scan_id
    assert tab.controller.work_for(removed) is not None
    tab.select_row(find_row(tab, "Page 2 · Good"))
    tab.findChild(type(tab.remove_button), "removeButton").click()
    assert tab.rows() == ["doc.tar · A4 · 2 pages", "Page 1 · Good", "Page 2 · Missing"]
    assert [s.path for s in doc.scans()] == [p1]
    assert tab.controller.work_for(removed) is None
    assert tab.detail.text().startswith("Page 2 of 2\nNo scan")  # still selected
    assert not tab.remove_button.isEnabled()
    assert tab.summary.text() == "1 of 2 pages good · 1 missing"


# --- Adding through the dialog and by dropping ------------------------------------------


def test_add_button_asks_for_files(qtbot, make_tab, printouts):
    _, (p1, p2) = printouts["two"]
    tab = make_tab()
    tab.ask_open_paths = lambda: [p2]
    tab.findChild(type(tab.add_button), "addButton").click()
    assert [s.path for s in tab.controller.document.scans()] == [p2]
    tab.ask_open_paths = lambda: []
    tab.add_button.click()
    assert len(tab.controller.document.scans()) == 1


def drop(tab, paths):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    event = QDropEvent(
        QPointF(5, 5), Qt.DropAction.CopyAction, mime,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )
    tab.dropEvent(event)
    return event


def test_drop_of_files_and_folder_adds_scans(qtbot, make_tab, printouts, tmp_path):
    _, (p1, p2, p3) = printouts["three"]
    _, (other,) = printouts["foreign"]
    folder = tmp_path / "dropped"
    folder.mkdir()
    shutil.copy(p3, folder / "b-page-3.PNG")
    shutil.copy(p1, folder / "a-page-1.png")
    (folder / "notes.txt").write_text("not a scan")
    (folder / "inner").mkdir()
    shutil.copy(p2, folder / "inner" / "page-2.png")  # not recursed into
    tab = make_tab()
    assert tab.acceptDrops()
    event = drop(tab, [other, folder])
    assert event.isAccepted()
    assert [s.path for s in tab.controller.document.scans()] == [
        other, str(folder / "a-page-1.png"), str(folder / "b-page-3.PNG")
    ]
    wait_settled(qtbot, tab)
    assert tab.rows() == [
        "other.tar · A4 · 1 page",  # the earliest-added scan defines the document
        "Page 1 · Good",
        text.NOT_PART_OF_THIS_FILE,
        "big.tar · A4 · 3 pages · 2 scans",
    ]


# --- Saving ------------------------------------------------------------------------------


def never_confirm(message):
    raise AssertionError(f"unexpected confirmation: {message}")


def test_save_verified_document_writes_exact_bytes_without_confirmation(
    qtbot, make_tab, printouts, tmp_path, monkeypatch
):
    data, paths = printouts["two"]
    tab = make_tab()
    tab.controller.add_paths(paths)
    wait_settled(qtbot, tab)
    assert tab.controller.summary.state == DocState.VERIFIED

    def no_assemble(self):
        raise AssertionError("saving must stream the chunks")

    monkeypatch.setattr(Document, "assemble", no_assemble)
    asked = []
    tab.confirm = never_confirm
    tab.ask_save_path = lambda suggested: asked.append(suggested) or str(tmp_path / suggested)
    tab.show_error = lambda message: pytest.fail(message)
    tab.save_button.click()
    assert asked == ["doc.tar"]
    assert not tab.save_button.isEnabled()  # while the save runs
    qtbot.waitUntil(lambda: not tab.controller.saving, timeout=TIMEOUT)
    saved = (tmp_path / "doc.tar").read_bytes()
    assert len(saved) == len(data) and saved == data
    assert tab.summary.text() == (
        f"Verified · {len(data):,} bytes — Saved {len(data):,} bytes to doc.tar"
    )
    assert tab.save_button.isEnabled()
    assert [p.name for p in tmp_path.iterdir()] == ["doc.tar"]  # no temporary file left


def test_save_incomplete_asks_and_respects_no(
    qtbot, make_tab, printouts, tmp_path, monkeypatch
):
    data, (p1, _, p3) = printouts["three"]
    tab = make_tab()
    tab.controller.add_paths([p1, p3])
    wait_settled(qtbot, tab)
    monkeypatch.setattr(Document, "assemble", lambda self: pytest.fail("not streamed"))
    target = tmp_path / "out.tar"
    asked = []
    tab.ask_save_path = lambda suggested: asked.append(suggested) or str(target)
    tab.show_error = lambda message: pytest.fail(message)
    warnings = []
    tab.confirm = lambda message: warnings.append(message) or False
    tab.save_button.click()
    assert warnings == ["The saved file will be incomplete: page 2 is missing."]
    assert asked == [] and not target.exists()

    tab.confirm = lambda message: True
    tab.save_button.click()
    qtbot.waitUntil(lambda: not tab.controller.saving, timeout=TIMEOUT)
    saved = target.read_bytes()
    page = tab.controller.document.page_bytes
    assert len(saved) == len(data)  # cut to the tag's size
    assert saved[:page] == data[:page]
    assert saved[page:2 * page] == bytes(page)
    assert saved[2 * page:] == data[2 * page:]


@pytest.mark.skipif(os.name != "posix" or os.geteuid() == 0, reason="needs file permissions")
def test_save_failure_shows_error_and_keeps_existing_file(
    qtbot, make_tab, printouts, tmp_path
):
    _, paths = printouts["two"]
    tab = make_tab()
    tab.controller.add_paths(paths)
    wait_settled(qtbot, tab)
    target = tmp_path / "doc.tar"
    target.write_bytes(b"precious")
    target.chmod(0o444)
    errors = []
    tab.ask_save_path = lambda suggested: str(target)
    tab.show_error = errors.append
    tab.save_button.click()
    qtbot.waitUntil(lambda: errors != [], timeout=TIMEOUT)
    assert errors == [text.save_failed(f"cannot write {target}: Permission denied")]
    assert target.read_bytes() == b"precious"
    assert not tab.controller.saving
    assert tab.save_button.isEnabled()
    assert tab.summary.text() == f"Verified · {250_000:,} bytes"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["doc.tar"]


def test_large_document_is_checked_off_the_interface_thread(
    qtbot, make_tab, printouts, monkeypatch
):
    real = document_module.hashlib
    threads = []

    class Recording:
        @staticmethod
        def sha256(*args):
            threads.append(threading.get_ident())
            return real.sha256(*args)

    monkeypatch.setattr(document_module, "hashlib", Recording)
    tab = make_tab()
    tab.controller.inline_verdict_bytes = 1000  # every real document is "large" here
    states = []
    tab.controller.changed.connect(lambda: states.append(tab.controller.summary.state))
    tab.controller.add_paths(printouts["two"][1])
    qtbot.waitUntil(lambda: tab.controller.summary.state == DocState.VERIFIED, timeout=TIMEOUT)
    assert DocState.CHECKING in states
    assert threads and threading.get_ident() not in threads
    # Saving while the verdict is not known yet warns instead of hashing.
    doc = tab.controller.document
    sid = doc.pages()[0].scan_id
    doc.set_outcome(sid, doc.scan(sid).outcome)  # same bytes, new outcome: unknown verdict
    tab.controller.refresh()
    assert tab.controller.summary.state == DocState.CHECKING
    assert tab.controller.save_warning().startswith("The fingerprint is still being checked")
    qtbot.waitUntil(lambda: tab.controller.summary.state == DocState.VERIFIED, timeout=TIMEOUT)
    assert threading.get_ident() not in threads


# --- Responsiveness ------------------------------------------------------------------------


def test_a_burst_of_results_produces_few_refreshes(qtbot, make_tab, printouts):
    paths = printouts["two"][1] + printouts["three"][1] + printouts["foreign"][1]
    for path in paths:
        cached_process(path)  # decoded already, so the results arrive in a burst
    tab = make_tab()
    events = []
    tab.controller.runner.started.connect(lambda i: events.append(i))
    tab.controller.runner.finished.connect(lambda i, r: events.append(i))
    start = time.perf_counter()
    before = tab.controller.refreshes
    tab.controller.add_paths(paths)
    wait_settled(qtbot, tab)  # its own refresh at the end counts too
    elapsed_ms = (time.perf_counter() - start) * 1000
    refreshes = tab.controller.refreshes - before
    assert len(events) == 12
    assert refreshes <= elapsed_ms / 100 + 3
    assert refreshes <= 4  # one for adding, one or two for the burst, one at the end
    assert tab.refreshes >= refreshes


def test_interface_thread_is_not_blocked_while_pages_decode(qtbot, make_tab, printouts):
    paths = printouts["three"][1] + printouts["foreign"][1]
    tab = make_tab(process=process_scan)
    ticks = []
    timer = QTimer()
    timer.setInterval(20)
    timer.timeout.connect(lambda: ticks.append(time.perf_counter()))
    timer.start()
    try:
        tab.controller.add_paths(paths)
        wait_settled(qtbot, tab, DECODE_TIMEOUT)
    finally:
        timer.stop()
    assert tab.rows()[1:4] == ["Page 1 · Good", "Page 2 · Good", "Page 3 · Good"]
    gaps = [b - a for a, b in zip(ticks, ticks[1:], strict=False)]
    print(f"largest interface-thread gap: {max(gaps) * 1000:.0f} ms over {len(ticks)} ticks")
    # Decoding one page on the interface thread would block it for seconds. Observed:
    # 299 ms at load 28 and 638 ms at load 136 on 16 cores (three decoding threads
    # contend for the GIL; one alone leaves gaps of about 35 ms).
    assert max(gaps) < 1.5


def test_closing_while_working_stops_cleanly(qtbot, printouts, monkeypatch):
    paths = printouts["two"][1] + printouts["three"][1] + printouts["foreign"][1]
    dialogs = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: dialogs.append(a))
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: dialogs.append(a))
    controller = ReadController(process=process_scan)
    window = MainWindow(controller)
    qtbot.addWidget(window)
    tab = window.findChild(ReadTab, "readTab")
    assert tab is window.read_tab and window.tabs.widget(0) is tab
    assert window.tabs.tabText(0) == text.READ_TAB
    try:
        tab.controller.add_paths(paths)
        assert controller.runner.active == 6
        start = time.perf_counter()
        assert window.close()
        elapsed = time.perf_counter() - start
        assert elapsed < 10
        assert controller.runner.active == 0
        assert dialogs == []
        assert not [w for w in QApplication.topLevelWidgets()
                    if isinstance(w, QMessageBox) and w.isVisible()]
        refreshes = controller.refreshes
        qtbot.wait(300)
        assert controller.refreshes == refreshes  # nothing arrives after closing
    finally:
        controller.shutdown(TIMEOUT)  # let any function still running return


def test_remove_while_working_does_not_resurrect_the_scan(qtbot, make_tab, printouts):
    _, (p1, _) = printouts["two"]
    tab = make_tab(process=process_scan)
    tab.controller.add_paths([p1])
    doc = tab.controller.document
    (scan,) = doc.scans()
    assert scan.state == ScanState.WORKING
    tab.controller.remove(scan.id)
    qtbot.waitUntil(lambda: tab.controller.runner.active == 0, timeout=TIMEOUT)
    qtbot.wait(2 * 100)  # any refresh that a result would start
    assert doc.scans() == ()
    assert tab.rows() == []
    assert tab.controller.work_for(scan.id) is None


# --- A large document, without real scans ------------------------------------------------


def _synthetic(controller, pages):
    doc = controller.document
    for page in range(1, pages + 1):
        scan_id = doc.add_scan(f"/scans/{page}.png")
        doc.set_identified(scan_id, ScanInfo(A4.to_string(), pages, page, "big.bin", None))
        doc.set_outcome(scan_id, PageOutcome(b"x" * 16, (100, page % 3, 0, 0), page % 7 == 0))


def test_large_document_refreshes_quickly(qtbot, make_tab):
    tab = make_tab()
    _synthetic(tab.controller, 2000)
    start = time.perf_counter()
    tab.controller.refresh()
    first = time.perf_counter() - start
    assert len(tab.rows()) == 2001
    assert tab.rows()[7] == "Page 7 · Damaged · 1 lost"
    tab.select_row(1000)
    doc = tab.controller.document
    doc.set_outcome(doc.pages()[999].scan_id, PageOutcome(b"y" * 16, (100, 0, 0, 0), 0))
    start = time.perf_counter()
    tab.controller.refresh()
    again = time.perf_counter() - start
    assert tab.rows()[1000] == "Page 1,000 · Good"
    assert tab.detail.text().startswith("Page 1000 of 2000 · 1000.png\n")
    print(f"2,000 pages: first refresh {first * 1000:.0f} ms, next {again * 1000:.0f} ms")
    assert first < 2.0 and again < 2.0
