# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Identifying a scan: its paper, dot size, which way up it is, and which page it is.

Rotations count counter-clockwise quarter turns that make a scan upright:
upright = np.rot90(image, rotation). The corner finder cannot find the
right-hand corners of an image wider than it is tall, so a landscape image
is only tried turned by a quarter turn either way.

A 0.2.0 page says what it is in its label; a version-1 page in the header
copies in its data, which only a decode can read.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from optar.container import Header, PagePayload, document_plan, page_payload, read_header
from optar.decoder import PageGrid, PageResult, decode_located, locate_page
from optar.decoder.dirt import isolate_page
from optar.decoder.geometry import find_corners
from optar.decoder.levels import analyze_levels
from optar.decoder.options import DecodeOptions
from optar.encoder import MAX_PAGES
from optar.errors import DecodeError, IdentifyError
from optar.format import (
    LAYOUTS,
    PAPERS,
    Layout,
    PageFormat,
    Paper,
    get_layout,
)
from optar.label import parse_label, read_label
from optar.tag import Tag, damaged_tag, split_label

__all__ = [
    "ScanIdentity",
    "candidate_rotations",
    "decode_unlabelled",
    "identify_any",
    "identify_scan",
    "scan_dpi",
]

NO_PAGE = "no page found"
LABEL_UNREADABLE = "label unreadable"

# A located grid whose crosses lie off the line through their neighbours, by
# more than one data dot (and at least _OFF_LINE_PX pixels), at more than
# this share of the crosses was laid on a page of another grid: it is not
# decoded. Measured on simulated scans: at most 4% for the page's own grid,
# 79% or more for a grid whose cross pitch is not a multiple of the page's.
_OFF_LINE_SHARE = 0.5
_OFF_LINE_PX = 1.5
# Every layout of the paper closest to the outline's shape is decoded for a
# header; a layout of another paper only if its width-to-height ratio is
# within this relative distance of the outline's. Shape only orders the
# candidates of the closest paper, so no stretch rules out its own layouts.
# Rollers stretch a page in one axis, which moves its ratio by about the
# stretch: enlarging an axis by s moves it by s / (1 + s), shrinking one by
# s / (1 - s), which is more. Measured on simulated scans of all ten layouts
# (blur 1.8, at the advised resolution), the distance of a page from its own
# layout was 0.0000 to 0.0005 undistorted, 0.056 to 0.061 with one axis
# enlarged by 6%, 0.060 to 0.065 with one shrunk by 6% (the worst, 0.0647,
# for a vertical shrink) and 0.060 to 0.070 at 6.5% (0.0701 for a vertical
# shrink). So with this value a page distorted by up to 6% in either axis
# and either direction that makes the other paper look closer still has its
# own layouts tried, with 0.005 to spare. The same scans, undistorted, were
# 0.067 (A4 medium against Letter large), 0.071 to 0.072 (A4 big and large,
# Letter large) and 0.081 to 0.099 (the rest) from the nearest layout of the
# other paper: one layout of the other paper is within the tolerance of an
# undistorted A4 medium page, and others come within it for a page distorted
# towards them. That costs time only, and only for a page not found on the
# closest paper, which is tried first.
_OTHER_PAPER_TOLERANCE = 0.07


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
    layout: Layout | None = None
    header: Header | None = None  # set for a version-1 page
    payload: PagePayload | None = None  # set with header: the page is already decoded
    result: PageResult | None = None  # set with header (decoded with detail=True)
    scan_dpi: float | None = None  # estimated resolution of the scan
    # "ordinary", or "slow" for a page read by decoder.soft (identify_coarse).
    reader: str = "ordinary"


def scan_dpi(grid: PageGrid, layout: Layout) -> float:
    """Scan pixels per inch: the mean distance between neighbouring cross
    centres, per cross pitch, times the layout's printed pixels per inch."""
    p = np.asarray(grid.positions, dtype=np.float64)
    steps = [np.hypot(*np.moveaxis(np.diff(p, axis=a), -1, 0)).ravel() for a in (0, 1)]
    spacing = float(np.concatenate(steps).mean())
    return spacing / layout.fmt.cpitch * float(layout.pixels_per_inch)


