# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Replacing a page's scan, spares, other documents and working by hand, off-screen.

The scans are written once per module and every test runs them through
``cached_process`` and ``cached_unlabelled``: the real ``process_scan`` and
``process_unlabelled``, with each result remembered by the file's contents (and
the format), so a scan is decoded once however many tests add it.
"""

import hashlib
import os
import shutil
import threading

import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMessageBox, QPushButton

from optar import PAPERS, PageFormat, encode
from optar.tag import Tag, make_tag, tagged_label
from optar_gui import text
from optar_gui.dialogs import AssignPageDialog, StartByHandDialog
from optar_gui.document import (
    MAX_TOTAL_PAGES,
    DocState,
    Health,
    PageOutcome,
    PageSlot,
    ScanInfo,
    ScanState,
)
from optar_gui.read_tab import ReadController, ReadTab
from optar_gui.work import (
    NOT_DECODABLE,
    STEP_FIND,
    Cancelled,
    Progress,
    ScanWork,
    process_scan,
    process_unlabelled,
)
from tests.helpers import fake_scan, save_scan, seeded_bytes

TIMEOUT = 300_000  # ms: decoding is slow on a loaded machine
A4 = PageFormat.for_paper(PAPERS["a4"])
LETTER = PageFormat.for_paper(PAPERS["letter"])
BUTTONS = ("replaceButton", "useSpareButton", "switchButton", "assignButton",
           "startByHandButton", "removeButton")  # fmt: skip

_RESULTS = {}
_RESULTS_LOCK = threading.Lock()


def _remembered(key, compute):
    with _RESULTS_LOCK:
        if key in _RESULTS:
            return _RESULTS[key]
    work = compute()
    with _RESULTS_LOCK:
        _RESULTS[key] = work
    return work


def _contents(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def cached_process(path, cancelled=lambda: False, on_progress=None):
    """``process_scan``, remembering each result by the file's contents."""
    return _remembered(
        ("scan", _contents(path)), lambda: process_scan(path, cancelled, on_progress=on_progress)
    )


def cached_unlabelled(path, format, cancelled=lambda: False):
    """``process_unlabelled``, remembering each result by the contents and format."""
    return _remembered(
        ("unlabelled", _contents(path), format),
        lambda: process_unlabelled(path, format, cancelled),
    )


def _blacken_label(pixels):
    out = np.array(pixels, copy=True)
    top = A4.border + A4.data_height
    out[top : top + A4.text_height, A4.border : A4.width - A4.border] = 0
    return out


@pytest.fixture(scope="module")
def scans(tmp_path_factory):
    """The scans as PNG files, by name, and the two-page file they hold."""
    root = tmp_path_factory.mktemp("scans")
    data = seeded_bytes(1, 250_000)  # two A4 pages
    tag = make_tag(data)
    # One fingerprint digit read wrongly, with the check that fits the wrong reading
    # (the misread the check lets through about once in 256).
    misread = Tag(tag.size, ("1" if tag.fingerprint[0] == "0" else "0") + tag.fingerprint[1:])

    p1, p2 = (
        page.pixels for page in encode(data, A4, lambda p, t: tagged_label(tag, "doc.tar", p, t))
    )
    _, wrong = (
        page.pixels
        for page in encode(data, A4, lambda p, t: tagged_label(misread, "doc.tar", p, t))
    )
    other = seeded_bytes(4, 1000)
    (o1,) = (
        page.pixels
        for page in encode(other, A4, lambda p, t: tagged_label(make_tag(other), "other.tar", p, t))
    )
    letter = seeded_bytes(5, 1000)
    (l1,) = (
        page.pixels
        for page in encode(
            letter, LETTER, lambda p, t: tagged_label(make_tag(letter), "letter.tar", p, t)
        )
    )
    images = {
        "letter.png": fake_scan(l1, scale=1),
        "page-1.png": fake_scan(p1, scale=1),
        "page-2.png": fake_scan(p2, scale=1),
        "page-2-damaged.png": fake_scan(p2, scale=1, flips=40_000, fmt=A4, seed=5),
        "page-2-misread.png": fake_scan(wrong, scale=1),
        "page-1-no-label.png": fake_scan(_blacken_label(p1), scale=1),
        "page-2-no-label-upside-down.png": np.rot90(fake_scan(_blacken_label(p2), scale=1), 2),
        "other.png": fake_scan(o1, scale=1),
    }
    paths = {}
    for name, image in images.items():
        save_scan(root / name, image)
        paths[name] = str(root / name)
    return data, paths


@pytest.fixture
def make_tab(qtbot):
    """make_tab(process=..., unlabelled=..., **controller_kw) -> ReadTab with its own
    controller, decoding through the caches by default."""
    controllers = []

    def make(process=cached_process, unlabelled=cached_unlabelled, **kw):
        controller = ReadController(process=process, unlabelled=unlabelled, **kw)
        controllers.append(controller)
        tab = ReadTab(controller)
        qtbot.addWidget(tab)
        tab.show_notice = lambda message: pytest.fail(f"unexpected notice: {message}")
        tab.show_error = lambda message: pytest.fail(f"unexpected error: {message}")
        return tab

    yield make
    for controller in controllers:
        controller.shutdown(TIMEOUT)


def wait_settled(qtbot, tab):
    """Waits for every scan to be read, then for the fingerprint check."""
    controller = tab.controller

    def done():
        busy = any(s.state in (ScanState.WAITING, ScanState.WORKING)
                   for s in controller.document.scans())
        return not busy and controller.runner.active == 0

    qtbot.waitUntil(done, timeout=TIMEOUT)
    controller.refresh()
    qtbot.waitUntil(lambda: not controller.checking, timeout=TIMEOUT)
    controller.refresh()


def select(tab, label):
    tab.select_row(tab.rows().index(label))


def enabled(tab):
    return {name for name in BUTTONS if tab.findChild(QPushButton, name).isEnabled()}


def scan_id(tab, path):
    return tab.controller.document.scan_id_of(path)


def click(tab, name):
    tab.findChild(QPushButton, name).click()


# --- Replacing a page's scan ---------------------------------------------------------


