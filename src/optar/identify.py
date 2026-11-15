# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Identifying a scan: its paper, which way up it is, and which page it is.

Rotations count counter-clockwise quarter turns that make a scan upright:
upright = np.rot90(image, rotation). The corner finder cannot find the
right-hand corners of an image wider than it is tall, so a landscape image
is only tried turned by a quarter turn either way.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from optar.decoder import PageGrid, PageResult, decode_located, locate_page
from optar.decoder.dirt import remove_border_dirt
from optar.decoder.geometry import find_corners
from optar.decoder.levels import analyze_levels
from optar.decoder.options import DecodeOptions
from optar.encoder import MAX_PAGES
from optar.errors import DecodeError, IdentifyError
from optar.format import PAPERS, PageFormat, Paper
from optar.label import parse_label, read_label
from optar.tag import Tag, split_label

__all__ = ["ScanIdentity", "candidate_rotations", "decode_unlabelled", "identify_scan"]

NO_PAGE = "no page found"
LABEL_UNREADABLE = "label unreadable"


@dataclass(frozen=True)
class ScanIdentity:
    paper: Paper
    fmt: PageFormat
    rotation: int  # counter-clockwise quarter turns that make the scan upright
    page: int
    total: int
    tag: Tag | None
    name: str  # the free text after the tag (all of it without a tag), as read
    confidence: float  # the label reading's, as LabelReading
    margin: float
    grid: PageGrid  # located on the upright image


def candidate_rotations(image: np.ndarray) -> tuple[int, ...]:
    """The rotations to try: those that leave the image at least as tall as wide."""
    h, w = image.shape[:2]
    return (0, 2) if h >= w else (1, 3)


def _check(image: np.ndarray) -> np.ndarray:
    image = np.asarray(image)
    if image.ndim != 2 or image.dtype != np.uint8:
        raise DecodeError(
            f"scan must be a 2-D uint8 grey image, got shape {image.shape} dtype {image.dtype}"
        )
    return image


def _turn(image: np.ndarray, rotation: int) -> np.ndarray:
    return np.ascontiguousarray(np.rot90(image, rotation))


def _outline(upright: np.ndarray, options: DecodeOptions | None = None) -> np.ndarray | None:
    """The page's corners (UL, UR, LL, LR as x, y), found without a format, or None."""
    if upright.size == 0:
        return None
    levels = analyze_levels(upright, options or DecodeOptions())
    cleaned = remove_border_dirt(upright, levels.fill_cut)
    try:
        return find_corners(cleaned, levels.cut)
    except DecodeError:
        return None


def _papers_by_shape(corners: np.ndarray) -> list[Paper]:
    """The paper presets, closest width-to-height ratio to the outline's first."""
    ul, ur, ll, lr = corners.astype(np.float64)
    width = (np.hypot(*(ur - ul)) + np.hypot(*(lr - ll))) / 2
    height = (np.hypot(*(ll - ul)) + np.hypot(*(lr - ur))) / 2
    if height == 0:
        return list(PAPERS.values())
    ratio = width / height

    def distance(paper: Paper) -> float:
        fmt = PageFormat.for_paper(paper)
        return abs(ratio - fmt.width / fmt.height)

    return sorted(PAPERS.values(), key=distance)


def _identify_upright(
    upright: np.ndarray, rotation: int, paper: Paper, options: DecodeOptions | None
) -> ScanIdentity | None:
    fmt = PageFormat.for_paper(paper)
    try:
        grid = locate_page(upright, fmt, options)
    except DecodeError:
        return None
    reading = read_label(grid)
    if not reading.reliable:
        return None
    info = parse_label(reading.text)
    if info is None or info.format != fmt.to_string():
        return None
    # The page count is untrusted: the encoder never writes more than MAX_PAGES.
    if info.total > MAX_PAGES or not 1 <= info.page <= min(max(info.total, 1), MAX_PAGES):
        return None
    tag, name = split_label(info.text)
    if tag is not None and not tag.fits(info.total, fmt):
        return None
    return ScanIdentity(
        paper, fmt, rotation, info.page, info.total, tag, name,
        reading.confidence, reading.margin, grid,
    )


def identify_scan(image: np.ndarray, options: DecodeOptions | None = None) -> ScanIdentity:
    """Work out a scan's paper, rotation and page from its printed label.

    Raises IdentifyError("no page found") when no candidate rotation shows a
    page outline, else IdentifyError("label unreadable") when no rotation and
    paper give a label that reads reliably, parses, carries the paper's own
    format string, a page number within the total, a total the encoder could
    have written (at most MAX_PAGES) and a tag (if any) that fits the total.
    """
    image = _check(image)
    rotations = candidate_rotations(image)
    views: dict[int, tuple[np.ndarray, np.ndarray | None]] = {}

    def view(rotation: int) -> tuple[np.ndarray, np.ndarray | None]:
        """The upright image for a rotation and its page outline, found once."""
        if rotation not in views:
            upright = _turn(image, rotation)
            views[rotation] = upright, _outline(upright, options)
        return views[rotation]

    outline = next((c for r in rotations if (c := view(r)[1]) is not None), None)
    if outline is None:
        raise IdentifyError(NO_PAGE)
    # The likelier paper in every orientation before the other paper: a page
    # turned the wrong way costs one locate, not one per paper.
    for paper in _papers_by_shape(outline):
        for rotation in rotations:
            upright, corners = view(rotation)
            if corners is None:
                continue
            ident = _identify_upright(upright, rotation, paper, options)
            if ident is not None:
                return ident
    raise IdentifyError(LABEL_UNREADABLE)


def _corrected_bits(result: PageResult) -> int:
    return sum(i * n for i, n in enumerate(result.stats.error_histogram))


def decode_unlabelled(
    image: np.ndarray,
    fmt: PageFormat,
    options: DecodeOptions | None = None,
    *,
    detail: bool = False,
) -> tuple[int, PageResult]:
    """Decode a scan whose label cannot be read, in the rotation that decodes best.

    Every candidate rotation is decoded; the one with the fewest
    unrecoverable symbols wins, then the fewest corrected bits, then the
    lower rotation. Returns (rotation, result). Raises DecodeError (the last
    rotation's) when no rotation decodes.
    """
    image = _check(image)
    best: tuple[tuple[int, int, int], PageResult] | None = None
    error: DecodeError | None = None
    for rotation in candidate_rotations(image):
        try:
            result = decode_located(
                locate_page(_turn(image, rotation), fmt, options), detail=detail
            )
        except DecodeError as e:
            error = e
            continue
        key = (result.stats.uncorrectable, _corrected_bits(result), rotation)
        if best is None or key < best[0]:
            best = (key, result)
    if best is None:
        assert error is not None
        raise DecodeError(*error.args) from error
    return best[0][2], best[1]