def _regular(grid: PageGrid) -> bool:
    """True unless most crosses lie off the line through their neighbours.

    A grid of the wrong size is still located, its crosses pulled to whatever
    lies near their places; only a decode would show that its data is noise.
    This check rejects most such grids first. It is a speed check, not a
    guard: a grid it lets through yields a page only with a valid header.
    """
    p = np.asarray(grid.positions, dtype=np.float64)
    if min(p.shape[:2]) < 3:
        return True
    across = p[2:] - 2 * p[1:-1] + p[:-2]
    down = p[:, 2:] - 2 * p[:, 1:-1] + p[:, :-2]
    off = np.concatenate([np.hypot(*np.moveaxis(d, -1, 0)).ravel() for d in (across, down)])
    steps = [np.hypot(*np.moveaxis(np.diff(p, axis=a), -1, 0)).ravel() for a in (0, 1)]
    dot = float(np.concatenate(steps).mean()) / grid.fmt.cpitch
    return float(np.mean(off > max(_OFF_LINE_PX, dot))) <= _OFF_LINE_SHARE


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
    cleaned = isolate_page(upright, levels.fill_cut)
    try:
        return find_corners(cleaned, levels.cut)
    except DecodeError:
        return None


def _size(corners: np.ndarray) -> tuple[float, float]:
    """The outline's width and height in pixels: the means of opposite sides."""
    ul, ur, ll, lr = corners.astype(np.float64)
    width = (np.hypot(*(ur - ul)) + np.hypot(*(lr - ll))) / 2
    height = (np.hypot(*(ll - ul)) + np.hypot(*(lr - ur))) / 2
    return float(width), float(height)


def _shape_distance(corners: np.ndarray, fmt: PageFormat) -> float:
    width, height = _size(corners)
    return abs(width / height - fmt.width / fmt.height)


def _papers_by_shape(corners: np.ndarray) -> list[Paper]:
    """The paper presets, closest width-to-height ratio to the outline's first."""
    if _size(corners)[1] == 0:
        return list(PAPERS.values())
    return sorted(PAPERS.values(), key=lambda p: _shape_distance(corners, PageFormat.for_paper(p)))


def _relative_shape_distance(corners: np.ndarray, fmt: PageFormat) -> float:
    width, height = _size(corners)
    return abs((width / height) / (fmt.width / fmt.height) - 1)


def _layouts_by_shape(corners: np.ndarray, paper: Paper) -> list[Layout]:
    """The layouts of paper to decode for a header, closest shape first (equal
    shapes in DOT_SIZES order): all of them if paper has the layout closest
    to the outline's shape, else those within _OTHER_PAPER_TOLERANCE."""
    layouts = [layout for layout in LAYOUTS.values() if layout.paper is paper]
    if _size(corners)[1] == 0:
        return layouts
    layouts.sort(key=lambda layout: _shape_distance(corners, layout.fmt))
    closest = min(LAYOUTS.values(), key=lambda layout: _shape_distance(corners, layout.fmt))
    if closest.paper is paper:
        return layouts
    return [
        layout for layout in layouts
        if _relative_shape_distance(corners, layout.fmt) <= _OTHER_PAPER_TOLERANCE
    ]


def _outline_dpi(corners: np.ndarray) -> float:
    """The scan's resolution from its outline: its width in pixels over the
    printed width, in inches, of the closest paper's standard page (every dot
    size prints within a few percent of that width)."""
    layout = get_layout(_papers_by_shape(corners)[0].name)
    return _size(corners)[0] / (layout.fmt.width / float(layout.pixels_per_inch))


def _locate(upright: np.ndarray, fmt: PageFormat, options: DecodeOptions | None):
    try:
        return locate_page(upright, fmt, options)
    except DecodeError:
        return None


def _identify_upright(
    upright: np.ndarray, rotation: int, paper: Paper, options: DecodeOptions | None
) -> ScanIdentity | None:
    """The 0.2.0 identity of a standard-dot page from its label, or None."""
    grid = _locate(upright, PageFormat.for_paper(paper), options)
    return None if grid is None else _identify_label(grid, rotation, paper)