def test_replace_with_a_better_scan_of_the_same_page(qtbot, make_tab, scans):
    data, paths = scans
    tab = make_tab()
    tab.controller.add_paths([paths["page-1.png"], paths["page-2-damaged.png"]])
    wait_settled(qtbot, tab)
    damaged = tab.rows()[2]
    assert damaged.startswith("Page 2 · Damaged · ") and damaged.endswith(" lost")
    asked = []
    tab.ask_replace_path = lambda page: asked.append(page) or paths["page-2.png"]
    select(tab, damaged)
    click(tab, "replaceButton")
    assert asked == [2]
    wait_settled(qtbot, tab)
    doc = tab.controller.document
    clean, spare = scan_id(tab, paths["page-2.png"]), scan_id(tab, paths["page-2-damaged.png"])
    assert (doc.pages()[1].scan_id, doc.pages()[1].spare_ids) == (clean, (spare,))
    assert tab.rows()[2] == "Page 2 · Good"
    assert tab.rows()[3] == f"    Spare · page-2-damaged.png · {damaged[len('Page 2 · '):]}"
    assert tab.controller.summary.state == DocState.VERIFIED
    # The page stays selected and the preview follows the scan now in use.
    assert tab.detail.text().startswith("Page 2 of 2 · page-2.png\n")
    assert tab.preview.path == paths["page-2.png"]

    # The user's choice wins over the ranking: replacing with the worse scan, which
    # is already added, puts it in use.
    tab.ask_replace_path = lambda page: paths["page-2-damaged.png"]
    click(tab, "replaceButton")
    assert doc.pages()[1].scan_id == spare
    assert tab.rows()[2] == damaged
    assert tab.preview.path == paths["page-2-damaged.png"]
    assert len(doc.scans()) == 3


def test_replace_with_the_wrong_page_is_rejected(qtbot, make_tab, scans):
    _, paths = scans
    tab = make_tab()
    tab.controller.add_paths([paths["page-1.png"], paths["page-2-damaged.png"]])
    wait_settled(qtbot, tab)
    doc = tab.controller.document
    in_use = doc.pages()[1].scan_id
    rows = tab.rows()
    notices = []
    tab.show_notice = notices.append
    select(tab, rows[2])
    tab.ask_replace_path = lambda page: paths["other.png"]
    click(tab, "replaceButton")
    qtbot.waitUntil(lambda: notices != [], timeout=TIMEOUT)
    assert notices == [
        "other.png was not used for page 2: it is page 1 of another printout, "
        "other.tar · A4 · 1 page."
    ]
    wait_settled(qtbot, tab)
    assert doc.pages()[1].scan_id == in_use
    assert tab.rows() == rows + [text.NOT_PART_OF_THIS_FILE, "other.tar · A4 · 1 page · 1 scan"]

    # Another page of this document, already added: told at once.
    tab.ask_replace_path = lambda page: paths["page-1.png"]
    click(tab, "replaceButton")
    assert notices[1] == (
        "page-1.png was not used for page 2: it is page 1 of this document and is listed there."
    )
    # A scan whose label cannot be read, made at fake_scan's scale 1 (200 dpi):
    # too coarse for Standard dots, so that is the reason given.
    tab.ask_replace_path = lambda page: paths["page-1-no-label.png"]
    click(tab, "replaceButton")
    qtbot.waitUntil(lambda: len(notices) == 3, timeout=TIMEOUT)
    assert notices[2] == (
        "page-1-no-label.png was not used for page 2. Scanned at about 200 dpi, which "
        "is too coarse to read. Scan at 600 dpi for Standard dots, 450 Medium, 360 Big, "
        "300 Large, 200 Extra large. The slower reader for coarse scans was tried too, "
        "and could not read it."
    )
    assert doc.pages()[1].scan_id == in_use
    assert doc.pages()[0].scan_id == scan_id(tab, paths["page-1.png"])
    # Cancelling the file dialog does nothing.
    tab.ask_replace_path = lambda page: None
    click(tab, "replaceButton")
    assert len(doc.scans()) == 4 and len(notices) == 3


def held_back(gate, slow):
    """A ``process`` that reads ``slow`` only once ``gate`` is set; others at once."""
    slow = os.path.realpath(slow)

    def process(path, cancelled=lambda: False, on_progress=None):
        if os.path.realpath(path) == slow:
            gate.wait(TIMEOUT / 1000)
        return cached_process(path, cancelled)

    return process


def test_the_latest_replacement_wins_whichever_is_read_first(qtbot, make_tab, scans, tmp_path):
    _, paths = scans
    slow = str(tmp_path / "slow-page-2.png")
    shutil.copy(paths["page-2.png"], slow)  # a better scan than the damaged one
    gate = threading.Event()
    tab = make_tab(process=held_back(gate, slow), max_workers=3)
    try:
        tab.controller.add_paths([paths["page-1.png"]])
        wait_settled(qtbot, tab)
        select(tab, "Page 2 · Missing")
        tab.ask_replace_path = lambda page: slow
        click(tab, "replaceButton")
        tab.ask_replace_path = lambda page: paths["page-2-damaged.png"]
        click(tab, "replaceButton")
        doc = tab.controller.document
        damaged = scan_id(tab, paths["page-2-damaged.png"])
        qtbot.waitUntil(lambda: doc.pages()[1].scan_id == damaged, timeout=TIMEOUT)
    finally:
        gate.set()
    wait_settled(qtbot, tab)
    # The earlier choice, read last, stays added as a spare, with no notice.
    assert doc.pages()[1].scan_id == damaged
    assert doc.pages()[1].spare_ids == (scan_id(tab, slow),)


def test_use_spare_after_a_replacement_in_flight(qtbot, make_tab, scans, tmp_path):
    _, paths = scans
    slow = str(tmp_path / "slow-page-2.png")
    shutil.copy(paths["page-2.png"], slow)
    gate = threading.Event()
    tab = make_tab(process=held_back(gate, slow), max_workers=3)
    try:
        tab.controller.add_paths(
            [paths["page-1.png"], paths["page-2.png"], paths["page-2-damaged.png"]]
        )
        wait_settled(qtbot, tab)
        select(tab, "Page 2 · Good")
        tab.ask_replace_path = lambda page: slow
        click(tab, "replaceButton")
        select(tab, next(r for r in tab.rows() if "page-2-damaged.png" in r))
        click(tab, "useSpareButton")
    finally:
        gate.set()
    wait_settled(qtbot, tab)
    doc = tab.controller.document
    assert doc.pages()[1].scan_id == scan_id(tab, paths["page-2-damaged.png"])


