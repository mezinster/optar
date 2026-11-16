# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The version-1 container: page headers, page counts, spreading and wrapping."""

import hashlib
import random
import time

import numpy as np
import pytest

from optar import OptarError
from optar.container import (
    PROTECTED_MAX_BYTES,
    Header,
    Plan,
    fingerprint,
    pages_promised,
    plan,
    plan_for,
    positions,
    read_header,
    wrap,
)
from optar.encoder import MAX_PAGES, page_count
from optar.format import CODEWORD, HEADER_COPIES, HEADER_SIZE, LAYOUTS, PARITY, get_layout
from optar.rs import RSCode

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

    assert promised(10, 32) == 0
    assert promised(11, 32) == 1
    assert promised(22, 32) == 2
    assert promised(5, 64) == 0
    assert promised(6, 64) == 1
    assert promised(50, 0) == 0


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
