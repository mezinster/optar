# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The version-1 container: page headers, page counts, spreading and wrapping."""

import dataclasses
import hashlib
import random
import time
import tracemalloc

import numpy as np
import pytest

import optar
from optar import OptarError, PageFormat, decode_page, encode
from optar.container import (
    BEST_EFFORT_PAGES,
    PROTECTED_MAX_BYTES,
    Header,
    PagePayload,
    Plan,
    Unwrapped,
    document_plan,
    fingerprint,
    page_payload,
    pages_promised,
    plan,
    plan_for,
    positions,
    read_header,
    unwrap,
    wrap,
)
from optar.decoder import PageResult, PageStats
from optar.encoder import MAX_PAGES, page_count
from optar.format import (
    CODEWORD,
    HEADER_COPIES,
    HEADER_SIZE,
    LAYOUTS,
    PARITY,
    PROMISE_DEN,
    PROMISE_NUM,
    get_layout,
)
from optar.rs import RSCode
from tests.helpers import fake_scan

A4 = get_layout("a4").fmt


def _header(**changes):
    values = dict(page=2, total=7, size=123456, fingerprint=bytes(range(16)), parity=32)
    values.update(changes)
    return Header(**values)


def _payload(header, page_bytes=1000, seed=0):
    rng = np.random.default_rng(seed)
    payload = bytearray(rng.integers(0, 256, page_bytes, dtype=np.uint8).tobytes())
    packed = header.pack()
    for c in range(HEADER_COPIES):
        start = c * (page_bytes // HEADER_COPIES)
        payload[start : start + HEADER_SIZE] = packed
    return payload


def _corrupt(payload, copy, page_bytes=1000):
    start = copy * (page_bytes // HEADER_COPIES)
    payload[start + 10] ^= 0xFF


def _page_payloads(stream, fmt, total):
    """Each page's payload as the decoder sees it: its net_bits, odd bits dropped."""
    bits = np.unpackbits(np.frombuffer(stream, dtype=np.uint8))
    page_bytes = fmt.net_bits // 8
    out = []
    for p in range(total):
        page_bits = bits[p * fmt.net_bits : p * fmt.net_bits + page_bytes * 8]
        out.append(np.packbits(page_bits).tobytes())
    return out


# Header


def test_header_packs_to_header_size():
    assert len(_header().pack()) == HEADER_SIZE
    assert _header().pack()[:4] == b"oPt1"


@pytest.mark.parametrize("size", [0, 15, 17, 32])
def test_header_with_wrong_fingerprint_size_is_refused(size):
    with pytest.raises(ValueError):
        _header(fingerprint=bytes(size)).pack()


def test_header_round_trip():
    header = _header()
    assert read_header(bytes(_payload(header))) == header


def test_header_reads_with_corrupted_copies():
    header = _header()
    payload = _payload(header)
    _corrupt(payload, 0)
    assert read_header(bytes(payload)) == header
    for c in (1, 2, 4):
        _corrupt(payload, c)
    assert read_header(bytes(payload)) == header
    _corrupt(payload, 3)
    assert read_header(bytes(payload)) is None


def test_disagreeing_valid_copies_read_as_none():
    payload = _payload(_header())
    other = _header(page=3).pack()
    start = 2 * (1000 // HEADER_COPIES)
    payload[start : start + HEADER_SIZE] = other
    assert read_header(bytes(payload)) is None


def test_random_payloads_have_no_header():
    rng = np.random.default_rng(1)
    payloads = rng.integers(0, 256, (10_000, 400), dtype=np.uint8)
    assert all(read_header(row.tobytes()) is None for row in payloads)


def test_fingerprint():
    assert fingerprint(b"abc") == hashlib.sha256(b"abc").digest()[:16]


# Plan


def test_known_page_counts():
    size = 552_508
    assert plan(size, "f", A4, 0).total == 3
    assert plan(size, "f", A4, 32).total == 4


@pytest.mark.parametrize("parity", PARITY.values())
@pytest.mark.parametrize("size", [0, 1, 1000, 199_000, 552_508, 3_000_000])
def test_plan_picks_smallest_total(size, parity):
    name = "file.bin"
    need = size + 1 + len(name.encode())
    p = plan(size, name, A4, parity)
    assert isinstance(p, Plan)
    assert p.data_bytes >= need
    assert p.codewords * (CODEWORD - parity) == p.data_bytes
    assert p.page_bytes == A4.net_bits // 8
    assert p.page_body == p.page_bytes - HEADER_COPIES * HEADER_SIZE
    assert p.codewords == p.total * p.page_body // CODEWORD
    if p.total > 1:
        assert plan_for(p.total - 1, A4, parity).data_bytes < need
    assert plan_for(p.total, A4, parity) == p


def test_empty_file_gives_one_page():
    assert plan(0, "", A4, 0).total == 1
    assert plan(0, "", A4, 64).total == 1
    stream = wrap(b"", "", A4, 32)
    assert page_count(len(stream), A4) == 1


def test_bad_parity_is_rejected():
    with pytest.raises(ValueError):
        plan(10, "f", A4, 16)


def test_too_many_pages_is_refused():
    p = plan_for(MAX_PAGES, A4, 0)
    with pytest.raises(OptarError):
        plan(p.data_bytes, "", A4, 0)


def test_protected_stream_over_limit_is_refused():
    started = time.perf_counter()
    with pytest.raises(OptarError):
        plan(PROTECTED_MAX_BYTES, "f", A4, 32)
    assert time.perf_counter() - started < 1
    # The same size without parity is allowed, given enough pages.
    assert plan(PROTECTED_MAX_BYTES, "f", get_layout("a4").fmt, 0).total <= MAX_PAGES


def test_protected_stream_limit_is_on_the_stream():
    fmt = A4
    page_bytes = fmt.net_bits // 8
    limit_pages = PROTECTED_MAX_BYTES // page_bytes
    assert plan_for(limit_pages, fmt, 32).total == limit_pages
    fits = plan_for(limit_pages, fmt, 32).data_bytes - 1
    plan(fits, "", fmt, 32)
    with pytest.raises(OptarError):
        plan(plan_for(limit_pages + 1, fmt, 32).data_bytes - 1, "", fmt, 32)


def test_pages_promised():
    def promised(total, parity):
        return pages_promised(plan_for(total, A4, parity))

    assert promised(11, 32) == 0
    assert promised(12, 32) == 1
    assert promised(23, 32) == 1
    assert promised(24, 32) == 2
    assert promised(5, 64) == 0
    assert promised(6, 64) == 1
    assert promised(11, 64) == 1
    assert promised(12, 64) == 2
    assert promised(50, 0) == 0


@pytest.mark.parametrize(("total", "parity"), [(12, 32), (24, 32), (6, 64), (12, 64)])
def test_promised_pages_fit_the_budget(total, parity):
    """Any n promised pages, adjacent or not, cost no codeword more than the budget."""
    p = plan_for(total, A4, parity)
    n = pages_promised(p)
    assert n >= 1
    page = positions(p) // p.page_body  # (m, CODEWORD) page index of each byte
    counts = np.zeros((p.codewords, total), dtype=np.int64)
    np.add.at(counts, (np.arange(p.codewords)[:, None], page), 1)
    # The worst n pages for a codeword are the n holding most of its bytes.
    worst = int(np.sort(counts, axis=1)[:, -n:].sum(axis=1).max())
    assert worst <= PROMISE_NUM * parity // PROMISE_DEN


# Spreading


@pytest.mark.parametrize("total", [1, 3, 12])
def test_positions_spread_one_byte_per_slice(total):
    p = plan_for(total, get_layout("a4", "large").fmt, 32)
    m = p.codewords
    pos = positions(p)
    assert pos.dtype == np.int64
    assert pos.shape == (m, CODEWORD)
    assert np.array_equal(np.sort(pos.ravel()), np.arange(CODEWORD * m))
    slices = pos // m
    assert np.array_equal(slices, np.broadcast_to(np.arange(CODEWORD), (m, CODEWORD)))


# Wrapping


def _check_wrapped(data, name, fmt, parity):
    p = plan(len(data), name, fmt, parity)
    stream = wrap(data, name, fmt, parity)
    assert page_count(len(stream), fmt) == p.total
    for number, payload in enumerate(_page_payloads(stream, fmt, p.total), start=1):
        header = read_header(payload)
        assert header == Header(
            page=number,
            total=p.total,
            size=len(data),
            fingerprint=fingerprint(data),
            parity=parity,
        )
    return p, stream


@pytest.mark.parametrize("parity", PARITY.values())
@pytest.mark.parametrize("key", list(LAYOUTS))
def test_wrap_headers_on_every_page(key, parity):
    fmt = LAYOUTS[key].fmt
    page_bytes = fmt.net_bits // 8
    data = random.Random(f"{key}{parity}").randbytes(int(page_bytes * 1.5))
    _check_wrapped(data, "name.txt", fmt, parity)


def _body(stream, fmt, p):
    """The body bytes of all pages, in order."""
    covered = np.zeros(p.page_bytes, dtype=bool)
    for c in range(HEADER_COPIES):
        start = c * (p.page_bytes // HEADER_COPIES)
        covered[start : start + HEADER_SIZE] = True
    pages = [np.frombuffer(x, dtype=np.uint8) for x in _page_payloads(stream, fmt, p.total)]
    return np.concatenate([page[~covered] for page in pages])


@pytest.mark.parametrize("parity", PARITY.values())
def test_wrap_body_layout(parity):
    fmt = get_layout("a4", "xlarge").fmt
    data = random.Random(parity).randbytes(50_000)
    name = "doc.pdf"
    p, stream = _check_wrapped(data, name, fmt, parity)
    body = _body(stream, fmt, p)
    assert len(body) == p.total * p.page_body
    words = body[positions(p)]
    k = CODEWORD - parity
    region = words[:, :k].ravel().tobytes()
    assert region[: len(data)] == data
    assert region[len(data)] == len(name)
    assert region[len(data) + 1 : len(data) + 1 + len(name)] == name.encode()
    assert not any(region[len(data) + 1 + len(name) :])
    assert not body[CODEWORD * p.codewords :].any()
    if parity:
        assert np.array_equal(words[:, k:], RSCode(parity).encode(words[:, :k]))


def test_long_name_is_cut_on_a_character_boundary():
    fmt = get_layout("a4", "xlarge").fmt
    name = "ab" + "é" * 200  # 402 bytes; byte 255 is the first half of a character
    data = b"x" * 10
    p, stream = _check_wrapped(data, name, fmt, 0)
    body = _body(stream, fmt, p)
    region = body[positions(p)].ravel().tobytes()
    length = region[10]
    assert length == 2 + 2 * 126
    assert region[11 : 11 + length].decode() == "ab" + "é" * 126
    assert plan(10, name, fmt, 0) == plan(10, name[:128], fmt, 0)


@pytest.mark.slow
def test_wrap_of_50_mb_is_fast():
    data = np.random.default_rng(3).integers(0, 256, 50_000_000, dtype=np.uint8).tobytes()
    started = time.perf_counter()
    stream = wrap(data, "big.bin", A4, 32)
    assert time.perf_counter() - started < 30
    assert page_count(len(stream), A4) == plan(len(data), "big.bin", A4, 32).total


# Reading


def test_new_names_are_exported():
    for name in ("PagePayload", "Unwrapped", "page_payload", "unwrap", "name_bytes"):
        assert getattr(optar, name) is getattr(optar.container, name)
        assert name in optar.__all__


def _fake_result(fmt, lost, seed=0):
    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, fmt.net_bits, dtype=np.uint8)
    stats = PageStats(symbols=fmt.fec_syms, error_histogram=(0, 0, 0, 0), uncorrectable=len(lost))
    return PageResult(
        bits=bits,
        stats=stats,
        debug_image=None,
        corrected_bits=np.zeros(0, dtype=np.int64),
        lost_symbols=np.asarray(lost, dtype=np.int64),
    )


@pytest.mark.parametrize("fmt", [A4, PageFormat(65, 93, fec_order=3), get_layout("a4", "big").fmt])
def test_page_payload_packs_bits_and_erases_lost_symbols(fmt):
    small = fmt.fec_smallbits
    lost = [0, 1, 7, fmt.fec_syms // 2, fmt.fec_syms - 1]
    result = _fake_result(fmt, lost)
    out = page_payload(result, fmt)
    assert isinstance(out, PagePayload)
    page_bytes = fmt.net_bits // 8
    assert out.data == np.packbits(result.bits[: page_bytes * 8]).tobytes()
    expected = np.zeros(page_bytes, dtype=bool)
    for s in lost:
        for bit in range(s * small, (s + 1) * small):
            if bit // 8 < page_bytes:
                expected[bit // 8] = True
    assert out.erased.dtype == bool
    assert np.array_equal(out.erased, expected)


def test_page_payload_without_loss_erases_nothing():
    out = page_payload(_fake_result(A4, []), A4)
    assert len(out.data) == A4.net_bits // 8
    assert not out.erased.any()


def test_page_payload_needs_detail():
    result = _fake_result(A4, [])
    plain = PageResult(bits=result.bits, stats=result.stats, debug_image=None)
    with pytest.raises(ValueError):
        page_payload(plain, A4)


def _clean_pages(stream, fmt, total):
    return {
        number: PagePayload(payload, np.zeros(len(payload), dtype=bool))
        for number, payload in enumerate(_page_payloads(stream, fmt, total), start=1)
    }


def _document(fmt, parity, total=None, size=None, name="name.txt", seed=0):
    """(data, name, plan, header, clean pages) of a document of `total` pages."""
    if size is None:
        size = plan_for(total, fmt, parity).data_bytes - 1 - len(name)
    data = random.Random(f"{seed}-{size}").randbytes(size)
    p = plan(len(data), name, fmt, parity)
    assert total is None or p.total == total
    stream = wrap(data, name, fmt, parity)
    pages = _clean_pages(stream, fmt, p.total)
    header = read_header(pages[1].data)
    return data, name, p, header, pages


@pytest.mark.parametrize("parity", PARITY.values())
@pytest.mark.parametrize("key", list(LAYOUTS))
def test_unwrap_round_trip(key, parity):
    fmt = LAYOUTS[key].fmt
    page_bytes = fmt.net_bits // 8
    data, name, p, header, pages = _document(fmt, parity, size=int(page_bytes * 1.5))
    out = unwrap(header, fmt, pages)
    assert isinstance(out, Unwrapped)
    assert out.verified
    assert out.data == data
    assert out.best_effort == data
    assert out.name == name
    assert out.repaired_bytes == 0
    assert out.worst_used == 0
    assert out.budget == parity
    assert out.failed == 0
    assert out.page_damage == {}
    assert out.missing == ()


def test_unwrap_of_empty_file():
    data, name, p, header, pages = _document(A4, 32, size=0, name="")
    out = unwrap(header, A4, pages)
    assert out.verified and out.data == b"" and out.name == ""


def _under_headers(p):
    covered = np.zeros(p.page_bytes, dtype=bool)
    for c in range(HEADER_COPIES):
        start = c * (p.page_bytes // HEADER_COPIES)
        covered[start : start + HEADER_SIZE] = True
    return covered


def _damage(pages, p, fraction, seed, erase):
    """Corrupt `fraction` of the codeword bytes of every page (not headers).

    Returns (damaged pages, number of corrupted bytes, per-page counts).
    """
    rng = np.random.default_rng(seed)
    body_index = np.flatnonzero(~_under_headers(p))
    out, total, per_page = {}, 0, {}
    for number, page in pages.items():
        data = np.frombuffer(page.data, dtype=np.uint8).copy()
        erased = page.erased.copy()
        # Body bytes of this page that lie in a codeword.
        start = (number - 1) * p.page_body
        usable = np.flatnonzero(start + np.arange(p.page_body) < CODEWORD * p.codewords)
        hit = body_index[rng.choice(usable, int(len(usable) * fraction), replace=False)]
        data[hit] ^= rng.integers(1, 256, len(hit), dtype=np.uint8)
        if erase:
            erased[hit] = True
        out[number] = PagePayload(data.tobytes(), erased)
        total += len(hit)
        per_page[number] = len(hit)
    return out, total, per_page


def test_unwrap_repairs_random_errors():
    fmt = get_layout("a4", "xlarge").fmt
    data, name, p, header, pages = _document(fmt, 32, total=6)
    damaged, count, per_page = _damage(pages, p, 0.02, seed=1, erase=False)
    out = unwrap(header, fmt, damaged)
    assert out.verified and out.data == data and out.name == name
    assert out.repaired_bytes == count
    assert 0 < out.worst_used <= 32
    assert out.failed == 0
    assert out.page_damage == per_page

    erased, count_e, _ = _damage(pages, p, 0.02, seed=1, erase=True)
    assert count_e == count
    out_e = unwrap(header, fmt, erased)
    assert out_e.verified and out_e.data == data
    assert out_e.repaired_bytes == count
    assert out_e.worst_used * 2 == out.worst_used
    assert out_e.page_damage == per_page


@pytest.mark.parametrize("lost", range(1, 13))
def test_unwrap_with_one_page_missing(lost):
    fmt = get_layout("a4", "xlarge").fmt
    data, name, p, header, pages = _document(fmt, 32, total=12)
    del pages[lost]
    out = unwrap(header, fmt, pages)
    assert out.verified and out.data == data and out.name == name
    assert out.missing == (lost,)
    assert out.failed == 0
    assert 0 < out.worst_used <= 24
    assert set(out.page_damage) == {lost}
    in_codewords = min(p.page_body, CODEWORD * p.codewords - (lost - 1) * p.page_body)
    assert out.page_damage[lost] == in_codewords
    assert out.repaired_bytes == in_codewords


# Measured 0.861 for the case below: about an eighth of each codeword lies on
# the missing page and stays zero (or is filled wrongly where a codeword has
# exactly `parity` erasures and an undetected error), plus 1% errors.
BEST_EFFORT_AGREEMENT = 0.85


def test_unwrap_beyond_repair_reports_failure():
    fmt = get_layout("a4", "xlarge").fmt
    data, name, p, header, pages = _document(fmt, 32, total=8)
    damaged, _, _ = _damage(pages, p, 0.01, seed=2, erase=False)
    del damaged[3]
    out = unwrap(header, fmt, damaged)
    assert not out.verified
    assert out.data is None
    assert out.failed > 0
    assert out.worst_used > out.budget
    assert out.missing == (3,)
    assert max(out.page_damage, key=out.page_damage.get) == 3
    assert len(out.best_effort) == len(data)
    same = np.mean(np.frombuffer(out.best_effort, np.uint8) == np.frombuffer(data, np.uint8))
    assert same >= BEST_EFFORT_AGREEMENT, same


def test_unwrap_with_another_documents_header():
    fmt = get_layout("a4", "xlarge").fmt
    _, _, _, _, pages = _document(fmt, 32, total=4)
    for total in (4, 3, 6):
        _, _, _, other, _ = _document(fmt, 32, total=total, seed=9)
        out = unwrap(other, fmt, pages)
        assert not out.verified


def _claim(total, size, parity, page=1):
    return Header(page, total, size, bytes(16), parity)


def test_a_header_no_wrap_writes_is_refused():
    fmt = get_layout("a4", "xlarge").fmt
    _, _, p, header, pages = _document(fmt, 32, total=4)
    fewer = plan_for(3, fmt, 32).data_bytes
    assert document_plan(header, fmt) == p
    bad = [
        _claim(4, p.data_bytes, 32),  # no room for the name's length byte
        _claim(4, p.data_bytes + 5, 32),  # a file larger than the document
        _claim(4, fewer - 256, 32),  # three pages hold it, whatever its name
        _claim(MAX_PAGES, 10, 0),  # thousands of pages for ten bytes
        _claim(MAX_PAGES + 1, plan_for(MAX_PAGES + 1, fmt, 0).data_bytes - 1, 0),
        _claim(4, -1, 32),
        _claim(4, 60000, 7),  # no such parity
        _claim(5, 60000, 32, page=6),
        _claim(1, 10, 32, page=0),
    ]
    for header in bad:
        assert document_plan(header, fmt) is None, header
        with pytest.raises(optar.FormatError):
            unwrap(header, fmt, pages)
    # The fewest pages depend on the name: both ends of the range are documents.
    assert document_plan(_claim(4, fewer - 255, 32), fmt) is not None
    assert document_plan(_claim(4, p.data_bytes - 1, 32), fmt) is not None
    # With parity, no more than PROTECTED_MAX_BYTES on paper.
    most = PROTECTED_MAX_BYTES // (A4.net_bits // 8)
    assert most < MAX_PAGES
    assert document_plan(_claim(most, plan_for(most, A4, 32).data_bytes - 1, 32), A4)
    over = _claim(most + 1, plan_for(most + 1, A4, 32).data_bytes - 1, 32)
    assert document_plan(over, A4) is None
    assert document_plan(dataclasses.replace(over, parity=0), A4) is None  # not the fewest pages
    size = plan_for(most + 1, A4, 0).data_bytes - 1
    assert document_plan(_claim(most + 1, size, 0), A4) is not None


def test_a_long_name_that_takes_one_more_page_unwraps():
    fmt = get_layout("a4", "xlarge").fmt
    size = plan_for(2, fmt, 32).data_bytes - 100  # two pages, unless the name is long
    for name, total in (("short", 2), ("n" * 200, 3)):
        data, _, p, header, pages = _document(fmt, 32, size=size, name=name)
        assert p.total == total
        out = unwrap(header, fmt, pages)
        assert out.verified and out.data == data and out.name == name


def _peak_and_seconds(call):
    tracemalloc.start()
    started = time.perf_counter()
    try:
        out = call()
        seconds = time.perf_counter() - started
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    return out, peak, seconds


@pytest.mark.parametrize("parity", [0, 32, 64])
def test_one_page_of_a_huge_claimed_document_costs_little(parity):
    # A single page whose header claims the largest document there is must not
    # make unwrap() lay that document out: the page may be hostile or damaged.
    p1 = plan_for(1, A4, parity)
    total = MAX_PAGES if not parity else PROTECTED_MAX_BYTES // p1.page_bytes
    header = _claim(total, plan_for(total, A4, parity).data_bytes - 1, parity, page=7)
    assert document_plan(header, A4) is not None
    page = PagePayload(bytes(p1.page_bytes), np.zeros(p1.page_bytes, dtype=bool))
    out, peak, seconds = _peak_and_seconds(lambda: unwrap(header, A4, {7: page}))
    assert seconds < 1.0, seconds
    assert peak < 40 * 1024 * 1024, peak
    assert out.data is None and out.best_effort is None and not out.verified
    assert out.name == "" and out.repaired_bytes == 0
    assert out.failed >= 1 and out.worst_used > out.budget == parity
    assert len(out.missing) == total - 1 and 7 not in out.missing
    assert set(out.page_damage) == set(out.missing)
    assert out.page_damage[1] == p1.page_body


def test_no_page_at_all_costs_little():
    header = _claim(MAX_PAGES, plan_for(MAX_PAGES, A4, 0).data_bytes - 1, 0)
    out, peak, seconds = _peak_and_seconds(lambda: unwrap(header, A4, {}))
    assert seconds < 1.0 and peak < 40 * 1024 * 1024
    assert out.data is None and out.best_effort is None and len(out.missing) == MAX_PAGES


@pytest.mark.parametrize("parity", [0, 32])
def test_best_effort_needs_half_of_the_pages(parity):
    assert BEST_EFFORT_PAGES == 2
    fmt = get_layout("a4", "xlarge").fmt
    data, name, p, header, pages = _document(fmt, parity, total=12)
    half = {n: pages[n] for n in (1, 3, 5, 8, 10, 12)}
    out = unwrap(header, fmt, half)
    assert out.data is None and not out.verified
    assert out.best_effort is not None and len(out.best_effort) == len(data)
    assert out.failed > 0 and out.missing == (2, 4, 6, 7, 9, 11)
    del half[8]
    out = unwrap(header, fmt, half)
    assert out.data is None and out.best_effort is None and not out.verified
    assert out.failed >= 1 and out.worst_used > out.budget
    assert out.missing == (2, 4, 6, 7, 8, 9, 11)
    assert out.page_damage == {n: p.page_body for n in out.missing}


def test_best_effort_is_the_file_itself_when_there_is_one():
    fmt = get_layout("a4", "xlarge").fmt
    data, name, p, header, pages = _document(fmt, 32, total=2)
    out = unwrap(header, fmt, pages)
    assert out.data == data and out.best_effort is out.data  # not a second copy


def test_the_last_page_of_a_document_holds_fewer_codeword_bytes():
    # page_damage of a page not supplied counts only the bytes codewords use.
    fmt = get_layout("a4", "xlarge").fmt
    _, _, p, header, pages = _document(fmt, 0, total=3)
    unused = p.total * p.page_body - CODEWORD * p.codewords
    assert unused > 0
    full = unwrap(header, fmt, {1: pages[1], 2: pages[2]})  # the best effort is built
    quick = unwrap(header, fmt, {1: pages[1]})  # it is not
    assert full.best_effort is not None and quick.best_effort is None
    assert full.page_damage[3] == quick.page_damage[3] == p.page_body - unused
    assert quick.page_damage[2] == p.page_body


def test_unwrap_without_parity_takes_data_as_read():
    fmt = get_layout("a4", "xlarge").fmt
    data, name, p, header, pages = _document(fmt, 0, total=3)
    damaged, count, _ = _damage(pages, p, 0.001, seed=3, erase=False)
    out = unwrap(header, fmt, damaged)
    assert out.data is not None and out.data != data
    assert not out.verified
    assert out.repaired_bytes == 0
    assert out.budget == 0
    del pages[2]
    out = unwrap(header, fmt, pages)
    assert out.data is None and not out.verified
    assert out.missing == (2,)
    assert out.failed > 0


def _file_byte_places(p, size):
    """(page number, payload index) of each file byte, for parity 0 (k = 255)."""
    body_index = np.flatnonzero(~_under_headers(p))
    pos = positions(p).reshape(-1)[:size]  # with k = 255 the region is positions in order
    return pos // p.page_body + 1, body_index[pos % p.page_body]


def test_best_effort_without_parity_keeps_an_erased_byte_as_read():
    fmt = get_layout("a4", "xlarge").fmt
    data, name, p, header, pages = _document(fmt, 0, total=3)
    target = len(data) // 2
    page_of, index_of = _file_byte_places(p, len(data))
    number, index = int(page_of[target]), int(index_of[target])
    payload = np.frombuffer(pages[number].data, np.uint8).copy()
    payload[index] ^= 0x5A
    erased = np.zeros(p.page_bytes, dtype=bool)
    erased[index] = True
    pages[number] = PagePayload(payload.tobytes(), erased)
    out = unwrap(header, fmt, pages)
    assert out.data is None and not out.verified
    diff = np.flatnonzero(np.frombuffer(out.best_effort, np.uint8) != np.frombuffer(data, np.uint8))
    assert diff.tolist() == [target]


def test_best_effort_without_parity_zeros_a_missing_page():
    fmt = get_layout("a4", "xlarge").fmt
    data, name, p, header, pages = _document(fmt, 0, total=3)
    del pages[2]
    out = unwrap(header, fmt, pages)
    assert out.data is None
    page_of, _ = _file_byte_places(p, len(data))
    expected = np.frombuffer(data, np.uint8).copy()
    expected[page_of == 2] = 0
    assert (page_of == 2).sum() > 0
    assert out.best_effort == expected.tobytes()


def test_unwrap_ignores_pages_outside_the_document():
    fmt = get_layout("a4", "xlarge").fmt
    data, name, p, header, pages = _document(fmt, 32, total=2)
    pages[7] = pages[1]
    out = unwrap(header, fmt, pages)
    assert out.verified and out.missing == ()


def _blotted_payload(stream, fmt, number, centre, radius):
    """Page `number` encoded, a white disc painted on it, decoded with detail."""
    page = list(encode(stream, fmt))[number - 1].pixels.copy()
    h, w = page.shape
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = centre[0] * w, centre[1] * h
    page[(xx - cx) ** 2 + (yy - cy) ** 2 <= (radius * w) ** 2] = 255
    result = decode_page(fake_scan(page, scale=1, margin=40), fmt, detail=True)
    return page_payload(result, fmt), result


@pytest.mark.parametrize(
    ("centre", "radius"),
    [
        ((0.5, 0.5), 0.12),
        ((0.25, 0.25), 0.12),
        ((0.75, 0.3), 0.12),
        ((0.3, 0.8), 0.12),
        ((0.5, 0.5), 0.30),
    ],
)
def test_unwrap_repairs_a_blotted_page(centre, radius):
    fmt = get_layout("a4", "large").fmt
    data, name, p, header, pages = _document(fmt, 32, total=12)
    stream = wrap(data, name, fmt, 32)
    pages[5], result = _blotted_payload(stream, fmt, 5, centre, radius)
    out = unwrap(header, fmt, pages)
    assert out.verified and out.data == data
    assert out.worst_used <= 24
    if radius > 0.2:
        # Golay alone absorbs the small discs; the large one needs the parity.
        assert len(result.lost_symbols) > 0
        assert out.repaired_bytes > 0


@pytest.mark.slow
def test_unwrap_of_50_mb_is_fast():
    data = np.random.default_rng(3).integers(0, 256, 50_000_000, dtype=np.uint8).tobytes()
    stream = wrap(data, "big.bin", A4, 32)
    p = plan(len(data), "big.bin", A4, 32)
    pages = _clean_pages(stream, A4, p.total)
    header = read_header(pages[1].data)
    started = time.perf_counter()
    out = unwrap(header, A4, pages)
    assert time.perf_counter() - started < 30
    assert out.verified and out.data == data
    del pages[p.total // 2]
    started = time.perf_counter()
    out = unwrap(header, A4, pages)
    assert time.perf_counter() - started < 60
    assert out.verified and out.data == data
