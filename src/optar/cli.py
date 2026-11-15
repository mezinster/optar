# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The `optar` command line: encode a file to pages, decode scans back to a file."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Iterator
from pathlib import Path

import numpy as np
from PIL import Image

from optar import __version__
from optar.decoder import BitPacker, decode_pages
from optar.encoder import check_encodable, encode
from optar.errors import DecodeError, FormatError, OptarError
from optar.fileio import io_error, replacing
from optar.format import PAPERS, PageFormat, Paper
from optar.imageio import read_scan, write_pgm, write_png
from optar.pdf import write_pdf

PAPER_HINT = "Check that --paper matches the printout and that the page is scanned upright."
ACTUAL_SIZE = 'Print at actual size (100%), not "fit to page".'


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="optar", description="Store files on paper.")
    parser.add_argument("--version", action="version", version=f"optar {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--paper",
            type=str.lower,
            choices=list(PAPERS),
            default="a4",
            help="paper size (default: a4)",
        )
        p.add_argument("--format", metavar="STRING", help="override the page format")

    enc = sub.add_parser("encode", help="encode a file into printable pages")
    enc.add_argument("input", metavar="INPUT", help="file to encode")
    enc.add_argument(
        "-o", dest="output", metavar="BASE", help="output base name (default: optar_out)"
    )
    enc.add_argument(
        "--to",
        choices=["pdf", "png", "pgm"],
        default="pdf",
        help="output type: one PDF (default), or PNG or PGM page files",
    )
    enc.add_argument(
        "--label", help="text printed on each page (default: the file name given with -o)"
    )
    common(enc)

    dec = sub.add_parser("decode", help="decode scanned pages back into a file")
    dec.add_argument("base", metavar="BASE", help="scans are BASE_0001.png, BASE_0002.png, ...")
    dec.add_argument("-o", dest="output", metavar="OUTPUT", help="output file (default: stdout)")
    dec.add_argument("--debug-images", action="store_true", help="write BASE_NNNN_debug.png")
    common(dec)
    return parser


def _eprint(message: str) -> None:
    print(message, file=sys.stderr)


def _resolve_format(args: argparse.Namespace) -> tuple[Paper, PageFormat]:
    paper = PAPERS[args.paper]
    fmt = PageFormat.parse(args.format) if args.format else PageFormat.for_paper(paper)
    return paper, fmt


def _encode(args: argparse.Namespace) -> int:
    paper, fmt = _resolve_format(args)
    if not fmt.fits(paper):
        raise FormatError(f"format {fmt.to_string()} does not fit on {paper.name} paper")
    try:
        with open(args.input, "rb") as f:
            data = f.read()
    except OSError as e:
        raise io_error("read", args.input, e) from e

    check_encodable(len(data), fmt)  # before any file is created
    base = args.output or "optar_out"
    label = args.label if args.label is not None else Path(args.output or "").name
    written: list[str] = []
    if args.to == "pdf":
        path = f"{base}.pdf"
        with replacing(path) as temp:
            count = write_pdf(temp, (page.pixels for page in encode(data, fmt, label)), paper)
        written.append(f"{path} ({count} page{'s' if count != 1 else ''})")
    else:
        writer = write_png if args.to == "png" else write_pgm
        for page in encode(data, fmt, label):
            path = f"{base}_{page.number:04d}.{args.to}"
            with replacing(path) as temp:
                writer(temp, page.pixels)
            written.append(path)
    for item in written:
        _eprint(f"wrote {item}")
    _eprint(ACTUAL_SIZE)
    return 0


def _save_debug_image(path: str, image: np.ndarray) -> None:
    Image.fromarray(np.ascontiguousarray(image).astype(np.uint8)).save(path, format="PNG")


def _decode(args: argparse.Namespace) -> int:
    _, fmt = _resolve_format(args)
    name = os.path.basename(args.base)
    gap = False

    def scan_name(number: int) -> str:
        return f"{name}_{number:04d}.png"

    def scans() -> Iterator[np.ndarray]:
        nonlocal gap
        number = 1
        while True:
            path = f"{args.base}_{number:04d}.png"
            if not os.path.exists(path):
                if number > 1 and os.path.exists(f"{args.base}_{number + 1:04d}.png"):
                    _eprint(
                        f"optar: {scan_name(number)} is missing but {scan_name(number + 1)} exists"
                    )
                    gap = True
                return
            yield read_scan(path)
            number += 1

    packer = BitPacker()
    chunks: list[bytes] = []
    uncorrectable = 0
    pages = decode_pages(scans(), fmt, debug=args.debug_images)
    try:
        for number, result in enumerate(pages, start=1):
            stats = result.stats
            corrected = sum(stats.error_histogram[1:])
            _eprint(
                f"page {number}: {stats.symbols} symbols, {corrected} corrected, "
                f"{stats.uncorrectable} uncorrectable"
            )
            uncorrectable += stats.uncorrectable
            chunks.append(packer.feed(result.bits))
            if args.debug_images and result.debug_image is not None:
                _save_debug_image(f"{args.base}_{number:04d}_debug.png", result.debug_image)
    except DecodeError as e:
        page = e.page or len(chunks) + 1
        raise DecodeError(f"{scan_name(page)}: {e}", page=page) from e

    if not chunks:
        raise OptarError(f"cannot open {args.base}_0001.png")

    data = b"".join(chunks)
    if args.output:
        with replacing(args.output) as temp, open(temp, "wb") as f:
            f.write(data)
    else:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()

    if uncorrectable:
        _eprint(f"optar: {uncorrectable} uncorrectable codewords. {PAPER_HINT}")
    return 1 if (uncorrectable or gap) else 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return _encode(args) if args.command == "encode" else _decode(args)
    except OptarError as e:
        message = str(e)
        if isinstance(e, DecodeError):
            message = f"{message.rstrip('.')}. {PAPER_HINT}"
        _eprint(f"optar: {message}")
        return 2
    except OSError as e:
        where = f"{e.filename}: " if e.filename else ""
        _eprint(f"optar: {where}{e.strerror or e}")
        return 2
