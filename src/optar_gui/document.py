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
- A group's title is the longest name among its grouped scans ("" if none).

Which group is the document.

- A document started with ``start_by_hand`` is the document until ``switch_to``,
  another ``start_by_hand``, or until every scan is removed. It comes first among
  the untagged groups, so matching untagged scans join it, and it exists with no
  scans at all.
- Otherwise, if the user has made a choice, the document is the group that holds
  the earliest-added grouped scan of the choice. A choice is the set of scans
  that were in the document's group when the user made it; it never grows, and
  shrinks only by ``remove_scan``. It is made by ``switch_to`` (the target
  group), by ``remove_scan`` of a scan of the document (the rest of the group,
  so a document with scans left is not abandoned), and by ``assign_page`` or
  ``use_scan`` when there is no choice yet (the document worked in). While no
  scan of the choice is grouped the default rule applies, and the choice takes
  effect again as soon as one is. It is dropped by ``switch_to``,
  ``start_by_hand``, or when all its scans are removed.
- Otherwise (default rule) the document is the group of the earliest-added
  grouped scan.

Pages given by hand and scans chosen by hand. ``assign_page`` and ``use_scan``
remember the document they were made in (the set of its group's scans at that
moment, or the hand-started document itself). They apply whenever that document
is the current one (it holds the earliest-added grouped scan of that set) and are
inactive, not deleted, otherwise. An active assignment puts the scan into that
page of the document whatever its label or state says; it is listed in neither
``others()`` nor ``unreadable()``. An inactive one leaves the scan where its own
identity puts it. Both are deleted when their scan is removed, when the user
re-assigns or re-chooses, or when the user leaves their document with
``switch_to`` or ``start_by_hand``.

Pages. ``slots()`` has one slot per page ``1..max(total, 1)`` of the document.
Within a page the scan in use is the one chosen with ``use_scan``; otherwise the
one with the best outcome (fewest lost, then fewest repaired, then earliest
added), scans with no outcome last. Spares follow in the same order.
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


@dataclass
class _Scan:
    id: int
    path: str  # as given
    real: str  # resolved, for spotting the same file added twice
    working: bool = False
    info: ScanInfo | None = None
    outcome: PageOutcome | None = None
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


# Which document a user operation was made in: a started-by-hand document, or the
# set of scans in the document's group at that moment.
_Anchor = _HandDocument | frozenset


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
        self._choice: frozenset[int] | None = None
        self._assigned: dict[int, tuple[_Anchor, int]] = {}  # scan -> (document, page)
        self._preferred: dict[int, tuple[_Anchor, int]] = {}  # scan -> (document, serial)
        self._serial = 0
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
        self._get(scan_id).info = info
        self._settle()

    def set_outcome(self, scan_id: int, outcome: PageOutcome) -> None:
        self._get(scan_id).outcome = outcome
        self._settle()

    def set_unreadable(self, scan_id: int, reason: str) -> None:
        self._get(scan_id).unreadable_reason = reason
        self._settle()

    # --- User operations -------------------------------------------------------

    def remove_scan(self, scan_id: int) -> None:
        self._get(scan_id)
        current = self._layout.current
        if self._hand is None and current is not None and scan_id in current.members:
            rest = frozenset(current.members) - {scan_id}
            self._choice = rest or self._choice
        if self._choice is not None:
            self._choice = (self._choice - {scan_id}) or None
        del self._scans[scan_id]
        self._assigned.pop(scan_id, None)
        self._preferred.pop(scan_id, None)
        for marks in (self._assigned, self._preferred):
            for other, (anchor, _) in list(marks.items()):
                if isinstance(anchor, frozenset) and not anchor & self._scans.keys():
                    del marks[other]  # every scan of its document is gone
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
        self._choice = frozenset(target.members)
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
        return self._group_view(lay.current, ids)

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

    def others(self) -> tuple[GroupView, ...]:
        return tuple(self._group_view(g, tuple(shown)) for g, shown in self._layout.others)

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
        """Working in the default document makes it the user's choice."""
        if self._hand is None and self._choice is None:
            self._choice = frozenset(self._layout.current.members)

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

    def _view(self, s: _Scan) -> ScanView:
        return ScanView(
            s.id, s.path, self._state(s), s.info, s.outcome, self._unreadable_reason(s) or ""
        )

    def _group_view(self, g: _Group, scan_ids: tuple[int, ...]) -> GroupView:
        names = [self._scans[i].info.name for i in g.members]
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
    def _resolve(scans: frozenset, groups: list[_Group]) -> _Group | None:
        """The group holding the earliest-added grouped scan of a set."""
        group_of = {m: g for g in groups for m in g.members}
        first = min((m for m in scans if m in group_of), default=None)
        return None if first is None else group_of[first]

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
        lay.anchor = self._hand if hand is not None else (
            frozenset(current.members) if current is not None else None
        )
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
