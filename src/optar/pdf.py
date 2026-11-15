# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Print-ready PDF writer: one 1-bit Flate image per page at 200 pixels per inch."""

import zlib
from collections.abc import Iterable

import numpy as np

from optar.format import PIXELS_PER_INCH, Paper

POINTS_PER_INCH = 72
_CATALOG = 1
_PAGES = 2


def write_pdf(path, pages: Iterable[np.ndarray], paper: Paper) -> int:
    """Write each page image (0 black / 255 white) as one PDF page; return the count.

    Pages are consumed lazily and written as they arrive.
    """
    offsets: dict[int, int] = {}
    kids: list[int] = []

    with open(path, "wb") as f:

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
        for image in pages:
            height, width = image.shape
            page_n, content_n, image_n = 3 + 3 * count, 4 + 3 * count, 5 + 3 * count
            w = width * POINTS_PER_INCH / PIXELS_PER_INCH
            h = height * POINTS_PER_INCH / PIXELS_PER_INCH
            x, y = paper.offset_x_pt, paper.offset_y_pt
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
