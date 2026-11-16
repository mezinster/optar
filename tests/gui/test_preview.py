# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The scan preview, off-screen: upright image, damage marks, zoom and pan."""

import time

import numpy as np
import pytest
from PIL import Image
from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QWheelEvent
from PySide6.QtWidgets import QApplication

import optar_gui.preview as preview_module
from optar import PAPERS, PageFormat
from optar.imageio import read_scan
from optar_gui import text
from optar_gui.preview import PREVIEW_MAX_PIXELS, ScanPreview, load_for_preview
from optar_gui.read_tab import ReadController, ReadTab
from optar_gui.work import process_scan

TIMEOUT = 120_000  # ms: the machine may be heavily loaded
DECODE_TIMEOUT = 600_000
A4 = PageFormat.for_paper(PAPERS["a4"])


@pytest.fixture
def preview(qtbot):
    view = ScanPreview()
    qtbot.addWidget(view)
    view.resize(400, 500)
    view.show()
    qtbot.waitExposed(view)
    return view


def show_and_wait(qtbot, view, path, rotation=0, marks=None):
    view.show_scan(path, rotation, marks)
    qtbot.waitUntil(lambda: not view.loading, timeout=TIMEOUT)


def scene_size(view):
    rect = view.scene().sceneRect()
    return (rect.width(), rect.height())


def sample(view, x, y):
    """The gray level the scene draws at scan pixel (x, y)."""
    image = QImage(1, 1, QImage.Format.Format_RGB32)
    image.fill(QColor(255, 0, 255))
    painter = QPainter(image)
    view.scene().render(painter, QRectF(0, 0, 1, 1), QRectF(x, y, 1, 1))
    painter.end()
    return QColor(image.pixel(0, 0)).value()


def render_scene(view):
    """The whole scene drawn at one screen pixel per scan pixel, as an RGB array."""
    rect = view.scene().sceneRect()
    w, h = int(rect.width()), int(rect.height())
    image = QImage(w, h, QImage.Format.Format_RGB32)
    image.fill(QColor(255, 0, 255))
    painter = QPainter(image)
    view.scene().render(painter, QRectF(0, 0, w, h), rect)
    painter.end()
    a = np.frombuffer(image.constBits(), np.uint8).reshape(h, image.bytesPerLine())
    return a[:, : w * 4].reshape(h, w, 4)[..., 2::-1].copy()  # B, G, R, A -> R, G, B


def red_pixels(view):
    """How many strongly red pixels the viewport shows."""
    image = view.viewport().grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
    ptr = image.constBits()
    a = np.frombuffer(ptr, np.uint8).reshape(image.height(), image.bytesPerLine())
    a = a[:, : image.width() * 4].reshape(image.height(), image.width(), 4)
    b, g, r = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    return int(np.count_nonzero((r > 150) & (g < 80) & (b < 80)))


def test_shows_upright_image_and_marks(qtbot, preview, scan_files):
    _, paths = scan_files(nbytes=1000)
    with Image.open(paths[0]) as im:
        width, height = im.size
    marks = np.array([[100, 200], [300, 400], [width - 100, height - 100]], np.float32)
    loaded = []
    preview.loaded.connect(loaded.append)
    show_and_wait(qtbot, preview, paths[0], 0, marks)
    assert loaded == [paths[0]]
    assert preview.path == paths[0] and preview.message == ""
    assert scene_size(preview) == (width, height)
    assert preview.mark_count == len(marks) == 3
    assert preview.objectName() == "scanPreview"
    # Marks show in red; the page shows as it is in the file.
    assert red_pixels(preview) > 0
    assert sample(preview, 5, 5) > 200  # white margin


