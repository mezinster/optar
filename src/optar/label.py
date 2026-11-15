# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Reading the printed page label back from a located scan.

The encoder draws the label (font.render_label) in the band below the data
area: white glyphs on black, a logo at the left end, then one TEXT_WIDTH-wide
cell per character. The reader samples that band through the page grid and
matches every cell against the glyphs of the same font.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache

import numpy as np

from optar.decoder import PageGrid, page_to_scan
from optar.decoder.crosses import interp
from optar.font import FIRST_CHAR, GLYPH_CELLS, glyph_strip
from optar.format import _FORMAT_RE, TEXT_WIDTH, PageFormat

_LAST_CHAR = FIRST_CHAR + GLYPH_CELLS - 1  # the last readable glyph ("~")

# Lowest best-match score over the label cells for a reading to be trusted.
# Observed on synthetic scans (every DEGRADED case on A4 and Letter, two noise
# seeds, labels showing every printable character): upright pages, 96 scans,
# minimum 0.962 (all read exactly); the same pages turned 180 degrees, whose
# "label band" is then data rows and crosses, 64 scans: maximum 0.404.
# The threshold sits roughly midway.
MIN_LABEL_CONFIDENCE = 0.70

_LABEL_RE = re.compile(
    rf" *({_FORMAT_RE.pattern}) ([0-9]{{1,5}})/([0-9]{{1,5}})(?: (.*))?", re.ASCII
)


@dataclass(frozen=True)
class LabelReading:
    text: str  # trailing spaces removed
    confidence: float  # lowest best-match score over all character cells, 0..1


@dataclass(frozen=True)
class LabelInfo:
    format: str
    page: int
    total: int
    text: str  # the free text after the page numbers, possibly empty


def _logo_width() -> int:
    return glyph_strip().shape[1] - TEXT_WIDTH * GLYPH_CELLS


def label_capacity(fmt: PageFormat) -> int:
    """How many label characters the encoder actually prints on a page."""
    return (fmt.data_width - _logo_width()) // TEXT_WIDTH


def printed_label(fmt: PageFormat, text: str) -> str:
    """The visible part of a label as font.label_text builds it."""
    kept = "".join(ch for ch in text if FIRST_CHAR <= ord(ch) <= _LAST_CHAR)
    return kept[: label_capacity(fmt)].rstrip(" ")


@cache
def _glyphs() -> tuple[np.ndarray, np.ndarray]:
    """Glyph bitmaps as rows of 0/1 (cells, h*w) float32, and their complements."""
    strip = glyph_strip()
    h = strip.shape[0]
    cells = strip[:, : TEXT_WIDTH * GLYPH_CELLS].reshape(h, GLYPH_CELLS, TEXT_WIDTH)
    on = (cells.transpose(1, 0, 2).reshape(GLYPH_CELLS, -1) > 0).astype(np.float32)
    return on, 1 - on


def read_label(grid: PageGrid) -> LabelReading:
    """Read the label band of a located page."""
    fmt = grid.fmt
    logo = _logo_width()
    ncells = label_capacity(fmt)
    xs = np.arange(logo, logo + ncells * TEXT_WIDTH)
    ys = np.arange(fmt.data_height, fmt.data_height + fmt.text_height)
    sx, sy = page_to_scan(grid, xs[None, :], ys[:, None])
    band = interp(grid.cleaned, sx, sy)
    lo, hi = float(band.min()), float(band.max())
    white = (band > (lo + hi) / 2).astype(np.float32)

    # (ncells, text_height * TEXT_WIDTH), rows in the same order as _glyphs().
    cells = white.reshape(fmt.text_height, ncells, TEXT_WIDTH).transpose(1, 0, 2)
    cells = cells.reshape(ncells, -1)
    on, off = _glyphs()
    agree = (cells @ on.T + (1 - cells) @ off.T) / cells.shape[1]
    best = agree.argmax(axis=1)  # ties go to the lowest character code
    scores = agree[np.arange(ncells), best]
    text = "".join(chr(FIRST_CHAR + int(k)) for k in best).rstrip(" ")
    return LabelReading(text, float(scores.min()))


def parse_label(text: str) -> LabelInfo | None:
    """Split a label read from paper into its parts, or None if it has another form."""
    m = _LABEL_RE.fullmatch(text)
    if m is None:
        return None
    return LabelInfo(m[1], int(m[2]), int(m[3]), m[4] or "")
