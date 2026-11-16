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

# What the reader and its gates do and do not give.
#
# The cut. The band is white ink on black, sampled from the scan in linear
# light, where blur leaves thin white strokes well below the white of wide
# ones: a cut halfway between the band's darkest and brightest samples thinned
# them, so that every exact reading of a moderately blurred scan failed the
# ink-loss rule (scale 2 with blur 1.0, or scale 3 with blur 1.5, saved as PNG
# and loaded with read_scan). Under heavy noise near black, on the other hand,
# a low cut turns the noise into ink. No single fraction suited both (measured
# 0.10 to 0.50, the darkest and brightest samples or the 1st/99th and
# 2nd/98th percentiles; the percentiles helped nothing), so the band is cut at
# each of BAND_CUTS and the cut whose cells best match glyphs is read. Fixed at
# 0.30 instead, the blurred scans read but blotchy noise of sigma 60 gave 44
# acceptable exact readings in 1600 instead of 1550.
#
# The gates. A reading is plausible when every identity cell matches its glyph
# closely and clearly (MIN_LABEL_CONFIDENCE, MIN_LABEL_MARGIN), and reliable
# when, besides, its strokes are neither thinned nor thickened (MAX_INK_BIAS)
# and no cell is in doubt (_MIN_CLEAR_LEAD and the cells after the text). Both
# are filters, not guarantees: some misreads are indistinguishable from print
# at the level of one cell (a speck the size and place of a ".", a blotch that
# gives ":" the tail of ";"). A tagged label needs only to be plausible,
# because its check code is the error detector: a misread of the size,
# fingerprint, page or total passes it about once in 256, and a misread that
# breaks the tag's form is refused (identify.py). An untagged label has no
# detector and must be reliable.
#
# Evidence (synthetic scans of A4 and Letter; tests/unit/test_label.py has the
# perturbations, applied to the band of a clean scale-3 scan; whole scans went
# through PNG and read_scan). Exact readings reliable, of exact readings:
#   every DEGRADED case, 8 labels, 2 seeds, both papers:      256 of 256
#   scale 2, blur 1.0, noise 0/15/20:  32/32/32 of 32 each (cut halfway: 0)
#   scale 3, blur 1.5, noise 0/15/20:  32/32/32 of 32 each (cut halfway: 0)
#   scale 2, blur 1.5, no noise:       28 of 32; with noise 15 or 20 few
#                                      readings are exact at any cut (8, 3)
#   ramps of 40/80/120 grey levels across the band, noise 20: 1600 of 1600
#   thinned strokes (MinFilter 3, blur 1.0, noise 8): 1600 of 1600 (was 0)
# Wrong readings that were reliable, per 1600 (none a well-formed digit or hex
# substitution in the format string, page numbers or tag; the same as with the
# cut halfway, or fewer):
#   (a) thinned strokes 0; (b) blotchy noise, sigma 60/70/80: 0, 4, 5;
#   (c) a 120/100-level ramp with noise 30/40: 0, 0; (d) half a page pixel
#   off in x: 0, 0; (e) a white speck over the text: 1, always in a blank
#   cell: 21.
# Wrong readings that were only plausible, per 1600: (b) 3, 15, 23; (c) 3, 0;
# (d) 2, 0; (e) 3, 36. Identification accepted 3, 12, 18 (b),
# 1 (c) and 11 (e) of them, every one with the true page, total and tag and a
# name differing in punctuation; it refused the rest.
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
# Highest ink loss and ink gain (see LabelReading). In exact readings: at most
# 0.009 and 0.005 on the blurred scans above; up to 0.097 and 0.060 under
# blotchy noise of sigma 80 and 0.136 under a 120-level ramp with noise 30,
# where some exact readings are rejected; 0.14 for half-pixel offsets (d).
MAX_INK_BIAS = 0.08
# Fractions of the way from the band's darkest to its brightest sample at
# which it is cut (see above).
BAND_CUTS = (0.2, 0.3, 0.4, 0.5)
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
    def plausible(self) -> bool:
        """Every identity cell matches its glyph closely and clearly."""
        return self.confidence >= MIN_LABEL_CONFIDENCE and self.margin >= MIN_LABEL_MARGIN

    @property
    def reliable(self) -> bool:
        """Plausible, and neither the strokes nor any cell cast doubt on it."""
        return (
            self.plausible
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

    The band is cut into ink and background at each fraction in BAND_CUTS
    of the way from its darkest to its brightest sample, and the cut whose
    cells agree best with their best glyphs is read. Each cell is matched
    against every glyph by the fraction of its pixels that agree. A cell's
    margin is the lead of the best glyph over the runner-up, in units of the
    pixels in which those two glyphs differ: 1 when the cell is exactly the
    best glyph, 0 for a tie.

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
    on, off, distance, clear_lead = _glyphs()

    def cut(fraction: float) -> tuple[float, np.ndarray, np.ndarray]:
        """The band cut at a fraction of the way from lo to hi: (agreeing
        pixels summed over every cell's best glyph, cells, agreement table)."""
        white = (band > lo + fraction * (hi - lo)).astype(np.float32)
        # (ncells, text_height * TEXT_WIDTH), rows in the same order as _glyphs().
        cells = white.reshape(fmt.text_height, ncells, TEXT_WIDTH).transpose(1, 0, 2)
        cells = cells.reshape(ncells, -1)
        agree = cells @ on.T + (1 - cells) @ off.T  # agreeing pixels, exact in float32
        return float(agree.max(axis=1).sum()), cells, agree

    # The cut whose cells look most like glyphs; the first of equals.
    _, cells, agree = max((cut(f) for f in BAND_CUTS), key=lambda c: c[0])
    rows = np.arange(ncells)
    order = np.argsort(-agree, axis=1, kind="stable")  # ties go to the lowest code
    best, second = order[:, 0], order[:, 1]
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
