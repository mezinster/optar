# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The preview of the selected scan: upright, with its damaged places marked.

``ScanPreview`` shows a scan file as an image (not through ``read_scan``: no
gamma, no decoding), turned upright, with one mark per bit that error
correction changed. The wheel zooms around the cursor, dragging pans and a
double-click fits the page to the view.

Scene coordinates are upright scan pixels: the scene is exactly as large as
the upright scan, and a mark at (x, y) (pixel centres at integers, as
``ScanWork.marks`` gives them) is drawn at the centre of that pixel.

Loading. The file is read by ``load_for_preview`` on a ``JobRunner`` (one
worker), never on the interface thread. Selecting another scan cancels the
load in progress, and a cancelled job never reports, so only the latest
selection is shown.

Size. The scan's size is the loaded image's, as ``read_scan`` sees it (Pillow
turns a TIFF with an orientation tag while loading it), so marks fall on the
pixels they belong to.

Memory. Only a gray copy of at most ``PREVIEW_MAX_PIXELS`` is kept for
display: a larger scan is reduced by a whole factor (box filter, boxes from
the top left corner of the file) and each reduced pixel is drawn over exactly
the scan pixels of its box, so marks stay exact at any zoom. While loading,
the decoded file is held once at full size (8 bits a pixel for a gray scan,
16 for a 16-bit one, its own depth for colour) until it has been reduced.
Scans above ``MAX_SCAN_PIXELS`` are refused, as ``read_scan`` refuses them.

Marks are one item. An ordinary page's (sparse) are drawn in a single
``drawPointsNp`` call with a cosmetic pen, straight from two numpy arrays, so
they keep their size on screen at any zoom (a PySide6 without ``drawPointsNp``
is given a polygon of points, built once). The few hundred thousand of a page
read by the slower reader are drawn one dot of the page wide instead
(``show_scan``'s ``dot``), as an image with a pixel per dot-sized cell: seen
whole the page shows a tint as dense as the marks, zoomed in single dots.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from functools import partial
from typing import NamedTuple

import numpy as np
from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QStyleOptionGraphicsItem,
    QWidget,
)

from optar.errors import OptarError
from optar.imageio import MAX_SCAN_PIXELS, SCAN_FORMATS, scan_pixel_limit
from optar_gui import text
from optar_gui.jobs import JobRunner
from optar_gui.work import Cancelled, regular_file

__all__ = [
    "MARK_SIZE",
    "MAX_ZOOM",
    "PREVIEW_MAX_PIXELS",
    "Loaded",
    "ScanPreview",
    "load_for_preview",
]

# Largest image kept for display: a 600 dpi A4 or Letter scan (about 35
# megapixels) is shown as it is; a 1200 dpi one is reduced 2 x 2.
PREVIEW_MAX_PIXELS = 40_000_000
# Side of a mark on screen, in device pixels, at any zoom.
MARK_SIZE = 5
MARK_COLOUR = QColor(230, 0, 0)
# Marks of blocks that the document's protection repaired: nothing is lost.
RESTORED_COLOUR = QColor(240, 170, 0)
BACKGROUND = QColor(128, 128, 128)
# Zoom per wheel notch, and the largest zoom (screen pixels per scan pixel).
ZOOM_STEP = 1.25
MAX_ZOOM = 16.0

_LOAD_JOB = 1  # the preview's only job id on its runner
# Modes Image.reduce handles; other modes become 8-bit gray before reducing.
_REDUCIBLE = ("L", "RGB", "RGBA")
# Pixels converted at a time from a 16-bit scan to 8 bits.
_STRIP_PIXELS = 4_000_000


def _check(cancelled: Callable[[], bool]) -> None:
    if cancelled():
        raise Cancelled()


def _ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def _reduction(width: int, height: int) -> int:
    """The smallest whole factor that brings the image to PREVIEW_MAX_PIXELS."""
    factor = 1
    while _ceil_div(width, factor) * _ceil_div(height, factor) > PREVIEW_MAX_PIXELS:
        factor += 1
    return factor