def _identify_label(grid: PageGrid, rotation: int, paper: Paper) -> ScanIdentity | None:
    fmt = PageFormat.for_paper(paper)
    reading = read_label(grid)
    if not reading.plausible:
        return None
    info = parse_label(reading.text)
    if info is None or info.format != fmt.to_string():
        return None
    # The page count is untrusted: the encoder never writes more than MAX_PAGES.
    if info.total > MAX_PAGES or not 1 <= info.page <= min(max(info.total, 1), MAX_PAGES):
        return None
    tag, check, name = split_label(info.text)
    if tag is not None:
        # The check covers the size, fingerprint, page number and count as
        # read: a misread digit that still leaves a well-formed label is
        # caught here, so a plausible reading is enough.
        if not (tag.fits(info.total, fmt) and tag.check(info.page, info.total) == check):
            return None
    # Without a tag nothing checks the reading but the stroke and cell rules;
    # and a tag that a misread has broken must not pass for a name.
    elif not reading.reliable or damaged_tag(info.text, info.page, info.total, fmt):
        return None
    return ScanIdentity(
        paper, fmt, rotation, info.page, info.total, tag, name,
        reading.confidence, reading.margin, grid, layout=get_layout(paper.name),
    )


def _header_fits(header: Header, fmt: PageFormat) -> bool:
    """True if a header describes a document wrap() could have written in fmt
    (container.document_plan)."""
    return document_plan(header, fmt) is not None


def _identify_header(
    upright: np.ndarray,
    rotation: int,
    layout: Layout,
    options: DecodeOptions | None,
    grid: PageGrid | None = None,
) -> ScanIdentity | None:
    """The version-1 identity of a page from the header in its data, or None.

    Locates the page (unless given its grid), skips a grid that is not
    _regular, decodes it and accepts a header that _header_fits.
    """
    if grid is None:
        grid = _locate(upright, layout.fmt, options)
    if grid is None or not _regular(grid):
        return None
    result = decode_located(grid, detail=True)
    payload = page_payload(result, layout.fmt)
    header = read_header(payload.data)
    if header is None or not _header_fits(header, layout.fmt):
        return None
    reading = read_label(grid)
    info = parse_label(reading.text)
    return ScanIdentity(
        layout.paper, layout.fmt, rotation, header.page, header.total, None,
        info.text if info is not None else "", reading.confidence, reading.margin, grid,
        layout=layout, header=header, payload=payload, result=result,
    )


