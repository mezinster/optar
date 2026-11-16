# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The version-1 container: a file wrapped into a stream of self-identifying pages.

Each page's payload (fmt.net_bits // 8 bytes) holds HEADER_COPIES copies of
a page header, copy c at byte c * (page_bytes // HEADER_COPIES), and the
page's share of the body in the remaining bytes, in order. The body of all
pages is cut into Reed-Solomon codewords spread over the whole document by
positions(). encode() turns the stream into ordinary version-0 pages.

Reading back: page_payload() turns each decoded page into its payload and
erasures, and unwrap() reassembles, repairs and checks the file.
"""

from __future__ import annotations

import hashlib
import struct
import zlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from optar.decoder import PageResult

__all__ = [
    "BEST_EFFORT_PAGES",
    "PROTECTED_MAX_BYTES",
    "Header",
    "PagePayload",
    "Plan",
    "Unwrapped",
    "document_plan",
    "fingerprint",
    "name_bytes",
    "page_payload",
    "pages_promised",
    "plan",
    "plan_for",
    "positions",
    "read_header",
    "unwrap",
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
        if len(self.fingerprint) != FINGERPRINT_SIZE:
            raise ValueError(
                f"fingerprint must be {FINGERPRINT_SIZE} bytes, not {len(self.fingerprint)}"
            )
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


def _covered(page_bytes: int) -> np.ndarray:
    """bool (page_bytes,): True for the payload bytes under a header copy."""
    covered = np.zeros(page_bytes, dtype=bool)
    for start in _header_offsets(page_bytes):
        covered[start : start + HEADER_SIZE] = True
    return covered


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
    return _positions(p, 0, p.codewords)


def _positions(p: Plan, first: int, stop: int) -> np.ndarray:
    """positions(p) for codewords first .. stop-1 only."""
    m = p.codewords
    j = np.arange(first, stop, dtype=np.int64)[:, None]
    i = np.arange(CODEWORD, dtype=np.int64)[None, :]
    return i * m + (j + i * SPREAD_STEP) % max(m, 1)


def pages_promised(p: Plan) -> int:
    """Whole pages the window may promise can be lost, any n of them, adjacent
    or not: the largest n with n * (ceil(page_body / codewords) + 1) <= 3 *
    parity // 4; 0 without parity.

    One page covers page_body body bytes, which touch at most
    ceil(page_body / codewords) + 1 slices, and a codeword has one byte in
    each slice: each lost page can cost a codeword that many bytes.
    """
    budget = PROMISE_NUM * p.parity // PROMISE_DEN
    if budget < 1 or p.codewords == 0:
        return 0
    per_page = -(-p.page_body // p.codewords) + 1
    return min(p.total, budget // per_page)


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
    covered = _covered(p.page_bytes)
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


# Reading


@dataclass(frozen=True)
class PagePayload:
    data: bytes  # fmt.net_bits // 8 bytes
    erased: np.ndarray  # bool, same length: bytes inside symbols Golay could not correct


def page_payload(result: PageResult, fmt: PageFormat) -> PagePayload:
    """A page's payload from decode_located(..., detail=True) or decode_page(..., detail=True).

    The bits are packed MSB first and the odd bits past the last whole byte
    dropped. Symbol s carries payload bits [s * fec_smallbits, (s + 1) *
    fec_smallbits); a byte is erased if any of its bits lies in a symbol
    listed in result.lost_symbols.
    """
    if result.lost_symbols is None:
        raise ValueError("the page must be decoded with detail=True")
    bits = np.asarray(result.bits, dtype=np.uint8)
    if bits.shape != (fmt.net_bits,):
        raise ValueError(f"expected {fmt.net_bits} payload bits, got shape {bits.shape}")
    page_bytes = fmt.net_bits // 8
    lost = np.zeros(fmt.fec_syms, dtype=bool)
    lost[result.lost_symbols] = True
    bad_bits = np.repeat(lost, fmt.fec_smallbits)[: page_bytes * 8]
    return PagePayload(
        data=np.packbits(bits[: page_bytes * 8]).tobytes(),
        erased=bad_bits.reshape(page_bytes, 8).any(axis=1),
    )


@dataclass(frozen=True)
class Unwrapped:
    """What unwrap() made of a document's pages.

    Only `verified` says the file is the original. `failed == 0` and
    `worst_used <= budget` do not: a codeword with more wrong bytes than its
    parity can correct may be "corrected" into another valid codeword, and
    without parity nothing is checked at all. `name` is outside the
    fingerprint, which covers the file's bytes only: it is as trustworthy as
    the codewords it was read from, and is untrusted text even when
    `verified`.
    """

    data: bytes | None  # the file, cut to size; None if any codeword holding file bytes failed
    # The file as far as it could be recovered, cut to the header's size:
    # corrected codewords where correction succeeded, bytes as read where it
    # failed or there is no parity, zeros for unrepaired bytes of missing pages.
    # The same object as data when data is not None. None when it was not
    # built: data is None and fewer than 1 / BEST_EFFORT_PAGES of the pages
    # were supplied (see unwrap). It MAY CONTAIN WRONG BYTES and is never
    # verified: it is only for an explicit "save anyway".
    best_effort: bytes | None
    name: str  # "" if unreadable; not covered by the fingerprint
    verified: bool  # data is not None and its fingerprint equals the header's
    repaired_bytes: int  # bytes parity changed or filled
    # Max over codewords of 2 * errors + erasures; a codeword that failed
    # counts as max(erasures, budget + 1), so worst_used > budget iff failed.
    worst_used: int
    budget: int  # parity bytes per codeword
    # Codewords not corrected. When best_effort is None the codewords were
    # not all looked at and this is only a lower bound (at least 1).
    failed: int
    page_damage: dict[int, int]  # page -> codeword bytes of it wrong or erased (pages with any)
    missing: tuple[int, ...]  # page numbers not supplied


# Codewords gathered, decoded and scattered per step of unwrap().
_UNWRAP_ROWS = 16384
# Codewords looked at per step of the search for one beyond repair.
_SCAN_ROWS = 2048
# The best-effort file of a document that cannot be recovered is built only
# when at least one page in this many was supplied.
BEST_EFFORT_PAGES = 2


def document_plan(header: Header, fmt: PageFormat) -> Plan | None:
    """The plan of the document a header describes, or None if wrap() writes
    no such document in fmt.

    wrap() writes at most MAX_PAGES pages (and with parity at most
    PROTECTED_MAX_BYTES), in the fewest pages that hold the file, a name
    length byte and a name of at most NAME_MAX_BYTES bytes. So the page count
    is in proportion to the file size the header gives: a header cannot claim
    many pages for a small file, or a large file in few.
    """
    if header.size < 0 or not 1 <= header.page <= header.total <= MAX_PAGES:
        return None
    try:
        p = plan_for(header.total, fmt, header.parity)
        fewer = plan_for(header.total - 1, fmt, header.parity).data_bytes
    except FormatError:
        return None
    if p.parity and p.total * p.page_bytes > PROTECTED_MAX_BYTES:
        return None
    if header.size + 1 > p.data_bytes:
        return None  # more than the pages hold
    if header.total > 1 and header.size + 1 + NAME_MAX_BYTES <= fewer:
        return None  # fewer pages would have held it, whatever its name
    return p


def _beyond_repair(p: Plan, absent: np.ndarray, rows: int) -> tuple[int, int]:
    """Whether the absent pages alone put a codeword holding the file beyond
    repair: (codewords found so, the most bytes one of them has on absent
    pages), or (0, 0) if there is none.

    absent is bool (total,), True for a page not supplied; rows is how many
    codewords hold the file. The search stops at the first step of
    _SCAN_ROWS codewords that has one, so the count is a lower bound.
    """
    for first in range(0, rows, _SCAN_ROWS):
        stop = min(rows, first + _SCAN_ROWS)
        gone = absent[_positions(p, first, stop) // p.page_body].sum(axis=1)
        over = gone > p.parity
        if over.any():
            return int(np.count_nonzero(over)), int(gone.max())
    return 0, 0


def unwrap(header: Header, fmt: PageFormat, pages: Mapping[int, PagePayload]) -> Unwrapped:
    """The file of a document from its page payloads, repaired by its parity.

    `pages` maps page numbers (from 1) to payloads; numbers outside the
    header's page count are ignored and missing pages are all-erased. With
    parity 0 nothing is repaired: a codeword is taken as read, and fails if
    any of its bytes is erased. A codeword that cannot be corrected is
    reported, never guessed; only the fingerprint decides `verified`.
    FormatError if the header describes a document no wrap() writes
    (document_plan).

    The header and the pages are untrusted. Memory and time are in
    proportion to the pages supplied, not to what the header claims: the
    pages are not laid out in a body of the claimed size, and when the pages
    not supplied alone put the file beyond repair and fewer than 1 /
    BEST_EFFORT_PAGES of the pages were supplied, the result says so at once,
    with `best_effort` None and `failed` a lower bound. With at least that
    share of the pages the best-effort file is built.
    """
    p = document_plan(header, fmt)
    if p is None:
        raise FormatError(
            f"the pages describe a document that cannot exist: {header.total} pages "
            f"for a file of {header.size} bytes"
        )
    k = CODEWORD - p.parity
    m = p.codewords
    size = header.size
    keep = ~_covered(p.page_bytes)
    # Row 0 stands for every page not supplied: zeros, all erased.
    stack = [np.zeros(p.page_body, dtype=np.uint8)]
    gone = [np.ones(p.page_body, dtype=bool)]
    row_of = np.zeros(p.total, dtype=np.intp)
    for number in sorted(n for n in pages if 1 <= n <= p.total):
        page = pages[number]
        data = np.frombuffer(page.data, dtype=np.uint8)
        erased = np.asarray(page.erased, dtype=bool)
        if data.shape != (p.page_bytes,) or erased.shape != data.shape:
            raise ValueError(
                f"page {number}: payload must be {p.page_bytes} bytes with an erasure "
                f"mask of the same length"
            )
        row_of[number - 1] = len(stack)
        stack.append(data[keep])
        gone.append(erased[keep])
    absent = row_of == 0
    missing = tuple(int(n) + 1 for n in np.flatnonzero(absent))

    if missing and (p.total - len(missing)) * BEST_EFFORT_PAGES < p.total:
        hopeless, most = _beyond_repair(p, absent, -(-size // k))
        if hopeless:
            # Every codeword byte of a page not supplied counts as damage.
            starts = np.arange(p.total) * p.page_body
            held = np.clip(m * CODEWORD - starts, 0, p.page_body)
            return Unwrapped(
                data=None,
                best_effort=None,
                name="",
                verified=False,
                repaired_bytes=0,
                worst_used=max(most, p.parity + 1),
                budget=p.parity,
                failed=hopeless,
                page_damage={n: int(held[n - 1]) for n in missing if held[n - 1]},
                missing=missing,
            )

    body = np.stack(stack)
    lost = np.stack(gone)
    del stack, gone
    code = RSCode(p.parity) if p.parity else None
    # Only the codewords that hold the file and its name are kept.
    kept = min(m, -(-(size + 1 + NAME_MAX_BYTES) // k))
    region = np.empty((kept, k), dtype=np.uint8)
    ok = np.empty(m, dtype=bool)
    worst = repaired = 0
    damage = np.zeros(p.total, dtype=np.int64)
    for first in range(0, m, _UNWRAP_ROWS):
        stop = min(m, first + _UNWRAP_ROWS)
        pos = _positions(p, first, stop)
        on_page = pos // p.page_body
        pos -= on_page * p.page_body  # now the byte's place within its page
        row = row_of[on_page]
        received, erased = body[row, pos], lost[row, pos]
        del row
        erasures = erased.sum(axis=1)
        if code is None:
            words, row_ok = received, erasures == 0
            used = np.zeros(len(pos), dtype=np.int64)
        else:
            result = code.decode(received, erased)
            words, row_ok = result.words, result.ok
            used = 2 * result.errors + erasures
        used = np.where(row_ok, used, np.maximum(erasures, p.parity + 1))
        # Wrong or erased: in a corrected codeword every byte changed or
        # filled; in a failed one only the erased bytes are known.
        bad = erased | ((words != received) & row_ok[:, None])
        repaired += int(bad[row_ok].sum())
        damage += np.bincount(on_page[bad], minlength=p.total)
        worst = max(worst, int(used.max(initial=0)))
        if first < kept:
            region[first : min(stop, kept)] = words[: kept - first, :k]
        ok[first:stop] = row_ok
    region = region.reshape(-1)

    data_out = region[:size].tobytes() if ok[: -(-size // k)].all() else None
    return Unwrapped(
        data=data_out,
        best_effort=data_out if data_out is not None else region[:size].tobytes(),
        name=_read_name(region, ok, size, k),
        verified=data_out is not None and fingerprint(data_out) == header.fingerprint,
        repaired_bytes=repaired,
        worst_used=worst,
        budget=p.parity,
        failed=int(np.count_nonzero(~ok)),
        page_damage={int(n) + 1: int(damage[n]) for n in np.flatnonzero(damage)},
        missing=missing,
    )


def _read_name(region: np.ndarray, ok: np.ndarray, size: int, k: int) -> str:
    """The name record after a file of `size` bytes; "" if failed or malformed."""
    if not ok[size // k]:
        return ""
    end = size + 1 + int(region[size])
    if end > len(region) or not ok[size // k : (end - 1) // k + 1].all():
        return ""
    try:
        return region[size + 1 : end].tobytes().decode("utf-8")
    except UnicodeDecodeError:
        return ""
