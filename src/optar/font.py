# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Label font (port of text_block() and label() in optar.c)."""

from __future__ import annotations

from functools import cache
from importlib import resources

import numpy as np
from PIL import Image

from optar.errors import FormatError
from optar.format import TEXT_WIDTH, PageFormat

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


def label_text(fmt: PageFormat, page: int, total: int, label: str) -> str:
    """The label line, truncated as C's snprintf into DATA_WIDTH/TEXT_WIDTH bytes."""
    text = f"  {fmt.to_string()} {page}/{total} {label}"
    return text[: fmt.data_width // TEXT_WIDTH - 1]


def render_label(fmt: PageFormat, text: str) -> np.ndarray:
    """The data-width part of the label band: (text_height, data_width), black background."""
    if fmt.text_height != LABEL_HEIGHT:
        raise FormatError(f"label band must be {LABEL_HEIGHT} rows, not {fmt.text_height}")
    strip = glyph_strip()
    out = np.zeros((fmt.text_height, fmt.data_width), dtype=np.uint8)

    def block(destx: int, srcx: int, width: int) -> None:
        if destx + width > fmt.data_width:
            return
        out[:, destx : destx + width] = strip[:, srcx : srcx + width]

    logo_x = TEXT_WIDTH * GLYPH_CELLS
    x = strip.shape[1] - logo_x
    block(0, logo_x, x)
    for ch in text:
        code = ord(ch)
        if FIRST_CHAR <= code <= 127:
            block(x, TEXT_WIDTH * (code - FIRST_CHAR), TEXT_WIDTH)
            x += TEXT_WIDTH
    return out