def identify_scan(image: np.ndarray, options: DecodeOptions | None = None) -> ScanIdentity:
    """Work out a scan's paper, dot size, rotation and page.

    The papers are tried closest outline shape first. For each paper:

    1. Its standard-dot page in every rotation, from the label (0.2.0 rules).
       A valid tag wins at once, whatever the data holds. A reliable untagged
       label is checked for a header first: a standard-dot version-1 page
       carries an untagged label.
    2. The paper's layouts, closest shape first, in every rotation: all of
       them for the paper with the layout closest to the outline's shape,
       only those of nearly its shape for the other paper (_layouts_by_shape).
       Unless its located grid is not _regular, the page is decoded and a
       valid header (version-1 rules) wins.

    Raises IdentifyError("no page found") when no candidate rotation shows a
    page outline, else IdentifyError("label unreadable"), carrying the
    resolution estimated from the outline, when no candidate is accepted.

    A label is accepted when it parses, carries the paper's own format
    string, a page number within the total and a total the encoder could
    have written (at most MAX_PAGES), and either
    - a tag that fits the total and whose check is right for the page number
      and total read, in a reading that is plausible (LabelReading), or
    - no tag, in a reading that is reliable, with free text that is not a tag
      of that page and total with one cell misread (tag.damaged_tag).

    The check code is the error detector for tagged labels, so their
    acceptance does not rest on the stroke heuristics, which can reject exact
    readings of blurred scans. An untagged label has no detector and needs
    the stricter reliable gate, a filter that makes misreads rare but cannot
    rule them out.

    A header is accepted when one of its copies passes its CRC, those that
    pass agree, and it describes a document of this layout (_header_fits).
    The identity of a version-1 page carries the header, the page's payload
    and its decode, so it need not be decoded again; its name is the label's
    free text if the label parses, else "".
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

    def done(ident: ScanIdentity) -> ScanIdentity:
        return dataclasses.replace(ident, scan_dpi=scan_dpi(ident.grid, ident.layout))

    outline = next((c for r in rotations if (c := view(r)[1]) is not None), None)
    if outline is None:
        raise IdentifyError(NO_PAGE)
    # The likelier paper in every orientation before the other paper: a page
    # turned the wrong way costs one locate, not one per paper.
    for paper in _papers_by_shape(outline):
        standard = get_layout(paper.name)
        grids: dict[int, PageGrid | None] = {}
        for rotation in rotations:
            upright, corners = view(rotation)
            if corners is None:
                continue
            grid = grids[rotation] = _locate(upright, standard.fmt, options)
            ident = None if grid is None else _identify_label(grid, rotation, paper)
            if ident is None:
                continue
            if ident.tag is None:
                ident = _identify_header(upright, rotation, standard, options, grid) or ident
            return done(ident)
        for layout in _layouts_by_shape(outline, paper):
            for rotation in rotations:
                upright, corners = view(rotation)
                if corners is None:
                    continue
                grid = grids.get(rotation) if layout is standard else None
                if layout is standard and grid is None:
                    continue  # not located in step 1
                ident = _identify_header(upright, rotation, layout, options, grid)
                if ident is not None:
                    return done(ident)
        grids.clear()
    raise IdentifyError(LABEL_UNREADABLE, scan_dpi=_outline_dpi(outline))


# A page accepted from an untagged label alone is read again by the slow reader
# when its scan has fewer pixels than this to a printed dot (the ordinary
# reader is made for three).
COARSE_PIXELS_PER_DOT = 2.5
# ... and only when the ordinary reader could not correct at least this share
# of the page's symbols, so that a header may have gone unread. (A header is
# stored five times; the owner's coarse scans lost 13% or more of their
# symbols, a clean scan loses none.)
DAMAGED_SHARE = 0.01


def identify_any(
    image: np.ndarray,
    options: DecodeOptions | None = None,
    *,
    slow: bool = True,
    cancelled: Callable[[], bool] | None = None,
    on_slow: Callable[[], None] | None = None,
) -> ScanIdentity:
    """identify_scan, then, where that is not enough, the slow reader (decoder.soft).

    The slow reader is tried when slow is true and either
    - identify_scan failed but found a page outline (its IdentifyError
      carries a scan_dpi), or
    - identify_scan accepted the page from an untagged label alone, with no
      header, on a scan with fewer than COARSE_PIXELS_PER_DOT pixels to a
      dot whose data the ordinary reader could not read well (DAMAGED_SHARE
      of its symbols beyond correction): such a label can be read where
      the data cannot, so a version-1
      page would pass for an old one and its document would never be found.
    on_slow() is called first. In the first case, if the slow reader fails
    too, identify_scan's error is raised with slow_tried set; in the second
    the label's identity is kept. A valid tag is never questioned.
    decoder.soft.Stopped propagates when cancelled() returns True during the
    slow reader.
    """
    error = label_only = None
    try:
        ident = identify_scan(image, options)
    except IdentifyError as first:
        if not slow or first.scan_dpi is None:
            raise
        error = first
    else:
        if not slow or not _label_only_and_coarse(ident):
            return ident
        label_only = ident
    from optar.decoder.soft import identify_coarse  # imports this module

    if on_slow is not None:
        on_slow()
    try:
        return identify_coarse(image, options, cancelled)
    except IdentifyError:
        if label_only is not None:
            return label_only
        error.slow_tried = True
        raise error from None


def _label_only_and_coarse(ident: ScanIdentity) -> bool:
    if ident.header is not None or ident.tag is not None:
        return False
    if ident.scan_dpi is None or ident.layout is None:
        return False
    if ident.scan_dpi >= COARSE_PIXELS_PER_DOT * float(ident.layout.pixels_per_inch):
        return False
    # A page whose data reads cleanly would have shown its header: it is an
    # old page, and is left alone.
    stats = decode_located(ident.grid).stats
    return stats.uncorrectable >= DAMAGED_SHARE * stats.symbols


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
    lower rotation. Returns (rotation, result). Raises DecodeError (with the
    last rotation's message) when no rotation decodes.

    The result is only the best of the rotations tried, not proof that the
    rotation is right: if the upright rotation raised and another one
    "decoded", its bytes are garbage. The caller must judge
    result.stats.uncorrectable before trusting the data or the rotation.
    """
    image = _check(image)
    best: tuple[tuple[int, int, int], PageResult] | None = None
    # Only the message: the exception itself holds the traceback, and with it
    # the rotated image and locate_page's locals, across the next decode.
    error_args: tuple = ()
    for rotation in candidate_rotations(image):
        try:
            result = decode_located(
                locate_page(_turn(image, rotation), fmt, options), detail=detail
            )
        except DecodeError as e:
            error_args = e.args
            continue
        key = (result.stats.uncorrectable, _corrected_bits(result), rotation)
        if best is None or key < best[0]:
            best = (key, result)
    if best is None:
        raise DecodeError(*error_args)
    return best[0][2], best[1]
