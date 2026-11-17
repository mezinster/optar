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
from optar.fec import encode_symbols
from optar.format import Layout, get_layout
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
    assert result.grid is grid
    assert sum(result.stats.error_histogram) == FMT.fec_syms == result.stats.symbols
    assert read_header(page_payload(result, FMT).data) is not None


def test_read_soft_lists_the_dots_whose_sign_its_choice_overruled():
    big, grid = enlarged(scan(**COARSE))
    fits = []
    real = soft._Reader._fit

    def recording(self):
        fits.append(real(self))
        return fits[-1]

    with mock.patch.object(soft._Reader, "_fit", recording):
        result = soft.read_soft(grid, big)
    corrected = result.corrected_bits
    assert corrected.dtype == np.int64 and corrected.ndim == 1
    assert np.all(np.diff(corrected) > 0)  # ascending, each once
    histogram = result.stats.error_histogram
    assert len(corrected) == sum(i * n for i, n in enumerate(histogram)) > 0
    # Each listed dot's sign in the last fit differs from its chosen codeword's bit,
    # and every other dot's agrees.
    words = (result.bits.reshape(FMT.fec_syms, FMT.fec_smallbits).astype(np.uint32)
             << np.arange(FMT.fec_smallbits - 1, -1, -1, dtype=np.uint32)).sum(axis=1)  # fmt: skip
    codewords = encode_symbols(words.astype(np.uint32), FMT)
    shifts = np.arange(FMT.fec_largebits - 1, -1, -1, dtype=np.uint32)
    chosen = ((codewords[None, :] >> shifts[:, None]) & 1).reshape(-1).astype(bool)
    dark = fits[-1] > 0
    assert len(fits) == soft.ROUNDS and dark.shape == chosen.shape
    assert np.array_equal(np.flatnonzero(dark != chosen), corrected)


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
    # The grid is on the scan enlarged to about ENLARGE_TO pixels a dot.
    assert ident.enlarged == pytest.approx(soft.ENLARGE_TO * 200 / dpi, abs=soft.ENLARGE_STEP)


@pytest.mark.parametrize("turns", [0, 1, 2, 3])
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
    ident = mock.Mock(header=object())
    with mock.patch.object(optar.identify, "identify_scan", lambda image, options=None: ident), \
            mock.patch.object(soft, "identify_coarse", mock.Mock(side_effect=AssertionError)):
        on_slow = mock.Mock()
        assert identify_any(np.zeros((4, 4), np.uint8), on_slow=on_slow) is ident
        on_slow.assert_not_called()


def test_identify_any_falls_back(only_layout):
    img = scan(**COARSER)
    on_slow = mock.Mock()
    ident = identify_any(img, on_slow=on_slow)
    on_slow.assert_called_once_with()
    check_slow_identity(ident, 0, COARSER["dpi"])


def _label_identity(dpi, **fields):
    """A stand-in for a page identify_scan accepted from its label."""
    base = dict(header=None, tag=None, scan_dpi=dpi, layout=get_layout("a4"))
    return mock.Mock(**{**base, **fields})


def _decoded(lost, symbols=1000):
    """A stand-in for decode_located: `lost` of the symbols beyond correction."""
    return lambda grid: mock.Mock(stats=mock.Mock(uncorrectable=lost, symbols=symbols))


@pytest.mark.parametrize(
    ("dpi", "fields", "lost", "tried"),
    [
        (300.0, {}, 130, True),  # an untagged label alone, coarse scan, damaged data
        (300.0, {}, 10, True),  # at the share of lost symbols that counts as damaged
        (300.0, {}, 9, False),  # the data reads well: an old page, left alone
        (300.0, {}, 0, False),
        (600.0, {}, 130, False),  # a fine scan
        (300.0, {"tag": object()}, 130, False),  # a valid tag is never questioned
        (300.0, {"header": object()}, 130, False),  # already a version-1 page
        (None, {}, 130, False),
    ],
)
def test_identify_any_reads_a_coarse_label_only_page_again(dpi, fields, lost, tried, monkeypatch):
    monkeypatch.setattr(optar.identify, "decode_located", _decoded(lost))
    label = _label_identity(dpi, **fields)
    found = object()
    coarse = mock.Mock(return_value=found)
    on_slow = mock.Mock()
    with mock.patch.object(optar.identify, "identify_scan", lambda image, options=None: label), \
            mock.patch.object(soft, "identify_coarse", coarse):
        got = identify_any(np.zeros((4, 4), np.uint8), on_slow=on_slow)
        assert got is (found if tried else label)
        assert coarse.call_count == on_slow.call_count == int(tried)
        if tried:  # not asked to: the label stands
            assert identify_any(np.zeros((4, 4), np.uint8), slow=False) is label


def test_identify_any_keeps_the_label_when_the_slow_reader_finds_nothing(monkeypatch):
    monkeypatch.setattr(optar.identify, "decode_located", _decoded(130))
    label = _label_identity(300.0)
    coarse = mock.Mock(side_effect=IdentifyError(optar.identify.LABEL_UNREADABLE))
    with mock.patch.object(optar.identify, "identify_scan", lambda image, options=None: label), \
            mock.patch.object(soft, "identify_coarse", coarse):
        assert identify_any(np.zeros((4, 4), np.uint8)) is label
    coarse.assert_called_once()


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


