# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The window and its "Read from paper" tab, off-screen.

Decoding a scan takes seconds, so the printouts are written once per module and
most tests run them through ``cached_process``: the real ``process_scan``, with
each file's result remembered by path. The tests about responsiveness, closing
and removing while working use ``process_scan`` itself.
"""

import dataclasses
import os
import re
import shutil
import threading
import time

import numpy as np
import pytest
from PySide6.QtCore import QMimeData, QPointF, Qt, QTimer, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication, QMessageBox

import optar_gui.document as document_module
from optar import PAPERS, PARITY, PageFormat, encode, get_layout
from optar.container import plan_for, wrap
from optar.tag import make_tag, tagged_label
from optar_gui import text
from optar_gui.document import DocState, Document, PageOutcome, Row, ScanInfo, ScanState
from optar_gui.main_window import MainWindow
from optar_gui.read_tab import ReadController, ReadTab
from optar_gui.work import ScanWork, process_scan
from tests.helpers import fake_scan, save_scan, seeded_bytes

TIMEOUT = 120_000  # ms: decoding is slow on a loaded machine
DECODE_TIMEOUT = 600_000  # ms: four real decodes, two rounds on three workers
A4 = PageFormat.for_paper(PAPERS["a4"])

_RESULTS = {}
_RESULTS_LOCK = threading.Lock()


def cached_process(path, cancelled=lambda: False, on_progress=None):
    """``process_scan``, remembering each file's result by its path."""
    key = os.path.realpath(path)
    with _RESULTS_LOCK:
        if key in _RESULTS:
            return _RESULTS[key]
    work = process_scan(path, cancelled, on_progress=on_progress)
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
    """Waits for the scans, then for the fingerprint check that the redraw starts."""
    qtbot.waitUntil(settled(tab), timeout=timeout)
    tab.controller.refresh()
    qtbot.waitUntil(lambda: not tab.controller.checking, timeout=timeout)
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
    assert summary.text() == f"File recovered and verified · {len(data):,} bytes"
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


def test_dropped_paths_take_the_systems_spelling(qtbot, make_tab, printouts, tmp_path):
    # Qt gives forward slashes on Windows; the document holds the system's spelling,
    # the same as for a path from the file dialog.
    _, (other,) = printouts["foreign"]
    (tmp_path / "sub").mkdir()
    spelled = os.path.join(str(tmp_path), "sub", "..", "copy.png")
    shutil.copy(other, spelled)
    tab = make_tab()
    assert drop(tab, [spelled]).isAccepted()
    assert [s.path for s in tab.controller.document.scans()] == [os.path.normpath(spelled)]
    wait_settled(qtbot, tab)


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
        f"File recovered and verified · {len(data):,} bytes — Saved {len(data):,} bytes to doc.tar"
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
    doc = tab.controller.document
    page = doc.page_bytes
    page_3 = doc.pages()[2].scan_id

    def ask_while_page_3_is_removed(suggested):
        tab.controller.remove(page_3)  # after the warning was confirmed
        return str(target)

    tab.ask_save_path = ask_while_page_3_is_removed
    tab.save_button.click()
    qtbot.waitUntil(lambda: not tab.controller.saving, timeout=TIMEOUT)
    assert doc.pages()[2].scan_id is None
    saved = target.read_bytes()  # what the confirmed warning described
    assert len(saved) == len(data)  # cut to the tag's size
    assert saved[:page] == data[:page]
    assert saved[page:2 * page] == bytes(page)
    assert saved[2 * page:] == data[2 * page:]