def _high_bytes(im: Image.Image) -> Image.Image:
    """A 16-bit (or 32-bit integer) gray image as 8-bit gray: its high byte, as
    read_scan takes it. Converted a strip at a time into one 8-bit array, so no
    other full-size copy is made."""
    width, height = im.size
    out = np.empty((height, width), np.uint8)
    rows = max(1, _STRIP_PIXELS // width)
    for top in range(0, height, rows):
        strip = np.array(im.crop((0, top, width, min(top + rows, height))))
        if im.mode == "I":
            np.clip(strip, 0, 65535, out=strip)
        strip >>= 8
        out[top : top + rows] = strip
    return Image.fromarray(out)


def _gray8(im: Image.Image) -> tuple[Image.Image, int]:
    """The loaded image reduced to PREVIEW_MAX_PIXELS, as 8-bit gray, and the
    reduction factor."""
    if im.mode.startswith("I"):
        im = _high_bytes(im)
    elif im.mode not in _REDUCIBLE:
        im = im.convert("L")
    factor = _reduction(*im.size)
    if factor > 1:
        im = im.reduce(factor)
    if im.mode != "L":
        im = im.convert("L")
    return im, factor


def _upright_box(
    size: tuple[int, int], cover: tuple[int, int], rotation: int
) -> tuple[int, int, int, int]:
    """Where the rectangle (0, 0, *cover) of a scan of ``size`` lies once the scan
    is turned upright: (x, y, width, height) in upright scan pixels."""
    w, h = size
    x0, y0, x1, y1 = 0, 0, cover[0], cover[1]
    for _ in range(rotation % 4):
        # A counter-clockwise quarter turn (np.rot90) takes (x, y) to (y, w - x).
        x0, y0, x1, y1 = y0, w - x1, y1, w - x0
        w, h = h, w
    return (x0, y0, x1 - x0, y1 - y0)


class Loaded(NamedTuple):
    """A scan read for display.

    ``pixels``: the upright image, 8-bit gray, at most PREVIEW_MAX_PIXELS.
    ``size``: the upright scan's (width, height). ``box``: where ``pixels`` is to
    be drawn, (x, y, width, height) in upright scan pixels; it reaches past the
    scan by part of a reduction box when the size does not divide by it.
    """

    pixels: np.ndarray
    size: tuple[int, int]
    box: tuple[int, int, int, int]


def load_for_preview(path: str, rotation: int, cancelled: Callable[[], bool]) -> Loaded:
    """Reads a scan for display, upright.

    Opens only the formats ``read_scan`` opens and refuses what it refuses for
    size, and only regular files (a named pipe would block the worker). Raises
    OptarError when the file cannot be read, Cancelled when ``cancelled()``
    turns True.
    """
    regular_file(path)
    im = None
    try:
        # Pillow's own pixel limit would warn about or refuse 1200 dpi scans;
        # the library's lock lifts it to read_scan's cap without racing it.
        with scan_pixel_limit():
            im = Image.open(path, formats=SCAN_FORMATS)
            width, height = im.size
            if width * height > MAX_SCAN_PIXELS:
                raise OptarError(text.too_large_to_show(width * height, MAX_SCAN_PIXELS))
            drafted = 1  # JPEG decodes straight to a smaller size; others ignore it
            factor = _reduction(width, height)
            if factor > 1:
                draft = im.draft("L", (_ceil_div(width, factor), _ceil_div(height, factor)))
                if draft is not None:
                    drafted = round(width / draft[1][2])
            if im.format != "PNG":  # other formats check the size again while loading
                im.load()
        _check(cancelled)
        im.load()
        if drafted == 1:
            # Pillow may turn the image while loading it (TIFF orientation);
            # read_scan, and so the marks, see the loaded image.
            if im.width * im.height != width * height:
                raise OptarError(text.size_changed())
            width, height = im.size
        elif im.size != (_ceil_div(width, drafted), _ceil_div(height, drafted)):
            # A JPEG decoded smaller must be exactly the reduction draft reported,
            # or its pixels would be drawn over the wrong scan pixels.
            raise OptarError(text.size_changed())
        _check(cancelled)
        gray, reduced = _gray8(im)
        gray = np.asarray(gray)  # may be ``im`` itself: take the pixels first
        im.close()
        im = None
        _check(cancelled)
        step = drafted * reduced  # scan pixels per displayed pixel, each way
        cover = (gray.shape[1] * step, gray.shape[0] * step)
        upright = np.rot90(gray, rotation % 4).copy()  # contiguous, writable
        del gray
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as e:
        raise OptarError(str(e)) from e
    finally:
        if im is not None:
            im.close()
    size = (height, width) if rotation % 2 else (width, height)
    return Loaded(upright, size, _upright_box((width, height), cover, rotation))


class _ImageItem(QGraphicsItem):
    """A gray image drawn over its box, clipped to the scan (0, 0, width, height)."""

    def __init__(self, loaded: Loaded) -> None:
        super().__init__()
        pixels = loaded.pixels
        self._pixels = pixels  # the QImage below refers to this buffer
        h, w = pixels.shape
        self._image = QImage(pixels.data, w, h, pixels.strides[0], QImage.Format.Format_Grayscale8)
        self._rect = QRectF(0, 0, *loaded.size)
        self._box = QRectF(*loaded.box)
        self._kx = w / self._box.width()  # image pixels per scan pixel
        self._ky = h / self._box.height()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemUsesExtendedStyleOption)

    def boundingRect(self) -> QRectF:  # noqa: N802
        return self._rect

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None
    ) -> None:
        exposed = option.exposedRect & self._rect & self._box
        if exposed.isEmpty():
            return
        kx, ky = self._kx, self._ky
        box = self._box
        source = QRectF((exposed.x() - box.x()) * kx, (exposed.y() - box.y()) * ky,
                        exposed.width() * kx, exposed.height() * ky)  # fmt: skip
        # Smooth when shrinking; sharp image pixels when zoomed in.
        on_screen = painter.worldTransform().m11() / kx
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, on_screen < 1)
        painter.drawImage(exposed, self._image, source)


