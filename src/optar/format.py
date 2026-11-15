# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Page format: the geometry and coding parameters of one optar page.

Derived quantities mirror the macros in optar.h. This is the only module
that holds format numbers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from optar.errors import FormatError

PIXELS_PER_INCH = 200
TEXT_WIDTH = 13

_FORMAT_RE = re.compile(r"[0-9]+(?:-[0-9]+){7}")


@dataclass(frozen=True)
class Paper:
    name: str
    width_pt: float
    height_pt: float
    offset_x_pt: float  # from the left edge
    offset_y_pt: float  # from the bottom edge
    xcrosses: int
    ycrosses: int


PAPERS: dict[str, Paper] = {
    "a4": Paper("a4", 595.28, 841.89, 19.22, 17.44, 65, 93),
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
        scale = 72 / PIXELS_PER_INCH
        return (
            paper.offset_x_pt + self.width * scale <= paper.width_pt
            and paper.offset_y_pt + self.height * scale <= paper.height_pt
        )
