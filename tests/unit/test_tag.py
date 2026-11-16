# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import hashlib
import random

import pytest

from optar.encoder import MAX_PAGES
from optar.font import FIRST_CHAR, GLYPH_CELLS, label_text
from optar.format import PageFormat
from optar.label import label_capacity, printed_label
from optar.tag import (
    CHECK_DIGITS,
    FINGERPRINT_DIGITS,
    MAX_SIZE_DIGITS,
    Tag,
    damaged_tag,
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


# ---- a tag damaged in one cell -------------------------------------------------

PRINTABLE = "".join(chr(c) for c in range(FIRST_CHAR, FIRST_CHAR + GLYPH_CELLS))
BIG = Tag(1399271, "9b0d6853")   # eight A4 pages
SMALL = Tag(5, "0b3d8e9f")       # the shortest size, one page
BIG_TEXT = BIG.page_text(8, 8)
SMALL_TEXT = SMALL.page_text(1, 1)
COLON1, COLON2 = BIG_TEXT.index(":"), BIG_TEXT.rindex(":")
LAST = len(BIG_TEXT) - 1


def put(text, at, glyph):
    """`text` with the cell `at` read as `glyph`; trailing blanks are not read."""
    assert text[at] != glyph
    return (text[:at] + glyph + text[at + 1:]).rstrip(" ")


def is_damaged(text, page=8, total=8):
    return damaged_tag(text, page, total, A4)


def test_span_covers_the_longest_tag_and_its_separator():
    longest = Tag(10 ** MAX_SIZE_DIGITS - 1, "f" * FINGERPRINT_DIGITS)
    total = -(-longest.size // (A4.net_bits // 8))
    text = longest.page_text(1, total)
    for at in range(len(text)):
        assert damaged_tag(put(text + " x", at, "~"), 1, total, A4)
    assert damaged_tag(text + "~x", 1, total, A4)   # the separator
    assert damaged_tag(text + "~", 1, total, A4)
    assert not damaged_tag(text + " ~", 1, total, A4)


@pytest.mark.parametrize("text", [
    put(BIG_TEXT + " x", 1, "0"),           # the first size digit read as 0
    put(BIG_TEXT + " x", COLON1, ";"),      # a colon read as ";"
    put(BIG_TEXT + " x", COLON2, "."),      # or "."
    put(BIG_TEXT + " x", LAST, ")"),        # the closing bracket read as ")"
    put(BIG_TEXT + " x", LAST, "1"),        # or as "1"
    put(BIG_TEXT + " x", 0, "("),           # the opening bracket read as "("
    put(BIG_TEXT + " x", 0, " "),           # or lost
    put(BIG_TEXT + " x", COLON2 - 1, "g"),  # a hex digit read as a letter
    put(BIG_TEXT + " x", LAST + 1, "`"),    # a stray mark after the tag
    put(BIG_TEXT + " x", LAST + 1, "."),
    BIG_TEXT + "`",                         # a stray mark after a tag with no name
    put(BIG_TEXT, LAST, " "),               # the closing bracket lost, no name
    put(BIG_TEXT, COLON1, ";"),
    # Missed by counting hexadecimal digits in the first word (review).
    put(BIG_TEXT + " x", COLON1, " "),      # the first colon read as a blank
    put(BIG_TEXT + " x", 2, "|"),           # a size digit read as "|"
    put(BIG_TEXT + " x", 3, " "),           # as a blank
    put(BIG_TEXT + " x", 3, "-"),           # as "-"
    put(BIG_TEXT + " x", 0, "<"),           # the opening bracket read as "<"
])
def test_tag_with_one_cell_misread_is_damaged(text):
    assert split_label(text)[0] is None
    assert is_damaged(text)


@pytest.mark.parametrize("text", [
    put(SMALL_TEXT + " x", 2, " "),         # the first colon read as a blank
    put(SMALL_TEXT + " x", 5, "|"),         # a fingerprint digit read as "|"
    put(SMALL_TEXT, 4, "."),
])
def test_short_tag_with_one_cell_misread_is_damaged(text):
    assert split_label(text)[0] is None
    assert is_damaged(text, 1, 1)


NAMES = [
    "", "x", "doc.tar", "holiday photos.tar", "3f9a2c1b0011.tar", "[", "[]",
    "[draft] report.pdf", "[2024] taxes.zip", "[2024.08.31] photos", "[2024.08.31 holiday] x",
    "[backup 2024-08-31]", "[20240831-1] x", "(2024) x", "[deadbeef] x",
    # Refused by counting hexadecimal digits in the first word (review).
    "[202411161230] backup.tar", "[1700000000] log.tar", "[2024.08.31.2] x", "(20241116123) x",
    "[0123456789] list", "[a1b2c3d4e5] x", "[deadbeef01] x",
    # The unreleased two-field form.
    f"[{BIG.size}:{BIG.fingerprint}] x", f"[{BIG.size}:{BIG.fingerprint}]", "[0:00000000]",
]


@pytest.mark.parametrize("text", NAMES)
def test_name_is_not_a_damaged_tag(text):
    assert not is_damaged(text)
    assert not is_damaged(text, 1, 1)
    assert not is_damaged(text, 1, 0)


def test_a_tag_is_not_a_damaged_tag():
    # Text in which split_label finds a tag is for the caller to check.
    assert not is_damaged(BIG_TEXT) and not is_damaged(BIG_TEXT + " x")
    wrong = BIG.page_text(7, 8)
    assert wrong != BIG_TEXT and split_label(wrong)[0] == BIG
    assert not is_damaged(wrong) and not is_damaged(wrong + " x")


def test_damage_is_judged_against_the_page_and_total_read():
    text = put(BIG_TEXT + " x", COLON1, ";")
    assert is_damaged(text, 8, 8)
    assert BIG.check(7, 8) != BIG.check(8, 8) and not is_damaged(text, 7, 8)
    # The repaired tag must fit the total, as a tag read whole must.
    assert BIG.check(8, 9) != BIG.check(8, 8)
    other = put(BIG.page_text(8, 9) + " x", COLON1, ";")
    assert not BIG.fits(9, A4) and not is_damaged(other, 8, 9)


def test_two_cells_misread_are_not_detected():
    # The known limit: such a page passes for an untagged page of its own.
    text = put(put(BIG_TEXT + " x", COLON1, ";"), COLON2, ";")
    assert not is_damaged(text)


def random_case(rng):
    """(tag, page, total) of a file the encoder could print on A4."""
    capacity = A4.net_bits // 8
    digits = rng.randint(1, len(str(MAX_PAGES * capacity)))
    size = min(rng.randrange(10 ** (digits - 1) if digits > 1 else 0, 10 ** digits),
               MAX_PAGES * capacity)
    total = -(-size // capacity)
    tag = Tag(size, f"{rng.getrandbits(4 * FINGERPRINT_DIGITS):0{FINGERPRINT_DIGITS}x}")
    assert tag.fits(total, A4)
    return tag, rng.randint(1, max(total, 1)), total


def single_cell_misreads(tags, seed):
    """Every glyph in every cell of `tags` random tags: (cells tried, still valid,
    refused by the check, detected as damaged). None may pass for a name."""
    rng = random.Random(seed)
    tried = valid = refused = damaged = 0
    for _ in range(tags):
        tag, page, total = random_case(rng)
        printed = tag.page_text(page, total)
        # With a name the separator can be misread too; without one a stray
        # mark can appear in the blank cell after the tag.
        for whole, cells in ((printed + " x", len(printed) + 1), (printed + " ", len(printed) + 1)):
            for at in range(cells):
                for glyph in PRINTABLE:
                    if glyph == whole[at]:
                        continue
                    text = put(whole, at, glyph)
                    tried += 1
                    got, check, _ = split_label(text)
                    if got is None:
                        assert damaged_tag(text, page, total, A4), (text, page, total)
                        damaged += 1
                    elif got.fits(total, A4) and got.check(page, total) == check:
                        valid += 1
                    else:
                        refused += 1
    return tried, valid, refused, damaged


def check_single_cell_misreads(tags, seed):
    tried, valid, refused, damaged = single_cell_misreads(tags, seed)
    print(f"single-cell misreads: {tried} tried, {valid} still valid tags, "
          f"{refused} refused by the check, {damaged} detected as damaged")
    assert tried == valid + refused + damaged
    # A misread that leaves a well-formed tag passes about once in 16**CHECK_DIGITS.
    assert valid < 3 * (valid + refused) / 16 ** CHECK_DIGITS + 5


def test_every_single_cell_misread_is_caught():
    check_single_cell_misreads(12, 1)


@pytest.mark.slow
def test_every_single_cell_misread_is_caught_in_many_tags():
    check_single_cell_misreads(400, 2)


def ordinary_names(rng, count):
    hexdigits = "0123456789abcdef"
    for _ in range(count):
        y, mo, d = rng.randint(1990, 2099), rng.randint(1, 12), rng.randint(1, 28)
        h, mi, s = rng.randint(0, 23), rng.randint(0, 59), rng.randint(0, 59)
        word = "".join(rng.choice(hexdigits) for _ in range(rng.randint(1, 24)))
        yield f"[{y}-{mo:02}-{d:02}] backup.tar"
        yield f"[{y}.{mo:02}.{d:02}.{rng.randint(0, 9)}] x"
        yield f"[{y}{mo:02}{d:02}{h:02}{mi:02}] backup.tar"
        yield f"[{y}{mo:02}{d:02}:{h:02}{mi:02}{s:02}] x"
        yield f"[{h:02}:{mi:02}:{s:02}] log"
        yield f"({y}{mo:02}{d:02}{h:02}{mi}) x"
        yield f"[{rng.randint(0, 2 ** 32)}] log.tar"
        yield f"[{word}] x"
        yield f"{word}.tar"
        yield f"[v{rng.randint(0, 20)}.{rng.randint(0, 99)}.{rng.randint(0, 99)}] release"
        yield f"{rng.randint(0, 20)}.{rng.randint(0, 99)}.{rng.randint(0, 99)}-rc{d}"
        # The two-field form with any size.
        yield f"[{rng.randrange(10 ** rng.randint(1, MAX_SIZE_DIGITS))}:{word[:8]:0<8}] x"


def random_text(rng, first=""):
    return first + "".join(rng.choice(PRINTABLE) for _ in range(rng.randint(0, 60)))


def check_names(count, seed):
    rng = random.Random(seed)
    for text in ordinary_names(rng, count):
        page, total = random_case(rng)[1:]
        assert not damaged_tag(text, page, total, A4), (text, page, total)
    refused = 0
    for _ in range(12 * count):
        page, total = random_case(rng)[1:]
        assert not damaged_tag(random_text(rng), page, total, A4)
        refused += damaged_tag(random_text(rng, "["), page, total, A4)
    print(f"random printable text starting with '[': {refused} of {12 * count} refused")
    assert refused <= 12 * count // 1000


def test_names_are_not_damaged_tags():
    check_names(1000, 3)


@pytest.mark.slow
def test_many_names_are_not_damaged_tags():
    check_names(20000, 4)


# Text that has a tag's form but for one cell and carries a random check: the
# chance that some repair's check matches bounds how often a name is refused.
def test_tag_shaped_text_is_refused_about_once_per_check_match():
    rng = random.Random(5)
    refused = tried = 0
    for _ in range(300):
        tag, page, total = random_case(rng)
        whole = tag.page_text(page, total) + " x"
        junk = whole[:-5] + f"{rng.getrandbits(4 * CHECK_DIGITS):0{CHECK_DIGITS}x}" + whole[-3:]
        if junk == whole:
            continue
        at = rng.randrange(len(whole) - 2)
        text = put(junk, at, rng.choice([g for g in "~|;.-" if g != junk[at]]))
        tried += 1
        refused += damaged_tag(text, page, total, A4)
    print(f"tag-shaped text with a random check: {refused} of {tried} refused")
    assert refused < tried / 4
