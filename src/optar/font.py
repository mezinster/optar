# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Label font (port of text_block() and label() in optar.c)."""

from __future__ import annotations

from functools import cache
from importlib import resources

import numpy as np
from PIL import Image

from optar.errors import FormatError, error
from optar.format import TEXT_WIDTH, Layout, PageFormat

FIRST_CHAR = 32  # first glyph in the strip (space)
GLYPH_CELLS = 127 - FIRST_CHAR  # 95 glyph cells; the logo follows them
LABEL_HEIGHT = 24  # the only strip height the label code supports


@cache
def _strip() -> np.ndarray:
    with resources.files("optar").joinpath("data", "font.png").open("rb") as f:
        img = Image.open(f)
        img.load()
    arr = np.where(np.array(img.convert("L")) >= 128, 255, 0).astype(np.uint8)
    arr.setflags(write=False)
    return arr


def glyph_strip() -> np.ndarray:
    """The font strip: (24, 1500) uint8 of 0 or 255 (read-only)."""
    return _strip()


def label_text(fmt: PageFormat, page: int, total: int, label: str, width: int | None = None) -> str:
    """The label line, truncated as C's snprintf into DATA_WIDTH/TEXT_WIDTH bytes.

    `width` is the width of the band the line is drawn in, in label pixels;
    it is the page's data width unless the line is drawn finer than the page.
    """
    text = f"  {fmt.to_string()} {page}/{total} {label}"
    return text[: (fmt.data_width if width is None else width) // TEXT_WIDTH - 1]


def render_line(text: str, width: int) -> np.ndarray:
    """The logo and `text` on a black strip: (LABEL_HEIGHT, width), 0 or 255.

    A glyph that would cross the right edge is left out, as in C.
    """
    strip = glyph_strip()
    out = np.zeros((LABEL_HEIGHT, width), dtype=np.uint8)

    def block(destx: int, srcx: int, w: int) -> None:
        if destx + w > width:
            return
        out[:, destx : destx + w] = strip[:, srcx : srcx + w]

    logo_x = TEXT_WIDTH * GLYPH_CELLS
    x = strip.shape[1] - logo_x
    block(0, logo_x, x)
    for ch in text:
        code = ord(ch)
        if FIRST_CHAR <= code <= 127:
            block(x, TEXT_WIDTH * (code - FIRST_CHAR), TEXT_WIDTH)
            x += TEXT_WIDTH
    return out


def render_label(fmt: PageFormat, text: str) -> np.ndarray:
    """The data-width part of the label band: (text_height, data_width), black background."""
    if fmt.text_height != LABEL_HEIGHT:
        raise error(
            FormatError, "err.label_band", "label band must be {rows} rows, not {height}",
            rows=LABEL_HEIGHT, height=fmt.text_height,
        )
    return render_line(text, fmt.data_width)


def fine_label(layout: Layout, page: int, total: int, label: str) -> np.ndarray | None:
    """The label line of a page with larger dots, drawn at the standard dot size.

    A page's own label is drawn in its data dots, so it grows with them and
    holds fewer characters. This strip is printed over it instead (see
    write_pdf): its pixels are standard dots whatever the layout, so the text
    keeps one printed size and the whole width of the band holds text. None
    for a standard-dot layout, whose own label is already this size.
    """
    if layout.dots.is_standard:
        return None
    fmt = layout.fmt
    width = int(fmt.data_width * layout.dots.scale)
    return render_line(label_text(fmt, page, total, label, width), width)
