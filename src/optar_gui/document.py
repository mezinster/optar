# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The document rules: which scan is which page of which printout.

Plain Python, no Qt and no numpy, so every rule here is testable on its own.

Purity. The state is a function of the scans (add order, identities, outcomes,
states), of the ordered user operations (``switch_to``, ``start_by_hand``,
``assign_page``, ``use_scan``, ``remove_scan``) and of which background results
were known when each user operation was made. It does not depend on the order in
which background results (``set_working``, ``set_identified``, ``set_outcome``,
``set_unreadable``, ``set_decoding``) arrive between user operations: everything shown is
recomputed from that information after every change, and a user's choice is
never lost or changed by a passing intermediate state.

Scans. ``add_scan`` refuses a path whose ``os.path.realpath``, after
``os.path.normcase``, is already present; ``ScanView.path`` is the path as given.
Whether the path exists, or is empty, is the caller's business. On Windows two
spellings of one file that differ in case are the same scan; on other systems
whose file systems ignore case (macOS) they are not recognised as one.

Grouping. A scan is *grouped* when it is identified, not unreadable and its page
lies in ``1..max(total, 1)``; a page outside that range makes it unreadable with
the reason ``"page number out of range"``. A label read off a scan is not
trusted: a total above ``MAX_TOTAL_PAGES`` (the encoder's limit) makes the scan
unreadable with the reason ``"page count out of range"``, so no document ever has
more pages than a real printout can. ``set_unreadable`` is final and keeps
the identity for display.

- A tagged scan belongs to the group of its ``(format, total, tag)``.
- Untagged scans are taken in add order. Each joins the first existing untagged
  group with the same format and total whose every member's name is
  prefix-compatible with its own (one is a prefix of the other, trailing spaces
  ignored); otherwise it starts a new group. Prefix compatibility is not
  transitive (``a`` matches ``ab`` and ``ac``, which do not match each other), so
  this order is what makes the grouping deterministic. A later-added scan never
  changes the group of an earlier one.
- A tagged and an untagged scan are never in the same group.
- A group's key is the id of its earliest-added scan; ``switch_to(key)`` switches
  to the group that now contains that scan, so an old key keeps working.
- A group's title comes from the names of the grouped scans it shows ("" if
  none), trailing spaces ignored; a scan assigned by hand into another document
  does not count. A tagged group takes the most common name (on a tie, the
  longest): its labels are accepted on a plausible reading, so one misread name
  must not rename it. An untagged group takes the longest name; its names are
  prefixes of one another by construction.

Remembering a document. User operations remember a document as a *reference*:
the set of scans in its group at the moment of the operation, plus, for a tagged
document, its identity ``(format, total, tag)``. A reference *resolves* to the
group holding its earliest-added grouped scan; if none of its scans is grouped
and it has a tagged identity, to the group with exactly that identity, if there
is one (a later page of the same printout, since a tag names one printout);
otherwise to nothing. A started-by-hand document is remembered as itself.

Which group is the document.

- A document started with ``start_by_hand`` is the document until ``switch_to``,
  another ``start_by_hand``, or until every scan is removed. It comes first among
  the untagged groups, so matching untagged scans join it, and it exists with no
  scans at all.
- Otherwise, if the user has made a choice and it resolves, the document is the
  group it resolves to. If it does not resolve, the default rule applies, and the
  choice takes effect again as soon as it resolves.
- Otherwise (default rule) the document is the group of the earliest-added
  grouped scan.

The choice. Background results never change it; user operations do.
``switch_to`` replaces it with a reference to the target group. ``assign_page``,
``use_scan`` and ``remove_scan`` are made while looking at the current document:
they add the current group's scans to the choice and give it the current group's
identity (``remove_scan`` only when the scan removed is in the current group or
the choice resolves to it, so a document with scans left is not abandoned).
``remove_scan`` then takes the removed scan out. The choice is dropped by
``switch_to``, ``start_by_hand``, or when it has no scans left.

Pages given by hand and scans chosen by hand. ``assign_page`` and ``use_scan``
remember the current document as a reference (or the hand-started document).
They apply whenever that reference resolves to the current document, and are
inactive, not deleted, otherwise. ``remove_scan`` updates the references that
resolve to the current document the same way as the choice. An active assignment
puts the scan into that page of the document whatever its label or state says;
it is listed in neither ``others()`` nor ``unreadable()``. An inactive one leaves
the scan where its own identity puts it. Both are deleted when their scan is
removed, when the user re-assigns or re-chooses, when the user leaves their
document with ``switch_to`` or ``start_by_hand``, or when their reference has no
scans left.

For a tagged document, a choice and an assignment made in the same operation
always resolve to the same group. Known limit of untagged documents: name chains
are not transitive, so a later identification can split a group, and a reference
follows its earliest-added grouped scan. Example: scans ``ac``, ``a``, ``ab``
added in that order; the user chooses the group of ``ab`` while ``a`` and ``ab``
are grouped together and ``ac`` is not yet identified. When ``ac`` is
identified, ``a`` joins it and ``ab`` is left alone, so the document becomes
``{ac, a}``, not the ``ab`` the user picked. A second route, through an
assignment: the user switches to a printout whose only scan is ``ab``; the
earlier-added ``a`` is then identified and joins it; the user assigns a page; then
``ac``, added before both, is identified. The choice and the assignment remember
``{a, ab}`` and follow ``a``, so the document becomes the group of ``ac`` and
``a``, with the assignment still active. Without the assignment the choice is
still ``{ab}`` and the document stays ``ab``.

A scan is expected to be identified once. Calling ``set_identified`` again with
different information is allowed and replaces it, but the guarantees above about
choices and assignments resolving to the same document assume that a scan's
identity does not change.

Pages. ``slots()`` has one slot per page ``1..max(total, 1)`` of the document.
Within a page the scan in use is the one chosen with ``use_scan``; otherwise the
one with the best outcome (fewest lost, then fewest repaired, then earliest
added), scans with no outcome last. Spares follow in the same order.

Health. ``pages()`` gives each slot a health from its scan in use: no scan is
``MISSING``; a scan waiting or working is ``WAITING`` or ``WORKING`` (an
identified scan with no outcome yet is still working); an unreadable scan (one
assigned by hand stays in its slot) is ``UNREADABLE``; otherwise the outcome
decides: any lost block is ``DAMAGED``, else any repaired block is ``REPAIRED``,
else ``GOOD``. ``PageView.reason`` says why an unreadable page is unreadable.

