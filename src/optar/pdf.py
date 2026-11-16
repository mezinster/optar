# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Print-ready PDF writer: one 1-bit Flate image per page.

The image is placed at the dot size of its layout: 200 pixels per inch for a
Paper (standard dots), the Layout's own pixels_per_inch otherwise.
"""

import contextlib
import os
import zlib
from collections.abc import Iterable

import numpy as np

from optar.errors import FormatError, OptarError
from optar.format import MIN_MARGIN_PT, PIXELS_PER_INCH, POINTS_PER_INCH, Layout, Paper

_CATALOG = 1
_PAGES = 2


def _placement(target: Paper | Layout) -> tuple[Paper, float, float, float]:
    """The paper, the image offsets in points and the pixels per inch for a target."""
    if isinstance(target, Layout):
        return target.paper, target.offset_x_pt, target.offset_y_pt, float(target.pixels_per_inch)
    return target, target.offset_x_pt, target.offset_y_pt, PIXELS_PER_INCH


def _check_page(image, target: Paper | Layout) -> np.ndarray:
    if not isinstance(image, np.ndarray) or image.dtype != np.uint8:
        kind = f"dtype {image.dtype}" if isinstance(image, np.ndarray) else type(image).__name__
        raise TypeError(f"page must be a uint8 numpy array, got {kind}")
    if image.ndim != 2 or image.size == 0:
        raise ValueError(f"page must be a non-empty 2-D image, got shape {image.shape}")
    height, width = image.shape
    if isinstance(target, Layout):
        fmt = target.fmt
        if (width, height) != (fmt.width, fmt.height):
            raise FormatError(
                f"a {width} x {height} pixel page is not the {fmt.width} x {fmt.height} "
                f"pixel page of the {target.dots.name} dot layout on {target.paper.name} paper"
            )
    elif not target.fits_image(width, height):
        raise FormatError(
            f"a {width} x {height} pixel page leaves less than the {MIN_MARGIN_PT:g} pt "
            f"margin on {target.name} paper and would be clipped by the printer"
        )
    return image


def write_pdf(path, pages: Iterable[np.ndarray], paper: Paper | Layout) -> int:
    """Write each page image (0 black / 255 white) as one PDF page; return the count.

    A Paper means its standard layout at 200 pixels per inch; a Layout places
    the page at its own offsets and dot size and refuses any other image size.

    Pages are consumed lazily and written as they arrive. The file is created
    only once the first page has arrived and passed its checks, and it is
    removed again if anything fails after that.

    Raises OptarError if there are no pages, TypeError for a page that is not
    a uint8 numpy array, ValueError for one that is not a non-empty 2-D image,
    and FormatError (a ValueError) for one that, with a Paper, would leave
    less than MIN_MARGIN_PT on any side of the paper or, with a Layout, is not
    exactly the size of the layout's page.
    """
    pages = iter(pages)
    first = next(pages, None)
    if first is None:
        raise OptarError("no pages to write")
    first = _check_page(first, paper)
    f = open(path, "wb")  # opened outside the try: a failed open removes nothing
    try:
        with f:
            return _write(f, first, pages, paper)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(path)
        raise


def _write(f, first: np.ndarray, rest, target: Paper | Layout) -> int:
    paper, x, y, ppi = _placement(target)
    offsets: dict[int, int] = {}
    kids: list[int] = []

    def all_pages():
        yield first
        for image in rest:
            yield _check_page(image, target)

    def emit(num: int, body: bytes) -> None:
        offsets[num] = f.tell()
        f.write(b"%d 0 obj\n" % num + body + b"\nendobj\n")

    def stream_obj(num: int, header: bytes, data: bytes) -> None:
        emit(
            num,
            b"<< " + header + b"/Length %d >>\nstream\n" % len(data) + data + b"\nendstream",
        )

    f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    count = 0
    for image in all_pages():
        height, width = image.shape
        page_n, content_n, image_n = 3 + 3 * count, 4 + 3 * count, 5 + 3 * count
        w = width * POINTS_PER_INCH / ppi
        h = height * POINTS_PER_INCH / ppi
        content = f"q {w:.2f} 0 0 {h:.2f} {x:.2f} {y:.2f} cm /Im0 Do Q".encode()
        packed = np.packbits(image > 127, axis=1).tobytes()
        emit(
            page_n,
            (
                f"<< /Type /Page /Parent {_PAGES} 0 R "
                f"/MediaBox [0 0 {paper.width_pt:g} {paper.height_pt:g}] "
                f"/Contents {content_n} 0 R "
                f"/Resources << /XObject << /Im0 {image_n} 0 R >> >> >>"
            ).encode(),
        )
        stream_obj(content_n, b"", content)
        stream_obj(
            image_n,
            (
                f"/Type /XObject /Subtype /Image /Width {width} /Height {height} "
                "/ColorSpace /DeviceGray /BitsPerComponent 1 "
                "/Interpolate false /Filter /FlateDecode "
            ).encode(),
            zlib.compress(packed, 9),
        )
        kids.append(page_n)
        count += 1

    emit(_CATALOG, b"<< /Type /Catalog /Pages %d 0 R >>" % _PAGES)
    refs = " ".join(f"{k} 0 R" for k in kids)
    emit(_PAGES, f"<< /Type /Pages /Kids [{refs}] /Count {count} >>".encode())

    size = 3 + 3 * count
    xref = f.tell()
    f.write(b"xref\n0 %d\n" % size)
    f.write(b"0000000000 65535 f \n")
    for n in range(1, size):
        f.write(b"%010d 00000 n \n" % offsets[n])
    f.write(b"trailer\n<< /Size %d /Root %d 0 R >>\n" % (size, _CATALOG))
    f.write(b"startxref\n%d\n%%%%EOF\n" % xref)
    return count
