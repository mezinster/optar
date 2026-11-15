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

import pytest

from optar.tag import Tag
from optar_gui.document import (
    Document,
    GroupView,
    PageOutcome,
    PageSlot,
    ScanInfo,
    ScanState,
    ScanView,
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
    # The choice is {b}; while b is not grouped the default rule shows the earliest
    # printout, in both orders.
    assert picture(doc) == {
        "current": (a,),
        "slots": [(1, a, ()), (2, None, ()), (3, None, ())],
        "others": [(c,)],
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


def _run(n, n_ops, events, shuffle, ops, op_rng):
    """Plays the scenario; chooses the operations (into ops) when op_rng is given."""
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
        if op_rng is not None:
            ops.append(_random_operation(op_rng, doc, ids))
        name, *args = ops[batch]
        try:
            getattr(doc, name)(*args)
            results.append(None)
        except (KeyError, ValueError) as error:
            results.append(type(error))
    return (doc.current, doc.slots(), doc.others(), doc.unreadable(), doc.scans(), results)


def test_property_background_order_never_changes_the_result():
    scenarios = 1000
    for seed in range(scenarios):
        rng = random.Random(seed)
        n, n_ops, events = _random_scenario(rng)
        ops: list = []
        expected = _run(n, n_ops, events, lambda _: None, ops, random.Random(seed + 10**6))
        for rep in range(5):
            order = random.Random(seed * 31 + rep)
            got = _run(n, n_ops, events, order.shuffle, ops, None)
            assert got == expected, (seed, rep, ops)


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


def test_document_imports_without_qt_or_numpy():
    code = (
        "import sys, optar_gui.document\n"
        "bad = [m for m in ('PySide6', 'numpy', 'PIL') if m in sys.modules]\n"
        "print(','.join(bad))\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""
