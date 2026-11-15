# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import io

import numpy as np

from optar.encoder import blank_page, encode, page_count
from optar.format import PageFormat
from optar.layout import channel_xy
from tests.helpers import seeded_bytes

F = PageFormat(65, 93)
PAGE_BYTES = F.net_bits // 8  # 199773


def test_page_counts():
    assert [page_count(n, F) for n in (0, 1, PAGE_BYTES, PAGE_BYTES + 1)] == [0, 1, 1, 2]
    assert [p.number for p in encode(b"", F)] == [1]
    assert len(list(encode(seeded_bytes(1, PAGE_BYTES), F))) == 1
    pages = list(encode(seeded_bytes(1, PAGE_BYTES + 1), F))
    assert [(p.number, p.total) for p in pages] == [(1, 2), (2, 2)]


def test_blank_page_structure():
    p = blank_page(F, "")
    assert p.shape == (2242, 1546) and p.dtype == np.uint8
    assert not p[:2].any() and not p[:, :2].any() and not p[:, -2:].any() and not p[-2:].any()
    assert np.array_equal(p[2:8, 2:8] == 0, np.kron(np.eye(2, dtype=bool), np.ones((3, 3), bool)))
    x, y = channel_xy(F)
    assert (p[y + 2, x + 2] == 255).all()


def test_all_ones_data_blackens_written_symbols_only():
    page = next(encode(b"\xff" * 3, F))  # 24 bits = 2 words of 0xFFF
    x, y = channel_xy(F)
    bits = page.pixels[y + 2, x + 2] == 0
    idx = np.flatnonzero(bits)
    assert len(idx) == 48 and set(idx % F.fec_syms) == {0, 1}


def test_stream_input_equals_bytes_input():
    data = seeded_bytes(3, 5000)
    a = [p.pixels for p in encode(data, F)]
    b = [p.pixels for p in encode(io.BytesIO(data), F)]
    assert all(np.array_equal(i, j) for i, j in zip(a, b, strict=True))

