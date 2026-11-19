# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Print-ready PDF writer: one 1-bit Flate image per page.

The image is placed at the dot size of its layout: 200 pixels per inch for a
Paper (standard dots), the Layout's own pixels_per_inch otherwise. A page of a
Layout may come with a label strip (font.fine_label), a second 1-bit image
printed over the page's label band at the standard dot size.
"""

import contextlib
import os
import zlib
from collections.abc import Iterable

import numpy as np

from optar.errors import FormatError, OptarError, error
from optar.format import (
    MIN_MARGIN_PT,
    PIXELS_PER_INCH,
    POINTS_PER_INCH,
    STANDARD_PRINTER_DOTS,
    Layout,
    Paper,
)

_CATALOG = 1
_PAGES = 2


def _placement(target: Paper | Layout) -> tuple[Paper, float, float, float]:
    """The paper, the image offsets in points and the pixels per inch for a target."""
    if isinstance(target, Layout):
        return target.paper, target.offset_x_pt, target.offset_y_pt, float(target.pixels_per_inch)
    return target, target.offset_x_pt, target.offset_y_pt, PIXELS_PER_INCH


def _check_page(item, target: Paper | Layout) -> tuple[np.ndarray, np.ndarray | None]:
    """A page and its label strip (None without one), both checked."""
    image, band = item if isinstance(item, tuple) else (item, None)
    if not isinstance(image, np.ndarray) or image.dtype != np.uint8:
        kind = f"dtype {image.dtype}" if isinstance(image, np.ndarray) else type(image).__name__
        raise TypeError(f"page must be a uint8 numpy array, got {kind}")
    if image.ndim != 2 or image.size == 0:
        raise ValueError(f"page must be a non-empty 2-D image, got shape {image.shape}")
    height, width = image.shape
    if isinstance(target, Layout):
        fmt = target.fmt
        if (width, height) != (fmt.width, fmt.height):
            raise error(
                FormatError, "err.page_size",
                "a {width} x {height} pixel page is not the {page_width} x {page_height} "
                "pixel page of the {dots} dot layout on {paper} paper",
                width=width, height=height, page_width=fmt.width, page_height=fmt.height,
                dots=target.dots.name, paper=target.paper.name,
            )
    elif not target.fits_image(width, height):
        raise error(
            FormatError, "err.page_clipped",
            "a {width} x {height} pixel page leaves less than the {margin} pt margin on "
            "{paper} paper and would be clipped by the printer",
            width=width, height=height, margin=f"{MIN_MARGIN_PT:g}", paper=target.name,
        )
    if band is None:
        return image, None
    if not isinstance(target, Layout):
        raise error(
            FormatError, "err.strip_needs_layout", "a label strip needs the layout of its page"
        )
    ok = isinstance(band, np.ndarray) and band.dtype == np.uint8 and band.ndim == 2
    if not ok or not band.size:
        raise TypeError("label strip must be a non-empty 2-D uint8 numpy array")
    fmt, dots = target.fmt, target.dots.printer_dots
    rows, cols = band.shape
    if (
        rows * STANDARD_PRINTER_DOTS > fmt.text_height * dots
        or cols * STANDARD_PRINTER_DOTS > fmt.data_width * dots
    ):
        raise error(
            FormatError, "err.strip_too_large",
            "a {width} x {height} label strip does not fit the label band of the {dots} "
            "dot layout",
            width=cols, height=rows, dots=target.dots.name,
        )
    return image, band


def write_pdf(
    path,
    pages: Iterable[np.ndarray | tuple[np.ndarray, np.ndarray | None]],
    paper: Paper | Layout,
) -> int:
    """Write each page image (0 black / 255 white) as one PDF page; return the count.

    A page may be given as (image, strip): the strip (font.fine_label) is
    printed over the label band of the image at the standard dot size, at the
    left of the band and in the middle of its height, and the rest of the band
    is printed black. This needs a Layout. The data area is untouched.

    A Paper means its standard layout at 200 pixels per inch; a Layout places
    the page at its own offsets and dot size and refuses any other image size.

    Pages are consumed lazily and written as they arrive. The file is created
    only once the first page has arrived and passed its checks, and it is
    removed again if anything fails after that.

    Raises OptarError if there are no pages, TypeError for a page that is not
    a uint8 numpy array, ValueError for one that is not a non-empty 2-D image,
    and FormatError (a ValueError) for one that, with a Paper, would leave
    less than MIN_MARGIN_PT on any side of the paper or, with a Layout, is not
    exactly the size of the layout's page, and for a label strip given with a
    Paper or larger than the label band.
    """
    pages = iter(pages)
    first = next(pages, None)
    if first is None:
        raise error(OptarError, "err.no_pages", "no pages to write")
    first = _check_page(first, paper)
    f = open(path, "wb")  # opened outside the try: a failed open removes nothing
    try:
        with f:
            return _write(f, first, pages, paper)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(path)
        raise


def _write(f, first, rest, target: Paper | Layout) -> int:
    paper, x, y, ppi = _placement(target)
    offsets: dict[int, int] = {}
    kids: list[int] = []

    def all_pages():
        yield first
        for item in rest:
            yield _check_page(item, target)

    def emit(num: int, body: bytes) -> None:
        offsets[num] = f.tell()
        f.write(b"%d 0 obj\n" % num + body + b"\nendobj\n")

    def stream_obj(num: int, header: bytes, data: bytes) -> None:
        emit(
            num,
            b"<< " + header + b"/Length %d >>\nstream\n" % len(data) + data + b"\nendstream",
        )

    def image_obj(num: int, image: np.ndarray) -> None:
        height, width = image.shape
        stream_obj(
            num,
            (
                f"/Type /XObject /Subtype /Image /Width {width} /Height {height} "
                "/ColorSpace /DeviceGray /BitsPerComponent 1 "
                "/Interpolate false /Filter /FlateDecode "
            ).encode(),
            zlib.compress(np.packbits(image > 127, axis=1).tobytes(), 9),
        )

    f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    count = 0
    free = 3  # the next unused object number
    for image, band in all_pages():
        height, width = image.shape
        page_n, content_n, image_n = free, free + 1, free + 2
        free += 3
        unit = POINTS_PER_INCH / ppi  # one page pixel, in points
        w = width * unit
        h = height * unit
        content = f"q {w:.2f} 0 0 {h:.2f} {x:.2f} {y:.2f} cm /Im0 Do Q"
        xobjects = f"/Im0 {image_n} 0 R"
        if band is not None:
            fmt = target.fmt
            top = fmt.border + fmt.data_height  # first row of the label band
            image = image.copy()
            image[top : top + fmt.text_height, fmt.border : fmt.border + fmt.data_width] = 0
            fine = POINTS_PER_INCH / PIXELS_PER_INCH  # one standard dot, in points
            bw = band.shape[1] * fine
            bh = band.shape[0] * fine
            bx = x + fmt.border * unit
            by = y + h - (top + fmt.text_height) * unit + (fmt.text_height * unit - bh) / 2
            content += f" q {bw:.3f} 0 0 {bh:.3f} {bx:.3f} {by:.3f} cm /Im1 Do Q"
            xobjects += f" /Im1 {free} 0 R"
        emit(
            page_n,
            (
                f"<< /Type /Page /Parent {_PAGES} 0 R "
                f"/MediaBox [0 0 {paper.width_pt:g} {paper.height_pt:g}] "
                f"/Contents {content_n} 0 R "
                f"/Resources << /XObject << {xobjects} >> >> >>"
            ).encode(),
        )
        stream_obj(content_n, b"", content.encode())
        image_obj(image_n, image)
        if band is not None:
            image_obj(free, band)
            free += 1
        kids.append(page_n)
        count += 1

    emit(_CATALOG, b"<< /Type /Catalog /Pages %d 0 R >>" % _PAGES)
    refs = " ".join(f"{k} 0 R" for k in kids)
    emit(_PAGES, f"<< /Type /Pages /Kids [{refs}] /Count {count} >>".encode())

    xref = f.tell()
    f.write(b"xref\n0 %d\n" % free)
    f.write(b"0000000000 65535 f \n")
    for n in range(1, free):
        f.write(b"%010d 00000 n \n" % offsets[n])
    f.write(b"trailer\n<< /Size %d /Root %d 0 R >>\n" % (free, _CATALOG))
    f.write(b"startxref\n%d\n%%%%EOF\n" % xref)
    return count
