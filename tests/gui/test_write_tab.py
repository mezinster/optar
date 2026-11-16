# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The "Put on paper" tab, the window's close handling and the entry point, off-screen."""

import os
import threading

import pytest
from PySide6.QtCore import QMimeData, QPointF, Qt, QTimer, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QRadioButton

import optar.encoder as encoder_module
import optar_gui.__main__ as entry
from optar import PAPERS, PageFormat
from optar.encoder import page_count
from optar.tag import make_tag
from optar_gui import text
from optar_gui.document import DocState
from optar_gui.main_window import MainWindow
from optar_gui.read_tab import ReadController
from optar_gui.work import encode_to_pdf, prepare_file
from optar_gui.write_tab import WriteTab
from tests.helpers import fake_scan, parse_pdf, save_scan, seeded_bytes

TIMEOUT = 120_000  # ms: the machine may be heavily loaded
DECODE_TIMEOUT = 600_000
A4 = PageFormat.for_paper(PAPERS["a4"])
LETTER = PageFormat.for_paper(PAPERS["letter"])


@pytest.fixture
def make_tab(qtbot):
    tabs = []

    def make(**kw):
        tab = WriteTab(**kw)
        qtbot.addWidget(tab)
        tabs.append(tab)
        return tab

    yield make
    for tab in tabs:
        tab.shutdown(TIMEOUT)


def child(tab, cls, name):
    widget = tab.findChild(cls, name)
    assert widget is not None, name
    return widget


def write_file(tmp_path, name, data):
    path = tmp_path / name
    path.write_bytes(data)
    return str(path)


def choose(qtbot, tab, path):
    tab.set_file(path)
    qtbot.waitUntil(lambda: tab.prepared, timeout=TIMEOUT)


def page_one_free_text(fmt, data, name):
    """What page 1 prints after the format and page number, built independently."""
    total = page_count(len(data), fmt)
    tag = make_tag(data)
    return f"[{tag.size}:{tag.fingerprint}:{tag.check(1, total)}] {name}"


# --- Choosing a file ------------------------------------------------------------------


def test_choosing_a_file_fills_name_pages_and_printed_label(qtbot, make_tab, tmp_path):
    data = seeded_bytes(1, 250_000)
    path = write_file(tmp_path, "data.bin", data)
    tab = make_tab()
    assert child(tab, QRadioButton, "paperA4").isChecked()
    assert child(tab, QLabel, "reminderLabel").text() == text.ACTUAL_SIZE
    assert not child(tab, QPushButton, "createButton").isEnabled()
    choose(qtbot, tab, path)
    assert child(tab, QLineEdit, "fileEdit").text() == path
    assert child(tab, QLineEdit, "nameEdit").text() == "data.bin"
    info = child(tab, QLabel, "infoLabel").text()
    assert "2 pages" in info
    assert "250,000 bytes" in info
    assert child(tab, QLabel, "printsAsLabel").text() == page_one_free_text(A4, data, "data.bin")
    assert child(tab, QLabel, "warningLabel").isHidden()
    assert child(tab, QPushButton, "createButton").isEnabled()
    # Editing the name changes what prints at once.
    child(tab, QLineEdit, "nameEdit").setText("photos.tar")
    assert child(tab, QLabel, "printsAsLabel").text() == page_one_free_text(
        A4, data, "photos.tar")


def test_letter_changes_page_count(qtbot, make_tab, tmp_path):
    # A size between Letter's and A4's capacity for two pages.
    a4_bytes, letter_bytes = A4.net_bits // 8, LETTER.net_bits // 8
    assert a4_bytes != letter_bytes
    nbytes = 2 * min(a4_bytes, letter_bytes) + 1
    data = seeded_bytes(2, nbytes)
    tab = make_tab()
    choose(qtbot, tab, write_file(tmp_path, "data.bin", data))
    a4_total, letter_total = page_count(nbytes, A4), page_count(nbytes, LETTER)
    assert a4_total != letter_total
    assert f"{a4_total} pages" in child(tab, QLabel, "infoLabel").text()
    child(tab, QRadioButton, "paperLetter").setChecked(True)
    assert f"{letter_total} pages" in child(tab, QLabel, "infoLabel").text()
    assert child(tab, QLabel, "printsAsLabel").text() == page_one_free_text(
        LETTER, data, "data.bin")


def test_non_ascii_name_warns_and_shows_what_prints(qtbot, make_tab, tmp_path):
    data = seeded_bytes(3, 1000)
    tab = make_tab()
    choose(qtbot, tab, write_file(tmp_path, "отпуск.tar", data))
    assert child(tab, QLineEdit, "nameEdit").text() == "отпуск.tar"
    shown = child(tab, QLabel, "printsAsLabel").text()
    assert shown.endswith("] .tar")
    assert shown == page_one_free_text(A4, data, ".tar")
    warning = child(tab, QLabel, "warningLabel")
    assert not warning.isHidden()
    assert "not printed" in warning.text()
    assert "о" in warning.text()
    assert "cut" not in warning.text()
    child(tab, QLineEdit, "nameEdit").setText("holiday.tar")
    assert warning.isHidden()