def test_save_writes_what_the_warning_described(qtbot, make_tab, printouts, tmp_path):
    data, paths = printouts["untagged"]
    tab = make_tab()
    tab.controller.add_paths(paths)
    wait_settled(qtbot, tab)
    assert tab.controller.summary.state == DocState.UNVERIFIABLE
    doc = tab.controller.document
    page = doc.page_bytes
    before = b"".join(doc.chunks())
    target = tmp_path / "old.tar"
    tab.ask_save_path = lambda suggested: str(target)
    tab.show_error = lambda message: pytest.fail(message)
    warnings = []

    def confirm_while_page_1_gets_worse(message):
        # While the dialog is open a background result makes page 1 damaged.
        warnings.append(message)
        sid = doc.pages()[0].scan_id
        doc.set_outcome(sid, PageOutcome(b"\xff" * page, (0, 0, 0, 0), 99))
        assert doc.pages()[0].lost == 99
        return True

    tab.confirm = confirm_while_page_1_gets_worse
    tab.save_button.click()
    assert len(warnings) == 1 and "cannot be verified" in warnings[0]
    qtbot.waitUntil(lambda: not tab.controller.saving, timeout=TIMEOUT)
    assert target.read_bytes() == before  # not the damaged page shown since


def test_save_untagged_document_confirms_and_pads(qtbot, make_tab, printouts, tmp_path):
    data, paths = printouts["untagged"]
    tab = make_tab()
    tab.controller.add_paths(paths)
    wait_settled(qtbot, tab)
    target = tmp_path / "old.tar"
    asked = []
    tab.ask_save_path = lambda suggested: asked.append(suggested) or str(target)
    tab.show_error = lambda message: pytest.fail(message)
    warnings = []
    tab.confirm = lambda message: warnings.append(message) or True
    tab.save_button.click()
    assert warnings == [
        "These pages carry no tag, so the file cannot be verified and will be "
        "padded with zeros to a whole page."
    ]
    assert asked == ["old.tar"]
    qtbot.waitUntil(lambda: not tab.controller.saving, timeout=TIMEOUT)
    saved = target.read_bytes()
    page = tab.controller.document.page_bytes
    assert len(saved) == 2 * page > len(data)  # padded to whole pages
    assert saved[: len(data)] == data and saved[len(data):] == bytes(2 * page - len(data))


def test_save_document_that_does_not_match_confirms(qtbot, make_tab, printouts, tmp_path):
    data, paths = printouts["two"]
    wrong = make_tag(seeded_bytes(99, len(data)))  # same size, another fingerprint

    def mislabelled(path, cancelled=lambda: False, on_progress=None):
        work = cached_process(path, cancelled)
        return dataclasses.replace(work, info=dataclasses.replace(work.info, tag=wrong))

    tab = make_tab(process=mislabelled)
    tab.controller.add_paths(paths)
    wait_settled(qtbot, tab)
    assert tab.controller.summary.state == DocState.MISMATCH
    target = tmp_path / "doc.tar"
    tab.ask_save_path = lambda suggested: str(target)
    tab.show_error = lambda message: pytest.fail(message)
    warnings = []
    tab.confirm = lambda message: warnings.append(message) or False
    tab.save_button.click()
    assert warnings == [
        "The recovered file does not match the fingerprint printed on the paper: "
        "some data was decoded wrongly, so this is not the original file."
    ]
    assert not target.exists() and not tab.controller.saving
    tab.confirm = lambda message: warnings.append(message) or True
    tab.save_button.click()
    qtbot.waitUntil(lambda: not tab.controller.saving, timeout=TIMEOUT)
    assert len(warnings) == 2 and target.read_bytes() == data


def test_a_save_still_running_when_closing_runs_out_of_time_leaves_no_file(
    qtbot, make_tab, printouts, tmp_path, monkeypatch
):
    _, paths = printouts["two"]
    tab = make_tab()
    tab.controller.add_paths(paths)
    wait_settled(qtbot, tab)
    target = tmp_path / "doc.tar"
    target.write_bytes(b"precious")
    real_chunks = Document.chunks
    gate = threading.Event()

    def stuck_chunks(self):
        chunks = real_chunks(self)
        yield next(chunks)  # written; the next one is late
        gate.wait(TIMEOUT / 1000)
        yield from chunks

    monkeypatch.setattr(Document, "chunks", stuck_chunks)
    tab.controller.save(str(target))
    qtbot.waitUntil(lambda: len(list(tmp_path.iterdir())) == 2, timeout=TIMEOUT)  # temp file
    assert not tab.controller.shutdown(300)  # the budget runs out: the save is told to stop
    gate.set()
    qtbot.waitUntil(lambda: [p.name for p in tmp_path.iterdir()] == ["doc.tar"], timeout=TIMEOUT)
    assert target.read_bytes() == b"precious"


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
    assert tab.summary.text() == f"File recovered and verified · {250_000:,} bytes"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["doc.tar"]


