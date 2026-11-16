# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The version-1 container: a file wrapped into a stream of self-identifying pages.

Each page's payload (fmt.net_bits // 8 bytes) holds HEADER_COPIES copies of
a page header, copy c at byte c * (page_bytes // HEADER_COPIES), and the
page's share of the body in the remaining bytes, in order. The body of all
pages is cut into Reed-Solomon codewords spread over the whole document by
positions(). encode() turns the stream into ordinary version-0 pages.
"""

from __future__ import annotations

import hashlib
import struct
import zlib
from dataclasses import dataclass

import numpy as np

from optar.encoder import MAX_PAGES
from optar.errors import FormatError, OptarError
from optar.format import (
    CODEWORD,
    CONTAINER_VERSION,
    FINGERPRINT_SIZE,
    HEADER_COPIES,
    HEADER_MAGIC,
    HEADER_SIZE,
    NAME_MAX_BYTES,
    PARITY,
    PROMISE_DEN,
    PROMISE_NUM,
    PROTECTED_MAX_BYTES,
    SPREAD_STEP,
    PageFormat,
)
from optar.rs import RSCode

__all__ = [
    "PROTECTED_MAX_BYTES",
    "Header",
    "Plan",
    "fingerprint",
    "name_bytes",
    "pages_promised",
    "plan",
    "plan_for",
    "positions",
    "read_header",
    "wrap",
]

# magic, version, parity, page, total, size, fingerprint; then the CRC-32.
_FIELDS = struct.Struct(f">{len(HEADER_MAGIC)}sBBHHQ{FINGERPRINT_SIZE}s")
_CRC = struct.Struct(">I")
assert _FIELDS.size + _CRC.size == HEADER_SIZE


def fingerprint(data: bytes) -> bytes:
    """The first FINGERPRINT_SIZE bytes of the SHA-256 of data."""
    return hashlib.sha256(data).digest()[:FINGERPRINT_SIZE]


def _check_parity(parity: int) -> None:
    if parity not in PARITY.values():
        known = ", ".join(str(v) for v in PARITY.values())
        raise FormatError(f"parity must be one of {known}, not {parity!r}")


@dataclass(frozen=True)
class Header:
    page: int  # from 1
    total: int
    size: int  # file size in bytes
    fingerprint: bytes  # FINGERPRINT_SIZE bytes
    parity: int  # parity bytes per codeword

    def pack(self) -> bytes:
        fields = _FIELDS.pack(
            HEADER_MAGIC,
            CONTAINER_VERSION,
            self.parity,
            self.page,
            self.total,
            self.size,
            self.fingerprint,
        )
        return fields + _CRC.pack(zlib.crc32(fields))


def _header_offsets(page_bytes: int) -> list[int]:
    return [c * (page_bytes // HEADER_COPIES) for c in range(HEADER_COPIES)]


def _unpack(raw: bytes) -> Header | None:
    """The header in one copy, or None if its CRC or fields are wrong."""
    if len(raw) != HEADER_SIZE:
        return None
    fields = raw[: _FIELDS.size]
    (crc,) = _CRC.unpack(raw[_FIELDS.size :])
    if zlib.crc32(fields) != crc:
        return None
    magic, version, parity, page, total, size, print_ = _FIELDS.unpack(fields)
    if magic != HEADER_MAGIC or version != CONTAINER_VERSION:
        return None
    if parity not in PARITY.values() or not 1 <= page <= total:
        return None
    return Header(page=page, total=total, size=size, fingerprint=print_, parity=parity)


def read_header(payload: bytes) -> Header | None:
    """The header of a page payload: the copies whose CRC passes must agree; else None."""
    found = set()
    for start in _header_offsets(len(payload)):
        header = _unpack(bytes(payload[start : start + HEADER_SIZE]))
        if header is not None:
            found.add(header)
    return found.pop() if len(found) == 1 else None


def name_bytes(name: str) -> bytes:
    """The file name in UTF-8, cut to NAME_MAX_BYTES on a character boundary."""
    raw = name.encode("utf-8", errors="replace")[:NAME_MAX_BYTES]
    return raw.decode("utf-8", errors="ignore").encode("utf-8")


@dataclass(frozen=True)
class Plan:
    fmt: PageFormat
    parity: int
    total: int  # pages
    page_bytes: int  # payload bytes per page
    page_body: int  # body bytes per page
    codewords: int  # m
    data_bytes: int  # m * (CODEWORD - parity)


def plan_for(total: int, fmt: PageFormat, parity: int) -> Plan:
    """The layout of a document of `total` pages (from a header's page count)."""
    _check_parity(parity)
    page_bytes = fmt.net_bits // 8
    if page_bytes // HEADER_COPIES < HEADER_SIZE:
        raise FormatError(f"page format {fmt.to_string()} is too small for the container")
    page_body = page_bytes - HEADER_COPIES * HEADER_SIZE
    m = total * page_body // CODEWORD
    return Plan(
        fmt=fmt,
        parity=parity,
        total=total,
        page_bytes=page_bytes,
        page_body=page_body,
        codewords=m,
        data_bytes=m * (CODEWORD - parity),
    )


def plan(size: int, name: str, fmt: PageFormat, parity: int) -> Plan:
    """The smallest document that holds a file of `size` bytes and its name.

    OptarError if more than MAX_PAGES pages, or parity > 0 and the stream
    exceeds PROTECTED_MAX_BYTES. Nothing is built.
    """
    probe = plan_for(1, fmt, parity)
    need = size + 1 + len(name_bytes(name))
    k = CODEWORD - parity
    m = -(-need // k)
    total = max(1, -(-(m * CODEWORD) // probe.page_body))
    if total > MAX_PAGES:
        raise OptarError(f"too many pages: {total} needed, at most {MAX_PAGES}")
    if parity and total * probe.page_bytes > PROTECTED_MAX_BYTES:
        raise OptarError(
            f"too large to protect: {total * probe.page_bytes} bytes on paper, "
            f"at most {PROTECTED_MAX_BYTES}"
        )
    return plan_for(total, fmt, parity)


def positions(p: Plan) -> np.ndarray:
    """int64 (m, CODEWORD): the body position of each byte of each codeword.

    Byte i of every codeword lies in slice i, body bytes [i*m, (i+1)*m), and
    codeword j takes the byte (j + i*SPREAD_STEP) % m of that slice.
    """
    m = p.codewords
    j = np.arange(m, dtype=np.int64)[:, None]
    i = np.arange(CODEWORD, dtype=np.int64)[None, :]
    return i * m + (j + i * SPREAD_STEP) % max(m, 1)


def pages_promised(p: Plan) -> int:
    """Whole pages the window may promise can be lost: the largest n with
    ceil(n * 255 / total) <= 3 * parity // 4; 0 without parity."""
    budget = PROMISE_NUM * p.parity // PROMISE_DEN
    return min(p.total, budget * p.total // CODEWORD)


def _codewords(data: bytes, name: str, p: Plan) -> np.ndarray:
    """uint8 (m, CODEWORD): data region row by row, then each row's parity."""
    k = CODEWORD - p.parity
    record = name_bytes(name)
    region = np.zeros(p.data_bytes, dtype=np.uint8)
    region[: len(data)] = np.frombuffer(data, dtype=np.uint8)
    region[len(data)] = len(record)
    region[len(data) + 1 : len(data) + 1 + len(record)] = np.frombuffer(record, dtype=np.uint8)
    words = region.reshape(p.codewords, k)
    if not p.parity:
        return words
    return np.hstack([words, RSCode(p.parity).encode(words)])


def _payloads(data: bytes, name: str, p: Plan) -> np.ndarray:
    """uint8 (total, page_bytes): every page's payload."""
    body = np.zeros(p.total * p.page_body, dtype=np.uint8)
    body[positions(p)] = _codewords(data, name, p)
    covered = np.zeros(p.page_bytes, dtype=bool)
    for start in _header_offsets(p.page_bytes):
        covered[start : start + HEADER_SIZE] = True
    pages = np.zeros((p.total, p.page_bytes), dtype=np.uint8)
    pages[:, ~covered] = body.reshape(p.total, p.page_body)
    print_ = fingerprint(data)
    for index in range(p.total):
        header = Header(index + 1, p.total, len(data), print_, p.parity).pack()
        packed = np.frombuffer(header, dtype=np.uint8)
        for start in _header_offsets(p.page_bytes):
            pages[index, start : start + HEADER_SIZE] = packed
    return pages


def wrap(data: bytes, name: str, fmt: PageFormat, parity: int) -> bytes:
    """The stream to give encode(): each page's payload, padded to fmt.net_bits bits."""
    data = bytes(data)
    p = plan(len(data), name, fmt, parity)
    pages = _payloads(data, name, p)
    net_bits = fmt.net_bits
    # encode() makes ceil(8 * length / net_bits) pages, so the stream ends
    # within the last page's net_bits; the last payload must still fit.
    length = p.total * net_bits // 8
    if -(-((p.total - 1) * net_bits + 8 * p.page_bytes) // 8) > length:
        raise FormatError(f"page format {fmt.to_string()} cannot end a stream on a page")
    out = np.zeros(length + 2, dtype=np.uint8)
    for index in range(p.total):
        byte, shift = divmod(index * net_bits, 8)
        page = pages[index]
        if shift == 0:
            out[byte : byte + p.page_bytes] |= page
        else:
            out[byte : byte + p.page_bytes] |= page >> shift
            out[byte + 1 : byte + 1 + p.page_bytes] |= page << (8 - shift)
    return out[:length].tobytes()