def test_long_name_warns_about_cut(qtbot, make_tab, tmp_path):
    data = seeded_bytes(4, 1000)
    tab = make_tab()
    choose(qtbot, tab, write_file(tmp_path, "data.bin", data))
    long_name = "x" * 90 + ".tar"
    child(tab, QLineEdit, "nameEdit").setText(long_name)
    shown = child(tab, QLabel, "printsAsLabel").text()
    tag_text = page_one_free_text(A4, data, "")
    assert shown.startswith(tag_text)
    assert long_name.startswith(shown[len(tag_text):])
    assert len(shown) < len(tag_text) + len(long_name)
    warning = child(tab, QLabel, "warningLabel")
    assert not warning.isHidden()
    assert "cut" in warning.text()
    assert "not printed" not in warning.text()


def test_preparing_a_file_runs_off_the_interface_thread(qtbot, make_tab, tmp_path):
    path = write_file(tmp_path, "big.bin", seeded_bytes(5, 1000))
    release = threading.Event()
    threads = []

    def slow_prepare(p, cancelled):
        threads.append(threading.get_ident())
        assert release.wait(TIMEOUT / 1000)
        return prepare_file(p, cancelled)

    tab = make_tab(prepare=slow_prepare)
    ticks = []
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start()
    tab.set_file(path)  # returns at once while the file is being read
    try:
        assert not tab.prepared
        assert child(tab, QLabel, "infoLabel").text() == text.PREPARING
        assert not child(tab, QPushButton, "createButton").isEnabled()
        qtbot.waitUntil(lambda: len(ticks) >= 5, timeout=TIMEOUT)
        assert not tab.prepared
        assert threads and threads[0] != threading.get_ident()
    finally:
        release.set()
        timer.stop()
    qtbot.waitUntil(lambda: tab.prepared, timeout=TIMEOUT)
    assert "1 page" in child(tab, QLabel, "infoLabel").text()


