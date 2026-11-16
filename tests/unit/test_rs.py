# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Reed-Solomon over GF(256): encoding, errors and erasures."""

import time

import numpy as np
import pytest

from optar.rs import RSCode

N = 255


def _gf_mul(a, b):
    """Multiplication in GF(256) modulo 0x11D, bit by bit (no tables)."""
    r = 0
    while b:
        if b & 1:
            r ^= a
        b >>= 1
        a <<= 1
        if a & 0x100:
            a ^= 0x11D
    return r


def _reference_parity(data, parity):
    """Systematic parity by long division of data(x) * x^parity by g(x)."""
    g = [1]  # highest degree first; roots alpha^0 .. alpha^(parity-1)
    root = 1
    for _ in range(parity):
        g = [a ^ _gf_mul(b, root) for a, b in zip(g + [0], [0] + g, strict=True)]
        root = _gf_mul(root, 2)
    rem = list(data) + [0] * parity
    for i in range(len(data)):
        coef = rem[i]
        if coef:
            for j in range(1, parity + 1):
                rem[i + j] ^= _gf_mul(g[j], coef)
    return rem[len(data) :]


def _codewords(rng, code, w):
    data = rng.integers(0, 256, size=(w, N - code.parity), dtype=np.uint8)
    return np.concatenate([data, code.encode(data)], axis=1)


def _damage(rng, words, t, e):
    """t errors and e erasures per row at distinct random places."""
    received = words.copy()
    erased = np.zeros(words.shape, dtype=bool)
    for row in range(words.shape[0]):
        places = rng.permutation(N)[: t + e]
        err, era = places[:t], places[t:]
        received[row, err] ^= rng.integers(1, 256, size=t, dtype=np.uint8)
        received[row, era] = rng.integers(0, 256, size=e, dtype=np.uint8)
        erased[row, era] = True
    return received, erased


def test_encode_matches_reference_division():
    data = np.arange(223, dtype=np.uint8)
    parity = RSCode(32).encode(data[None, :])
    assert parity.shape == (1, 32)
    assert parity.dtype == np.uint8
    assert parity[0].tolist() == _reference_parity(data.tolist(), 32)


@pytest.mark.parametrize("parity", [1, 2, 7, 64, 254])
def test_encode_matches_reference_other_parities(parity):
    rng = np.random.default_rng(parity)
    data = rng.integers(0, 256, size=(3, N - parity), dtype=np.uint8)
    out = RSCode(parity).encode(data)
    for row in range(3):
        assert out[row].tolist() == _reference_parity(data[row].tolist(), parity)


def test_clean_words_decode_ok_with_zero_counts():
    rng = np.random.default_rng(1)
    code = RSCode(32)
    words = _codewords(rng, code, 50)
    result = code.decode(words)
    assert result.ok.all()
    assert (result.errors == 0).all()
    assert (result.erasures == 0).all()
    assert np.array_equal(result.words, words)


