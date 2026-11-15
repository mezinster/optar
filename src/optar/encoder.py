# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Page encoder (port of optar.c)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import BinaryIO

import numpy as np

from optar.errors import OptarError
from optar.fec import encode_symbols
from optar.font import label_text, render_label
from optar.format import PageFormat
from optar.layout import channel_xy

MAX_PAGES = 9999


@dataclass(frozen=True)
class Page:
    number: int  # 1-based
    total: int
    pixels: np.ndarray  # uint8, (height, width)


def page_count(nbytes: int, fmt: PageFormat) -> int:
    """Number of pages for nbytes of data (0 for an empty file, as in C)."""
    return (nbytes * 8 + fmt.net_bits - 1) // fmt.net_bits


def blank_page(fmt: PageFormat, label_text: str) -> np.ndarray:
    """White page with black border, crosses and label band (optar.c border/crosses/label)."""
    b = fmt.border
    ch = fmt.chalf
    page = np.full((fmt.height, fmt.width), 0xFF, dtype=np.uint8)

    page[:b] = 0
    page[b : b + fmt.data_height, :b] = 0
    page[b : b + fmt.data_height, fmt.width - b :] = 0
    page[b + fmt.data_height : b + fmt.data_height + fmt.text_height] = 0
    page[fmt.height - b :] = 0

    for y in range(b, fmt.height - fmt.text_height - b - 2 * ch + 1, fmt.cpitch):
        for x in range(b, fmt.width - b - 2 * ch + 1, fmt.cpitch):
            page[y : y + ch, x : x + ch] = 0
            page[y : y + ch, x + ch : x + 2 * ch] = 0xFF
            page[y + ch : y + 2 * ch, x : x + ch] = 0xFF
            page[y + ch : y + 2 * ch, x + ch : x + 2 * ch] = 0

    ty = b + fmt.data_height
    page[ty : ty + fmt.text_height, b : b + fmt.data_width] = render_label(fmt, label_text)
    return page


def _page_words(buf: np.ndarray, page_index: int, fmt: PageFormat, nwords: int) -> np.ndarray:
    """The fec_smallbits-bit words of one page, MSB first, last word zero-padded."""
    sb = fmt.fec_smallbits
    start = page_index * fmt.net_bits
    stop = start + nwords * sb
    bits = np.unpackbits(buf[start // 8 : (stop + 7) // 8])
    bits = bits[start % 8 : start % 8 + nwords * sb]
    if bits.size < nwords * sb:
        bits = np.concatenate([bits, np.zeros(nwords * sb - bits.size, dtype=np.uint8)])
    weights = np.uint32(1) << np.arange(sb - 1, -1, -1, dtype=np.uint32)
    return (bits.reshape(nwords, sb).astype(np.uint32) * weights).sum(axis=1, dtype=np.uint32)


def encode(data: bytes | BinaryIO, fmt: PageFormat, label: str = "") -> Iterator[Page]:
    """Yield the pages that carry data. A stream must be seekable."""
    if not isinstance(data, bytes | bytearray | memoryview):
        data.seek(0, 2)
        data.seek(0)
        data = data.read()
    nbytes = len(data)
    total = page_count(nbytes, fmt)
    if total > MAX_PAGES:
        raise OptarError(f"too many pages: {total} needed, at most {MAX_PAGES}")
    if total == 0:
        yield Page(1, 0, blank_page(fmt, label_text(fmt, 1, 0, label)))
        return

    buf = np.frombuffer(data, dtype=np.uint8)
    x, y = channel_xy(fmt)
    px = x + fmt.border
    py = y + fmt.border
    shifts = np.arange(fmt.fec_largebits - 1, -1, -1, dtype=np.uint32)
    syms = fmt.fec_syms
    total_words = -(-nbytes * 8 // fmt.fec_smallbits)

    for i in range(total):
        nwords = min(syms, total_words - i * syms)
        words = _page_words(buf, i, fmt, nwords)
        codewords = encode_symbols(words, fmt)
        bits = (codewords[None, :] >> shifts[:, None]) & 1
        pos = np.arange(fmt.fec_largebits)[:, None] * syms + np.arange(nwords)[None, :]
        pixels = blank_page(fmt, label_text(fmt, i + 1, total, label))
        pixels[py[pos], px[pos]] = np.where(bits == 1, 0, 255).astype(np.uint8)
        yield Page(i + 1, total, pixels)
