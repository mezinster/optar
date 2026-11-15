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
import tracemalloc

import pytest

from optar.tag import Tag, make_tag
from optar_gui.document import (
    MAX_TOTAL_PAGES,
    DocState,
    Document,
    GroupView,
    Health,
    PageOutcome,
    PageSlot,
    PageView,
    ScanInfo,
    ScanState,
    ScanView,
    Summary,
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


def test_tagged_group_title_is_the_longest_name():
    doc, (a, b) = build(info(1, name="holiday-photos.t"), info(2, name="holiday-photos.tar"))
    assert doc.current.title == "holiday-photos.tar"


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
    assert doc.pages()[1] == PageView(2, Health.UNREADABLE, bad, (), 0, 0, None)
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


def test_assemble_refuses_pages_of_different_sizes():
    doc, (p1, p2) = build(info(1, total=2, tag=None), info(2, total=2, tag=None))
    doc.set_outcome(p1, page_out(b"a" * PAGE))
    doc.set_outcome(p2, page_out(b"b" * (PAGE + 1)))
    with pytest.raises(ValueError, match="pages have different sizes"):
        doc.assemble()


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
    doc, (p1, p2) = build(info(1, total=2, tag=None), info(2, total=2, tag=None))
    doc.set_outcome(p1, page_out(b"a" * PAGE))
    doc.set_outcome(p2, page_out(b"b" * (PAGE + 1)))
    with pytest.raises(ValueError, match="pages have different sizes"):
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
