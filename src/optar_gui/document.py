# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The document rules: which scan is which page of which printout.

Plain Python, no Qt and no numpy, so every rule here is testable on its own.

Scans are kept in the order they were added. Background work reports on them
(``set_working``, ``set_identified``, ``set_outcome``, ``set_unreadable``) in any
order; after every change the groups are recomputed from the scans' identities
and add order, never accumulated in event order, so the result is the same
whatever order the results arrive in.

Grouping. A scan takes part in grouping when it is identified, not unreadable,
its page number lies in ``1..max(total, 1)`` and it has not been assigned a page
by hand.

- A tagged scan belongs to the group of its ``(format, total, tag)``.
- Untagged scans are taken in add order. Each joins the first existing untagged
  group with the same format and total whose every member's name is
  prefix-compatible with its own (one is a prefix of the other, trailing spaces
  ignored); otherwise it starts a new group. Prefix compatibility is not
  transitive (``a`` matches ``ab`` and ``ac``, which do not match each other), so
  this order is what makes the grouping deterministic.
- A tagged and an untagged scan are never in the same group.

The current document is the group of the earliest-added grouped scan, unless the
user chose another with ``switch_to`` or started one with ``start_by_hand``. A
document started by hand comes first among the untagged groups, so matching
untagged scans join it; it exists even with no scans and lasts until
``switch_to`` or until every scan is removed. Removing a scan of the current
group keeps that group the document while it has scans left. When a chosen
group loses its last scan, the default rule applies again.

Scans assigned a page by hand belong to the current document at that page
whatever their label says. When the current document becomes a different one,
those assignments and any ``use_scan`` choices are dropped and the scans go back
to where their own identity puts them.
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
    path: str
    working: bool = False
    info: ScanInfo | None = None
    outcome: PageOutcome | None = None
    unreadable_reason: str | None = None


@dataclass
class _Group:
    key: object
    format: str
    total: int
    tag: Tag | None
    members: list[int] = field(default_factory=list)


