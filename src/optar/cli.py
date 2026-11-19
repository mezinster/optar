# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The `optar` command line: encode a file to pages, decode scans back to a file."""

from __future__ import annotations

import argparse
import functools
import locale
import os
import re
import sys
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path

import numpy as np
from PIL import Image

from optar import __version__, i18n
from optar.container import (
    BEST_EFFORT_PAGES,
    PagePayload,
    pages_promised,
    plan,
    unwrap,
    wrap,
)
from optar.decoder import BitPacker, decode_pages
from optar.encoder import check_encodable, encode
from optar.errors import DecodeError, FormatError, IdentifyError, OptarError, keyed
from optar.fileio import io_error, replacing
from optar.font import fine_label
from optar.format import DOT_SIZES, PAPERS, PARITY, Layout, PageFormat, Paper, get_layout
from optar.identify import ScanIdentity, identify_any
from optar.imageio import read_scan, write_pgm, write_png
from optar.pdf import write_pdf
from optar.tag import make_tag, tagged_label

# The catalogue keys of the dot sizes' names (written out so a key is always a literal).
DOT_NAME_KEYS = {
    "standard": "cli.dot_name.standard",
    "medium": "cli.dot_name.medium",
    "big": "cli.dot_name.big",
    "large": "cli.dot_name.large",
    "xlarge": "cli.dot_name.xlarge",
}
# An unidentified scan estimated below this resolution gets the dot sizes' advice.
COARSE_DPI = 400


_t = i18n.t
_n = i18n.n


def __getattr__(name: str) -> str:
    """The wording the window shares with the command line, in the chosen language."""
    if name == "ACTUAL_SIZE":
        return _t("cli.ACTUAL_SIZE")
    if name == "PAPER_HINT":
        return _t("cli.PAPER_HINT")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def choose_language(
    environ: Mapping[str, str], encoding: str | None, system: str | None = None
) -> str:
    """The language code for the given environment: OPTAR_LANG, LC_ALL, LC_MESSAGES,
    LANG, then the system's, else English. A language whose text the output
    encoding cannot hold gives English."""
    names = [environ.get(key) for key in ("OPTAR_LANG", "LC_ALL", "LC_MESSAGES", "LANG")]
    code = i18n.pick_language([*names, system]) or "en"
    try:
        return code if i18n.encodable(code, encoding or "utf-8") else "en"
    except LookupError:  # an encoding Python does not know
        return "en"


def _system_language() -> str | None:
    """The user's interface language where the environment does not carry it (Windows)."""
    if sys.platform != "win32":
        return None
    try:
        return locale.getlocale()[0]
    except (ValueError, TypeError):
        return None


class _Formatter(argparse.HelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):
        super().add_usage(
            usage, actions, groups, _t("cli.argparse.usage") if prefix is None else prefix
        )