def test_switching_document_drops_a_replacement_in_flight(qtbot, make_tab, scans, tmp_path):
    _, paths = scans
    slow = str(tmp_path / "slow-page-2.png")
    shutil.copy(paths["page-2.png"], slow)
    gate = threading.Event()
    tab = make_tab(process=held_back(gate, slow), max_workers=3)
    try:
        tab.controller.add_paths([paths["page-1.png"], paths["other.png"]])
        wait_settled(qtbot, tab)
        select(tab, "Page 2 · Missing")
        tab.ask_replace_path = lambda page: slow
        click(tab, "replaceButton")
        select(tab, "other.tar · A4 · 1 page · 1 scan")
        click(tab, "switchButton")
    finally:
        gate.set()
    wait_settled(qtbot, tab)  # no notice about page 2 of a document the user left
    assert tab.rows()[0] == "other.tar · A4 · 1 page"
    assert tab.rows()[-1] == "doc.tar · A4 · 2 pages · 2 scans"


# --- Spares and other documents --------------------------------------------------------


def test_use_spare_switches_the_scan_in_use(qtbot, make_tab, scans):
    _, paths = scans
    tab = make_tab()
    tab.controller.add_paths(
        [paths["page-1.png"], paths["page-2.png"], paths["page-2-damaged.png"]]
    )
    wait_settled(qtbot, tab)
    rows = tab.rows()
    assert rows[2] == "Page 2 · Good"
    assert rows[3].startswith("    Spare · page-2-damaged.png · Damaged · ")
    select(tab, rows[3])
    assert tab.detail.text().splitlines()[0] == "Page 2 of 2 · page-2-damaged.png · spare"
    assert tab.preview.path == paths["page-2-damaged.png"]
    assert enabled(tab) == {"useSpareButton", "removeButton"}
    click(tab, "useSpareButton")
    doc = tab.controller.document
    assert doc.pages()[1].scan_id == scan_id(tab, paths["page-2-damaged.png"])
    assert tab.rows()[2].startswith("Page 2 · Damaged · ")
    assert tab.rows()[3] == "    Spare · page-2.png · Good"
    # The page is selected and the preview shows its new scan.
    assert [i.row() for i in tab.page_list.selectionModel().selectedIndexes()] == [2]
    assert tab.detail.text().startswith("Page 2 of 2 · page-2-damaged.png\n")
    assert tab.preview.path == paths["page-2-damaged.png"]
    assert tab.controller.summary.state == DocState.INCOMPLETE
    assert tab.summary.text() == "1 of 2 pages good · 1 damaged"


def test_switch_to_other_document(qtbot, make_tab, scans):
    _, paths = scans
    tab = make_tab()
    tab.controller.add_paths([paths["page-1.png"], paths["other.png"]])
    wait_settled(qtbot, tab)
    assert tab.rows()[0] == "doc.tar · A4 · 2 pages"
    select(tab, "other.tar · A4 · 1 page · 1 scan")
    assert "switchButton" in enabled(tab)
    click(tab, "switchButton")
    wait_settled(qtbot, tab)
    assert tab.rows() == [
        "other.tar · A4 · 1 page",
        "Page 1 · Good",
        text.NOT_PART_OF_THIS_FILE,
        "doc.tar · A4 · 2 pages · 1 scan",
    ]
    assert tab.controller.summary.state == DocState.VERIFIED
    assert tab.summary.text() == "File recovered and verified · 1,000 bytes"


# --- Assigning by hand -----------------------------------------------------------------


def test_tag_misread_scan_can_be_assigned_and_document_verifies(qtbot, make_tab, scans):
    data, paths = scans
    tab = make_tab()
    tab.controller.add_paths([paths["page-1.png"], paths["page-2-misread.png"]])
    wait_settled(qtbot, tab)
    assert tab.rows() == [
        "doc.tar · A4 · 2 pages",
        "Page 1 · Good",
        "Page 2 · Missing",
        text.NOT_PART_OF_THIS_FILE,
        "doc.tar · A4 · 2 pages · 1 scan",
    ]
    select(tab, "doc.tar · A4 · 2 pages · 1 scan")
    assert enabled(tab) == {"switchButton", "assignButton"}
    asked = []
    tab.ask_page = lambda total, suggested, name: asked.append((total, suggested, name)) or 2
    click(tab, "assignButton")
    assert asked == [(2, 2, "page-2-misread.png")]  # its own label says page 2
    wait_settled(qtbot, tab)
    assert tab.rows() == ["doc.tar · A4 · 2 pages", "Page 1 · Good", "Page 2 · Good"]
    assert tab.controller.summary.state == DocState.VERIFIED
    assert tab.summary.text() == f"File recovered and verified · {len(data):,} bytes"
    assert tab.preview.path == paths["page-2-misread.png"]


def test_assign_unreadable_scan_decodes_it_in_the_best_rotation(qtbot, make_tab, scans):
    data, paths = scans
    upside_down = paths["page-2-no-label-upside-down.png"]
    tab = make_tab()
    tab.controller.add_paths([paths["page-1.png"], upside_down])
    wait_settled(qtbot, tab)
    row = (  # fake_scan's scale 1 is 200 dpi: too coarse, which is the reason given
        "page-2-no-label-upside-down.png · Scanned at about 200 dpi, which is too coarse "
        "to read. Scan at 600 dpi for Standard dots, 450 Medium, 360 Big, 300 Large, "
        "200 Extra large. The slower reader for coarse scans was tried too, and could "
        "not read it."
    )
    assert tab.rows()[2:] == ["Page 2 · Missing", text.NOT_READABLE, row]
    select(tab, row)
    assert enabled(tab) == {"assignButton", "removeButton"}
    tab.ask_page = lambda total, suggested, name: suggested  # the first missing page
    click(tab, "assignButton")
    assert tab.rows()[2] == "Page 2 · Working…"
    wait_settled(qtbot, tab)
    assert tab.rows() == ["doc.tar · A4 · 2 pages", "Page 1 · Good", "Page 2 · Good"]
    assert tab.controller.summary.state == DocState.VERIFIED
    work = tab.controller.work_for(scan_id(tab, upside_down), A4.to_string())
    assert work.rotation == 2 and work.info is None
    assert tab.preview.path == upside_down
    assert tab.detail.text().startswith("Page 2 of 2 · page-2-no-label-upside-down.png\n")