def test_saving_clears_the_note_when_the_document_changes(
    qtbot, make_tab, printouts, tmp_path
):
    data, (p1, p2) = printouts["two"]
    tab = make_tab()
    tab.controller.add_paths([p1, p2])
    wait_settled(qtbot, tab)
    tab.ask_save_path = lambda suggested: str(tmp_path / suggested)
    tab.save_button.click()
    qtbot.waitUntil(lambda: not tab.controller.saving, timeout=TIMEOUT)
    assert "Saved" in tab.summary.text()
    tab.select_row(find_row(tab, "Page 2 · Good"))
    tab.remove_button.click()
    assert tab.summary.text() == "1 of 2 pages good · 1 missing"
    tab.controller.note = "Saved 1 byte to x"
    tab.controller.add_paths([p2])
    assert "Saved" not in tab.summary.text()


def test_save_after_closing_is_refused_with_its_own_message(qtbot, make_tab, printouts):
    tab = make_tab()
    tab.controller.add_paths(printouts["two"][1][:1])
    wait_settled(qtbot, tab)
    assert tab.controller.shutdown(TIMEOUT)
    with pytest.raises(RuntimeError, match=re.escape(text.SAVE_AFTER_CLOSE)):
        tab.controller.save("/nowhere/x.bin")


def test_closing_lets_a_running_save_finish(qtbot, make_tab, printouts, tmp_path, monkeypatch):
    data, paths = printouts["two"]
    tab = make_tab()
    tab.controller.add_paths(paths)
    wait_settled(qtbot, tab)
    real_chunks = Document.chunks

    def slow_chunks(self):
        for chunk in real_chunks(self):
            time.sleep(0.5)  # longer than closing takes when nothing waits for the save
            yield chunk

    monkeypatch.setattr(Document, "chunks", slow_chunks)
    target = tmp_path / "doc.tar"
    tab.controller.save(str(target))
    assert tab.controller.saving
    assert tab.controller.shutdown(30_000)
    assert target.read_bytes() == data
    assert sorted(p.name for p in tmp_path.iterdir()) == ["doc.tar"]


def test_a_failed_check_is_shown_and_not_retried(qtbot, make_tab, printouts, monkeypatch):
    calls = []

    def broken(self, cancelled=lambda: False):
        calls.append(1)
        raise RuntimeError("boom")

    monkeypatch.setattr(document_module.VerdictJob, "__call__", broken)
    tab = make_tab()
    tab.controller.add_paths(printouts["two"][1])
    wait_settled(qtbot, tab)
    assert tab.controller.summary.state == DocState.CHECKING
    assert tab.summary.text() == text.check_failed("RuntimeError: boom")
    for _ in range(3):
        tab.controller.refresh()
    qtbot.wait(300)
    assert len(calls) == 1 and not tab.controller.checking
    assert tab.summary.text() == text.check_failed("RuntimeError: boom")
    # Other pages make a new check, which is tried.
    doc = tab.controller.document
    sid = doc.pages()[0].scan_id
    doc.set_outcome(sid, doc.scan(sid).outcome)
    tab.controller.refresh()
    qtbot.waitUntil(lambda: len(calls) == 2, timeout=TIMEOUT)


