# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The document rules: which scan is which page of which printout.

Each test builds a Document from scans and identities, then reads back the four
things the window shows: the current document, its page slots, the groups that
are not part of it, and the unreadable scans.
"""

import itertools
import random
import subprocess
import sys
import time
import tracemalloc

import numpy as np
import pytest

from optar.container import PagePayload, plan, plan_for, read_header, wrap
from optar.format import get_layout
from optar.tag import Tag, make_tag
from optar_gui.document import (
    FORMAT_MISMATCH,
    MAX_TOTAL_PAGES,
    NO_ACTIONS,
    SCAN_EXTENSIONS,
    SIZE_MISMATCH,
    Actions,
    DocState,
    Document,
    Fit,
    GroupView,
    Health,
    PageOutcome,
    PageSlot,
    PageView,
    Row,
    ScanInfo,
    ScanState,
    ScanView,
    Summary,
    expand_paths,
    paper_for_size,
)

A = "0-65-93-24-3-1-2-24"
LETTER = "0-67-87-24-3-1-2-24"
TAG = Tag(500000, "aaaaaaaa")
OTHER_TAG = Tag(500000, "bbbbbbbb")


def info(page, total=3, name="doc.tar", tag=TAG, fmt=A):
    return ScanInfo(fmt, total, page, name, tag)


def out(lost=0, repaired=0, data=b"x"):
    return PageOutcome(data, (100 - repaired, repaired, 0, 0), lost)


def add(doc, n):
    """Adds the scan /scans/<n>.png and returns its id."""
    scan_id = doc.add_scan(f"/scans/{n}.png")
    assert scan_id is not None
    return scan_id


def build(*infos):
    """A document with one scan per info (None: left unidentified), identified in order."""
    doc = Document()
    ids = [add(doc, n) for n in range(len(infos))]
    for scan_id, i in zip(ids, infos, strict=True):
        if i is not None:
            doc.set_identified(scan_id, i)
    return doc, ids


def picture(doc):
    """What the window shows, as plain data."""
    cur = doc.current
    return {
        "current": None if cur is None else cur.scan_ids,
        "slots": [(s.number, s.scan_id, s.spare_ids) for s in doc.slots()],
        "others": [g.scan_ids for g in doc.others()],
        "unreadable": [s.id for s in doc.unreadable()],
    }


# --- Placing scans into pages -------------------------------------------------


def test_scans_fill_their_slots_in_any_order():
    doc, (p3, p1) = build(info(3), info(1))
    assert picture(doc) == {
        "current": (p3, p1),
        "slots": [(1, p1, ()), (2, None, ()), (3, p3, ())],
        "others": [],
        "unreadable": [],
    }
    assert doc.current.title == "doc.tar"
    assert doc.current.tag == TAG
    assert (doc.current.format, doc.current.total) == (A, 3)


def test_same_file_spelled_in_another_case_is_one_scan_where_case_is_ignored(monkeypatch):
    # The test machine's file system tells case apart, so stand in for Windows,
    # whose os.path.normcase folds case.
    import os

    monkeypatch.setattr(os.path, "normcase", str.lower)
    doc = Document()
    first = doc.add_scan("/scans/Page-1.PNG")
    assert doc.add_scan("/scans/page-1.png") is None
    assert doc.scan_id_of("/SCANS/PAGE-1.png") == first
    doc.remove_scan(first)
    assert doc.add_scan("/scans/page-1.png") is not None


def test_same_path_added_twice_is_ignored(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    doc = Document()
    first = doc.add_scan(str(tmp_path / "a.png"))
    assert first is not None
    assert doc.add_scan("./a.png") is None
    assert doc.add_scan(str(tmp_path / "sub" / ".." / "a.png")) is None
    assert [s.id for s in doc.scans()] == [first]
    assert doc.scan(first).path == str(tmp_path / "a.png")
    # The path is shown as given; only the comparison uses the resolved path.
    second = doc.add_scan("./b.png")
    assert doc.scan(second).path == "./b.png"
    assert doc.add_scan(str(tmp_path / "b.png")) is None
    doc.remove_scan(second)
    assert doc.scan(first).state == ScanState.WAITING
    assert picture(doc) == {"current": None, "slots": [], "others": [], "unreadable": []}


def test_first_added_defines_the_document_not_first_finished():
    doc = Document()
    x = add(doc, "x")
    y = add(doc, "y")
    doc.set_identified(y, info(1, name="other.tar", tag=OTHER_TAG))
    assert doc.current.scan_ids == (y,)
    doc.set_identified(x, info(2))
    assert picture(doc) == {
        "current": (x,),
        "slots": [(1, None, ()), (2, x, ()), (3, None, ())],
        "others": [(y,)],
        "unreadable": [],
    }
    assert doc.others()[0].title == "other.tar"


def test_different_tag_same_name_and_total_is_a_separate_group():
    doc, (a, b) = build(info(1), info(2, tag=OTHER_TAG))
    assert picture(doc) == {
        "current": (a,),
        "slots": [(1, a, ()), (2, None, ()), (3, None, ())],
        "others": [(b,)],
        "unreadable": [],
    }
    assert doc.others()[0].tag == OTHER_TAG


@pytest.mark.parametrize(
    "first, second, together",
    [
        ("holiday-photos.ta", "holiday-photos.tar", True),
        ("holiday-photos.tar", "holiday-photos.ta", True),
        ("holiday-photos.tar  ", "holiday-photos.tar", True),
        ("holiday-photos.tar", "other.tar", False),
        ("holiday-photos.tar", "holiday-photos.taz", False),
        ("", "anything", True),
    ],
)
def test_untagged_names_match_by_prefix(first, second, together):
    doc, (a, b) = build(info(1, name=first, tag=None), info(2, name=second, tag=None))
    if together:
        assert picture(doc) == {
            "current": (a, b),
            "slots": [(1, a, ()), (2, b, ()), (3, None, ())],
            "others": [],
            "unreadable": [],
        }
    else:
        assert picture(doc) == {
            "current": (a,),
            "slots": [(1, a, ()), (2, None, ()), (3, None, ())],
            "others": [(b,)],
            "unreadable": [],
        }


def test_untagged_name_cut_one_character_shorter_on_two_digit_pages():
    # "9/12" is one character shorter than "10/12", so page 9 shows one more character.
    doc, (p9, p10, p11) = build(
        info(9, total=12, name="holiday-photos.tar.g", tag=None),
        info(10, total=12, name="holiday-photos.tar.", tag=None),
        info(11, total=12, name="holiday-photos.tar.", tag=None),
    )
    assert doc.current.scan_ids == (p9, p10, p11)
    assert doc.current.title == "holiday-photos.tar.g"
    assert doc.current.tag is None
    filled = [(s.number, s.scan_id) for s in doc.slots() if s.scan_id is not None]
    assert filled == [(9, p9), (10, p10), (11, p11)]
    assert len(doc.slots()) == 12
    assert doc.others() == ()


def test_untagged_prefix_grouping_is_by_add_order_when_not_transitive():
    # "a" matches both "ab" and "ac", which do not match each other. Scans join the
    # first earlier group whose every member matches them, so "ac" starts its own group.
    doc, (a, ab, ac) = build(
        info(1, name="a", tag=None), info(2, name="ab", tag=None), info(3, name="ac", tag=None)
    )
    assert picture(doc) == {
        "current": (a, ab),
        "slots": [(1, a, ()), (2, ab, ()), (3, None, ())],
        "others": [(ac,)],
        "unreadable": [],
    }
    assert doc.current.title == "ab"
    assert doc.others()[0].title == "ac"


def test_tagged_and_untagged_never_mix():
    doc, (t, u) = build(info(1), info(2, tag=None))
    assert picture(doc) == {
        "current": (t,),
        "slots": [(1, t, ()), (2, None, ()), (3, None, ())],
        "others": [(u,)],
        "unreadable": [],
    }
    assert doc.others()[0].tag is None


@pytest.mark.parametrize(
    "second",
    [
        info(2, fmt=LETTER),
        info(2, total=4),
        info(2, fmt=LETTER, tag=None),
    ],
)
def test_mixed_papers_are_separate_groups(second):
    doc, (a, b) = build(info(1), second)
    assert picture(doc) == {
        "current": (a,),
        "slots": [(1, a, ()), (2, None, ()), (3, None, ())],
        "others": [(b,)],
        "unreadable": [],
    }
    assert (doc.others()[0].format, doc.others()[0].total) == (second.format, second.total)


def test_several_foreign_groups_are_listed_in_add_order():
    doc, (a, f1, f2, f3) = build(
        info(1),
        info(1, fmt=LETTER),
        info(1, tag=OTHER_TAG),
        info(2, fmt=LETTER),
    )
    assert picture(doc)["others"] == [(f1, f3), (f2,)]


# --- Duplicate pages ----------------------------------------------------------


def test_duplicate_page_better_outcome_wins_and_other_is_spare():
    doc, (worse, better) = build(info(1), info(1))
    doc.set_outcome(worse, out(lost=2))
    doc.set_outcome(better, out(lost=0, repaired=50))
    assert picture(doc) == {
        "current": (worse, better),
        "slots": [(1, better, (worse,)), (2, None, ()), (3, None, ())],
        "others": [],
        "unreadable": [],
    }
    doc.use_scan(worse)
    assert doc.slots()[0] == PageSlot(1, worse, (better,))
    doc.use_scan(better)
    assert doc.slots()[0] == PageSlot(1, better, (worse,))


@pytest.mark.parametrize(
    "first, second, winner",
    [
        (out(lost=1), out(lost=0), 1),  # fewest lost
        (out(repaired=9), out(repaired=3), 1),  # then fewest repaired
        (out(repaired=3), out(repaired=3), 0),  # then earliest added
        (out(lost=0, repaired=90), out(lost=1, repaired=0), 0),  # lost outranks repaired
    ],
)
def test_duplicate_ranking(first, second, winner):
    doc, ids = build(info(1), info(1))
    doc.set_outcome(ids[0], first)
    doc.set_outcome(ids[1], second)
    assert picture(doc) == {
        "current": tuple(ids),
        "slots": [(1, ids[winner], (ids[1 - winner],)), (2, None, ()), (3, None, ())],
        "others": [],
        "unreadable": [],
    }


def test_duplicate_without_outcome_ranks_last():
    doc, (pending, done) = build(info(1), info(1))
    # Neither has an outcome: the earliest added is in use.
    assert picture(doc) == {
        "current": (pending, done),
        "slots": [(1, pending, (done,)), (2, None, ()), (3, None, ())],
        "others": [],
        "unreadable": [],
    }
    doc.set_outcome(done, out(lost=7))
    assert picture(doc) == {
        "current": (pending, done),
        "slots": [(1, done, (pending,)), (2, None, ()), (3, None, ())],
        "others": [],
        "unreadable": [],
    }


def test_use_scan_of_a_scan_outside_the_document_raises():
    doc, (a, foreign) = build(info(1), info(1, tag=OTHER_TAG))
    with pytest.raises(ValueError):
        doc.use_scan(foreign)
    doc.use_scan(a)  # already in use: allowed


def test_remove_scan_in_use_promotes_best_spare():
    doc, (a, b, c) = build(info(1), info(1), info(1))
    doc.set_outcome(a, out(lost=0))
    doc.set_outcome(b, out(lost=3))
    doc.set_outcome(c, out(lost=1))
    doc.use_scan(b)
    assert doc.slots()[0] == PageSlot(1, b, (a, c))
    doc.remove_scan(b)
    assert doc.slots()[0] == PageSlot(1, a, (c,))
    doc.remove_scan(a)
    assert doc.slots()[0] == PageSlot(1, c, ())


# --- Which group is the document ----------------------------------------------


def test_remove_last_scan_promotes_earliest_remaining_group():
    doc, (a1, f1, a2, f2, g) = build(
        info(1),
        info(1, tag=OTHER_TAG),
        info(2),
        info(2, tag=OTHER_TAG),
        info(1, fmt=LETTER),
    )
    assert picture(doc)["current"] == (a1, a2)
    doc.remove_scan(a1)
    assert picture(doc)["current"] == (a2,)
    doc.remove_scan(a2)
    assert picture(doc) == {
        "current": (f1, f2),
        "slots": [(1, f1, ()), (2, f2, ()), (3, None, ())],
        "others": [(g,)],
        "unreadable": [],
    }
    doc.remove_scan(f1)
    doc.remove_scan(f2)
    assert picture(doc)["current"] == (g,)
    doc.remove_scan(g)
    assert picture(doc) == {"current": None, "slots": [], "others": [], "unreadable": []}
    assert doc.scans() == ()


def test_switch_to_other_group():
    doc, (early, a, f1, f2) = build(None, info(1), info(1, tag=OTHER_TAG), info(3, tag=OTHER_TAG))
    assert picture(doc)["current"] == (a,)
    key = doc.others()[0].key
    doc.switch_to(key)
    assert picture(doc) == {
        "current": (f1, f2),
        "slots": [(1, f1, ()), (2, None, ()), (3, f2, ())],
        "others": [(a,)],
        "unreadable": [],
    }
    assert doc.current.key == key
    doc.switch_to(key)  # already current: nothing changes
    assert picture(doc)["current"] == (f1, f2)
    # An earlier-added scan identified later does not undo the user's choice.
    doc.set_identified(early, info(2))
    assert picture(doc)["current"] == (f1, f2)
    assert picture(doc)["others"] == [(early, a)]
    with pytest.raises(KeyError):
        doc.switch_to(("no", "such", "group"))


def test_switch_to_survives_removing_part_of_the_chosen_group():
    doc, (a, f1, f2) = build(info(1), info(1, tag=OTHER_TAG), info(2, tag=OTHER_TAG))
    doc.switch_to(doc.others()[0].key)
    doc.remove_scan(f1)
    assert picture(doc)["current"] == (f2,)
    doc.remove_scan(f2)
    assert picture(doc)["current"] == (a,)


# --- Assigning pages by hand --------------------------------------------------


def test_assign_page_moves_unreadable_and_foreign_scans_in():
    doc, (a, foreign, bad) = build(info(1), info(2, tag=OTHER_TAG), None)
    doc.set_unreadable(bad, "label unreadable")
    assert picture(doc) == {
        "current": (a,),
        "slots": [(1, a, ()), (2, None, ()), (3, None, ())],
        "others": [(foreign,)],
        "unreadable": [bad],
    }
    doc.assign_page(bad, 3)
    doc.assign_page(foreign, 2)
    assert picture(doc) == {
        "current": (a, foreign, bad),
        "slots": [(1, a, ()), (2, foreign, ()), (3, bad, ())],
        "others": [],
        "unreadable": [],
    }
    # The assigned scan keeps its own label and reason for display.
    assert doc.scan(foreign).info == info(2, tag=OTHER_TAG)
    assert doc.scan(bad).reason == "label unreadable"
    # Decoding the assigned unreadable scan completes it.
    doc.set_working(bad)
    assert doc.scan(bad).state == ScanState.WORKING
    doc.set_outcome(bad, out(lost=4))
    assert doc.scan(bad).state == ScanState.DONE


def test_assigned_scans_go_back_when_the_document_changes():
    doc, (a, foreign, bad) = build(info(1), info(2, tag=OTHER_TAG), None)
    doc.set_unreadable(bad, "label unreadable")
    doc.assign_page(bad, 3)
    doc.assign_page(foreign, 2)
    doc.remove_scan(a)
    assert picture(doc) == {
        "current": (foreign,),
        "slots": [(1, None, ()), (2, foreign, ()), (3, None, ())],
        "others": [],
        "unreadable": [bad],
    }


def test_assigned_scans_go_back_on_switch_to():
    doc, (a, b, bad) = build(info(1), info(1, tag=OTHER_TAG), None)
    doc.set_unreadable(bad, "no page outline found")
    doc.assign_page(bad, 2)
    doc.switch_to(doc.others()[0].key)
    assert picture(doc) == {
        "current": (b,),
        "slots": [(1, b, ()), (2, None, ()), (3, None, ())],
        "others": [(a,)],
        "unreadable": [bad],
    }


def test_assign_page_moves_a_scan_of_the_document_to_another_page():
    doc, (only, foreign) = build(info(1), info(1, tag=OTHER_TAG))
    doc.assign_page(only, 3)
    assert picture(doc) == {
        "current": (only,),
        "slots": [(1, None, ()), (2, None, ()), (3, only, ())],
        "others": [(foreign,)],
        "unreadable": [],
    }
    doc.use_scan(only)
    assert doc.slots()[2] == PageSlot(3, only, ())


def test_assign_page_out_of_range_raises():
    doc, (a, bad) = build(info(1), None)
    doc.set_unreadable(bad, "label unreadable")
    for page in (0, 4, -1):
        with pytest.raises(ValueError):
            doc.assign_page(bad, page)
    assert picture(doc)["unreadable"] == [bad]
    doc.assign_page(bad, 3)
    assert doc.slots()[2] == PageSlot(3, bad, ())


def test_assign_page_without_a_document_raises():
    doc, (bad,) = build(None)
    doc.set_unreadable(bad, "label unreadable")
    with pytest.raises(ValueError):
        doc.assign_page(bad, 1)


def test_start_by_hand_then_assign():
    doc, (bad1, bad2) = build(None, None)
    doc.set_unreadable(bad1, "label unreadable")
    doc.set_unreadable(bad2, "no page outline found")
    assert doc.current is None
    doc.start_by_hand(A, 2)
    cur = doc.current
    assert (cur.format, cur.total, cur.tag, cur.title, cur.scan_ids) == (A, 2, None, "", ())
    assert picture(doc) == {
        "current": (),
        "slots": [(1, None, ()), (2, None, ())],
        "others": [],
        "unreadable": [bad1, bad2],
    }
    doc.assign_page(bad2, 2)
    doc.assign_page(bad1, 1)
    assert picture(doc) == {
        "current": (bad1, bad2),
        "slots": [(1, bad1, ()), (2, bad2, ())],
        "others": [],
        "unreadable": [],
    }


def test_start_by_hand_takes_in_matching_untagged_scans():
    doc = Document()
    doc.start_by_hand(A, 3)
    assert doc.current is not None  # exists with no scans at all
    u = add(doc, "u")
    t = add(doc, "t")
    w = add(doc, "w")
    doc.set_identified(u, info(2, name="x.tar", tag=None))
    doc.set_identified(t, info(1))
    doc.set_identified(w, info(1, total=4, name="x.tar", tag=None))
    assert picture(doc) == {
        "current": (u,),
        "slots": [(1, None, ()), (2, u, ()), (3, None, ())],
        "others": [(t,), (w,)],
        "unreadable": [],
    }
    assert doc.current.title == "x.tar"
    # It persists when its own scans go, until every scan is removed.
    doc.remove_scan(u)
    assert doc.current.total == 3 and doc.current.scan_ids == ()
    doc.remove_scan(t)
    doc.remove_scan(w)
    assert doc.current is None


# --- Odd labels ---------------------------------------------------------------


def test_total_zero_is_a_one_page_document():
    doc, (empty,) = build(info(1, total=0))
    assert picture(doc) == {
        "current": (empty,),
        "slots": [(1, empty, ())],
        "others": [],
        "unreadable": [],
    }
    assert doc.current.total == 0
    with pytest.raises(ValueError):
        doc.assign_page(empty, 2)


@pytest.mark.parametrize("page, total", [(4, 3), (0, 3), (2, 0), (-1, 5)])
def test_page_number_out_of_range_is_unreadable(page, total):
    doc, (good, bad) = build(info(1), info(page, total=total))
    assert picture(doc) == {
        "current": (good,),
        "slots": [(1, good, ()), (2, None, ()), (3, None, ())],
        "others": [],
        "unreadable": [bad],
    }
    view = doc.scan(bad)
    assert view.state == ScanState.UNREADABLE
    assert view.reason == "page number out of range"
    assert view.info == info(page, total=total)


def test_unknown_ids_raise_key_error():
    doc, (a,) = build(info(1))
    calls = [
        lambda: doc.set_working(99),
        lambda: doc.set_identified(99, info(1)),
        lambda: doc.set_outcome(99, out()),
        lambda: doc.set_unreadable(99, "x"),
        lambda: doc.remove_scan(99),
        lambda: doc.assign_page(99, 1),
        lambda: doc.use_scan(99),
        lambda: doc.scan(99),
    ]
    for call in calls:
        with pytest.raises(KeyError):
            call()
    doc.remove_scan(a)
    with pytest.raises(KeyError):
        doc.remove_scan(a)


# --- Scan states and event order ----------------------------------------------


def test_scan_states_follow_the_work():
    doc = Document()
    s = add(doc, 1)
    assert doc.scan(s).state == ScanState.WAITING
    doc.set_working(s)
    assert doc.scan(s).state == ScanState.WORKING
    doc.set_identified(s, info(1))
    assert doc.scan(s).state == ScanState.WORKING
    doc.set_outcome(s, out(lost=1))
    assert doc.scan(s) == ScanView(s, "/scans/1.png", ScanState.DONE, info(1), out(lost=1), "")


@pytest.mark.parametrize("outcome_first", [False, True])
def test_outcome_and_identity_in_either_order(outcome_first):
    doc = Document()
    s = add(doc, 1)
    doc.set_working(s)
    steps = [lambda: doc.set_identified(s, info(2)), lambda: doc.set_outcome(s, out(3))]
    for step in reversed(steps) if outcome_first else steps:
        step()
    assert doc.scan(s).state == ScanState.DONE
    assert doc.scan(s).outcome == out(3)
    assert picture(doc)["slots"] == [(1, None, ()), (2, s, ()), (3, None, ())]


def test_unreadable_after_identified_wins_and_keeps_info():
    doc, (a, b) = build(info(1), info(2))
    doc.set_unreadable(b, "decoding failed")
    view = doc.scan(b)
    assert view.state == ScanState.UNREADABLE
    assert (view.reason, view.info) == ("decoding failed", info(2))
    assert picture(doc) == {
        "current": (a,),
        "slots": [(1, a, ()), (2, None, ()), (3, None, ())],
        "others": [],
        "unreadable": [b],
    }


def test_final_state_does_not_depend_on_the_order_results_arrive():
    infos = [
        info(2, total=3, name="photos.tar.", tag=None),
        info(1, tag=OTHER_TAG),
        info(1, total=3, name="photos.tar.g", tag=None),
        info(3, total=3, name="photos.tar", tag=None),
        info(1, name="photos.taz", tag=None),
        info(9),  # out of range
    ]
    outcomes = {0: out(1), 2: out(0, 5), 3: out(0, 2)}
    expected = None
    for order in itertools.permutations(range(len(infos))):
        doc = Document()
        ids = [add(doc, n) for n in range(len(infos))]
        for n in order:
            doc.set_identified(ids[n], infos[n])
            if n in outcomes:
                doc.set_outcome(ids[n], outcomes[n])
        result = (picture(doc), doc.current, doc.others(), doc.unreadable(), doc.scans())
        if expected is None:
            expected = result
        assert result == expected, order
    assert expected[0] == {
        "current": (1, 3, 4),
        "slots": [(1, 3, ()), (2, 1, ()), (3, 4, ())],
        "others": [(2,), (5,)],
        "unreadable": [6],
    }


# --- Keys and titles ------------------------------------------------------------


def test_group_key_is_its_earliest_scan_and_an_old_key_still_works():
    doc, (a, early, x) = build(info(1), None, info(1, name="n", tag=None))
    old_key = doc.others()[0].key
    assert old_key == x
    doc.set_identified(early, info(2, name="n", tag=None))
    assert doc.others()[0].key == early
    doc.switch_to(old_key)  # the group that now contains scan x
    assert picture(doc) == {
        "current": (early, x),
        "slots": [(1, x, ()), (2, early, ()), (3, None, ())],
        "others": [(a,)],
        "unreadable": [],
    }
    assert doc.current.key == early
    for bad_key in (99, a + 100, None):
        with pytest.raises(KeyError):
            doc.switch_to(bad_key)


def test_switch_to_a_scan_in_no_group_raises():
    doc, (a, bad) = build(info(1), None)
    doc.set_unreadable(bad, "label unreadable")
    with pytest.raises(KeyError):
        doc.switch_to(bad)


def test_tagged_group_title_is_the_longest_name_on_a_tie():
    doc, (a, b) = build(info(1, name="holiday-photos.t"), info(2, name="holiday-photos.tar"))
    assert doc.current.title == "holiday-photos.tar"


def test_tagged_group_title_is_the_most_common_name():
    # A tagged label is accepted on a plausible reading: one misread scan with a
    # longer name must not rename the document or its suggested file.
    doc, _ = build(
        info(1, name="doc.tar"),
        info(2, name="doc.tar  "),  # trailing spaces do not count
        info(3, name="doc.tar.misread"),
    )
    assert doc.current.title == "doc.tar"
    assert doc.suggested_name == "doc.tar"
    doc, _ = build(info(1, name="doc.tar.misread"), info(2, name="doc.tar"),
                   info(3, name="doc.tar"), info(1, name="doc,tar", tag=OTHER_TAG))  # fmt: skip
    assert doc.current.title == "doc.tar"
    assert doc.others()[0].title == "doc,tar"


def test_untagged_group_title_is_still_the_longest_name():
    doc, _ = build(info(1, name="doc", tag=None), info(2, name="doc", tag=None),
                   info(3, name="doc.tar", tag=None))  # fmt: skip
    assert doc.current.title == "doc.tar"


# --- User choices are never lost to background results ----------------------------


@pytest.mark.parametrize("order", [(3, 4), (4, 3)])
def test_regression_switch_choice_does_not_drift_with_result_order(order):
    # The user picks the "ac" printout; "a" and "ab" (added earlier) arrive later
    # in either order. "a" briefly groups with "ac" in one order; it must not
    # carry the user's choice away.
    doc = Document()
    ids = [add(doc, n) for n in range(1, 6)]
    doc.set_identified(ids[0], info(1))
    doc.set_identified(ids[4], info(3, name="ac", tag=None))
    doc.switch_to(doc.others()[0].key)
    late = {3: info(1, name="a", tag=None), 4: info(2, name="ab", tag=None)}
    for n in order:
        doc.set_identified(ids[n - 1], late[n])
    assert picture(doc) == {
        "current": (5,),
        "slots": [(1, None, ()), (2, None, ()), (3, 5, ())],
        "others": [(1,), (3, 4)],
        "unreadable": [],
    }


@pytest.mark.parametrize("unreadable_first", [True, False])
def test_regression_switch_choice_not_reset_by_an_unreadable_scan(unreadable_first):
    doc, (a, b, c) = build(info(1), info(1, tag=OTHER_TAG), None)
    doc.switch_to(b)
    steps = [lambda: doc.set_unreadable(b, "decoding failed"),
             lambda: doc.set_identified(c, info(2, tag=OTHER_TAG))]
    for step in steps if unreadable_first else reversed(steps):
        step()
    # The choice is {b} with b's tagged identity; once b fails, the group with that
    # identity (c, a later page of the same printout) is the document, in both orders.
    assert picture(doc) == {
        "current": (c,),
        "slots": [(1, None, ()), (2, c, ()), (3, None, ())],
        "others": [(a,)],
        "unreadable": [b],
    }


@pytest.mark.parametrize("identified_first", [True, False])
def test_regression_assignment_survives_identified_then_unreadable(identified_first):
    doc, (e, a, f, bad) = build(None, info(1), None, None)
    doc.set_unreadable(bad, "label unreadable")
    doc.assign_page(bad, 2)
    doc.set_outcome(a, out())
    steps = [lambda: doc.set_identified(e, info(1, tag=OTHER_TAG)),
             lambda: doc.set_unreadable(e, "decoding failed")]
    for step in steps if identified_first else reversed(steps):
        step()
    assert picture(doc) == {
        "current": (a, bad),
        "slots": [(1, a, ()), (2, bad, ()), (3, None, ())],
        "others": [],
        "unreadable": [e],
    }


@pytest.mark.parametrize("identified_first", [True, False])
def test_regression_use_scan_survives_identified_then_unreadable(identified_first):
    doc, (e, a, b) = build(None, info(1), info(1))
    doc.set_outcome(a, out())
    doc.set_outcome(b, out(3))
    doc.use_scan(b)
    steps = [lambda: doc.set_identified(e, info(1, tag=OTHER_TAG)),
             lambda: doc.set_unreadable(e, "decoding failed")]
    for step in steps if identified_first else reversed(steps):
        step()
    assert picture(doc) == {
        "current": (a, b),
        "slots": [(1, b, (a,)), (2, None, ()), (3, None, ())],
        "others": [],
        "unreadable": [e],
    }


def test_choice_and_assignments_are_inactive_not_lost_while_their_scans_are_away():
    doc, (a, b, bad) = build(info(1), info(1, tag=OTHER_TAG), None)
    doc.set_unreadable(bad, "label unreadable")
    doc.switch_to(b)
    doc.assign_page(bad, 2)
    away = {
        "current": (a,),
        "slots": [(1, a, ()), (2, None, ()), (3, None, ())],
        "others": [],
        "unreadable": [b, bad],
    }
    doc.set_identified(b, info(7, tag=OTHER_TAG))  # out of range: b is not grouped
    assert picture(doc) == away
    doc.set_identified(b, info(1, tag=OTHER_TAG))
    assert picture(doc) == {
        "current": (b, bad),
        "slots": [(1, b, ()), (2, bad, ()), (3, None, ())],
        "others": [(a,)],
        "unreadable": [],
    }


@pytest.mark.parametrize("fails_first", [True, False])
def test_regression_chosen_printout_kept_when_its_first_scan_fails(fails_first):
    doc, (a, b, c, d) = build(info(1), info(1, tag=OTHER_TAG), None, None)
    doc.switch_to(b)  # the choice is {b}
    steps = [lambda: doc.set_identified(c, info(2, tag=OTHER_TAG)),
             lambda: doc.set_identified(d, info(3, tag=OTHER_TAG))]
    fail = lambda: doc.set_unreadable(b, "decoding failed")  # noqa: E731
    for step in [fail, *steps] if fails_first else [*steps, fail]:
        step()
    assert picture(doc) == {
        "current": (c, d),
        "slots": [(1, None, ()), (2, c, ()), (3, d, ())],
        "others": [(a,)],
        "unreadable": [b],
    }


def test_regression_assignment_kept_when_the_chosen_printouts_first_scan_fails():
    doc, (a, b, c, d, bad) = build(info(1), info(1, tag=OTHER_TAG), None, None, None)
    doc.set_unreadable(bad, "label unreadable")
    doc.switch_to(b)
    doc.set_identified(c, info(2, tag=OTHER_TAG))
    doc.set_identified(d, info(3, tag=OTHER_TAG))
    doc.assign_page(bad, 1)  # while pages 1-3 of the printout are on screen
    doc.set_unreadable(b, "decoding failed")
    assert picture(doc) == {
        "current": (c, d, bad),
        "slots": [(1, bad, ()), (2, c, ()), (3, d, ())],
        "others": [(a,)],
        "unreadable": [b],
    }
    doc.remove_scan(b)  # removing the failed scan does not abandon the printout
    assert picture(doc)["current"] == (c, d, bad)


def test_regression_working_in_the_fallback_document_keeps_it():
    # The chosen printout's only scan failed, so the default document is shown; working
    # in it adds it to the choice, and an earlier-added scan of a third printout that is
    # identified later does not take over.
    doc, (e, a, b, bad) = build(None, info(1), info(1, tag=OTHER_TAG), None)
    doc.set_unreadable(bad, "label unreadable")
    doc.switch_to(b)
    doc.set_unreadable(b, "decoding failed")
    doc.assign_page(bad, 2)
    doc.set_identified(e, info(1, tag=Tag(500000, "cccccccc")))
    assert picture(doc) == {
        "current": (a, bad),
        "slots": [(1, a, ()), (2, bad, ()), (3, None, ())],
        "others": [(e,)],
        "unreadable": [b],
    }


def test_title_comes_from_the_scans_a_group_shows():
    doc, (a, long_name, short_name) = build(
        info(1, name="a.tar"),
        info(1, name="report-final.tar", tag=OTHER_TAG),
        info(2, name="report", tag=OTHER_TAG),
    )
    doc.assign_page(long_name, 2)
    assert doc.others()[0].scan_ids == (short_name,)
    assert doc.others()[0].title == "report"
    assert doc.current.title == "a.tar"


def test_assigned_scan_that_becomes_unreadable_stays_in_its_slot():
    doc, (a, foreign) = build(info(1), info(1, tag=OTHER_TAG))
    doc.assign_page(foreign, 3)
    doc.set_unreadable(foreign, "decoding failed")
    assert picture(doc) == {
        "current": (a, foreign),
        "slots": [(1, a, ()), (2, None, ()), (3, foreign, ())],
        "others": [],
        "unreadable": [],
    }
    assert doc.scan(foreign).state == ScanState.UNREADABLE


def test_working_in_the_default_document_keeps_it():
    # Assigning a page makes the document the user's choice, so an earlier-added scan
    # that later turns out to be another printout does not take over.
    doc, (early, a, bad) = build(None, info(1), None)
    doc.set_unreadable(bad, "label unreadable")
    doc.assign_page(bad, 2)
    doc.set_identified(early, info(1, tag=OTHER_TAG))
    assert picture(doc) == {
        "current": (a, bad),
        "slots": [(1, a, ()), (2, bad, ()), (3, None, ())],
        "others": [(early,)],
        "unreadable": [],
    }


def test_switching_back_after_leaving_drops_what_was_done_there():
    doc, (a, b, bad) = build(info(1), info(1, tag=OTHER_TAG), None)
    doc.set_unreadable(bad, "label unreadable")
    doc.assign_page(bad, 3)
    doc.switch_to(b)
    doc.switch_to(a)
    assert picture(doc) == {
        "current": (a,),
        "slots": [(1, a, ()), (2, None, ()), (3, None, ())],
        "others": [(b,)],
        "unreadable": [bad],
    }


def test_regression_removing_a_failed_scan_keeps_the_assignment_of_its_printout():
    # The assignment was made while the chosen printout held only b; when b is removed,
    # what remembers the printout takes in its remaining scan c instead of being dropped.
    doc, (a, b, c, bad) = build(info(1), info(1, tag=OTHER_TAG), None, None)
    doc.set_unreadable(bad, "label unreadable")
    doc.switch_to(b)
    doc.assign_page(bad, 3)
    doc.set_unreadable(b, "decoding failed")
    doc.set_identified(c, info(2, tag=OTHER_TAG))
    chosen = {
        "current": (c, bad),
        "slots": [(1, None, ()), (2, c, ()), (3, bad, ())],
        "others": [(a,)],
        "unreadable": [b],
    }
    assert picture(doc) == chosen
    assert doc.current.tag == OTHER_TAG
    doc.remove_scan(b)
    assert picture(doc) == {**chosen, "unreadable": []}
    assert doc.current.tag == OTHER_TAG


def test_working_in_the_fallback_document_gives_the_choice_its_identity():
    # The choice takes the identity of the document the user worked in (TAG), not the
    # one switched to earlier (OTHER_TAG). When none of the choice's scans is grouped
    # and no group has TAG, the default rule picks v, the earliest grouped scan, even
    # though c is a page of the printout switched to first. A later page of the TAG
    # printout brings the choice back, with its assignment.
    third = Tag(500000, "cccccccc")
    doc, (a, b, v, c, d, bad) = build(info(1), info(1, tag=OTHER_TAG), None, None, None, None)
    doc.set_unreadable(bad, "label unreadable")
    doc.switch_to(b)
    doc.set_unreadable(b, "decoding failed")
    assert doc.current.scan_ids == (a,)
    doc.assign_page(bad, 2)
    doc.set_unreadable(a, "decoding failed")
    doc.set_identified(v, info(1, tag=third))
    doc.set_identified(c, info(2, tag=OTHER_TAG))
    assert picture(doc) == {
        "current": (v,),
        "slots": [(1, v, ()), (2, None, ()), (3, None, ())],
        "others": [(c,)],
        "unreadable": [a, b, bad],
    }
    doc.set_identified(d, info(3))
    assert picture(doc) == {
        "current": (d, bad),
        "slots": [(1, None, ()), (2, bad, ()), (3, d, ())],
        "others": [(v,), (c,)],
        "unreadable": [a, b],
    }


@pytest.mark.parametrize("assign", [True, False])
def test_untagged_limit_an_assignment_follows_the_earliest_scan_of_its_reference(assign):
    # The documented limit, second route: the user picks the group of "ab", "a" joins
    # it, a page is assigned; when the earlier-added "ac" is identified, "a" leaves
    # "ab" for "ac", and the remembered reference {a, ab} follows "a".
    doc, (x, ac, a, ab, bad) = build(info(1), None, None, None, None)
    doc.set_unreadable(bad, "label unreadable")
    doc.set_identified(ab, info(2, name="ab", tag=None))
    doc.switch_to(ab)
    doc.set_identified(a, info(1, name="a", tag=None))
    assert doc.current.scan_ids == (a, ab)
    if assign:
        doc.assign_page(bad, 3)  # ab is page 2
    doc.set_identified(ac, info(2, name="ac", tag=None))
    if assign:
        assert doc.current.scan_ids == (ac, a, bad)
        assert doc.slots()[2].scan_id == bad
    else:
        assert doc.current.scan_ids == (ab,)


# --- Property: the order of background results does not matter --------------------

POOL = [
    info(1, name="", tag=None),
    info(1, name="a", tag=None),
    info(2, name="ab", tag=None),
    info(3, name="ac", tag=None),
    info(2, name="ab  ", tag=None),
    info(1, name="ab", tag=None),
    info(1),
    info(2),
    info(2, name="other"),
    info(1, tag=OTHER_TAG),
    info(5),  # page out of range
    info(1, total=0, name="a", tag=None),
    info(2, fmt=LETTER, name="ab", tag=None),
    info(1, fmt=LETTER),
]


def _random_scenario(rng):
    """Scans with their final background events, and the number of user operations.

    Each background event is put in a batch: batch j happens before user operation j,
    the last batch after all of them. Only the order within a batch varies.
    """
    n = rng.randint(3, 7)
    n_ops = rng.randint(1, 4)
    events = []
    for scan in range(n):
        mine = []
        if rng.random() < 0.3:
            mine.append(("working", None))
        if rng.random() < 0.85:
            mine.append(("identified", rng.choice(POOL)))
        if rng.random() < 0.5:
            mine.append(("outcome", out(rng.randint(0, 2), rng.randint(0, 3))))
        if rng.random() < 0.35:
            mine.append(("unreadable", "decoding failed"))
        events += [(rng.randint(0, n_ops), scan, kind, value) for kind, value in mine]
    return n, n_ops, events


def _random_operation(rng, doc, ids):
    """A user operation, mostly valid in the state it is chosen in."""
    current = doc.current
    others = [g.key for g in doc.others()]
    pages = max(current.total, 1) if current else 1
    kind = rng.choice(["switch", "switch", "hand", "assign", "assign", "use", "remove"])
    if kind == "switch":
        return ("switch_to", rng.choice(others) if others and rng.random() < 0.9 else 999)
    if kind == "hand":
        return ("start_by_hand", rng.choice([A, LETTER]), rng.randint(0, 3))
    if kind == "assign":
        page = rng.randint(1, pages) if rng.random() < 0.9 else pages + 1
        return ("assign_page", rng.choice(ids), page)
    if kind == "use" and current and current.scan_ids:
        return ("use_scan", rng.choice(current.scan_ids))
    return ("use_scan" if kind == "use" else "remove_scan", rng.choice(ids))


def _apply(doc, ids, event):
    _, scan, kind, value = event
    method = {
        "working": lambda i: doc.set_working(i),
        "identified": lambda i: doc.set_identified(i, value),
        "outcome": lambda i: doc.set_outcome(i, value),
        "unreadable": lambda i: doc.set_unreadable(i, value),
    }[kind]
    try:
        method(ids[scan])
    except KeyError:
        pass  # the user removed this scan


def _run(n, n_ops, events, shuffle, ops, choose):
    """Plays the scenario; chooses the operations (into ops) when choose is given."""
    doc = Document()
    ids = [add(doc, k) for k in range(n)]
    results = []
    for batch in range(n_ops + 1):
        mine = [e for e in events if e[0] == batch]
        shuffle(mine)
        for event in mine:
            _apply(doc, ids, event)
        if batch == n_ops:
            break
        if choose is not None:
            ops.append(choose(doc, ids, batch))
        name, *args = ops[batch]
        try:
            getattr(doc, name)(*args)
            results.append(None)
        except (KeyError, ValueError) as error:
            results.append(type(error))
    return (doc.current, doc.slots(), doc.others(), doc.unreadable(), doc.scans(), results)


def _away_and_back_scenario(rng):
    """The family most likely to lose user work: switch to a printout, assign a page or
    choose a scan in it, the printout goes away (its first scan fails before its later
    pages arrive, or the user leaves) and comes back.

    Scans: 0 printout T page 1, 1 printout U page 1, 2 and 3 U pages 2 and 3, 4 an
    unreadable scan, then 0-2 extra scans (a U page 1 duplicate or from the pool).
    """
    events = [(0, 0, "identified", info(1)), (0, 1, "identified", info(1, tag=OTHER_TAG)),
              (0, 4, "unreadable", "label unreadable")]
    # Mostly after the user's work and in the same batch as the first scan failing, so
    # that in some orders it fails before the later pages arrive.
    fails = rng.choice([2, 3])
    if rng.random() < 0.85:
        events.append((fails, 1, "unreadable", "decoding failed"))
    for scan, page in ((2, 2), (3, 3)):
        if rng.random() < 0.9:
            batch = fails if rng.random() < 0.75 else rng.randint(1, 3)
            events.append((batch, scan, "identified", info(page, tag=OTHER_TAG)))
    extras = rng.randint(0, 2)
    for scan in range(5, 5 + extras):
        identity = info(1, tag=OTHER_TAG) if rng.random() < 0.2 else rng.choice(POOL)
        events.append((rng.randint(0, 3), scan, "identified", identity))
    for scan in range(5 + extras):
        if scan != 4 and rng.random() < 0.5:
            events.append((rng.randint(0, 3), scan, "outcome", out(rng.randint(0, 2))))
    return 5 + extras, 3, events


def _away_and_back_operations(rng):
    def choose(doc, ids, j):
        current = doc.current
        if j == 0:
            return ("switch_to", ids[1])
        if j == 1:
            if rng.random() < 0.6 or not (current and current.scan_ids):
                pages = max(current.total, 1) if current else 1
                return ("assign_page", ids[4], rng.randint(1, pages))
            return ("use_scan", rng.choice(current.scan_ids))
        return rng.choice([
            ("switch_to", ids[0]), ("switch_to", ids[2]), ("remove_scan", ids[1]),
            ("start_by_hand", A, 3), ("use_scan", ids[2]), ("assign_page", ids[4], 3),
        ])
    return choose


def _check_background_order(scenario, operations, scenarios, salt):
    for seed in range(scenarios):
        rng = random.Random(seed + salt)
        n, n_ops, events = scenario(rng)
        ops: list = []
        expected = _run(n, n_ops, events, lambda _: None, ops,
                        operations(random.Random(seed + salt + 10**6)))
        for rep in range(5):
            order = random.Random(seed * 31 + rep + salt)
            got = _run(n, n_ops, events, order.shuffle, ops, None)
            assert got == expected, (seed, rep, ops)


def test_property_background_order_never_changes_the_result():
    def operations(rng):
        return lambda doc, ids, j: _random_operation(rng, doc, ids)
    _check_background_order(_random_scenario, operations, 1000, 0)


def test_property_user_work_survives_a_printout_going_away_and_back():
    _check_background_order(_away_and_back_scenario, _away_and_back_operations, 300, 7 * 10**6)


# --- Page health, document state, assembling and verifying -------------------

PAGE = 1000  # bytes per page in these tests


def page_out(data, lost=0, repaired=0):
    return PageOutcome(data, (1000, repaired, 0, 0), lost)


def split(data, pages=None):
    """The pages a file is printed on, the last one padded with zeros."""
    pages = pages or max(1, -(-len(data) // PAGE))
    padded = data.ljust(pages * PAGE, b"\0")
    return [padded[i * PAGE:(i + 1) * PAGE] for i in range(pages)]


def decoded(tag, pages, name="doc.tar"):
    """A document whose pages (None: not added) are all identified and decoded."""
    doc = Document()
    ids = []
    for number, data in enumerate(pages, 1):
        if data is None:
            ids.append(None)
            continue
        scan_id = add(doc, number)
        doc.set_identified(scan_id, info(number, total=len(pages), name=name, tag=tag))
        doc.set_outcome(scan_id, page_out(data))
        ids.append(scan_id)
    return doc, ids


def health(doc):
    return [p.health for p in doc.pages()]


def counts(s):
    return (s.good, s.repaired, s.damaged, s.unreadable, s.missing)


def count_passes(doc):
    """Counts the passes over ``doc.chunks()`` and the bytes each produced."""
    passes = []
    original = doc.chunks

    def chunks():
        produced = [0]
        passes.append(produced)
        for chunk in original():
            produced[0] += len(chunk)
            yield chunk

    doc.chunks = chunks
    return passes


def test_health_of_each_slot_state():
    doc, (good, rep, dmg, waiting, working, bad) = build(
        info(1, total=7), info(2, total=7), info(3, total=7), None, None, None
    )
    doc.set_outcome(good, page_out(b"g" * PAGE))
    doc.set_outcome(rep, page_out(b"r" * PAGE, repaired=198))
    doc.set_outcome(dmg, page_out(b"d" * PAGE, lost=37, repaired=5))
    doc.assign_page(waiting, 4)
    doc.assign_page(working, 5)
    doc.set_working(working)
    doc.assign_page(bad, 6)
    doc.set_unreadable(bad, "no page found")
    assert health(doc) == [
        Health.GOOD,
        Health.REPAIRED,
        Health.DAMAGED,
        Health.WAITING,
        Health.WORKING,
        Health.UNREADABLE,
        Health.MISSING,
    ]
    pages = doc.pages()
    assert pages[0] == PageView(1, Health.GOOD, good, (), 0, 0, (1000, 0, 0, 0))
    assert pages[1] == PageView(2, Health.REPAIRED, rep, (), 198, 0, (1000, 198, 0, 0))
    assert (pages[2].repaired, pages[2].lost) == (5, 37)
    assert pages[3] == PageView(4, Health.WAITING, waiting, (), 0, 0, None)
    assert pages[6] == PageView(7, Health.MISSING, None, (), 0, 0, None)


def test_identified_page_without_an_outcome_is_working():
    doc, (a, b) = build(info(1, total=2), info(1, total=2))
    doc.set_outcome(b, page_out(b"b" * PAGE))
    assert doc.scan(a).state == ScanState.WORKING
    assert doc.pages()[0] == PageView(1, Health.GOOD, b, (a,), 0, 0, (1000, 0, 0, 0))
    doc, (a,) = build(info(1, total=2))
    assert health(doc) == [Health.WORKING, Health.MISSING]
    assert doc.summary().state == DocState.WORKING


def test_summary_counts_and_states():
    doc, (p1, p2, p3) = build(info(1), info(2), None)
    doc.set_outcome(p1, page_out(b"1" * PAGE))
    doc.set_outcome(p2, page_out(b"2" * PAGE, repaired=3))
    s = doc.summary()
    assert s == Summary(DocState.INCOMPLETE, 1, 1, 0, 0, 1, TAG.size)
    doc.assign_page(p3, 3)
    doc.set_unreadable(p3, "label unreadable")
    assert counts(doc.summary()) == (1, 1, 0, 1, 0)
    assert doc.summary().state == DocState.INCOMPLETE


def test_summary_of_an_empty_document():
    doc = Document()
    assert doc.summary() == Summary(DocState.EMPTY, 0, 0, 0, 0, 0, None)
    assert doc.pages() == ()
    assert doc.page_bytes is None
    assert not doc.can_save
    assert doc.suggested_name == "recovered.bin"


def test_working_while_any_slot_is_waiting():
    data = bytes(range(256)) * 10
    doc, ids = decoded(make_tag(data), split(data))
    assert doc.summary().state == DocState.VERIFIED
    late = add(doc, "late")
    doc.set_identified(late, info(2, total=3, tag=make_tag(data)))  # a spare, no outcome
    assert doc.summary().state == DocState.VERIFIED  # the page in use is decoded
    lost_page = add(doc, "x")
    doc.assign_page(lost_page, 2)  # in use now, waiting
    doc.use_scan(lost_page)
    assert doc.pages()[1].health == Health.WAITING
    assert doc.summary().state == DocState.WORKING
    assert counts(doc.summary()) == (2, 0, 0, 0, 0)


def test_verified_when_assembled_data_matches_tag():
    data = bytes(range(256)) * 10  # 2560 bytes over pages of 1000 bytes
    tag = make_tag(data)
    pages = [data[0:1000], data[1000:2000], data[2000:] + b"\0" * 440]
    doc, _ = decoded(tag, pages)
    s = doc.summary()
    assert s.state == DocState.VERIFIED and s.size == 2560
    assert counts(s) == (3, 0, 0, 0, 0)
    assert doc.page_bytes == PAGE
    assert doc.assemble() == data and len(doc.assemble()) == 2560
    assert doc.can_save


def test_mismatch_when_a_page_is_silently_wrong():
    data = bytes(range(256)) * 10
    pages = split(data)
    pages[1] = pages[1][:10] + bytes([pages[1][10] ^ 1]) + pages[1][11:]
    doc, _ = decoded(make_tag(data), pages)
    assert health(doc) == [Health.GOOD] * 3
    assert doc.summary().state == DocState.MISMATCH
    assert len(doc.assemble()) == len(data) and doc.assemble() != data


def test_untagged_complete_document_is_unverifiable_and_padded():
    data = bytes(range(256)) * 10
    doc, _ = decoded(None, split(data))
    s = doc.summary()
    assert s == Summary(DocState.UNVERIFIABLE, 3, 0, 0, 0, 0, None)
    assert doc.assemble() == data + b"\0" * 440
    assert len(doc.assemble()) == 3 * doc.page_bytes


def test_missing_page_contributes_zeros_and_keeps_offsets():
    data = bytes(range(1, 251)) * 12  # 3000 bytes, no zero byte
    pages = split(data)
    doc, _ = decoded(make_tag(data), [pages[0], None, pages[2]])
    assert health(doc) == [Health.GOOD, Health.MISSING, Health.GOOD]
    assert doc.summary().state == DocState.INCOMPLETE
    got = doc.assemble()
    assert len(got) == 3000
    assert got[:1000] == data[:1000]
    assert got[1000:2000] == bytes(1000)
    assert got[2000:] == data[2000:]


def test_damaged_page_contributes_its_data():
    data = bytes(range(1, 251)) * 12
    pages = split(data)
    doc, (p1, p2, p3) = decoded(make_tag(data), pages)
    doc.set_outcome(p2, page_out(b"\xff" * PAGE, lost=4))
    assert health(doc) == [Health.GOOD, Health.DAMAGED, Health.GOOD]
    assert doc.summary().state == DocState.INCOMPLETE
    assert doc.assemble() == pages[0] + b"\xff" * PAGE + pages[2]


def test_assigned_unreadable_scan_shows_unreadable_and_contributes_zeros():
    data = bytes(range(1, 251)) * 8  # 2000 bytes: two pages
    pages = split(data)
    doc, (p1, _) = decoded(make_tag(data), [pages[0], None])
    bad = add(doc, "bad")
    doc.assign_page(bad, 2)
    doc.set_unreadable(bad, "decoding failed")
    assert doc.pages()[1] == PageView(
        2, Health.UNREADABLE, bad, (), 0, 0, None, "decoding failed"
    )
    assert doc.summary() == Summary(DocState.INCOMPLETE, 1, 0, 0, 1, 0, 2000)
    assert doc.assemble() == pages[0] + bytes(PAGE)


def test_assemble_with_nothing_decoded_raises():
    with pytest.raises(ValueError):
        Document().assemble()
    doc, _ = build(info(1), info(2))
    assert not doc.can_save
    assert doc.page_bytes is None
    with pytest.raises(ValueError):
        doc.assemble()


def test_page_of_another_size_is_unreadable_not_an_error():
    doc, (p1, p2) = build(info(1, total=2, tag=None), info(2, total=2, tag=None))
    doc.set_outcome(p1, page_out(b"a" * PAGE))
    doc.set_outcome(p2, page_out(b"b" * (PAGE + 1)))
    assert doc.page_bytes == PAGE
    assert doc.pages()[1] == PageView(2, Health.UNREADABLE, p2, (), 0, 0, None, SIZE_MISMATCH)
    assert doc.summary() == Summary(DocState.INCOMPLETE, 1, 0, 0, 1, 0, None)
    assert doc.assemble() == b"a" * PAGE + bytes(PAGE)


def test_regression_scan_of_another_paper_size_used_for_a_page():
    data = bytes(range(1, 251)) * 8  # 2000 bytes: two pages
    pages = split(data)
    doc, (p1, p2) = decoded(make_tag(data), pages)
    passes = count_passes(doc)
    assert doc.summary().state == DocState.VERIFIED
    letter = add(doc, "letter")
    doc.set_identified(letter, info(2, total=2, fmt=LETTER, tag=make_tag(data)))
    doc.set_outcome(letter, page_out(b"L" * (PAGE + 37)))
    doc.assign_page(letter, 2)
    doc.use_scan(letter)
    assert doc.pages()[1] == PageView(
        2, Health.UNREADABLE, letter, (p2,), 0, 0, None, FORMAT_MISMATCH
    )
    assert doc.summary() == Summary(DocState.INCOMPLETE, 1, 0, 0, 1, 0, 2000)
    assert doc.assemble() == pages[0] + bytes(PAGE)
    assert doc.can_save
    # Choosing the proper scan again restores the verdict; the bytes are the same as
    # before, so the cached verdict holds and nothing is hashed again.
    doc.use_scan(p2)
    assert doc.summary().state == DocState.VERIFIED
    assert len(passes) == 2  # the first verdict and the assemble() above
    doc.remove_scan(letter)
    assert doc.summary().state == DocState.VERIFIED
    assert doc.assemble() == data


def test_regression_assigned_scan_with_an_unreadable_label_and_another_size():
    data = bytes(range(1, 251)) * 8
    pages = split(data)
    doc, (p1, _) = decoded(make_tag(data), [pages[0], None])
    odd = add(doc, "odd")
    doc.set_unreadable(odd, "label unreadable")
    doc.set_outcome(odd, page_out(b"o" * (PAGE + 3)))
    doc.assign_page(odd, 2)
    assert doc.pages()[1].health == Health.UNREADABLE
    assert doc.pages()[1].reason == SIZE_MISMATCH
    assert doc.summary().state == DocState.INCOMPLETE
    assert doc.assemble() == pages[0] + bytes(PAGE)
    proper = add(doc, "proper")
    doc.set_identified(proper, info(2, total=2, tag=make_tag(data)))
    doc.set_outcome(proper, page_out(pages[1]))
    doc.use_scan(proper)
    assert doc.summary().state == DocState.VERIFIED


def test_page_size_comes_from_the_documents_own_scans_first():
    # Only a hand-assigned scan has an outcome: it sets the page size. Once one of the
    # group's own scans has an outcome, that one does.
    doc, (p1, p2) = build(info(1, total=2, tag=None), None)
    doc.set_unreadable(p2, "label unreadable")
    doc.set_outcome(p2, page_out(b"b" * (PAGE + 3)))
    doc.assign_page(p2, 2)
    assert doc.page_bytes == PAGE + 3
    assert doc.can_save
    assert doc.pages()[1].health == Health.GOOD
    doc.set_outcome(p1, page_out(b"a" * PAGE))
    assert doc.page_bytes == PAGE
    assert doc.pages()[1].reason == SIZE_MISMATCH
    assert doc.assemble() == b"a" * PAGE + bytes(PAGE)


def test_verdict_follows_a_change_of_page_size():
    # The earliest-added scan of the group gets an outcome of another length later: it
    # sets the page size, so a page that verified becomes unusable; no stale verdict.
    data = bytes(range(1, 251)) * 8
    pages = split(data)
    doc = Document()
    early = add(doc, "early")
    doc.set_identified(early, info(1, total=2, tag=make_tag(data)))
    p1 = add(doc, "p1")
    p2 = add(doc, "p2")
    doc.set_identified(p1, info(1, total=2, tag=make_tag(data)))
    doc.set_identified(p2, info(2, total=2, tag=make_tag(data)))
    doc.set_outcome(p1, page_out(pages[0]))
    doc.set_outcome(p2, page_out(pages[1]))
    doc.use_scan(p1)
    assert doc.summary().state == DocState.VERIFIED
    doc.set_outcome(early, page_out(b"e" * (PAGE + 1)))
    assert doc.page_bytes == PAGE + 1
    assert [p.reason for p in doc.pages()] == [SIZE_MISMATCH, SIZE_MISMATCH]
    assert doc.summary().state == DocState.INCOMPLETE
    assert not doc.can_save
    with pytest.raises(ValueError, match="no page has been decoded"):
        doc.chunks()
    doc.remove_scan(early)
    assert doc.summary().state == DocState.VERIFIED


def test_empty_file_assembles_to_nothing():
    tag = make_tag(b"")
    doc, (only,) = build(info(1, total=0, tag=tag))
    assert doc.summary().state == DocState.WORKING
    doc.set_outcome(only, page_out(bytes(PAGE)))
    assert doc.summary() == Summary(DocState.VERIFIED, 1, 0, 0, 0, 0, 0)
    assert doc.assemble() == b""


def test_verdict_updates_after_replacing_a_page():
    data = bytes(range(256)) * 10
    pages = split(data)
    wrong = b"\x01" + pages[2][1:]
    doc, (p1, p2, p3) = decoded(make_tag(data), [pages[0], pages[1], wrong])
    assert doc.summary().state == DocState.MISMATCH
    spare = add(doc, "spare")
    doc.set_identified(spare, info(3, tag=make_tag(data)))
    doc.set_outcome(spare, page_out(pages[2], repaired=2))
    assert doc.pages()[2].scan_id == p3  # fewer repaired wins until the user chooses
    assert doc.summary().state == DocState.MISMATCH
    doc.use_scan(spare)
    assert doc.pages()[2] == PageView(3, Health.REPAIRED, spare, (p3,), 2, 0, (1000, 2, 0, 0))
    assert doc.summary().state == DocState.VERIFIED
    assert doc.assemble() == data


def test_verdict_changes_when_a_page_is_removed():
    data = bytes(range(256)) * 10
    doc, (p1, p2, p3) = decoded(make_tag(data), split(data))
    assert doc.summary().state == DocState.VERIFIED
    doc.remove_scan(p2)
    assert doc.summary() == Summary(DocState.INCOMPLETE, 2, 0, 0, 0, 1, 2560)


def test_verdict_is_computed_once_until_the_document_changes():
    data = bytes(range(256)) * 10
    pages = split(data)
    doc, (p1, p2, p3) = decoded(make_tag(data), pages)
    passes = count_passes(doc)
    assert doc.summary().state == DocState.VERIFIED
    assert doc.summary().state == DocState.VERIFIED
    assert passes == [[2560]]
    other = add(doc, "other")  # unrelated: nothing assembled changes
    doc.set_identified(other, info(1, tag=OTHER_TAG))
    assert doc.summary().state == DocState.VERIFIED
    assert len(passes) == 1
    doc.set_outcome(p2, page_out(b"\x01" + pages[1][1:]))  # same scan, new outcome
    assert doc.summary().state == DocState.MISMATCH
    doc.set_outcome(p2, page_out(pages[1]))
    assert doc.summary().state == DocState.VERIFIED
    assert len(passes) == 3


def test_page_count_above_the_encoders_limit_is_unreadable():
    doc, (a, b) = build(info(1, total=99999), info(1, total=MAX_TOTAL_PAGES, tag=None))
    assert doc.scan(a).state == ScanState.UNREADABLE
    assert doc.scan(a).reason == "page count out of range"
    assert picture(doc)["unreadable"] == [a]
    assert picture(doc)["current"] == (b,)
    assert len(doc.slots()) == MAX_TOTAL_PAGES
    doc, (a,) = build(info(1, total=MAX_TOTAL_PAGES + 1))
    assert picture(doc) == {"current": None, "slots": [], "others": [], "unreadable": [a]}


def test_max_total_pages_is_the_encoders_limit():
    from optar.encoder import MAX_PAGES

    assert MAX_TOTAL_PAGES == MAX_PAGES


@pytest.mark.parametrize("total", [-1, MAX_TOTAL_PAGES + 1, 99999])
def test_start_by_hand_refuses_impossible_page_counts(total):
    doc = Document()
    with pytest.raises(ValueError):
        doc.start_by_hand(A, total)
    assert doc.current is None


def test_start_by_hand_accepts_the_page_count_limits():
    doc = Document()
    doc.start_by_hand(A, MAX_TOTAL_PAGES)
    assert len(doc.slots()) == MAX_TOTAL_PAGES
    doc.start_by_hand(A, 0)
    assert len(doc.slots()) == 1


def test_chunks_of_a_tagged_document_stop_at_its_size():
    data = bytes(range(1, 251)) * 10  # 2500 bytes: the third page holds 500
    doc, _ = decoded(make_tag(data), split(data))
    chunks = list(doc.chunks())
    assert [len(c) for c in chunks] == [1000, 1000, 500]
    assert b"".join(chunks) == data == doc.assemble()


def test_chunks_never_yield_pages_past_the_tags_size():
    data = bytes(range(1, 251)) * 4  # 1000 bytes: one page, though the label says three
    doc, _ = decoded(make_tag(data), [data, b"\xff" * PAGE, b"\xff" * PAGE])
    assert list(doc.chunks()) == [data]


def test_chunks_of_an_untagged_document_are_whole_pages():
    data = bytes(range(1, 251)) * 10
    doc, _ = decoded(None, split(data))
    chunks = list(doc.chunks())
    assert [len(c) for c in chunks] == [PAGE] * 3
    assert b"".join(chunks) == doc.assemble() == data + bytes(500)


def test_missing_pages_share_one_zero_block():
    doc, (p1, p2, p3, p4) = decoded(None, [None, b"x" * PAGE, None, None])
    chunks = list(doc.chunks())
    assert chunks[1] == b"x" * PAGE
    assert chunks[0] == bytes(PAGE)
    assert chunks[0] is chunks[2] is chunks[3]


def test_chunks_check_before_producing_anything():
    doc, _ = build(info(1), info(2))
    with pytest.raises(ValueError, match="no page has been decoded"):
        doc.chunks()
    doc, (p1,) = build(info(1, total=2, tag=None))
    doc.set_working(p1)
    with pytest.raises(ValueError, match="no page has been decoded"):
        doc.chunks()


def test_short_file_against_a_larger_tag_size_does_not_match():
    data = bytes(range(1, 251)) * 12  # 3000 bytes
    short = Tag(5000, make_tag(data).fingerprint)  # fingerprint of what is produced
    doc, _ = decoded(short, split(data))
    assert doc.assemble() == data  # shorter than the tag says: returned as is
    assert doc.summary().state == DocState.MISMATCH


def test_chunks_of_the_largest_document_use_little_memory():
    page_bytes = 200_000
    doc, (only,) = build(info(5000, total=MAX_TOTAL_PAGES, tag=None))
    doc.set_outcome(only, page_out(b"x" * page_bytes))
    tracemalloc.start()
    try:
        produced = sum(len(c) for c in doc.chunks())
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    assert produced == MAX_TOTAL_PAGES * page_bytes
    assert peak < 50_000_000


def test_suggested_name():
    doc, _ = build(info(1, name="doc.tar"))
    assert doc.suggested_name == "doc.tar"
    doc, _ = build(info(1, name="", tag=None))
    assert doc.suggested_name == "recovered.bin"
    doc, _ = build(info(1, name="photos.tar  ", tag=None))
    assert doc.suggested_name == "photos.tar"


@pytest.mark.parametrize(
    "name, suggested",
    [
        ("holiday-photos.tar", "holiday-photos.tar"),
        ("my file (2).zip", "my file (2).zip"),
        ("../../.bashrc", "bashrc"),
        ("/home/u/.profile", "profile"),
        ("C:\\Users\\x\\evil.exe", "evil.exe"),
        ("dir/", "recovered.bin"),
        ('a<b>c:d"e|f?g*h.txt', "abcdefgh.txt"),
        ("tab\there\x7f.txt", "tabhere.txt"),
        ("  .hidden. ", "hidden"),
        (".", "recovered.bin"),
        ("..", "recovered.bin"),
        ("...", "recovered.bin"),
        ("CON", "recovered.bin"),
        ("con.txt", "recovered.bin"),
        ("Lpt9.tar.gz", "recovered.bin"),
        ("com1", "recovered.bin"),
        ("nul", "recovered.bin"),
        ("aux.", "recovered.bin"),
        ("COM10", "COM10"),
        ("console.txt", "console.txt"),
        ("con .txt", "recovered.bin"),
        ("LPT1 .tar.gz", "recovered.bin"),
        ("nul  ", "recovered.bin"),
    ],
)
def test_suggested_name_is_a_plain_file_name(name, suggested):
    doc, _ = build(info(1, name=name))
    assert doc.suggested_name == suggested


def test_by_hand():
    doc, (a,) = build(info(1, tag=None))
    assert not doc.by_hand
    doc.start_by_hand(A, 2)
    assert doc.by_hand
    doc.switch_to(a)
    assert not doc.by_hand


def test_can_save_once_any_page_is_decoded():
    tag = make_tag(bytes(2500))
    doc, (p1, p2) = build(info(1, tag=tag), info(2, tag=tag))
    assert not doc.can_save
    doc.set_outcome(p2, page_out(b"x" * PAGE, lost=900))
    assert doc.can_save
    assert doc.page_bytes == PAGE
    # Cut to the tag's size, with zeros where no page was decoded.
    assert doc.assemble() == bytes(PAGE) + b"x" * PAGE + bytes(500)


# --- Values and imports -------------------------------------------------------


def test_page_outcome_counts():
    o = PageOutcome(b"abcde", (90, 5, 3, 2), 1)
    assert (o.repaired, o.bytes, o.lost) == (10, 5, 1)


def test_views_are_frozen():
    doc, (a,) = build(info(1))
    for view in (doc.scan(a), doc.current, doc.slots()[0], info(1), out()):
        with pytest.raises(AttributeError):
            view.number = 1  # type: ignore[misc]
    assert isinstance(doc.current, GroupView)


@pytest.mark.parametrize("module", ["optar_gui.document", "optar_gui.text"])
def test_document_imports_without_qt_or_numpy(module):
    code = (
        f"import sys, {module}\n"
        "bad = [m for m in ('PySide6', 'numpy', 'PIL') if m in sys.modules]\n"
        "print(','.join(bad))\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


# --- Cost -----------------------------------------------------------------------


def _big(n, tag):
    doc = Document()
    for page in range(1, n + 1):
        scan_id = doc.add_scan(f"/scans/{page}.png")
        doc.set_identified(scan_id, info(page, total=n, tag=tag))
        doc.set_outcome(scan_id, page_out(b"x" * PAGE))
    doc.pages()
    doc.summary()
    return doc


@pytest.mark.slow
@pytest.mark.parametrize("n, limit", [(2000, 10.0), (MAX_TOTAL_PAGES, 120.0)])
def test_building_a_large_printout_is_fast(n, limit):
    start = time.perf_counter()
    _big(n, Tag(n * PAGE - 5, "aaaaaaaa"))
    assert time.perf_counter() - start < limit


@pytest.mark.slow
@pytest.mark.parametrize("tag", [TAG, None])
def test_one_event_on_a_large_printout_is_fast(tag):
    doc = _big(2000, tag)
    extra = doc.add_scan("/scans/extra.png")
    doc.slots()
    start = time.perf_counter()
    for _ in range(20):
        doc.set_identified(extra, info(1, total=2000, tag=tag))
        doc.slots()
    assert (time.perf_counter() - start) / 20 < 0.005


# --- Checking the fingerprint off the interface thread ---------------------------


def test_verdict_job_is_none_without_a_complete_tagged_document():
    data = bytes(range(256)) * 10
    assert Document().verdict_job() is None
    doc, _ = decoded(None, split(data))  # untagged: nothing to hash
    assert doc.verdict_job() is None
    doc, _ = decoded(make_tag(data), [split(data)[0], None, split(data)[2]])  # incomplete
    assert doc.verdict_job() is None


def test_summary_without_verifying_reports_checking_and_hashes_nothing():
    data = bytes(range(256)) * 10
    doc, _ = decoded(make_tag(data), split(data))
    passes = count_passes(doc)
    s = doc.summary(verify=False)
    assert s == Summary(DocState.CHECKING, 3, 0, 0, 0, 0, 2560)
    assert passes == []


def test_verdict_job_hashes_a_snapshot_and_its_verdict_is_cached():
    data = bytes(range(256)) * 10
    doc, (p1, p2, p3) = decoded(make_tag(data), split(data))
    job = doc.verdict_job()
    assert job is not None and job.size == 2560
    # A change after the job was made does not affect what it hashes.
    doc.set_outcome(p2, page_out(b"\xff" * PAGE))
    verdict = job()
    assert verdict.matches
    doc.accept_verdict(verdict)  # stale: kept only for the bytes it was made from
    assert doc.summary(verify=False).state == DocState.CHECKING
    doc.accept_verdict(doc.verdict_job()())
    assert doc.verdict_job() is None
    passes = count_passes(doc)
    assert doc.summary(verify=False).state == DocState.MISMATCH
    assert doc.summary().state == DocState.MISMATCH
    assert passes == []  # summary() used the accepted verdict


def test_verdict_job_stops_when_cancelled():
    data = bytes(range(256)) * 10
    doc, _ = decoded(make_tag(data), split(data))
    job = doc.verdict_job()
    assert job(lambda: True) is None
    doc.accept_verdict(None)  # ignored
    assert doc.summary(verify=False).state == DocState.CHECKING


# --- Which files are scans --------------------------------------------------------


def test_expand_paths_takes_the_images_directly_inside_a_folder(tmp_path):
    folder = tmp_path / "scans"
    folder.mkdir()
    for name in ["b.PNG", "a.tif", "c.jpeg", "notes.txt", "x.gif", "d.Pgm", "e.bmp"]:
        (folder / name).write_bytes(b"")
    (folder / "sub").mkdir()
    (folder / "sub" / "deep.png").write_bytes(b"")
    (folder / "dir.png").mkdir()  # a folder with an image's name is not a file
    loose = tmp_path / "loose.txt"
    loose.write_bytes(b"")
    got = expand_paths([str(loose), str(folder)])
    assert got == [str(loose)] + [
        str(folder / n) for n in ["a.tif", "b.PNG", "c.jpeg", "d.Pgm", "e.bmp"]
    ]


def test_scan_extensions():
    assert SCAN_EXTENSIONS == (".png", ".tif", ".tiff", ".bmp", ".pgm", ".ppm", ".jpg", ".jpeg")


def test_expand_paths_keeps_a_missing_path(tmp_path):
    assert expand_paths([str(tmp_path / "gone.png")]) == [str(tmp_path / "gone.png")]


# --- What the window offers for a selected row -------------------------------------


def test_actions_for_a_page():
    doc, (a, b) = build(info(1), info(1))
    doc.set_outcome(a, out())
    doc.set_outcome(b, out(lost=2))
    assert doc.actions(Row.PAGE, 1) == Actions(remove=a, replace=1)
    assert doc.actions(Row.PAGE, 2) == Actions(replace=2)  # missing: nothing to remove
    assert doc.actions(Row.PAGE, 4) == NO_ACTIONS  # no such page
    assert doc.actions(Row.SPARE, b) == Actions(remove=b, use_spare=b)
    assert doc.actions(Row.SPARE, a) == NO_ACTIONS  # in use, not a spare
    doc.use_scan(b)
    assert doc.actions(Row.SPARE, a) == Actions(remove=a, use_spare=a)
    assert doc.actions(Row.SPARE, b) == NO_ACTIONS


def test_actions_for_other_documents():
    doc, (a, one, two, three) = build(
        info(1), info(1, tag=OTHER_TAG), info(1, total=2, name="x", tag=None),
        info(2, total=2, name="x", tag=None)
    )
    single, double = doc.others()
    assert doc.actions(Row.OTHER, single.key) == Actions(switch=single.key, assign=one)
    # A group of several scans is switched to, not assigned to a page as a whole.
    assert doc.actions(Row.OTHER, double.key) == Actions(switch=double.key)
    assert doc.actions(Row.OTHER, a) == NO_ACTIONS  # the current document
    assert doc.actions(Row.OTHER, three) == NO_ACTIONS  # not a group's key


def test_actions_for_unreadable_scans():
    doc, (bad,) = build(None)
    doc.set_unreadable(bad, "label unreadable")
    # No document to assign it to: it must be started by hand first.
    assert doc.actions(Row.UNREADABLE, bad) == Actions(remove=bad)
    assert doc.can_start_by_hand
    doc.start_by_hand(A, 2)
    assert not doc.can_start_by_hand
    assert doc.actions(Row.UNREADABLE, bad) == Actions(remove=bad, assign=bad)
    doc.assign_page(bad, 2)
    assert doc.actions(Row.UNREADABLE, bad) == NO_ACTIONS  # now page 2
    assert doc.actions(Row.PAGE, 2) == Actions(remove=bad, replace=2)
    assert doc.actions(Row.UNREADABLE, 99) == NO_ACTIONS
    assert doc.actions("title", None) == NO_ACTIONS


def test_start_by_hand_is_offered_only_without_a_document_and_with_unreadable_scans():
    doc = Document()
    assert not doc.can_start_by_hand  # nothing to put in it
    waiting = add(doc, 1)
    assert not doc.can_start_by_hand
    doc.set_unreadable(waiting, "no page found")
    assert doc.can_start_by_hand
    good = add(doc, 2)
    doc.set_identified(good, info(1))
    assert not doc.can_start_by_hand


def test_replacement_fit():
    doc, (a, same, other_page, foreign, bad, waiting) = build(
        info(2), info(2), info(1), info(2, tag=OTHER_TAG), info(2), None
    )
    doc.set_unreadable(bad, "decoding failed")
    assert doc.replacement_fit(same, 2) == Fit.PENDING  # identified, not decoded yet
    for scan_id in (a, same, other_page, foreign):
        doc.set_outcome(scan_id, out())
    assert doc.replacement_fit(same, 2) == Fit.THIS_PAGE
    assert doc.replacement_fit(same, 3) == Fit.OTHER_PAGE
    assert doc.replacement_fit(other_page, 2) == Fit.OTHER_PAGE
    assert doc.replacement_fit(foreign, 2) == Fit.OTHER_DOCUMENT
    assert doc.replacement_fit(bad, 2) == Fit.UNREADABLE
    assert doc.replacement_fit(waiting, 2) == Fit.PENDING
    # A scan assigned to the page by hand is in that page.
    doc.assign_page(foreign, 3)
    assert doc.replacement_fit(foreign, 3) == Fit.THIS_PAGE


def test_page_with_shows_a_spare_as_if_it_were_in_use():
    doc, (a, b) = build(info(1), info(1))
    doc.set_outcome(a, out(repaired=3))
    doc.set_outcome(b, out(lost=5))
    spare = doc.page_with(b)
    assert (spare.number, spare.health, spare.scan_id, spare.lost) == (1, Health.DAMAGED, b, 5)
    assert doc.pages()[0].health == Health.REPAIRED  # unchanged
    with pytest.raises(KeyError):
        doc.page_with(99)
    foreign = add(doc, "foreign")
    doc.set_identified(foreign, info(1, tag=OTHER_TAG))
    with pytest.raises(ValueError):
        doc.page_with(foreign)  # not a page of the current document


def test_suggested_page():
    doc, (a, foreign, bad) = build(info(1), info(3, tag=OTHER_TAG), None)
    doc.set_unreadable(bad, "label unreadable")
    assert doc.suggested_page(foreign) == 3  # what its own label says
    assert doc.suggested_page(bad) == 2  # the first page with no scan
    for scan_id in (foreign, bad):
        doc.assign_page(scan_id, doc.suggested_page(scan_id))
    assert doc.suggested_page(a) == 1  # every page has a scan, own label
    alone, (lost,) = build(None)
    alone.set_unreadable(lost, "label unreadable")
    with pytest.raises(ValueError):
        alone.suggested_page(lost)  # no document to suggest a page of


def test_scan_id_of_a_path(tmp_path):
    doc = Document()
    scan = tmp_path / "s.png"
    scan.write_bytes(b"")
    scan_id = doc.add_scan(str(scan))
    assert doc.scan_id_of(str(tmp_path / "." / "s.png")) == scan_id
    assert doc.scan_id_of(str(tmp_path / "t.png")) is None


def test_assigned_scan_that_fails_to_decode_after_working_is_unreadable():
    doc, (a, bad) = build(info(1), None)
    doc.set_working(bad)
    doc.set_unreadable(bad, "label unreadable")
    doc.set_working(bad, False)
    doc.assign_page(bad, 2)
    doc.set_working(bad)  # decoding it without a label
    assert doc.scan(bad).state == ScanState.WORKING
    doc.set_unreadable(bad, "could not be decoded in any orientation")
    assert doc.scan(bad).state == ScanState.WORKING  # its work has not reported yet
    doc.set_working(bad, False)
    assert doc.scan(bad).state == ScanState.UNREADABLE
    assert doc.pages()[1].health == Health.UNREADABLE


# --- Data decoded in another format ------------------------------------------------


def test_needs_decoding_when_no_outcome_or_decoded_in_another_format():
    doc, (a, letter, bad) = build(info(1), info(1, total=1, fmt=LETTER, name="l"), None)
    doc.set_outcome(a, out(data=b"aaaa"))
    doc.set_outcome(letter, out(data=b"letter"))
    doc.set_unreadable(bad, "label unreadable")
    assert not doc.needs_decoding(a)
    assert doc.needs_decoding(letter)  # identified, so decoded, as Letter
    assert doc.needs_decoding(bad)  # no outcome
    doc.set_outcome(bad, out(data=b"bbbb"), format=A)  # decoded without its label as A4
    assert not doc.needs_decoding(bad)
    doc.set_outcome(bad, out(data=b"bbbb"), format=LETTER)
    assert not doc.needs_decoding(bad)  # the A4 decode is kept beside the Letter one
    with pytest.raises(ValueError):
        build(None)[0].needs_decoding(1)  # no document


def test_data_decoded_in_another_format_is_never_placed_on_a_page():
    doc, (a, letter) = build(info(1), info(1, total=1, fmt=LETTER, name="l"))
    doc.set_outcome(a, out(data=b"aaaa"))
    doc.set_outcome(letter, out(data=b"llll"))  # the same length, the wrong layout
    doc.assign_page(letter, 2)
    page = doc.pages()[1]
    assert (page.health, page.reason, page.histogram) == (Health.UNREADABLE, FORMAT_MISMATCH, None)
    assert doc.assemble()[4:8] == bytes(4)  # zeros, not the Letter data
    doc.set_working(letter)  # decoding it again in this document's format
    assert doc.pages()[1].health == Health.WORKING
    doc.set_working(letter, False)
    doc.set_outcome(letter, out(data=b"LLLL"), format=A)
    assert doc.pages()[1].health == Health.GOOD
    assert doc.assemble()[4:8] == b"LLLL"


def test_by_hand_document_takes_page_size_only_from_its_own_format():
    doc, (a4,) = build(info(1, total=1))
    doc.set_outcome(a4, out(data=b"a4a4a4"))
    doc.start_by_hand(LETTER, 2)
    doc.assign_page(a4, 1)
    assert doc.page_bytes is None
    assert doc.pages()[0].reason == FORMAT_MISMATCH
    assert not doc.can_save


def test_paper_for_size():
    from optar.format import PAPERS

    for name, paper in PAPERS.items():
        w, h = int(paper.width_pt * 3), int(paper.height_pt * 3)
        assert paper_for_size((w, h)) == name
        assert paper_for_size((h + 50, w + 40)) == name  # turned, with margins
    assert paper_for_size((0, 0)) is None


# --- Replacing ---------------------------------------------------------------------


def test_a_replacement_without_usable_data_does_not_replace_usable_data():
    doc, (a, b) = build(info(1, tag=None, name="x"), info(1, tag=OTHER_TAG))
    doc.set_outcome(a, out())
    doc.start_by_hand(A, 3)  # takes in the untagged scan of page 1
    assert doc.slots()[0].scan_id == a
    doc.assign_page(b, 1)
    doc.set_unreadable(b, "decoding failed")
    assert doc.replacement_fit(b, 1) == Fit.UNUSABLE
    # A page with no usable data may take it.
    doc.assign_page(b, 2)
    assert doc.replacement_fit(b, 2) == Fit.THIS_PAGE


# --- One outcome per page format ---------------------------------------------------


def _letter_by_mistake(decode_succeeds):
    """An A4 printout and a Letter one, both verified; page 1 of the Letter printout
    is assigned by mistake to page 2 of the A4 document and decoded there as A4."""
    a_data, l_data = b"a" * 4 + b"b" * 4, b"L" * 5 + b"M" * 5
    a_tag, l_tag = make_tag(a_data), make_tag(l_data)
    doc = Document()
    a1, a2, l1, l2 = (add(doc, n) for n in ("a1", "a2", "l1", "l2"))
    doc.set_identified(a1, info(1, total=2, tag=a_tag))
    doc.set_outcome(a1, out(data=a_data[:4]))
    doc.set_identified(a2, info(2, total=2, tag=a_tag))
    doc.set_outcome(a2, out(data=a_data[4:]))
    doc.set_identified(l1, info(1, total=2, tag=l_tag, fmt=LETTER, name="let"))
    doc.set_identified(l2, info(2, total=2, tag=l_tag, fmt=LETTER, name="let"))
    doc.set_outcome(l2, out(data=l_data[5:]))
    doc.set_outcome(l1, out(data=l_data[:5]))
    letter_key = doc.others()[0].key
    assert doc.summary().state == DocState.VERIFIED
    doc.assign_page(l1, 2)
    assert doc.needs_decoding(l1)
    doc.set_decoding(l1, A, True)
    if decode_succeeds:
        doc.set_outcome(l1, out(data=b"zzzz", lost=9), format=A)
    else:
        doc.set_unreadable(l1, "could not be decoded in any orientation", format=A)
    doc.set_decoding(l1, A, False)
    return doc, (a1, a2, l1, l2), letter_key, l_data


@pytest.mark.parametrize("decode_succeeds", [False, True])
def test_a_decode_in_another_format_leaves_the_scans_own_page_intact(decode_succeeds):
    doc, (a1, a2, l1, l2), _, l_data = _letter_by_mistake(decode_succeeds)
    # In the A4 document: the A4 page keeps its place, never demoted by the mistake.
    assert doc.slots()[1] == PageSlot(2, a2, (l1,))
    assert doc.summary().state == DocState.VERIFIED
    assert doc.unreadable() == ()  # the Letter scan is still identified
    doc.switch_to(doc.others()[0].key)  # the Letter printout, as listed now
    assert (doc.current.format, doc.current.scan_ids) == (LETTER, (l1, l2))
    assert [p.health for p in doc.pages()] == [Health.GOOD, Health.GOOD]
    assert doc.assemble() == l_data
    assert doc.summary().state == DocState.VERIFIED
    assert not doc.needs_decoding(l1)  # no decoding again in its own document
    assert doc.scan(l1).outcome == out(data=l_data[:5])


def test_a_decode_requested_is_pending_from_the_moment_it_is_asked_for():
    doc, (bad,) = build(None)
    doc.set_unreadable(bad, "label unreadable")
    doc.start_by_hand(A, 1)
    doc.assign_page(bad, 1)
    doc.set_decoding(bad, A, True)  # queued: no worker has started it
    assert doc.scan(bad).state == ScanState.WORKING
    assert doc.pages()[0].health == Health.WORKING
    assert doc.summary().state == DocState.WORKING
    assert doc.replacement_fit(bad, 1) == Fit.PENDING
    doc.set_outcome(bad, out(data=b"dddd"), format=A)
    assert doc.pages()[0].health == Health.WORKING  # until the decode has reported
    doc.set_decoding(bad, A, False)
    assert doc.pages()[0].health == Health.GOOD
    assert doc.replacement_fit(bad, 1) == Fit.THIS_PAGE


def test_a_scan_ranks_only_by_its_outcome_in_the_documents_format():
    # Page 1 of a document by hand uses a damaged scan; a Letter scan with a clean
    # Letter page is assigned there: it has no A4 page, so it does not displace it.
    doc, (dmg, letter) = build(None, info(1, total=1, fmt=LETTER, name="l"))
    doc.set_unreadable(dmg, "label unreadable")
    doc.set_outcome(letter, out(data=b"LLLL"))
    doc.start_by_hand(A, 2)
    doc.assign_page(dmg, 1)
    doc.set_outcome(dmg, out(data=b"dddd", lost=5), format=A)
    doc.assign_page(letter, 1)
    assert doc.slots()[0] == PageSlot(1, dmg, (letter,))
    doc.set_decoding(letter, A, True)
    assert doc.slots()[0] == PageSlot(1, dmg, (letter,))
    assert doc.pages()[0].health == Health.DAMAGED
    doc.set_unreadable(letter, "could not be decoded in any orientation", format=A)
    doc.set_decoding(letter, A, False)
    assert doc.slots()[0] == PageSlot(1, dmg, (letter,))  # still its usable scan
    assert doc.replacement_fit(letter, 1) == Fit.UNUSABLE
    assert doc.scan(letter).reason == "could not be decoded in any orientation"
    # Unassigned again (a new document by hand drops the assignment), the Letter scan
    # is its own Letter page, never unreadable.
    doc.start_by_hand(A, 2)
    doc.switch_to(doc.others()[0].key)
    assert doc.pages()[0].health == Health.GOOD


def test_page_in_current():
    doc, (a, bad) = build(info(1), None)
    doc.set_unreadable(bad, "label unreadable")
    assert (doc.page_in_current(a), doc.page_in_current(bad)) == (1, None)
    doc.assign_page(bad, 3)
    assert doc.page_in_current(bad) == 3


# --- Version-1 documents ----------------------------------------------------------

XL = get_layout("a4", "xlarge").fmt  # small pages keep these tests fast
XL_FORMAT = XL.to_string()
XL_BYTES = XL.net_bits // 8


def v1_pages(pages=None, parity=32, name="v1.bin", size=None, seed=0):
    """(file, payload by page) of a file wrapped with ``wrap``; with ``pages`` and no
    ``size``, the largest file that takes exactly that many pages."""
    if size is None:
        size = plan_for(pages, XL, parity).data_bytes - 1 - len(name.encode())
    data = random.Random(f"v1-{seed}-{size}").randbytes(size)
    stream = wrap(data, name, XL, parity)
    total = plan(len(data), name, XL, parity).total
    assert pages is None or total == pages
    bits = np.unpackbits(np.frombuffer(stream, dtype=np.uint8))
    payloads = {}
    for n in range(1, total + 1):
        start = (n - 1) * XL.net_bits
        raw = np.packbits(bits[start : start + XL_BYTES * 8]).tobytes()
        payloads[n] = PagePayload(raw, np.zeros(XL_BYTES, dtype=bool))
    return data, payloads


def erased(payload, count, start=1000):
    """The payload with ``count`` bytes from ``start`` marked erased (data kept)."""
    mask = np.zeros(len(payload.data), dtype=bool)
    mask[start : start + count] = True
    return PagePayload(payload.data, mask)


def v1_info(payload, label_name="v1.bin"):
    header = read_header(payload.data)
    assert header is not None
    return ScanInfo(XL_FORMAT, header.total, header.page, label_name, None, header=header)


def add_v1(doc, n, payload, corrected=0, label_name="v1.bin"):
    """Adds, identifies and decodes a version-1 scan; returns its id."""
    scan_id = add(doc, n)
    doc.set_identified(scan_id, v1_info(payload, label_name))
    doc.set_payload(scan_id, payload)
    lost = int(np.count_nonzero(payload.erased))
    doc.set_outcome(scan_id, PageOutcome(payload.data, (1000, corrected, 0, 0), lost))
    return scan_id


def v1_document(payloads, skip=(), label_name="v1.bin"):
    doc = Document()
    ids = {
        n: add_v1(doc, f"p{n}", p, label_name=label_name)
        for n, p in payloads.items()
        if n not in skip
    }
    return doc, ids


def repaired(doc):
    """Runs the offered repair job and accepts its result; returns the result."""
    job = doc.repair_job()
    assert job is not None
    repair = job()
    doc.accept_repair(repair)
    return repair.result


def test_version1_pages_in_any_order_make_a_document_that_verifies():
    data, payloads = v1_pages(3)
    doc = Document()
    p3 = add_v1(doc, "c", payloads[3])
    p1 = add_v1(doc, "a", payloads[1])
    assert doc.summary().state == DocState.INCOMPLETE
    assert doc.summary().missing_pages == (2,)
    p2 = add_v1(doc, "b", payloads[2])
    assert [s.scan_id for s in doc.slots()] == [p1, p2, p3]
    assert doc.current.total == 3 and doc.current.format == XL_FORMAT
    assert doc.current.tag is None and doc.current.header is not None
    s = doc.summary()
    assert s.state == DocState.CHECKING  # complete, repair not run yet
    assert (s.protection, s.missing_pages, s.repair, s.size) == (32, (), None, len(data))
    assert not doc.can_save and doc.save_bytes() is None
    assert doc.verdict_job() is None
    result = repaired(doc)
    assert result.verified
    s = doc.summary()
    assert s.state == DocState.VERIFIED and s.repair is result
    assert counts(s) == (3, 0, 0, 0, 0)
    assert doc.can_save and doc.save_bytes() == data
    assert doc.salvage_bytes() is None
    assert doc.assemble() == data
    assert doc.repair_job() is None  # nothing changed since


def test_version1_page_count_and_number_come_from_the_header():
    data, payloads = v1_pages(3)
    doc = Document()
    scan_id = add(doc, "x")
    label = v1_info(payloads[2])
    doc.set_identified(scan_id, ScanInfo(XL_FORMAT, 0, 0, "", None, header=label.header))
    assert doc.scan(scan_id).info.page == 2 and doc.scan(scan_id).info.total == 3
    assert doc.slots()[1].scan_id == scan_id


def test_version1_scan_is_working_until_it_has_its_payload_and_its_outcome():
    data, payloads = v1_pages(1)
    doc = Document()
    a = add(doc, "a")
    doc.set_identified(a, v1_info(payloads[1]))
    doc.set_outcome(a, PageOutcome(payloads[1].data, (1000, 0, 0, 0), 0))
    assert doc.scan(a).state == ScanState.WORKING
    assert doc.summary().state == DocState.WORKING and doc.repair_job() is None
    doc.set_payload(a, payloads[1])
    assert doc.scan(a).state == ScanState.DONE
    b = add(doc, "b")
    doc.set_identified(b, v1_info(payloads[1]))
    doc.set_payload(b, payloads[1])
    assert doc.scan(b).state == ScanState.WORKING


def test_version1_lost_page_within_the_promise_is_recoverable():
    data, payloads = v1_pages(12)
    doc, _ = v1_document(payloads, skip=(7,))
    s = doc.summary()
    assert s.state == DocState.RECOVERABLE
    assert s.missing_pages == (7,) and s.missing == 1 and s.repair is None
    assert not doc.can_save
    result = repaired(doc)
    assert result.verified and result.missing == (7,)
    s = doc.summary()
    assert s.state == DocState.RECOVERABLE and s.repair.verified
    assert doc.can_save and doc.save_bytes() == data


def test_version1_recoverable_document_whose_repair_fails_is_incomplete():
    data, payloads = v1_pages(12)
    payloads[8] = erased(payloads[8], XL_BYTES, start=0)  # read, but every byte erased
    doc, _ = v1_document(payloads, skip=(7,))
    assert doc.summary().state == DocState.RECOVERABLE
    result = repaired(doc)
    assert not result.verified and result.data is None
    s = doc.summary()
    assert s.state == DocState.INCOMPLETE and s.missing_pages == (7,)
    assert not doc.can_save and doc.save_bytes() is None
    assert doc.salvage_bytes() == result.best_effort


def test_version1_too_many_pages_missing_is_incomplete():
    data, payloads = v1_pages(3)
    doc, _ = v1_document(payloads, skip=(2,))
    assert doc.summary().state == DocState.INCOMPLETE
    assert doc.repair_job() is not None  # a page is present: repairing is offered
    result = repaired(doc)
    assert not result.verified
    s = doc.summary()
    assert s.state == DocState.INCOMPLETE
    assert s.repair is result and s.repair.page_damage
    assert not doc.can_save and doc.save_bytes() is None
    assert doc.salvage_bytes() == result.best_effort and len(result.best_effort) == len(data)


def test_version1_failed_repair_of_a_complete_document_reports_damage():
    data, payloads = v1_pages(2, parity=0)
    payloads[1] = erased(payloads[1], 40)
    doc, _ = v1_document(payloads)
    assert doc.summary().state == DocState.CHECKING
    repaired(doc)
    s = doc.summary()
    assert s.state == DocState.INCOMPLETE and s.protection == 0
    assert s.repair.page_damage.get(1, 0) > 0 and not s.repair.verified
    assert not doc.can_save


def test_version1_unverified_file_does_not_match():
    from dataclasses import replace

    data, payloads = v1_pages(2)
    doc, _ = v1_document(payloads)
    repair = doc.repair_job()()
    # Stands in for a codeword miscorrected without being flagged.
    wrong = replace(repair.result, data=b"wrong", best_effort=b"wrong", verified=False)
    doc.accept_repair(replace(repair, result=wrong))
    assert doc.summary().state == DocState.MISMATCH
    assert doc.can_save and doc.save_bytes() == b"wrong"  # after the usual warning


def test_version1_documents_of_two_protections_are_separate():
    data, strong = v1_pages(parity=64, size=30000)
    same, standard = v1_pages(parity=32, size=30000)
    assert same == data
    doc = Document()
    s_ids = [add_v1(doc, f"s{n}", p) for n, p in standard.items()]
    h_ids = [add_v1(doc, f"h{n}", p) for n, p in strong.items()]
    assert doc.current.scan_ids == tuple(s_ids)
    assert [s.scan_id for s in doc.slots()] == s_ids
    assert [g.scan_ids for g in doc.others()] == [tuple(h_ids)]
    assert doc.save_bytes() is None and repaired(doc).verified
    assert doc.save_bytes() == data
    doc.switch_to(doc.others()[0].key)
    assert [s.scan_id for s in doc.slots()] == h_ids
    assert doc.summary().protection == 64 and doc.summary().repair is None
    assert repaired(doc).verified and doc.save_bytes() == data


def test_version1_documents_of_two_dot_sizes_are_separate():
    data, payloads = v1_pages(1)
    doc = Document()
    a = add_v1(doc, "a", payloads[1])
    b = add(doc, "b")
    i = v1_info(payloads[1])
    doc.set_identified(b, ScanInfo("0-23-29-24-3-1-2-24", 1, 1, "v1.bin", None, header=i.header))
    assert doc.current.scan_ids == (a,)
    assert [g.scan_ids for g in doc.others()] == [(b,)]


def test_tagged_and_version1_scans_of_one_file_are_separate():
    data, payloads = v1_pages(1)
    doc = Document()
    tagged = add(doc, "t")
    doc.set_identified(tagged, ScanInfo(XL_FORMAT, 1, 1, "v1.bin", make_tag(data)))
    untagged = add(doc, "u")
    doc.set_identified(untagged, ScanInfo(XL_FORMAT, 1, 1, "v1.bin", None))
    v1 = add_v1(doc, "v", payloads[1])
    assert doc.current.scan_ids == (tagged,)
    assert [g.scan_ids for g in doc.others()] == [(untagged,), (v1,)]


def test_version1_scan_with_fewer_erased_bytes_is_used_and_replacing_drops_the_result():
    data, payloads = v1_pages(3)
    doc = Document()
    worse = add_v1(doc, "worse", erased(payloads[1], 50), corrected=0)
    for n in (2, 3):
        add_v1(doc, f"p{n}", payloads[n])
    assert repaired(doc).verified and doc.summary().state == DocState.VERIFIED
    # Fewer erased bytes beats fewer corrected bits.
    better = add_v1(doc, "better", payloads[1], corrected=30)
    assert doc.slots()[0] == PageSlot(1, better, (worse,))
    assert doc.summary().repair is None and doc.summary().state == DocState.CHECKING
    assert not doc.can_save
    assert repaired(doc).verified
    # On equal erasures, fewer corrected bits wins.
    best = add_v1(doc, "best", payloads[1], corrected=3)
    assert doc.slots()[0] == PageSlot(1, best, (better, worse))
    assert doc.repair_job() is not None
    # Choosing a spare by hand works as for tagged documents.
    doc.use_scan(worse)
    assert doc.slots()[0].scan_id == worse


def test_version1_result_is_dropped_when_a_scan_in_use_is_removed():
    data, payloads = v1_pages(3)
    doc, ids = v1_document(payloads)
    spare = add_v1(doc, "spare", erased(payloads[2], 10))
    repaired(doc)
    doc.remove_scan(spare)  # not in use: the result still stands
    assert doc.summary().state == DocState.VERIFIED
    doc.remove_scan(ids[3])
    s = doc.summary()
    assert s.repair is None and s.state == DocState.INCOMPLETE
    assert doc.save_bytes() is None and doc.salvage_bytes() is None


@pytest.mark.parametrize("read_between", [False, True])
def test_version1_result_counts_again_when_its_pages_are_back_whether_or_not_read(
    read_between,
):
    data, payloads = v1_pages(2)
    doc, ids = v1_document({1: erased(payloads[1], 5), 2: payloads[2]})
    result = repaired(doc)
    better = add_v1(doc, "better", payloads[1])  # now page 1's scan in use
    if read_between:
        assert doc.summary().repair is None and doc.repair_job() is not None
    doc.remove_scan(better)  # the payloads in use are what they were
    assert doc.summary().repair is result and doc.repair_job() is None
    assert doc.summary().state == DocState.VERIFIED


def test_version1_new_payload_of_the_scan_in_use_drops_the_result():
    data, payloads = v1_pages(2)
    doc, ids = v1_document(payloads)
    repaired(doc)
    doc.set_payload(ids[1], payloads[1])  # same bytes, but a new reading
    assert doc.summary().repair is None and doc.summary().state == DocState.CHECKING
    assert doc.repair_job() is not None


def test_version1_result_kept_when_switching_away_and_back():
    data, payloads = v1_pages(2)
    doc, ids = v1_document(payloads)
    result = repaired(doc)
    other = add(doc, "other")
    doc.set_identified(other, info(1, total=1, name="other.tar"))
    doc.switch_to(other)
    assert doc.summary().repair is None and doc.save_bytes() is None
    doc.switch_to(ids[1])
    assert doc.summary().repair is result and doc.repair_job() is None
    assert doc.save_bytes() == data


def test_version1_failed_repair_job_is_not_offered_again_until_the_pages_change():
    data, payloads = v1_pages(2)
    doc, ids = v1_document(payloads)
    job = doc.repair_job()
    doc.fail_repair(("not", "these", "pages"), "stale")  # ignored
    assert doc.summary().repair_error == "" and doc.repair_job() is not None
    doc.fail_repair(job.key, "header describes an impossible document")
    s = doc.summary()
    assert s.state == DocState.INCOMPLETE
    assert s.repair_error == "header describes an impossible document"
    assert s.repair is None and doc.repair_job() is None and not doc.can_save
    assert doc.summary(verify=False).state == DocState.INCOMPLETE
    again = add_v1(doc, "again", payloads[2], corrected=0)  # a spare: same pages
    assert doc.repair_job() is None
    doc.use_scan(again)  # the pages in use change: the failure counts no longer
    assert doc.summary().repair_error == "" and doc.summary().state == DocState.CHECKING
    assert doc.repair_job() is not None


def test_holding_a_repair_result_keeps_background_results_cheap():
    # Measured on the development machine: about 0.03 s either way; 10 s before
    # the key was compared only when read.
    def run(hold):
        data, payloads = v1_pages(1)
        doc, ids = v1_document(payloads)
        if hold:
            repaired(doc)
        start = time.perf_counter()
        for n in range(3000):
            scan_id = doc.add_scan(f"/scans/other-{n}.png")
            doc.set_identified(scan_id, info(1, total=1, name=f"other-{n}", tag=None))
        elapsed = time.perf_counter() - start
        assert (doc.summary().repair is not None) == hold
        return elapsed

    without, held = run(False), run(True)
    assert held < 2.0 and held < 5 * without + 0.5


def test_version1_stale_or_cancelled_repair_is_not_accepted():
    data, payloads = v1_pages(3)
    doc, ids = v1_document(payloads)
    job = doc.repair_job()
    assert job(lambda: True) is None
    doc.accept_repair(None)  # ignored
    stale = job()
    add_v1(doc, "later", payloads[2])  # same quality, added later: a spare
    assert doc.repair_job().key == stale.key
    doc.remove_scan(ids[2])  # the later scan is now page 2: the scans in use changed
    doc.accept_repair(stale)
    assert doc.summary().repair is None and doc.repair_job() is not None


def test_version1_documents_take_no_pages_by_hand():
    data, payloads = v1_pages(2)
    doc, ids = v1_document(payloads)
    bad = add(doc, "bad")
    doc.set_unreadable(bad, "label unreadable")
    assert doc.actions(Row.UNREADABLE, bad) == Actions(remove=bad)
    with pytest.raises(ValueError):
        doc.assign_page(bad, 1)
    # Nor is a version-1 page put into another document by hand.
    doc2, (t,) = build(info(1))
    v1 = add_v1(doc2, "v", payloads[1])
    key = doc2.others()[0].key
    assert doc2.actions(Row.OTHER, key) == Actions(switch=key)
    with pytest.raises(ValueError):
        doc2.assign_page(v1, 1)
    doc2.set_unreadable(v1, "could not be decoded")
    assert doc2.actions(Row.UNREADABLE, v1) == Actions(remove=v1)
    with pytest.raises(ValueError):
        doc2.assign_page(v1, 1)
    # Its scans still replace a page as tagged scans do.
    again = add_v1(doc, "again", payloads[2])
    assert doc.replacement_fit(again, 2) == Fit.THIS_PAGE
    assert doc.replacement_fit(again, 1) == Fit.OTHER_PAGE


def test_version1_suggested_name_comes_from_the_label_then_the_repaired_name():
    data, payloads = v1_pages(2, name="report.txt")
    doc, _ = v1_document(payloads, label_name="")
    assert doc.suggested_name == "recovered.bin"
    repaired(doc)
    assert doc.suggested_name == "report.txt"
    data, payloads = v1_pages(1, name="../x/evil.txt")
    doc, _ = v1_document(payloads, label_name="label.txt")
    assert doc.suggested_name == "label.txt"
    repaired(doc)
    assert doc.suggested_name == "evil.txt"


def test_version1_choice_follows_its_identity():
    data, payloads = v1_pages(2)
    doc, (t,) = build(info(1))
    first = add_v1(doc, "v1", payloads[1])
    doc.switch_to(doc.others()[0].key)
    assert doc.current.scan_ids == (first,)
    doc.set_unreadable(first, "could not be decoded")  # the choice keeps its identity
    second = add_v1(doc, "v2", payloads[2])  # another page of the same document
    assert doc.current.scan_ids == (second,)
