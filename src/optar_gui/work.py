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
one per scan. Identifying and decoding a scan larger than ``LARGE_SCAN_PIXELS``
waits for its turn: only one such scan is worked on at a time, whatever the
number of workers.

Only regular files are read: a named pipe would block a worker until something
writes to it, and a device never ends. ``optar.imageio.read_scan`` itself
accepts them (``optar decode`` may read a pipe), so the checks are here.
"""

from __future__ import annotations

import hashlib
import os
import stat
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

import optar.container
import optar.encoder
from optar.container import Header, PagePayload, pages_promised, plan, plan_for, wrap
from optar.decoder import PageResult, decode_located, page_to_scan
from optar.decoder.soft import Stopped
from optar.encoder import check_encodable, encode, page_count
from optar.errors import DecodeError, IdentifyError, OptarError
from optar.fileio import io_error, replacing
from optar.font import FIRST_CHAR, GLYPH_CELLS, fine_label, label_text
from optar.format import (
    DOT_SIZES,
    LAYOUTS,
    PAPERS,
    PARITY,
    Layout,
    PageFormat,
    get_layout,
    get_paper,
)
from optar.identify import (
    STEP_FIND,
    STEP_IDENTIFY,
    STEP_SLOW_FIT,
    STEP_SLOW_SAMPLE,
    decode_unlabelled,
    identify_any,
)
from optar.imageio import read_scan
from optar.label import printed_label
from optar.layout import channel_xy
from optar.pdf import write_pdf
from optar.tag import FINGERPRINT_DIGITS, Tag, make_tag, tagged_label
from optar_gui import text
from optar_gui.document import NOT_DECODABLE, PageOutcome, Progress, ScanInfo

__all__ = [
    "LARGE_SCAN_PIXELS",
    "Cancelled",
    "FileFacts",
    "MIN_PIXELS_PER_DOT",
    "NamePreview",
    "PrintPlan",
    "Progress",
    "STEP_FIND",
    "STEP_IDENTIFY",
    "STEP_OPEN",
    "STEP_READ",
    "STEP_SLOW_FIT",
    "STEP_SLOW_SAMPLE",
    "ScanWork",
    "TOO_LARGE_TO_PROTECT",
    "TOO_MANY_PAGES",
    "WindowError",
    "dot_choices",
    "encode_to_pdf",
    "name_only_preview",
    "name_preview",
    "prepare_file",
    "print_plan",
    "process_scan",
    "process_unlabelled",
    "regular_file",
    "same_file",
    "too_coarse",
]

# Scans with more pixels than this are identified and decoded one at a time.
# Measured peaks: 513 MB for one 600 dpi A4 scan (about 35 megapixels) and
# 1.33 GB for three at once; three 1200 dpi scans (about 140 megapixels each)
# at once peak near 4 GB. A 600 dpi scan stays below the limit and runs in
# parallel; a 1200 dpi one waits for its turn.
LARGE_SCAN_PIXELS = 80_000_000
_LARGE_SCAN_TURN = threading.Lock()
# How often a scan waiting for its turn checks whether it was cancelled (seconds).
_TURN_POLL_S = 0.1


class Cancelled(Exception):
    """The work was cancelled before it finished."""


class WindowError(OptarError):
    """An error the window words itself: ``words`` (a ``text.Words``) says it, in
    the language current whenever it is shown; ``str(e)`` words it then too."""

    def __init__(self, words: text.Words) -> None:
        super().__init__()
        self.words = words

    def __str__(self) -> str:
        return str(self.words)


def _never() -> bool:
    return False


def _check(cancelled: Callable[[], bool]) -> None:
    if cancelled():
        raise Cancelled()


def _take_turn(pixels: int, cancelled: Callable[[], bool]) -> bool:
    """For a large scan, waits until no other large scan is being worked on and
    returns True: the caller then releases ``_LARGE_SCAN_TURN``. Returns False at
    once for a smaller scan. Raises ``Cancelled`` while waiting, holding nothing."""
    if pixels <= LARGE_SCAN_PIXELS:
        return False
    _wait_turn(cancelled)
    return True


def _wait_turn(cancelled: Callable[[], bool]) -> None:
    """Waits until ``_LARGE_SCAN_TURN`` is taken; raises ``Cancelled`` while
    waiting, holding nothing."""
    while not _LARGE_SCAN_TURN.acquire(timeout=_TURN_POLL_S):
        _check(cancelled)


def _irregular(path: str) -> bool:
    """Whether ``path`` exists but is not a regular file. A path that cannot be
    examined is left for reading it to report."""
    try:
        return not stat.S_ISREG(os.stat(path).st_mode)
    except (OSError, ValueError):
        return False


def _not_regular(path: str) -> text.Words:
    """Why ``path`` is not read: a folder, a named pipe or a device."""
    return text.Words(text.not_regular_file, path)


def regular_file(path: str) -> None:
    """Raises OptarError when ``path`` exists but is not a regular file (a folder,
    a named pipe, a device), without opening it."""
    if _irregular(path):
        raise WindowError(_not_regular(path))


def _open_regular(path: str):
    """Opens ``path`` for reading in binary, only if it is a regular file.

    Where the system has it, the file is opened without waiting (a named pipe
    with no writer would block an ordinary open) and checked once open, so it
    cannot be swapped between the check and the open. Raises OptarError.
    """
    nonblock = getattr(os, "O_NONBLOCK", 0)
    try:
        if not nonblock:
            regular_file(path)
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | nonblock)
    except OSError as e:
        raise io_error("read", path, e) from e
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise WindowError(_not_regular(path))
        if nonblock:
            os.set_blocking(fd, True)
        return os.fdopen(fd, "rb")
    except OSError as e:
        os.close(fd)
        raise io_error("read", path, e) from e
    except BaseException:
        os.close(fd)
        raise


@dataclass(frozen=True, eq=False)
class ScanWork:
    """What processing one scan found.

    ``info`` is None when the scan was not identified (always for a scan
    assigned by hand); ``reason`` is empty when it was identified and decoded,
    else why not: a code (the library's English constants, ``NOT_DECODABLE``) or a
    ``text.Words`` that words it when shown, never a finished sentence, so that it
    follows the window's language. ``outcome`` is None when the page was not decoded.
    ``rotation`` is the counter-clockwise quarter turns that make the scan
    upright. ``marks`` holds the (x, y) scan-pixel positions (float32, shape
    (n, 2), pixel centres at integers) of every bit error correction changed,
    on the upright image, or None when the page was not decoded. ``size`` is
    the upright image's (width, height), (0, 0) when it could not be read.

    ``payload`` is a version-1 page's payload (``header`` gives its header,
    from ``info``); ``scan_dpi`` the scan's estimated resolution, also for a
    scan that was found but not identified; ``layout`` the identified page's
    paper and dot size. ``slow`` is True when the page was read by the slower
    reader for coarse scans (``optar.decoder.soft``): its outcome counts no
    repairs (that reader measures no per-block damage) but the dots whose own
    impression lost its decision of their symbol (``PageOutcome.corrected_dots``),
    and its marks are those dots, on the scan as loaded (that reader works on an
    enlarged copy of it). There may be a few hundred thousand of them (about
    2 MB).
    """

    info: ScanInfo | None
    reason: str | text.Words
    outcome: PageOutcome | None
    rotation: int
    marks: np.ndarray | None
    size: tuple[int, int]
    payload: PagePayload | None = None
    scan_dpi: float | None = None
    layout: Layout | None = None
    slow: bool = False
    # Of a page read by the slower reader: the width of one of its dots in scan
    # pixels, at which its (dense) marks are drawn; 0 for another page.
    dot: float = 0.0

    @property
    def header(self) -> Header | None:
        """The version-1 header the page's data carries, or None."""
        return self.info.header if self.info is not None else None


