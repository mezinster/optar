# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Choosing a language in the menu changes the whole window at once.

The stand-in language is English with every entry marked (``MARK`` before each
string, placeholders kept), so any text left in English after a switch is
caught without a real translation. A window built afresh in the new language
is the reference: whatever the switched window shows must equal it.
"""

import os
import threading

import pytest
from PySide6.QtCore import QLocale
from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QGraphicsSimpleTextItem,
    QLabel,
    QMessageBox,
)

import optar_gui.document as document_module
import optar_gui.read_tab as read_tab_module
from optar import PAPERS, PageFormat, i18n
from optar.errors import OptarError, error
from optar.identify import LABEL_UNREADABLE, STEP_FIND
from optar.tag import make_tag
from optar_gui import language, text
from optar_gui.document import DocState, PageOutcome, Progress, Row, ScanInfo
from optar_gui.main_window import MainWindow
from optar_gui.read_tab import ReadController, ReadTab
from optar_gui.work import ScanWork, prepare_file, process_scan
from tests.gui.conftest import MARK

TIMEOUT = 60_000  # ms
A_FMT = PageFormat.for_paper(PAPERS["a4"]).to_string()
SIZE = (100, 141)


@pytest.fixture
def make_window(qtbot):
    """make_window(process=None) -> MainWindow, with its controller shut down after."""
    controllers = []

    def make(process=None, **kw):
        controller = None
        if process is not None:
            controller = ReadController(process=process, **kw)
            controllers.append(controller)
        window = MainWindow(controller)
        qtbot.addWidget(window)
        controllers.append(window.read_tab.controller)
        return window

    yield make
    for controller in controllers:
        controller.shutdown(TIMEOUT)


def choose(window, code):
    action = next(a for a in window.language_menu.actions() if a.data() == code)
    action.trigger()


def shown(window):
    """Every text the window shows, by where it is; language names are left out."""
    out = {"title": window.windowTitle(), "menu": window.language_menu.title()}
    for i in range(window.tabs.count()):
        out[f"tab {i}"] = window.tabs.tabText(i)
    for i, action in enumerate(window.language_menu.actions()):
        if action.data() is None:
            out[f"menu entry {i}"] = action.text()
    for widget in window.findChildren(QAbstractButton):
        out[f"button {widget.objectName() or id(widget)}"] = widget.text()
    labels = [w for w in window.findChildren(QLabel) if w.objectName() != "printsAsLabel"]
    for i, widget in enumerate(labels):
        out[f"label {widget.objectName() or i}"] = widget.text()
    for box in window.findChildren(QComboBox):
        for i in range(box.count()):
            out[f"{box.objectName()} item {i}"] = box.itemText(i)
    for i, row in enumerate(window.read_tab.rows()):
        out[f"row {i}"] = row
    scene = window.read_tab.preview.scene()
    for i, item in enumerate(scene.items()):
        if isinstance(item, QGraphicsSimpleTextItem):
            out[f"preview {i}"] = item.text()
    return out


def assert_all_marked(texts):
    unmarked = {where: t for where, t in texts.items() if t and MARK not in t}
    assert unmarked == {}


def test_choosing_a_language_rewords_the_whole_window(qtbot, stub, make_window):
    window = make_window()
    english = shown(window)
    assert all(MARK not in t for t in english.values())
    choose(window, stub)
    assert i18n.language() == stub
    texts = shown(window)
    assert_all_marked(texts)
    assert texts == shown(make_window())  # as if it had started in the language
    names = [a.text() for a in window.language_menu.actions() if a.data() is not None]
    assert names == list(i18n.languages().values())  # each in its own language


def test_no_message_box_and_the_choice_is_saved(qtbot, stub, make_window, monkeypatch):
    boxes = []
    monkeypatch.setattr(QMessageBox, "exec", lambda box: boxes.append(box.text()))
    window = make_window()
    choose(window, stub)
    assert boxes == []
    assert language.saved() == stub
    checked = [a.data() for a in window.language_menu.actions() if a.isChecked()]
    assert checked == [stub]
    choose(window, "en")
    assert language.saved() == "en" and i18n.language() == "en"
    checked = [a.data() for a in window.language_menu.actions() if a.isChecked()]
    assert checked == ["en"]


def test_switching_back_to_english_gives_the_original_texts(qtbot, stub, make_window):
    window = make_window()
    before = shown(window)
    choose(window, stub)
    assert shown(window) != before
    choose(window, "en")
    assert shown(window) == before


def test_system_language_entry_applies_the_system_language(
    qtbot, stub, make_window, monkeypatch
):
    monkeypatch.setattr(QLocale, "system", staticmethod(lambda: QLocale("it_IT")))
    language.save("en")
    i18n.set_language("en")
    window = make_window()
    assert MARK not in window.windowTitle() + window.tabs.tabText(0)
    choose(window, None)
    assert language.saved() is None and i18n.language() == stub
    assert_all_marked(shown(window))


# --- The read tab: rows, detail, caution, summary ------------------------------------


class Fakes:
    """``process`` by file name; a name in ``held`` reports a step and waits for ``gate``."""

    def __init__(self, scans):
        self.scans = scans
        self.calls = []
        self.held = set()
        self.gate = threading.Event()

    def process(self, path, cancelled=lambda: False, on_progress=None):
        name = os.path.basename(path)
        self.calls.append(name)
        if name in self.held:
            if on_progress is not None:
                on_progress(Progress(STEP_FIND, 0, 1, 0.1))
            self.gate.wait(TIMEOUT / 1000)
        work = self.scans[name]
        return work(path) if callable(work) else work


def identified(total, page, tag, data):
    info = ScanInfo(A_FMT, total, page, "doc", tag)
    return ScanWork(info, "", PageOutcome(data, (100, 0, 0, 0), 0), 0, None, SIZE)


def coarse():
    reason = text.Words(text.coarse_scan, 203.0, None, True)
    return ScanWork(None, reason, None, 0, None, SIZE, scan_dpi=203.0)


def idle(qtbot, controller):
    qtbot.waitUntil(lambda: controller.runner.active == 0, timeout=TIMEOUT)
    controller.refresh()
    qtbot.waitUntil(lambda: not controller.checking, timeout=TIMEOUT)
    controller.refresh()


def read_tab_texts(tab):
    return {
        "rows": tab.rows(),
        "detail": tab.detail.text(),
        "caution": tab.caution.text(),
        "summary": tab.summary.text(),
        "preview": tab.preview.message,
    }


def test_rows_details_and_summary_follow_the_language(qtbot, stub, make_window, tmp_path):
    folder = tmp_path / "folder.png"
    folder.mkdir()  # not a regular file, on every system
    fakes = Fakes({
        "p1.png": identified(2, 1, None, b"a" * 4),
        "coarse.png": coarse(),
        "pipe.png": lambda path: process_scan(str(folder)),  # the real reading
    })  # fmt: skip
    window = make_window(fakes.process)
    tab = window.read_tab
    names = ("p1.png", "coarse.png", "pipe.png")
    tab.controller.add_paths([str(tmp_path / name) for name in names])
    idle(qtbot, tab.controller)
    assert tab.controller.summary.state == DocState.INCOMPLETE  # page 2 is missing
    for key in ((Row.UNREADABLE, 2), (Row.UNREADABLE, 3), (Row.PAGE, 1)):
        tab._select(key)
    qtbot.waitUntil(lambda: bool(tab.preview.message), timeout=TIMEOUT)  # no such file
    english = read_tab_texts(tab)
    assert english["caution"] and len(english["rows"]) == 6
    choose(window, stub)
    texts = read_tab_texts(tab)
    assert tab._selected == (Row.PAGE, 1)
    for line in texts["rows"] + texts["detail"].splitlines():
        assert MARK in line, line
    assert MARK in texts["caution"] and MARK in texts["summary"]
    assert texts["preview"].startswith(text.preview_failed(""))
    for key in ((Row.UNREADABLE, 2), (Row.UNREADABLE, 3)):
        tab._select(key)
        assert MARK in tab.detail.text().splitlines()[1]
    tab._select((Row.PAGE, 1))
    # A view made now, in the language, shows the same.
    fresh = ReadTab(tab.controller)
    qtbot.addWidget(fresh)
    fresh._select((Row.PAGE, 1))
    qtbot.waitUntil(lambda: bool(fresh.preview.message), timeout=TIMEOUT)
    assert read_tab_texts(tab) == read_tab_texts(fresh)


def test_saved_note_and_check_failure_follow_the_language(
    qtbot, stub, make_window, tmp_path, monkeypatch
):
    fakes = Fakes({"p1.png": identified(1, 1, None, b"a" * 4)})
    window = make_window(fakes.process)
    tab = window.read_tab
    tab.controller.add_paths([str(tmp_path / "p1.png")])
    idle(qtbot, tab.controller)
    target = str(tmp_path / "doc.bin")
    tab.controller.save(target)
    qtbot.waitUntil(lambda: not tab.controller.saving, timeout=TIMEOUT)
    assert tab.summary.text().endswith(" — " + text.saved_message(target, 4))
    choose(window, stub)
    assert tab.summary.text().endswith(" — " + text.saved_message(target, 4))
    assert text.saved_message(target, 4).startswith(MARK)
    choose(window, "en")

    def broken(self, cancelled=lambda: False):
        raise RuntimeError("boom")

    monkeypatch.setattr(document_module.VerdictJob, "__call__", broken)
    data = b"b" * 4
    fakes.scans["t1.png"] = identified(1, 1, make_tag(data), data)
    other = make_window(fakes.process)
    other.read_tab.controller.add_paths([str(tmp_path / "t1.png")])
    idle(qtbot, other.read_tab.controller)
    assert other.read_tab.summary.text() == text.check_failed("RuntimeError: boom")
    choose(other, stub)
    assert other.read_tab.summary.text() == text.check_failed("RuntimeError: boom")
    assert other.read_tab.summary.text().startswith(MARK)


def test_switch_while_a_file_is_being_saved(
    qtbot, stub, make_window, tmp_path, monkeypatch
):
    fakes = Fakes({"p1.png": identified(1, 1, None, b"a" * 4)})
    window = make_window(fakes.process)
    tab = window.read_tab
    tab.controller.add_paths([str(tmp_path / "p1.png")])
    idle(qtbot, tab.controller)
    writes = []
    write_chunks = read_tab_module._write_chunks

    def counted(*args):
        writes.append(args[0])
        return write_chunks(*args)

    monkeypatch.setattr(read_tab_module, "_write_chunks", counted)
    gate, started = threading.Event(), threading.Event()

    def held():
        started.set()
        gate.wait(TIMEOUT / 1000)
        yield b"a" * 4

    finished = []
    tab.controller.save_finished.connect(lambda path, size: finished.append((path, size)))
    target = str(tmp_path / "doc.bin")
    tab.controller.save(target, held())
    qtbot.waitUntil(started.is_set, timeout=TIMEOUT)
    choose(window, stub)
    assert tab.controller.saving
    gate.set()
    qtbot.waitUntil(lambda: not tab.controller.saving, timeout=TIMEOUT)
    assert writes == [target] and finished == [(target, 4)]
    note = text.saved_message(target, 4)
    assert note.startswith(MARK) and tab.summary.text().endswith(" — " + note)
    with open(target, "rb") as f:
        assert f.read() == b"a" * 4


def test_switch_while_a_scan_is_being_read(qtbot, stub, make_window, tmp_path):
    fakes = Fakes({"x.png": ScanWork(None, LABEL_UNREADABLE, None, 0, None, SIZE)})
    fakes.held.add("x.png")
    window = make_window(fakes.process)
    tab = window.read_tab
    tab.controller.add_paths([str(tmp_path / "x.png")])
    english_row = text.being_read_row("x.png", Progress(STEP_FIND, 0, 1, 0.1))
    qtbot.waitUntil(lambda: english_row in tab.rows(), timeout=TIMEOUT)
    tab._select((Row.BEING_READ, 1))
    choose(window, stub)
    row = text.being_read_row("x.png", Progress(STEP_FIND, 0, 1, 0.1))
    assert MARK in row and row in tab.rows()
    assert all(MARK in line for line in tab.detail.text().splitlines()[1:])
    fakes.gate.set()
    idle(qtbot, tab.controller)
    assert fakes.calls == ["x.png"]  # not read again
    assert tab.rows()[-1] == f"x.png · {text.unreadable_reason(LABEL_UNREADABLE)}"
    assert MARK in tab.rows()[-1]


# --- The write tab -------------------------------------------------------------------


def test_write_tab_status_and_warnings_follow_the_language(
    qtbot, stub, make_window, tmp_path, monkeypatch
):
    window = make_window()
    tab = window.write_tab
    source = tmp_path / "data.bin"
    source.write_bytes(b"x" * 1000)
    tab._prepare = prepare_file
    pdfs = []

    def encode(src, dest, paper, name, cancelled, **choices):
        pdfs.append(dest)
        if len(pdfs) == 2:
            raise OptarError("disk full")
        return 3

    tab._encode = encode
    dest = str(tmp_path / "data.pdf")
    monkeypatch.setattr(tab, "ask_save_path", lambda suggested: dest)
    tab.set_file(str(source))
    qtbot.waitUntil(lambda: tab.prepared, timeout=TIMEOUT)
    tab.dots_box.setCurrentIndex(1)
    tab.protect_box.setCurrentIndex(2)
    dots, protect = tab.dots, tab.protect
    tab.name_edit.setText("файл")  # letters the label cannot print: a warning
    assert tab.warning.text()

    def created():
        return bool(pdfs) and not tab.creating

    tab.create_button.click()
    qtbot.waitUntil(created, timeout=TIMEOUT)
    assert tab.status.text() == text.created_message(dest, 3)
    choose(window, stub)
    assert tab.status.text() == text.created_message(dest, 3) and MARK in tab.status.text()
    assert MARK in tab.info.text() and MARK in tab.warning.text()
    assert (tab.dots, tab.protect) == (dots, protect)
    assert tab.name_edit.text() == "файл"
    assert_all_marked(shown(window))

    choose(window, "en")
    tab.create_button.click()  # fails
    qtbot.waitUntil(lambda: len(pdfs) == 2 and not tab.creating, timeout=TIMEOUT)
    assert tab.status.text() == text.create_failed("disk full")
    choose(window, stub)
    assert tab.status.text() == text.create_failed("disk full") and MARK in tab.status.text()

    choose(window, "en")
    missing = str(tmp_path / "gone.bin")
    tab.set_file(missing)  # cannot be read
    qtbot.waitUntil(lambda: tab.prepared, timeout=TIMEOUT)
    english = tab.status.text()
    assert english.startswith(text.file_unreadable(""))
    choose(window, stub)
    assert tab.status.text().startswith(text.file_unreadable("")) and MARK in tab.status.text()
    assert tab.status.text().count(MARK) == 2  # the library's own message too


# --- Facts kept instead of sentences -------------------------------------------------


def test_a_kept_library_error_words_itself_in_the_language(stub):
    e = error(OptarError, "err.no_pages", "no pages to write")
    words = text.Words.error(e)
    line = text.Words.error_line(ValueError("bad\nmore"))
    assert str(words) == "no pages to write" and str(line) == "ValueError: bad"
    i18n.set_language(stub)
    assert str(words) == MARK + "no pages to write"
    assert str(line) == "ValueError: bad"


def test_a_kept_list_of_formats_is_joined_in_the_stub_language(stub, tmp_path):
    path = tmp_path / "t.txt"
    path.write_text("hello")
    work = process_scan(str(path))
    english = str(work.reason)
    assert english.endswith(" PGM/PPM or JPEG image")
    i18n.set_language(stub)
    worded = str(work.reason)
    # Every part is the stub's: the sentence, the separators and the join.
    assert worded.startswith(MARK) and worded.count(MARK) == 1 + 3 + 1
    assert f"PNG{MARK}, TIFF" in worded and f"{MARK}PNG" in worded


def test_a_scan_that_is_not_a_regular_file_words_its_reason_when_shown(stub, tmp_path):
    folder = tmp_path / "folder.png"
    folder.mkdir()  # not a regular file, on every system
    work = process_scan(str(folder))
    english = text.unreadable_reason(work.reason)
    assert english == text.not_regular_file(str(folder))
    i18n.set_language(stub)
    assert text.unreadable_reason(work.reason) == MARK + english


def test_the_reason_codes_are_the_library_constants_and_each_is_worded():
    import optar.identify

    assert document_module.NO_PAGE == optar.identify.NO_PAGE
    assert document_module.LABEL_UNREADABLE == optar.identify.LABEL_UNREADABLE
    for code in (
        document_module.NO_PAGE,
        document_module.LABEL_UNREADABLE,
        document_module.NOT_DECODABLE,
        document_module.SIZE_MISMATCH,
    ):
        assert text._reason_key(code) is not None


def test_kept_words_are_not_hashed_and_a_kept_error_names_itself():
    words = text.Words(text.not_regular_file, "x")
    with pytest.raises(TypeError):
        hash(words)
    kept = text._KeptError(error(OptarError, "err.no_pages", "no pages to write"))
    assert repr(kept) == "_KeptError('OptarError', 'err.no_pages', 'no pages to write')"


def test_a_failed_repair_words_its_library_error_in_the_language(stub):
    e = error(OptarError, "err.no_pages", "no pages to write")
    s = document_module.Summary(DocState.INCOMPLETE, 2, 0, 0, 0, 1, 9, protection=32,
                                repair_error=text.Words.error_line(e))
    english = text.summary_line(s)
    assert english == text.repair_failed("no pages to write")
    i18n.set_language(stub)
    assert text.summary_line(s) == text.repair_failed(MARK + "no pages to write")
