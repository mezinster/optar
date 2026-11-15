# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import dataclasses
from functools import cache

import numpy as np
import pytest
from PIL import Image, ImageFilter

from optar.decoder import locate_page
from optar.encoder import encode
from optar.errors import DecodeError, FormatError
from optar.font import GLYPH_CELLS, glyph_strip, label_text, render_label
from optar.format import PAPERS, TEXT_WIDTH, PageFormat
from optar.imageio import read_scan
from optar.label import (
    MAX_INK_BIAS,
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


@cache
def clean_grid(fmt: PageFormat):
    """tag_page scanned cleanly with SCALE and MARGIN, located."""
    return locate_page(fake_scan(tag_page(fmt), scale=SCALE, margin=MARGIN), fmt)


@pytest.fixture(scope="module")
def grid():
    """Located grids, cached for the module: grid(paper, kind)."""
    cache_ = {}

    def get(paper, kind):
        key = paper, kind
        if key not in cache_:
            fmt = FORMATS[paper]
            if kind == "clean3":
                cache_[key] = clean_grid(fmt)
                return cache_[key]
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


def test_reliable_needs_every_score():
    c, m, b = MIN_LABEL_CONFIDENCE, MIN_LABEL_MARGIN, MAX_INK_BIAS
    assert LabelReading("x", c, m, b, b, 0).reliable
    assert not LabelReading("x", c - 0.01, 1.0, 0.0, 0.0, 0).reliable
    assert not LabelReading("x", 1.0, m - 0.01, 0.0, 0.0, 0).reliable
    assert not LabelReading("x", 1.0, 1.0, b + 0.01, 0.0, 0).reliable
    assert not LabelReading("x", 1.0, 1.0, 0.0, b + 0.01, 0).reliable
    assert not LabelReading("x", 1.0, 1.0, 0.0, 0.0, 1).reliable


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
    assert reading.ink_loss == reading.ink_gain == 0.0 and reading.doubtful_cells == 0


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


def test_shifted_band_is_rejected_or_exact():
    reading = read_or_none(shifted_band_scan(LETTER, 2, seed=1), LETTER)
    assert_never_wrong_and_reliable(reading, expected(LETTER))


@pytest.mark.parametrize("paper", ["a4", "letter"])
@pytest.mark.parametrize("sigma", [90, 120, 150, 170, 190, 200])
@pytest.mark.parametrize("seed", [1, 2])
def test_heavy_noise_is_rejected_or_exact(grid, paper, sigma, seed):
    reading = read_label(with_noise_after_locating(grid(paper, "clean3"), sigma, seed))
    assert_never_wrong_and_reliable(reading, expected(FORMATS[paper]))


# Found while choosing the thresholds: heavy noise turns a blank cell after
# the text into a sparse glyph ("`" or ".") whose margin clears
# MIN_LABEL_MARGIN. Whatever the noise does at these seeds, such a reading
# must not be accepted.
@pytest.mark.parametrize("sigma", [90, 105, 120, 135])
def test_spurious_glyph_after_the_text_is_rejected(grid, sigma):
    g = grid("letter", "clean3")
    for seed in (7, 16, 73, *range(20)):
        reading = read_label(with_noise_after_locating(g, sigma, seed))
        assert_never_wrong_and_reliable(reading, expected(LETTER))


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


# ---- families of misreads found in review ---------------------------------------
#
# Each family perturbs the label band in a way a real scan can, and found
# wrong readings that the confidence and margin alone accepted. The default
# tests check, at fixed seeds, that families (a) and (e) now give no wrong
# reliable reading. The gate is a filter, not a guarantee: the slow tests
# bound the measured share of wrong readings accepted and check that none of
# them is a well-formed substitution (a digit for a digit, a hex digit for a
# hex digit) in the part of the label that identifies a page, which would
# still parse and match. Those are what a check code in the tag is for.

# Labels rich in sparse glyphs, hex digits and the tag's punctuation.
FAMILY_LABELS = [
    (3, 8, "[3880860:9b0d6853] 0 6 8 9 3 5 1 7 b d.tar"),
    (13, 18, "[58:6083b9d1] 0689:3517bd 6 8"),
    (1, 1, "[5:0b3d8e9f] notes."),
    (2, 3, "[61:9b8d0e3f] a-b-"),
    (4, 5, "[3:8e9f0b3d] it`"),
    (2, 3, "[61:9b8d0e3f] it`s a`b"),
    (1, 2, "[7:3d0b9e8f] x.y,z'w"),
    (4, 5, "[3:8e9f0b3d] a-b_c:d;e"),
]
HEX = set("0123456789abcdef")
SPECK_SEEDS = 6  # seed 5 gave a wrong reading the old gate accepted


def labelled_page(fmt: PageFormat, page: int, total: int, name: str) -> tuple[np.ndarray, str]:
    """tag_page with its label band redrawn for page/total and name, and the
    text that band shows."""
    text = label_text(fmt, page, total, name)
    pixels = tag_page(fmt).copy()
    top = fmt.border + fmt.data_height
    pixels[top : top + fmt.text_height, fmt.border : fmt.border + fmt.data_width] = render_label(
        fmt, text
    )
    return pixels, printed_label(fmt, text)


@cache
def located(fmt: PageFormat, page: int, total: int, name: str):
    """A clean scan of labelled_page as located: (grid, text). Only the label
    band differs from tag_page, so clean_grid is reused with its band redrawn
    rather than locating the page again."""
    pixels, want = labelled_page(fmt, page, total, name)
    g = clean_grid(fmt)
    rows, cols = band_box(fmt)
    rows, cols = slice(rows.start - 12, rows.stop + 12), slice(cols.start - 12, cols.stop + 12)
    cleaned = g.cleaned.copy()
    cleaned[rows, cols] = fake_scan(pixels, scale=SCALE, margin=MARGIN)[rows, cols]
    return dataclasses.replace(g, cleaned=cleaned), want


def perturbed_band(grid, perturb, seed: int | tuple[int, ...]):
    """The grid with its label band (and 12 scan pixels around it) passed
    through perturb(band, rng); the crosses and the grid stay as located."""
    rows, cols = band_box(grid.fmt)
    rows, cols = slice(rows.start - 12, rows.stop + 12), slice(cols.start - 12, cols.stop + 12)
    cleaned = grid.cleaned.copy()
    cleaned[rows, cols] = perturb(cleaned[rows, cols].copy(), np.random.default_rng(seed))
    return dataclasses.replace(grid, cleaned=cleaned)


def correlated_noise(shape, rng, sigma: float) -> np.ndarray:
    """Gaussian noise blurred over 2 scan pixels, scaled to standard deviation sigma."""
    n = rng.normal(0.0, 1.0, shape)
    im = Image.fromarray(np.clip(n * 40 + 128, 0, 255).astype(np.uint8))
    im = np.asarray(im.filter(ImageFilter.GaussianBlur(2.0)), np.float64) - 128
    return im / (im.std() + 1e-9) * sigma


def blotchy(sigma: float):
    def perturb(band, rng):
        out = band + correlated_noise(band.shape, rng, sigma)
        return np.clip(np.rint(out), 0, 255).astype(np.uint8)

    return perturb


def gradient(amplitude: float, sigma: float):
    """Brightness falling off across the band by `amplitude` grey levels, plus noise."""

    def perturb(band, rng):
        ramp = np.linspace(-amplitude / 2, amplitude / 2, band.shape[1])[None, :]
        out = band * (1 - amplitude / 400) + ramp + rng.normal(0.0, sigma, band.shape)
        return np.clip(np.rint(out), 0, 255).astype(np.uint8)

    return perturb


def offset_x(dx: float):
    """The band moved dx scan pixels sideways (bilinear), then blur 0.8 and noise 8."""

    def perturb(band, rng):
        im = Image.fromarray(band)
        im = im.transform(im.size, Image.AFFINE, (1, 0, -dx, 0, 1, 0), resample=Image.BILINEAR,
                          fillcolor=255)
        return blur_and_noise(np.asarray(im, np.uint8), 0.8, 8, int(rng.integers(1 << 31)))

    return perturb


def well_formed_substitutions(text: str, want: str) -> list[tuple[int, str, str]]:
    """Digit-for-digit or hex-for-hex substitutions in the format string, the
    page numbers or the tag: misreads that would still parse and match."""
    end = want.index("]") + 1
    return [(i, a, b) for i, (a, b) in enumerate(zip(want, text, strict=False))
            if i < end and a != b and a in HEX and b in HEX]


def measure(perturb_for, seeds) -> tuple[int, list[tuple[str, str, LabelReading]]]:
    """Readings of FAMILY_LABELS on both papers, each perturbed by
    perturb_for(fmt, text): how many, and the wrong ones that were accepted."""
    count, accepted_wrong = 0, []
    for paper, fmt in enumerate((A4, LETTER)):
        for label, (page, total, name) in enumerate(FAMILY_LABELS):
            g, want = located(fmt, page, total, name)
            perturb = perturb_for(fmt, want)
            for seed in seeds:
                reading = read_label(perturbed_band(g, perturb, (seed, label, paper)))
                count += 1
                if reading.reliable and reading.text != want:
                    accepted_wrong.append((reading.text, want, reading))
    return count, accepted_wrong


def assert_rate(perturb_for, bound: float) -> None:
    count, wrong = measure(perturb_for, RATE_SEEDS)
    for text, want, _ in wrong:
        assert not well_formed_substitutions(text, want), f"{text!r} accepted for {want!r}"
    assert len(wrong) / count <= bound, [(t, r.confidence, r.margin) for t, _, r in wrong]


def thin(image: np.ndarray, seed: int) -> np.ndarray:
    """Strokes thinned (MinFilter 3), then blur 1.0 and noise 8."""
    image = np.asarray(Image.fromarray(image).filter(ImageFilter.MinFilter(3)), np.uint8)
    return blur_and_noise(image, 1.0, 8, seed)


# (a) Thinned strokes make a sparse glyph vanish. When it was the last
# character its cell lies after the text and nothing used to score it; the
# surviving glyphs come out thin, which the ink loss measures.
THIN_LABELS = ["[61:9b8d0e3f] it`s a`b", "[61:9b8d0e3f] it`"]


@pytest.mark.parametrize("name", THIN_LABELS)
@pytest.mark.parametrize("seed", [1, 2])
def test_thinned_scan_is_rejected_or_exact(name, seed):
    # The whole scan thinned, then located.
    pixels, want = labelled_page(A4, 2, 3, name)
    scan = thin(fake_scan(pixels, scale=SCALE, margin=MARGIN), seed)
    assert_never_wrong_and_reliable(read_or_none(scan, A4), want)


@pytest.mark.slow
@pytest.mark.parametrize("paper", ["a4", "letter"])
@pytest.mark.parametrize("name", THIN_LABELS)
def test_thinned_scan_sweep(paper, name):
    fmt = FORMATS[paper]
    pixels, want = labelled_page(fmt, 2, 3, name)
    clean = fake_scan(pixels, scale=SCALE, margin=MARGIN)
    for seed in range(3, 9):
        assert_never_wrong_and_reliable(read_or_none(thin(clean, seed), fmt), want)


def test_thinned_band_is_rejected_or_exact():
    # Only the band thinned, on a grid located once: cheap, so many seeds.
    def perturb(band, rng):
        return thin(band, int(rng.integers(1 << 31)))

    for paper in ("a4", "letter"):
        for name in THIN_LABELS:
            g, want = located(FORMATS[paper], 2, 3, name)
            for seed in range(10):
                assert_never_wrong_and_reliable(read_label(perturbed_band(g, perturb, seed)), want)


# (e) White specks of 2-4 page pixels in the band. A speck covering part of a
# sparse glyph's place in a blank cell read as that glyph ("`", "'") with a
# clear margin; such a glyph must now beat the blank by its clear lead. A
# speck the size and place of a whole "." or "`" is that glyph to any reader
# of the cell and is accepted (test_speck_in_a_blank_cell_rate).
def speck(fmt: PageFormat, want: str, blank_cells_only: bool):
    """Perturbation: a white square of 2-4 page pixels, page-pixel aligned, at
    a random place over the printed text (or in a random blank cell after the
    page numbers), then blotchy noise of sigma 25."""
    logo = glyph_strip().shape[1] - TEXT_WIDTH * GLYPH_CELLS
    blanks = [i for i in range(want.index("/"), len(want)) if want[i] == " "]

    def perturb(band, rng):
        k = int(rng.integers(2, 5))
        y = 12 + SCALE * int(rng.integers(0, fmt.text_height - k + 1))
        if blank_cells_only:
            x = TEXT_WIDTH * int(rng.choice(blanks)) + int(rng.integers(0, TEXT_WIDTH - k + 1))
        else:
            x = int(rng.integers(0, TEXT_WIDTH * len(want) - k + 1))
        x = 12 + SCALE * (logo + x)
        band[y : y + SCALE * k, x : x + SCALE * k] = 255
        return blotchy(25)(band, rng)

    return perturb


@pytest.mark.parametrize("paper", ["a4", "letter"])
def test_speck_is_rejected_or_exact(paper):
    fmt = FORMATS[paper]
    for label, (page, total, name) in enumerate(FAMILY_LABELS):
        g, want = located(fmt, page, total, name)
        perturb = speck(fmt, want, blank_cells_only=False)
        for seed in range(SPECK_SEEDS):
            reading = read_label(perturbed_band(g, perturb, (seed, label, int(paper == "letter"))))
            assert_never_wrong_and_reliable(reading, want)


# The rest are filters, not guarantees. Each test reads FAMILY_LABELS on both
# papers at RATE_SEEDS seeds (480 readings) and bounds the share of wrong
# readings accepted. The rates in the comments were measured with this code
# over seeds 0-99 (1600 readings; "before" is the confidence and margin gate
# alone). None of the wrong readings accepted was a well-formed substitution.
RATE_SEEDS = range(30)


@pytest.mark.slow
@pytest.mark.parametrize("blank_cells_only,bound", [
    (False, 0.005),  # before 7/1600, now 2/1600 (0.13%): a whole "." in a blank cell
    (True, 0.03),  # before 57/1600, now 21/1600 (1.3%): a whole "." or "`"
])
def test_speck_rate(blank_cells_only, bound):
    def perturb_for(fmt, want):
        return speck(fmt, want, blank_cells_only)

    assert_rate(perturb_for, bound)


# (b) Correlated (blotchy) noise. What passes: ":" read as ";" or ".", "."
# as "," or blank, a blank as ".".
@pytest.mark.slow
@pytest.mark.parametrize("sigma,bound", [
    (60, 0.005),  # before 5/1600, now 2/1600 (0.13%)
    (70, 0.01),  # before 17/1600, now 6/1600 (0.38%)
    (80, 0.005),  # before 31/1600, now 2/1600 (0.13%); most readings are rejected
])
def test_blotchy_noise_rate(sigma, bound):
    assert_rate(lambda fmt, want: blotchy(sigma), bound)


# (c) A brightness gradient across the band plus noise. The global threshold
# thins the strokes on the dark side, so nearly every reading is now rejected.
@pytest.mark.slow
@pytest.mark.parametrize("amplitude,sigma,bound", [
    (120, 30, 0.005),  # before 3/1600, now 0/1600
    (100, 40, 0.005),  # before 0/1600, now 0/1600
])
def test_gradient_rate(amplitude, sigma, bound):
    assert_rate(lambda fmt, want: gradient(amplitude, sigma), bound)


# (d) The band sampled half a page pixel off in x, between two columns.
@pytest.mark.slow
@pytest.mark.parametrize("dx,bound", [
    (1.5, 0.005),  # before 1/1600, now 0/1600
    (-1.5, 0.005),  # before 1/1600, now 0/1600
])
def test_half_pixel_offset_rate(dx, bound):
    assert_rate(lambda fmt, want: offset_x(dx), bound)


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
