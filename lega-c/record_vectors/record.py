# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Record the C tools' results as conformance vectors in tests/vectors/c/.

Run from the repository root (needs a C compiler and libpng headers):

    .venv/bin/python lega-c/record_vectors/record.py

This is the last run of the C tools: the vectors it wrote are frozen, and
tests/vectors/test_vectors_c.py checks the Python code against them without a
compiler. Each function below mirrors one comparison of tests/oracle/ and
writes one vector file. Running it twice writes the same files.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from optar import PageFormat, encode  # noqa: E402
from optar.container import wrap  # noqa: E402
from optar.fec import serialize_table  # noqa: E402
from optar.format import LAYOUTS, get_layout  # noqa: E402
from optar.imageio import pgm_bytes  # noqa: E402
from optar.layout import channel_xy  # noqa: E402
from tests import cbuild  # noqa: E402
from tests.helpers import DEGRADED, fake_scan, save_scan, seeded_bytes  # noqa: E402
from tests.vectors.load import array_digest, digest  # noqa: E402

OUT = REPO_ROOT / "tests" / "vectors" / "c"
SCANS = OUT / "scans"
A4 = PageFormat(65, 93)
LETTER = PageFormat(67, 87)

# The format of the stored scans: small, so that the scans fit in the size
# budget. PageFormat(6, 8) was tried first: C decodes the "flips" case
# wrongly there (200 flips on so small a page leave one uncorrectable
# symbol, in C and in Python alike). 6 x 9 is the next larger step on which
# every stored case decodes as the oracle tests require.
SMALL = (6, 9)

# Stored scans left out to keep tests/vectors under 2,000,000 bytes, in the
# order the plan gives: the scale-6 scan first, then DEGRADED cases whose
# degradation another stored case already contains ("noisy": noise is in
# "combined" and in the noise-60 cases; "rotated": rotation is in "combined"
# and in the degraded scan of decoder_internals.json). Without "rotated" the
# directory would be within a few kilobytes of the limit.
DROPPED = ("scale6", "noisy", "rotated")


class Builds:
    """C builds, one per optar.h override set, made on first use."""

    def __init__(self, root: Path):
        self.root = root
        self.cache: dict[tuple, cbuild.CBuild] = {}
        self.patched: dict[tuple, Path] = {}

    def get(self, overrides: dict[str, int] | None = None) -> cbuild.CBuild:
        key = tuple(sorted((overrides or {}).items()))
        if key not in self.cache:
            name = "_".join(f"{k}{v}" for k, v in key) or "default"
            build = cbuild.build_c_tools(self.root / name, dict(key))
            if build.unoptar is None:
                raise SystemExit("unoptar was not built: libpng headers are needed")
            self.cache[key] = build
        return self.cache[key]

    def for_format(self, fmt: PageFormat) -> cbuild.CBuild:
        return self.get(overrides(fmt))

    def patched_unoptar(self, fmt: PageFormat, name: str, replacements) -> Path:
        key = (fmt.to_string(), name)
        if key not in self.patched:
            self.patched[key] = cbuild.build_patched_unoptar(
                self.for_format(fmt), name, replacements
            )
        return self.patched[key]


def overrides(fmt: PageFormat) -> dict[str, int]:
    """The optar.h overrides that build C for fmt (only grid and FEC order vary)."""
    assert (fmt.cpitch, fmt.chalf, fmt.border, fmt.text_height) == (24, 3, 2, 24), fmt
    out = {}
    if (fmt.xcrosses, fmt.ycrosses) != (65, 93):
        out.update(XCROSSES=fmt.xcrosses, YCROSSES=fmt.ycrosses)
    if fmt.fec_order != 1:
        out["FEC_ORDER"] = fmt.fec_order
    return out


def c_commit() -> str:
    """The C commit recorded by tests/golden/make_fixtures.py (kept in the vectors)."""
    return json.loads((OUT / "golay.json").read_text())["c_commit"]


def write(name: str, pins: str, cases) -> None:
    doc = {"c_commit": c_commit(), "cases": cases, "pins": pins, "source": "c"}
    (OUT / f"{name}.json").write_text(json.dumps(doc, sort_keys=True, indent=1) + "\n")


def run(cmd, cwd: Path, stdin: bytes | None = None) -> bytes:
    r = subprocess.run(
        [str(c) for c in cmd], cwd=cwd, input=stdin, capture_output=True, check=False
    )
    if r.returncode != 0:
        raise RuntimeError(f"{cmd} exited with {r.returncode}: {r.stderr[-2000:].decode()}")
    return r.stdout