# A scan with fewer pixels than this per printed dot is too coarse for its page:
# it is still decoded and used if it reads, but its note says so.
MIN_PIXELS_PER_DOT = 2


def too_coarse(
    scan_dpi: float | None, layout: Layout | None, *, unreadable: bool = False
) -> bool:
    """Whether a scan at ``scan_dpi`` has fewer than ``MIN_PIXELS_PER_DOT`` pixels
    per dot of ``layout``. An ``unreadable`` scan has no layout: it is judged by
    the finest dots there are. False when the resolution (or the layout of a
    readable scan) is not known."""
    if scan_dpi is None:
        return False
    if unreadable:
        finest = max(float(lay.pixels_per_inch) for lay in LAYOUTS.values())
        return scan_dpi < MIN_PIXELS_PER_DOT * finest
    return layout is not None and scan_dpi < MIN_PIXELS_PER_DOT * float(layout.pixels_per_inch)


# The steps of a scan's reading besides the library's (optar.identify.STEP_*):
# reading the file, and decoding the identified page.
STEP_OPEN = "open"
STEP_READ = "read"

# The share of the bar each step of an ordinary reading covers: (start, end).
# Rough, from where the time goes on a 600 dpi A4 scan: loading it, finding its
# outline, trying candidates (one, for most pages; more for a page turned or of
# larger dots), decoding it. A version-1 page is decoded while it is
# identified: its bar jumps from identifying to the end.
_SPANS = {
    STEP_OPEN: (0.0, 0.05),
    STEP_FIND: (0.05, 0.2),
    STEP_IDENTIFY: (0.2, 0.5),
    STEP_READ: (0.5, 1.0),
}
# The slower reader takes the rest of the bar from where it starts: its
# preparation of a candidate (enlarging, locating, sampling) this share, its
# fits the remainder, evenly. Each fit costs about the same (decoder.soft).
_SLOW_SAMPLE_SHARE = 0.2
# Reports of the same step are sent at most this often (seconds); a new step,
# and the end, are sent at once. Steps change a few times a scan.
PROGRESS_INTERVAL_S = 0.1


