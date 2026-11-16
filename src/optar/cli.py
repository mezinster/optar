# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The `optar` command line: encode a file to pages, decode scans back to a file."""

from __future__ import annotations

import argparse
import functools
import os
import re
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import numpy as np
from PIL import Image

from optar import __version__
from optar.container import PagePayload, pages_promised, plan, unwrap, wrap
from optar.decoder import BitPacker, decode_pages
from optar.encoder import check_encodable, encode
from optar.errors import DecodeError, FormatError, IdentifyError, OptarError
from optar.fileio import io_error, replacing
from optar.format import DOT_SIZES, PAPERS, PARITY, Layout, PageFormat, Paper, get_layout
from optar.identify import ScanIdentity, identify_scan
from optar.imageio import read_scan, write_pgm, write_png
from optar.pdf import write_pdf
from optar.tag import make_tag, tagged_label

PAPER_HINT = "Check that --paper matches the printout and that the page is scanned upright."
ACTUAL_SIZE = 'Print at actual size (100%), not "fit to page".'
DOT_NAMES = {
    "standard": "Standard",
    "medium": "Medium",
    "big": "Big",
    "large": "Large",
    "xlarge": "Extra large",
}
# An unidentified scan estimated below this resolution gets the dot sizes' advice.
COARSE_DPI = 400


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
    enc.add_argument(
        "--no-tag",
        action="store_true",
        help="do not add the size, fingerprint and check tag to the page labels",
    )
    enc.add_argument(
        "--dots",
        type=str.lower,
        choices=list(DOT_SIZES),
        help="dot size (default: standard). Any size but standard makes self-identifying "
        "pages, protected at the standard level unless --protect says otherwise",
    )
    enc.add_argument(
        "--protect",
        type=str.lower,
        choices=list(PARITY),
        help="repair data spread over the whole document; makes self-identifying pages, "
        "with standard dots unless --dots says otherwise. Use 'none' for self-identifying "
        "pages without protection. Without --dots and --protect the pages are compatible "
        "and unprotected",
    )
    enc.add_argument(
        "--compatible",
        action="store_true",
        help="pages that optar 0.2 and the C tool read (the default without --dots and --protect)",
    )
    common(enc)

    dec = sub.add_parser("decode", help="decode scanned pages back into a file")
    dec.add_argument("base", metavar="BASE", help="scans are BASE_0001.png, BASE_0002.png, ...")
    dec.add_argument("-o", dest="output", metavar="OUTPUT", help="output file (default: stdout)")
    dec.add_argument("--debug-images", action="store_true", help="write BASE_NNNN_debug.png")
    dec.add_argument(
        "--force",
        action="store_true",
        help="save what was recovered of self-identifying pages even if it did not verify",
    )
    common(dec)
    return parser


def _eprint(message: str) -> None:
    print(message, file=sys.stderr)


def _resolve_format(args: argparse.Namespace) -> tuple[Paper, PageFormat]:
    paper = PAPERS[args.paper]
    fmt = PageFormat.parse(args.format) if args.format else PageFormat.for_paper(paper)
    return paper, fmt


def _check_options(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.command != "encode":
        return
    chosen = [f"--{o}" for o in ("dots", "protect") if getattr(args, o) is not None]
    if chosen and args.compatible:
        parser.error(f"--compatible cannot be used with {' or '.join(chosen)}")
    if chosen and args.format:
        parser.error(f"--format cannot be used with {' or '.join(chosen)}")


def _container(args: argparse.Namespace) -> bool:
    """True if the options ask for version-1 (self-identifying) pages."""
    return args.protect is not None or args.dots not in (None, "standard")


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'s' if n != 1 else ''}"


def _after_encoding(layout: Layout) -> None:
    _eprint(f"{ACTUAL_SIZE} Scan at {layout.scan_dpi} dpi.")


def _encode(args: argparse.Namespace) -> int:
    if _container(args):
        return _encode_protected(args)
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
    name = args.label if args.label is not None else Path(args.output or "").name
    # Each page's tag carries its own check: label(page, total).
    label: str | Callable[[int, int], str] = (
        name if args.no_tag else functools.partial(tagged_label, make_tag(data), name)
    )
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
    _after_encoding(get_layout(paper.name))
    return 0


def _encode_protected(args: argparse.Namespace) -> int:
    """Version-1 pages: the file wrapped with page headers and parity."""
    layout = get_layout(args.paper, args.dots or "standard")
    fmt = layout.fmt
    protection = args.protect or "standard"  # the window's default
    parity = PARITY[protection]
    stored_name = os.path.basename(args.input)
    try:
        size = os.path.getsize(args.input)
    except OSError as e:
        raise io_error("read", args.input, e) from e
    plan(size, stored_name, fmt, parity)  # refuses a file too large before reading it
    try:
        with open(args.input, "rb") as f:
            data = f.read()
    except OSError as e:
        raise io_error("read", args.input, e) from e
    document = plan(len(data), stored_name, fmt, parity)
    stream = wrap(data, stored_name, fmt, parity)
    base = args.output or "optar_out"
    label = args.label if args.label is not None else Path(args.output or "").name
    written: list[str] = []
    if args.to == "pdf":
        path = f"{base}.pdf"
        with replacing(path) as temp:
            count = write_pdf(temp, (page.pixels for page in encode(stream, fmt, label)), layout)
        written.append(f"{path} ({_plural(count, 'page')})")
    else:
        for page in encode(stream, fmt, label):
            path = f"{base}_{page.number:04d}.{args.to}"
            with replacing(path) as temp:
                if args.to == "png":
                    write_png(temp, page.pixels, layout.pixels_per_inch)
                else:
                    write_pgm(temp, page.pixels)
            written.append(path)
    for item in written:
        _eprint(f"wrote {item}")
    _after_encoding(layout)
    lose = pages_promised(document)
    if not parity:
        effect = "nothing is repaired; a lost or damaged page loses part of the file."
    elif lose:
        effect = f"can lose {_plural(lose, 'page')} of {document.total} and still recover the file."
    else:
        effect = "repairs damage within pages; it cannot make up for a lost page."
    _eprint(f"Protection {protection}: {effect}")
    return 0