class _Parser(argparse.ArgumentParser):
    """An ArgumentParser that says its own words (usage, headings, errors) in the
    chosen language. The words argparse builds inside its messages stay English."""

    def __init__(self, *args, **kwargs):
        kwargs.pop("add_help", None)
        kwargs.setdefault("formatter_class", _Formatter)
        super().__init__(*args, add_help=False, **kwargs)
        self._positionals.title = _t("cli.argparse.positionals")
        self._optionals.title = _t("cli.argparse.options")
        self.add_argument(
            "-h",
            "--help",
            action="help",
            default=argparse.SUPPRESS,
            help=_t("cli.argparse.help"),
        )

    def error(self, message: str):
        self.print_usage(sys.stderr)
        self.exit(2, _t("cli.argparse.error", prog=self.prog, message=message) + "\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="optar", description=_t("cli.description"))
    parser.add_argument(
        "--version",
        action="version",
        version=f"optar {__version__}",
        help=_t("cli.argparse.version"),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--paper",
            type=str.lower,
            choices=list(PAPERS),
            default="a4",
            help=_t("cli.help.paper"),
        )
        p.add_argument("--format", metavar="STRING", help=_t("cli.help.format"))

    enc = sub.add_parser("encode", help=_t("cli.help.encode"))
    enc.add_argument("input", metavar="INPUT", help=_t("cli.help.input"))
    enc.add_argument("-o", dest="output", metavar="BASE", help=_t("cli.help.output"))
    enc.add_argument("--to", choices=["pdf", "png", "pgm"], default="pdf", help=_t("cli.help.to"))
    enc.add_argument("--label", help=_t("cli.help.label"))
    enc.add_argument("--no-tag", action="store_true", help=_t("cli.help.no_tag"))
    enc.add_argument("--dots", type=str.lower, choices=list(DOT_SIZES), help=_t("cli.help.dots"))
    enc.add_argument("--protect", type=str.lower, choices=list(PARITY), help=_t("cli.help.protect"))
    enc.add_argument("--compatible", action="store_true", help=_t("cli.help.compatible"))
    common(enc)

    dec = sub.add_parser("decode", help=_t("cli.help.decode"))
    dec.add_argument("base", metavar="BASE", help=_t("cli.help.base"))
    dec.add_argument("-o", dest="output", metavar="OUTPUT", help=_t("cli.help.decode_output"))
    dec.add_argument("--debug-images", action="store_true", help=_t("cli.help.debug_images"))
    dec.add_argument("--force", action="store_true", help=_t("cli.help.force"))
    dec.add_argument("--no-slow-reader", action="store_true", help=_t("cli.help.no_slow_reader"))
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
    options = chosen[0] if len(chosen) == 1 else ""
    if len(chosen) == 2:
        options = _t("cli.or_two", first=chosen[0], second=chosen[1])
    if chosen and args.compatible:
        parser.error(_t("cli.compatible_conflict", options=options))
    if chosen and args.format:
        parser.error(_t("cli.format_conflict", options=options))


def _container(args: argparse.Namespace) -> bool:
    """True if the options ask for version-1 (self-identifying) pages."""
    return args.protect is not None or args.dots not in (None, "standard")


def _after_encoding(layout: Layout) -> None:
    _eprint(_t("cli.after_encoding", actual_size=_t("cli.ACTUAL_SIZE"), dpi=layout.scan_dpi))


def _encode(args: argparse.Namespace) -> int:
    if _container(args):
        return _encode_protected(args)
    paper, fmt = _resolve_format(args)
    if not fmt.fits(paper):
        raise FormatError(_t("cli.format_does_not_fit", format=fmt.to_string(), paper=paper.name))
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
        written.append(_n("cli.wrote_pdf", count, path=path))
    else:
        writer = write_png if args.to == "png" else write_pgm
        for page in encode(data, fmt, label):
            path = f"{base}_{page.number:04d}.{args.to}"
            with replacing(path) as temp:
                writer(temp, page.pixels)
            written.append(_t("cli.wrote", path=path))
    for line in written:
        _eprint(line)
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
            count = write_pdf(
                temp,
                (
                    (page.pixels, fine_label(layout, page.number, page.total, label))
                    for page in encode(stream, fmt, label)
                ),
                layout,
            )
        written.append(_n("cli.wrote_pdf", count, path=path))
    else:
        for page in encode(stream, fmt, label):
            path = f"{base}_{page.number:04d}.{args.to}"
            with replacing(path) as temp:
                if args.to == "png":
                    write_png(temp, page.pixels, layout.pixels_per_inch)
                else:
                    write_pgm(temp, page.pixels)
            written.append(_t("cli.wrote", path=path))
    for line in written:
        _eprint(line)
    _after_encoding(layout)
    lose = pages_promised(document)
    if not parity:
        _eprint(_t("cli.protection.nothing", level=protection))
    elif lose:
        _eprint(_n("cli.protection.lose", lose, level=protection, total=document.total))
    else:
        _eprint(_t("cli.protection.within", level=protection))
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


# Scans looked at to decide between the version-1 path and the 0.2.0 path.
PROBE_FILES = 3


def _probe(path: str, slow: bool = True) -> ScanIdentity | str:
    """The identity of a scan, or in plain words why there is none.

    Unless `slow` is false, a scan the ordinary reader cannot identify is
    given to the slower reader, which is announced on stderr."""
    try:
        image = read_scan(path)
    except OptarError as e:
        return _t("cli.probe.unread", detail=i18n.error_text(e))
    try:
        return identify_any(
            image,
            slow=slow,
            on_slow=lambda: _eprint(_t("cli.slow_reader", name=os.path.basename(path))),
        )
    except IdentifyError as e:
        return _unidentified(i18n.error_text(e), e.scan_dpi, e.slow_tried)
    except DecodeError as e:
        return _t("cli.probe.unidentified", detail=i18n.error_text(e))


def _document_key(ident: ScanIdentity) -> tuple:
    h, layout = ident.header, ident.layout
    assert h is not None and layout is not None
    return (h.fingerprint, h.size, h.total, h.parity, layout.fmt.to_string())


def _unidentified(reason: str, dpi: float | None, slow_tried: bool) -> str:
    if dpi is None or dpi >= COARSE_DPI:
        return _t("cli.probe.unidentified", detail=reason)
    needs = _t("cli.list_separator").join(
        _t("cli.dot_need", name=_t(DOT_NAME_KEYS[d]), dpi=dots.scan_dpi)
        for d, dots in DOT_SIZES.items()
    )
    key = "cli.probe.coarse_tried" if slow_tried else "cli.probe.coarse"
    return _t(key, detail=reason, dpi=f"{round(dpi, -1):.0f}", needs=needs)


def _listed(numbers, most: int = 20) -> str:
    """The first `most` numbers, then how many more there are."""
    numbers = list(numbers)
    more = len(numbers) - most
    shown = [str(x) for x in numbers[:most]]
    if more > 0:
        shown.append(_n("cli.list_more", more))
    return _t("cli.list_separator").join(shown)


def _gather(
    files: list[str],
    probes: dict[str, ScanIdentity | str],
    first: ScanIdentity,
    slow: bool = True,
) -> dict[int, PagePayload]:
    """The payload of each page of first's document among the scans, the
    better scan of a page given twice. Reports each scan on stderr."""
    key = _document_key(first)
    total = first.header.total  # type: ignore[union-attr]
    chosen: dict[int, PagePayload] = {}
    by_slow_reader: dict[int, bool] = {}
    ignored: list[str] = []
    for path in files:
        shown = os.path.basename(path)
        ident = probes[path] if path in probes else _probe(path, slow)
        if isinstance(ident, str):
            _eprint(_t("cli.scan.missing", name=shown, reason=ident))
            continue
        if ident.header is None or _document_key(ident) != key:
            ignored.append(shown)
            continue
        assert ident.payload is not None
        page = ident.header.page
        unreadable = int(np.count_nonzero(ident.payload.erased))
        note = _n("cli.scan.note_unreadable", unreadable) if unreadable else ""
        if ident.reader == "slow":
            note += _t("cli.scan.note_slow")
        slow_read = ident.reader == "slow"
        if page in chosen:
            # The slower reader marks no byte unreadable, so its count says
            # nothing: an ordinary reading of the page is preferred to it.
            if slow_read != by_slow_reader[page]:
                better = by_slow_reader[page]
            else:
                better = unreadable < int(np.count_nonzero(chosen[page].erased))
            again = "cli.scan.page_again_better" if better else "cli.scan.page_again_earlier"
            _eprint(_t(again, name=shown, page=page, total=total, note=note))
            if not better:
                continue
        else:
            _eprint(_t("cli.scan.page", name=shown, page=page, total=total, note=note))
        chosen[page] = ident.payload
        by_slow_reader[page] = slow_read
    if ignored:
        names = _t("cli.list_separator").join(ignored)
        _eprint(_n("cli.scan.ignored", len(ignored), names=names))
    return chosen


def _decode_version1(
    args: argparse.Namespace,
    files: list[str],
    probes: dict[str, ScanIdentity | str],
    first: ScanIdentity,
) -> int:
    """Decode version-1 pages: identify every scan, group by header, repair, verify."""
    if args.debug_images:
        _eprint(_t("cli.debug_images_unavailable"))
    header, layout = first.header, first.layout
    assert header is not None and layout is not None
    result = unwrap(header, layout.fmt, _gather(files, probes, first, not args.no_slow_reader))

    summary = []
    if result.data is None and result.best_effort is None:
        summary.append(_t("cli.summary.too_many_missing"))
    elif result.budget:
        summary.append(_n("cli.summary.repaired", result.repaired_bytes))
        if result.failed:
            summary.append(_n("cli.summary.blocks_failed", result.failed))
        else:
            summary.append(_t("cli.summary.worst", used=result.worst_used, budget=result.budget))
    summary.append(
        _n("cli.summary.missing", len(result.missing), list=_listed(result.missing))
        if result.missing
        else _t("cli.summary.none_missing")
    )
    _eprint(_t("cli.summary.line", summary=_t("cli.summary.separator").join(summary)))

    out = result.data if result.data is not None else result.best_effort
    if out is None:
        # Too few pages to build even a best-effort file (container.unwrap).
        read = header.total - len(result.missing)
        _eprint(
            _t(
                "cli.sentences",
                first=_n("cli.too_few.read", header.total, read=read),
                second=_n(
                    "cli.too_few.rescan",
                    len(result.missing),
                    list=_listed(result.missing),
                    fraction=BEST_EFFORT_PAGES,
                ),
            )
        )
        return 1
    if result.verified or args.force:
        if args.output:
            with replacing(args.output) as temp, open(temp, "wb") as f:
                f.write(out)
        else:
            sys.stdout.buffer.write(out)
            sys.stdout.buffer.flush()
    if result.verified:
        _eprint(_n("cli.verified", header.size))
        return 0
    if args.force:
        _eprint(
            _t("cli.force_saved.unrepaired")
            if result.data is None
            else _t("cli.force_saved.mismatch")
        )
        return 1
    damaged = sorted(
        (p for p in result.page_damage if p not in result.missing),
        key=lambda p: (-result.page_damage[p], p),
    )[:3]
    rescan = sorted(set(result.missing) | set(damaged))
    force = _t("cli.force_advice")
    advice = (
        _n("cli.rescan_advice", len(rescan), list=_listed(rescan), force=force) if rescan else force
    )
    _eprint(
        _t("cli.not_saved.unrepaired", advice=advice)
        if result.data is None
        else _t("cli.not_saved.mismatch", advice=advice)
    )
    return 1


def _decode(args: argparse.Namespace) -> int:
    if not args.format:
        # The first of the first PROBE_FILES scans that identifies decides:
        # a version-1 page takes the whole set down the version-1 path.
        files = _scan_files(args.base)
        probes: dict[str, ScanIdentity | str] = {}
        for path in files[:PROBE_FILES]:
            ident = probes[path] = _probe(path, not args.no_slow_reader)
            if isinstance(ident, str):
                continue
            if ident.header is not None:
                return _decode_version1(args, files, probes, ident)
            break
    if args.force:
        _eprint(_t("cli.force_no_effect"))
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
                        _t("cli.gap", missing=scan_name(number), existing=scan_name(number + 1))
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
                _t(
                    "cli.page_stats",
                    number=number,
                    symbols=_n("cli.stat_symbols", stats.symbols),
                    corrected=_n("cli.stat_corrected", corrected),
                    uncorrectable=_n("cli.stat_uncorrectable", stats.uncorrectable),
                )
            )
            uncorrectable += stats.uncorrectable
            chunks.append(packer.feed(result.bits))
            if args.debug_images and result.debug_image is not None:
                _save_debug_image(f"{args.base}_{number:04d}_debug.png", result.debug_image)
    except DecodeError as e:
        page = e.page or len(chunks) + 1
        named = DecodeError(f"{scan_name(page)}: {e}", page=page)
        values = {"name": scan_name(page), "message": i18n.error_text(e)}
        raise keyed(named, "cli.in_scan", values) from e

    if not chunks:
        raise OptarError(_t("cli.cannot_open", path=f"{args.base}_0001.png"))

    data = b"".join(chunks)
    if args.output:
        with replacing(args.output) as temp, open(temp, "wb") as f:
            f.write(data)
    else:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()

    if uncorrectable:
        _eprint(_n("cli.uncorrectable_codewords", uncorrectable, hint=_t("cli.PAPER_HINT")))
    return 1 if (uncorrectable or gap) else 0


def main(argv: list[str] | None = None) -> int:
    previous = i18n.language()
    i18n.set_language(choose_language(os.environ, sys.stderr.encoding, _system_language()))
    try:
        return _run(argv)
    finally:
        i18n.set_language(previous)


def _run(argv: list[str] | None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _check_options(parser, args)
    try:
        return _encode(args) if args.command == "encode" else _decode(args)
    except OptarError as e:
        message = i18n.error_text(e)
        if isinstance(e, DecodeError):
            _eprint(_t("cli.line_hint", message=message.rstrip("."), hint=_t("cli.PAPER_HINT")))
        else:
            _eprint(_t("cli.line", message=message))
        return 2
    except OSError as e:
        reason = e.strerror or e
        if e.filename:
            _eprint(_t("cli.os_error_file", file=e.filename, reason=reason))
        else:
            _eprint(_t("cli.os_error", reason=reason))
        return 2