class _Reporter:
    """Turns the steps of one scan's reading into ``Progress`` for ``emit``: a
    fraction that never decreases, sent no more often than ``PROGRESS_INTERVAL_S``
    for one step."""

    def __init__(self, emit: Callable[[Progress], None], clock=time.monotonic) -> None:
        self._emit = emit
        self._clock = clock
        self._fraction = 0.0
        self._slow_from: float | None = None  # where the slower reader started
        self._sent: Progress | None = None
        self._sent_at = 0.0

    def __call__(self, step: str, done: int, of: int) -> None:
        self._fraction = max(self._fraction, self._share(step, done, of))
        progress = Progress(step, done, of, self._fraction)
        if progress == self._sent:
            return
        now = self._clock()
        sent = self._sent
        if (
            sent is not None
            and sent.step == step
            and progress.fraction < 1.0
            and now - self._sent_at < PROGRESS_INTERVAL_S
        ):
            return
        self._sent, self._sent_at = progress, now
        self._emit(progress)

    def _share(self, step: str, done: int, of: int) -> float:
        part = min(max(done / of, 0.0), 1.0) if of > 0 else 0.0
        if step in (STEP_SLOW_SAMPLE, STEP_SLOW_FIT):
            if self._slow_from is None:
                self._slow_from = self._fraction
            within = 0.0
            if step == STEP_SLOW_FIT:
                within = _SLOW_SAMPLE_SHARE + (1 - _SLOW_SAMPLE_SHARE) * part
            return self._slow_from + (1 - self._slow_from) * within
        if step not in _SPANS:
            return self._fraction
        start, end = _SPANS[step]
        return start + (end - start) * part


def _upright_size(image: np.ndarray, rotation: int) -> tuple[int, int]:
    h, w = image.shape[:2]
    return (int(h), int(w)) if rotation % 2 else (int(w), int(h))


def _outcome(
    result: PageResult, slow: bool = False, enlarged: float = 1.0
) -> tuple[PageOutcome, np.ndarray]:
    """The page's packed data and statistics, and its corrected bits' scan positions.

    Takes only small arrays out of the result: nothing returned refers to
    the grid or the scan. A page read by the slower reader (``slow``) counts no
    repairs: its histogram counts the dot decisions that reader overruled, so
    its outcome's histogram is zeros and it carries the number of those dots
    (``corrected_dots``, of ``dots``) instead; its marks are those dots. That
    reader located the page on the scan enlarged ``enlarged`` times: the marks
    are brought back to the scan as loaded.
    """
    stats = result.stats
    data = np.packbits(result.bits).tobytes()
    grid = result.grid
    positions = result.corrected_bits
    if slow:
        outcome = PageOutcome(
            data=data,
            histogram=(0, 0, 0, 0),
            lost=int(stats.uncorrectable),
            slow=True,
            dots=int(grid.fmt.used_bits),
            corrected_dots=len(positions),
        )
    else:
        outcome = PageOutcome(
            data=data,
            histogram=tuple(int(n) for n in stats.error_histogram[:4]),
            lost=int(stats.uncorrectable),
        )
    return outcome, _marks(grid, positions, enlarged)