Formats. A scan has its own page (``set_outcome`` without a format), laid out in
the format its label gives (or taken as it is when no label was read), and at
most one page per other format, decoded without its label for a document it was
put into by hand (``set_outcome`` with that format). A failed decode in a format
(``set_unreadable`` with that format) is kept per format too: it never makes the
scan unreadable, never drops its identity, its own page or another format's page.
So a scan assigned to another document by mistake and decoded there is, back in
its own document, its own page exactly as before. ``set_decoding`` records that a
decode in a format has been asked for, from the moment it is queued until it
reports. A scan assigned by hand is seen only through the document's format: it is
``WORKING`` while a decode in that format is pending, ranks, shows and gives data
only by its page in that format, is ``UNREADABLE`` with that decode's reason when it
failed, and otherwise (no page in this format but one in another) ``UNREADABLE``
with the reason ``FORMAT_MISMATCH``, giving zeros. ``needs_decoding`` says when a
scan put into the document by hand has no page in its format yet. Memory: a page
is about 200 kB; a scan holds at most one page per paper format, and only scans
assigned by hand are ever decoded in a second format.

Page size. A document has one page size: the outcome length of the earliest-added
of its group's own scans (not those assigned by hand) that has an outcome; if none
has one yet, that of the earliest-added assigned scan in use that has one. A scan
in use whose outcome has another length (another paper size) cannot be used for
its page: the page is ``UNREADABLE`` with the reason ``"page size does not match
this document"`` and gives zeros.

The whole document. ``summary()`` is ``EMPTY`` with no document; ``WORKING``
while any page is waiting or working; ``VERIFIED`` or ``MISMATCH`` when every page
is good or repaired and the document has a tag, by assembling the file and
checking it against the tag; ``UNVERIFIABLE`` when every page is good or repaired
and there is no tag; otherwise ``INCOMPLETE``. The verdict is cached until the
scans in use, their outcomes or the tag change.

Checking off the interface thread. Hashing a large file takes seconds, so the
window does not let ``summary()`` hash a large document. ``summary(verify=False)``
never hashes: where ``summary()`` would have to, it reports ``CHECKING`` instead.
``verdict_job()`` returns ``None`` when ``summary()`` would not hash (no complete
tagged document, or the verdict is cached); otherwise a ``VerdictJob``, a snapshot
of the pages in use, safe to run on another thread while the document changes. Its
result goes back through ``accept_verdict``, which caches it for exactly the bytes
it hashed, so a verdict for a state that has since changed is never shown.

Assembling. ``chunks()`` yields the recovered file page by page, ``1..max(total,
1)`` in order, without building it in memory. A page whose scan in use has an
outcome gives its data, damaged or not; any other page gives ``page_bytes`` zero
bytes (one shared block), so later pages keep their offsets. With a tag the file
is cut to the tag's size. ``assemble()`` joins the chunks, for small documents.
The verdict is computed by hashing the chunks as they are produced.
``suggested_name`` is a plain file name made from the label (which is untrusted):
no directories, no characters Windows refuses, no device names; otherwise
``"recovered.bin"``.

What the window offers. The window lists the pages of the document (each followed
by its spares), the other groups and the unreadable scans; ``Row`` names these
kinds of row. ``actions(kind, key)`` says which actions apply to a row, as an
``Actions`` whose fields are what each action acts on (None: not offered):

- a page (key: its number) can have its scan replaced, and its scan in use, if
  any, removed;
- a spare (key: its scan) can be put in use or removed;
- another group (key: its key) can be switched to; one with a single scan can
  also have that scan assigned to a page of the document;
- an unreadable scan (key: its scan) can be removed, and assigned to a page when
  there is a document.

``can_start_by_hand`` is true when there is no document but there are unreadable
scans to put into one. ``replacement_fit(scan_id, page)`` says whether a scan
added to replace a page identifies as that page of the current document (same
group: same format, total and tag or name), and if not, what it is instead; a
scan of that page that gives no usable data is ``UNUSABLE`` when the page has
usable data, so it never replaces it, and one still being read in the document's
format is ``PENDING``. ``page_in_current`` says which page of the document a scan is
in. ``paper_for_size`` guesses a paper from an
image's shape, for starting a document by hand.
``page_with(scan_id)`` is the page a scan of the document is in, as it would be
with that scan in use, so a spare's health can be shown. ``suggested_page``
offers a page to assign a scan to: the page its own label names if the document
has it, else the first page with no scan, else page 1.

Scan files. ``expand_paths`` turns the paths a user drops or picks into scans to
add: a folder gives the files directly inside it with a ``SCAN_EXTENSIONS``
extension (any case), sorted by name, without recursing; any other path is kept.

Cost. Background results only mark the layout stale; it is recomputed, in time
linear in the number of scans and pages (times the number of untagged groups for
untagged scans), when it is next read.
"""

from __future__ import annotations

import hashlib
import os
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Only for annotations: importing the optar package at run time loads numpy, and
    # tags are only compared and hashed here.
    from optar.tag import Tag

OUT_OF_RANGE = "page number out of range"
COUNT_OUT_OF_RANGE = "page count out of range"
SIZE_MISMATCH = "page size does not match this document"
FORMAT_MISMATCH = "decoded for another page format"
# The encoder's page limit (optar.encoder.MAX_PAGES), repeated here because
# importing optar at run time loads numpy.
MAX_TOTAL_PAGES = 9999
RECOVERED_NAME = "recovered.bin"
# The extensions of the image files ``optar.imageio.read_scan`` accepts.
SCAN_EXTENSIONS = (".png", ".tif", ".tiff", ".bmp", ".pgm", ".ppm", ".jpg", ".jpeg")


def paper_for_size(size: tuple[int, int]) -> str | None:
    """The paper (its name in ``optar.format``) whose shape is closest to an image of
    ``size`` (width, height) in either orientation; None for an empty size."""
    if min(size) <= 0:
        return None
    # Imported here: loading the optar package loads numpy, which importing this
    # module must not.
    from optar.format import PAPERS

    short, long = sorted(size)
    return min(
        PAPERS, key=lambda n: abs(PAPERS[n].width_pt / PAPERS[n].height_pt - short / long)
    )


def expand_paths(paths: Iterable[str]) -> list[str]:
    """The scans to add for ``paths``: a folder gives the image files directly in it,
    sorted by name; anything else is kept as given."""
    found: list[str] = []
    for path in paths:
        if not os.path.isdir(path):
            found.append(path)
            continue
        try:
            names = sorted(os.listdir(path))
        except OSError:
            continue  # a folder that cannot be listed has nothing to add
        for name in names:
            full = os.path.join(path, name)
            if name.lower().endswith(SCAN_EXTENSIONS) and os.path.isfile(full):
                found.append(full)
    return found


@dataclass(frozen=True)
class ScanInfo:
    """What a scan's label says it is."""

    format: str
    total: int
    page: int
    name: str
    tag: Tag | None