def test_assigning_a_scan_of_the_other_paper_decodes_it_in_this_format(qtbot, make_tab, scans):
    _, paths = scans
    calls = []

    def recording(path, format, cancelled=lambda: False):
        calls.append((path, format))
        return cached_unlabelled(path, format, cancelled)

    tab = make_tab(unlabelled=recording)
    tab.controller.add_paths([paths["page-1.png"], paths["letter.png"]])
    wait_settled(qtbot, tab)
    select(tab, "letter.tar · US Letter · 1 page · 1 scan")
    tab.ask_page = lambda total, suggested, name: 2
    click(tab, "assignButton")
    wait_settled(qtbot, tab)
    assert calls == [(paths["letter.png"], A4.to_string())]
    assert tab.rows()[2] == "Page 2 · Not readable"  # never the Letter page's data
    doc = tab.controller.document
    page = doc.page_bytes
    assert page == doc.scan(scan_id(tab, paths["page-1.png"])).outcome.bytes
    saved = b"".join(tab.controller.snapshot())
    assert saved[page:] == bytes(len(saved) - page)


def test_replace_on_a_page_of_a_document_started_by_hand(qtbot, make_tab, scans):
    data, paths = scans
    tab = make_tab()
    tab.controller.add_paths([paths["page-1-no-label.png"]])
    wait_settled(qtbot, tab)
    tab.ask_start_by_hand = lambda paper: ("a4", 2)
    click(tab, "startByHandButton")
    select(tab, "Page 2 · Missing")
    assert "replaceButton" in enabled(tab)
    upside_down = paths["page-2-no-label-upside-down.png"]
    tab.ask_replace_path = lambda page: upside_down  # its label cannot be read
    click(tab, "replaceButton")
    wait_settled(qtbot, tab)
    doc = tab.controller.document
    assert doc.pages()[1].scan_id == scan_id(tab, upside_down)
    assert tab.rows()[2] == "Page 2 · Good"
    assert tab.controller.work_for(scan_id(tab, upside_down), A4.to_string()).rotation == 2


def test_names_from_scans_are_shown_as_plain_text(qtbot, make_tab, monkeypatch):
    shown = []

    def fake_exec(box):
        shown.append((box.textFormat(), box.text()))
        return 0

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    tab = make_tab()
    name = "<b>x</b>.png"
    ReadTab.show_notice(tab, f"{name} was not used for page 2")
    ReadTab.show_error(tab, f"cannot write /tmp/{name}")
    assert not ReadTab.confirm(tab, f"{name} is damaged")
    assert shown == [
        (Qt.TextFormat.PlainText, f"{name} was not used for page 2"),
        (Qt.TextFormat.PlainText, f"cannot write /tmp/{name}"),
        (Qt.TextFormat.PlainText, f"{name} is damaged"),
    ]
    dialog = AssignPageDialog(2, 1, name)
    qtbot.addWidget(dialog)
    (label,) = [w for w in dialog.findChildren(QLabel) if name in w.text()]
    assert label.textFormat() == Qt.TextFormat.PlainText
    assert label.text() == text.assign_prompt(name)


def test_start_by_hand_when_nothing_is_identified(qtbot, make_tab, scans):
    data, paths = scans
    first, second = paths["page-1-no-label.png"], paths["page-2-no-label-upside-down.png"]
    tab = make_tab()
    tab.controller.add_paths([second, first])
    wait_settled(qtbot, tab)
    assert tab.rows()[0] == text.NOT_READABLE and len(tab.rows()) == 3
    assert enabled(tab) == {"startByHandButton"}
    select(tab, tab.rows()[2])
    assert enabled(tab) == {"startByHandButton", "removeButton"}  # no document to assign to
    suggested = []
    tab.ask_start_by_hand = lambda paper: suggested.append(paper) or ("a4", 2)
    click(tab, "startByHandButton")
    assert suggested == ["a4"]
    assert tab.rows()[:3] == ["(no name) · A4 · 2 pages", "Page 1 · Missing", "Page 2 · Missing"]
    assert tab.caution.text() == text.by_hand_caution()
    assert "startByHandButton" not in enabled(tab)
    for path, page in ((second, 2), (first, 1)):
        select(tab, next(r for r in tab.rows() if r.startswith(os.path.basename(path))))
        tab.ask_page = lambda total, suggested, name, page=page: page
        click(tab, "assignButton")
    wait_settled(qtbot, tab)
    assert tab.rows() == ["(no name) · A4 · 2 pages", "Page 1 · Good", "Page 2 · Good"]
    assert tab.controller.summary.state == DocState.UNVERIFIABLE
    assert tab.summary.text() == "All 2 pages read · cannot be verified (no tag)"
    saved = b"".join(tab.controller.snapshot())
    assert saved[: len(data)] == data and not saved[len(data):].strip(b"\0")


# --- Which buttons apply ---------------------------------------------------------------


def test_buttons_enable_only_when_applicable(qtbot, make_tab, scans, tmp_path):
    _, paths = scans
    tab = make_tab()
    assert enabled(tab) == set()
    tab.controller.add_paths([
        paths["page-1.png"], paths["page-2.png"], paths["page-2-damaged.png"],
        paths["other.png"], paths["page-1-no-label.png"],
    ])
    wait_settled(qtbot, tab)
    rows = tab.rows()
    expected = {
        "doc.tar · A4 · 2 pages": set(),
        "Page 1 · Good": {"replaceButton", "removeButton"},
        rows[3]: {"useSpareButton", "removeButton"},  # the spare of page 2
        text.NOT_PART_OF_THIS_FILE: set(),
        "other.tar · A4 · 1 page · 1 scan": {"switchButton", "assignButton"},
        text.NOT_READABLE: set(),
        rows[-1]: {"assignButton", "removeButton"},  # the unreadable scan
    }
    for label, want in expected.items():
        select(tab, label)
        assert enabled(tab) == want, label
    # A missing page can be given a scan but has none to remove.
    select(tab, "Page 1 · Good")
    click(tab, "removeButton")
    assert tab.rows()[1] == "Page 1 · Missing"
    assert enabled(tab) == {"replaceButton"}
    # A group of several scans is switched to, not assigned to one page.
    shutil.copy(paths["other.png"], tmp_path / "other-again.png")
    tab.controller.add_paths([str(tmp_path / "other-again.png")])
    wait_settled(qtbot, tab)
    select(tab, "other.tar · A4 · 1 page · 2 scans")
    assert enabled(tab) == {"switchButton"}


