# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import hashlib

import pytest

from optar.encoder import MAX_PAGES
from optar.font import label_text
from optar.format import PageFormat
from optar.label import label_capacity, printed_label
from optar.tag import (
    CHECK_DIGITS,
    FINGERPRINT_DIGITS,
    MAX_SIZE_DIGITS,
    Tag,
    make_tag,
    split_label,
    tagged_label,
)

A4 = PageFormat(65, 93)
LETTER = PageFormat(67, 87)
ZERO = "0" * 8
T = Tag(2481152, "3f9a2c1b")


def check_of(size, fingerprint, page, total):
    """The check as the design states it, computed independently of tag.py."""
    text = f"{size}:{fingerprint}:{page}/{total}".encode("ascii")
    return hashlib.sha256(text).hexdigest()[:2]


def test_make_tag():
    data = b"hello world"
    t = make_tag(data)
    assert FINGERPRINT_DIGITS == 8
    assert t == Tag(11, hashlib.sha256(data).hexdigest()[:8])
    assert t.matches(data)
    assert not t.matches(data + b"\0") and not t.matches(b"hello_world")


def test_tag_has_no_page_independent_text():
    assert not hasattr(T, "text")


def test_tag_is_hashable_and_comparable():
    assert len({Tag(1, ZERO), Tag(1, ZERO), Tag(2, ZERO)}) == 2


@pytest.mark.parametrize("size,fp", [(-1, ZERO), (1, "0" * 7), (1, "0" * 9),
                                     (1, "ABCDEF01"), (1, "0000000g"), (1, ""),
                                     (10 ** 12, ZERO), (True, ZERO), (1.0, ZERO),
                                     ("1", ZERO), (1, None), (1, b"00000000")])
def test_tag_rejects_invalid_fields(size, fp):
    with pytest.raises(ValueError):
        Tag(size, fp)


# ---- the per-page check ------------------------------------------------------


@pytest.mark.parametrize("tag,page,total", [
    (T, 1, 1), (T, 3, 8), (Tag(0, "e3b0c442"), 1, 0), (Tag(10 ** 12 - 1, "ffffffff"), 9999, 9999),
])
def test_check_is_the_stated_sha256(tag, page, total):
    assert CHECK_DIGITS == 2
    check = tag.check(page, total)
    assert check == check_of(tag.size, tag.fingerprint, page, total)
    assert len(check) == CHECK_DIGITS and check == check.lower()


def test_check_varies_with_page_and_document():
    pages = {T.check(p, 50) for p in range(1, 51)}
    assert len(pages) > 20
    documents = {Tag(T.size + i, T.fingerprint).check(1, 1) for i in range(50)}
    assert len(documents) > 20


def test_page_text_and_tagged_label():
    c = check_of(2481152, "3f9a2c1b", 3, 8)
    assert T.page_text(3, 8) == f"[2481152:3f9a2c1b:{c}]"
    label = tagged_label(T, "holiday-photos.tar", 3, 8)
    assert label == f"[2481152:3f9a2c1b:{c}] holiday-photos.tar"
    assert tagged_label(T, "", 3, 8) == f"[2481152:3f9a2c1b:{c}]"


def test_tagged_label_and_split_round_trip():
    c = T.check(1, 2)
    assert split_label(f"[2481152:3f9a2c1b:{c}] holiday photos.tar") == (T, c, "holiday photos.tar")
    assert split_label(f"[2481152:3f9a2c1b:{c}]") == (T, c, "")
    assert split_label(f"[2481152:3f9a2c1b:{c}] ") == (T, c, "")


@pytest.mark.parametrize(
    "name", ["a b c", "x  y", "with [brackets] in", "[1:aaaaaaaa:00]", "[1:aaaaaaaa]",
             " lead", " ", ""])
@pytest.mark.parametrize("page,total", [(1, 1), (7, 12), (1, 0)])
def test_label_round_trip_names(name, page, total):
    t = Tag(7, "0123abcd")
    assert split_label(tagged_label(t, name, page, total)) == (t, t.check(page, total), name)


def test_split_label_reads_the_check_without_judging_it():
    # Whether the check is right for a page is for whoever knows the page.
    assert split_label("[12:3f9a2c1b:00] x") == (Tag(12, "3f9a2c1b"), "00", "x")


@pytest.mark.parametrize("text", [
    "plain.tar", "",
    "[12:3f9a2c1b] x", "[12:3f9a2c1b]",                    # the two-field form
    "[12:3F9A2C1B:7e] x", "[12:3f9a2c1b:7E] x",            # upper-case hex
    "[12:3f9a2c1b:7] x", "[12:3f9a2c1b:7ee] x", "[12:3f9a2c1b:] x",
    "[12:3f9a2c1:7e] x", "[12:3f9a2c1bb:7e] x", "[12:3f9a2c1b:7g] x",
    "[007:3f9a2c1b:7e] x", "[00:3f9a2c1b:7e]",              # leading zeros
    "[1000000000000:3f9a2c1b:7e] x",                        # 13 digits
    "[١:3f9a2c1b:7e] x", "[1٢:3f9a2c1b:7e] x",    # non-ASCII digits
    "[1:3f9a2c1b:7e]\n", "[1:3f9a2c1b:7e]\nx", "[1:3f9a2c1b:7e]\tx",
    "[1:3f9a2c1b:7e]x",                                     # no space before the name
    " [12:3f9a2c1b:7e] x", "[:3f9a2c1b:7e] x", "[12-3f9a2c1b-7e] x", "[12:3f9a2c1b:7e x",
])
def test_split_label_rejects(text):
    assert split_label(text) == (None, "", text)


