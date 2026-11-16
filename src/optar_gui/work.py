# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The work done in the background: one scan end to end, or one PDF.

Plain Python, no Qt: every function here that reads a file runs on a worker
thread (never on the interface thread, since each one reads or decodes a scan,
reads or hashes a whole file or writes one) and is testable on its own.
``name_preview`` reads nothing and is cheap: the writing tab calls it on the
interface thread whenever the name or the paper changes.

Each function takes ``cancelled``, a callable returning True once the work is
no longer wanted, checks it between stages and raises ``Cancelled`` when it
does. Bad input never raises from ``process_scan`` or ``process_unlabelled``:
it comes back as a ``ScanWork`` with a reason.

Memory. A located page holds the whole cleaned scan (tens of MB for a 600 dpi
scan). A ``ScanWork`` holds only the page's packed data (about 200 KB), its
statistics and the positions of its corrected bits, so the interface can keep
one per scan.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from optar.decoder import PageResult, decode_located, page_to_scan
from optar.encoder import check_encodable, encode, page_count
from optar.errors import DecodeError, IdentifyError, OptarError
from optar.fileio import io_error, replacing
from optar.font import FIRST_CHAR, GLYPH_CELLS, label_text
from optar.format import PageFormat, get_paper
from optar.identify import decode_unlabelled, identify_scan
from optar.imageio import read_scan
from optar.label import printed_label
from optar.layout import channel_xy
from optar.pdf import write_pdf
from optar.tag import FINGERPRINT_DIGITS, Tag, make_tag, tagged_label
from optar_gui import text
from optar_gui.document import PageOutcome, ScanInfo

__all__ = [
    "NOT_DECODABLE",
    "Cancelled",
    "FileFacts",
    "NamePreview",
    "ScanWork",
    "encode_to_pdf",
    "name_preview",
    "prepare_file",
    "process_scan",
    "process_unlabelled",
    "same_file",
]

# The reason given when a page assigned by hand decodes badly in every rotation.
NOT_DECODABLE = "could not be decoded in any orientation"


class Cancelled(Exception):
    """The work was cancelled before it finished."""


def _never() -> bool:
    return False


def _check(cancelled: Callable[[], bool]) -> None:
    if cancelled():
        raise Cancelled()


@dataclass(frozen=True, eq=False)
class ScanWork:
    """What processing one scan found.

    ``info`` is None when the scan was not identified (always for a scan
    assigned by hand); ``reason`` is empty when it was identified and decoded,
    else why not. ``outcome`` is None when the page was not decoded.
    ``rotation`` is the counter-clockwise quarter turns that make the scan
    upright. ``marks`` holds the (x, y) scan-pixel positions (float32, shape
    (n, 2), pixel centres at integers) of every bit error correction changed,
    on the upright image, or None when the page was not decoded. ``size`` is
    the upright image's (width, height), (0, 0) when it could not be read.
    """

    info: ScanInfo | None
    reason: str
    outcome: PageOutcome | None
    rotation: int
    marks: np.ndarray | None
    size: tuple[int, int]


def _upright_size(image: np.ndarray, rotation: int) -> tuple[int, int]:
    h, w = image.shape[:2]
    return (int(h), int(w)) if rotation % 2 else (int(w), int(h))


def _outcome(result: PageResult) -> tuple[PageOutcome, np.ndarray]:
    """The page's packed data and statistics, and its corrected bits' scan positions.

    Takes only small arrays out of the result: nothing returned refers to
    the grid or the scan.
    """
    stats = result.stats
    outcome = PageOutcome(
        data=np.packbits(result.bits).tobytes(),
        histogram=tuple(int(n) for n in stats.error_histogram[:4]),
        lost=int(stats.uncorrectable),
    )
    grid = result.grid
    xs, ys = channel_xy(grid.fmt)
    positions = result.corrected_bits
    sx, sy = page_to_scan(grid, xs[positions], ys[positions])
    marks = np.column_stack([np.ravel(sx), np.ravel(sy)]).astype(np.float32)
    return outcome, marks


def process_scan(path: str, cancelled: Callable[[], bool] = _never) -> ScanWork:
    """Load, identify and decode one scan.

    An unreadable file comes back with ``info=None`` and the reading error as
    the reason; a scan that is not identified with ``info=None`` and the
    reason "no page found" or "label unreadable"; an identified scan that
    does not decode with its ``info``, no outcome and the decoder's message.
    Checks ``cancelled`` after loading, after identifying and after decoding.
    """
    try:
        image = read_scan(path)
    except OptarError as e:
        return ScanWork(None, str(e), None, 0, None, (0, 0))
    _check(cancelled)
    try:
        identity = identify_scan(image)
    except IdentifyError as e:
        return ScanWork(None, e.reason, None, 0, None, _upright_size(image, 0))
    except DecodeError as e:
        return ScanWork(None, str(e), None, 0, None, _upright_size(image, 0))
    rotation = identity.rotation
    size = _upright_size(image, rotation)
    del image
    info = ScanInfo(
        format=identity.fmt.to_string(),
        total=identity.total,
        page=identity.page,
        name=identity.name,
        tag=identity.tag,
    )
    grid = identity.grid
    del identity
    _check(cancelled)
    try:
        result = decode_located(grid, detail=True)
    except DecodeError as e:
        return ScanWork(info, str(e), None, rotation, None, size)
    finally:
        del grid
    outcome, marks = _outcome(result)
    del result
    _check(cancelled)
    return ScanWork(info, "", outcome, rotation, marks, size)