# --- Decoding for a document, with work that reads no image ---------------------------

A_FMT, L_FMT = A4.to_string(), LETTER.to_string()
SIZE = (100, 141)


def unreadable_work():
    return ScanWork(None, "label unreadable", None, 0, None, SIZE)


def identified_work(fmt, total, page, name, tag, data, lost=0):
    info = ScanInfo(fmt, total, page, name, tag)
    return ScanWork(info, "", PageOutcome(data, (100, 0, 0, 0), lost), 0, None, SIZE)


def decoded_work(data, lost=0):
    return ScanWork(None, "", PageOutcome(data, (100, 0, 0, 0), lost), 0, None, SIZE)


def failed_work():
    return ScanWork(None, NOT_DECODABLE, None, 0, None, SIZE)


class Fakes:
    """``process`` and ``unlabelled`` by file name; names in ``held`` wait for ``gate``."""

    def __init__(self, scans, decodes):
        self.scans = scans  # name -> ScanWork
        self.decodes = decodes  # (name, format) -> ScanWork
        self.calls = []  # (name, format) of every decode without the label
        self.held = set()
        self.gate = threading.Event()

    def _hold(self, name):
        if name in self.held:
            self.gate.wait(TIMEOUT / 1000)

    def process(self, path, cancelled=lambda: False, on_progress=None):
        name = os.path.basename(path)
        self._hold(name)
        return self.scans[name]

    def unlabelled(self, path, format, cancelled=lambda: False):
        name = os.path.basename(path)
        self.calls.append((name, format))
        self._hold(name)
        return self.decodes[(name, format)]


@pytest.fixture
def fake_controller(qtbot):
    """fake_controller(fakes, max_workers=3) -> (controller, notices)."""
    made = []

    def make(fakes, max_workers=3):
        controller = ReadController(
            process=fakes.process, unlabelled=fakes.unlabelled, max_workers=max_workers
        )
        notices = []
        controller.replace_rejected.connect(notices.append)
        made.append((controller, fakes))
        return controller, notices

    yield make
    for controller, fakes in made:
        fakes.gate.set()
        controller.shutdown(TIMEOUT)


def idle(qtbot, controller):
    qtbot.waitUntil(lambda: controller.runner.active == 0, timeout=TIMEOUT)
    controller.refresh()
    qtbot.waitUntil(lambda: not controller.checking, timeout=TIMEOUT)
    controller.refresh()


def by_hand_with_damaged_page_1(qtbot, make, fakes, max_workers=3):
    """A document by hand whose page 1 is damaged.png, decoded without its label."""
    controller, notices = make(fakes, max_workers)
    controller.add_paths([f"/x/{name}" for name in fakes.scans if name not in fakes.held])
    idle(qtbot, controller)
    controller.start_by_hand("a4", 2)
    doc = controller.document
    dmg = doc.scan_id_of("/x/damaged.png")
    assert controller.assign(dmg, 1)
    idle(qtbot, controller)
    assert (doc.pages()[0].scan_id, doc.pages()[0].health) == (dmg, Health.DAMAGED)
    return controller, notices, dmg


def test_replace_by_hand_with_a_scan_whose_decode_fails_keeps_the_page(qtbot, fake_controller):
    fakes = Fakes(
        {"damaged.png": unreadable_work(),
         "letter.png": identified_work(L_FMT, 1, 1, "let", make_tag(b"L" * 5), b"L" * 5)},
        {("damaged.png", A_FMT): decoded_work(b"d" * 10, lost=5),
         ("letter.png", A_FMT): failed_work()},
    )  # fmt: skip
    controller, notices, dmg = by_hand_with_damaged_page_1(qtbot, fake_controller, fakes)
    doc = controller.document
    controller.replace(1, "/x/letter.png")
    assert notices == []  # nothing is judged before the decode in A4 has reported
    assert doc.pages()[0].scan_id == dmg  # ranked by its A4 page, which it has not
    idle(qtbot, controller)
    letter = doc.scan_id_of("/x/letter.png")
    assert (doc.pages()[0].scan_id, doc.pages()[0].health) == (dmg, Health.DAMAGED)
    assert doc.pages()[0].spare_ids == (letter,)
    assert notices == [
        "letter.png was not used for page 1: it could not be read "
        f"({NOT_DECODABLE}), so page 1 keeps the scan it has."
    ]
    assert fakes.calls[-1] == ("letter.png", A_FMT)


def test_replace_by_hand_with_an_added_file_while_every_worker_is_busy(qtbot, fake_controller):
    fakes = Fakes(
        {"damaged.png": unreadable_work(), "good.png": unreadable_work(),
         "slow.png": unreadable_work()},
        {("damaged.png", A_FMT): decoded_work(b"d" * 10, lost=5),
         ("good.png", A_FMT): decoded_work(b"g" * 10)},
    )  # fmt: skip
    fakes.held.add("slow.png")
    controller, notices, dmg = by_hand_with_damaged_page_1(qtbot, fake_controller, fakes, 1)
    doc = controller.document
    controller.add_paths(["/x/slow.png"])  # takes the only worker
    controller.replace(1, "/x/good.png")
    good = doc.scan_id_of("/x/good.png")
    assert notices == []
    assert doc.scan(good).state == ScanState.WORKING  # queued counts as being read
    assert doc.pages()[0].scan_id == dmg
    fakes.gate.set()
    idle(qtbot, controller)
    assert (doc.pages()[0].scan_id, doc.pages()[0].health) == (good, Health.GOOD)
    assert notices == []


