# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import re
from functools import cache
from unittest import mock

import numpy as np
import pytest

import optar.identify
from optar import PAPERS, PageFormat, encode
from optar.decoder import DecodeOptions, PageResult, PageStats, locate_page
from optar.encoder import MAX_PAGES, blank_page
from optar.errors import DecodeError, IdentifyError
from optar.font import label_text
from optar.identify import (
    ScanIdentity,
    candidate_rotations,
    decode_unlabelled,
    identify_scan,
)
from optar.imageio import read_scan
from optar.label import (
    MIN_LABEL_CONFIDENCE,
    MIN_LABEL_MARGIN,
    LabelReading,
    parse_label,
    printed_label,
    read_label,
)
from optar.tag import Tag, damaged_tag, make_tag, split_label, tagged_label
from tests.helpers import DEGRADED, fake_scan, save_scan, seeded_bytes
from tests.unit import test_label as label_tests


@cache
def document(paper):
    """A two-page tagged document: (fmt, data, pages)."""
    fmt = PageFormat.for_paper(PAPERS[paper])
    data = seeded_bytes(4, fmt.net_bits // 8 + 700)
    tag = make_tag(data)
    return fmt, data, tuple(encode(data, fmt, lambda p, t: tagged_label(tag, "doc.tar", p, t)))


def scan_of(paper, page_no=2, name="doc.tar", **kw):
    assert name == "doc.tar"
    fmt, data, pages = document(paper)
    return data, fake_scan(pages[page_no - 1].pixels, **({"scale": 2, "margin": 50} | kw))


@cache
def upright(paper, case=None):
    """A read-only upright scan of page 2: clean at scale 2, or a DEGRADED case."""
    fmt = PageFormat.for_paper(PAPERS[paper])
    kw = {} if case is None else {"fmt": fmt} | DEGRADED[case]
    img = scan_of(paper, **kw)[1]
    img.flags.writeable = False
    return img


def turned(img, turns):
    """The scan as it needs `turns` counter-clockwise quarter turns to be upright."""
    return np.rot90(img, -turns)


def pad(img, top=0, bottom=0, left=0, right=0):
    return np.pad(img, ((top, bottom), (left, right)), constant_values=255)


def check_identity(ident, paper, turns, page=2, total=2, name="doc.tar"):
    _, data, _ = document(paper)
    assert isinstance(ident, ScanIdentity)
    assert ident.paper is PAPERS[paper] and ident.fmt == PageFormat.for_paper(PAPERS[paper])
    assert ident.rotation == turns
    assert (ident.page, ident.total, ident.name) == (page, total, name)
    assert ident.tag == make_tag(data)
    assert ident.confidence >= MIN_LABEL_CONFIDENCE and ident.margin >= MIN_LABEL_MARGIN
    assert ident.grid.fmt == ident.fmt


def test_candidate_rotations():
    assert candidate_rotations(np.zeros((30, 20), np.uint8)) == (0, 2)
    assert candidate_rotations(np.zeros((20, 20), np.uint8)) == (0, 2)
    assert candidate_rotations(np.zeros((20, 30), np.uint8)) == (1, 3)


# One case per rotation and per paper by default; all eight in the slow run.
DEFAULT_CLEAN = [("a4", 0), ("letter", 1), ("letter", 2), ("a4", 3)]
ALL_CLEAN = [(p, t) for p in ("a4", "letter") for t in range(4)]


@pytest.mark.parametrize("paper,turns", [
    pytest.param(p, t, marks=() if (p, t) in DEFAULT_CLEAN else pytest.mark.slow)
    for p, t in ALL_CLEAN
])
def test_identifies_paper_page_tag_and_rotation(paper, turns):
    ident, located = identified(paper, turns)
    check_identity(ident, paper, turns)
    # The likelier paper in both orientations first: a page the wrong way up
    # costs one extra locate, with the same paper.
    fmt = PageFormat.for_paper(PAPERS[paper])
    assert located == ((fmt,) if turns in (0, 1) else (fmt, fmt))


@cache
def identified(paper, turns, case=None):
    """identify_scan of a cached scan, and the formats locate_page was called with."""
    located = []
    real = optar.identify.locate_page

    def counting(image, fmt, options=None):
        located.append(fmt)
        return real(image, fmt, options)

    with mock.patch.object(optar.identify, "locate_page", counting):
        ident = identify_scan(turned(upright(paper, case), turns))
    return ident, tuple(located)


def test_grid_is_located_on_the_upright_image():
    img = upright("a4")
    ident, _ = identified("a4", 3)
    assert ident.grid.cleaned.shape == img.shape
    # The top-left cross is where fake_scan put it: margin 50, scale 2.
    fmt = ident.fmt
    x0 = 50 + 2 * (fmt.border + fmt.chalf)
    assert np.abs(ident.grid.positions[0, 0] - x0).max() <= 2


# A half turn (a wrong orientation is tried first) under the combined
# degradation by default; every rotation, paper and DEGRADED case in the slow run.
@pytest.mark.parametrize("paper,turns", [("a4", 2)])
def test_identifies_combined_degradation(paper, turns):
    check_identity(identified(paper, turns, "combined")[0], paper, turns)


@pytest.mark.slow
@pytest.mark.parametrize("case", sorted(DEGRADED))
@pytest.mark.parametrize("paper", ["a4", "letter"])
@pytest.mark.parametrize("turns", [0, 1, 2, 3])
def test_identifies_every_degradation(case, paper, turns):
    check_identity(identified(paper, turns, case)[0], paper, turns)


@pytest.mark.parametrize("paper", ["a4", "letter"])
def test_slightly_rotated_with_unequal_margins(paper):
    _, img = scan_of(paper, margin=20, rotate=0.5)
    img = pad(img, top=150, left=10, right=90)
    check_identity(identify_scan(img), paper, 0)


@pytest.mark.parametrize("paper", ["a4", "letter"])
def test_outline_not_image_shape_decides_paper(paper):
    img = upright(paper)
    # A wide white margin on one side: the image is still portrait, but its
    # width-to-height ratio is no longer the page's, so only the outline found
    # inside it can name the paper.
    wide = pad(img, right=600)
    assert optar.identify._papers_by_shape(optar.identify._outline(wide))[0] is PAPERS[paper]
    check_identity(identify_scan(wide), paper, 0)
    # Taller than wide, with the page in one corner of the bed.
    tall = pad(img, bottom=900, right=300)
    assert optar.identify._papers_by_shape(optar.identify._outline(tall))[0] is PAPERS[paper]


@pytest.mark.parametrize("paper", ["a4", "letter"])
@pytest.mark.parametrize("angle", [-1.0, -0.5, 0.5, 1.0])
def test_aspect_ratio_orders_the_right_paper_first(paper, angle):
    fmt, _, pages = document(paper)
    img = fake_scan(pages[0].pixels, scale=1, margin=30, rotate=angle)
    for turns in (0, 2):
        corners = optar.identify._outline(np.ascontiguousarray(np.rot90(img, turns)))
        assert optar.identify._papers_by_shape(corners)[0] is PAPERS[paper]


def test_untagged_label_and_empty_file():
    fmt = PageFormat.for_paper(PAPERS["a4"])
    ident = identify_scan(fake_scan(next(encode(b"", fmt, "")).pixels, scale=1, margin=40))
    assert (ident.page, ident.total, ident.tag, ident.name) == (1, 0, None, "")


def test_untagged_name_is_the_whole_free_text():
    fmt = PageFormat.for_paper(PAPERS["letter"])
    page = next(encode(b"abc", fmt, "holiday photos.tar")).pixels
    ident = identify_scan(fake_scan(page, scale=1, margin=40))
    assert (ident.paper, ident.page, ident.total) == (PAPERS["letter"], 1, 1)
    assert (ident.tag, ident.name) == (None, "holiday photos.tar")


def gradient():
    y, x = np.mgrid[0:2400, 0:1700]
    return ((x + y) * 255 // (2400 + 1700)).astype(np.uint8)


@pytest.mark.parametrize("img,reason", [
    (np.full((900, 700), 255, np.uint8), "no page found"),
    (np.full((700, 900), 0, np.uint8), None),
    (np.random.default_rng(1).integers(0, 256, (2400, 1700), dtype=np.uint8), None),
    (gradient(), None),
], ids=["white", "black-landscape", "noise", "gradient"])
def test_non_pages_raise_identify_error(img, reason):
    with pytest.raises(IdentifyError) as e:
        identify_scan(img)
    assert isinstance(e.value, DecodeError) and e.value.page is None
    assert e.value.reason in ("no page found", "label unreadable")
    assert str(e.value) == e.value.reason
    if reason:
        assert e.value.reason == reason


def test_identify_error():
    e = IdentifyError("label unreadable")
    assert (e.reason, str(e), e.page) == ("label unreadable", "label unreadable", None)
    e.page = 3
    assert e.page == 3


def test_rejects_bad_images():
    with pytest.raises(DecodeError):
        identify_scan(np.zeros((30, 20, 3), np.uint8))
    with pytest.raises(DecodeError):
        identify_scan(np.zeros((30, 20), np.float32))
    with pytest.raises(IdentifyError, match="no page found"):
        identify_scan(np.zeros((0, 0), np.uint8))


def test_tag_that_does_not_fit_is_not_identified():
    assert candidate(tagged_label(Tag(999999999, "3f9a2c1b"), "x", 8, 8)) is None
    assert candidate(tagged_label(Tag(1399271, "3f9a2c1b"), "x", 8, 8)) is not None


def test_tag_printed_for_another_page_count_is_not_identified():
    # The tag of the two-page document, printed on a one-page printout.
    fmt, data, _ = document("letter")
    for label, accepted in ((tagged_label(make_tag(data), "doc.tar", 1, 1), False),
                            (tagged_label(make_tag(b"abc"), "doc.tar", 1, 1), True)):
        page = next(encode(b"abc", fmt, label)).pixels
        img = fake_scan(page, scale=1, margin=40)
        ident = optar.identify._identify_upright(img, 0, PAPERS["letter"], None)
        assert (ident is not None) == accepted


@cache
def other_format_scan():
    """A blank A4 page whose label carries Letter's format string."""
    a4 = PageFormat.for_paper(PAPERS["a4"])
    letter = PageFormat.for_paper(PAPERS["letter"])
    return fake_scan(blank_page(a4, label_text(letter, 1, 1, "x")), scale=1, margin=40)


def test_label_naming_another_format_is_not_identified():
    a4 = PageFormat.for_paper(PAPERS["a4"])
    img = other_format_scan()
    # Under its own grid the label reads perfectly, so only the format string
    # read from it can tell that it does not belong to this paper.
    reading = read_label(locate_page(img, a4))
    assert reading.reliable
    assert parse_label(reading.text).format == PageFormat.for_paper(PAPERS["letter"]).to_string()
    assert optar.identify._identify_upright(img, 0, PAPERS["a4"], None) is None


@pytest.mark.slow
def test_label_naming_another_format_is_unreadable():
    with pytest.raises(IdentifyError) as e:
        identify_scan(other_format_scan())
    assert e.value.reason == "label unreadable"


# A tag whose size fits 8 A4 pages (7 * 199773 < size <= 8 * 199773), and the
# same tag with the size or the fingerprint changed in one digit.
EIGHT = Tag(1500000, "3f9a2c1b")


def check_label(text):
    """A blank A4 page labelled `text`: (whether the label read reliably and
    exactly as printed, the candidate for A4 upright or None)."""
    fmt = PageFormat.for_paper(PAPERS["a4"])
    full = label_text(fmt, 8, 8, text)
    img = fake_scan(blank_page(fmt, full), scale=1, margin=40)
    readings = []

    def reading(grid):
        readings.append(read_label(grid))
        return readings[-1]

    with mock.patch.object(optar.identify, "read_label", reading):
        ident = optar.identify._identify_upright(img, 0, PAPERS["a4"], None)
    return readings[0].reliable and readings[0].text == full, ident


def test_label_with_the_right_check_is_identified():
    clear, ident = check_label(tagged_label(EIGHT, "x", 8, 8))
    assert clear and ident is not None
    assert (ident.page, ident.total, ident.tag, ident.name) == (8, 8, EIGHT, "x")


def forged(size, fingerprint, check):
    return f"[{size}:{fingerprint}:{check}] x"


# Each label below reads clearly and says page 8 of 8 with a tag that fits 8
# pages; only the check can tell that the label is not what was printed.
@pytest.mark.parametrize("text", [
    tagged_label(EIGHT, "x", 3, 8),                          # the check of page 3
    tagged_label(EIGHT, "x", 8, 9),                          # the check for 9 pages
    forged(1510000, EIGHT.fingerprint, EIGHT.check(8, 8)),   # size one digit off
    forged(EIGHT.size, "3f9a2c1c", EIGHT.check(8, 8)),       # fingerprint one digit off
], ids=["other-page", "other-total", "size", "fingerprint"])
def test_label_with_a_wrong_check_is_not_identified(text):
    from optar.tag import split_label

    tag, check, _ = split_label(text)
    assert tag is not None and tag.fits(8, PageFormat.for_paper(PAPERS["a4"]))
    assert check != tag.check(8, 8)
    clear, ident = check_label(text)
    assert clear and ident is None


def test_wrong_check_is_reported_as_unreadable_label():
    fmt = PageFormat.for_paper(PAPERS["a4"])
    img = fake_scan(blank_page(fmt, label_text(fmt, 8, 8, tagged_label(EIGHT, "x", 3, 8))),
                    scale=1, margin=40)
    with mock.patch.object(optar.identify, "_papers_by_shape", lambda c: [PAPERS["a4"]]):
        with pytest.raises(IdentifyError) as e:
            identify_scan(img)
    assert e.value.reason == "label unreadable"


def test_misread_page_or_total_rarely_passes_the_check():
    # Every single-digit substitution of the page or the total in the labels
    # p/9 (p = 1..9) of one document: 162 forged labels. A check of two hex
    # digits lets an accidental misread through 1 time in 256, so about 0.6
    # are expected to pass; measured with this tag: 0.
    tag = EIGHT
    passed = []
    for page in range(1, 10):
        for digit in range(10):
            if digit != page and tag.check(digit, 9) == tag.check(page, 9):
                passed.append((page, 9, digit, 9))
            if digit != 9 and tag.check(page, digit) == tag.check(page, 9):
                passed.append((page, 9, page, digit))
    assert len(passed) <= 3, passed


def labelled_blank(page, total):
    """A scan of a blank A4 page whose label says page/total, whatever the encoder allows."""
    fmt = PageFormat.for_paper(PAPERS["a4"])
    return fake_scan(blank_page(fmt, label_text(fmt, page, total, "x")), scale=1, margin=40)


# Each full refusal locates the page four times (two papers, two orientations),
# so these run only in the slow run; test_page_count_limit_is_the_encoders
# checks the limit by default.
@pytest.mark.slow
@pytest.mark.parametrize("page,total", [(1, 99999), (10000, 10000)])
def test_page_count_the_encoder_could_not_write_is_not_identified(page, total):
    assert total > MAX_PAGES
    with pytest.raises(IdentifyError) as e:
        identify_scan(labelled_blank(page, total))
    assert e.value.reason == "label unreadable"


@pytest.mark.parametrize("count,accepted", [(MAX_PAGES, True), (MAX_PAGES + 1, False)])
def test_page_count_limit_is_the_encoders(count, accepted):
    readings = []

    def reading(grid):
        readings.append(read_label(grid))
        return readings[-1]

    with mock.patch.object(optar.identify, "read_label", reading):
        ident = optar.identify._identify_upright(
            labelled_blank(count, count), 0, PAPERS["a4"], None
        )
    # Both labels read clearly and correctly; only the count decides.
    assert readings[0].reliable and readings[0].text.endswith(f" {count}/{count} x")
    assert (ident is not None) == accepted
    if accepted:
        assert (ident.page, ident.total, ident.name) == (count, count, "x")


# ---- moderately blurred scans, through the real path ---------------------------
#
# Saved as PNG and loaded with read_scan, which converts to linear light: that
# darkens blurred white strokes, which a threshold halfway up the band then
# thinned. The pages decode with no uncorrectable symbol, so their labels must
# identify them.
BLURRED = {
    "s2-b1.0-n15": dict(scale=2, blur=1.0, noise=15),
    "s2-b1.0-n0": dict(scale=2, blur=1.0),
    "s3-b1.5-n20": dict(scale=3, blur=1.5, noise=20),
}


def via_png(tmp_path, scan):
    path = tmp_path / "scan.png"
    save_scan(path, scan)
    return read_scan(path)


@pytest.mark.parametrize("seed", [1, 2])
@pytest.mark.parametrize("case", list(BLURRED))
def test_blurred_tagged_scan_is_identified(tmp_path, case, seed):
    fmt, data, pages = document("a4")
    img = via_png(tmp_path, fake_scan(pages[1].pixels, margin=60, seed=seed, **BLURRED[case]))
    ident = identify_scan(img)
    check_identity(ident, "a4", 0)
    want = printed_label(fmt, label_text(fmt, 2, 2, tagged_label(make_tag(data), "doc.tar", 2, 2)))
    assert read_label(ident.grid).text == want


@cache
def untagged_page():
    fmt = PageFormat.for_paper(PAPERS["a4"])
    return next(encode(b"abc", fmt, "holiday photos.tar")).pixels


# Untagged labels need a reliable reading, which blur can deny: only the
# invariant is asserted. Measured: all six are identified correctly (cut
# halfway up the band, all six were refused). One runs by default.
@pytest.mark.parametrize("case,seed", [
    pytest.param(c, s, marks=() if (c, s) == ("s2-b1.0-n0", 1) else pytest.mark.slow)
    for c in BLURRED for s in (1, 2)
])
def test_blurred_untagged_scan_is_identified_or_refused(tmp_path, case, seed):
    img = via_png(tmp_path, fake_scan(untagged_page(), margin=60, seed=seed, **BLURRED[case]))
    try:
        ident = identify_scan(img)
    except IdentifyError as e:
        assert e.reason == "label unreadable"
        return
    assert (ident.paper, ident.rotation, ident.page, ident.total) == (PAPERS["a4"], 0, 1, 1)
    assert (ident.tag, ident.name) == (None, "holiday photos.tar")


# ---- no misread is accepted as another page or document ---------------------
#
# The five families of misreads of tests/unit/test_label.py, applied to the
# label band of a located scan. Whatever a family does, the candidate is
# refused or names the true page, total and tag; the name may differ, but
# only in punctuation (a "." gained or lost, ":" read as ";").
UNTAGGED = (8, 9, "holiday 2024-08-31 8.tar")
IDENTITY_LABELS = [*label_tests.FAMILY_LABELS, UNTAGGED]
def thinned(band, rng):
    return label_tests.thin(band, int(rng.integers(1 << 31)))


FAMILIES = {
    "thinned": lambda fmt, want: thinned,
    "blotchy": lambda fmt, want: label_tests.blotchy(70),
    "ramp": lambda fmt, want: label_tests.gradient(120, 30),
    "offset": lambda fmt, want: label_tests.offset_x(1.5),
    "speck": lambda fmt, want: label_tests.speck(fmt, want, True),
}


def truth(label):
    page, total, text = IDENTITY_LABELS[label]
    tag, _, name = split_label(text)
    return page, total, tag, name


def perturbed_candidate(paper, label, family, seed):
    """_identify_upright of a located scan of IDENTITY_LABELS[label] whose band
    `family` perturbed: the candidate for the true paper and rotation."""
    fmt = PageFormat.for_paper(PAPERS[paper])
    page, total, text = IDENTITY_LABELS[label]
    grid, want = label_tests.located(fmt, page, total, text)
    seed = (seed, label, int(paper == "letter"))
    grid = label_tests.perturbed_band(grid, FAMILIES[family](fmt, want), seed)
    with mock.patch.object(optar.identify, "locate_page", lambda image, f, o=None: grid):
        return optar.identify._identify_upright(grid.cleaned, 0, PAPERS[paper], None)


def same_but_punctuation(a, b):
    return re.sub(r"[^0-9A-Za-z]", "", a) == re.sub(r"[^0-9A-Za-z]", "", b)


def check_misreads(family, seeds):
    """Every candidate is refused or right; returns (accepted, names misread)."""
    accepted, misnamed = 0, []
    for paper in ("a4", "letter"):
        for label in range(len(IDENTITY_LABELS)):
            page, total, tag, name = truth(label)
            for seed in seeds:
                ident = perturbed_candidate(paper, label, family, seed)
                if ident is None:
                    continue
                accepted += 1
                assert (ident.page, ident.total, ident.tag) == (page, total, tag), (
                    paper, label, seed, ident.name)
                if ident.name != name:
                    misnamed.append((name, ident.name))
    for want, got in misnamed:
        assert same_but_punctuation(want, got), (want, got)
    return accepted, misnamed


@pytest.mark.parametrize("family", list(FAMILIES))
def test_misread_is_refused_or_right(family):
    check_misreads(family, range(2))


@pytest.mark.slow
@pytest.mark.parametrize("family", list(FAMILIES))
def test_misread_is_refused_or_right_sweep(family):
    check_misreads(family, range(2, 40))


def check_whole(img, label, paper):
    """identify_scan of a whole scan: refused, or the truth on the true paper."""
    try:
        ident = identify_scan(img)
    except IdentifyError as e:
        assert e.reason == "label unreadable"
        return None
    page, total, tag, name = truth(label)
    assert ident.paper is PAPERS[paper] and ident.rotation == 0
    assert (ident.page, ident.total, ident.tag) == (page, total, tag)
    assert same_but_punctuation(ident.name, name)
    return ident


def labelled_scan(paper, label, **kw):
    fmt = PageFormat.for_paper(PAPERS[paper])
    page, total, text = IDENTITY_LABELS[label]
    pixels, _ = label_tests.labelled_page(fmt, page, total, text)
    return fake_scan(pixels, margin=60, **kw)


# The whole scan perturbed and identified from scratch, every candidate paper
# and rotation tried: the blurred scans through the real path, and the band
# families on the scan itself.
@pytest.mark.slow
@pytest.mark.parametrize("paper", ["a4", "letter"])
@pytest.mark.parametrize("case", list(BLURRED))
def test_blurred_scan_is_refused_or_right(tmp_path, paper, case):
    for label in (0, 1, 4, 8):
        for seed in (3, 4):
            img = via_png(tmp_path, labelled_scan(paper, label, seed=seed, **BLURRED[case]))
            check_whole(img, label, paper)


@pytest.mark.slow
@pytest.mark.parametrize("paper", ["a4", "letter"])
@pytest.mark.parametrize("family", list(FAMILIES))
def test_misread_scan_is_refused_or_right(paper, family):
    fmt = PageFormat.for_paper(PAPERS[paper])
    for label in (0, 4, 8):
        page, total, text = IDENTITY_LABELS[label]
        _, want = label_tests.labelled_page(fmt, page, total, text)
        img = labelled_scan(paper, label, scale=label_tests.SCALE)
        rows, cols = label_tests.band_box(fmt)
        rows, cols = slice(rows.start - 12, rows.stop + 12), slice(cols.start - 12, cols.stop + 12)
        img[rows, cols] = FAMILIES[family](fmt, want)(img[rows, cols].copy(),
                                                     np.random.default_rng(label))
        check_whole(img, label, paper)


# ---- damaged tags --------------------------------------------------------------

def candidate(text, page=8, total=8):
    """The A4 candidate for a label reading `text` as page 8 of 8, perfectly
    and with every score at its best: only the text decides."""
    fmt = PageFormat.for_paper(PAPERS["a4"])
    reading = LabelReading(printed_label(fmt, label_text(fmt, page, total, text)), 1.0, 1.0)
    assert reading.reliable
    grid = mock.Mock(fmt=fmt)
    with mock.patch.object(optar.identify, "locate_page", lambda image, f, o=None: grid), \
            mock.patch.object(optar.identify, "read_label", lambda g: reading):
        return optar.identify._identify_upright(None, 0, PAPERS["a4"], None)


# A tag (of a file that fits 8 A4 pages) that a misread has broken in one cell
# must not pass for a name: such a page would join no document, or the wrong one.
WHOLE = Tag(1399271, "9b0d6853").page_text(8, 8)
SHORT = Tag(5, "0b3d8e9f")


def misread(text, at, glyph):
    assert text[at] != glyph
    return text[:at] + glyph + text[at + 1:]


@pytest.mark.parametrize("text", [
    misread(WHOLE + " x", 1, "0"),                     # the first size digit read as 0
    misread(WHOLE + " x", WHOLE.index(":"), ";"),      # a colon read as ";"
    misread(WHOLE + " x", WHOLE.rindex(":"), "."),     # a colon read as "."
    misread(WHOLE + " x", len(WHOLE) - 1, ")"),        # the bracket read as ")"
    misread(WHOLE + " x", len(WHOLE) - 1, "1"),        # the bracket read as "1"
    misread(WHOLE + " x", 0, "("),                     # the opening bracket read as "("
    misread(WHOLE + " x", 0, "<"),
    misread(WHOLE + " x", 0, " "),                     # the opening bracket lost
    misread(WHOLE + " x", WHOLE.rindex(":") - 2, "s"),  # a hex digit read as a letter
    misread(WHOLE + " x", len(WHOLE), "`"),            # a stray mark after the tag
    misread(WHOLE + " x", len(WHOLE), "."),
    misread(WHOLE, 1, "0"),                            # one of them with no name
    misread(WHOLE, len(WHOLE) - 1, " "),               # the closing bracket lost, no name
    misread(WHOLE + " x", WHOLE.index(":"), " "),      # the first colon read as a blank
    misread(WHOLE + " x", 2, "|"),                     # a size digit read as "|"
    misread(WHOLE + " x", 3, " "),                     # as a blank
    misread(WHOLE + " x", 3, "-"),                     # as "-"
])
def test_damaged_tag_is_unreadable(text):
    assert split_label(text)[0] is None
    assert damaged_tag(text.rstrip(" "), 8, 8, PageFormat.for_paper(PAPERS["a4"]))
    assert candidate(text) is None


@pytest.mark.parametrize("at, glyph", [(2, " "), (2, ";"), (5, "|"), (0, "<")])
@pytest.mark.parametrize("name", ["", " x"])
def test_damaged_short_tag_is_unreadable(at, glyph, name):
    text = misread(SHORT.page_text(1, 1), at, glyph) + name
    assert split_label(text)[0] is None
    assert candidate(text, 1, 1) is None
    assert candidate(SHORT.page_text(1, 1) + name, 1, 1).tag == SHORT


def test_tag_with_a_wrong_check_is_unreadable():
    wrong = Tag(1399271, "9b0d6853").page_text(7, 8)
    assert wrong != WHOLE and candidate(wrong + " x") is None
    assert candidate(WHOLE + " x").tag == Tag(1399271, "9b0d6853")


@pytest.mark.parametrize("text", [
    "[draft] report.pdf", "[2024] taxes.zip", "[2024.08.31] photos", "[backup 2024-08-31]",
    "[61:9b8d0e3f] x",  # the unreleased two-field form is a name
    # Names with many digits: only a tag one cell away from a right check is refused.
    "[202411161230] backup.tar", "[1700000000] log.tar", "[2024.08.31.2] x", "(20241116123) x",
    "[0123456789] list", "[a1b2c3d4e5] x", "[deadbeef01] x",
])
def test_bracketed_name_is_an_untagged_name(text):
    ident = candidate(text)
    assert (ident.page, ident.total, ident.tag, ident.name) == (8, 8, None, text)


def test_bracketed_name_is_read_from_the_page():
    clear, ident = check_label("[draft] report.pdf")
    assert clear and (ident.tag, ident.name) == (None, "[draft] report.pdf")


@pytest.mark.slow
def test_damaged_tag_is_reported_as_unreadable_label():
    fmt = PageFormat.for_paper(PAPERS["a4"])
    img = fake_scan(blank_page(fmt, label_text(fmt, 8, 8, misread(WHOLE, 1, "0") + " x")),
                    scale=1, margin=40)
    with mock.patch.object(optar.identify, "_papers_by_shape", lambda c: [PAPERS["a4"]]):
        with pytest.raises(IdentifyError) as e:
            identify_scan(img)
    assert e.value.reason == "label unreadable"


def blacken_label(pixels, fmt):
    out = np.array(pixels, copy=True)
    top = fmt.border + fmt.data_height
    out[top : top + fmt.text_height, fmt.border : fmt.width - fmt.border] = 0
    return out


def test_black_label_band_is_unreadable_but_decodes_unlabelled():
    fmt, data, pages = document("a4")
    img = turned(fake_scan(blacken_label(pages[0].pixels, fmt), scale=2, margin=50), 2)
    with pytest.raises(IdentifyError) as e:
        identify_scan(img)
    assert e.value.reason == "label unreadable"
    turns, result = decode_unlabelled(img, fmt)
    assert turns == 2 and result.stats.uncorrectable == 0
    assert np.packbits(result.bits).tobytes() == data[: fmt.net_bits // 8]


@pytest.mark.slow
def test_decode_unlabelled_landscape_and_detail():
    fmt, data, _ = document("letter")
    img = turned(upright("letter"), 1)
    turns, result = decode_unlabelled(img, fmt, DecodeOptions(), detail=True)
    assert turns == 1 and result.stats.uncorrectable == 0
    assert result.grid is not None and result.grid.cleaned.shape == upright("letter").shape
    tail = data[fmt.net_bits // 8 :]
    assert np.packbits(result.bits).tobytes()[: len(tail)] == tail


def test_decode_unlabelled_raises_when_every_rotation_raises():
    fmt = PageFormat.for_paper(PAPERS["letter"])
    with pytest.raises(DecodeError):
        decode_unlabelled(np.full((900, 700), 255, np.uint8), fmt)


def fake_result(uncorrectable, histogram):
    return PageResult(np.zeros(0, np.uint8), PageStats(10, histogram, uncorrectable), None)


@pytest.mark.parametrize("outcomes,want", [
    ({0: (5, (5, 0, 0, 0)), 2: (0, (10, 0, 0, 0))}, 2),
    ({0: (1, (0, 9, 0, 0)), 2: (1, (0, 0, 9, 0))}, 0),   # fewer corrected bits
    ({0: (1, (0, 0, 9, 0)), 2: (1, (0, 9, 0, 0))}, 2),
    ({0: (1, (1, 2, 0, 0)), 2: (1, (0, 0, 1, 0))}, 0),   # equal: lower rotation
    ({0: "raise", 2: (40, (0, 0, 0, 0))}, 2),
], ids=["unrecoverable", "corrected-0", "corrected-2", "tie", "skip-error"])
def test_decode_unlabelled_choice(monkeypatch, outcomes, want):
    marked = np.zeros((4, 3), np.uint8)
    marked[0, 0] = 1  # at the top left only when not turned

    def locate(image, fmt, options=None):
        rotation = 0 if image[0, 0] else 2
        if outcomes[rotation] == "raise":
            raise DecodeError("cannot find upper left corner")
        return rotation

    def decode(rotation, *, debug=False, detail=False):
        return fake_result(*outcomes[rotation])

    monkeypatch.setattr(optar.identify, "locate_page", locate)
    monkeypatch.setattr(optar.identify, "decode_located", decode)
    turns, result = decode_unlabelled(marked, PageFormat.for_paper(PAPERS["a4"]))
    assert turns == want and result.stats == fake_result(*outcomes[want]).stats


def test_decode_unlabelled_reraises_the_last_error(monkeypatch):
    def locate(image, fmt, options=None):
        raise DecodeError("first" if image[0, 0] else "last")

    marked = np.zeros((4, 3), np.uint8)
    marked[0, 0] = 1
    monkeypatch.setattr(optar.identify, "locate_page", locate)
    with pytest.raises(DecodeError, match="^last$") as e:
        decode_unlabelled(marked, PageFormat.for_paper(PAPERS["a4"]))
    # A fresh error: nothing chains back to the caught one and its traceback.
    assert e.value.__cause__ is None and e.value.__context__ is None