def test_fingerprint_is_checked_off_the_interface_thread(
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
    # One for adding, one or two for the burst, up to three around the check.
    assert refreshes <= 7
    assert tab.refreshes >= refreshes


@pytest.mark.slow
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
        assert elapsed < 10  # closing waits a bounded time
        assert dialogs == []
        assert not [w for w in QApplication.topLevelWidgets()
                    if isinstance(w, QMessageBox) and w.isVisible()]
        results = []
        controller.runner.finished.connect(lambda *args: results.append(args))
        controller.runner.failed.connect(lambda *args: results.append(args))
        states = [(s.id, s.state, s.info, s.outcome) for s in controller.document.scans()]
        # The running decodes really stop: each checks ``cancelled`` between its
        # stages, so all of them return within one stage's time.
        assert controller.shutdown(30_000)
        qtbot.wait(200)  # a result delivered late would arrive now
        assert results == []  # nothing arrived after closing
        assert [(s.id, s.state, s.info, s.outcome)
                for s in controller.document.scans()] == states  # fmt: skip
    finally:
        controller.shutdown(TIMEOUT)


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
    assert tab.detail.text().startswith("Page 1,000 of 2,000 · 1000.png\n")
    print(f"2,000 pages: first refresh {first * 1000:.0f} ms, next {again * 1000:.0f} ms")
    assert first < 2.0 and again < 2.0


# --- Version-1 documents ---------------------------------------------------------------

XLARGE = get_layout("a4", "xlarge")  # small pages keep these tests fast
V1_NAME = "v1.bin"


def _v1_printout(folder, pages, parity, seed):
    """A version-1 printout of exactly ``pages`` pages as exact PNG scans."""
    fmt = XLARGE.fmt
    size = plan_for(pages, fmt, parity).data_bytes - 1 - len(V1_NAME)
    data = seeded_bytes(seed, size)
    folder.mkdir()
    paths = []
    for page in encode(wrap(data, V1_NAME, fmt, parity), fmt, V1_NAME):
        path = folder / f"page-{page.number}.png"
        save_scan(path, fake_scan(page.pixels, scale=2, margin=40))
        paths.append(str(path))
    assert len(paths) == pages
    return data, paths


@pytest.fixture(scope="module")
def v1_printouts(tmp_path_factory):
    root = tmp_path_factory.mktemp("v1")
    return {
        "three": _v1_printout(root / "three", 3, PARITY["standard"], 11),
        "twelve": _v1_printout(root / "twelve", 12, PARITY["standard"], 12),
    }


def all_plain(tab):
    """Every label of the tab shows plain text, never rich text."""
    for label in (tab.summary, tab.detail, tab.caution):
        assert label.textFormat() == Qt.TextFormat.PlainText


def test_three_version1_scans_are_verified_and_saved(qtbot, make_tab, v1_printouts, tmp_path):
    data, paths = v1_printouts["three"]
    tab = make_tab()
    states = []
    tab.controller.changed.connect(lambda: states.append(tab.summary.text()))
    tab.controller.add_paths(list(reversed(paths)))
    wait_settled(qtbot, tab)
    summary = tab.controller.summary
    assert summary.state == DocState.VERIFIED and summary.repair.verified
    assert tab.summary.text() == (
        f"File recovered and verified · {len(data):,} bytes · {text.repair_line(summary.repair)}"
    )
    assert text.REPAIRING in states  # shown while the repair ran
    assert tab.rows()[1:] == ["Page 1 · Good", "Page 2 · Good", "Page 3 · Good"]
    assert not tab.caution.isVisible()
    assert all(w not in tab.summary.text().lower() for w in ("parity", "codeword", "header"))
    all_plain(tab)
    asked = []
    tab.confirm = never_confirm
    tab.ask_save_path = lambda suggested: asked.append(suggested) or str(tmp_path / suggested)
    tab.show_error = lambda message: pytest.fail(message)
    assert tab.save_button.isEnabled()
    tab.save_button.click()
    qtbot.waitUntil(lambda: not tab.controller.saving, timeout=TIMEOUT)
    assert asked == [V1_NAME]
    assert (tmp_path / V1_NAME).read_bytes() == data
    assert sorted(p.name for p in tmp_path.iterdir()) == [V1_NAME]


def test_a_version1_scan_is_decoded_once_and_keeps_no_payload(qtbot, make_tab, v1_printouts):
    _, paths = v1_printouts["three"]
    tab = make_tab()
    tab.controller.add_paths(paths[:1])
    wait_settled(qtbot, tab)
    doc = tab.controller.document
    (scan,) = doc.scans()
    assert scan.info.header is not None and scan.info.header.page == 1
    work = tab.controller.work_for(scan.id)
    assert work.scan_dpi == pytest.approx(2 * float(XLARGE.pixels_per_inch), rel=0.02)
    assert work.outcome is None and work.payload is None  # the document holds them
    assert tab.controller.scan_note(work) is None  # two pixels per dot: not too coarse


def test_assigning_into_a_version1_document_is_refused_not_raised(
    qtbot, make_tab, v1_printouts, tmp_path
):
    # The page dialog can be open while the document under it becomes one that
    # takes no pages by hand: the choice is then dropped, without an error.
    _, paths = v1_printouts["three"]
    blank = tmp_path / "blank.png"
    save_scan(blank, np.full((600, 400), 255, np.uint8))
    tab = make_tab()
    tab.controller.add_paths([paths[0], str(blank)])
    wait_settled(qtbot, tab)
    doc = tab.controller.document
    unreadable = doc.scan_id_of(str(blank))
    assert doc.actions(Row.UNREADABLE, unreadable).assign is None
    before = doc.slots()
    assert tab.controller.assign(unreadable, 2) is False
    assert tab.controller.assign(unreadable + 50, 1) is False  # removed meanwhile
    assert doc.slots() == before


def test_one_page_of_twelve_missing_is_recoverable_and_saves_the_original(
    qtbot, make_tab, v1_printouts, tmp_path
):
    data, paths = v1_printouts["twelve"]
    tab = make_tab()
    tab.controller.add_paths(paths[:4] + paths[5:])  # page 5 missing
    wait_settled(qtbot, tab, DECODE_TIMEOUT)
    summary = tab.controller.summary
    assert summary.state == DocState.RECOVERABLE and summary.missing_pages == (5,)
    assert tab.summary.text().startswith("Recoverable: page 5 missing")
    assert "Page 5 · Missing" in tab.rows()
    assert tab.save_button.isEnabled()
    all_plain(tab)
    target = tmp_path / "out.bin"
    tab.confirm = never_confirm  # the fingerprint matched: nothing to confirm
    tab.ask_save_path = lambda suggested: str(target)
    tab.show_error = lambda message: pytest.fail(message)
    tab.save_button.click()
    qtbot.waitUntil(lambda: not tab.controller.saving, timeout=TIMEOUT)
    assert target.read_bytes() == data


def test_a_failed_repair_advises_rescanning_and_saves_only_after_a_warning(
    qtbot, make_tab, v1_printouts, tmp_path
):
    data, paths = v1_printouts["twelve"]
    tab = make_tab()
    tab.controller.add_paths(paths[:2] + paths[5:])  # pages 3, 4 and 5 missing
    wait_settled(qtbot, tab, DECODE_TIMEOUT)
    summary = tab.controller.summary
    assert summary.state == DocState.INCOMPLETE
    assert summary.repair is not None and summary.repair.data is None
    shown = tab.summary.text()
    assert text.rescan_advice(summary.repair) in shown
    assert "pages 3-5" in shown or "pages 3, 4 and 5" in shown
    assert "verified" not in shown.lower()
    all_plain(tab)
    assert tab.save_button.isEnabled()  # the best effort, after a warning
    target = tmp_path / "out.bin"
    tab.ask_save_path = lambda suggested: str(target)
    tab.show_error = lambda message: pytest.fail(message)
    warnings = []
    tab.confirm = lambda message: warnings.append(message) or False
    tab.save_button.click()
    assert len(warnings) == 1 and "could not be fully repaired" in warnings[0]
    assert "verified" not in warnings[0].lower()
    assert not target.exists()
    tab.confirm = lambda message: True
    tab.save_button.click()
    qtbot.waitUntil(lambda: not tab.controller.saving, timeout=TIMEOUT)
    saved = target.read_bytes()
    assert saved == summary.repair.best_effort and len(saved) == len(data)
    assert "verified" not in tab.summary.text().lower()


def test_a_repair_that_raises_is_shown_as_plain_text_and_not_retried(
    qtbot, make_tab, v1_printouts, monkeypatch
):
    calls = []

    def broken(self, cancelled=lambda: False):
        calls.append(1)
        raise ValueError("<b>boom</b>")

    monkeypatch.setattr(document_module.RepairJob, "__call__", broken)
    tab = make_tab()
    tab.controller.add_paths(v1_printouts["three"][1])
    wait_settled(qtbot, tab)
    assert tab.controller.summary.state == DocState.INCOMPLETE
    assert tab.summary.text() == text.repair_failed("ValueError: <b>boom</b>")
    all_plain(tab)
    assert not tab.save_button.isEnabled()
    for _ in range(3):
        tab.controller.refresh()
    qtbot.wait(300)
    assert len(calls) == 1 and not tab.controller.checking


def test_closing_or_removing_while_repairing_stops_cleanly(
    qtbot, make_tab, v1_printouts, monkeypatch
):
    started, release = threading.Event(), threading.Event()
    ended = []  # (pages repaired, whether cancelled) of every repair that returned
    real = document_module.RepairJob.__call__

    def slow(self, cancelled=lambda: False):
        started.set()
        while not cancelled() and not release.wait(0.01):
            pass
        ended.append((tuple(sorted(self._pages)), cancelled()))
        return real(self, cancelled)

    monkeypatch.setattr(document_module.RepairJob, "__call__", slow)
    dialogs = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: dialogs.append(a))
    _, paths = v1_printouts["three"]
    tab = make_tab()
    controller = tab.controller
    controller.add_paths(paths)
    qtbot.waitUntil(started.is_set, timeout=TIMEOUT)
    assert controller.checking and tab.summary.text() == text.REPAIRING
    # Removing a page while the repair runs: that repair stops, one for the pages
    # left starts, and only its result counts.
    started.clear()
    controller.remove(controller.document.pages()[2].scan_id)
    qtbot.waitUntil(started.is_set, timeout=TIMEOUT)
    qtbot.waitUntil(lambda: len(ended) == 1, timeout=TIMEOUT)
    assert ended == [((1, 2, 3), True)]
    release.set()
    qtbot.waitUntil(lambda: not controller.checking, timeout=TIMEOUT)
    controller.refresh()
    assert ended[1] == ((1, 2), False)
    summary = controller.summary
    assert summary.missing_pages == (3,) and summary.state != DocState.VERIFIED
    assert summary.repair is not None and summary.repair.missing == (3,)
    # Closing while a repair runs: it stops at once and nothing is reported.
    release.clear()
    started.clear()
    controller.add_paths(paths[2:])
    qtbot.waitUntil(started.is_set, timeout=TIMEOUT)
    start = time.perf_counter()
    assert controller.shutdown(10_000)
    assert time.perf_counter() - start < 5
    assert ended[2] == ((1, 2, 3), True)
    assert dialogs == []


