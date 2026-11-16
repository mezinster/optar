# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Page format: the geometry and coding parameters of one optar page.

Derived quantities mirror the macros in optar.h. This is the only module
that holds format numbers.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from fractions import Fraction

from optar.errors import FormatError

PIXELS_PER_INCH = 200
POINTS_PER_INCH = 72
TEXT_WIDTH = 13
# Smallest margin, on every side, that a printer can be trusted not to clip.
MIN_MARGIN_PT = 12.0

# A format string: eight dash-separated non-negative decimal integers.
FORMAT_PATTERN = r"[0-9]+(?:-[0-9]+){7}"
_FORMAT_RE = re.compile(FORMAT_PATTERN)


@dataclass(frozen=True)
class Paper:
    name: str
    width_pt: float
    height_pt: float
    offset_x_pt: float  # from the left edge
    offset_y_pt: float  # from the bottom edge
    xcrosses: int
    ycrosses: int

    def margins_for(self, width_px: int, height_px: int) -> tuple[float, float, float, float]:
        """Margins (left, bottom, right, top) in points around an image of the
        given pixel size placed at this paper's offsets at PIXELS_PER_INCH."""
        scale = POINTS_PER_INCH / PIXELS_PER_INCH
        return (
            self.offset_x_pt,
            self.offset_y_pt,
            self.width_pt - self.offset_x_pt - width_px * scale,
            self.height_pt - self.offset_y_pt - height_px * scale,
        )

    def fits_image(self, width_px: int, height_px: int) -> bool:
        """True if every margin around the placed image is at least MIN_MARGIN_PT."""
        return min(self.margins_for(width_px, height_px)) >= MIN_MARGIN_PT


# Image offsets must be whole multiples of 72/600 pt (one 600 dpi printer dot)
# so that the image edges fall on device-pixel boundaries and each data pixel
# prints as exactly 3 x 3 dots. pgm2ps placed A4 at 19.22, 17.44, which is off
# that grid (160.17, 145.33 dots), and a rasteriser filling every partly
# covered pixel then paints an extra column and row; A4 is snapped to 160 and
# 145 dots. Letter's 19.08, 18.36 (159, 153 dots) are already on the grid.
PAPERS: dict[str, Paper] = {
    "a4": Paper("a4", 595.28, 841.89, 19.20, 17.40, 65, 93),
    "letter": Paper("letter", 612, 792, 19.08, 18.36, 67, 87),
}


def get_paper(name: str) -> Paper:
    try:
        return PAPERS[name.lower()]
    except KeyError:
        raise FormatError(f"unknown paper {name!r}; known: {', '.join(PAPERS)}") from None


@dataclass(frozen=True)
class PageFormat:
    xcrosses: int
    ycrosses: int
    cpitch: int = 24
    chalf: int = 3
    fec_order: int = 1
    border: int = 2
    text_height: int = 24
    version: int = 0

    def __post_init__(self) -> None:
        checks = [
            (self.version == 0, "version must be 0"),
            (1 <= self.fec_order <= 5, "fec_order must be 1..5"),
            (self.xcrosses >= 2, "xcrosses must be >= 2"),
            (self.ycrosses >= 2, "ycrosses must be >= 2"),
            (self.chalf >= 1, "chalf must be >= 1"),
            (self.cpitch > 2 * self.chalf, "cpitch must exceed 2*chalf"),
            (self.border >= 1, "border must be >= 1"),
            (self.text_height >= 1, "text_height must be >= 1"),
        ]
        for ok, message in checks:
            if not ok:
                raise FormatError(f"invalid page format: {message}")

    @property
    def data_width(self) -> int:
        return self.cpitch * (self.xcrosses - 1) + 2 * self.chalf

    @property
    def data_height(self) -> int:
        return self.cpitch * (self.ycrosses - 1) + 2 * self.chalf

    @property
    def width(self) -> int:
        return 2 * self.border + self.data_width

    @property
    def height(self) -> int:
        return 2 * self.border + self.data_height + self.text_height

    @property
    def narrow_height(self) -> int:
        return 2 * self.chalf

    @property
    def gap_width(self) -> int:
        return self.cpitch - 2 * self.chalf

    @property
    def narrow_width(self) -> int:
        return self.gap_width * (self.xcrosses - 1)

    @property
    def narrow_pixels(self) -> int:
        return self.narrow_height * self.narrow_width

    @property
    def wide_height(self) -> int:
        return self.gap_width

    @property
    def wide_width(self) -> int:
        return self.width - 2 * self.border

    @property
    def wide_pixels(self) -> int:
        return self.wide_height * self.wide_width

    @property
    def rep_height(self) -> int:
        return self.narrow_height + self.wide_height

    @property
    def rep_pixels(self) -> int:
        return self.wide_pixels + self.narrow_pixels

    @property
    def total_bits(self) -> int:
        return self.rep_pixels * (self.ycrosses - 1) + self.narrow_pixels

    @property
    def fec_largebits(self) -> int:
        return 24 if self.fec_order == 1 else 1 << self.fec_order

    @property
    def fec_smallbits(self) -> int:
        if self.fec_order == 1:
            return 12
        return self.fec_largebits - 1 - self.fec_order

    @property
    def fec_syms(self) -> int:
        return self.total_bits // self.fec_largebits

    @property
    def net_bits(self) -> int:
        return self.fec_syms * self.fec_smallbits

    @property
    def used_bits(self) -> int:
        return self.fec_syms * self.fec_largebits

    @classmethod
    def parse(cls, text: str) -> PageFormat:
        if not _FORMAT_RE.fullmatch(text):
            raise FormatError(f"page format must be eight dash-separated integers: {text!r}")
        version, xcrosses, ycrosses, cpitch, chalf, fec_order, border, text_height = (
            int(part) for part in text.split("-")
        )
        return cls(
            xcrosses=xcrosses,
            ycrosses=ycrosses,
            cpitch=cpitch,
            chalf=chalf,
            fec_order=fec_order,
            border=border,
            text_height=text_height,
            version=version,
        )

    def to_string(self) -> str:
        return "-".join(
            str(n)
            for n in (
                self.version,
                self.xcrosses,
                self.ycrosses,
                self.cpitch,
                self.chalf,
                self.fec_order,
                self.border,
                self.text_height,
            )
        )

    @classmethod
    def for_paper(cls, paper: Paper) -> PageFormat:
        return cls(xcrosses=paper.xcrosses, ycrosses=paper.ycrosses)

    def fits(self, paper: Paper) -> bool:
        """True if the page image leaves at least MIN_MARGIN_PT on every side of paper."""
        return paper.fits_image(self.width, self.height)