@dataclass(frozen=True, eq=False)
class _HandDocument:
    """A document the user started by hand; compared by identity."""

    serial: int
    format: str
    total: int


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
        self._hand_serial = 0
        # Members of the group the user chose with switch_to; empty for the default rule.
        self._chosen: frozenset[int] = frozenset()
        # Pages given by hand: scans from outside the current group (taken out of grouping)
        # and scans of the current group moved to another page (kept in it).
        self._assigned: dict[int, int] = {}
        self._moved: dict[int, int] = {}
        self._preferred: dict[int, int] = {}  # page -> scan id chosen with use_scan
        self._current: _Group | None = None
        self._others: list[_Group] = []
        self._token: object = None  # identifies the current document across changes

    # --- Adding and reporting on scans ---------------------------------------

    def add_scan(self, path: str) -> int | None:
        resolved = os.path.realpath(path)
        if any(s.path == resolved for s in self._scans.values()):
            return None
        scan_id = self._next_id
        self._next_id += 1
        self._scans[scan_id] = _Scan(scan_id, resolved)
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

    def remove_scan(self, scan_id: int) -> None:
        self._get(scan_id)
        current = self._current
        if self._hand is None and current is not None and scan_id in current.members:
            # Removing one of its scans keeps the current group the document while it
            # has any left, even if an earlier-added scan of another group remains.
            self._chosen = frozenset(current.members) - {scan_id}
        del self._scans[scan_id]
        self._assigned.pop(scan_id, None)
        self._moved.pop(scan_id, None)
        self._preferred = {p: s for p, s in self._preferred.items() if s != scan_id}
        if not self._scans:
            self._hand = None
            self._chosen = frozenset()
        self._settle()

    # --- User choices ----------------------------------------------------------

    def assign_page(self, scan_id: int, page: int) -> None:
        self._get(scan_id)
        if self._current is None:
            raise ValueError("there is no document to assign a page in")
        self._check_page(page)
        if scan_id in self._current.members:
            self._moved[scan_id] = page
        else:
            self._assigned[scan_id] = page
        self._settle()

    def use_scan(self, scan_id: int) -> None:
        self._get(scan_id)
        page = self._page_in_current(scan_id)
        if page is None:
            raise ValueError(f"scan {scan_id} is not a page of the current document")
        self._preferred[page] = scan_id
        self._settle()

    def switch_to(self, key: object) -> None:
        groups = ([self._current] if self._current else []) + self._others
        target = next((g for g in groups if g.key == key), None)
        if target is None:
            raise KeyError(key)
        if target is self._current:
            return
        self._hand = None
        self._chosen = frozenset(target.members)
        self._settle()

    def start_by_hand(self, format: str, total: int) -> None:
        if total < 0:
            raise ValueError("total must not be negative")
        self._hand_serial += 1
        self._hand = _HandDocument(self._hand_serial, format, total)
        self._chosen = frozenset()
        self._settle()

    # --- Reading the state -----------------------------------------------------

    def scan(self, scan_id: int) -> ScanView:
        return self._view(self._get(scan_id))

    def scans(self) -> tuple[ScanView, ...]:
        return tuple(self._view(s) for s in self._scans.values())

    @property
    def current(self) -> GroupView | None:
        if self._current is None:
            return None
        ids = sorted(self._current.members + list(self._assigned))
        return self._group_view(self._current, tuple(ids))

    def slots(self) -> tuple[PageSlot, ...]:
        if self._current is None:
            return ()
        by_page: dict[int, list[int]] = {}
        for scan_id in self._current.members:
            page = self._moved.get(scan_id, self._scans[scan_id].info.page)
            by_page.setdefault(page, []).append(scan_id)
        for scan_id, page in self._assigned.items():
            by_page.setdefault(page, []).append(scan_id)
        slots = []
        for page in range(1, _pages(self._current.total) + 1):
            ranked = sorted(by_page.get(page, []), key=self._rank)
            preferred = self._preferred.get(page)
            if preferred in ranked:
                ranked.remove(preferred)
                ranked.insert(0, preferred)
            in_use = ranked[0] if ranked else None
            slots.append(PageSlot(page, in_use, tuple(ranked[1:])))
        return tuple(slots)

    def others(self) -> tuple[GroupView, ...]:
        return tuple(self._group_view(g, tuple(g.members)) for g in self._others)

    def unreadable(self) -> tuple[ScanView, ...]:
        return tuple(
            self._view(s)
            for s in self._scans.values()
            if s.id not in self._assigned and self._unreadable_reason(s) is not None
        )

    # --- Internals -------------------------------------------------------------

    def _get(self, scan_id: int) -> _Scan:
        try:
            return self._scans[scan_id]
        except KeyError:
            raise KeyError(scan_id) from None

    def _check_page(self, page: int) -> None:
        total = self._current.total
        if not 1 <= page <= _pages(total):
            raise ValueError(f"page {page} is outside 1..{_pages(total)}")

    def _page_in_current(self, scan_id: int) -> int | None:
        if scan_id in self._assigned:
            return self._assigned[scan_id]
        if self._current is not None and scan_id in self._current.members:
            return self._moved.get(scan_id, self._scans[scan_id].info.page)
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
        assigned = s.id in self._assigned
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
        if not names:
            title = ""
        elif g.tag is not None:
            title = names[0]
        else:
            title = max(names, key=lambda n: len(n.rstrip(" ")))
        return GroupView(g.key, title, g.total, g.format, g.tag, scan_ids)

    def _grouped(self, s: _Scan) -> bool:
        return (
            s.info is not None
            and self._unreadable_reason(s) is None
            and s.id not in self._assigned
        )

    def _group(self) -> tuple[_Group | None, list[_Group]]:
        """Groups the scans; returns the hand-started group (if any) and the others."""
        hand = None
        untagged: list[_Group] = []
        if self._hand is not None:
            h = self._hand
            hand = _Group(("hand", h.serial), h.format, h.total, None)
            untagged.append(hand)
        tagged: dict[tuple, _Group] = {}
        for s in self._scans.values():
            if not self._grouped(s):
                continue
            i = s.info
            if i.tag is not None:
                identity = (i.format, i.total, i.tag)
                if identity not in tagged:
                    tagged[identity] = _Group(("tag", *identity), i.format, i.total, i.tag)
                tagged[identity].members.append(s.id)
                continue
            for g in untagged:
                if (
                    g.format == i.format
                    and g.total == i.total
                    and all(_prefix_compatible(self._scans[m].info.name, i.name) for m in g.members)
                ):
                    g.members.append(s.id)
                    break
            else:
                g = _Group(("name", i.format, i.total, s.id), i.format, i.total, None)
                g.members.append(s.id)
                untagged.append(g)
        others = [g for g in untagged if g is not hand] + list(tagged.values())
        others.sort(key=lambda g: g.members[0])
        return hand, others

    def _pick_current(self) -> tuple[_Group | None, list[_Group]]:
        hand, groups = self._group()
        if hand is not None:
            return hand, groups
        if self._chosen:
            # The chosen group is the one now holding the earliest of its members.
            group_of = {m: g for g in groups for m in g.members}
            anchor = min((m for m in self._chosen if m in group_of), default=None)
            if anchor is not None:
                chosen = group_of[anchor]
                return chosen, [g for g in groups if g is not chosen]
            self._chosen = frozenset()
        if not groups:
            return None, []
        return groups[0], groups[1:]

    def _token_for(self, current: _Group | None) -> object:
        if self._hand is not None:
            return self._hand
        if current is None:
            return None
        return frozenset(current.members)

    def _same_document(self, old: object, new: object) -> bool:
        if isinstance(old, frozenset) and isinstance(new, frozenset):
            return bool(old & new)
        return old is new

    def _settle(self) -> None:
        current, others = self._pick_current()
        token = self._token_for(current)
        if not self._same_document(self._token, token):
            had_choices = bool(self._assigned)
            self._assigned.clear()
            self._moved.clear()
            self._preferred.clear()
            if had_choices:
                current, others = self._pick_current()
                token = self._token_for(current)
        if self._chosen and current is not None and self._hand is None:
            self._chosen = frozenset(current.members)
        self._current, self._others, self._token = current, others, token