def test_split_label_accepts_zero_size():
    assert split_label("[0:3f9a2c1b:7e] x") == (Tag(0, "3f9a2c1b"), "7e", "x")


def test_split_label_bounds_size_digits():
    assert MAX_SIZE_DIGITS == 12
    for digits in ("9" * 5000, "1" + "0" * 12):
        text = f"[{digits}:aaaaaaaa:00] x"
        assert split_label(text) == (None, "", text)
    t = Tag(10 ** 12 - 1, "aaaaaaaa")
    assert split_label(tagged_label(t, "x", 2, 3)) == (t, t.check(2, 3), "x")


def test_split_label_second_tag_stays_in_name():
    assert split_label("[1:aaaaaaaa:01] [2:bbbbbbbb:02] x") == (
        Tag(1, "aaaaaaaa"), "01", "[2:bbbbbbbb:02] x")


def test_split_label_never_raises():
    for text in ["[", "[]", "[:", "[1:", "[1:aaaaaaaa:", "\0", "\ud800", "[" * 10000,
                 "[" + "1" * 5000 + ":" + "a" * 5000 + ":" + "b" * 5000 + "]"]:
        assert split_label(text) == (None, "", text)


# ---- the tag on the printed page -----------------------------------------------


@pytest.mark.parametrize("fmt", [A4, LETTER], ids=["a4", "letter"])
def test_tag_is_never_cut_on_the_page(fmt):
    # The largest file the encoder accepts has a 10-digit size.
    largest = MAX_PAGES * (fmt.net_bits // 8)
    assert len(str(largest)) == 10
    tag = Tag(largest, "ffffffff")
    for page in (1, 9, 10, 99, 100, 999, 1000, 9998, MAX_PAGES):
        assert len(tagged_label(tag, "", page, MAX_PAGES) + " ") <= 25
        text = label_text(fmt, page, MAX_PAGES, tagged_label(tag, "n" * 200, page, MAX_PAGES))
        printed = printed_label(fmt, text)
        assert tag.page_text(page, MAX_PAGES) + " n" in printed
    # The worst case, page 9999/9999 with a 10-digit size, leaves this much
    # of the line for the name: 41 characters on A4, 44 on Letter.
    tag_text = tag.page_text(MAX_PAGES, MAX_PAGES)
    head = f"  {fmt.to_string()} {MAX_PAGES}/{MAX_PAGES} {tag_text} "
    left = label_capacity(fmt) - len(head)
    assert left == {A4: 41, LETTER: 44}[fmt]
    name = "".join(chr(ord("a") + i % 26) for i in range(60))
    printed = printed_label(fmt, label_text(fmt, MAX_PAGES, MAX_PAGES,
                                            tagged_label(tag, name, MAX_PAGES, MAX_PAGES)))
    assert printed == head + name[:left]


# ---- fits and matches (unchanged) ----------------------------------------------


def test_fits_page_count():
    b = A4.net_bits // 8                      # 199773
    assert Tag(1, ZERO).fits(1, A4) and Tag(b, ZERO).fits(1, A4)
    assert not Tag(b + 1, ZERO).fits(1, A4) and Tag(b + 1, ZERO).fits(2, A4)
    assert not Tag(b, ZERO).fits(2, A4)
    # an empty file prints one page labelled 1/0
    assert Tag(0, ZERO).fits(0, A4)
    assert not Tag(5, ZERO).fits(0, A4)


def test_fits_empty_file_and_zero_total():
    assert not Tag(0, ZERO).fits(1, A4)
    assert not Tag(0, ZERO).fits(2, A4)
    assert not Tag(1, ZERO).fits(0, A4)


def test_fits_letter_capacity():
    b = LETTER.net_bits // 8
    assert b == 192591
    assert Tag(b, ZERO).fits(1, LETTER) and not Tag(b + 1, ZERO).fits(1, LETTER)
    assert Tag(b + 1, ZERO).fits(2, LETTER) and not Tag(2 * b + 1, ZERO).fits(2, LETTER)
    # the same size is a different page count on A4
    assert Tag(195000, ZERO).fits(1, A4) and not Tag(195000, ZERO).fits(1, LETTER)


def test_fits_negative_total_is_false():
    assert not Tag(0, ZERO).fits(-1, A4)
    assert not Tag(1, ZERO).fits(-1, A4)


def test_matches_requires_right_length():
    d = b"abc"
    assert not Tag(len(d) + 1, make_tag(d).fingerprint).matches(d)