def _save_debug_image(path: str, image: np.ndarray) -> None:
    Image.fromarray(np.ascontiguousarray(image).astype(np.uint8)).save(path, format="PNG")


def _scan_files(base: str) -> list[str]:
    """Every BASE_NNNN.png, by number."""
    folder = os.path.dirname(base) or "."
    pattern = re.compile(re.escape(os.path.basename(base)) + r"_([0-9]{4,})\.png")
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    found = sorted((int(m.group(1)), n) for n in names if (m := pattern.fullmatch(n)))
    return [os.path.join(folder, n) for _, n in found]


def _identify_version1(path: str) -> ScanIdentity | None:
    """The identity of a scan if it is a version-1 page, else None."""
    try:
        ident = identify_scan(read_scan(path))
    except DecodeError:
        return None
    return ident if ident.header is not None else None


def _document_key(ident: ScanIdentity) -> tuple:
    h, layout = ident.header, ident.layout
    assert h is not None and layout is not None
    return (h.fingerprint, h.size, h.total, h.parity, layout.fmt.to_string())


def _coarse_advice(dpi: float | None) -> str:
    if dpi is None or dpi >= COARSE_DPI:
        return ""
    needs = ", ".join(f"{DOT_NAMES[d]} {get_layout('a4', d).scan_dpi}" for d in DOT_SIZES)
    return f" It was scanned at about {round(dpi, -1):.0f} dpi; the dot sizes need: {needs}."


def _pages(numbers) -> str:
    numbers = list(numbers)
    return f"page{'s' if len(numbers) != 1 else ''} {', '.join(map(str, numbers))}"


def _decode_version1(args: argparse.Namespace, files: list[str], first: ScanIdentity) -> int:
    """Decode version-1 pages: identify every scan, group by header, repair, verify."""
    if args.debug_images:
        _eprint("optar: --debug-images is not available for self-identifying pages")
    key = _document_key(first)
    header, layout = first.header, first.layout
    assert header is not None and layout is not None
    chosen: dict[int, PagePayload] = {}
    ignored: list[str] = []
    for index, path in enumerate(files):
        shown = os.path.basename(path)
        if index == 0:
            ident = first
        else:
            try:
                ident = identify_scan(read_scan(path))
            except IdentifyError as e:
                _eprint(
                    f"optar: {shown}: not identified ({e.reason}); counted as a missing page."
                    + _coarse_advice(e.scan_dpi)
                )
                continue
            except DecodeError as e:
                _eprint(f"optar: {shown}: not identified ({e}); counted as a missing page.")
                continue
        if ident.header is None or _document_key(ident) != key:
            ignored.append(shown)
            continue
        assert ident.payload is not None
        page = ident.header.page
        unreadable = int(np.count_nonzero(ident.payload.erased))
        note = f", {_plural(unreadable, 'byte')} unreadable" if unreadable else ""
        if page in chosen:
            better = unreadable < int(np.count_nonzero(chosen[page].erased))
            _eprint(
                f"{shown}: page {page} of {header.total} again{note}; "
                f"using the {'better' if better else 'earlier'} scan"
            )
            if not better:
                continue
        else:
            _eprint(f"{shown}: page {page} of {header.total}{note}")
        chosen[page] = ident.payload
    if ignored:
        n = len(ignored)
        _eprint(
            f"optar: {_plural(n, 'scan')} from another document "
            f"{'was' if n == 1 else 'were'} ignored: {', '.join(ignored)}"
        )

    result = unwrap(header, layout.fmt, chosen)
    summary = []
    if result.budget:
        summary.append(f"repaired {_plural(result.repaired_bytes, 'byte')}")
        summary.append(f"worst codeword used {result.worst_used} of {result.budget}")
    summary.append(f"missing {_pages(result.missing)}" if result.missing else "no pages missing")
    _eprint(f"optar: {'; '.join(summary)}")

    if result.verified or args.force:
        out = result.data if result.data is not None else result.best_effort
        if args.output:
            with replacing(args.output) as temp, open(temp, "wb") as f:
                f.write(out)
        else:
            sys.stdout.buffer.write(out)
            sys.stdout.buffer.flush()
    if result.verified:
        _eprint(f"optar: file verified ({_plural(header.size, 'byte')})")
        return 0
    why = "could not be repaired" if result.data is None else "does not match its fingerprint"
    if args.force:
        _eprint(
            f"optar: the file {why}: it did not verify and may be damaged. "
            "Saved anyway because of --force."
        )
        return 1
    damaged = sorted(
        (p for p in result.page_damage if p not in result.missing),
        key=lambda p: (-result.page_damage[p], p),
    )[:3]
    rescan = sorted(set(result.missing) | set(damaged))
    force = "--force saves what was recovered, which may be damaged."
    advice = f"Rescan {_pages(rescan)} and decode again; {force}" if rescan else force
    _eprint(f"optar: the file {why} and was not saved. {advice}")
    return 1


def _decode(args: argparse.Namespace) -> int:
    if not args.format:
        files = _scan_files(args.base)
        first = _identify_version1(files[0]) if files else None
        if first is not None:
            return _decode_version1(args, files, first)
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
    parser = _build_parser()
    args = parser.parse_args(argv)
    _check_options(parser, args)
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