def test_dropping_a_file_chooses_it(qtbot, make_tab, tmp_path):
    path = write_file(tmp_path, "dropped.bin", seeded_bytes(6, 500))
    tab = make_tab()
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(path)])
    event = QDropEvent(QPointF(5, 5), Qt.DropAction.CopyAction, mime,
                       Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    tab.dropEvent(event)
    qtbot.waitUntil(lambda: tab.prepared, timeout=TIMEOUT)
    assert child(tab, QLineEdit, "nameEdit").text() == "dropped.bin"


# --- Creating the PDF ------------------------------------------------------------------


def test_create_pdf_round_trips_through_the_reading_tab(qtbot, make_tab, tmp_path):
    data = seeded_bytes(7, 250_000)
    src = write_file(tmp_path, "data.bin", data)
    dest = tmp_path / "out" / "data.pdf"
    dest.parent.mkdir()
    threads = []

    def recording_encode(*args, **kw):
        threads.append(threading.get_ident())
        return encode_to_pdf(*args, **kw)

    tab = make_tab(encode=recording_encode)
    choose(qtbot, tab, src)
    asked = []

    def ask(suggested):
        asked.append(suggested)
        return str(dest)

    tab.ask_save_path = ask
    child(tab, QPushButton, "createButton").click()
    assert asked == [os.path.join(str(tmp_path), "data.pdf")]
    status = child(tab, QLabel, "statusLabel")
    qtbot.waitUntil(lambda: not tab.creating, timeout=TIMEOUT)
    assert status.text() == text.created_message(str(dest), 2)
    assert threads and threads[0] != threading.get_ident()

    pages = parse_pdf(dest)
    assert len(pages) == 2
    scans = tmp_path / "scans"
    scans.mkdir()
    paths = []
    for i, page in enumerate(pages, 1):
        path = scans / f"page-{i}.png"
        save_scan(path, fake_scan(page["pixels"], scale=1))
        paths.append(str(path))
    controller = ReadController()
    try:
        controller.add_paths(paths)
        assert controller.runner.wait_idle(DECODE_TIMEOUT)
        controller.refresh()  # starts the fingerprint check in the background
        qtbot.waitUntil(lambda: not controller.checking, timeout=TIMEOUT)
        controller.refresh()
        assert controller.summary.state == DocState.VERIFIED
        assert controller.document.assemble() == data
        assert controller.document.current.title == "data.bin"
    finally:
        controller.shutdown(TIMEOUT)


def test_a_pdf_source_is_not_offered_as_the_destination(qtbot, make_tab, tmp_path):
    src = write_file(tmp_path, "report.pdf", seeded_bytes(10, 1000))
    tab = make_tab()
    choose(qtbot, tab, src)
    asked = []
    tab.ask_save_path = lambda suggested: asked.append(suggested) or None
    child(tab, QPushButton, "createButton").click()
    assert asked == [os.path.join(str(tmp_path), "report-optar.pdf")]


def test_the_source_chosen_as_destination_is_refused(qtbot, make_tab, tmp_path):
    data = seeded_bytes(11, 1000)
    src = write_file(tmp_path, "report.pdf", data)
    encodes = []
    tab = make_tab(encode=lambda *args, **kw: encodes.append(args) or 1)
    choose(qtbot, tab, src)
    status = child(tab, QLabel, "statusLabel")
    spellings = [src, os.path.join(str(tmp_path), ".", "report.pdf")]
    if hasattr(os, "symlink"):
        os.symlink(src, tmp_path / "link.pdf")
        spellings.append(str(tmp_path / "link.pdf"))
    for spelling in spellings:
        tab.ask_save_path = lambda suggested, spelling=spelling: spelling
        child(tab, QPushButton, "createButton").click()
        assert status.text() == text.create_failed(text.DEST_IS_SOURCE), spelling
        assert not tab.creating
    assert encodes == []
    assert (tmp_path / "report.pdf").read_bytes() == data


def test_too_many_pages_is_reported(qtbot, make_tab, tmp_path, monkeypatch):
    monkeypatch.setattr(encoder_module, "MAX_PAGES", 1)
    tab = make_tab()
    choose(qtbot, tab, write_file(tmp_path, "data.bin", seeded_bytes(8, 250_000)))
    assert "2 pages" in child(tab, QLabel, "infoLabel").text()
    asked = []
    tab.ask_save_path = lambda suggested: asked.append(suggested) or str(tmp_path / "x.pdf")
    child(tab, QPushButton, "createButton").click()
    assert asked == []
    assert "too many pages" in child(tab, QLabel, "statusLabel").text()
    assert not tab.creating
    assert not (tmp_path / "x.pdf").exists()


def test_unreadable_file_is_reported_before_asking(qtbot, make_tab, tmp_path):
    tab = make_tab()
    folder = tmp_path / "folder.bin"
    folder.mkdir()
    choose(qtbot, tab, str(folder))  # a folder cannot be read as a file
    assert child(tab, QLabel, "infoLabel").text() == ""
    assert child(tab, QLabel, "printsAsLabel").text() == ""
    status = child(tab, QLabel, "statusLabel")
    assert status.text().startswith(text.file_unreadable(""))
    asked = []
    tab.ask_save_path = lambda suggested: asked.append(suggested) or str(tmp_path / "x.pdf")
    child(tab, QPushButton, "createButton").click()
    assert asked == []
    assert status.text().startswith(text.file_unreadable(""))


def test_create_pdf_failure_is_reported_and_keeps_existing_file(qtbot, make_tab, tmp_path):
    src = write_file(tmp_path, "data.bin", seeded_bytes(9, 1000))
    dest = tmp_path / "data.pdf"
    dest.write_bytes(b"existing")
    tab = make_tab()
    choose(qtbot, tab, src)
    os.remove(src)  # the file disappears after it was chosen
    tab.ask_save_path = lambda suggested: str(dest)
    child(tab, QPushButton, "createButton").click()
    qtbot.waitUntil(lambda: not tab.creating, timeout=TIMEOUT)
    status = child(tab, QLabel, "statusLabel").text()
    assert status.startswith(text.create_failed(""))
    assert "data.bin" in status
    assert dest.read_bytes() == b"existing"
    assert sorted(os.listdir(tmp_path)) == ["data.pdf"]
    assert child(tab, QPushButton, "createButton").isEnabled()


# --- The window ------------------------------------------------------------------------


# Showing a window off-screen makes the offscreen plugin warn about size hints.
@pytest.mark.qt_log_ignore("This plugin does not support propagateSizeHints")
def test_window_has_both_tabs_and_hides_before_shutting_down(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == [
        text.READ_TAB, text.WRITE_TAB]
    assert window.findChild(WriteTab, "writeTab") is window.write_tab
    seen = []
    read_shutdown = window.read_tab.controller.shutdown
    write_shutdown = window.write_tab.shutdown

    def record(name, real):
        def shutdown(*args, **kw):
            seen.append((name, window.isVisible()))
            return real(*args, **kw)
        return shutdown

    window.read_tab.controller.shutdown = record("read", read_shutdown)
    window.write_tab.shutdown = record("write", write_shutdown)
    window.close()
    assert sorted(seen) == [("read", False), ("write", False)]


# --- The entry point -------------------------------------------------------------------


def test_main_version_and_missing_arguments(capsys, monkeypatch):
    from optar import __version__

    assert entry.main(["--version"]) == 0
    assert capsys.readouterr().out == f"optar-gui {__version__}\n"
    assert entry.main(["--no-such-option"]) == 2
    assert "--no-such-option" in capsys.readouterr().err
    # Without PySide6 the window cannot start: say how to install it.
    monkeypatch.setitem(__import__("sys").modules, "PySide6", None)
    assert entry.main([]) == 2
    assert capsys.readouterr().err == "optar-gui needs PySide6: pip install 'optar[gui]'\n"