def _dot_width(grid) -> float:
    """The width of one dot of the located page in the pixels it was located on:
    the mean distance between neighbouring cross centres per cross pitch."""
    p = np.asarray(grid.positions, dtype=np.float64)
    steps = [np.hypot(*np.moveaxis(np.diff(p, axis=a), -1, 0)).ravel() for a in (0, 1)]
    return float(np.concatenate(steps).mean()) / grid.fmt.cpitch


# Corrected dots brought to scan positions at a time: bounds the temporaries of
# page_to_scan for the slower reader's few hundred thousand.
_MARK_CHUNK = 65_536


def _marks(grid, positions: np.ndarray, enlarged: float = 1.0) -> np.ndarray:
    """The (x, y) scan positions (float32, shape (n, 2)) of channel ``positions`` on
    ``grid``, divided back from a scan enlarged ``enlarged`` times."""
    xs, ys = channel_xy(grid.fmt)
    marks = np.empty((len(positions), 2), np.float32)
    for start in range(0, len(positions), _MARK_CHUNK):
        part = positions[start : start + _MARK_CHUNK]
        sx, sy = page_to_scan(grid, xs[part], ys[part])
        marks[start : start + len(part), 0] = np.ravel(sx)
        marks[start : start + len(part), 1] = np.ravel(sy)
    if enlarged != 1.0:
        marks += np.float32(0.5)
        marks /= np.float32(enlarged)
        marks -= np.float32(0.5)
    return marks