@dataclass(frozen=True)
class PageOutcome:
    """The result of decoding one page.

    ``histogram`` counts the symbols with 0, 1, 2 and 3 corrected bits.
    """

    data: bytes
    histogram: tuple[int, int, int, int]
    lost: int

    @property
    def repaired(self) -> int:
        return sum(self.histogram[1:])

    @property
    def bytes(self) -> int:
        return len(self.data)


class ScanState:
    WAITING = "waiting"
    WORKING = "working"
    DONE = "done"
    UNREADABLE = "unreadable"


@dataclass(frozen=True)
class ScanView:
    id: int
    path: str
    state: str
    info: ScanInfo | None
    outcome: PageOutcome | None
    reason: str


@dataclass(frozen=True)
class GroupView:
    key: object
    title: str
    total: int
    format: str
    tag: Tag | None
    scan_ids: tuple[int, ...]


@dataclass(frozen=True)
class PageSlot:
    number: int
    scan_id: int | None
    spare_ids: tuple[int, ...]


class Health:
    GOOD = "good"
    REPAIRED = "repaired"
    DAMAGED = "damaged"
    UNREADABLE = "unreadable"
    MISSING = "missing"
    WAITING = "waiting"
    WORKING = "working"


# Pages that count towards a complete document.
_SOUND = (Health.GOOD, Health.REPAIRED)


@dataclass(frozen=True)
class PageView:
    number: int
    health: str
    scan_id: int | None
    spare_ids: tuple[int, ...]
    repaired: int
    lost: int
    histogram: tuple[int, int, int, int] | None
    reason: str = ""  # why an unreadable page is unreadable


class DocState:
    EMPTY = "empty"
    WORKING = "working"
    INCOMPLETE = "incomplete"
    UNVERIFIABLE = "unverifiable"
    VERIFIED = "verified"
    MISMATCH = "mismatch"
    CHECKING = "checking"  # summary(verify=False) only: complete, verdict not known yet


class Row:
    """The kinds of row of the window's list that ``Document.actions`` knows."""

    PAGE = "page"  # key: page number
    SPARE = "spare"  # key: scan id
    OTHER = "other"  # key: group key
    UNREADABLE = "unreadable"  # key: scan id


@dataclass(frozen=True)
class Actions:
    """What each action applies to for a selected row; None when it is not offered."""

    remove: int | None = None  # the scan Remove removes
    replace: int | None = None  # the page whose scan is replaced
    use_spare: int | None = None  # the spare put in use
    switch: object | None = None  # the key of the group switched to
    assign: int | None = None  # the scan assigned to a page


NO_ACTIONS = Actions()


class Fit:
    """How a scan added to replace a page fits; see ``Document.replacement_fit``."""

    PENDING = "pending"  # not identified yet
    THIS_PAGE = "this page"
    UNUSABLE = "unusable"  # this page, but no usable data where the page has some
    OTHER_PAGE = "other page"  # another page of the current document
    OTHER_DOCUMENT = "other document"
    UNREADABLE = "unreadable"


@dataclass(frozen=True)
class Summary:
    state: str
    good: int
    repaired: int
    damaged: int
    unreadable: int
    missing: int
    size: int | None  # the tag's size, or None without a tag


@dataclass(frozen=True)
class Verdict:
    """Whether the bytes identified by ``key`` match the tag."""

    key: tuple
    matches: bool


class VerdictJob:
    """Hashes a snapshot of a complete tagged document; see ``Document.verdict_job``.

    ``size`` is the number of bytes it hashes. Calling it returns a ``Verdict``, or
    None once ``cancelled()`` is true. It holds only immutable page data, so it may
    run on any thread while the document changes.
    """

    def __init__(self, key: tuple, size: int, chunks: Iterator[bytes], tag: Tag) -> None:
        self.key = key
        self.size = size
        self._chunks = chunks
        self._tag = tag

    def __call__(self, cancelled: Callable[[], bool] = lambda: False) -> Verdict | None:
        matches = _matches(self._chunks, self._tag, cancelled)
        return None if matches is None else Verdict(self.key, matches)


def _matches(
    chunks: Iterable[bytes], tag: Tag, cancelled: Callable[[], bool] = lambda: False
) -> bool | None:
    """Whether the chunks make a file of the tag's size and fingerprint; None if cancelled."""
    digest = hashlib.sha256()
    produced = 0
    for chunk in chunks:
        if cancelled():
            return None
        digest.update(chunk)
        produced += len(chunk)
    fingerprint = digest.hexdigest()[: len(tag.fingerprint)]
    return produced == tag.size and fingerprint == tag.fingerprint


@dataclass
class _Scan:
    id: int
    path: str  # as given
    real: str  # ``_file_key`` of the path, for spotting the same file added twice
    working: bool = False
    info: ScanInfo | None = None
    outcome: PageOutcome | None = None
    outcome_serial: int = 0  # changes with every outcome, for the verdict cache
    # Pages decoded without the label in a format given by the caller, and why a
    # decode in a format failed, by format; never more than one per page format.
    decoded: dict[str, tuple[PageOutcome, int]] = field(default_factory=dict)
    failed: dict[str, str] = field(default_factory=dict)
    decoding: set[str] = field(default_factory=set)  # formats being decoded in
    unreadable_reason: str | None = None


@dataclass
class _Group:
    format: str
    total: int
    tag: Tag | None
    members: list[int] = field(default_factory=list)  # grouped scans, add order
    # Untagged: the longest member name, trailing spaces stripped. Members are pairwise
    # prefix-compatible, so all are prefixes of it, and a name is compatible with every
    # member exactly when it is compatible with this one.
    longest: str = ""