def test_assign_with_a_failing_decode_keeps_the_pages_usable_scan(qtbot, fake_controller):
    fakes = Fakes(
        {"damaged.png": unreadable_work(),
         "letter.png": identified_work(L_FMT, 1, 1, "let", make_tag(b"L" * 5), b"L" * 5)},
        {("damaged.png", A_FMT): decoded_work(b"d" * 10, lost=5),
         ("letter.png", A_FMT): failed_work()},
    )  # fmt: skip
    controller, notices, dmg = by_hand_with_damaged_page_1(qtbot, fake_controller, fakes)
    doc = controller.document
    letter = doc.scan_id_of("/x/letter.png")
    assert controller.assign(letter, 1)
    assert doc.pages()[0].scan_id == dmg
    idle(qtbot, controller)
    assert doc.slots()[0] == PageSlot(1, dmg, (letter,))
    assert doc.pages()[0].health == Health.DAMAGED
    assert notices == []


def test_a_queued_decode_shows_the_page_working(qtbot, fake_controller):
    fakes = Fakes(
        {"bad.png": unreadable_work(), "slow.png": unreadable_work()},
        {("bad.png", A_FMT): decoded_work(b"b" * 10)},
    )
    fakes.held.add("slow.png")
    controller, _ = fake_controller(fakes, max_workers=1)
    tab = ReadTab(controller)
    qtbot.addWidget(tab)
    controller.add_paths(["/x/bad.png"])
    idle(qtbot, controller)
    controller.add_paths(["/x/slow.png"])  # takes the only worker
    controller.start_by_hand("a4", 1)
    assert controller.assign(controller.document.scan_id_of("/x/bad.png"), 1)
    assert controller.document.pages()[0].health == Health.WORKING
    assert controller.summary.state == DocState.WORKING
    assert tab.rows()[1] == "Page 1 · Working…"
    fakes.gate.set()
    idle(qtbot, controller)
    assert tab.rows()[1] == "Page 1 · Good"


@pytest.mark.parametrize("decode_succeeds", [False, True])
def test_a_letter_scan_assigned_by_mistake_keeps_its_own_page(
    qtbot, fake_controller, decode_succeeds
):
    a_data, l_data = b"a" * 4 + b"b" * 4, b"L" * 5 + b"M" * 5
    a_tag, l_tag = make_tag(a_data), make_tag(l_data)
    fakes = Fakes(
        {"a1.png": identified_work(A_FMT, 2, 1, "doc", a_tag, a_data[:4]),
         "a2.png": identified_work(A_FMT, 2, 2, "doc", a_tag, a_data[4:]),
         "l1.png": identified_work(L_FMT, 2, 1, "let", l_tag, l_data[:5]),
         "l2.png": identified_work(L_FMT, 2, 2, "let", l_tag, l_data[5:])},
        {("l1.png", A_FMT): decoded_work(b"z" * 4, lost=9) if decode_succeeds
         else failed_work()},
    )  # fmt: skip
    controller, notices = fake_controller(fakes)
    controller.add_paths([f"/x/{n}" for n in ("a1.png", "a2.png", "l1.png", "l2.png")])
    idle(qtbot, controller)
    doc = controller.document
    assert controller.summary.state == DocState.VERIFIED
    a2, l1 = doc.scan_id_of("/x/a2.png"), doc.scan_id_of("/x/l1.png")
    assert controller.assign(l1, 2)  # by mistake
    idle(qtbot, controller)
    assert doc.slots()[1] == PageSlot(2, a2, (l1,))
    assert controller.summary.state == DocState.VERIFIED
    controller.switch_document(doc.others()[0].key)
    idle(qtbot, controller)
    assert doc.current.format == L_FMT
    assert [p.health for p in doc.pages()] == [Health.GOOD, Health.GOOD]
    assert controller.summary.state == DocState.VERIFIED
    assert b"".join(controller.snapshot()) == l_data
    assert fakes.calls == [("l1.png", A_FMT)]  # nothing decoded again back home
    assert notices == []


def test_rejection_names_the_page_a_scan_assigned_by_hand_is_on(qtbot, fake_controller):
    a_data = b"a" * 4 + b"b" * 4
    fakes = Fakes(
        {"a1.png": identified_work(A_FMT, 2, 1, "doc", make_tag(a_data), a_data[:4]),
         "bad.png": unreadable_work()},
        {("bad.png", A_FMT): decoded_work(a_data[4:])},
    )  # fmt: skip
    controller, notices = fake_controller(fakes)
    controller.add_paths(["/x/a1.png", "/x/bad.png"])
    idle(qtbot, controller)
    assert controller.assign(controller.document.scan_id_of("/x/bad.png"), 2)
    idle(qtbot, controller)
    controller.replace(1, "/x/bad.png")
    assert notices == [
        "bad.png was not used for page 1: it is page 2 of this document and is listed there."
    ]


def test_choosing_one_new_file_for_two_pages_by_hand_keeps_the_later(qtbot, fake_controller):
    fakes = Fakes({"damaged.png": unreadable_work()},
                  {("damaged.png", A_FMT): decoded_work(b"d" * 10, lost=5),
                   ("new.png", A_FMT): decoded_work(b"n" * 10)})  # fmt: skip
    controller, notices, dmg = by_hand_with_damaged_page_1(qtbot, fake_controller, fakes)
    fakes.held.add("new.png")
    controller.replace(1, "/x/new.png")
    controller.replace(2, "/x/new.png")  # the user changes their mind while it decodes
    fakes.gate.set()
    idle(qtbot, controller)
    doc = controller.document
    new = doc.scan_id_of("/x/new.png")
    assert doc.pages()[0].scan_id == dmg
    assert (doc.pages()[1].scan_id, doc.pages()[1].health) == (new, Health.GOOD)
    assert notices == []