def process_scan(
    path: str,
    cancelled: Callable[[], bool] = _never,
    on_slow: Callable[[], None] | None = None,
    on_progress: Callable[[Progress], None] | None = None,
) -> ScanWork:
    """Load, identify and decode one scan.

    A scan the ordinary reader cannot identify, but whose page outline it found,
    is tried with the slower reader for coarse scans (``identify.identify_any``):
    ``on_slow()`` is called (on the worker thread) just before that starts, and
    the work then waits for the large-scan turn, since that reader works on an
    enlarged copy of the scan. A page it reads comes back with ``slow`` True; if
    it fails too, a coarse scan's reason says that it was tried.

    An unreadable file comes back with ``info=None`` and the reading error as
    the reason; a scan that is not identified with ``info=None`` and the
    reason "no page found" or "label unreadable" (``text.coarse_scan``'s words instead
    when the resolution a page outline gave is ``too_coarse`` for any dots), with
    its ``scan_dpi`` when known; an identified scan that does
    not decode with its ``info``, no outcome and the decoder's message. A
    version-1 page was decoded while it was identified: that decode is used,
    not repeated, and its payload kept.
    Checks ``cancelled`` after loading, after identifying and after decoding,
    while a large scan waits for its turn, and throughout the slower reader.

    ``on_progress``, if given, is called on the worker thread with a ``Progress``
    as the reading goes through its steps (``STEP_OPEN``, the library's
    ``STEP_FIND``, ``STEP_IDENTIFY``, ``STEP_SLOW_SAMPLE`` and ``STEP_SLOW_FIT``,
    then ``STEP_READ``): its fraction never decreases and reaches 1 when the page
    is decoded. Reports of one step come at most every ``PROGRESS_INTERVAL_S``.
    """
    report = _Reporter(on_progress) if on_progress is not None else None
    if report is not None:
        report(STEP_OPEN, 0, 1)
    if _irregular(path):
        return ScanWork(None, _not_regular(path), None, 0, None, (0, 0))
    try:
        image = read_scan(path)
    except OptarError as e:
        return ScanWork(None, text.Words.error(e), None, 0, None, (0, 0))
    _check(cancelled)
    turn = _take_turn(image.size, cancelled)

    def slow_started() -> None:
        nonlocal turn
        if on_slow is not None:
            on_slow()
        if not turn:
            _wait_turn(cancelled)
            turn = True

    reporting = {} if report is None else {"on_progress": report}
    try:
        try:
            identity = identify_any(
                image, cancelled=cancelled, on_slow=slow_started, **reporting
            )
        except Stopped:
            raise Cancelled() from None
        except IdentifyError as e:
            reason = e.reason
            if too_coarse(e.scan_dpi, None, unreadable=True):
                reason = text.Words(text.coarse_scan, e.scan_dpi, None, e.slow_tried)
            size = _upright_size(image, 0)
            return ScanWork(None, reason, None, 0, None, size, scan_dpi=e.scan_dpi)
        except DecodeError as e:
            return ScanWork(None, text.Words.error(e), None, 0, None, _upright_size(image, 0))
        rotation = identity.rotation
        size = _upright_size(image, rotation)
        del image
        header, payload = identity.header, identity.payload
        slow = identity.reader == "slow"
        enlarged = identity.enlarged
        found = {"scan_dpi": identity.scan_dpi, "layout": identity.layout, "slow": slow}
        info = ScanInfo(
            format=identity.fmt.to_string(),
            total=identity.total,
            page=identity.page,
            name=identity.name,
            tag=identity.tag,
            header=header,
            scan_dpi=identity.scan_dpi,
        )
        grid, result = identity.grid, identity.result
        del identity
        _check(cancelled)
        if header is None or payload is None or result is None:
            payload = result = None
            if report is not None:
                report(STEP_READ, 0, 1)
            try:
                result = decode_located(grid, detail=True)
            except DecodeError as e:
                return ScanWork(info, text.Words.error(e), None, rotation, None, size, **found)
            finally:
                del grid
        else:
            del grid  # decoded already: identifying found the header in its data
    finally:
        if turn:
            _LARGE_SCAN_TURN.release()
    outcome, marks = _outcome(result, slow, enlarged)
    dot = _dot_width(result.grid) / enlarged if slow else 0.0
    del result
    _check(cancelled)
    if report is not None:
        report(STEP_READ, 1, 1)
    return ScanWork(info, "", outcome, rotation, marks, size, payload=payload, dot=dot, **found)


def process_unlabelled(
    path: str, format: str, cancelled: Callable[[], bool] = _never
) -> ScanWork:
    """Decode a scan whose label is not read, in the rotation that decodes best.

    ``format`` is the page format string of the document the user assigns the
    scan to (an invalid one raises FormatError: it is the caller's error).
    ``info`` is always None. If even the best rotation has more than a
    quarter of its symbols unrecoverable, the page was not found the right
    way up: no outcome, reason NOT_DECODABLE. Checks ``cancelled`` after
    loading and after decoding, and while a large scan waits for its turn.
    """
    fmt = PageFormat.parse(format)
    if _irregular(path):
        return ScanWork(None, _not_regular(path), None, 0, None, (0, 0))
    try:
        image = read_scan(path)
    except OptarError as e:
        return ScanWork(None, text.Words.error(e), None, 0, None, (0, 0))
    _check(cancelled)
    turn = _take_turn(image.size, cancelled)
    try:
        rotation, result = decode_unlabelled(image, fmt, detail=True)
    except DecodeError as e:
        return ScanWork(None, text.Words.error(e), None, 0, None, _upright_size(image, 0))
    finally:
        if turn:
            _LARGE_SCAN_TURN.release()
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
    *,
    dots: str = "standard",
    protect: str = "standard",
    compatible: bool = False,
) -> int:
    """Encode the file ``src`` as a print-ready PDF at ``dest``; return the page count.

    With ``compatible`` the printout is optar 0.2.0's (Standard dots, no
    protection; ``dots`` and ``protect`` are ignored): every page's label is
    the document tag (with that page's check) followed by ``name``. Otherwise
    the file and ``name`` are wrapped with page headers and ``protect``'s
    parity (``optar.container.wrap``) and printed at the dot size ``dots``;
    each label is ``name`` alone. The PDF is written through a temporary
    file: on failure or cancellation an existing ``dest`` is left untouched
    and nothing is left behind. Checks ``cancelled`` before each page.
    Raises OptarError on failure, before reading anything when ``dest`` is
    ``src`` itself, and before reading the file when it is too large.
    """
    if same_file(src, dest):
        raise WindowError(text.Words.constant("DEST_IS_SOURCE"))
    if not compatible:
        return _encode_wrapped(src, dest, paper_name, name, cancelled, dots, protect)
    paper = get_paper(paper_name)
    fmt = PageFormat.for_paper(paper)
    with _open_regular(src) as f:
        try:
            check_encodable(os.fstat(f.fileno()).st_size, fmt)  # before reading it
            data = f.read()
        except OSError as e:
            raise io_error("read", src, e) from e
    check_encodable(len(data), fmt)  # it may have grown
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


