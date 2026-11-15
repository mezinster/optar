# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Error correction: the Golay (24,12) code and extended Hamming codes.

Ports golay.c, hamming()/split() from optar.c and ungolay()/unhamming()/
shrink() from unoptar.c.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from optar.format import PageFormat

# For each dodecahedron face (1-12) the 5 adjacent faces (see golay.c).
_DODECAHEDRON = (
    (2, 3, 4, 5, 6),
    (1, 3, 6, 7, 8),
    (1, 2, 4, 8, 9),
    (1, 3, 5, 9, 10),
    (1, 4, 6, 10, 11),
    (1, 2, 5, 7, 11),
    (2, 6, 8, 11, 12),
    (2, 3, 7, 9, 12),
    (3, 4, 8, 10, 12),
    (4, 5, 9, 11, 12),
    (5, 6, 7, 10, 12),
    (7, 8, 9, 10, 11),
)

_POP12 = np.array([bin(i).count("1") for i in range(4096)], dtype=np.uint8)
_CHUNK = 256


def _parity(x: np.ndarray) -> np.ndarray:
    """Parity of each element (uint64 in, uint64 out), as parity.c."""
    x = x ^ (x >> np.uint64(32))
    x = x ^ (x >> np.uint64(16))
    x = x ^ (x >> np.uint64(8))
    x = x ^ (x >> np.uint64(4))
    x = x ^ (x >> np.uint64(2))
    x = x ^ (x >> np.uint64(1))
    return x & np.uint64(1)


def _popcount24(x: np.ndarray) -> np.ndarray:
    return _POP12[x >> 12] + _POP12[x & 0xFFF]


@lru_cache(maxsize=1)
def _golay_table() -> np.ndarray:
    masks = []
    for faces in _DODECAHEDRON:
        mask = 0xFFF
        for f in faces:
            mask ^= 1 << (f - 1)
        masks.append(mask)
    data = np.arange(4096, dtype=np.uint64)
    prty = np.zeros(4096, dtype=np.uint64)
    for mask in masks:
        prty = (prty << np.uint64(1)) | _parity(data & np.uint64(mask))
    table = ((data << np.uint64(12)) | prty).astype(np.uint32)
    table.flags.writeable = False
    return table


def golay_table() -> np.ndarray:
    """The 4096 Golay codewords, entry d is (d << 12) | parity12. Read-only."""
    return _golay_table()


def serialize_table(table: np.ndarray) -> bytes:
    """Each entry as 4 big-endian bytes, concatenated."""
    return np.asarray(table).astype(">u4").tobytes()


def _split(x: np.ndarray, bit: int) -> np.ndarray:
    low = x & np.uint64((1 << bit) - 1)
    high = x ^ low
    return (high << np.uint64(1)) | low


def _hamming_encode(words: np.ndarray, fmt: PageFormat) -> np.ndarray:
    order = fmt.fec_order
    x = words.astype(np.uint64) & np.uint64((1 << fmt.fec_smallbits) - 1)
    x = x << np.uint64(3)
    if order >= 3:
        x = _split(x, 4)
    if order >= 4:
        x = _split(x, 8)
    if order >= 5:
        x = _split(x, 16)
        x |= _parity(x & np.uint64(0xFFFF0000)) << np.uint64(16)
    if order >= 4:
        x |= _parity(x & np.uint64(0xFF00FF00)) << np.uint64(8)
    if order >= 3:
        x |= _parity(x & np.uint64(0xF0F0F0F0)) << np.uint64(4)
    x |= _parity(x & np.uint64(0xCCCCCCCC)) << np.uint64(2)
    x |= _parity(x & np.uint64(0xAAAAAAAA)) << np.uint64(1)
    x |= _parity(x)
    return x.astype(np.uint32)


def encode_symbols(words: np.ndarray, fmt: PageFormat) -> np.ndarray:
    """Encode data words into codewords of fmt.fec_largebits bits."""
    words = np.asarray(words, dtype=np.uint32)
    if fmt.fec_order == 1:
        return golay_table()[words & 0xFFF]
    return _hamming_encode(words, fmt)


def _golay_decode(cw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    table = golay_table()
    cw = cw & np.uint32(0xFFFFFF)
    out = cw >> 12
    errs = np.zeros(cw.shape, dtype=np.int8)
    bad = np.flatnonzero(table[out] != cw)
    for start in range(0, len(bad), _CHUNK):
        idx = bad[start : start + _CHUNK]
        dist = _popcount24(table[None, :] ^ cw[idx, None])  # (n, 4096)
        best = dist.argmin(axis=1)  # first minimum, as C scans in order
        best_d = dist[np.arange(len(idx)), best]
        ok = best_d <= 3
        out[idx[ok]] = best[ok].astype(np.uint32)
        errs[idx] = np.where(ok, best_d.astype(np.int8), np.int8(-1))
    return out, errs


def _shrink(x: np.ndarray, bitpos: int) -> np.ndarray:
    x = x & ~np.uint64(1 << bitpos)
    low = x & np.uint64((1 << bitpos) - 1)
    high = x ^ low
    return (high >> np.uint64(1)) | low


def _hamming_decode(cw: np.ndarray, fmt: PageFormat) -> tuple[np.ndarray, np.ndarray]:
    order = fmt.fec_order
    x = cw.astype(np.uint64) & np.uint64((1 << fmt.fec_largebits) - 1)
    bugpos = np.zeros(x.shape, dtype=np.uint64)
    if order >= 5:
        bugpos |= _parity(x & np.uint64(0xFFFF0000)) << np.uint64(4)
    if order >= 4:
        bugpos |= _parity(x & np.uint64(0xFF00FF00)) << np.uint64(3)
    if order >= 3:
        bugpos |= _parity(x & np.uint64(0xF0F0F0F0)) << np.uint64(2)
    bugpos |= _parity(x & np.uint64(0xCCCCCCCC)) << np.uint64(1)
    bugpos |= _parity(x & np.uint64(0xAAAAAAAA))
    flagged = bugpos != 0
    x = np.where(flagged, x ^ (np.uint64(1) << bugpos), x)
    odd = _parity(x) == 1
    errs = np.zeros(x.shape, dtype=np.int8)
    errs[flagged & ~odd] = 1
    errs[~flagged & odd] = 1
    errs[flagged & odd] = -1
    if order >= 5:
        x = _shrink(x, 16)
    if order >= 4:
        x = _shrink(x, 8)
    if order >= 3:
        x = _shrink(x, 4)
    x >>= np.uint64(3)
    return x.astype(np.uint32), errs


def decode_symbols(codewords: np.ndarray, fmt: PageFormat) -> tuple[np.ndarray, np.ndarray]:
    """Decode codewords to (words uint32, errors int8).

    errors is the number of corrected bits, or -1 if uncorrectable.
    """
    cw = np.asarray(codewords, dtype=np.uint32)
    if fmt.fec_order == 1:
        return _golay_decode(cw)
    return _hamming_decode(cw, fmt)