def test_a_scan_decoded_in_another_format_keeps_its_own_preview(qtbot, fake_controller):
    a_data = b"a" * 4 + b"b" * 4
    a_tag = make_tag(a_data)
    own_marks = np.array([[1, 2]], np.float32)
    letter_marks = np.array([[3, 4], [5, 6]], np.float32)
    a1 = ScanWork(ScanInfo(A_FMT, 2, 1, "doc", a_tag), "",
                  PageOutcome(a_data[:4], (100, 1, 0, 0), 0), 1, own_marks, SIZE)
    in_letter = ScanWork(None, "", PageOutcome(b"z" * 5, (100, 2, 0, 0), 0), 3,
                         letter_marks, SIZE)  # fmt: skip
    fakes = Fakes({"a1.png": a1, "a2.png": identified_work(A_FMT, 2, 2, "doc", a_tag, a_data[4:])},
                  {("a1.png", L_FMT): in_letter})  # fmt: skip
    controller, notices = fake_controller(fakes)
    tab = ReadTab(controller)
    qtbot.addWidget(tab)
    shown = []
    tab.preview.show_scan = lambda path, rotation, marks, restored=False, dot=0.0: shown.append(
        (path and os.path.basename(path), rotation, None if marks is None else marks.tolist()))
    controller.add_paths(["/x/a1.png", "/x/a2.png"])
    idle(qtbot, controller)
    doc = controller.document
    sid = doc.scan_id_of("/x/a1.png")
    controller.start_by_hand("letter", 1)
    assert controller.assign(sid, 1)
    idle(qtbot, controller)
    select(tab, "Page 1 · Repaired · 2")
    assert shown[-1] == ("a1.png", 3, letter_marks.tolist())  # as decoded for this document
    controller.switch_document(doc.others()[0].key)  # back to its own document
    idle(qtbot, controller)
    assert doc.current.format == A_FMT
    select(tab, "Page 1 · Repaired · 1")
    assert shown[-1] == ("a1.png", 1, own_marks.tolist())  # its own reading again
    assert notices == []


def test_a_scan_whose_reading_was_cancelled_by_hand_is_read_again(qtbot, fake_controller):
    fakes = Fakes(
        {"damaged.png": unreadable_work(),
         "other.png": identified_work(A_FMT, 1, 1, "o", make_tag(b"o" * 4), b"o" * 4),
         "slow.png": unreadable_work(), "x.png": unreadable_work()},
        {("x.png", A_FMT): decoded_work(b"x" * 4)},
    )  # fmt: skip
    controller, notices = fake_controller(fakes, max_workers=1)
    controller.add_paths(["/x/damaged.png", "/x/other.png"])
    idle(qtbot, controller)
    controller.start_by_hand("a4", 2)
    fakes.held.add("slow.png")
    controller.add_paths(["/x/slow.png", "/x/x.png"])  # x.png waits behind slow.png
    controller.replace(2, "/x/x.png")  # decoding it for this page cancels its reading
    fakes.gate.set()
    idle(qtbot, controller)
    doc = controller.document
    x = doc.scan_id_of("/x/x.png")
    assert (doc.pages()[1].scan_id, doc.pages()[1].health) == (x, Health.GOOD)
    controller.switch_document(doc.others()[0].key)  # leaves the document by hand
    idle(qtbot, controller)
    # Its own reading was done after all, so it is listed (and could not be added
    # again, being there already).
    assert [s.id for s in doc.unreadable()] == [doc.scan_id_of("/x/damaged.png"),
                                                doc.scan_id_of("/x/slow.png"), x]  # fmt: skip
    assert notices == []


class ReportingFakes(Fakes):
    """Fakes whose own readings of the names in ``reporting`` report finding the
    page, then wait until cancelled or until ``gate`` is set."""

    reporting: frozenset = frozenset()

    def process(self, path, cancelled=lambda: False, on_progress=None):
        name = os.path.basename(path)
        if name in self.reporting and on_progress is not None:
            on_progress(Progress(STEP_FIND, 0, 1, 0.1))
            while not self.gate.is_set():
                if cancelled():
                    raise Cancelled()
                self.gate.wait(0.01)
        return super().process(path, cancelled, on_progress)


def test_a_scan_read_again_keeps_its_last_step_until_it_reports(qtbot, fake_controller):
    fakes = ReportingFakes(
        {"damaged.png": unreadable_work(),
         "other.png": identified_work(A_FMT, 1, 1, "o", make_tag(b"o" * 4), b"o" * 4),
         "x.png": unreadable_work()},
        {("x.png", A_FMT): decoded_work(b"x" * 4)},
    )  # fmt: skip
    controller, notices = fake_controller(fakes)
    tab = ReadTab(controller)
    qtbot.addWidget(tab)
    controller.add_paths(["/x/damaged.png", "/x/other.png"])
    idle(qtbot, controller)
    controller.start_by_hand("a4", 2)
    fakes.reporting = frozenset({"x.png"})
    controller.add_paths(["/x/x.png"])
    qtbot.waitUntil(lambda: "x.png · Finding the page" in tab.rows(), timeout=TIMEOUT)
    fakes.held.add("x.png")  # its decode for the page waits
    controller.replace(2, "/x/x.png")  # decoding it for this page cancels its reading
    doc = controller.document
    x = doc.scan_id_of("/x/x.png")
    assert doc.pages()[1].scan_id == x
    controller.switch_document(doc.others()[0].key)  # leaves the document by hand
    # Listed as being read again: its last step, not back to "Waiting".
    assert "x.png · Finding the page" in tab.rows()
    assert "x.png · Waiting" not in tab.rows()
    fakes.gate.set()  # the decode reports; its own reading runs again and ends
    idle(qtbot, controller)
    assert x in [s.id for s in doc.unreadable()]
    assert notices == []


def test_a_new_scan_replaced_by_hand_is_read_with_its_label_too(qtbot, fake_controller):
    fakes = Fakes(
        {"damaged.png": unreadable_work(),
         "other.png": identified_work(A_FMT, 1, 1, "o", make_tag(b"o" * 4), b"o" * 4),
         "new.png": unreadable_work()},
        {("new.png", A_FMT): decoded_work(b"n" * 4)},
    )  # fmt: skip
    controller, notices = fake_controller(fakes)
    controller.add_paths(["/x/damaged.png", "/x/other.png"])
    idle(qtbot, controller)
    controller.start_by_hand("a4", 1)
    controller.replace(1, "/x/new.png")  # added for the page: no label to go by
    idle(qtbot, controller)
    doc = controller.document
    new = doc.scan_id_of("/x/new.png")
    assert (doc.pages()[0].scan_id, doc.pages()[0].health) == (new, Health.GOOD)
    controller.switch_document(doc.others()[0].key)
    idle(qtbot, controller)
    assert new in [s.id for s in doc.unreadable()]  # listed, not lost
    assert notices == []