def c_encode(build: cbuild.CBuild, data: bytes, label: str | None, work: Path) -> list[Path]:
    """Run C optar on data; return its pages in order."""
    work.mkdir(parents=True)
    (work / "in.bin").write_bytes(data)
    run([build.optar, "in.bin", *([label] if label is not None else [])], work)
    prefix = label if label is not None else "optar_out"
    files = sorted(work.glob("*.pgm"))
    assert [f.name for f in files] == [f"{prefix}_{i:04d}.pgm" for i in range(1, len(files) + 1)]
    return files


def c_decode(build: cbuild.CBuild, fmt: PageFormat, scans: list[Path], work: Path) -> bytes:
    """Run C unoptar on exactly these PNG files (copied, not rewritten)."""
    work.mkdir(parents=True)
    for i, f in enumerate(scans, 1):
        shutil.copyfile(f, work / f"scan_{i:04d}.png")
    return run([build.unoptar, fmt.to_string(), "scan"], work)


def read_pgm(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im, np.uint8)


# --- golay.json -------------------------------------------------------------


def record_golay(builds: Builds, tmp: Path) -> None:
    build = builds.get()
    probe = build.dir / "golay_dump.c"
    probe.write_text(
        '#include <stdio.h>\n#include "optar.h"\n'
        "int main(void){int i;for(i=0;i<4096;i++)printf(\"%lu\\n\",golay_codes[i]);return 0;}\n"
    )
    run([cbuild.compiler(), "-o", "golay_dump", "golay_dump.c", "golay_codes.o", "-lm"], build.dir)
    table = [int(v) for v in run(["./golay_dump"], build.dir).split()]
    write(
        "golay",
        "The SHA-256 of the serialized Golay table equals the one built by the C tool.",
        {"golay_sha256": digest(serialize_table(table))},
    )


# --- bit_placement.json -----------------------------------------------------


def seq_choices(fmt: PageFormat, n: int) -> list[int]:
    """The sequence numbers tests/golden/make_fixtures.py picked (its first n)."""
    raw = seeded_bytes(7, 4 * n)
    return [int.from_bytes(raw[4 * i : 4 * i + 4], "big") % fmt.total_bits for i in range(n)]


def placement_formats() -> list[PageFormat]:
    fmts = [layout.fmt for layout in LAYOUTS.values()]
    return fmts + [PageFormat(4, 4), PageFormat(7, 5), PageFormat(65, 93, fec_order=3)]


def record_bit_placement(builds: Builds, tmp: Path) -> None:
    cases = {}
    for fmt in placement_formats():
        exe = cbuild.build_seq2xy_dump(builds.for_format(fmt))
        seqs = "".join(f"{s}\n" for s in range(fmt.total_bits)).encode()
        rows = np.array(run([exe], tmp, seqs).split(), np.int64).reshape(-1, 3)
        assert (rows[:, 0] == np.arange(fmt.total_bits)).all()
        x, y = rows[:, 1], rows[:, 2]
        py_x, py_y = channel_xy(fmt)
        assert py_x.size == fmt.total_bits
        cases[fmt.to_string()] = {
            "all_sha256": array_digest(np.stack([x, y]).astype("<i4"), np.dtype("<i4")),
            "samples": [[s, int(x[s]), int(y[s])] for s in seq_choices(fmt, 100)],
        }
    write(
        "bit_placement",
        "Every payload bit sits where C seq2xy puts it, for every layout and three other formats.",
        cases,
    )


# --- encoder_pages.json -----------------------------------------------------