# Whether this PySide6 draws points straight from numpy arrays; older ones are
# given a polygon of points instead (built once per set of marks).
_POINTS_NP = hasattr(QPainter, "drawPointsNp")


class _MarksItem(QGraphicsItem):
    """Every mark as a square of MARK_SIZE screen pixels, in one drawing call."""

    def __init__(
        self, points: tuple[np.ndarray, np.ndarray], rect: QRectF, colour: QColor = MARK_COLOUR
    ) -> None:
        super().__init__()
        self._xs, self._ys = points
        self._polygon = None if _POINTS_NP else _polygon(self._xs, self._ys)
        self._rect = rect
        self._pen = QPen(colour)
        self._pen.setWidthF(MARK_SIZE)
        self._pen.setCosmetic(True)  # the width is in screen pixels
        self._pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        self.setZValue(1)

    def boundingRect(self) -> QRectF:  # noqa: N802
        return self._rect

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(self._pen)
        if self._polygon is None:
            painter.drawPointsNp(self._xs, self._ys)
        else:
            painter.drawPoints(self._polygon)


def _polygon(xs: np.ndarray, ys: np.ndarray) -> QPolygonF:
    return QPolygonF([QPointF(x, y) for x, y in zip(xs.tolist(), ys.tolist(), strict=True)])


_NO_POINTS = (np.zeros(0), np.zeros(0))


def _points(marks: np.ndarray | None) -> tuple[np.ndarray, np.ndarray]:
    """The marks' scene points (pixel centres) as contiguous x and y arrays."""
    if marks is None or len(marks) == 0:
        return _NO_POINTS
    centres = np.asarray(marks, np.float64).reshape(-1, 2) + 0.5
    return np.ascontiguousarray(centres[:, 0]), np.ascontiguousarray(centres[:, 1])


