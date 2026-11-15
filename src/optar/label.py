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

# What these thresholds do and do not give. A reading is reliable only if it
# passes all of them; that makes the gate a filter, not a guarantee. Some
# misreads are indistinguishable from print at the level of one cell (a speck
# the size and place of a ".", a blotch that gives ":" the tail of ";"), and
# under harsh conditions up to about one reading in a hundred is accepted
# though wrong. In every condition measured none of those was a well-formed
# substitution (a digit for a digit, a hex digit for a hex digit) in the format
# string, the page numbers or the tag: what was accepted no longer parses or no
# longer matches. Well-formed substitutions are what a check code in the tag
# is for; this gate does not rule them out.
#
# Evidence (synthetic scans of A4 and Letter at scale 3; tests/unit/test_label.py
# has the perturbations). Ordinary scans, every DEGRADED case with five labels
# on both papers (80 readings): all exact and reliable, confidence and margin
# 1.0, ink loss and gain 0, no doubtful cell. Band blur 0.8 with noise 8,
# noise of sigma 60 or blotchy noise of sigma 50 (1600 readings each), a band
# offset of 0.45 page pixel (1040): no wrong reading accepted; at most 9 exact
# readings in 1600 rejected. Wrong readings accepted per 1600 (confidence and
# margin alone -> all rules):
#   (a) band strokes thinned (MinFilter 3, blur 1.0, noise 8):          344 -> 0
#   (b) blotchy noise (blurred over 2 scan pixels), sigma 60, 70, 80:  5, 17, 31 -> 2, 6, 2
#   (c) a 120 or 100 grey-level ramp across the band, noise 30 or 40:   3, 0 -> 0, 0
#   (d) the band sampled half a page pixel off in x, either way:        1, 1 -> 0, 0
#   (e) a white speck of 2-4 page pixels over the text:                 7 -> 2
#       the same speck always in a blank cell:                         57 -> 21
# The price: under (a), (c) and (d) nearly every reading is now rejected, and
# under (b) at sigma 80 three in four.
#
# Lowest best-match score over the identity cells (the cells from the first
# through the last non-space character read): the fraction of a cell's pixels
# that agree with the glyph chosen. Non-labels (pages turned 180 degrees, a
# page located with the other paper's format, random bands): at most 0.404.
MIN_LABEL_CONFIDENCE = 0.90
# Lowest normalised lead of the best glyph over the runner-up over the identity
# cells (1 for a perfect read, 0 for a tie; see read_label). Systematic misreads
# from stroke width or a 2-pixel band shift: at most 0.050.
MIN_LABEL_MARGIN = 0.20
# Highest ink loss and ink gain (see LabelReading). In exact readings that
# confidence and margin accepted: loss at most 0.051 and gain at most 0.031
# under noise of sigma 60, blotchy noise up to sigma 70 and specks; up to
# 0.090 and 0.057 under blotchy noise of sigma 80, and 0.076 under a 100-level
# ramp with noise 30, where some exact readings are now rejected. Thinned
# strokes (a): loss 0.113-0.138; ramps (c) up to 0.21; half-pixel offsets (d)
# 0.12-0.14.
MAX_INK_BIAS = 0.08
# A glyph must beat the blank by max(_MIN_CLEAR_LEAD, half its ink pixels)
# agreeing pixels. The sparsest glyphs have 9 ("`") to 31 (";") ink pixels.
_MIN_CLEAR_LEAD = 6

_LABEL_RE = re.compile(
    rf" *({FORMAT_PATTERN}) ([1-9][0-9]{{0,4}})/(0|[1-9][0-9]{{0,4}})(?: ([ -~]*))?",
    re.ASCII,
)


@dataclass(frozen=True)
class LabelReading:
    text: str  # trailing spaces removed
    confidence: float  # lowest best-match score over the identity cells, 0..1
    margin: float  # lowest normalised lead of the best glyph over the identity cells, 0..1
    # Over the cells read as glyphs: the fraction of the chosen glyphs' ink
    # pixels sampled as background, and of their background pixels sampled as
    # ink. Both near 0 on a good scan; large when strokes come out thinned or
    # thickened, which makes sparse glyphs vanish or appear.
    ink_loss: float = 0.0
    ink_gain: float = 0.0
    # Cells that are neither clearly a glyph nor clearly blank (see read_label).
    doubtful_cells: int = 0

    @property
    def reliable(self) -> bool:
        return (
            self.confidence >= MIN_LABEL_CONFIDENCE
            and self.margin >= MIN_LABEL_MARGIN
            and self.ink_loss <= MAX_INK_BIAS
            and self.ink_gain <= MAX_INK_BIAS
            and self.doubtful_cells == 0
        )


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
def _glyphs() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Glyph bitmaps as rows of 0/1 float32 (cells, h*w), their complements,
    the table of pixel counts in which two glyphs differ, and for each glyph
    the lead in agreeing pixels it needs over the blank (space) glyph to
    count as clearly present: max(_MIN_CLEAR_LEAD, half its ink pixels)."""
    strip = glyph_strip()
    h = strip.shape[0]
    cells = strip[:, : TEXT_WIDTH * GLYPH_CELLS].reshape(h, GLYPH_CELLS, TEXT_WIDTH)
    on = (cells.transpose(1, 0, 2).reshape(GLYPH_CELLS, -1) > 0).astype(np.float32)
    off = 1 - on
    distance = on @ off.T + off @ on.T
    clear_lead = np.maximum(_MIN_CLEAR_LEAD, on.sum(axis=1) / 2)
    return on, off, distance, clear_lead


def read_label(grid: PageGrid) -> LabelReading:
    """Read the label band of a located page.

    Each cell is matched against every glyph by the fraction of its pixels
    that agree. A cell's margin is the lead of the best glyph over the
    runner-up, in units of the pixels in which those two glyphs differ:
    1 when the cell is exactly the best glyph, 0 for a tie.

    A cell is doubtful when it is read as a glyph that does not beat the
    blank by its clear lead, or when it lies after the text and either some
    glyph agrees with it as well as the blank does or its agreement with the
    blank is below MIN_LABEL_CONFIDENCE. A doubtful cell makes the reading
    unreliable; the text is left as read.
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
    on, off, distance, clear_lead = _glyphs()
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

    # Glyph 0 is the space, which is all background.
    glyph = best != 0
    ink, seen = on[best[glyph]], cells[glyph]
    ink_loss = float((ink * (1 - seen)).sum() / ink.sum())
    ink_gain = float(((1 - ink) * seen).sum() / (1 - ink).sum())

    # A cell read as a glyph must beat the blank by that glyph's clear lead,
    # so that a speck or a blotch does not pass for a sparse glyph.
    doubtful = glyph & (agree[rows, best] - agree[:, 0] < clear_lead[best])
    # Nothing else scores the cells after the text, where a lost last
    # character would be: each must read as blank with no glyph tying it, and
    # agree with the blank as well as the identity cells must agree with
    # their glyphs.
    after = rows >= last
    tied = agree[after, 1:].max(axis=1) >= agree[after, 0]
    doubtful[after] = tied | (scores[after] < MIN_LABEL_CONFIDENCE)

    return LabelReading(
        text,
        float(scores[first:last].min()),
        float(margins[first:last].min()),
        ink_loss,
        ink_gain,
        int(doubtful.sum()),
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
