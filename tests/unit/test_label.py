# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import dataclasses
from functools import cache

import numpy as np
import pytest
from PIL import Image, ImageFilter

from optar.decoder import locate_page
from optar.encoder import encode
from optar.errors import DecodeError, FormatError
from optar.font import glyph_strip, label_text
from optar.format import PAPERS, PageFormat
from optar.imageio import read_scan
from optar.label import (
    MIN_LABEL_CONFIDENCE,
    MIN_LABEL_MARGIN,
    LabelInfo,
    LabelReading,
    label_capacity,
    parse_label,
    printed_label,
    read_label,
)
from tests.helpers import DEGRADED, fake_scan, save_scan, seeded_bytes

PRINTABLE = "".join(chr(c) for c in range(32, 127))
# Every hexadecimal digit and the tag's punctuation, which the document tag relies on.
TAG_LABEL = "[199999:3f9a2c1b] 0123456789abcdef:[] holiday-photos.tar"
A4 = PageFormat.for_paper(PAPERS["a4"])
LETTER = PageFormat.for_paper(PAPERS["letter"])
FORMATS = {"a4": A4, "letter": LETTER}
SCALE, MARGIN = 3, 60  # of the scans built here without DEGRADED


# ---- scans -----------------------------------------------------------------


@cache
def tag_page(fmt: PageFormat) -> np.ndarray:
    """Page 2 of 2 of a file labelled TAG_LABEL."""
    data = seeded_bytes(3, fmt.net_bits // 8 + 500)
    return list(encode(data, fmt, TAG_LABEL))[1].pixels


def expected(fmt: PageFormat) -> str:
    return printed_label(fmt, label_text(fmt, 2, 2, TAG_LABEL))


def band_box(fmt: PageFormat) -> tuple[slice, slice]:
    """Rows and columns of the label band in a scan made with SCALE and MARGIN."""
    y = MARGIN + (fmt.border + fmt.data_height) * SCALE
    x = MARGIN + fmt.border * SCALE
    return slice(y, y + fmt.text_height * SCALE), slice(x, x + fmt.data_width * SCALE)


def blur_and_noise(scan: np.ndarray, blur: float, noise: float, seed: int) -> np.ndarray:
    out = np.asarray(Image.fromarray(scan).filter(ImageFilter.GaussianBlur(blur)), np.float64)
    out += np.random.default_rng(seed).normal(0.0, noise, out.shape)
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def stroke_scan(fmt: PageFormat, filt: str, size: int) -> np.ndarray:
    """A clean scan whose strokes are thinned (Min) or thickened (Max), as a
    black-and-white scan with a biased threshold would be."""
    f = ImageFilter.MinFilter(size) if filt == "min" else ImageFilter.MaxFilter(size)
    scan = fake_scan(tag_page(fmt), scale=SCALE, margin=MARGIN)
    return np.asarray(Image.fromarray(scan).filter(f), np.uint8)


def shifted_band_scan(fmt: PageFormat, shift: int, seed: int) -> np.ndarray:
    """The label band moved sideways against the cross grid by `shift` scan
    pixels (half a page pixel and more), then blur 0.8 and noise 8."""
    scan = fake_scan(tag_page(fmt), scale=SCALE, margin=MARGIN).copy()
    rows, _ = band_box(fmt)
    scan[rows] = np.roll(scan[rows], shift, axis=1)
    return blur_and_noise(scan, 0.8, 8, seed)


def noisy_scan(fmt: PageFormat, sigma: float, seed: int) -> np.ndarray:
    """Noise on the whole scan; above about sigma 120 the page is seldom located."""
    return fake_scan(tag_page(fmt), scale=SCALE, margin=MARGIN, noise=sigma, seed=seed)


def with_noise_after_locating(grid, sigma: float, seed: int):
    """A grid located on a clean scan (made with SCALE and MARGIN) whose label
    band then gets noise: the reader sees noise the locator would not survive."""
    rows, cols = band_box(grid.fmt)
    rows, cols = slice(rows.start - 6, rows.stop + 6), slice(cols.start - 6, cols.stop + 6)
    cleaned = grid.cleaned.copy()
    band = cleaned[rows, cols].astype(np.float64)
    band += np.random.default_rng(seed).normal(0.0, sigma, band.shape)
    cleaned[rows, cols] = np.clip(np.rint(band), 0, 255).astype(np.uint8)
    return dataclasses.replace(grid, cleaned=cleaned)


def read_or_none(scan: np.ndarray, fmt: PageFormat) -> LabelReading | None:
    """The reading, or None when the page cannot even be located (rejected)."""
    try:
        return read_label(locate_page(scan, fmt))
    except DecodeError:
        return None


def assert_never_wrong_and_reliable(reading: LabelReading | None, want: str) -> None:
    """The gate's invariant: a reading is either rejected or exactly right."""
    if reading is None:
        return
    assert not reading.reliable or reading.text == want, (
        f"wrong text accepted: {reading.text!r} (confidence {reading.confidence:.3f}, "
        f"margin {reading.margin:.3f}), expected {want!r}"
    )


@pytest.fixture(scope="module")
def grid():
    """Located grids, cached for the module: grid(paper, kind)."""
    cache_ = {}

    def get(paper, kind):
        key = paper, kind
        if key not in cache_:
            fmt = FORMATS[paper]
            if kind == "upside-down":
                scan = np.rot90(fake_scan(tag_page(fmt), **DEGRADED["clean1"]), 2)
            else:
                scan = fake_scan(tag_page(fmt), seed=1, fmt=fmt, **DEGRADED[kind])
            cache_[key] = locate_page(scan, fmt)
        return cache_[key]

    return get


# ---- pure functions ----------------------------------------------------------


def test_capacity():
    assert label_capacity(PageFormat(65, 93)) == 98
    assert label_capacity(PageFormat(67, 87)) == 101


def test_space_glyph_is_all_black():
    # Unprinted cells are black; they must read as spaces.
    assert not glyph_strip()[:, :13].any()


def test_printed_label_drops_and_cuts():
    f = PageFormat(65, 93)
    assert printed_label(f, label_text(f, 1, 1, "отпуск.tar")) == "  0-65-93-24-3-1-2-24 1/1 .tar"
    long = label_text(f, 10, 12, "n" * 200)
    assert printed_label(f, long) == ("  0-65-93-24-3-1-2-24 10/12 " + "n" * 200)[:98]
    assert printed_label(f, label_text(f, 1, 0, "")) == "  0-65-93-24-3-1-2-24 1/0"
    assert printed_label(f, "  a\x80b   ") == "  ab"


def test_printed_label_keeps_the_logo_slice_code_in_its_cell():
    # The encoder draws code 127 (part of the logo) in a cell of its own.
    f = PageFormat(65, 93)
    assert printed_label(f, "  ab\x7fcd") == "  ab\x7fcd"
    assert len(printed_label(f, "\x7f" * 200)) == 98


@pytest.mark.parametrize(
    "text,want",
    [
        (
            "  0-65-93-24-3-1-2-24 4/5 [12:3f9a2c1b] a b.tar",
            LabelInfo("0-65-93-24-3-1-2-24", 4, 5, "[12:3f9a2c1b] a b.tar"),
        ),
        ("  0-65-93-24-3-1-2-24 1/0", LabelInfo("0-65-93-24-3-1-2-24", 1, 0, "")),
        ("0-67-87-24-3-1-2-24 10/12 x", LabelInfo("0-67-87-24-3-1-2-24", 10, 12, "x")),
        ("  0-65-93-24-3-1-2-24 1/2 ", LabelInfo("0-65-93-24-3-1-2-24", 1, 2, "")),
        (
            "  0-65-93-24-3-1-2-24 1/2  two  spaces ",
            LabelInfo("0-65-93-24-3-1-2-24", 1, 2, " two  spaces "),
        ),
        ("0-65-93-24-3-1-2-24 99999/99999", LabelInfo("0-65-93-24-3-1-2-24", 99999, 99999, "")),
        ("0-65-93-24-3-1-2-24 7/3 ~", LabelInfo("0-65-93-24-3-1-2-24", 7, 3, "~")),
    ],
)
def test_parse_label(text, want):
    assert parse_label(text) == want


@pytest.mark.parametrize(
    "text",
    [
        "",
        "hello",
        "  0-65-93 1/2 x",
        "  0-65-93-24-3-1-2-24 1-2 x",
        "  0-65-93-24-3-1-2-24 1/2x",
        "  0-65-93-24-3-1-2-24-1 1/2 x",
        "  0-+65-93-24-3-1-2-24 1/2",
        "  -0-65-93-24-3-1-2-24 1/2",
        "  0-65-93-24-3-1-2-24  1/2",
        "  0-65-93-24-3-1-2-24 1/2\n",
        "  0-65-93-24-3-1-2-24 1/2\nx",
        "  0-65-93-24-3-1-2-24 1/2 a\x7fb",
        "  0-65-93-24-3-1-2-24 1/2 é",
        "\t0-65-93-24-3-1-2-24 1/2",
        "  0-65-93-24-3-1-2-24 +1/2",
        "  0-65-93-24-3-1-2-24 1/-2",
        "  0-65-93-24-3-1-2-24 1/",
        "  0-65-93-24-3-1-2-24 /2",
        "  0-65-93-24-3-1-2-24 ١/٢",  # non-ASCII digits
        "  0-65-93-24-3-1-2-24 123456/1",
        "  0-65-93-24-3-1-2-24 1/" + "9" * 5000,
        "  0-65-93-24-3-1-2-24 0/12",  # page 0
        "  0-65-93-24-3-1-2-24 00/12",  # "10/12" misread
        "  0-65-93-24-3-1-2-24 01/12",
        "  0-65-93-24-3-1-2-24 1/012",
        "  0-65-93-24-3-1-2-24 1/00",
        "x 0-65-93-24-3-1-2-24 1/2",
    ],
)
def test_parse_label_rejects(text):
    assert parse_label(text) is None


def test_parse_label_never_raises_on_long_digit_runs():
    assert parse_label("9" * 100_000) is None
    assert parse_label("-".join(["9" * 5000] * 8) + " 1/1") is not None


def test_reliable_needs_both_scores():
    assert LabelReading("x", MIN_LABEL_CONFIDENCE, MIN_LABEL_MARGIN).reliable
    assert not LabelReading("x", MIN_LABEL_CONFIDENCE - 0.01, 1.0).reliable
    assert not LabelReading("x", 1.0, MIN_LABEL_MARGIN - 0.01).reliable


# ---- reading good scans ------------------------------------------------------


@pytest.mark.parametrize(
    "paper,name",
    [
        ("a4", "clean3"),
        ("letter", "clean3"),
        ("a4", "combined"),
        pytest.param("letter", "combined", marks=pytest.mark.slow),
    ],
)
def test_reads_tag_label(grid, paper, name):
    fmt = FORMATS[paper]
    reading = read_label(grid(paper, name))
    assert reading.text == expected(fmt)
    assert reading.reliable
    assert parse_label(reading.text) == LabelInfo(fmt.to_string(), 2, 2, TAG_LABEL)


def test_clean_scan_reads_perfectly(grid):
    reading = read_label(grid("a4", "clean3"))
    assert reading.confidence == 1.0 and reading.margin == 1.0


def test_wrong_text_height_is_a_format_error(grid):
    g = dataclasses.replace(grid("a4", "clean3"), fmt=PageFormat(65, 93, text_height=20))
    with pytest.raises(FormatError, match="label band"):
        read_label(g)


@pytest.mark.slow
@pytest.mark.parametrize("paper", ["a4", "letter"])
@pytest.mark.parametrize("name", list(DEGRADED))
def test_reads_label_from_degraded_scans(tmp_path, paper, name):
    fmt = FORMATS[paper]
    path = tmp_path / "s.png"
    save_scan(path, fake_scan(tag_page(fmt), seed=1, fmt=fmt, **DEGRADED[name]))
    reading = read_label(locate_page(read_scan(path), fmt))
    assert reading.text == expected(fmt)
    assert reading.reliable


# Two pages whose labels together show every printable character, each filling
# all label_capacity cells (the free text is rotated so the part the first page
# cuts off appears on the second).
def full_width_case(offset, name):
    fmt = A4
    label = PRINTABLE[offset:] + PRINTABLE[:offset]
    want = printed_label(fmt, label_text(fmt, 1, 1, label))
    assert len(want) == label_capacity(fmt) == 98
    page = next(encode(b"x", fmt, label)).pixels
    reading = read_label(locate_page(fake_scan(page, seed=2, fmt=fmt, **DEGRADED[name]), fmt))
    assert reading.text == want
    assert reading.reliable


@pytest.mark.parametrize("offset", [0, 48])
def test_full_width_label_reads_back(offset):
    full_width_case(offset, "clean1")


@pytest.mark.slow
@pytest.mark.parametrize("offset", [0, 48])
@pytest.mark.parametrize("name", ["clean3", "combined"])
def test_full_width_label_reads_back_at_scale_3(offset, name):
    full_width_case(offset, name)


def test_full_width_pages_cover_every_printable_character():
    seen = set()
    for offset in (0, 48):
        label = PRINTABLE[offset:] + PRINTABLE[:offset]
        seen |= set(printed_label(A4, label_text(A4, 1, 1, label)))
    assert seen == set(PRINTABLE)


def test_logo_slice_code_takes_a_cell():
    fmt = A4
    want = printed_label(fmt, label_text(fmt, 1, 1, "ab\x7fcd"))
    assert want.endswith(" 1/1 ab\x7fcd")
    page = next(encode(b"x", fmt, "ab\x7fcd")).pixels
    text = read_label(locate_page(fake_scan(page, **DEGRADED["clean1"]), fmt)).text
    assert len(text) == len(want)
    assert text[:-3] == want[:-3] and text[-2:] == "cd"
    assert text[-3] != "\x7f"


# ---- misreads must be rejected -------------------------------------------------


@pytest.mark.parametrize("filt", ["min", "max"])
def test_stroke_width_change_is_rejected_or_exact(filt):
    reading = read_or_none(stroke_scan(A4, filt, 3), A4)
    assert_never_wrong_and_reliable(reading, expected(A4))


def test_shifted_band_is_rejected_or_exact():
    reading = read_or_none(shifted_band_scan(LETTER, 2, seed=1), LETTER)
    assert_never_wrong_and_reliable(reading, expected(LETTER))


@pytest.mark.parametrize("paper", ["a4", "letter"])
@pytest.mark.parametrize("sigma", [90, 120, 150, 170, 190, 200])
@pytest.mark.parametrize("seed", [1, 2])
def test_heavy_noise_is_rejected_or_exact(grid, paper, sigma, seed):
    reading = read_label(with_noise_after_locating(grid(paper, "clean3"), sigma, seed))
    assert_never_wrong_and_reliable(reading, expected(FORMATS[paper]))


# Found while choosing the thresholds: noise turns a blank cell after the text
# into a sparse glyph ("`" or ".") whose margin clears MIN_LABEL_MARGIN; the
# cell's low confidence is what rejects it.
@pytest.mark.parametrize("sigma,seed", [(90, 7), (105, 73), (120, 16), (135, 7)])
def test_spurious_glyph_after_the_text_is_rejected(grid, sigma, seed):
    reading = read_label(with_noise_after_locating(grid("letter", "clean3"), sigma, seed))
    assert reading.text.startswith(expected(LETTER)) and reading.text != expected(LETTER)
    assert reading.margin >= MIN_LABEL_MARGIN
    assert not reading.reliable


@pytest.mark.slow
@pytest.mark.parametrize("paper", ["a4", "letter"])
@pytest.mark.parametrize("sigma", [60, 90, 120, 150, 170, 190, 200, 250])
def test_heavy_noise_after_locating_sweep(grid, paper, sigma):
    g = grid(paper, "clean3")
    for seed in range(3, 40):
        reading = read_label(with_noise_after_locating(g, sigma, seed))
        assert_never_wrong_and_reliable(reading, expected(FORMATS[paper]))


@pytest.mark.slow
@pytest.mark.parametrize("paper", ["a4", "letter"])
@pytest.mark.parametrize("filt", ["min", "max"])
@pytest.mark.parametrize("size", [3, 5, 7])
def test_stroke_width_sweep(paper, filt, size):
    fmt = FORMATS[paper]
    assert_never_wrong_and_reliable(read_or_none(stroke_scan(fmt, filt, size), fmt), expected(fmt))


@pytest.mark.slow
@pytest.mark.parametrize("paper", ["a4", "letter"])
@pytest.mark.parametrize("shift", [-2, -1, 1, 2])
def test_shifted_band_sweep(paper, shift):
    fmt = FORMATS[paper]
    reading = read_or_none(shifted_band_scan(fmt, shift, seed=3), fmt)
    assert_never_wrong_and_reliable(reading, expected(fmt))


@pytest.mark.slow
@pytest.mark.parametrize("paper", ["a4", "letter"])
@pytest.mark.parametrize("sigma", [120, 150, 170, 190, 200])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_heavy_noise_on_scan_sweep(paper, sigma, seed):
    fmt = FORMATS[paper]
    reading = read_or_none(noisy_scan(fmt, sigma, seed), fmt)
    assert_never_wrong_and_reliable(reading, expected(fmt))


# ---- non-labels must be rejected -----------------------------------------------


def test_upside_down_page_is_not_reliable(grid):
    assert not read_label(grid("a4", "upside-down")).reliable


# A Letter scan at scale 1 cannot even be located as A4; at scale 3 it can, and
# its "label" then reads as empty or nearly so.
@pytest.mark.parametrize(
    "paper,other,name",
    [
        ("letter", "a4", "clean3"),
        ("a4", "letter", "clean1"),
        pytest.param("letter", "a4", "clean1", marks=pytest.mark.slow),
        pytest.param("a4", "letter", "clean3", marks=pytest.mark.slow),
        pytest.param("letter", "a4", "combined", marks=pytest.mark.slow),
        pytest.param("a4", "letter", "combined", marks=pytest.mark.slow),
    ],
)
def test_page_located_with_the_other_format_is_not_reliable(paper, other, name):
    scan = fake_scan(tag_page(FORMATS[paper]), seed=1, fmt=FORMATS[paper], **DEGRADED[name])
    reading = read_or_none(scan, FORMATS[other])
    assert reading is None or not reading.reliable


@pytest.mark.slow
@pytest.mark.parametrize("paper,other", [("letter", "a4"), ("a4", "letter")])
def test_upside_down_page_located_with_the_other_format_is_not_reliable(paper, other):
    scan = np.rot90(fake_scan(tag_page(FORMATS[paper]), scale=SCALE, margin=MARGIN), 2)
    reading = read_or_none(scan, FORMATS[other])
    assert reading is None or not reading.reliable


@pytest.mark.slow
@pytest.mark.parametrize("paper", ["a4", "letter"])
@pytest.mark.parametrize("name", list(DEGRADED))
def test_upside_down_degraded_pages_are_not_reliable(paper, name):
    fmt = FORMATS[paper]
    scan = np.rot90(fake_scan(tag_page(fmt), seed=1, fmt=fmt, **DEGRADED[name]), 2)
    reading = read_or_none(scan, fmt)
    assert reading is None or not reading.reliable


@pytest.mark.parametrize("fill", ["white", "black", "random"])
def test_blank_or_random_band_is_not_reliable(grid, fill):
    fmt = A4
    g = grid("a4", "clean3")
    rows, cols = band_box(fmt)
    cleaned = g.cleaned.copy()
    if fill == "random":
        dots = np.random.default_rng(5).integers(0, 2, (fmt.text_height, fmt.data_width)) * 255
        cleaned[rows, cols] = np.kron(dots, np.ones((SCALE, SCALE))).astype(np.uint8)
    else:
        cleaned[rows, cols] = 255 if fill == "white" else 0
    reading = read_label(dataclasses.replace(g, cleaned=cleaned))
    assert not reading.reliable
    if fill == "black":
        assert reading == LabelReading("", 0.0, 0.0)
