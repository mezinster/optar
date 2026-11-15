#!/usr/bin/env python3
# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Convert binary PGM (P5, maxval 255) pages written by optar into 8-bit
grayscale PNG files that unoptar can read. Standard library only.

usage: pgm2png.py [--scale N] page_0001.pgm [page_0002.pgm ...]

Each foo.pgm becomes foo.png next to it. --scale N repeats every pixel
N times in both directions (nearest neighbour), imitating a scan at a
higher resolution than the page was rendered at.
"""
import struct
import sys
import zlib


def read_pgm(path):
    with open(path, "rb") as f:
        data = f.read()
    fields = []
    pos = 0
    while len(fields) < 4:
        while data[pos:pos + 1].isspace():
            pos += 1
        if data[pos:pos + 1] == b"#":
            pos = data.index(b"\n", pos) + 1
            continue
        end = pos
        while not data[end:end + 1].isspace():
            end += 1
        fields.append(data[pos:end])
        pos = end
    pos += 1  # the single whitespace byte that ends the header
    if fields[0] != b"P5" or int(fields[3]) != 255:
        raise SystemExit(f"{path}: expected a binary PGM with maxval 255")
    width, height = int(fields[1]), int(fields[2])
    pixels = data[pos:pos + width * height]
    if len(pixels) != width * height:
        raise SystemExit(f"{path}: truncated pixel data")
    return width, height, pixels


def chunk(kind, payload):
    crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)


def write_png(path, width, height, pixels, scale):
    rows = []
    for y in range(height):
        row = pixels[y * width:(y + 1) * width]
        if scale > 1:
            row = bytes(b for b in row for _ in range(scale))
        rows.extend([b"\x00" + row] * scale)
    header = struct.pack(">IIBBBBB", width * scale, height * scale, 8, 0, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", header))
        f.write(chunk(b"IDAT", zlib.compress(b"".join(rows), 6)))
        f.write(chunk(b"IEND", b""))


def main(argv):
    scale = 1
    if argv[:1] == ["--scale"]:
        scale = int(argv[1])
        argv = argv[2:]
    if not argv or scale < 1:
        raise SystemExit(__doc__)
    for src in argv:
        dst = src[:-4] + ".png" if src.endswith(".pgm") else src + ".png"
        width, height, pixels = read_pgm(src)
        write_png(dst, width, height, pixels, scale)


if __name__ == "__main__":
    main(sys.argv[1:])