@pytest.mark.parametrize("parity", [32, 64])
def test_correctable_damage_is_repaired_exactly(parity):
    rng = np.random.default_rng(parity)
    code = RSCode(parity)
    words = _codewords(rng, code, 200)
    splits = [(parity // 2, 0), (0, parity)]
    while len(splits) < 200:
        t = int(rng.integers(0, parity // 2 + 1))
        e = int(rng.integers(0, parity - 2 * t + 1))
        splits.append((t, e))
    received = np.empty_like(words)
    erased = np.zeros(words.shape, dtype=bool)
    for row, (t, e) in enumerate(splits):
        received[row : row + 1], erased[row : row + 1] = _damage(rng, words[row : row + 1], t, e)
    result = code.decode(received, erased)
    assert result.ok.all()
    assert np.array_equal(result.words, words)
    assert result.errors.tolist() == [t for t, _ in splits]
    assert result.erasures.tolist() == [e for _, e in splits]


def _overload(rng, words, total, max_e):
    """Damage each row with 2t + e = total and e <= max_e, splits chosen at random."""
    received = np.empty_like(words)
    erased = np.zeros(words.shape, dtype=bool)
    t_min = max(0, -(-(total - max_e) // 2))
    for row in range(words.shape[0]):
        t = int(rng.integers(t_min, total // 2 + 1))
        e = total - 2 * t
        received[row : row + 1], erased[row : row + 1] = _damage(rng, words[row : row + 1], t, e)
    return received, erased


@pytest.mark.parametrize("parity", [32, 64])
@pytest.mark.parametrize("excess", [1, 8])
def test_too_much_damage_is_never_reported_as_the_original(parity, excess):
    rng = np.random.default_rng(parity * 100 + excess)
    code = RSCode(parity)
    words = _codewords(rng, code, 200)
    received, erased = _overload(rng, words, parity + excess, parity + excess)
    result = code.decode(received, erased)
    same = (result.words == words).all(axis=1)
    assert not (result.ok & same).any()
    failed = ~result.ok
    assert np.array_equal(result.words[failed], received[failed])
    assert (result.errors[failed] == 0).all()
    assert result.erasures.tolist() == erased.sum(axis=1).tolist()


@pytest.mark.parametrize("parity", [32, 64])
@pytest.mark.parametrize("excess", [1, 8])
def test_too_much_damage_rarely_decodes_to_another_codeword(parity, excess):
    # With e close to parity few checks are left, so a few extra errors land
    # within reach of another codeword by necessity; this bound holds while at
    # least half the parity is left to check errors.
    rng = np.random.default_rng(parity * 1000 + excess)
    code = RSCode(parity)
    words = _codewords(rng, code, 200)
    received, erased = _overload(rng, words, parity + excess, parity // 2)
    result = code.decode(received, erased)
    assert result.ok.mean() < 0.05


def test_more_erasures_than_parity_fails_without_exception():
    rng = np.random.default_rng(5)
    code = RSCode(16)
    words = _codewords(rng, code, 10)
    received, erased = _damage(rng, words, 0, 17)
    result = code.decode(received, erased)
    assert not result.ok.any()
    assert np.array_equal(result.words, received)
    assert (result.erasures == 17).all()


def test_all_bytes_erased_fails_without_exception():
    code = RSCode(32)
    words = np.zeros((2, N), dtype=np.uint8)
    result = code.decode(words, np.ones((2, N), dtype=bool))
    assert not result.ok.any()


def test_failing_rows_do_not_disturb_good_rows():
    rng = np.random.default_rng(6)
    code = RSCode(32)
    words = _codewords(rng, code, 60)
    plan = [(0, 0), (10, 5), (0, 40), (20, 0)] * 15  # clean, good, too many erasures, bad
    received = np.empty_like(words)
    erased = np.zeros(words.shape, dtype=bool)
    for row, (t, e) in enumerate(plan):
        received[row : row + 1], erased[row : row + 1] = _damage(rng, words[row : row + 1], t, e)
    result = code.decode(received, erased)
    good = np.array([t * 2 + e <= 32 for t, e in plan])
    assert result.ok[good].all()
    assert np.array_equal(result.words[good], words[good])
    assert not result.ok[~good].any()
    assert np.array_equal(result.words[~good], received[~good])
    alone = code.decode(received[good], erased[good])
    assert np.array_equal(alone.words, result.words[good])
    assert np.array_equal(alone.errors, result.errors[good])


def test_empty_batch():
    code = RSCode(32)
    result = code.decode(np.zeros((0, N), dtype=np.uint8))
    assert result.words.shape == (0, N)
    assert result.ok.shape == (0,)


def test_input_is_not_modified():
    rng = np.random.default_rng(7)
    code = RSCode(8)
    words = _codewords(rng, code, 5)
    received, erased = _damage(rng, words, 2, 2)
    before = received.copy()
    code.decode(received, erased)
    assert np.array_equal(received, before)


@pytest.mark.parametrize("parity", [0, 255])
def test_parity_out_of_range(parity):
    with pytest.raises(ValueError):
        RSCode(parity)


def test_20000_words_with_few_errors_decode_quickly():
    rng = np.random.default_rng(8)
    code = RSCode(32)
    words = _codewords(rng, code, 20000)
    received = words.copy()
    rows = np.arange(20000)
    for k in range(4):
        hit = rng.random(20000) < 0.5
        cols = rng.integers(0, N, size=20000)
        received[rows[hit], cols[hit]] ^= np.uint8(1 << k)
    start = time.perf_counter()
    result = code.decode(received)
    elapsed = time.perf_counter() - start
    assert result.ok.all()
    assert np.array_equal(result.words, words)
    assert elapsed < 5, f"decoding took {elapsed:.1f} s"


@pytest.mark.parametrize("dtype", [np.int64, np.uint16, np.int8, np.float64])
def test_non_uint8_arrays_are_refused(dtype):
    code = RSCode(8)
    with pytest.raises(ValueError):
        code.encode(np.zeros((2, N - 8), dtype=dtype))
    with pytest.raises(ValueError):
        code.decode(np.zeros((2, N), dtype=dtype))
    # A bool erasure mask is accepted as before.
    code.decode(np.zeros((2, N), dtype=np.uint8), np.zeros((2, N), dtype=bool))