@dataclass(frozen=True)
class _Table:
    """The pages of the current document as the health and the file see them."""

    views: tuple[PageView, ...]
    usable: tuple[PageOutcome | None, ...]  # per page: the data it contributes, if any
    page_bytes: int | None
    key: tuple  # identifies the bytes the pages produce, for the verdict cache


@dataclass(frozen=True, eq=False)
class _HandDocument:
    """A document the user started by hand; compared by identity."""

    format: str
    total: int


@dataclass(frozen=True)
class _Choice:
    """A document remembered by its scans and, if tagged, by its identity."""

    members: frozenset[int]
    identity: tuple | None  # (format, total, tag) of a tagged document, else None


# Which document a user operation was made in.
_Anchor = _HandDocument | _Choice


def _identity(g: _Group) -> tuple | None:
    return (g.format, g.total, g.tag) if g.tag is not None else None


@dataclass
class _Layout:
    """Everything shown, computed from the state after each change."""

    current: _Group | None = None  # the document's group (grouped members)
    anchor: _Anchor | None = None  # how operations made now remember the document
    shown: list[int] = field(default_factory=list)  # current members not moved by hand
    assigned: dict[int, int] = field(default_factory=dict)  # active: scan -> page
    preferred: dict[int, int] = field(default_factory=dict)  # active: scan -> serial
    others: list[tuple[_Group, list[int]]] = field(default_factory=list)  # group, shown
    groups: list[_Group] = field(default_factory=list)  # every group, current included
    group_of: dict[int, _Group] = field(default_factory=dict)  # grouped scan -> its group
    # Computed on first use from the above; the layout is replaced after every change.
    slots: tuple[PageSlot, ...] | None = None
    table: _Table | None = None


def _pages(total: int) -> int:
    return max(total, 1)


def _prefix_compatible(a: str, b: str) -> bool:
    """Whether one name is a prefix of the other; both already stripped."""
    return a.startswith(b) or b.startswith(a)


_RESERVED_NAMES = frozenset(
    ["CON", "PRN", "AUX", "NUL"]
    + [f"COM{n}" for n in range(1, 10)]
    + [f"LPT{n}" for n in range(1, 10)]
)
_BAD_NAME_CHARACTERS = frozenset('<>:"/\\|?*' + "".join(map(chr, range(32))) + chr(127))


def _file_key(path: str) -> str:
    """The same for two paths of one file: resolved, and folded where the system
    ignores case (``os.path.normcase``; Windows)."""
    return os.path.normcase(os.path.realpath(path))


def _safe_file_name(name: str) -> str:
    """A plain file name, valid on Windows too, made from untrusted label text."""
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(c for c in name if c not in _BAD_NAME_CHARACTERS).strip(" .")
    if not name or name.split(".", 1)[0].strip().upper() in _RESERVED_NAMES:
        return RECOVERED_NAME
    return name


