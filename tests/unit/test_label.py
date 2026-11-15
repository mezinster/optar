# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import numpy as np
import pytest

from optar.decoder import locate_page
from optar.encoder import encode
from optar.font import glyph_strip, label_text
from optar.format import PAPERS, PageFormat
from optar.imageio import read_scan
from optar.label import (
    MIN_LABEL_CONFIDENCE,
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
    assert printed_label(f, "  a\x7fb   ") == "  ab"


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
        ("  0-65-93-24-3-1-2-24 1/2  two  spaces ",
         LabelInfo("0-65-93-24-3-1-2-24", 1, 2, " two  spaces ")),
        ("0-65-93-24-3-1-2-24 99999/99999", LabelInfo("0-65-93-24-3-1-2-24", 99999, 99999, "")),
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
        "\t0-65-93-24-3-1-2-24 1/2",
        "  0-65-93-24-3-1-2-24 +1/2",
        "  0-65-93-24-3-1-2-24 1/-2",
        "  0-65-93-24-3-1-2-24 1/",
        "  0-65-93-24-3-1-2-24 /2",
        "  0-65-93-24-3-1-2-24 ١/٢",  # non-ASCII digits
        "  0-65-93-24-3-1-2-24 123456/1",
        "  0-65-93-24-3-1-2-24 1/" + "9" * 5000,
        "x 0-65-93-24-3-1-2-24 1/2",
    ],
)
def test_parse_label_rejects(text):
    assert parse_label(text) is None


def test_parse_label_never_raises_on_long_digit_runs():
    assert parse_label("9" * 100_000) is None
    assert parse_label("-".join(["9" * 5000] * 8) + " 1/1") is not None


@pytest.fixture(scope="module")
def degraded_scan(tmp_path_factory):
    cache = {}

    def get(paper, name):
        if (paper, name) not in cache:
            fmt = PageFormat.for_paper(PAPERS[paper])
            data = seeded_bytes(3, fmt.net_bits // 8 + 500)
            page = list(encode(data, fmt, TAG_LABEL))[1]
            path = tmp_path_factory.mktemp("scan") / "s.png"
            save_scan(path, fake_scan(page.pixels, seed=1, fmt=fmt, **DEGRADED[name]))
            cache[paper, name] = fmt, read_scan(path)
        return cache[paper, name]

    return get


@pytest.mark.parametrize("paper", ["a4", "letter"])
@pytest.mark.parametrize("name", list(DEGRADED))
def test_reads_label_from_degraded_scans(degraded_scan, paper, name):
    fmt, scan = degraded_scan(paper, name)
    reading = read_label(locate_page(scan, fmt))
    assert isinstance(reading, LabelReading)
    assert reading.text == printed_label(fmt, label_text(fmt, 2, 2, TAG_LABEL))
    assert reading.confidence >= MIN_LABEL_CONFIDENCE
    assert parse_label(reading.text) == LabelInfo(fmt.to_string(), 2, 2, TAG_LABEL)


@pytest.mark.parametrize("paper", ["a4", "letter"])
@pytest.mark.parametrize("name", ["clean3", "combined"])
def test_upside_down_page_has_low_confidence(degraded_scan, paper, name):
    fmt, scan = degraded_scan(paper, name)
    assert read_label(locate_page(np.rot90(scan, 2), fmt)).confidence < MIN_LABEL_CONFIDENCE


def test_upside_down_page_from_brief_has_low_confidence():
    fmt = PageFormat(65, 93)
    page = next(encode(seeded_bytes(1, 5000), fmt, "name")).pixels
    scan = np.rot90(fake_scan(page, scale=3, margin=60), 2)
    assert read_label(locate_page(scan, fmt)).confidence < MIN_LABEL_CONFIDENCE


# Two pages whose labels together show every printable character, each filling
# all label_capacity cells (the free text is rotated so the parts the first page
# cuts off appear on the second).
@pytest.mark.parametrize("offset", [0, 48])
@pytest.mark.parametrize("name", ["clean3", "combined"])
def test_full_width_label_reads_back(offset, name):
    fmt = PageFormat(65, 93)
    label = PRINTABLE[offset:] + PRINTABLE[:offset]
    text = label_text(fmt, 1, 1, label)
    want = printed_label(fmt, text)
    assert len(want) == label_capacity(fmt) == 98
    page = next(encode(b"x", fmt, label)).pixels
    reading = read_label(locate_page(fake_scan(page, seed=2, fmt=fmt, **DEGRADED[name]), fmt))
    assert reading.text == want
    assert reading.confidence >= MIN_LABEL_CONFIDENCE


def test_full_width_pages_cover_every_printable_character():
    fmt = PageFormat(65, 93)
    seen = set()
    for offset in (0, 48):
        label = PRINTABLE[offset:] + PRINTABLE[:offset]
        seen |= set(printed_label(fmt, label_text(fmt, 1, 1, label)))
    assert seen == set(PRINTABLE)