def _encode_wrapped(
    src: str,
    dest: str,
    paper_name: str,
    name: str,
    cancelled: Callable[[], bool],
    dots: str,
    protect: str,
) -> int:
    """encode_to_pdf of a version-1 printout."""
    layout = get_layout(paper_name, dots)
    fmt = layout.fmt
    parity = _parity(protect)
    with _open_regular(src) as f:
        try:
            plan(os.fstat(f.fileno()).st_size, name, fmt, parity)  # before reading it
            data = f.read()
        except OSError as e:
            raise io_error("read", src, e) from e
    stream = wrap(data, name, fmt, parity)  # plans again: the file may have grown
    del data
    _check(cancelled)

    def pages():
        pending = encode(stream, fmt, name)
        while True:
            _check(cancelled)
            page = next(pending, None)
            if page is None:
                return
            yield page.pixels, fine_label(layout, page.number, page.total, name)

    with replacing(dest) as temp:
        return write_pdf(temp, pages(), layout)


def _parity(protect: str) -> int:
    try:
        return PARITY[protect]
    except KeyError:
        raise OptarError(
            f"unknown protection {protect!r}; known: {', '.join(PARITY)}"
        ) from None


# Why a file cannot be put on paper with the chosen dot size and protection.
TOO_MANY_PAGES = text.TOO_MANY_PAGES
TOO_LARGE_TO_PROTECT = text.TOO_LARGE_TO_PROTECT


@dataclass(frozen=True)
class PrintPlan:
    """How a file of a given size prints with the chosen paper, dot size and protection.

    ``total`` is the page count (0 for an empty file printed compatibly: its
    one page is labelled 1/0; 0 too when the file is too large). ``promised``
    is how many pages may be lost, from ``optar.container.pages_promised``;
    ``protected`` is whether damage within pages is repaired. ``too_large``
    is None, ``TOO_MANY_PAGES`` or ``TOO_LARGE_TO_PROTECT``, and ``limit``
    then the most pages a printout of that kind may have. For a file too
    large, ``unprotected_fits`` is whether it fits at the same dot size without
    protection, and ``smaller_dots`` the largest smaller dot size at which it
    fits with the same protection, or None.
    """

    total: int
    promised: int = 0
    protected: bool = False
    too_large: str | None = None
    limit: int = 0
    unprotected_fits: bool = False
    smaller_dots: str | None = None


def print_plan(
    size: int,
    name: str,
    paper_name: str,
    dots: str = "standard",
    protect: str = "standard",
    compatible: bool = False,
) -> PrintPlan:
    """What ``encode_to_pdf`` makes of a file of ``size`` bytes named ``name``.

    Reads nothing and builds nothing: cheap enough for the interface thread.
    A compatible printout ignores ``dots`` and ``protect``.
    """
    if compatible:
        fmt = PageFormat.for_paper(get_paper(paper_name))
        try:
            return PrintPlan(check_encodable(size, fmt))
        except OptarError:
            return PrintPlan(0, too_large=TOO_MANY_PAGES, limit=optar.encoder.MAX_PAGES)
    fmt = get_layout(paper_name, dots).fmt
    parity = _parity(protect)
    try:
        p = plan(size, name, fmt, parity)
    except OptarError:
        # What would take the file: no protection, or the next smaller dots that do.
        smaller = [d for d in DOT_SIZES if DOT_SIZES[d].scale < DOT_SIZES[dots].scale]
        other = {
            "unprotected_fits": parity > 0 and _fits(size, name, fmt, 0),
            "smaller_dots": next(
                (d for d in reversed(smaller)
                 if _fits(size, name, get_layout(paper_name, d).fmt, parity)),
                None,
            ),
        }
        # The tighter of the two limits is the one the file is over.
        limit = optar.container.MAX_PAGES
        if parity:
            page_bytes = plan_for(1, fmt, parity).page_bytes
            protected = optar.container.PROTECTED_MAX_BYTES // page_bytes
            if protected < limit:
                return PrintPlan(0, too_large=TOO_LARGE_TO_PROTECT, limit=protected, **other)
        return PrintPlan(0, too_large=TOO_MANY_PAGES, limit=limit, **other)
    return PrintPlan(p.total, pages_promised(p), parity > 0)


