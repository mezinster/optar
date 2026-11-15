# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Shared test helpers."""

import hashlib


def seeded_bytes(seed: int, n: int) -> bytes:
    """Deterministic pseudo-random bytes: SHA-256 in counter mode."""
    out = bytearray()
    i = 0
    while len(out) < n:
        out += hashlib.sha256(f"{seed}:{i}".encode()).digest()
        i += 1
    return bytes(out[:n])


def parse_pdf(path) -> list[dict]:
    """Read a PDF written by optar.pdf.write_pdf back into per-page dicts."""
    import re
    import zlib

    import numpy as np

    raw = open(path, "rb").read()
    mediabox = tuple(
        float(v)
        for v in re.search(rb"/MediaBox \[([^\]]*)\]", raw).group(1).split()
    )
    pages = []
    page_re = (
        rb"/Type /Page /Parent[^\n]*?/Contents (\d+) 0 R "
        rb"/Resources << /XObject << /Im0 (\d+) 0 R"
    )
    for m in re.finditer(page_re, raw):
        content_n, image_n = int(m.group(1)), int(m.group(2))
        content_re = rb"\n%d 0 obj\n<< /Length \d+ >>\nstream\n(.*?)\nendstream" % content_n
        cs = re.search(content_re, raw, re.S)
        cm = tuple(float(v) for v in re.search(rb"q ([^c]*) cm", cs.group(1)).group(1).split())
        im = re.search(rb"\n%d 0 obj\n<<([^>]*)>>\nstream\n" % image_n, raw)
        d = im.group(1)
        length = int(re.search(rb"/Length (\d+)", d).group(1))
        data = raw[im.end():im.end() + length]
        width = int(re.search(rb"/Width (\d+)", d).group(1))
        height = int(re.search(rb"/Height (\d+)", d).group(1))
        bits = zlib.decompress(data)
        rowbytes = (width + 7) // 8
        packed = np.frombuffer(bits, np.uint8).reshape(height, rowbytes)
        px = np.unpackbits(packed, axis=1)[:, :width].astype(np.uint8) * 255
        pages.append({
            "mediabox": mediabox,
            "cm": cm,
            "width": width,
            "height": height,
            "bits": int(re.search(rb"/BitsPerComponent (\d+)", d).group(1)),
            "interpolate": re.search(rb"/Interpolate (\w+)", d).group(1) == b"true",
            "filter": re.search(rb"/Filter /(\w+)", d).group(1).decode(),
            "pixels": px,
        })
    return pages
