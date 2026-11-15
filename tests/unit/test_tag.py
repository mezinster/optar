# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import hashlib

import pytest

from optar.format import PageFormat
from optar.tag import FINGERPRINT_DIGITS, Tag, make_tag, split_label, tagged_label

A4 = PageFormat(65, 93)
LETTER = PageFormat(67, 87)
ZERO = "0" * 8


def test_make_tag_and_text():
    data = b"hello world"
    t = make_tag(data)
    assert FINGERPRINT_DIGITS == 8
    assert t == Tag(11, hashlib.sha256(data).hexdigest()[:8])
    assert t.text == f"[11:{t.fingerprint}]" and t.matches(data)
    assert not t.matches(data + b"\0") and not t.matches(b"hello_world")


def test_tag_is_hashable_and_comparable():
    assert len({Tag(1, ZERO), Tag(1, ZERO), Tag(2, ZERO)}) == 2


@pytest.mark.parametrize("size,fp", [(-1, ZERO), (1, "0" * 7), (1, "0" * 9),
                                     (1, "ABCDEF01"), (1, "0000000g"), (1, "")])
def test_tag_rejects_invalid_fields(size, fp):
    with pytest.raises(ValueError):
        Tag(size, fp)


def test_tagged_label_and_split_round_trip():
    t = Tag(2481152, "3f9a2c1b")
    assert tagged_label(t, "holiday-photos.tar") == "[2481152:3f9a2c1b] holiday-photos.tar"
    assert tagged_label(t, "") == "[2481152:3f9a2c1b]"
    assert split_label("[2481152:3f9a2c1b] holiday photos.tar") == (t, "holiday photos.tar")
    assert split_label("[2481152:3f9a2c1b]") == (t, "")


@pytest.mark.parametrize("name", ["a b c", "x  y", "with [brackets] in", "[1:aaaaaaaa]", " lead"])
def test_label_round_trip_names(name):
    t = Tag(7, "0123abcd")
    assert split_label(tagged_label(t, name)) == (t, name)


def test_split_label_rejects_near_misses():
    for text in ["plain.tar", "[12:3F9A2C1B] x", "[12:3f9a2c1] x", "[12:3f9a2c1bb] x",
                 " [12:3f9a2c1b] x", "[12:3f9a2c1b]x", "[:3f9a2c1b] x", "[12-3f9a2c1b] x", ""]:
        assert split_label(text) == (None, text)


def test_split_label_rejects_leading_zeros_but_accepts_zero():
    assert split_label("[007:3f9a2c1b] x") == (None, "[007:3f9a2c1b] x")
    assert split_label("[00:3f9a2c1b]") == (None, "[00:3f9a2c1b]")
    assert split_label("[0:3f9a2c1b] x") == (Tag(0, "3f9a2c1b"), "x")


def test_split_label_rejects_non_ascii_digits_and_extra_whitespace():
    for text in ["[\u0661:3f9a2c1b] x", "[1:3f9a2c1b]\tx", "[1:3f9a2c1b]\n", "[1:3f9a2c1b]\nx"]:
        assert split_label(text) == (None, text)


def test_split_label_second_tag_stays_in_name():
    assert split_label("[1:aaaaaaaa] [2:bbbbbbbb] x") == (Tag(1, "aaaaaaaa"), "[2:bbbbbbbb] x")


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