@dataclass(frozen=True)
class DotSize:
    name: str  # "standard" | "medium" | "big" | "large" | "xlarge"
    printer_dots: int  # width of one data dot in 600 dpi printer dots

    @property
    def scale(self) -> Fraction:
        """Printed size of a data dot relative to the standard 1/200 inch."""
        return Fraction(self.printer_dots, 3)


DOT_SIZES: dict[str, DotSize] = {
    "standard": DotSize("standard", 3),
    "medium": DotSize("medium", 4),
    "big": DotSize("big", 5),
    "large": DotSize("large", 6),
    "xlarge": DotSize("xlarge", 9),
}

# Reed-Solomon parity bytes per codeword, and the container's fixed numbers.
PARITY: dict[str, int] = {"none": 0, "standard": 32, "high": 64}
HEADER_SIZE = 38
HEADER_COPIES = 5
SPREAD_STEP = 7919
CODEWORD = 255

# One printer device dot at 600 dpi, in points.
_DEVICE_DOT_PT = POINTS_PER_INCH / 600


@dataclass(frozen=True)
class Layout:
    paper: Paper
    dots: DotSize
    xcrosses: int
    ycrosses: int
    offset_x_pt: float
    offset_y_pt: float

    @property
    def fmt(self) -> PageFormat:
        return PageFormat(xcrosses=self.xcrosses, ycrosses=self.ycrosses)

    @property
    def pixels_per_inch(self) -> Fraction:
        return Fraction(600, self.dots.printer_dots)

    def margins(self) -> tuple[float, float, float, float]:
        """Margins (left, bottom, right, top) in points around the placed image."""
        fmt = self.fmt
        unit = POINTS_PER_INCH * self.dots.printer_dots / 600
        return (
            self.offset_x_pt,
            self.offset_y_pt,
            self.paper.width_pt - self.offset_x_pt - fmt.width * unit,
            self.paper.height_pt - self.offset_y_pt - fmt.height * unit,
        )

    @property
    def scan_dpi(self) -> int:
        """The advised scan resolution: three scan pixels per printed dot."""
        return 1800 // self.dots.printer_dots


def _centred_offset(free_pt: float) -> float:
    """Half of free_pt, rounded down to a whole 600 dpi device dot."""
    return math.floor(free_pt / 2 / _DEVICE_DOT_PT + 1e-9) * _DEVICE_DOT_PT


def _fitted_layout(paper: Paper, dots: DotSize) -> Layout:
    """The largest grid that leaves MIN_MARGIN_PT on every side, centred."""
    unit = POINTS_PER_INCH * dots.printer_dots / 600
    probe = PageFormat(xcrosses=2, ycrosses=2)
    pitch = probe.cpitch * unit
    # width = 2*border + cpitch*(x-1) + 2*chalf; height adds text_height
    base_x = probe.width * unit - pitch
    base_y = probe.height * unit - pitch
    x = math.floor((paper.width_pt - 2 * MIN_MARGIN_PT - base_x) / pitch + 1e-9) + 1
    y = math.floor((paper.height_pt - 2 * MIN_MARGIN_PT - base_y) / pitch + 1e-9) + 1
    fmt = PageFormat(xcrosses=x, ycrosses=y)
    return Layout(
        paper,
        dots,
        x,
        y,
        _centred_offset(paper.width_pt - fmt.width * unit),
        _centred_offset(paper.height_pt - fmt.height * unit),
    )


def _build_layouts() -> dict[tuple[str, str], Layout]:
    layouts: dict[tuple[str, str], Layout] = {}
    for paper in PAPERS.values():
        for dots in DOT_SIZES.values():
            if dots.printer_dots == 3:
                layout = Layout(
                    paper,
                    dots,
                    paper.xcrosses,
                    paper.ycrosses,
                    paper.offset_x_pt,
                    paper.offset_y_pt,
                )
            else:
                layout = _fitted_layout(paper, dots)
            layouts[(paper.name, dots.name)] = layout
    return layouts


LAYOUTS: dict[tuple[str, str], Layout] = _build_layouts()


def get_layout(paper: str, dots: str = "standard") -> Layout:
    key = (get_paper(paper).name, dots.lower())
    try:
        return LAYOUTS[key]
    except KeyError:
        raise FormatError(f"unknown dot size {dots!r}; known: {', '.join(DOT_SIZES)}") from None


def layout_for_format(format: str) -> Layout | None:
    """The layout whose page format string is `format`, or None."""
    for layout in LAYOUTS.values():
        if layout.fmt.to_string() == format:
            return layout
    return None
