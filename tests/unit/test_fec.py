# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import numpy as np
import pytest

from optar.fec import decode_symbols, encode_symbols, golay_table, serialize_table
from optar.format import PageFormat

G = PageFormat(65, 93)


def test_golay_table_shape_and_weights():
    t = golay_table()
    assert t.shape == (4096,) and t.dtype == np.uint32
    assert np.array_equal(t >> 12, np.arange(4096))
    weights = {bin(int(v)).count("1") for v in t}
    assert weights <= {0, 8, 12, 16, 24}


def test_golay_minimum_distance_is_8():
    t = golay_table().astype(np.uint32)
    x = t[:, None] ^ t[None, :256]  # linear code: distances to 256 words suffice
    pop = np.array([bin(i).count("1") for i in range(4096)], dtype=np.uint8)
    d = pop[x >> 12] + pop[x & 0xFFF]
    assert d[d > 0].min() == 8


def test_serialize_table_is_big_endian():
    t = golay_table()
    b = serialize_table(t)
    assert len(b) == 4 * 4096
    assert b[4:8] == int(t[1]).to_bytes(4, "big")


@pytest.mark.parametrize("nerr", [0, 1, 2, 3])
def test_golay_corrects_up_to_three_errors(nerr):
    rng = np.random.default_rng(nerr)
    words = rng.integers(0, 4096, 2000, dtype=np.uint32)
    cw = encode_symbols(words, G)
    for i in range(len(cw)):
        for b in rng.choice(24, nerr, replace=False):
            cw[i] ^= np.uint32(1 << int(b))
    out, errs = decode_symbols(cw, G)
    assert np.array_equal(out, words) and np.all(errs == nerr)


def test_golay_four_errors_reported_uncorrectable():
    cw = encode_symbols(np.array([0x123], dtype=np.uint32), G)
    cw[0] ^= np.uint32(0b1111)
    out, errs = decode_symbols(cw, G)
    assert errs[0] == -1 and out[0] == cw[0] >> 12


@pytest.mark.parametrize("order", [2, 3, 4, 5])
def test_hamming_round_trip_and_single_error(order):
    f = PageFormat(65, 93, fec_order=order)
    words = np.arange(1 << min(f.fec_smallbits, 12), dtype=np.uint32)
    cw = encode_symbols(words, f)
    assert np.all(cw < (1 << f.fec_largebits))
    out, errs = decode_symbols(cw.copy(), f)
    assert np.array_equal(out, words) and np.all(errs == 0)
    for bit in range(f.fec_largebits):
        out, errs = decode_symbols(cw ^ np.uint32(1 << bit), f)
        assert np.array_equal(out, words) and np.all(errs == 1)


def test_hamming_double_error_uncorrectable():
    f = PageFormat(65, 93, fec_order=3)
    cw = encode_symbols(np.array([5], dtype=np.uint32), f)
    _, errs = decode_symbols(cw ^ np.uint32(0b1100), f)
    assert errs[0] == -1