def test_a_coarse_scan_is_noted_on_its_page_and_when_unreadable(qtbot, make_tab):
    std = get_layout("a4")
    data = b"x" * 100
    tag = make_tag(data)
    works = {
        "page.png": ScanWork(
            ScanInfo(A4.to_string(), 1, 1, "doc", tag), "",
            PageOutcome(data.ljust(16, b"\0"), (100, 0, 0, 0), 0), 0, None, (10, 10),
            scan_dpi=296.0, layout=std,
        ),
        "coarse.png": ScanWork(
            None, text.coarse_scan(203.0, None), None, 0, None, (10, 10), scan_dpi=203.0
        ),
        "photo.png": ScanWork(
            None, "label unreadable", None, 0, None, (10, 10), scan_dpi=600.0
        ),
    }
    def process(path, cancelled=lambda: False, on_progress=None):
        return works[os.path.basename(path)]

    tab = make_tab(process=process)
    tab.controller.add_paths(["/scans/page.png", "/scans/coarse.png", "/scans/photo.png"])
    wait_settled(qtbot, tab)
    def starting(prefix):
        return next(i for i, row in enumerate(tab.rows()) if row.startswith(prefix))

    tab.select_row(starting("Page 1 "))
    assert text.coarse_scan(296.0, std) in tab.detail.text().splitlines()
    tab.select_row(starting("coarse.png"))
    assert tab.detail.text().splitlines() == ["coarse.png", text.coarse_scan(203.0, None)]
    assert f"coarse.png · {text.coarse_scan(203.0, None)}" in tab.rows()
    tab.select_row(starting("photo.png"))
    assert text.coarse_scan(600.0, None) not in tab.detail.text()
    assert "dpi" not in tab.detail.text()