def record_encoder_pages(builds: Builds, tmp: Path) -> None:
    net = A4.net_bits // 8
    # The cases tests/golden/make_fixtures.py recorded (seed = position).
    old = [
        ("empty", A4, 0, ""),
        ("one_byte", A4, 1, ""),
        ("exact_page", A4, net, ""),
        ("page_plus_one", A4, net + 1, ""),
        ("two_pages", A4, 300_000, ""),
        ("labelled", A4, 5_000, "my label"),
        ("one_byte", LETTER, 1, ""),
        ("two_pages", LETTER, 300_000, ""),
    ]
    cases = [(name, fmt, i, size, label) for i, (name, fmt, size, label) in enumerate(old)]
    # The inputs of tests/oracle/test_encoder_oracle.py.
    variants = [("a4", A4), ("letter", LETTER)]
    variants += [(f"fec{n}", PageFormat(65, 93, fec_order=n)) for n in (2, 3, 4, 5)]
    for vname, fmt in variants:
        sizes = [0, 1, 777, 2 * (fmt.net_bits // 8) + 5]
        cases += [(f"{vname}-{seed}", fmt, seed, size, "") for seed, size in enumerate(sizes)]
    out = []
    for n, (name, fmt, seed, size, label) in enumerate(cases):
        files = c_encode(
            builds.for_format(fmt), seeded_bytes(seed, size), label or None, tmp / f"enc{n}"
        )
        out.append({
            "format": fmt.to_string(), "label": label, "name": name, "seed": seed,
            "sha256": [digest(f.read_bytes()) for f in files], "size": size,
        })  # fmt: skip
    write(
        "encoder_pages",
        "The SHA-256 of each page's PGM bytes equals the C encoder's for the same input.",
        out,
    )


# --- container_pages.json ---------------------------------------------------


def record_container_pages(builds: Builds, tmp: Path) -> None:
    out = []
    for paper, dots in (("a4", "large"), ("letter", "medium")):
        fmt = get_layout(paper, dots).fmt
        build = builds.for_format(fmt)
        case = {"file_name": "name.bin", "format": fmt.to_string(), "label": "doc",
                "name": f"{paper}-{dots}", "parity": 32, "recipe": {"scale": 1},
                "seed": 31, "size": 100_000}  # fmt: skip
        stream = wrap(
            seeded_bytes(case["seed"], case["size"]), case["file_name"], fmt, case["parity"]
        )
        work = tmp / f"cont-{case['name']}"
        files = c_encode(build, stream, case["label"], work / "enc")
        pages = list(encode(stream, fmt, case["label"]))
        assert len(pages) > 1
        scans = []
        for p in pages:
            scans.append(work / f"py_{p.number:04d}.png")
            save_scan(scans[-1], fake_scan(p.pixels, **case["recipe"]))
        c_out = c_decode(build, fmt, scans, work / "dec")
        assert len(c_out) == len(pages) * fmt.net_bits // 8
        assert c_out[: len(stream)] == stream
        case.update(
            c_output_sha256=digest(c_out),
            page_sha256=[digest(f.read_bytes()) for f in files],
            stream_sha256=digest(stream),
        )
        out.append(case)
    write(
        "container_pages",
        "Container streams on larger-dot layouts encode to C optar's pages, and C unoptar's "
        "reading of the Python pages is known.",
        out,
    )


# --- label.json -------------------------------------------------------------

LABEL_TEXTS = [
    "",
    "my label",
    ("The quick brown fox jumps over the lazy dog 0123456789. " * 4)[:200],
    "naïve ☃",
]


def record_label(builds: Builds, tmp: Path) -> None:
    out = []
    build = builds.for_format(A4)
    top = A4.border + A4.data_height
    for n, text in enumerate(LABEL_TEXTS):
        assert "/" not in text and len(text.encode()) < 240  # C uses it as a file name
        data = b"x"
        (page, *_) = c_encode(build, data, text or None, tmp / f"label{n}")
        band = read_pgm(page)[top : top + A4.text_height, :]
        out.append({"band_sha256": array_digest(band, np.uint8), "format": A4.to_string(),
                    "input_hex": data.hex(), "text": text})  # fmt: skip
    write(
        "label",
        "The label band of page 1 is the one C optar draws for the same label text.",
        out,
    )


# --- decoder.json -----------------------------------------------------------


def _decoder_variants():
    big = 300_000
    out = [("a4", A4, big), ("letter", LETTER, big)]
    for n in (2, 3, 4, 5):
        fmt = PageFormat(65, 93, fec_order=n)
        out.append((f"fec{n}", fmt, fmt.net_bits // 8 + 2000))
    return out


def _decode_case(builds, fmt, case, scans, work, *, pages_expected=None):
    data = seeded_bytes(case["seed"], case["size"])
    c_out = c_decode(builds.for_format(fmt), fmt, scans, work)
    if pages_expected is not None:
        assert len(c_out) == pages_expected * fmt.net_bits // 8, case["name"]
    starts = case["starts_with_input"]
    if starts:
        assert c_out[: len(data)] == data, case["name"]
    case.update(c_output_sha256=digest(c_out), c_output_size=len(c_out))
    return case


def _regenerated(pages, recipe, work: Path) -> list[Path]:
    work.mkdir(parents=True)
    scans = []
    for p in pages:
        scans.append(work / f"scan_{p.number:04d}.png")
        save_scan(scans[-1], fake_scan(p.pixels, **recipe))
    return scans


def _stored(name: str, array) -> list[str]:
    rel = f"scans/{name}.png"
    save_scan(OUT / rel, array)
    return [rel]


def record_decoder(builds: Builds, tmp: Path) -> None:
    out = []
    # Full size: tests/oracle/test_decoder_oracle.py, C <-> Python pages.
    for vname, fmt, size in _decoder_variants():
        base = {"format": fmt.to_string(), "group": "full_size", "recipe": {"scale": 1},
                "size": size, "starts_with_input": True}  # fmt: skip
        # C unoptar reads Python pages.
        case = dict(base, name=f"{vname}-c-decodes-python", seed=21)
        pages = list(encode(seeded_bytes(21, size), fmt))
        assert len(pages) == 2
        scans = _regenerated(pages, case["recipe"], tmp / f"{case['name']}-scans")
        out.append(_decode_case(builds, fmt, case, scans, tmp / case["name"], pages_expected=2))
        # C unoptar reads C optar's pages (which equal the Python pages).
        case = dict(base, name=f"{vname}-python-decodes-c", seed=22)
        data = seeded_bytes(22, size)
        files = c_encode(builds.for_format(fmt), data, None, tmp / f"{case['name']}-enc")
        assert [pgm_bytes(p.pixels) for p in encode(data, fmt)] == [
            f.read_bytes() for f in files
        ]
        scans = []
        for i, f in enumerate(files, 1):
            scans.append(tmp / f"{case['name']}-enc" / f"scan_{i:04d}.png")
            save_scan(scans[-1], fake_scan(read_pgm(f), **case["recipe"]))
        case["page_sha256"] = [digest(f.read_bytes()) for f in files]
        out.append(_decode_case(builds, fmt, case, scans, tmp / case["name"], pages_expected=2))
    # Full size at scale 3: the degraded-tests page of A4 (one page).
    case = {"format": A4.to_string(), "group": "full_size", "name": "a4-scale3",
            "recipe": {"scale": 3}, "seed": 11, "size": 150_000,
            "starts_with_input": True}  # fmt: skip
    pages = list(encode(seeded_bytes(11, 150_000), A4))
    scans = _regenerated(pages, case["recipe"], tmp / "a4-scale3-scans")
    out.append(_decode_case(builds, A4, case, scans, tmp / "a4-scale3", pages_expected=1))

    # Small format: the degraded cases, stored unless their scan is regenerated.
    fmt = PageFormat(*SMALL)
    net = fmt.net_bits // 8
    small_page = next(encode(seeded_bytes(11, net), fmt))
    for name, kw in DEGRADED.items():
        if name in DROPPED:
            continue
        case = {"format": fmt.to_string(), "group": "small", "name": name, "seed": 11,
                "size": net, "starts_with_input": True}  # fmt: skip
        if set(kw) <= {"scale"} and kw.get("scale") in (1, 3):
            case["recipe"] = dict(kw)
            scans = _regenerated([small_page], kw, tmp / name)
        else:
            scan = fake_scan(small_page.pixels, seed=1, fmt=fmt, **kw)
            case["scan_files"] = _stored(name, scan)
            scans = [OUT / f for f in case["scan_files"]]
        out.append(_decode_case(builds, fmt, case, scans, tmp / f"{name}-dec", pages_expected=1))
    # Heavy noise: uncorrectable symbols, written exactly as C writes them.
    for n in (1, 2, 5):
        nfmt = PageFormat(*SMALL, fec_order=n)
        nnet = nfmt.net_bits // 8
        name = f"noise60-fec{n}"
        npage = next(encode(seeded_bytes(23, nnet), nfmt)).pixels
        scan = fake_scan(npage, scale=3, noise=60, seed=2)
        case = {"format": nfmt.to_string(), "group": "small", "name": name, "seed": 23,
                "size": nnet, "starts_with_input": False}  # fmt: skip
        case["scan_files"] = _stored(name, scan)
        scans = [OUT / f for f in case["scan_files"]]
        out.append(_decode_case(builds, nfmt, case, scans, tmp / f"{name}-dec", pages_expected=1))
    # Two things no case above has, in one small stored PNG (flipped dots on a clean
    # scan compress well): Golay symbols beyond repair, which the noise-60 scan leaves
    # none of in fec_order 1, and a 1200 dpi scan (scale 6), where min/max runs 3 passes
    # and blur 2 cycles while every scale-3 scan runs 1 of each.
    name = "flips1000-scale6"
    scan = fake_scan(small_page.pixels, scale=6, flips=1000, seed=1, fmt=fmt)
    case = {"format": fmt.to_string(), "group": "small", "name": name, "seed": 11,
            "size": net, "starts_with_input": False}  # fmt: skip
    case["scan_files"] = _stored(name, scan)
    scans = [OUT / f for f in case["scan_files"]]
    out.append(_decode_case(builds, fmt, case, scans, tmp / f"{name}-dec", pages_expected=1))
    write(
        "decoder",
        "The decoder writes exactly the bytes C unoptar writes for the same scans.",
        out,
    )


# --- decoder_internals.json -------------------------------------------------

_CROSS_HOOK = "\tsync_crosses();\n"
_CROSS_DUMP = r"""	sync_crosses();
	{
		unsigned dcx, dcy;
		FILE *dump=fopen("crosses.txt", "w");
		for (dcy=0;dcy<YCROSSES;dcy++)
			for (dcx=0;dcx<XCROSSES;dcx++)
				fprintf(dump, "%a %a %a\n", crosses[dcx][dcy][0],
					crosses[dcx][dcy][1], (double)cutlevels[dcx][dcy]);
		fclose(dump);
		exit(0);
	}
"""
_BIT = "read_hamming_bit(pixval<local_cutlevel, hamming_sym);"
_BIT_DUMP = (
    """{
				static FILE *bitdump;
				if (!bitdump) bitdump=fopen("bits.bin", "wb");
				fputc(pixval<local_cutlevel, bitdump);
			}
			"""
    + _BIT
)
_READ = "\tread_syms();\n"
_READ_EXIT = "\tread_syms();\n\texit(0);\n"


def record_decoder_internals(builds: Builds, tmp: Path) -> None:
    fmt = PageFormat(*SMALL)
    net = fmt.net_bits // 8
    crosses_exe = builds.patched_unoptar(fmt, "unoptar_dump", [(_CROSS_HOOK, _CROSS_DUMP)])
    bits_exe = builds.patched_unoptar(
        fmt, "unoptar_bits", [(_BIT, _BIT_DUMP), (_READ, _READ_EXIT)]
    )
    page = next(encode(seeded_bytes(5, net), fmt))
    degraded = dict(scale=3, margin=120, rotate=0.4, blur=1.0, noise=8.0, seed=3)
    cases = [
        {"name": "clean", "recipe": {"scale": 3}},
        {"name": "degraded",
         "scan_files": _stored("internals-degraded", fake_scan(page.pixels, **degraded))},
    ]  # fmt: skip
    for case in cases:
        work = tmp / f"internals-{case['name']}"
        if "recipe" in case:
            (scan,) = _regenerated([page], case["recipe"], work / "scans")
        else:
            scan = OUT / case["scan_files"][0]
        c_decode_dir = work / "crosses"
        c_decode_dir.mkdir(parents=True)
        shutil.copyfile(scan, c_decode_dir / "scan_0001.png")
        run([crosses_exe, fmt.to_string(), "scan"], c_decode_dir)
        rows = [line.split() for line in (c_decode_dir / "crosses.txt").read_text().splitlines()]
        assert len(rows) == fmt.xcrosses * fmt.ycrosses and all(len(r) == 3 for r in rows)
        bits_dir = work / "bits"
        bits_dir.mkdir()
        shutil.copyfile(scan, bits_dir / "scan_0001.png")
        run([bits_exe, fmt.to_string(), "scan"], bits_dir)
        raw = np.fromfile(bits_dir / "bits.bin", np.uint8)
        assert raw.size == fmt.used_bits
        # C loop: hamming_sym outer, bit inner, seq = hamming_sym + bit * fec_syms.
        c_bits = np.ascontiguousarray(raw.reshape(fmt.fec_syms, fmt.fec_largebits).T.ravel())
        case.update(bits_sha256=array_digest(c_bits, np.uint8), crosses=rows)
    doc = {
        "c_commit": c_commit(), "cases": cases, "format": fmt.to_string(),
        "pins": "Cross positions, cut levels and sampled bits equal those of an instrumented "
                "C unoptar on the same scans.",
        "seed": 5, "size": net, "source": "c",
    }  # fmt: skip
    (OUT / "decoder_internals.json").write_text(json.dumps(doc, sort_keys=True, indent=1) + "\n")


def main() -> None:
    if cbuild.compiler() is None:
        raise SystemExit("no C compiler found")
    if SCANS.exists():
        shutil.rmtree(SCANS)
    SCANS.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        builds = Builds(tmp / "builds")
        for record in (record_golay, record_bit_placement, record_encoder_pages,
                       record_container_pages, record_label, record_decoder,
                       record_decoder_internals):  # fmt: skip
            work = tmp / record.__name__
            work.mkdir()
            print(record.__name__, flush=True)
            record(builds, work)


if __name__ == "__main__":
    main()