class _DotMarksItem(QGraphicsItem):
    """Marks one dot of the page wide, in scan pixels: they grow and shrink with the
    zoom. Drawn as an image with one pixel per dot-sized cell of the scan (a mark
    fills the cell its centre falls in), smoothed when shrunk, so seen whole a
    dense page shows a tint as dense as its marks are; zoomed in, each is a square
    of one dot. The image is a byte a cell (an A4 page of Standard dots is about
    4 MB)."""

    def __init__(
        self, points: tuple[np.ndarray, np.ndarray], dot: float, rect: QRectF,
        colour: QColor = MARK_COLOUR,
    ) -> None:  # fmt: skip
        super().__init__()
        xs, ys = points
        w = max(1, math.ceil(rect.width() / dot))
        h = max(1, math.ceil(rect.height() / dot))
        cells = np.zeros((h, w), np.uint8)
        cx = np.clip((xs / dot).astype(np.intp), 0, w - 1)
        cy = np.clip((ys / dot).astype(np.intp), 0, h - 1)
        cells[cy, cx] = 1
        self._cells = cells  # the QImage below refers to this buffer
        self._image = QImage(cells.data, w, h, w, QImage.Format.Format_Indexed8)
        self._image.setColorTable([0, colour.rgba()])
        self._dot = dot
        self._rect = rect
        self.setZValue(1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemUsesExtendedStyleOption)

    def boundingRect(self) -> QRectF:  # noqa: N802
        return self._rect

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None
    ) -> None:
        exposed = option.exposedRect & self._rect
        if exposed.isEmpty():
            return
        dot = self._dot
        source = QRectF(exposed.x() / dot, exposed.y() / dot,
                        exposed.width() / dot, exposed.height() / dot)  # fmt: skip
        on_screen = painter.worldTransform().m11() * dot  # screen pixels per dot
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, on_screen < 1)
        painter.drawImage(exposed, self._image, source)


