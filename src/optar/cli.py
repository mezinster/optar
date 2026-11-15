# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The `optar` command line: encode a file to pages, decode scans back to a file."""

from __future__ import annotations

import argparse
import contextlib
import os
import sys

import numpy as np
from PIL import Image

from optar import __version__
from optar.decoder import decode_page
from optar.encoder import encode
from optar.errors import DecodeError, FormatError, OptarError
from optar.format import PAPERS, PageFormat, Paper
from optar.imageio import read_scan, write_pgm, write_png
from optar.pdf import write_pdf

PAPER_HINT = "Check that --paper matches the printout."
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
    enc.add_argument("input", metavar="INPUT")
    enc.add_argument("-o", dest="output", metavar="BASE", help="output base name")
    enc.add_argument("--to", choices=["pdf", "png", "pgm"], default="pdf")
    enc.add_argument("--label", help="text printed on each page")
    common(enc)

    dec = sub.add_parser("decode", help="decode scanned pages back into a file")
    dec.add_argument("base", metavar="BASE", help="scans are BASE_0001.png, BASE_0002.png, ...")
    dec.add_argument("-o", dest="output", metavar="OUTPUT", help="output file (default: stdout)")
    dec.add_argument("--debug-images", action="store_true", help="write BASE_NNNN_debug.png")
    common(dec)
    return parser


def _eprint(message: str) -> None:
    print(message, file=sys.stderr)


def _io_error(verb: str, path: str, e: OSError) -> OptarError:
    return OptarError(f"cannot {verb} {path}: {e.strerror or e}")


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
        raise _io_error("read", args.input, e) from e

    base = args.output or "optar_out"
    label = args.label if args.label is not None else (args.output or "")
    written: list[str] = []
    if args.to == "pdf":
        path = f"{base}.pdf"
        pages = (page.pixels for page in encode(data, fmt, label))
        try:
            count = write_pdf(path, pages, paper)
        except BaseException as e:
            with contextlib.suppress(OSError):
                os.unlink(path)
            if isinstance(e, OSError):
                raise _io_error("write", path, e) from e
            raise
        written.append(f"{path} ({count} page{'s' if count != 1 else ''})")
    else:
        writer = write_png if args.to == "png" else write_pgm
        for page in encode(data, fmt, label):
            path = f"{base}_{page.number:04d}.{args.to}"
            try:
                writer(path, page.pixels)
            except OSError as e:
                raise _io_error("write", path, e) from e
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
    chunks: list[np.ndarray] = []
    uncorrectable = 0
    gap = False

    number = 1
    while True:
        path = f"{args.base}_{number:04d}.png"
        if not os.path.exists(path):
            if number > 1 and os.path.exists(f"{args.base}_{number + 1:04d}.png"):
                _eprint(
                    f"optar: {name}_{number:04d}.png is missing "
                    f"but {name}_{number + 1:04d}.png exists"
                )
                gap = True
            break
        result = decode_page(read_scan(path), fmt, debug=args.debug_images)
        stats = result.stats
        corrected = sum(stats.error_histogram[1:])
        _eprint(
            f"page {number}: {stats.symbols} symbols, {corrected} corrected, "
            f"{stats.uncorrectable} uncorrectable"
        )
        uncorrectable += stats.uncorrectable
        chunks.append(result.bits)
        if args.debug_images and result.debug_image is not None:
            _save_debug_image(f"{args.base}_{number:04d}_debug.png", result.debug_image)
        number += 1

    if not chunks:
        raise OptarError(f"cannot open {args.base}_0001.png")

    bits = np.concatenate(chunks)
    data = np.packbits(bits[: len(bits) // 8 * 8]).tobytes()
    if args.output:
        try:
            with open(args.output, "wb") as f:
                f.write(data)
        except OSError as e:
            raise _io_error("write", args.output, e) from e
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
            message = f"{message} {PAPER_HINT}"
        _eprint(f"optar: {message}")
        return 2
    except OSError as e:
        where = f"{e.filename}: " if e.filename else ""
        _eprint(f"optar: {where}{e.strerror or e}")
        return 2
