# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The slow reader (decoder.soft) on a small custom page scanned too coarsely."""

import dataclasses
import time
from functools import cache
from unittest import mock

import numpy as np
import pytest

import optar.identify
from optar import DOT_SIZES, PAPERS, PARITY, encode
from optar.container import page_payload, plan_for, read_header, wrap
from optar.decoder import decode_located, locate_page, soft
from optar.errors import DecodeError, IdentifyError
from optar.format import Layout
from optar.identify import ScanIdentity, identify_any, identify_scan
from tests.helpers import seeded_bytes, simulate_scan

# A page of 20 x 28 crosses (466 x 682 dots): big enough that most of its
# 352 regions fit their own filter, small enough to read in about a second.
LAYOUT = Layout(PAPERS["a4"], DOT_SIZES["standard"], 20, 28, 19.2, 17.4)
FMT = LAYOUT.fmt
# Measured: at 290 dpi with blur 1.6 the ordinary reader leaves about 370
# of the 11749 symbols uncorrectable on the enlarged scan (about 1000 at the
# scan's own size); with blur 1.8 about 2800 at the scan's own size, so its
# header copies are gone and identify_scan fails.
COARSE = dict(dpi=290, blur=1.6)
COARSER = dict(dpi=290, blur=1.8)


@cache
def document():
    """A two-page version-1 document of LAYOUT: (data, stream, page images)."""
    one = plan_for(1, FMT, PARITY["high"]).data_bytes
    data = seeded_bytes(21, one + one // 2)
    stream = wrap(data, "coarse.bin", FMT, PARITY["high"])
    images = tuple(p.pixels for p in encode(stream, FMT, "coarse.bin"))
    assert len(images) == 2
    return data, stream, images


def page_bits(stream, page):
    """The payload bits of a page (1-based) of a stream."""
    bits = np.unpackbits(np.frombuffer(stream, np.uint8))
    want = bits[(page - 1) * FMT.net_bits : page * FMT.net_bits]
    return np.pad(want, (0, FMT.net_bits - len(want)))


@cache
def scan(dpi, blur, turns=0, page=2):
    img = simulate_scan(document()[2][page - 1], LAYOUT, dpi, blur=blur, quarter_turns=turns,
                        seed=page)  # fmt: skip
    img.flags.writeable = False
    return img


def enlarged(img):
    """The upright scan enlarged as identify_coarse does it, and its grid."""
    corners = optar.identify._outline(img)
    big, _ = soft._enlarge(img, soft._enlargement(corners, FMT))
    return big, locate_page(big, FMT)


@pytest.fixture
def only_layout():
    """identify_scan and identify_coarse try LAYOUT only."""
    with mock.patch.object(optar.identify, "_papers_by_shape", lambda c: [PAPERS["a4"]]), \
            mock.patch.object(optar.identify, "_layouts_by_shape", lambda c, p: [LAYOUT]):
        yield


def test_read_soft_reads_a_scan_the_ordinary_reader_cannot():
    big, grid = enlarged(scan(**COARSE))
    ordinary = decode_located(grid, detail=True)
    assert ordinary.stats.uncorrectable > 100
    result = soft.read_soft(grid, big)
    assert np.array_equal(result.bits, page_bits(document()[1], 2))
    assert result.bits.dtype == np.uint8 and result.bits.shape == (FMT.net_bits,)
    assert result.lost_symbols is not None and result.lost_symbols.dtype == np.int64
    assert len(result.lost_symbols) == 0 and result.stats.uncorrectable == 0
    assert result.corrected_bits is None and result.grid is grid
    assert sum(result.stats.error_histogram) == FMT.fec_syms == result.stats.symbols
    assert read_header(page_payload(result, FMT).data) is not None


def test_read_soft_matches_the_ordinary_reader_on_a_clean_scan():
    img = scan(600, 1.0)
    grid = locate_page(img, FMT)
    ordinary = decode_located(grid, detail=True)
    assert ordinary.stats.uncorrectable == 0
    result = soft.read_soft(grid, img)
    assert np.array_equal(result.bits, ordinary.bits)
    assert np.array_equal(result.bits, page_bits(document()[1], 2))


def test_read_soft_survives_a_page_with_nothing_to_learn_from():
    _, grid = enlarged(scan(**COARSE))
    shape = grid.cleaned.shape
    rng = np.random.default_rng(3)
    grey = np.full(shape, 128, np.uint8)
    framed = grey.copy()
    framed[40:-40, 40:-40] = 0
    framed[60:-60, 60:-60] = 128
    noise = rng.integers(0, 256, shape, dtype=np.uint8)
    for picture in (grey, framed, noise):
        g = dataclasses.replace(grid, cleaned=picture)
        try:
            result = soft.read_soft(g, picture)
        except DecodeError:
            continue
        assert result.bits.shape == (FMT.net_bits,)
    # Nothing known at all: the fit refuses rather than dividing by nothing.
    big, grid = enlarged(scan(**COARSE))
    with mock.patch.object(soft, "SEED_ERRORS", -1), pytest.raises(DecodeError):
        soft.read_soft(grid, big)


def check_slow_identity(ident, turns, dpi, page=2):
    data = document()[0]
    assert isinstance(ident, ScanIdentity)
    assert ident.reader == "slow" and ident.layout is LAYOUT and ident.fmt == FMT
    assert ident.paper is PAPERS["a4"] and ident.rotation == turns
    assert (ident.page, ident.total, ident.tag, ident.name) == (page, 2, None, "")
    assert ident.header is not None and ident.header.size == len(data)
    assert (ident.header.page, ident.header.total) == (page, 2)
    assert read_header(ident.payload.data) == ident.header
    assert ident.result is not None and ident.result.grid is ident.grid
    again = page_payload(ident.result, FMT)
    assert ident.payload.data == again.data and not ident.payload.erased.any()
    assert ident.scan_dpi == pytest.approx(dpi, rel=0.05)


@pytest.mark.parametrize("turns", [0, 1])
def test_identify_coarse_finds_a_version_1_page(only_layout, turns):
    img = scan(**COARSER, turns=turns)
    with pytest.raises(IdentifyError):
        identify_scan(img)
    ident = soft.identify_coarse(img)
    check_slow_identity(ident, turns, COARSER["dpi"])
    bits = page_bits(document()[1], 2)
    # A few bits may be wrong at this blur: the document's parity repairs them.
    assert np.count_nonzero(ident.result.bits != bits) < FMT.net_bits // 1000


def damaged_headers(stream):
    """The stream with every header copy of page 2 overwritten."""
    bits = np.unpackbits(np.frombuffer(stream, np.uint8)).copy()
    page_bytes = FMT.net_bits // 8
    for start in optar.container._header_offsets(page_bytes):
        first = FMT.net_bits + 8 * start
        bits[first : first + 8 * optar.container.HEADER_SIZE] ^= 1
    return np.packbits(bits).tobytes()


@pytest.mark.parametrize("kind", ["unwrapped", "damaged"])
def test_identify_coarse_refuses_a_page_without_a_header(only_layout, kind):
    data, stream, _ = document()
    content = data if kind == "unwrapped" else damaged_headers(stream)
    pixels = list(encode(content, FMT, "coarse.bin"))[1].pixels
    img = simulate_scan(pixels, LAYOUT, COARSER["dpi"], blur=COARSER["blur"], seed=2)
    with pytest.raises(IdentifyError) as e:
        soft.identify_coarse(img)
    assert e.value.reason == optar.identify.LABEL_UNREADABLE and e.value.scan_dpi is not None


def test_identify_coarse_refuses_a_picture(only_layout):
    rng = np.random.default_rng(5)
    smooth = rng.integers(0, 256, (90, 60)).astype(np.uint8)
    from PIL import Image

    picture = np.asarray(Image.fromarray(smooth).resize((600, 900), Image.Resampling.BICUBIC))
    framed = np.full((1000, 700), 255, np.uint8)
    framed[50:950, 50:650] = picture
    framed[40:960, 40:50] = framed[40:960, 650:660] = 0
    framed[40:50, 40:660] = framed[950:960, 40:660] = 0
    blank = np.full((1000, 700), 255, np.uint8)
    blank[40:960, 40:660] = 0
    blank[50:950, 50:650] = 255
    for img in (framed, blank, picture):
        start = time.monotonic()
        with pytest.raises(IdentifyError):
            soft.identify_coarse(img)
        assert time.monotonic() - start < 60


def test_identify_any_keeps_the_ordinary_result():
    ident = object()
    with mock.patch.object(optar.identify, "identify_scan", lambda image, options=None: ident), \
            mock.patch.object(soft, "identify_coarse", mock.Mock(side_effect=AssertionError)):
        assert identify_any(np.zeros((4, 4), np.uint8), on_slow=mock.Mock()) is ident


def test_identify_any_falls_back(only_layout):
    img = scan(**COARSER)
    on_slow = mock.Mock()
    ident = identify_any(img, on_slow=on_slow)
    on_slow.assert_called_once_with()
    check_slow_identity(ident, 0, COARSER["dpi"])


def test_identify_any_reports_the_first_error():
    first = IdentifyError(optar.identify.LABEL_UNREADABLE, scan_dpi=290.0)

    def fails(image, options=None):
        raise first

    coarse = mock.Mock(side_effect=IdentifyError(optar.identify.NO_PAGE))
    with mock.patch.object(optar.identify, "identify_scan", fails), \
            mock.patch.object(soft, "identify_coarse", coarse):
        with pytest.raises(IdentifyError) as e:
            identify_any(np.zeros((4, 4), np.uint8))
        assert e.value is first and e.value.slow_tried
        coarse.assert_called_once()
        # Not asked to, or no outline: the slow reader is not tried.
        first.slow_tried = False
        with pytest.raises(IdentifyError) as e:
            identify_any(np.zeros((4, 4), np.uint8), slow=False)
        assert e.value is first and not e.value.slow_tried
        first.scan_dpi = None
        with pytest.raises(IdentifyError) as e:
            identify_any(np.zeros((4, 4), np.uint8))
        assert e.value is first and not e.value.slow_tried
        coarse.assert_called_once()


def test_identify_error_is_not_slow_tried_by_default():
    assert IdentifyError("x").slow_tried is False


def test_cancel_stops_the_slow_reader(only_layout):
    big, grid = enlarged(scan(**COARSE))
    with pytest.raises(soft.Stopped):
        soft.read_soft(grid, big, cancelled=lambda: True)
    with pytest.raises(soft.Stopped):
        soft.identify_coarse(scan(**COARSER), cancelled=lambda: True)

    # Cancelled part way: the reader stops at its next check.
    calls = []

    def later():
        calls.append(None)
        return len(calls) > 20

    start = time.monotonic()
    with pytest.raises(soft.Stopped):
        soft.read_soft(grid, big, cancelled=later)
    assert time.monotonic() - start < 10
    assert len(calls) == 21

    def fails(image, options=None):
        raise IdentifyError(optar.identify.LABEL_UNREADABLE, scan_dpi=290.0)

    with mock.patch.object(optar.identify, "identify_scan", fails), \
            pytest.raises(soft.Stopped):
        identify_any(scan(**COARSER), cancelled=lambda: True)