def test_a_finished_check_keeps_the_saved_note(qtbot, fake_controller, monkeypatch, tmp_path):
    import optar_gui.document as document_module

    a_data = b"a" * 4 + b"b" * 4
    a_tag = make_tag(a_data)
    fakes = Fakes({"a1.png": identified_work(A_FMT, 2, 1, "doc", a_tag, a_data[:4]),
                   "a2.png": identified_work(A_FMT, 2, 2, "doc", a_tag, a_data[4:])},
                  {})  # fmt: skip
    gate = threading.Event()
    real_check = document_module.VerdictJob.__call__

    def held_check(self, cancelled=lambda: False):
        gate.wait(TIMEOUT / 1000)
        return real_check(self, cancelled)

    monkeypatch.setattr(document_module.VerdictJob, "__call__", held_check)
    controller, _ = fake_controller(fakes)
    controller.add_paths(["/x/a1.png", "/x/a2.png"])
    qtbot.waitUntil(lambda: controller.runner.active == 0, timeout=TIMEOUT)
    controller.refresh()
    assert controller.checking
    controller.save(str(tmp_path / "doc"))
    qtbot.waitUntil(lambda: not controller.saving, timeout=TIMEOUT)
    assert controller.note == text.saved_message(str(tmp_path / "doc"), 8)
    gate.set()
    qtbot.waitUntil(lambda: not controller.checking, timeout=TIMEOUT)
    controller.refresh()
    assert controller.summary.state == DocState.VERIFIED
    assert controller.note == text.saved_message(str(tmp_path / "doc"), 8)  # nothing changed


# --- The controller on its own ---------------------------------------------------------


def _two_scans_of_page_1(controller):
    doc = controller.document
    ids = []
    for n, lost in ((1, 0), (2, 3)):
        sid = doc.add_scan(f"/scans/{n}.png")
        doc.set_identified(sid, ScanInfo(A4.to_string(), 1, 1, "x.bin", None))
        doc.set_outcome(sid, PageOutcome(b"x" * 16, (100, 0, 0, 0), lost))
        ids.append(sid)
    controller.refresh()
    return ids


def test_actions_clear_the_note_and_do_nothing_after_closing(qtbot):
    controller = ReadController(process=cached_process, unlabelled=cached_unlabelled)
    try:
        good, spare = _two_scans_of_page_1(controller)
        doc = controller.document
        controller.note = "Saved 16 bytes to x.bin"
        controller.use_spare(spare)
        assert controller.note == "" and doc.pages()[0].scan_id == spare
        controller.note = "Saved 16 bytes to x.bin"
        assert not controller.assign(good, 2)  # no such page: nothing happens
        assert controller.note == "Saved 16 bytes to x.bin"
        assert controller.assign(good, 1)
        assert controller.note == "" and doc.slots()[0] == PageSlot(1, spare, (good,))
        assert controller.shutdown(TIMEOUT)
        changes = []
        controller.changed.connect(lambda: changes.append(1))
        controller.note = "Saved 16 bytes to x.bin"
        controller.use_spare(spare)
        assert not controller.assign(spare, 1)
        controller.start_by_hand("a4", 3)
        controller.switch_document(spare)
        controller.replace(1, "/scans/3.png")
        controller.remove(good)
        controller.add_paths(["/scans/4.png"])
        assert doc.slots()[0] == PageSlot(1, spare, (good,)) and not doc.by_hand
        assert len(doc.scans()) == 2 and changes == []
        assert controller.note == "Saved 16 bytes to x.bin"  # every action clears it, if run
    finally:
        controller.shutdown(TIMEOUT)


def test_start_by_hand_suggests_the_paper_from_the_scan_shape(qtbot, tmp_path):
    controller = ReadController(process=cached_process, unlabelled=cached_unlabelled)
    try:
        doc = controller.document
        assert controller.suggested_paper() == "a4"  # nothing to go by
        letter = PAPERS["letter"]
        size = (int(letter.width_pt * 3), int(letter.height_pt * 3))
        sid = doc.add_scan(str(tmp_path / "s.png"))
        controller._on_finished(sid, _unreadable_work(size))
        assert controller.suggested_paper() == "letter"
        assert controller.suggested_paper(sid) == "letter"
        controller.start_by_hand("letter", 4)
        cur = doc.current
        assert (cur.format, cur.total, doc.by_hand) == (
            PageFormat.for_paper(letter).to_string(), 4, True
        )
    finally:
        controller.shutdown(TIMEOUT)


def _unreadable_work(size):
    from optar_gui.work import ScanWork

    return ScanWork(None, "label unreadable", None, 0, None, size)


# --- The dialogs -----------------------------------------------------------------------


def test_assign_page_dialog(qtbot):
    dialog = AssignPageDialog(5, suggested=3, scan_name="scan.png")
    qtbot.addWidget(dialog)
    assert dialog.page() == 3
    assert (dialog.spin.minimum(), dialog.spin.maximum()) == (1, 5)
    assert dialog.spin.suffix() == text.of_pages(5)
    assert dialog.windowTitle() == text.ASSIGN_TITLE
    dialog.spin.setValue(9)
    assert dialog.page() == 5


def test_start_by_hand_dialog(qtbot):
    dialog = StartByHandDialog("letter")
    qtbot.addWidget(dialog)
    assert dialog.choice() == ("letter", 1)
    assert [dialog.paper.itemText(i) for i in range(dialog.paper.count())] == [
        text.paper_label(name) for name in PAPERS
    ]
    dialog.paper.setCurrentIndex(list(PAPERS).index("a4"))
    dialog.total.setValue(12)
    assert dialog.choice() == ("a4", 12)
    assert dialog.total.maximum() == MAX_TOTAL_PAGES
    assert dialog.windowTitle() == text.START_BY_HAND_TITLE
