# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""One-off developer script: convert font.h (GIMP header image) to src/optar/data/font.png.

A pixel is white when the colour map entry of its index has bit 7 set in the red
channel (as in text_block() of optar.c). Run from anywhere: python tools/extract_font.py
"""

import re
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 1500, 24


def parse(text: str) -> np.ndarray:
    cmap_start = text.index("header_data_cmap[256][3]")
    data_start = text.index("header_data[36000]")
    cmap_text = text[cmap_start:data_start]
    cmap_red = [int(m) & 0xFF for m in re.findall(r"\{\s*(-?\d+)\s*,", cmap_text)]
    cmap_red += [0] * (256 - len(cmap_red))  # static storage: unlisted entries are zero
    body = text[data_start:]
    body = body[body.index("{") + 1 : body.index("}")]
    indices = np.array([int(m) & 0xFF for m in re.findall(r"-?\d+", body)], dtype=np.uint8)
    if indices.size != WIDTH * HEIGHT:
        raise SystemExit(f"expected {WIDTH * HEIGHT} pixels, found {indices.size}")
    white = (np.array(cmap_red, dtype=np.uint8) & 0x80) != 0
    return white[indices].reshape(HEIGHT, WIDTH)


def main() -> None:
    text = (ROOT / "font.h").read_text(errors="replace")
    white = parse(text)
    out = ROOT / "src" / "optar" / "data" / "font.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(white).save(out, optimize=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