class ScanPreview(QGraphicsView):
    """The selected scan, upright, with its damaged places marked.

    ``loaded(path)`` is emitted once the scan asked for last is shown, or
    could not be (``message`` then says why). Loads run on ``runner`` (by
    default its own, with one worker); whoever owns the runner shuts it down.
    """

    loaded = Signal(str)

    def __init__(self, runner: JobRunner | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("scanPreview")
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(BACKGROUND)
        self._runner = runner if runner is not None else JobRunner(self, max_workers=1)
        self._runner.finished.connect(self._on_loaded)
        self._runner.failed.connect(self._on_failed)
        self._path: str | None = None
        self._rotation = 0
        self._marks: np.ndarray | None = None  # as given, to see whether they changed
        self._mark_colour = MARK_COLOUR
        self._dot = 0.0  # scan pixels per dot for marks sized to the dots; 0: screen size
        self._points = _NO_POINTS
        self._size: tuple[int, int] | None = None  # upright scan size, once shown
        self._marks_item: QGraphicsItem | None = None
        self._loading = False
        self._message = ""
        self._fitted = True  # whether resizing refits the page

    # --- State -------------------------------------------------------------------

    @property
    def path(self) -> str | None:
        """The scan shown or being loaded."""
        return self._path

    @property
    def loading(self) -> bool:
        return self._loading

    @property
    def message(self) -> str:
        """Why the scan cannot be shown, or ""."""
        return self._message

    @property
    def mark_count(self) -> int:
        """How many marks are drawn."""
        return len(self._points[0]) if self._marks_item is not None else 0

    @property
    def zoom(self) -> float:
        """Screen pixels per scan pixel."""
        return self.transform().m11()

    # --- Showing -----------------------------------------------------------------

    def show_scan(
        self,
        path: str | None,
        rotation: int,
        marks: np.ndarray | None,
        restored: bool = False,
        dot: float = 0.0,
    ) -> None:
        """Shows ``path`` turned upright by ``rotation`` counter-clockwise quarter
        turns, with a mark at each (x, y) row of ``marks`` (upright scan pixels).
        ``None`` clears the view. The same scan and rotation are not loaded again.
        ``restored`` draws the marks in RESTORED_COLOUR: the blocks they show were
        repaired by the document's protection. ``dot`` (scan pixels), when given,
        draws each mark one dot of the page wide, growing with the zoom, as for the
        dense marks of a page read by the slower reader; otherwise each mark is
        MARK_SIZE screen pixels at any zoom."""
        rotation %= 4
        colour = RESTORED_COLOUR if restored else MARK_COLOUR
        dot = float(dot) if dot and dot > 0 else 0.0
        changed = colour != self._mark_colour or dot != self._dot
        self._mark_colour = colour
        self._dot = dot
        if path is not None and path == self._path and rotation == self._rotation:
            if changed or marks is not self._marks:
                self._set_marks(marks)
            return
        self._runner.cancel(_LOAD_JOB)
        self._clear()
        if path is None:
            return
        self._path, self._rotation = path, rotation
        self._set_marks(marks)
        try:
            self._runner.submit(_LOAD_JOB, partial(load_for_preview, path, rotation))
        except RuntimeError:  # the runner was shut down with the window
            self._path = None
            return
        self._loading = True
        self._show_text(text.PREVIEW_LOADING)

    def fit(self) -> None:
        """Fits the whole page into the view."""
        self._fitted = True
        if self._size is not None:
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _clear(self) -> None:
        self._scene.clear()
        self._scene.setSceneRect(QRectF())
        self.resetTransform()
        self._path = None
        self._marks = None
        self._points = _NO_POINTS
        self._size = None
        self._marks_item = None
        self._loading = False
        self._message = ""
        self._fitted = True

    def _set_marks(self, marks: np.ndarray | None) -> None:
        self._marks = marks
        self._points = _points(marks)
        if self._marks_item is not None:
            self._scene.removeItem(self._marks_item)
            self._marks_item = None
        self._add_marks()

    def _add_marks(self) -> None:
        if self._size is None or len(self._points[0]) == 0:
            return
        rect = QRectF(0, 0, *self._size)
        if self._dot:
            self._marks_item = _DotMarksItem(self._points, self._dot, rect, self._mark_colour)
        else:
            self._marks_item = _MarksItem(self._points, rect, self._mark_colour)
        self._scene.addItem(self._marks_item)

    def _on_loaded(self, job: int, result: Loaded) -> None:
        if job != _LOAD_JOB or not self._loading:
            return
        self._loading = False
        self._scene.clear()  # the "loading" text
        self._size = result.size
        self._scene.setSceneRect(QRectF(0, 0, *result.size))
        self._scene.addItem(_ImageItem(result))
        self._add_marks()
        self.fit()
        self.loaded.emit(self._path)

    def _on_failed(self, job: int, message: str) -> None:
        if job != _LOAD_JOB or not self._loading:
            return
        self._loading = False
        self._message = text.preview_failed(message)
        self._show_text(self._message)
        self.loaded.emit(self._path)

    def _show_text(self, line: str) -> None:
        """Shows only ``line``, at its natural size."""
        self._scene.clear()
        item = QGraphicsSimpleTextItem(line)
        self._scene.addItem(item)
        self._scene.setSceneRect(item.boundingRect())

    # --- Zooming and panning -----------------------------------------------------

    def _fit_zoom(self) -> float:
        rect = self._scene.sceneRect()
        view = self.viewport().rect()
        if rect.isEmpty() or view.isEmpty():
            return 1.0
        return min(view.width() / rect.width(), view.height() / rect.height())

    def wheelEvent(self, event) -> None:  # noqa: N802
        steps = event.angleDelta().y() / 120
        event.accept()
        if not steps or self._size is None:
            return
        low = min(self._fit_zoom() / 2, MAX_ZOOM)
        target = min(max(self.zoom * ZOOM_STEP**steps, low), MAX_ZOOM)
        factor = target / self.zoom
        cursor = event.position().toPoint()
        under = self.mapToScene(cursor)
        self.scale(factor, factor)
        moved = self.mapFromScene(under) - cursor  # keep that scan point under the cursor
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + moved.x())
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() + moved.y())
        self._fitted = False

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.fit()
        event.accept()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._fitted:
            self.fit()