# --- Progress reports ---------------------------------------------------------------

STEP_FIND = optar.identify.STEP_FIND
STEP_IDENTIFY = optar.identify.STEP_IDENTIFY
STEP_SLOW_SAMPLE = optar.identify.STEP_SLOW_SAMPLE
STEP_SLOW_FIT = optar.identify.STEP_SLOW_FIT


def keys(reports):
    """The step keys reported, each run of one key once."""
    out = []
    for step, _, _ in reports:
        if not out or out[-1] != step:
            out.append(step)
    return out


def same_identity(a, b):
    assert (a.paper, a.fmt, a.rotation, a.page, a.total, a.tag, a.name, a.layout, a.reader) == (
        b.paper, b.fmt, b.rotation, b.page, b.total, b.tag, b.name, b.layout, b.reader
    )  # fmt: skip
    assert (a.confidence, a.margin, a.header, a.scan_dpi) == (
        b.confidence, b.margin, b.header, b.scan_dpi
    )  # fmt: skip
    assert np.array_equal(a.grid.positions, b.grid.positions)
    assert (a.payload is None) == (b.payload is None)
    if a.payload is not None:
        assert a.payload.data == b.payload.data
        assert np.array_equal(a.result.bits, b.result.bits)


def test_identify_scan_reports_finding_then_each_candidate(only_layout):
    img = scan(600, 1.0)
    reports = []
    ident = identify_scan(img, on_progress=lambda *r: reports.append(r))
    same_identity(ident, identify_scan(img))
    assert keys(reports) == [STEP_FIND, STEP_IDENTIFY]
    assert reports[0] == (STEP_FIND, 0, 1)
    tried = [(done, of) for step, done, of in reports if step == STEP_IDENTIFY]
    # LAYOUT on one paper, in two rotations: the label, then the layouts.
    assert {of for _, of in tried} == {2 * (1 + 1)}
    assert [done for done, _ in tried] == list(range(len(tried)))


def test_identify_scan_reports_nothing_more_when_it_fails(only_layout):
    reports = []
    with pytest.raises(IdentifyError):
        identify_scan(np.full((60, 40), 255, np.uint8), on_progress=lambda *r: reports.append(r))
    assert reports == [(STEP_FIND, 0, 1)]
    reports.clear()
    with pytest.raises(IdentifyError):
        identify_scan(scan(**COARSER), on_progress=lambda *r: reports.append(r))
    assert keys(reports) == [STEP_FIND, STEP_IDENTIFY]
    assert [r[1] for r in reports[1:]] == list(range(4)) and {r[2] for r in reports[1:]} == {4}


def test_read_soft_reports_sampling_then_each_fit():
    big, grid = enlarged(scan(**COARSE))
    reports = []
    result = soft.read_soft(grid, big, on_progress=lambda *r: reports.append(r))
    assert reports == [(STEP_SLOW_SAMPLE, 0, 1)] + [
        (STEP_SLOW_FIT, k, soft.ROUNDS) for k in range(soft.ROUNDS + 1)
    ]
    assert np.array_equal(result.bits, page_bits(document()[1], 2))


def test_identify_any_reports_the_ordinary_steps_then_the_slow_reader(only_layout):
    img = scan(**COARSER)
    reports = []
    ident = identify_any(img, on_progress=lambda *r: reports.append(r))
    check_slow_identity(ident, 0, COARSER["dpi"])
    assert keys(reports) == [STEP_FIND, STEP_IDENTIFY, STEP_SLOW_SAMPLE, STEP_SLOW_FIT]
    first_slow = keys(reports).index(STEP_SLOW_SAMPLE)
    slow = [r for r in reports if r[0] in (STEP_SLOW_SAMPLE, STEP_SLOW_FIT)]
    assert slow[0] == (STEP_SLOW_SAMPLE, 0, 1) and first_slow == 2
    assert (STEP_SLOW_SAMPLE, 0, 2) in slow  # the first of two candidates (rotations)
    fits = [done for step, done, of in slow if step == STEP_SLOW_FIT]
    assert fits == list(range(soft.ROUNDS + 1))


def test_identify_any_passes_the_callback_only_when_given():
    calls = []

    def ordinary(image, options=None, **kw):
        calls.append(("scan", sorted(kw)))
        raise IdentifyError(optar.identify.LABEL_UNREADABLE, scan_dpi=290.0)

    def coarse(image, options=None, cancelled=None, **kw):
        calls.append(("coarse", sorted(kw)))
        raise IdentifyError(optar.identify.LABEL_UNREADABLE)

    with mock.patch.object(optar.identify, "identify_scan", ordinary), \
            mock.patch.object(soft, "identify_coarse", coarse):
        for report in (None, lambda *r: None):
            with pytest.raises(IdentifyError):
                identify_any(np.zeros((4, 4), np.uint8), on_progress=report)
    assert calls == [("scan", []), ("coarse", []),
                     ("scan", ["on_progress"]), ("coarse", ["on_progress"])]  # fmt: skip
