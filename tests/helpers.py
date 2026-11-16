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


def fake_scan(
    pixels,
    *,
    scale=3,
    margin=60,
    rotate=0.0,
    blur=0.0,
    noise=0.0,
    specks=0,
    flips=0,
    seed=0,
    fmt=None,
):
    """A synthetic scan of an encoded page (uint8, 2-D, 0 black, 255 white).

    Order: scale and margin, flips, specks, rotate, blur, noise. Specks are
    black 4 x 4 squares in the margin, at least 8 pixels from the page and the
    image edge; flips invert whole page pixels at channel-bit positions (needs
    fmt). With rotate=0 there is no resampling. Deterministic for a seed.
    """
    import numpy as np
    from PIL import Image, ImageFilter

    from optar.layout import channel_xy

    if flips > 0 and fmt is None:
        raise ValueError("fake_scan needs fmt when flips > 0")
    rng = np.random.default_rng(seed)
    pixels = np.asarray(pixels, np.uint8)
    ph, pw = pixels.shape[0] * scale, pixels.shape[1] * scale
    out = np.full((ph + 2 * margin, pw + 2 * margin), 255, np.uint8)
    out[margin : margin + ph, margin : margin + pw] = np.kron(
        pixels, np.ones((scale, scale), np.uint8)
    )

    if flips > 0:
        xs, ys = channel_xy(fmt)
        for i in rng.choice(xs.size, flips, replace=False):
            y = margin + (int(ys[i]) + fmt.border) * scale
            x = margin + (int(xs[i]) + fmt.border) * scale
            out[y : y + scale, x : x + scale] = 255 - out[y : y + scale, x : x + scale]

    if specks > 0:
        gap, size = 8, 4
        hh, ww = out.shape
        placed = []
        for _ in range(specks):
            for _attempt in range(10000):
                y = int(rng.integers(gap, hh - gap - size + 1)) if hh >= 2 * gap + size else -1
                x = int(rng.integers(gap, ww - gap - size + 1)) if ww >= 2 * gap + size else -1
                if x < 0 or y < 0:
                    raise ValueError("image too small for specks")
                near_page = (
                    y + size + gap > margin
                    and y < margin + ph + gap
                    and x + size + gap > margin
                    and x < margin + pw + gap
                )
                overlaps = any(abs(y - py) < size and abs(x - px) < size for py, px in placed)
                if not near_page and not overlaps:
                    placed.append((y, x))
                    out[y : y + size, x : x + size] = 0
                    break
            else:
                raise ValueError("no room for specks in the margin")

    if rotate or blur:
        im = Image.fromarray(out)
        if rotate:
            im = im.rotate(rotate, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=255)
        if blur:
            im = im.filter(ImageFilter.GaussianBlur(blur))
        out = np.asarray(im, np.uint8).copy()

    if noise:
        noisy = out + rng.normal(0.0, noise, out.shape)
        out = np.clip(np.rint(noisy), 0, 255).astype(np.uint8)
    return out


def save_scan(path, array) -> None:
    """Write a 2-D uint8 array as an 8-bit grayscale PNG."""
    import numpy as np
    from PIL import Image

    Image.fromarray(np.ascontiguousarray(array, np.uint8)).save(path, format="PNG")


def reference_remove_border_dirt(img, fill_cut):
    """Direct queue-based port of remove_dirt_from_border, for small images."""
    from collections import deque

    import numpy as np

    h, w = img.shape
    ary = img.tolist()
    newary = [[0xFF] * w for _ in range(h)]

    def fill(x, y, test):
        que = deque()

        def try_copy_white(x, y):
            if test and ary[y][x] < fill_cut:
                return
            if not newary[y][x]:
                return
            newary[y][x] = 0
            que.append((x, y))

        try_copy_white(x, y)
        while que:
            x, y = que.popleft()
            if x + 1 < w:
                try_copy_white(x + 1, y)
            if x:
                try_copy_white(x - 1, y)
            if y + 1 < h:
                try_copy_white(x, y + 1)
            if y:
                try_copy_white(x, y - 1)

    fill(0, 0, 1)
    fill(w >> 1, 0, 1)
    fill(w - 1, 0, 1)
    fill(0, h >> 1, 1)
    fill(0, h - 1, 1)
    fill(w - 1, h - 1, 1)
    fill(w - 1, h >> 1, 1)
    fill(w >> 1, h - 1, 1)
    fill(w >> 1, h >> 1, 0)
    return np.asarray(img, np.uint8) | np.array(newary, np.uint8)


# Degraded scan cases shared by the unit and oracle decoder tests: fake_scan
# keyword arguments (cases with flips need fmt= as well). They are defined for
# scans as decoders see them: saved with save_scan and loaded through
# optar.imageio.read_scan (gamma linearisation, like C read_png). Every case
# must decode with no uncorrectable symbol and at most 2 corrected bits each.
DEGRADED = {
    "clean1": dict(scale=1),
    "clean3": dict(scale=3),
    "rotated": dict(scale=3, margin=120, rotate=0.3),
    "blurred": dict(scale=3, blur=1.0),
    "noisy": dict(scale=3, noise=12),
    "specks": dict(scale=3, specks=30),
    "flips": dict(scale=3, flips=200),
    "combined": dict(scale=3, margin=120, rotate=0.2, blur=0.8, noise=8, specks=20, flips=100),
}


def simulate_scan(
    pixels,
    layout,
    dpi,
    *,
    rotate_deg=0.4,
    blur=1.0,
    noise=6.0,
    seed=1,
    quarter_turns=0,
):
    """A grey scan of a printed page (uint8, 2-D, 0 black, 255 white).

    Order: 600 dpi print (each page pixel is layout.dots.printer_dots printer
    dots wide, nearest neighbour), Gaussian blur (sigma blur, in 600 dpi dots),
    rotation by rotate_deg degrees (bicubic, expanded, white fill), a white
    border of 0.2 inch, box resampling to dpi, noise, then np.rot90(-quarter_turns)
    so that np.rot90(scan, quarter_turns) is upright. Deterministic for a seed.

    The default blur of 1.0 is the mild blur behind the project's evidence; Standard
    (3-dot) pages stop decoding at about 2.0.
    """
    import numpy as np
    from PIL import Image, ImageFilter

    d = layout.dots.printer_dots
    border = 120
    rng = np.random.default_rng(seed)
    im = Image.fromarray(np.asarray(pixels, np.uint8))
    big = im.resize((im.width * d, im.height * d), Image.Resampling.NEAREST)
    if blur:
        big = big.filter(ImageFilter.GaussianBlur(blur))
    if rotate_deg:
        big = big.rotate(
            rotate_deg, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=255
        )
    pad = Image.new("L", (big.width + 2 * border, big.height + 2 * border), 255)
    pad.paste(big, (border, border))
    size = (round(pad.width * dpi / 600), round(pad.height * dpi / 600))
    out = pad.resize(size, Image.Resampling.BOX)
    a = np.asarray(out).astype(np.float32)
    if noise:
        a = a + rng.normal(0.0, noise, a.shape)
    a = np.clip(a, 0, 255).astype(np.uint8)
    return np.ascontiguousarray(np.rot90(a, -quarter_turns))
