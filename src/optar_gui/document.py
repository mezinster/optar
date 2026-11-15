# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The document rules: which scan is which page of which printout.

Plain Python, no Qt and no numpy, so every rule here is testable on its own.

Purity. The state is a function of the scans (add order, identities, outcomes,
states), of the ordered user operations (``switch_to``, ``start_by_hand``,
``assign_page``, ``use_scan``, ``remove_scan``) and of which background results
were known when each user operation was made. It does not depend on the order in
which background results (``set_working``, ``set_identified``, ``set_outcome``,
``set_unreadable``) arrive between user operations: everything shown is
recomputed from that information after every change, and a user's choice is
never lost or changed by a passing intermediate state.

Scans. ``add_scan`` refuses a path whose ``os.path.realpath`` is already present;
``ScanView.path`` is the path as given. Whether the path exists, or is empty, is
the caller's business. On a case-insensitive file system two spellings of one
file are not recognised as the same scan.

Grouping. A scan is *grouped* when it is identified, not unreadable and its page
lies in ``1..max(total, 1)``; a page outside that range makes it unreadable with
the reason ``"page number out of range"``. ``set_unreadable`` is final and keeps
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
- A group's title is the longest name among the grouped scans it shows ("" if
  none); a scan assigned by hand into another document does not count.

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
else ``GOOD``.

The whole document. ``summary()`` is ``EMPTY`` with no document; ``WORKING``
while any page is waiting or working; ``VERIFIED`` or ``MISMATCH`` when every page
is good or repaired and the document has a tag, by assembling the file and
checking it against the tag; ``UNVERIFIABLE`` when every page is good or repaired
and there is no tag; otherwise ``INCOMPLETE``. The verdict is cached until the
scans in use, their outcomes or the tag change.

Assembling. ``assemble()`` joins pages ``1..max(total, 1)`` in order. A page whose
scan in use has an outcome gives its data, damaged or not; any other page gives
``page_bytes`` zero bytes, so later pages keep their offsets. With a tag the
result is cut to the tag's size. Every page of a document has the same capacity;
pages of different sizes are refused.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Only for annotations: importing the optar package at run time loads numpy, and
    # tags are only compared and hashed here.
    from optar.tag import Tag

OUT_OF_RANGE = "page number out of range"
RECOVERED_NAME = "recovered.bin"


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


class DocState:
    EMPTY = "empty"
    WORKING = "working"
    INCOMPLETE = "incomplete"
    UNVERIFIABLE = "unverifiable"
    VERIFIED = "verified"
    MISMATCH = "mismatch"


@dataclass(frozen=True)
class Summary:
    state: str
    good: int
    repaired: int
    damaged: int
    unreadable: int
    missing: int
    size: int | None  # the tag's size, or None without a tag


@dataclass
class _Scan:
    id: int
    path: str  # as given
    real: str  # resolved, for spotting the same file added twice
    working: bool = False
    info: ScanInfo | None = None
    outcome: PageOutcome | None = None
    outcome_serial: int = 0  # changes with every outcome, for the verdict cache
    unreadable_reason: str | None = None


@dataclass
class _Group:
    format: str
    total: int
    tag: Tag | None
    members: list[int] = field(default_factory=list)  # grouped scans, add order


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


def _pages(total: int) -> int:
    return max(total, 1)