def process_unlabelled(
    path: str, format: str, cancelled: Callable[[], bool] = _never
) -> ScanWork:
    """Decode a scan whose label is not read, in the rotation that decodes best.

    ``format`` is the page format string of the document the user assigns the
    scan to (an invalid one raises FormatError: it is the caller's error).
    ``info`` is always None. If even the best rotation has more than a
    quarter of its symbols unrecoverable, the page was not found the right
    way up: no outcome, reason NOT_DECODABLE. Checks ``cancelled`` after
    loading and after decoding.
    """
    fmt = PageFormat.parse(format)
    try:
        image = read_scan(path)
    except OptarError as e:
        return ScanWork(None, str(e), None, 0, None, (0, 0))
    _check(cancelled)
    try:
        rotation, result = decode_unlabelled(image, fmt, detail=True)
    except DecodeError as e:
        return ScanWork(None, str(e), None, 0, None, _upright_size(image, 0))
    size = _upright_size(image, rotation)
    del image
    if result.stats.uncorrectable > result.stats.symbols // 4:
        del result
        _check(cancelled)
        return ScanWork(None, NOT_DECODABLE, None, rotation, None, size)
    outcome, marks = _outcome(result)
    del result
    _check(cancelled)
    return ScanWork(None, "", outcome, rotation, marks, size)


def encode_to_pdf(
    src: str,
    dest: str,
    paper_name: str,
    name: str,
    cancelled: Callable[[], bool] = _never,
) -> int:
    """Encode the file ``src`` as a print-ready PDF at ``dest``; return the page count.

    Every page's label is the document tag (with that page's check) followed
    by ``name``. The PDF is written through a temporary file: on failure or
    cancellation an existing ``dest`` is left untouched and nothing is left
    behind. Checks ``cancelled`` before each page. Raises OptarError on
    failure, and before reading anything when ``dest`` is ``src`` itself.
    """
    if same_file(src, dest):
        raise OptarError(text.DEST_IS_SOURCE)
    paper = get_paper(paper_name)
    fmt = PageFormat.for_paper(paper)
    try:
        with open(src, "rb") as f:
            data = f.read()
    except OSError as e:
        raise io_error("read", src, e) from e
    check_encodable(len(data), fmt)
    tag = make_tag(data)

    def pages():
        pending = encode(data, fmt, lambda page, total: tagged_label(tag, name, page, total))
        while True:
            _check(cancelled)
            page = next(pending, None)
            if page is None:
                return
            yield page.pixels

    with replacing(dest) as temp:
        return write_pdf(temp, pages(), paper)


def same_file(a: str, b: str) -> bool:
    """Whether the paths name the same file: by the file system when both exist
    (hard links and symbolic links included), else by their resolved spelling."""
    try:
        return os.path.samefile(a, b)
    except (OSError, ValueError):
        pass
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


# How much of a file is read at a time while its tag is computed.
_READ_CHUNK = 1 << 20


@dataclass(frozen=True)
class FileFacts:
    """What the writing tab needs to know about a chosen file: its size and tag."""

    size: int
    tag: Tag


def prepare_file(path: str, cancelled: Callable[[], bool] = _never) -> FileFacts:
    """Read the file at ``path`` once, in chunks, and make its document tag.

    The tag equals ``make_tag`` of the whole contents, without holding them in
    memory. Checks ``cancelled`` after every chunk. Raises OptarError when the
    file cannot be read.
    """
    digest = hashlib.sha256()
    size = 0
    try:
        with open(path, "rb") as f:
            while chunk := f.read(_READ_CHUNK):
                digest.update(chunk)
                size += len(chunk)
                _check(cancelled)
    except OSError as e:
        raise io_error("read", path, e) from e
    return FileFacts(size, Tag(size, digest.hexdigest()[:FINGERPRINT_DIGITS]))


@dataclass(frozen=True)
class NamePreview:
    """How a name prints on the pages of a file.

    ``printed`` is page 1's free text (tag and name) exactly as printed, without
    the format string and page number before it. ``dropped`` lists, once each and
    in order, the name's characters the label font cannot print. ``cut`` is True
    when some page prints less of the name than the font could show.
    """

    total: int
    printed: str
    dropped: str
    cut: bool


def _drawable(ch: str) -> bool:
    return FIRST_CHAR <= ord(ch) <= FIRST_CHAR + GLYPH_CELLS


def _free_text(fmt: PageFormat, tag: Tag, name: str, page: int, total: int) -> str:
    """What page ``page`` of ``total`` prints after its format string and page number."""
    printed = printed_label(fmt, label_text(fmt, page, total, tagged_label(tag, name, page, total)))
    prefix = f"  {fmt.to_string()} {page}/{total} "
    return printed[len(prefix):] if printed.startswith(prefix) else ""


def name_preview(paper_name: str, tag: Tag, name: str) -> NamePreview:
    """What the pages of a file with tag ``tag`` will print for ``name`` on this paper."""
    fmt = PageFormat.for_paper(get_paper(paper_name))
    total = page_count(tag.size, fmt)
    dropped = "".join(dict.fromkeys(ch for ch in name if not _drawable(ch)))
    # The longest page number takes the most room, so the last page is cut first;
    # an empty file prints one page labelled 1/0.
    last = max(total, 1)
    wanted = "".join(ch for ch in tagged_label(tag, name, last, total) if _drawable(ch))
    cut = len(_free_text(fmt, tag, name, last, total)) < len(wanted.rstrip(" "))
    return NamePreview(total, _free_text(fmt, tag, name, 1, total), dropped, cut)