def _fits(size: int, name: str, fmt: PageFormat, parity: int) -> bool:
    """Whether a file of ``size`` bytes can be put on pages of ``fmt``."""
    try:
        plan(size, name, fmt, parity)
    except OptarError:
        return False
    return True


def dot_choices() -> list[tuple[str, int]]:
    """Each dot size, in order, with the scan resolution advised for it (dpi)."""
    return [(name, dots.scan_dpi) for name, dots in DOT_SIZES.items()]


def native_path(path: str) -> str:
    """A local path in the system's own spelling. Qt gives forward slashes on
    Windows (drops, file dialogs); paths are shown and compared as the system
    spells them. An empty path (a cancelled dialog) stays empty."""
    return os.path.normpath(path) if path else path


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
    """What the writing tab needs to know about a chosen file: its size and tag.

    ``tag`` is None for a file that needs more pages than the encoder allows on
    any paper: it was not read, since it cannot be put on paper.
    """

    size: int
    tag: Tag | None


def _roomiest_format() -> PageFormat:
    """The paper preset's format that holds the most bytes a page."""
    return max((PageFormat.for_paper(p) for p in PAPERS.values()), key=lambda f: f.net_bits)


def prepare_file(path: str, cancelled: Callable[[], bool] = _never) -> FileFacts:
    """Read the file at ``path`` once, in chunks, and make its document tag.

    The tag equals ``make_tag`` of the whole contents, without holding them in
    memory. Checks ``cancelled`` after every chunk. Raises OptarError when the
    file cannot be read. A file that needs more pages than the encoder allows on
    any paper is not read: its facts come back with no tag.
    """
    digest = hashlib.sha256()
    size = 0
    with _open_regular(path) as f:
        try:
            whole = os.fstat(f.fileno()).st_size
            try:
                check_encodable(whole, _roomiest_format())
            except OptarError:
                return FileFacts(whole, None)  # too large on any paper: not read
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

    @property
    def shown(self) -> bool:
        """Whether the pages print any of the name at all."""
        return bool(self.printed.strip())


def _drawable(ch: str) -> bool:
    return FIRST_CHAR <= ord(ch) <= FIRST_CHAR + GLYPH_CELLS


def _free_text(fmt: PageFormat, tag: Tag, name: str, page: int, total: int) -> str:
    """What page ``page`` of ``total`` prints after its format string and page number."""
    return _printed_free_text(fmt, tagged_label(tag, name, page, total), page, total)


def _printed_free_text(fmt: PageFormat, free: str, page: int, total: int) -> str:
    """What page ``page`` of ``total`` prints of the free text ``free``."""
    printed = printed_label(fmt, label_text(fmt, page, total, free))
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


def name_only_preview(paper_name: str, dots: str, name: str, total: int) -> NamePreview:
    """What the ``total`` pages of a wrapped printout at dot size ``dots`` print
    for ``name``: the name alone, as much as the layout's label holds."""
    fmt = get_layout(paper_name, dots).fmt
    dropped = "".join(dict.fromkeys(ch for ch in name if not _drawable(ch)))
    last = max(total, 1)
    wanted = "".join(ch for ch in name if _drawable(ch))
    cut = len(_printed_free_text(fmt, name, last, total)) < len(wanted.rstrip(" "))
    return NamePreview(total, _printed_free_text(fmt, name, 1, total), dropped, cut)
