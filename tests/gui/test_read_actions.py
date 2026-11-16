# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Replacing a page's scan, spares, other documents and working by hand, off-screen.

The scans are written once per module and every test runs them through
``cached_process`` and ``cached_unlabelled``: the real ``process_scan`` and
``process_unlabelled``, with each result remembered by the file's contents (and
the format), so a scan is decoded once however many tests add it.
"""

import hashlib
import shutil
import threading

import numpy as np
import pytest
from PySide6.QtWidgets import QPushButton

from optar import PAPERS, PageFormat, encode
from optar.tag import Tag, make_tag, tagged_label
from optar_gui import text
from optar_gui.dialogs import AssignPageDialog, StartByHandDialog
from optar_gui.document import (
    MAX_TOTAL_PAGES,
    DocState,
    PageOutcome,
    PageSlot,
    ScanInfo,
    ScanState,
)
from optar_gui.read_tab import ReadController, ReadTab
from optar_gui.work import process_scan, process_unlabelled
from tests.helpers import fake_scan, save_scan, seeded_bytes

TIMEOUT = 300_000  # ms: decoding is slow on a loaded machine
A4 = PageFormat.for_paper(PAPERS["a4"])
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


def cached_process(path, cancelled=lambda: False):
    """``process_scan``, remembering each result by the file's contents."""
    return _remembered(("scan", _contents(path)), lambda: process_scan(path, cancelled))


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
    images = {
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
    """make_tab() -> ReadTab with its own controller, decoding through the caches."""
    controllers = []

    def make():
        controller = ReadController(process=cached_process, unlabelled=cached_unlabelled)
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
    assert notices[1] == "page-1.png was not used for page 2: it is page 1 of this document."
    # A scan whose label cannot be read.
    tab.ask_replace_path = lambda page: paths["page-1-no-label.png"]
    click(tab, "replaceButton")
    qtbot.waitUntil(lambda: len(notices) == 3, timeout=TIMEOUT)
    assert notices[2] == (
        "page-1-no-label.png was not used for page 2. "
        "The label at the bottom of the page could not be read."
    )
    assert doc.pages()[1].scan_id == in_use
    assert doc.pages()[0].scan_id == scan_id(tab, paths["page-1.png"])
    # Cancelling the file dialog does nothing.
    tab.ask_replace_path = lambda page: None
    click(tab, "replaceButton")
    assert len(doc.scans()) == 4 and len(notices) == 3


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
    assert tab.summary.text() == "Verified · 1,000 bytes"


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
    assert tab.summary.text() == f"Verified · {len(data):,} bytes"
    assert tab.preview.path == paths["page-2-misread.png"]


def test_assign_unreadable_scan_decodes_it_in_the_best_rotation(qtbot, make_tab, scans):
    data, paths = scans
    upside_down = paths["page-2-no-label-upside-down.png"]
    tab = make_tab()
    tab.controller.add_paths([paths["page-1.png"], upside_down])
    wait_settled(qtbot, tab)
    row = (
        "page-2-no-label-upside-down.png · "
        "The label at the bottom of the page could not be read"
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
    work = tab.controller.work_for(scan_id(tab, upside_down))
    assert work.rotation == 2 and work.info is None
    assert tab.preview.path == upside_down
    assert tab.detail.text().startswith("Page 2 of 2 · page-2-no-label-upside-down.png\n")


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
        select(tab, next(r for r in tab.rows() if r.startswith(path.rsplit("/", 1)[1])))
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
        refreshes = controller.refreshes
        controller.use_spare(spare)
        assert not controller.assign(spare, 1)
        controller.start_by_hand("a4", 3)
        controller.switch_document(spare)
        controller.replace(1, "/scans/3.png")
        assert doc.slots()[0] == PageSlot(1, spare, (good,)) and not doc.by_hand
        assert len(doc.scans()) == 2 and controller.refreshes == refreshes
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
