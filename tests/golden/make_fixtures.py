# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Regenerate fixtures.json from the C tools.

Run from the repo root: .venv/bin/python -m tests.golden.make_fixtures
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from optar.fec import serialize_table
from optar.format import PageFormat
from tests import cbuild
from tests.helpers import seeded_bytes

HERE = Path(__file__).parent
LETTER = {"XCROSSES": 67, "YCROSSES": 87}
LABEL = "my label"


_C_FILES = ("optar.c", "common.c", "golay.c", "parity.c", "optar.h", "font.h")
_C_HISTORY_PATHS = [*_C_FILES, *(f"lega-c/{name}" for name in _C_FILES)]


def c_golay_sha256(build: cbuild.CBuild) -> str:
    """Hash the C golay_codes table, serialized like optar.fec.serialize_table."""
    probe = build.dir / "golay_dump.c"
    probe.write_text(
        '#include <stdio.h>\n#include "optar.h"\n'
        "int main(void){int i;for(i=0;i<4096;i++)printf(\"%lu\\n\",golay_codes[i]);return 0;}\n"
    )
    cc = cbuild.compiler()
    subprocess.run(
        [cc, "-o", "golay_dump", "golay_dump.c", "golay_codes.o", "-lm"],
        cwd=build.dir, check=True,
    )  # fmt: skip
    out = subprocess.run(
        ["./golay_dump"], cwd=build.dir, check=True, capture_output=True, text=True
    ).stdout
    table = [int(v) for v in out.split()]
    return hashlib.sha256(serialize_table(table)).hexdigest()


def seq2xy_values(build: cbuild.CBuild, seqs: list[int]) -> list[list[int]]:
    exe = cbuild.build_seq2xy_dump(build)
    out = subprocess.run(
        [exe], input="".join(f"{s}\n" for s in seqs), check=True,
        capture_output=True, text=True,
    ).stdout  # fmt: skip
    return [[int(v) for v in line.split()] for line in out.splitlines()]


def c_pages(build: cbuild.CBuild, data: bytes, label: str) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / "in.bin").write_bytes(data)
        cmd = [str(build.optar), "in.bin"] + ([label] if label else [])
        subprocess.run(cmd, cwd=work, check=True, capture_output=True)
        prefix = label if label else "optar_out"
        files = sorted(work.glob(f"{prefix}_*.pgm"))
        return [hashlib.sha256(f.read_bytes()).hexdigest() for f in files]


def seq_choices(fmt: PageFormat, n: int = 2000) -> list[int]:
    raw = seeded_bytes(7, 4 * n)
    return [int.from_bytes(raw[4 * i : 4 * i + 4], "big") % fmt.total_bits for i in range(n)]


def main() -> None:
    a4 = PageFormat(65, 93)
    letter = PageFormat(67, 87)
    with tempfile.TemporaryDirectory() as t:
        builds = {
            a4.to_string(): cbuild.build_c_tools(Path(t) / "a4"),
            letter.to_string(): cbuild.build_c_tools(Path(t) / "letter", LETTER),
        }
        builds_by_fmt = {a4.to_string(): (a4, builds[a4.to_string()]),
                         letter.to_string(): (letter, builds[letter.to_string()])}  # fmt: skip

        net = a4.net_bits // 8
        cases = [
            ("empty", a4, 0, ""),
            ("one_byte", a4, 1, ""),
            ("exact_page", a4, net, ""),
            ("page_plus_one", a4, net + 1, ""),
            ("two_pages", a4, 300_000, ""),
            ("labelled", a4, 5_000, LABEL),
        ]
        cases += [("one_byte", letter, 1, ""), ("two_pages", letter, 300_000, "")]
        pages = []
        for i, (name, fmt, size, label) in enumerate(cases):
            build = builds_by_fmt[fmt.to_string()][1]
            sha = c_pages(build, seeded_bytes(i, size), label)
            pages.append({"name": name, "format": fmt.to_string(), "seed": i,
                          "size": size, "label": label, "sha256": sha})  # fmt: skip

        seq2xy = {
            key: seq2xy_values(b, seq_choices(f)) for key, (f, b) in builds_by_fmt.items()
        }
        fixtures = {
            "c_commit": subprocess.run(
                # The last commit that changed the C sources' contents. They moved
                # from the repo root to lega-c unchanged: with both locations named
                # and renames detected, the move is not counted as a change.
                ["git", "log", "-1", "--format=%H", "-M", "--diff-filter=AM", "--",
                 *_C_HISTORY_PATHS],
                cwd=cbuild.REPO_ROOT, check=True, capture_output=True, text=True,
            ).stdout.strip(),
            "golay_sha256": c_golay_sha256(builds[a4.to_string()]),
            "seq2xy": seq2xy,
            "pages": pages,
        }  # fmt: skip
    text = json.dumps(fixtures, sort_keys=True, indent=1) + "\n"
    (HERE / "fixtures.json").write_text(text)


if __name__ == "__main__":
    main()