@pytest.mark.parametrize("rotation", [1, 2, 3])
def test_rotated_scan_is_shown_upright(qtbot, preview, scan_files, tmp_path, rotation):
    _, paths = scan_files(nbytes=1000)
    upright = np.asarray(Image.open(paths[0]).convert("L"))
    height, width = upright.shape
    # A pixel dark in the upright scan that a wrong turn would show white.
    wrong = np.rot90(upright, 2) if rotation == 2 else np.full_like(upright, 255)
    ys, xs = np.nonzero((upright < 50) & (wrong > 200))
    x, y = int(xs[len(xs) // 2]), int(ys[len(ys) // 2])
    path = tmp_path / f"turned-{rotation}.png"
    Image.fromarray(np.ascontiguousarray(np.rot90(upright, -rotation))).save(path)

    show_and_wait(qtbot, preview, str(path), rotation)
    assert scene_size(preview) == (width, height)  # portrait, like the page
    assert height > width
    assert sample(preview, x, y) < 100
    assert sample(preview, 5, 5) > 200


def test_fit_and_zoom(qtbot, preview, scan_files):
    _, paths = scan_files(nbytes=1000)
    show_and_wait(qtbot, preview, paths[0])
    preview.fit()
    visible = preview.mapToScene(preview.viewport().rect()).boundingRect()
    assert visible.adjusted(-1, -1, 1, 1).contains(preview.scene().sceneRect())
    fitted = preview.zoom
    assert 0 < fitted < 1

    # The wheel zooms in around the cursor: the scan point under it stays put.
    cursor = QPointF(150, 200)
    under = preview.mapToScene(cursor.toPoint())
    wheel = QWheelEvent(
        cursor, preview.viewport().mapToGlobal(cursor), QPoint(0, 0), QPoint(0, 240),
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(preview.viewport(), wheel)
    assert preview.zoom > fitted * 1.4
    after = preview.mapFromScene(under)
    assert abs(after.x() - cursor.x()) <= 2 and abs(after.y() - cursor.y()) <= 2

    # Dragging pans.
    before = (preview.horizontalScrollBar().value(), preview.verticalScrollBar().value())
    for kind, pos, buttons in (
        (QEvent.Type.MouseButtonPress, QPointF(200, 250), Qt.MouseButton.LeftButton),
        (QEvent.Type.MouseMove, QPointF(150, 180), Qt.MouseButton.LeftButton),
        (QEvent.Type.MouseButtonRelease, QPointF(150, 180), Qt.MouseButton.NoButton),
    ):
        event = QMouseEvent(
            kind, pos, preview.viewport().mapToGlobal(pos), Qt.MouseButton.LeftButton,
            buttons, Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(preview.viewport(), event)
    after_drag = (preview.horizontalScrollBar().value(), preview.verticalScrollBar().value())
    assert after_drag[0] > before[0] and after_drag[1] > before[1]

    # A double-click fits the page again.
    qtbot.mouseDClick(preview.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(100, 100))
    assert preview.zoom == pytest.approx(fitted)


def test_marks_keep_their_size_on_screen(qtbot, preview, tmp_path):
    path = tmp_path / "blank.png"
    Image.new("L", (2000, 2000), 255).save(path)
    show_and_wait(qtbot, preview, str(path), 0, np.array([[1000, 1000]], np.float32))
    preview.fit()
    at_fit = red_pixels(preview)
    preview.centerOn(1000, 1000)
    preview.scale(8, 8)
    preview.centerOn(1000, 1000)
    assert at_fit > 0
    assert red_pixels(preview) == at_fit


def test_latest_selection_wins(qtbot, preview, scan_files):
    _, paths = scan_files(nbytes=250_000)
    a, b = paths
    loaded = []
    preview.loaded.connect(loaded.append)
    marks_b = np.array([[50, 60]], np.float32)
    preview.show_scan(a, 0, np.zeros((5, 2), np.float32))
    preview.show_scan(b, 0, marks_b)
    qtbot.waitUntil(lambda: not preview.loading, timeout=TIMEOUT)
    qtbot.wait(200)  # a late result for a would arrive now
    assert loaded == [b]
    assert preview.path == b and preview.mark_count == 1


def test_same_scan_is_not_loaded_again(qtbot, preview, scan_files):
    _, paths = scan_files(nbytes=1000)
    loaded = []
    preview.loaded.connect(loaded.append)
    show_and_wait(qtbot, preview, paths[0])
    preview.show_scan(paths[0], 0, np.array([[10, 10], [20, 20]], np.float32))
    assert not preview.loading and preview.mark_count == 2  # marks change at once
    qtbot.wait(200)
    assert loaded == [paths[0]]


def test_clear(qtbot, preview, tmp_path):
    path = tmp_path / "blank.png"
    Image.new("L", (300, 400), 255).save(path)
    show_and_wait(qtbot, preview, str(path), 0, np.array([[10, 10]], np.float32))
    preview.show_scan(None, 0, None)
    assert preview.path is None and preview.mark_count == 0 and not preview.loading
    assert preview.scene().items() == []
    # Clearing while a scan loads drops its result.
    loaded = []
    preview.loaded.connect(loaded.append)
    preview.show_scan(str(path), 1, None)
    preview.show_scan(None, 0, None)
    qtbot.wait(500)
    assert loaded == [] and preview.scene().items() == []


def test_unreadable_file_shows_why(qtbot, preview, tmp_path):
    path = tmp_path / "notes.png"
    path.write_text("not an image")
    show_and_wait(qtbot, preview, str(path))
    assert preview.message.startswith(text.preview_failed(""))
    assert preview.mark_count == 0


def test_large_scan_is_reduced_for_display(tmp_path):
    # 2 x 2 reduction keeps the display under the limit; size is the scan's.
    side = int(PREVIEW_MAX_PIXELS**0.5) + 100
    path = tmp_path / "big.png"
    Image.new("L", (side, side + 10), 255).save(path)
    loaded = load_for_preview(str(path), 1, lambda: False)
    image, size = loaded.pixels, loaded.size
    h, w = image.shape
    assert h * w <= PREVIEW_MAX_PIXELS
    assert (w, h) == ((side + 11) // 2, (side + 1) // 2)  # upright: turned a quarter
    assert size == (side + 10, side)


def test_colour_and_deep_scans_load_as_gray(tmp_path):
    gray = np.tile(np.arange(256, dtype=np.uint8), (4, 1))
    Image.fromarray(np.dstack([gray] * 3)).save(tmp_path / "c.png")
    Image.fromarray(gray.astype(np.uint16) * 257).save(tmp_path / "d.png")
    Image.fromarray(gray >= 128).save(tmp_path / "b.png")
    Image.fromarray(gray.astype(np.uint16) * 257).save(tmp_path / "d.tif")
    colour = load_for_preview(str(tmp_path / "c.png"), 0, lambda: False).pixels
    deep = load_for_preview(str(tmp_path / "d.png"), 0, lambda: False).pixels
    deep_tiff = load_for_preview(str(tmp_path / "d.tif"), 0, lambda: False).pixels
    loaded = load_for_preview(str(tmp_path / "b.png"), 0, lambda: False)
    bits = loaded.pixels
    assert loaded.size == (256, 4)
    assert colour.dtype == deep.dtype == bits.dtype == np.uint8
    assert np.array_equal(colour, gray) and np.array_equal(deep, gray)
    assert np.array_equal(deep_tiff, gray)
    assert np.array_equal(bits, np.where(gray >= 128, 255, 0))


def test_selecting_a_page_in_the_tab_updates_preview_and_details(qtbot, scan_files):
    _, paths = scan_files(nbytes=250_000, flips=300, fmt=A4)
    controller = ReadController(process=process_scan)
    tab = ReadTab(controller)
    qtbot.addWidget(tab)
    try:
        assert tab.findChild(ScanPreview, "scanPreview") is tab.preview
        controller.add_paths(paths)
        qtbot.waitUntil(
            lambda: controller.runner.active == 0 and len(controller.document.pages()) == 2
            and all(p.histogram is not None for p in controller.document.pages()),
            timeout=DECODE_TIMEOUT,
        )
        controller.refresh()
        tab.select_row(tab.rows().index(text.page_row(controller.document.pages()[1])))
        page = controller.document.pages()[1]
        work = controller.work_for(page.scan_id)
        assert work.marks is not None and len(work.marks) > 0

        lines = tab.detail.text().splitlines()
        assert lines[0] == "Page 2 of 2 · page-2.png"
        assert lines[1].endswith(f"· {page.repaired:,} repaired · {page.lost:,} lost")
        assert page.repaired > 0
        one, two, three = page.histogram[1:]
        assert lines[2] == f"Repairs: {one:,} one-bit, {two:,} two-bit, {three:,} three-bit"

        qtbot.waitUntil(lambda: not tab.preview.loading, timeout=TIMEOUT)
        assert tab.preview.path == paths[1]
        assert tab.preview.mark_count == len(work.marks)
        w, h = work.size
        assert scene_size(tab.preview) == (w, h)

        # A page with no scan clears the preview.
        controller.remove(page.scan_id)
        assert tab.preview.path is None and tab.preview.mark_count == 0
    finally:
        assert controller.shutdown(TIMEOUT)


def test_closing_stops_a_preview_load(qtbot, tmp_path):
    controller = ReadController(process=process_scan)
    tab = ReadTab(controller)
    qtbot.addWidget(tab)
    path = tmp_path / "blank.png"
    Image.new("L", (300, 400), 255).save(path)
    tab.preview.show_scan(str(path), 0, None)
    assert controller.shutdown(TIMEOUT)
    assert controller.preview_runner.active == 0
    tab.preview.show_scan(str(path), 1, None)  # after closing: ignored, no error
    assert not tab.preview.loading


def test_thirty_thousand_marks_draw_quickly(qtbot, preview, tmp_path):
    path = tmp_path / "blank.png"
    Image.new("L", (4960, 7016), 255).save(path)
    rng = np.random.default_rng(1)
    marks = (rng.random((30_000, 2)) * [4960, 7016]).astype(np.float32)
    show_and_wait(qtbot, preview, str(path), 0, marks)
    assert preview.mark_count == 30_000
    for zoom in (1, 6):
        preview.scale(zoom, zoom)
        start = time.perf_counter()
        preview.viewport().repaint()
        assert time.perf_counter() - start < 0.5


def test_orientation_tagged_tiff_is_sized_as_read_scan_reads_it(qtbot, preview, tmp_path):
    # Pillow turns a TIFF with orientation 6 or 8 while loading it; read_scan
    # (so the marks) uses the loaded image, and the preview must too.
    a = np.full((20, 40), 255, np.uint8)
    a[3, 7] = 0
    path = tmp_path / "turned.tif"
    Image.fromarray(a).save(path, tiffinfo={274: 6})
    scan = read_scan(path)
    ys, xs = np.nonzero(scan < 128)
    assert len(xs) == 1
    x, y = int(xs[0]), int(ys[0])

    loaded = load_for_preview(str(path), 0, lambda: False)
    assert loaded.size == (scan.shape[1], scan.shape[0])
    assert loaded.pixels.shape == scan.shape

    show_and_wait(qtbot, preview, str(path), 0, None)
    assert scene_size(preview) == (scan.shape[1], scan.shape[0])
    drawn = render_scene(preview)
    assert np.array_equal(drawn[..., 0] < 128, scan < 128)
    preview.show_scan(str(path), 0, np.array([[x, y]], np.float32))
    r, g, b = render_scene(preview)[y, x]
    assert r > 150 and g < 80 and b < 80  # the mark is on that very pixel


@pytest.mark.parametrize("rotation", [0, 1, 2, 3])
def test_reduced_scan_lines_up_with_marks(qtbot, preview, tmp_path, monkeypatch, rotation):
    # 101 x 61 reduced 2 x 2: the last column and row are half boxes.
    monkeypatch.setattr(preview_module, "PREVIEW_MAX_PIXELS", 2000)
    full = np.full((61, 101), 255, np.uint8)
    full[20:22, 100] = 0  # in the half-box column
    full[60, 30:32] = 0  # in the half-box row
    full[10:12, 40:42] = 0  # a whole box
    path = tmp_path / "odd.png"
    Image.fromarray(full).save(path)
    upright = np.rot90(full, rotation)
    loaded = load_for_preview(str(path), rotation, lambda: False)
    assert loaded.pixels.shape == np.rot90(np.zeros((31, 51)), rotation).shape

    show_and_wait(qtbot, preview, str(path), rotation, None)
    assert scene_size(preview) == (upright.shape[1], upright.shape[0])
    drawn = render_scene(preview)[..., 0]
    assert np.array_equal(drawn < 128, upright < 128)


def test_shows_loading_until_the_image_arrives(qtbot, preview, tmp_path):
    path = tmp_path / "blank.png"
    Image.new("L", (300, 400), 255).save(path)
    preview.show_scan(str(path), 0, None)
    items = preview.scene().items()
    assert preview.loading and len(items) == 1 and items[0].text() == text.PREVIEW_LOADING
    qtbot.waitUntil(lambda: not preview.loading, timeout=TIMEOUT)
    assert all(not hasattr(item, "text") for item in preview.scene().items())
