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
from optar.errors import FormatError
from optar.font import FIRST_CHAR, GLYPH_CELLS, glyph_strip
from optar.format import FORMAT_PATTERN, TEXT_WIDTH, PageFormat

# The encoder draws (and advances over) every code from FIRST_CHAR to this one.
# The last code is not a glyph but a slice of the logo, so a label containing
# it cannot be read back exactly: that cell reads as some other character.
_LAST_DRAWN = FIRST_CHAR + GLYPH_CELLS

# Both thresholds apply to the identity cells: the cells from the first through
# the last non-space character read. Evidence from synthetic scans of A4 and
# Letter (every DEGRADED case, stroke width changed by Min/MaxFilter 3-7, the
# band shifted 1-2 scan pixels against the crosses with blur and noise, noise
# of sigma 40-250 added to the band after locating, 3600 noisy readings):
#
# Lowest best-match score (fraction of a cell's pixels that agree with the glyph
# chosen); 1 - confidence bounds the noise in the worst cell. Exact reads in the
# DEGRADED cases: minimum 0.962; with band noise up to sigma 60: minimum 0.952.
# Non-labels (pages turned 180 degrees, a page located with the other paper's
# format, random bands): maximum 0.404. Under heavy noise (sigma 90-135) a
# blank cell after the text can read as a sparse glyph ("`", ".") with a margin
# up to 0.333; those readings had confidence at most 0.878. The threshold is
# set above them: the margin on that side is thin (0.022).
MIN_LABEL_CONFIDENCE = 0.90
# Lowest normalised lead of the best glyph over the runner-up (1 for a perfect
# read, 0 for a tie; see read_label). Exact reads in the DEGRADED cases, under
# a 1-pixel band shift and in full-width labels: 1.0; with band noise up to
# sigma 60: minimum 0.429. Systematic misreads (stroke width, 2-pixel band
# shift): maximum 0.050.
MIN_LABEL_MARGIN = 0.20

_LABEL_RE = re.compile(
    rf" *({FORMAT_PATTERN}) ([1-9][0-9]{{0,4}})/(0|[1-9][0-9]{{0,4}})(?: ([ -~]*))?",
    re.ASCII,
)


@dataclass(frozen=True)
class LabelReading:
    text: str  # trailing spaces removed
    confidence: float  # lowest best-match score over the identity cells, 0..1
    margin: float  # lowest normalised lead of the best glyph over the identity cells, 0..1

    @property
    def reliable(self) -> bool:
        return self.confidence >= MIN_LABEL_CONFIDENCE and self.margin >= MIN_LABEL_MARGIN


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
    """The visible part of a label as font.label_text builds it.

    Characters the encoder skips are removed; the logo-slice code is kept,
    since it takes a cell, though it cannot be read back as itself.
    """
    kept = "".join(ch for ch in text if FIRST_CHAR <= ord(ch) <= _LAST_DRAWN)
    return kept[: label_capacity(fmt)].rstrip(" ")


@cache
def _glyphs() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Glyph bitmaps as rows of 0/1 float32 (cells, h*w), their complements,
    and the table of pixel counts in which two glyphs differ."""
    strip = glyph_strip()
    h = strip.shape[0]
    cells = strip[:, : TEXT_WIDTH * GLYPH_CELLS].reshape(h, GLYPH_CELLS, TEXT_WIDTH)
    on = (cells.transpose(1, 0, 2).reshape(GLYPH_CELLS, -1) > 0).astype(np.float32)
    off = 1 - on
    distance = on @ off.T + off @ on.T
    return on, off, distance


def read_label(grid: PageGrid) -> LabelReading:
    """Read the label band of a located page.

    Each cell is matched against every glyph by the fraction of its pixels
    that agree. A cell's margin is the lead of the best glyph over the
    runner-up, in units of the pixels in which those two glyphs differ:
    1 when the cell is exactly the best glyph, 0 for a tie.
    """
    fmt = grid.fmt
    strip_height = glyph_strip().shape[0]
    if fmt.text_height != strip_height:
        raise FormatError(
            f"cannot read a label band of {fmt.text_height} rows; the font is {strip_height}"
        )
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
    on, off, distance = _glyphs()
    agree = cells @ on.T + (1 - cells) @ off.T  # agreeing pixels, exact in float32
    order = np.argsort(-agree, axis=1, kind="stable")  # ties go to the lowest code
    best, second = order[:, 0], order[:, 1]
    rows = np.arange(ncells)
    scores = agree[rows, best] / cells.shape[1]
    margins = (agree[rows, best] - agree[rows, second]) / distance[best, second]

    chars = "".join(chr(FIRST_CHAR + int(k)) for k in best)
    text = chars.rstrip(" ")
    first, last = len(chars) - len(chars.lstrip(" ")), len(text)
    if first >= last:
        return LabelReading(text, 0.0, 0.0)
    return LabelReading(
        text, float(scores[first:last].min()), float(margins[first:last].min())
    )


def parse_label(text: str) -> LabelInfo | None:
    """Split a label read from paper into its parts, or None if it has another form.

    Only the form the encoder prints is accepted: no leading zeros in the page
    numbers, page from 1, printable ASCII only. Page > total is not checked.
    """
    m = _LABEL_RE.fullmatch(text)
    if m is None:
        return None
    return LabelInfo(m[1], int(m[2]), int(m[3]), m[4] or "")