def _prefix_compatible(a: str, b: str) -> bool:
    a, b = a.rstrip(" "), b.rstrip(" ")
    return a.startswith(b) or b.startswith(a)


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
        self._layout = _Layout()

    # --- Adding and reporting on scans ---------------------------------------

    def add_scan(self, path: str) -> int | None:
        real = os.path.realpath(path)
        if any(s.real == real for s in self._scans.values()):
            return None
        scan_id = self._next_id
        self._next_id += 1
        self._scans[scan_id] = _Scan(scan_id, path, real)
        self._settle()
        return scan_id

    def set_working(self, scan_id: int) -> None:
        self._get(scan_id).working = True
        self._settle()

    def set_identified(self, scan_id: int, info: ScanInfo) -> None:
        """Records what the scan's label says.

        A scan is expected to be identified once. A second call with different
        information replaces the first, but the guarantees about choices and
        assignments resolving to the same document assume the identity does not
        change.
        """
        self._get(scan_id).info = info
        self._settle()

    def set_outcome(self, scan_id: int, outcome: PageOutcome) -> None:
        s = self._get(scan_id)
        self._outcomes += 1
        s.outcome = outcome
        s.outcome_serial = self._outcomes
        self._settle()

    def set_unreadable(self, scan_id: int, reason: str) -> None:
        self._get(scan_id).unreadable_reason = reason
        self._settle()

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
        del self._scans[scan_id]
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
        self._settle()

    def assign_page(self, scan_id: int, page: int) -> None:
        self._get(scan_id)
        current = self._require_current()
        if not 1 <= page <= _pages(current.total):
            raise ValueError(f"page {page} is outside 1..{_pages(current.total)}")
        self._pin()
        self._assigned[scan_id] = (self._layout.anchor, page)
        self._preferred.pop(scan_id, None)
        self._settle()

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
        self._settle()

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
        self._settle()

    def start_by_hand(self, format: str, total: int) -> None:
        if total < 0:
            raise ValueError("total must not be negative")
        self._leave_document()
        self._hand = _HandDocument(format, total)
        self._settle()

    # --- Reading the state -----------------------------------------------------

    def scan(self, scan_id: int) -> ScanView:
        return self._view(self._get(scan_id))

    def scans(self) -> tuple[ScanView, ...]:
        return tuple(self._view(s) for s in self._scans.values())

    @property
    def current(self) -> GroupView | None:
        lay = self._layout
        if lay.current is None:
            return None
        ids = tuple(sorted(lay.shown + list(lay.assigned)))
        return self._group_view(lay.current, lay.shown, ids)

    def slots(self) -> tuple[PageSlot, ...]:
        lay = self._layout
        if lay.current is None:
            return ()
        by_page: dict[int, list[int]] = {}
        for scan_id in lay.shown:
            by_page.setdefault(self._scans[scan_id].info.page, []).append(scan_id)
        for scan_id, page in lay.assigned.items():
            by_page.setdefault(page, []).append(scan_id)
        slots = []
        for page in range(1, _pages(lay.current.total) + 1):
            ranked = sorted(by_page.get(page, []), key=self._rank)
            chosen = [s for s in ranked if s in lay.preferred]
            if chosen:
                pick = max(chosen, key=lay.preferred.__getitem__)
                ranked.remove(pick)
                ranked.insert(0, pick)
            slots.append(PageSlot(page, ranked[0] if ranked else None, tuple(ranked[1:])))
        return tuple(slots)

    def pages(self) -> tuple[PageView, ...]:
        return tuple(self._page_view(slot) for slot in self.slots())

    def summary(self) -> Summary:
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
                state = DocState.VERIFIED if self._verified(cur.tag) else DocState.MISMATCH
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

    @property
    def page_bytes(self) -> int | None:
        """Bytes per page: the length of the first outcome among the pages in use."""
        outcomes = self._outcomes_in_use()
        return next((len(o.data) for o in outcomes if o is not None), None)

    def assemble(self) -> bytes:
        outcomes = self._outcomes_in_use()
        sizes = {len(o.data) for o in outcomes if o is not None}
        if not sizes:
            raise ValueError("no page has been decoded")
        if len(sizes) > 1:
            raise ValueError("pages have different sizes")
        blank = bytes(sizes.pop())
        data = b"".join(o.data if o is not None else blank for o in outcomes)
        tag = self._layout.current.tag
        return data[: tag.size] if tag is not None else data

    @property
    def can_save(self) -> bool:
        return any(o is not None for o in self._outcomes_in_use())

    @property
    def suggested_name(self) -> str:
        cur = self.current
        name = cur.title.strip() if cur is not None else ""
        return name or RECOVERED_NAME

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
        return self._resolve(anchor, lay.groups) is lay.current

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
        if s.info is not None and not 1 <= s.info.page <= _pages(s.info.total):
            return OUT_OF_RANGE
        return None

    def _rank(self, scan_id: int) -> tuple:
        """Sort key within a page: best outcome first, no outcome last, then add order."""
        o = self._scans[scan_id].outcome
        if o is None:
            return (1, 0, 0, scan_id)
        return (0, o.lost, o.repaired, scan_id)

    def _state(self, s: _Scan) -> str:
        unreadable = self._unreadable_reason(s) is not None
        assigned = s.id in self._layout.assigned
        if s.outcome is not None and (assigned or (s.info is not None and not unreadable)):
            return ScanState.DONE
        if unreadable and not (assigned and s.working):
            return ScanState.UNREADABLE
        if s.working or s.info is not None or s.outcome is not None:
            return ScanState.WORKING
        return ScanState.WAITING

    def _page_view(self, slot: PageSlot) -> PageView:
        def view(health: str, o: PageOutcome | None = None) -> PageView:
            if o is None:
                return PageView(slot.number, health, slot.scan_id, slot.spare_ids, 0, 0, None)
            return PageView(
                slot.number, health, slot.scan_id, slot.spare_ids, o.repaired, o.lost, o.histogram
            )

        if slot.scan_id is None:
            return view(Health.MISSING)
        s = self._scans[slot.scan_id]
        state = self._state(s)
        if state == ScanState.WAITING:
            return view(Health.WAITING)
        if state == ScanState.UNREADABLE:
            return view(Health.UNREADABLE)
        if state != ScanState.DONE:
            return view(Health.WORKING)
        o = s.outcome
        if o.lost > 0:
            return view(Health.DAMAGED, o)
        return view(Health.REPAIRED if o.repaired > 0 else Health.GOOD, o)

    def _outcomes_in_use(self) -> list[PageOutcome | None]:
        """The outcome of each page's scan in use, in page order (None: no data)."""
        return [
            self._scans[slot.scan_id].outcome if slot.scan_id is not None else None
            for slot in self.slots()
        ]

    def _verified(self, tag: Tag) -> bool:
        """Whether the assembled file matches the tag; hashed once per distinct input."""
        key = (tag,) + tuple(
            (slot.scan_id, self._scans[slot.scan_id].outcome_serial)
            for slot in self.slots()
            if slot.scan_id is not None
        )
        if self._verdict is None or self._verdict[0] != key:
            self._verdict = (key, tag.matches(self.assemble()))
        return self._verdict[1]

    def _view(self, s: _Scan) -> ScanView:
        return ScanView(
            s.id, s.path, self._state(s), s.info, s.outcome, self._unreadable_reason(s) or ""
        )

    def _group_view(self, g: _Group, shown: list[int], scan_ids: tuple[int, ...]) -> GroupView:
        """The title comes from the group's own scans that it shows."""
        names = [self._scans[i].info.name for i in shown]
        title = max(names, key=lambda n: len(n.rstrip(" ")), default="")
        key = scan_ids[0] if scan_ids else None
        return GroupView(key, title, g.total, g.format, g.tag, scan_ids)

    def _grouped(self, s: _Scan) -> bool:
        return s.info is not None and self._unreadable_reason(s) is None

    def _group(self) -> tuple[_Group | None, list[_Group]]:
        """Groups the scans; returns the hand-started group (if any) and all groups."""
        hand = None
        untagged: list[_Group] = []
        if self._hand is not None:
            hand = _Group(self._hand.format, self._hand.total, None)
            untagged.append(hand)
        tagged: dict[tuple, _Group] = {}
        for s in self._scans.values():
            if not self._grouped(s):
                continue
            i = s.info
            if i.tag is not None:
                identity = (i.format, i.total, i.tag)
                tagged.setdefault(identity, _Group(i.format, i.total, i.tag)).members.append(s.id)
                continue
            # Quadratic in the number of untagged scans; fine for a stack of pages.
            for g in untagged:
                if (
                    g.format == i.format
                    and g.total == i.total
                    and all(_prefix_compatible(self._scans[m].info.name, i.name) for m in g.members)
                ):
                    g.members.append(s.id)
                    break
            else:
                untagged.append(_Group(i.format, i.total, None, [s.id]))
        groups = [g for g in untagged if g is not hand] + list(tagged.values())
        groups.sort(key=lambda g: g.members[0])
        if hand is not None:
            groups.insert(0, hand)
        return hand, groups

    @staticmethod
    def _resolve(choice: _Choice, groups: list[_Group]) -> _Group | None:
        """The group holding the earliest-added grouped scan of the choice; if none is
        grouped, the group with the choice's tagged identity; otherwise None."""
        group_of = {m: g for g in groups for m in g.members}
        first = min((m for m in choice.members if m in group_of), default=None)
        if first is not None:
            return group_of[first]
        if choice.identity is not None:
            return next((g for g in groups if _identity(g) == choice.identity), None)
        return None

    def _settle(self) -> None:
        hand, groups = self._group()
        if hand is not None:
            current = hand
        else:
            current = self._resolve(self._choice, groups) if self._choice else None
            if current is None and groups:
                current = groups[0]

        def active(anchor: _Anchor) -> bool:
            if current is None:
                return False
            if isinstance(anchor, _HandDocument):
                return anchor is self._hand
            return self._resolve(anchor, groups) is current

        lay = _Layout(current=current, groups=groups)
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
        self._layout = lay