class Document:
    """The scans the user added and the rules that place them into pages."""

    def __init__(self) -> None:
        self._scans: dict[int, _Scan] = {}  # insertion order is add order; ids increase
        self._next_id = 1
        self._hand: _HandDocument | None = None
        self._choice: _Choice | None = None
        self._assigned: dict[int, tuple[_Anchor, int]] = {}  # scan -> (document, page)
        self._preferred: dict[int, tuple[_Anchor, int]] = {}  # scan -> (document, serial)
        self._serial = 0
        self._outcomes = 0  # outcomes recorded so far
        self._verdict: tuple[tuple, bool] | None = None  # (what was assembled, matches)
        self._reals: dict[str, int] = {}  # resolved path -> scan
        self._lay = _Layout()
        self._dirty = False  # the layout is recomputed when next read

    # --- Adding and reporting on scans ---------------------------------------

    def add_scan(self, path: str) -> int | None:
        real = _file_key(path)
        if real in self._reals:
            return None
        scan_id = self._next_id
        self._next_id += 1
        self._scans[scan_id] = _Scan(scan_id, path, real)
        self._reals[real] = scan_id
        self._changed()
        return scan_id

    def set_working(self, scan_id: int, working: bool = True) -> None:
        """Records that the scan's work started, or (``working=False``) that it ended.

        Only a scan assigned by hand that is unreadable needs the end: its work is
        decoding it without a label, and until that reports it shows as working.
        """
        self._get(scan_id).working = working
        self._changed()

    def set_identified(self, scan_id: int, info: ScanInfo) -> None:
        """Records what the scan's label says.

        A scan is expected to be identified once. A second call with different
        information replaces the first, but the guarantees about choices and
        assignments resolving to the same document assume the identity does not
        change.
        """
        self._get(scan_id).info = info
        self._changed()

    def set_outcome(
        self, scan_id: int, outcome: PageOutcome, format: str | None = None
    ) -> None:
        """Records a decoded page. Without ``format`` it is the scan's own page, in
        the format its label gives (``ScanInfo.format``). With ``format`` it was
        decoded without its label in that format, for a document the scan was put
        into by hand; it is kept beside the scan's own page and any other format's,
        and replaces only an earlier decode in the same format."""
        s = self._get(scan_id)
        self._outcomes += 1
        if format is None:
            s.outcome = outcome
            s.outcome_serial = self._outcomes
        else:
            s.decoded[format] = (outcome, self._outcomes)
            s.failed.pop(format, None)
        self._changed()

    def set_unreadable(self, scan_id: int, reason: str, format: str | None = None) -> None:
        """Records why the scan could not be read. Without ``format`` this is final
        for the scan itself. With ``format`` only its decode in that format failed:
        the scan keeps its identity, its own page and pages in other formats."""
        s = self._get(scan_id)
        if format is None:
            s.unreadable_reason = reason
        else:
            s.failed[format] = reason
            s.decoded.pop(format, None)
        self._changed()

    def set_decoding(self, scan_id: int, format: str, pending: bool) -> None:
        """Records that a decode of the scan in ``format`` has been asked for
        (``pending``), from the moment it is queued, or that it has reported. Until
        it reports, the scan counts as being read in that format."""
        s = self._get(scan_id)
        if pending:
            s.decoding.add(format)
        else:
            s.decoding.discard(format)
        self._changed()

    # --- User operations -------------------------------------------------------

    def remove_scan(self, scan_id: int) -> None:
        self._get(scan_id)
        lay = self._layout
        current = lay.current
        # Removing is done while looking at the current document: what remembers that
        # document takes in its remaining scans, so it is not abandoned while it has any.
        if self._hand is None and current is not None and (
            scan_id in current.members or self._resolves_to_current(self._choice)
        ):
            self._choice = self._grown(self._choice)
        if self._choice is not None:
            self._choice = self._without(self._choice, scan_id)
        del self._reals[self._scans.pop(scan_id).real]
        self._assigned.pop(scan_id, None)
        self._preferred.pop(scan_id, None)
        for marks in (self._assigned, self._preferred):
            for other, (anchor, value) in list(marks.items()):
                if isinstance(anchor, _HandDocument):
                    continue
                if self._resolves_to_current(anchor):
                    anchor = self._grown(anchor)
                anchor = self._without(anchor, scan_id)
                if anchor is None:
                    del marks[other]  # every scan of its document is gone
                else:
                    marks[other] = (anchor, value)
        if not self._scans:
            self._hand = None
            self._choice = None
            self._assigned.clear()
            self._preferred.clear()
        self._changed()

    def assign_page(self, scan_id: int, page: int) -> None:
        self._get(scan_id)
        current = self._require_current()
        if not 1 <= page <= _pages(current.total):
            raise ValueError(f"page {page} is outside 1..{_pages(current.total)}")
        self._pin()
        self._assigned[scan_id] = (self._layout.anchor, page)
        self._preferred.pop(scan_id, None)
        self._changed()

    def use_scan(self, scan_id: int) -> None:
        self._get(scan_id)
        self._require_current()
        page = self._page_in_current(scan_id)
        if page is None:
            raise ValueError(f"scan {scan_id} is not a page of the current document")
        self._pin()
        for other in self._layout.preferred:
            if other != scan_id and self._page_in_current(other) == page:
                del self._preferred[other]
        self._serial += 1
        self._preferred[scan_id] = (self._layout.anchor, self._serial)
        self._changed()

    def switch_to(self, key: object) -> None:
        lay = self._layout
        if lay.current is not None and (
            key in lay.shown or key in lay.assigned or (key is None and self.current.key is None)
        ):
            return
        target = next((g for g, shown in lay.others if key in shown), None)
        if target is None:
            raise KeyError(key)
        self._leave_document()
        self._choice = _Choice(frozenset(target.members), _identity(target))
        self._changed()

    def start_by_hand(self, format: str, total: int) -> None:
        if not 0 <= total <= MAX_TOTAL_PAGES:
            raise ValueError(f"total must be between 0 and {MAX_TOTAL_PAGES}")
        self._leave_document()
        self._hand = _HandDocument(format, total)
        self._changed()

    # --- Reading the state -----------------------------------------------------

    def scan(self, scan_id: int) -> ScanView:
        return self._view(self._get(scan_id))

    def scan_id_of(self, path: str) -> int | None:
        """The scan added for the same file as ``path``, if any."""
        return self._reals.get(_file_key(path))

    def scans(self) -> tuple[ScanView, ...]:
        return tuple(self._view(s) for s in self._scans.values())

    @property
    def current(self) -> GroupView | None:
        lay = self._layout
        if lay.current is None:
            return None
        ids = tuple(sorted(lay.shown + list(lay.assigned)))
        return self._group_view(lay.current, lay.shown, ids)

    @property
    def by_hand(self) -> bool:
        """Whether the current document was started with ``start_by_hand``."""
        return self._hand is not None

    def slots(self) -> tuple[PageSlot, ...]:
        lay = self._layout
        if lay.slots is None:
            lay.slots = self._make_slots(lay)
        return lay.slots

    def _make_slots(self, lay: _Layout) -> tuple[PageSlot, ...]:
        if lay.current is None:
            return ()
        by_page: dict[int, list[int]] = {}
        for scan_id in lay.shown:
            by_page.setdefault(self._scans[scan_id].info.page, []).append(scan_id)
        for scan_id, page in lay.assigned.items():
            by_page.setdefault(page, []).append(scan_id)
        slots = []
        for page in range(1, _pages(lay.current.total) + 1):
            ranked = by_page.get(page)
            if not ranked:
                slots.append(PageSlot(page, None, ()))
                continue
            if len(ranked) > 1:
                ranked.sort(key=self._rank)
                chosen = [s for s in ranked if s in lay.preferred]
                if chosen:
                    pick = max(chosen, key=lay.preferred.__getitem__)
                    ranked.remove(pick)
                    ranked.insert(0, pick)
            slots.append(PageSlot(page, ranked[0], tuple(ranked[1:])))
        return tuple(slots)

    def pages(self) -> tuple[PageView, ...]:
        return self._table().views

    def summary(self, verify: bool = True) -> Summary:
        """The state of the whole document and its page counts.

        For a complete tagged document this hashes the whole recovered file, once per
        change (the verdict is cached). That takes seconds for a very large document;
        with ``verify=False`` nothing is hashed and an unknown verdict is ``CHECKING``
        (see ``verdict_job``).
        """
        cur = self._layout.current
        if cur is None:
            return Summary(DocState.EMPTY, 0, 0, 0, 0, 0, None)
        healths = [p.health for p in self.pages()]
        tally = {h: healths.count(h) for h in set(healths)}
        if tally.get(Health.WAITING) or tally.get(Health.WORKING):
            state = DocState.WORKING
        elif all(h in _SOUND for h in healths):
            if cur.tag is None:
                state = DocState.UNVERIFIABLE
            else:
                verified = self._verified(cur.tag, verify)
                if verified is None:
                    state = DocState.CHECKING
                else:
                    state = DocState.VERIFIED if verified else DocState.MISMATCH
        else:
            state = DocState.INCOMPLETE
        return Summary(
            state,
            tally.get(Health.GOOD, 0),
            tally.get(Health.REPAIRED, 0),
            tally.get(Health.DAMAGED, 0),
            tally.get(Health.UNREADABLE, 0),
            tally.get(Health.MISSING, 0),
            cur.tag.size if cur.tag is not None else None,
        )

    def verdict_job(self) -> VerdictJob | None:
        """A job that checks the file against the tag, or None when ``summary()``
        would not hash anything (no complete tagged document, or verdict cached)."""
        cur = self._layout.current
        if cur is None or cur.tag is None:
            return None
        if not all(p.health in _SOUND for p in self.pages()):
            return None
        key = (cur.tag, self._table().key)
        if self._verdict is not None and self._verdict[0] == key:
            return None
        table = self._table()
        chunks = self._chunks(list(table.usable), bytes(table.page_bytes), cur.tag.size)
        return VerdictJob(key, cur.tag.size, chunks, cur.tag)

    def accept_verdict(self, verdict: Verdict | None) -> None:
        """Caches a ``VerdictJob``'s result; it only counts for the bytes it hashed."""
        if verdict is not None:
            self._verdict = (verdict.key, verdict.matches)

    @property
    def page_bytes(self) -> int | None:
        """The document's page size (see the module docstring), or None."""
        return self._table().page_bytes

    def chunks(self) -> Iterator[bytes]:
        """The recovered file, page by page; cut to the tag's size with a tag.

        Checks before anything is produced: raises ``ValueError`` when no page has
        usable data.
        """
        table = self._table()
        if not any(o is not None for o in table.usable):
            raise ValueError("no page has been decoded")
        tag = self._layout.current.tag
        blank = bytes(table.page_bytes)
        return self._chunks(list(table.usable), blank, None if tag is None else tag.size)

    @staticmethod
    def _chunks(
        outcomes: list[PageOutcome | None], blank: bytes, size: int | None
    ) -> Iterator[bytes]:
        left = size
        for o in outcomes:
            chunk = o.data if o is not None else blank
            if left is not None:
                if left <= 0:
                    return
                if len(chunk) > left:
                    chunk = chunk[:left]
                left -= len(chunk)
            yield chunk

    def assemble(self) -> bytes:
        """The whole recovered file in memory; callers that save use ``chunks()``."""
        return b"".join(self.chunks())

    @property
    def can_save(self) -> bool:
        return any(o is not None for o in self._table().usable)

    @property
    def suggested_name(self) -> str:
        """A plain file name made from the label, which is untrusted text."""
        cur = self.current
        return _safe_file_name(cur.title if cur is not None else "")

    # --- What the window offers ---------------------------------------------------

    def actions(self, kind: str, key: object) -> Actions:
        """The actions that apply to a row of the window's list (see the module
        docstring); ``NO_ACTIONS`` for a row that is not or no longer there."""
        lay = self._layout
        if lay.current is None:
            if kind == Row.UNREADABLE and self._listed_unreadable(key):
                return Actions(remove=key)
            return NO_ACTIONS
        if kind == Row.PAGE:
            slots = self.slots()
            if not isinstance(key, int) or not 1 <= key <= len(slots):
                return NO_ACTIONS
            return Actions(remove=slots[key - 1].scan_id, replace=key)
        if kind == Row.SPARE:
            page = self._page_in_current(key) if key in self._scans else None
            if page is None or key not in self.slots()[page - 1].spare_ids:
                return NO_ACTIONS
            return Actions(remove=key, use_spare=key)
        if kind == Row.OTHER:
            shown = next((shown for _, shown in lay.others if shown[0] == key), None)
            if shown is None:
                return NO_ACTIONS
            return Actions(switch=key, assign=shown[0] if len(shown) == 1 else None)
        if kind == Row.UNREADABLE and self._listed_unreadable(key):
            return Actions(remove=key, assign=key)
        return NO_ACTIONS

    def _listed_unreadable(self, scan_id: object) -> bool:
        s = self._scans.get(scan_id) if isinstance(scan_id, int) else None
        return (
            s is not None
            and s.id not in self._layout.assigned
            and self._unreadable_reason(s) is not None
        )

    @property
    def can_start_by_hand(self) -> bool:
        """No document, but unreadable scans that could be put into one by hand."""
        return self._layout.current is None and any(
            self._unreadable_reason(s) is not None for s in self._scans.values()
        )

    def replacement_fit(self, scan_id: int, page: int) -> str:
        """Whether the scan is page ``page`` of the current document; a ``Fit``."""
        s = self._get(scan_id)
        in_page = self._page_in_current(scan_id)
        if in_page == page:
            if self._status(s)[0] in (ScanState.WAITING, ScanState.WORKING):
                return Fit.PENDING
            usable = self.page_with(scan_id).histogram is not None
            if not usable and self.pages()[page - 1].histogram is not None:
                return Fit.UNUSABLE
            return Fit.THIS_PAGE
        if in_page is not None:
            return Fit.OTHER_PAGE
        if self._unreadable_reason(s) is not None:
            return Fit.UNREADABLE
        if s.info is None:
            return Fit.PENDING
        return Fit.OTHER_DOCUMENT

    def page_with(self, scan_id: int) -> PageView:
        """The page of the current document the scan is in, as it would be with this
        scan in use. Raises ValueError when it is not a page of the current document."""
        self._get(scan_id)
        page = self._page_in_current(scan_id)
        if page is None:
            raise ValueError(f"scan {scan_id} is not a page of the current document")
        slot = self.slots()[page - 1]
        spares = tuple(i for i in (slot.scan_id, *slot.spare_ids) if i != scan_id)
        view, _ = self._page_view(PageSlot(page, scan_id, spares), self.page_bytes)
        return view

    def needs_decoding(self, scan_id: int) -> bool:
        """Whether the scan, put into the current document by hand, must be decoded
        (without its label, in the document's format) before it gives a page: it
        has no decoded page, or one decoded in another format. Raises ValueError
        when there is no document."""
        s = self._get(scan_id)
        return self._out(s, self._require_current().format) is None

    def page_in_current(self, scan_id: int) -> int | None:
        """The page of the current document the scan is in (by its label or by hand)."""
        self._get(scan_id)
        return self._page_in_current(scan_id)

    @staticmethod
    def _out(s: _Scan, format: str) -> tuple[PageOutcome, int] | None:
        """The scan's page decoded in ``format`` and its serial, or None: its own page
        when its label gives that format, else its decode in that format, else (no
        label read) an own page whose format nobody stated."""
        own = (s.outcome, s.outcome_serial) if s.outcome is not None else None
        if own is not None and s.info is not None and s.info.format == format:
            return own
        if format in s.decoded:
            return s.decoded[format]
        return own if s.info is None else None

    def suggested_page(self, scan_id: int) -> int:
        """The page to offer when assigning the scan; see the module docstring.

        Raises ValueError when there is no document."""
        s = self._get(scan_id)
        slots = self.slots()
        if not slots:
            raise ValueError("there is no document")
        if s.info is not None and 1 <= s.info.page <= len(slots):
            return s.info.page
        return next((slot.number for slot in slots if slot.scan_id is None), 1)

    def others(self) -> tuple[GroupView, ...]:
        return tuple(self._group_view(g, shown, tuple(shown)) for g, shown in self._layout.others)

    def unreadable(self) -> tuple[ScanView, ...]:
        return tuple(
            self._view(s)
            for s in self._scans.values()
            if s.id not in self._layout.assigned and self._unreadable_reason(s) is not None
        )

    # --- Internals -------------------------------------------------------------

    def _get(self, scan_id: int) -> _Scan:
        try:
            return self._scans[scan_id]
        except (KeyError, TypeError):
            raise KeyError(scan_id) from None

    def _require_current(self) -> _Group:
        if self._layout.current is None:
            raise ValueError("there is no document")
        return self._layout.current

    def _pin(self) -> None:
        """Working in the current document adds it to the user's choice."""
        if self._hand is None:
            self._choice = self._grown(self._choice)

    def _grown(self, choice: _Choice | None) -> _Choice:
        """A choice that also holds the current group's scans and takes its identity."""
        current = self._layout.current
        old = choice.members if choice is not None else frozenset()
        return _Choice(old | frozenset(current.members), _identity(current))

    @staticmethod
    def _without(choice: _Choice, scan_id: int) -> _Choice | None:
        members = choice.members - {scan_id}
        return _Choice(members, choice.identity) if members else None

    def _resolves_to_current(self, anchor: _Anchor | None) -> bool:
        lay = self._layout
        if anchor is None or lay.current is None:
            return False
        if isinstance(anchor, _HandDocument):
            return anchor is self._hand
        return self._resolve(anchor, lay.group_of, lay.groups) is lay.current

    def _leave_document(self) -> None:
        """Drops what the user did in the current document, and any choice."""
        lay = self._layout
        for scan_id in lay.assigned:
            del self._assigned[scan_id]
        for scan_id in lay.preferred:
            del self._preferred[scan_id]
        self._hand = None
        self._choice = None

    def _page_in_current(self, scan_id: int) -> int | None:
        lay = self._layout
        if scan_id in lay.assigned:
            return lay.assigned[scan_id]
        if scan_id in lay.shown:
            return self._scans[scan_id].info.page
        return None

    @staticmethod
    def _unreadable_reason(s: _Scan) -> str | None:
        if s.unreadable_reason is not None:
            return s.unreadable_reason
        if s.info is not None and s.info.total > MAX_TOTAL_PAGES:
            return COUNT_OUT_OF_RANGE
        if s.info is not None and not 1 <= s.info.page <= _pages(s.info.total):
            return OUT_OF_RANGE
        return None

    def _rank(self, scan_id: int) -> tuple:
        """Sort key within a page: best outcome (in the document's format) first, no
        outcome last, then add order."""
        o = self._status(self._scans[scan_id])[1]
        if o is None:
            return (1, 0, 0, scan_id)
        return (0, o.lost, o.repaired, scan_id)

    def _state(self, s: _Scan) -> str:
        return self._status(s)[0]

    def _status(self, s: _Scan) -> tuple[str, PageOutcome | None, int, str]:
        """(state, outcome, its serial, reason) of a scan as the current document sees
        it. A scan assigned by hand counts only by its page in the document's format;
        any other scan by its own reading."""
        lay = self._layout
        own_reason = self._unreadable_reason(s)
        if s.id in lay.assigned:
            fmt = lay.current.format
            if fmt in s.decoding:
                return ScanState.WORKING, None, 0, ""
            found = self._out(s, fmt)
            if found is not None:
                return ScanState.DONE, found[0], found[1], ""
            if fmt in s.failed:
                return ScanState.UNREADABLE, None, 0, s.failed[fmt]
            if s.working:
                return ScanState.WORKING, None, 0, ""
            if own_reason is not None:
                return ScanState.UNREADABLE, None, 0, own_reason
            if s.outcome is not None or s.decoded:
                return ScanState.UNREADABLE, None, 0, FORMAT_MISMATCH
            if s.info is not None:
                return ScanState.WORKING, None, 0, ""
            return ScanState.WAITING, None, 0, ""
        if s.outcome is not None and s.info is not None and own_reason is None:
            return ScanState.DONE, s.outcome, s.outcome_serial, ""
        if own_reason is not None:
            return ScanState.UNREADABLE, None, 0, own_reason
        if s.working or s.info is not None or s.outcome is not None:
            return ScanState.WORKING, None, 0, ""
        return ScanState.WAITING, None, 0, ""

    def _table(self) -> _Table:
        lay = self._layout
        if lay.table is None:
            lay.table = self._make_table(lay)
        return lay.table

    def _make_table(self, lay: _Layout) -> _Table:
        slots = self.slots()
        size = self._page_size(lay, slots)
        views = []
        usable: list[PageOutcome | None] = []
        key: list = [size]
        for slot in slots:
            view, o = self._page_view(slot, size)
            views.append(view)
            usable.append(o)
            if o is not None:
                key.append((slot.scan_id, self._status(self._scans[slot.scan_id])[2]))
            else:
                key.append(None)
        return _Table(tuple(views), tuple(usable), size, tuple(key))

    def _page_size(self, lay: _Layout, slots: tuple[PageSlot, ...]) -> int | None:
        """The outcome length of the earliest-added of the group's own scans that has
        one; failing that, of the earliest-added assigned scan in use that has one.
        Only outcomes decoded in the document's format count."""
        if lay.current is None:
            return None
        for scan_id in lay.shown:
            o = self._status(self._scans[scan_id])[1]
            if o is not None:
                return len(o.data)
        for scan_id in sorted(slot.scan_id for slot in slots if slot.scan_id in lay.assigned):
            o = self._status(self._scans[scan_id])[1]
            if o is not None:
                return len(o.data)
        return None

    def _page_view(
        self, slot: PageSlot, size: int | None
    ) -> tuple[PageView, PageOutcome | None]:
        """The page's view and the outcome it contributes to the file, if any."""

        def view(health: str, o: PageOutcome | None = None, reason: str = "") -> PageView:
            if o is None:
                return PageView(
                    slot.number, health, slot.scan_id, slot.spare_ids, 0, 0, None, reason
                )
            return PageView(
                slot.number, health, slot.scan_id, slot.spare_ids, repaired, o.lost, o.histogram
            )

        if slot.scan_id is None:
            return view(Health.MISSING), None
        state, o, _, why = self._status(self._scans[slot.scan_id])
        if state == ScanState.WAITING:
            return view(Health.WAITING), None
        if state == ScanState.UNREADABLE:
            return view(Health.UNREADABLE, reason=why), None
        if state != ScanState.DONE:
            return view(Health.WORKING), None
        if len(o.data) != size:
            return view(Health.UNREADABLE, reason=SIZE_MISMATCH), None
        repaired = o.repaired
        if o.lost > 0:
            return view(Health.DAMAGED, o), o
        return view(Health.REPAIRED if repaired > 0 else Health.GOOD, o), o

    def _verified(self, tag: Tag, verify: bool = True) -> bool | None:
        """Whether the assembled file matches the tag; hashed once per distinct input.

        None when the verdict is not cached and ``verify`` is false.
        """
        key = (tag, self._table().key)
        if self._verdict is None or self._verdict[0] != key:
            if not verify:
                return None
            self._verdict = (key, _matches(self.chunks(), tag))
        return self._verdict[1]

    def _view(self, s: _Scan) -> ScanView:
        """For a scan assigned by hand, its page and reason in the document's format."""
        state, o, _, why = self._status(s)
        if s.id not in self._layout.assigned:
            o, why = s.outcome, self._unreadable_reason(s) or ""
        return ScanView(s.id, s.path, state, s.info, o, why)

    def _group_view(self, g: _Group, shown: list[int], scan_ids: tuple[int, ...]) -> GroupView:
        """The title comes from the group's own scans that it shows: the most common
        name of a tagged group (on a tie, the longest), the longest of another."""
        names = [self._scans[i].info.name.rstrip(" ") for i in shown]
        if g.tag is not None:
            counts = Counter(names)
            title = max(names, key=lambda n: (counts[n], len(n)), default="")
        else:
            title = max(names, key=len, default="")
        key = scan_ids[0] if scan_ids else None
        return GroupView(key, title, g.total, g.format, g.tag, scan_ids)

    def _group(self) -> tuple[_Group | None, list[_Group]]:
        """Groups the scans; returns the hand-started group (if any) and all groups."""
        hand = None
        untagged: list[_Group] = []
        if self._hand is not None:
            hand = _Group(self._hand.format, self._hand.total, None)
            untagged.append(hand)
        tagged: dict[tuple, _Group] = {}
        for s in self._scans.values():
            i = s.info
            if i is None or s.unreadable_reason is not None:
                continue
            if i.total > MAX_TOTAL_PAGES or not 1 <= i.page <= _pages(i.total):
                continue  # unreadable: see _unreadable_reason
            if i.tag is not None:
                identity = (i.format, i.total, i.tag)
                g = tagged.get(identity)
                if g is None:
                    g = tagged[identity] = _Group(i.format, i.total, i.tag)
                g.members.append(s.id)
                continue
            # Linear in the number of untagged groups for each untagged scan.
            name = i.name.rstrip(" ")
            for g in untagged:
                if (
                    g.format == i.format
                    and g.total == i.total
                    and _prefix_compatible(g.longest, name)
                ):
                    g.members.append(s.id)
                    if len(name) > len(g.longest):
                        g.longest = name
                    break
            else:
                untagged.append(_Group(i.format, i.total, None, [s.id], name))
        groups = [g for g in untagged if g is not hand] + list(tagged.values())
        groups.sort(key=lambda g: g.members[0])
        if hand is not None:
            groups.insert(0, hand)
        return hand, groups

    @staticmethod
    def _resolve(
        choice: _Choice, group_of: dict[int, _Group], groups: list[_Group]
    ) -> _Group | None:
        """The group holding the earliest-added grouped scan of the choice; if none is
        grouped, the group with the choice's tagged identity; otherwise None."""
        first = min((m for m in choice.members if m in group_of), default=None)
        if first is not None:
            return group_of[first]
        if choice.identity is not None:
            return next((g for g in groups if _identity(g) == choice.identity), None)
        return None

    @property
    def _layout(self) -> _Layout:
        """Everything shown, recomputed on first use after a change.

        Recomputing is a pure function of the state, so doing it lazily gives the same
        result as doing it after every change. Operations read the layout before they
        change anything and mark it stale only when done.
        """
        if self._dirty:
            self._settle()
        return self._lay

    def _changed(self) -> None:
        self._dirty = True

    def _settle(self) -> None:
        hand, groups = self._group()
        group_of = {m: g for g in groups for m in g.members}
        if hand is not None:
            current = hand
        else:
            current = self._resolve(self._choice, group_of, groups) if self._choice else None
            if current is None and groups:
                current = groups[0]
        resolved: dict[int, bool] = {}  # id(anchor) -> active; many marks share one anchor

        def active(anchor: _Anchor) -> bool:
            if current is None:
                return False
            if isinstance(anchor, _HandDocument):
                return anchor is self._hand
            if id(anchor) not in resolved:
                resolved[id(anchor)] = self._resolve(anchor, group_of, groups) is current
            return resolved[id(anchor)]

        lay = _Layout(current=current, groups=groups, group_of=group_of)
        if hand is not None:
            lay.anchor = self._hand
        elif current is not None:
            lay.anchor = _Choice(frozenset(current.members), _identity(current))
        lay.assigned = {s: p for s, (a, p) in self._assigned.items() if active(a)}
        lay.preferred = {s: n for s, (a, n) in self._preferred.items() if active(a)}
        if current is not None:
            lay.shown = [m for m in current.members if m not in lay.assigned]
        for g in groups:
            if g is current:
                continue
            shown = [m for m in g.members if m not in lay.assigned]
            if shown:
                lay.others.append((g, shown))
        lay.others.sort(key=lambda item: item[1][0])
        self._lay = lay
        self._dirty = False
