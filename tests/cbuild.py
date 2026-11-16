# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Build the original C tools in a temporary copy of the sources.

Environment: CC (compiler, default cc), OPTAR_TEST_CFLAGS and OPTAR_TEST_LDFLAGS
(shlex-split, appended to compile and link commands).
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# The original C tools: a frozen test oracle kept apart from the Python code.
C_DIR = REPO_ROOT / "lega-c"
C_SOURCES = [
    "common.c", "golay.c", "optar.c", "parity.c", "unoptar.c",
    "optar.h", "font.h", "parity.h",
]  # fmt: skip
# -ffp-contract=off: no FMA contraction, so C float results match numpy on any CPU.
CFLAGS = ["-O3", "-Wall", "-DNODEBUG", "-ffp-contract=off"]
UNOPTAR_OBJECTS = ["common.o", "golay_codes.o", "parity.o"]
UNOPTAR_LIBS = ["-lm", "-lpng", "-lz"]


class CBuildError(RuntimeError):
    """A C build step failed; the message carries the command and compiler output."""


@dataclass
class CBuild:
    dir: Path
    optar: Path
    unoptar: Path | None
    golay_codes_c: Path


def compiler() -> str | None:
    """Return the C compiler command, or None if none is available."""
    return shutil.which(os.environ.get("CC") or "cc")


def _run(cmd: list[str], cwd: Path, **kw) -> subprocess.CompletedProcess:
    """Run a build command; raise CBuildError with its output if it fails."""
    kw.setdefault("stdout", subprocess.PIPE)
    try:
        r = subprocess.run(cmd, cwd=cwd, text=True, stderr=subprocess.PIPE, **kw)
    except OSError as e:
        raise CBuildError(f"{shlex.join(cmd)}: {e}") from e
    if r.returncode != 0:
        output = "\n".join(part.strip() for part in (r.stdout, r.stderr) if part and part.strip())
        raise CBuildError(f"{shlex.join(cmd)} exited with {r.returncode}: {output}")
    return r


def _tool_flags(cmd: list[str]) -> list[str]:
    if shutil.which(cmd[0]) is None:
        return []
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, OSError):
        return []
    return shlex.split(out)


def _png_flags() -> list[str]:
    flags = _tool_flags(["libpng-config", "--I_opts"])
    if not flags:
        flags = _tool_flags(["pkg-config", "--cflags", "libpng"])
    return flags + shlex.split(os.environ.get("OPTAR_TEST_CFLAGS", ""))


def _has_png_h(cc: str, flags: list[str], cwd: Path) -> bool:
    src = cwd / "pngcheck.c"
    src.write_text("#include <png.h>\nint main(void){return 0;}\n")
    r = subprocess.run([cc, "-fsyntax-only", *flags, str(src)], cwd=cwd, capture_output=True)
    return r.returncode == 0


def _override(header: Path, overrides: dict[str, int]) -> None:
    text = header.read_text()
    for name, value in overrides.items():
        text, n = re.subn(
            rf"^(#define\s+{re.escape(name)}\s+)\S+", rf"\g<1>{value}", text, flags=re.M
        )
        if n != 1:
            raise ValueError(f"cannot override {name} in optar.h")
    header.write_text(text)


def _link_unoptar(cc: str, cwd: Path, src: str, name: str) -> Path:
    """Compile an unoptar source and link it like the normal unoptar."""
    obj = src.replace(".c", ".o")
    _run([cc, "-c", *CFLAGS, *_png_flags(), "-o", obj, src], cwd)
    extra_ld = shlex.split(os.environ.get("OPTAR_TEST_LDFLAGS", ""))
    _run([cc, "-o", name, obj, *UNOPTAR_OBJECTS, *extra_ld, *UNOPTAR_LIBS], cwd)
    return cwd / name


def build_patched_unoptar(build: CBuild, name: str, replacements: list[tuple[str, str]]) -> Path:
    """Build a copy of the build's unoptar.c with exact-string replacements applied.

    Each `old` must occur exactly once. Writes <name>.c in the build directory
    and returns the linked executable. Raises RuntimeError when the build has
    no unoptar (libpng unavailable); callers skip on build.unoptar is None.
    """
    if build.unoptar is None:
        raise RuntimeError("unoptar was not built (libpng headers not available)")
    cc = compiler()
    if cc is None:
        raise RuntimeError("no C compiler found")
    text = (build.dir / "unoptar.c").read_text()
    for old, new in replacements:
        n = text.count(old)
        if n != 1:
            raise ValueError(f"replacement target occurs {n} times, expected 1: {old!r}")
        text = text.replace(old, new)
    (build.dir / f"{name}.c").write_text(text)
    return _link_unoptar(cc, build.dir, f"{name}.c", name)


def build_c_tools(dest: Path, format_overrides: dict[str, int] | None = None) -> CBuild:
    """Copy the C sources into dest, apply overrides, and build the tools there.

    Raises CBuildError if optar cannot be built. If unoptar cannot be built
    (no png.h, or linking against libpng fails), CBuild.unoptar is None.
    """
    cc = compiler()
    if cc is None:
        raise CBuildError("no C compiler found")
    dest = Path(dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    for name in C_SOURCES:
        shutil.copy(C_DIR / name, dest / name)
    if format_overrides:
        _override(dest / "optar.h", format_overrides)

    extra_c = shlex.split(os.environ.get("OPTAR_TEST_CFLAGS", ""))
    extra_ld = shlex.split(os.environ.get("OPTAR_TEST_LDFLAGS", ""))
    png_flags = _png_flags()
    has_png = _has_png_h(cc, png_flags, dest)

    def compile_(src: str, flags: list[str]) -> str:
        obj = src.replace(".c", ".o")
        _run([cc, "-c", *CFLAGS, *flags, "-o", obj, src], dest)
        return obj

    plain = [compile_(s, extra_c) for s in ("common.c", "golay.c", "optar.c", "parity.c")]
    common, golay_o, optar_o, parity = plain
    _run([cc, "-o", "golay", golay_o, parity, "-lm", *extra_ld], dest)
    with open(dest / "golay_codes.c", "w") as f:
        _run([str(dest / "golay")], dest, stdout=f)
    codes = compile_("golay_codes.c", extra_c)
    _run([cc, "-o", "optar", optar_o, common, codes, parity, "-lm", *extra_ld], dest)

    unoptar = None
    if has_png:
        try:
            unoptar = _link_unoptar(cc, dest, "unoptar.c", "unoptar")
        except CBuildError:
            unoptar = None
    return CBuild(dest, dest / "optar", unoptar, dest / "golay_codes.c")


def build_seq2xy_dump(build: CBuild) -> Path:
    """Compile tests/oracle/seq2xy_dump.c against the build's common.o; return the binary."""
    cc = compiler()
    if cc is None:
        raise RuntimeError("no C compiler found")
    shutil.copy(REPO_ROOT / "tests" / "oracle" / "seq2xy_dump.c", build.dir)
    extra_c = shlex.split(os.environ.get("OPTAR_TEST_CFLAGS", ""))
    extra_ld = shlex.split(os.environ.get("OPTAR_TEST_LDFLAGS", ""))
    _run([cc, "-c", *CFLAGS, *extra_c, "-o", "seq2xy_dump.o", "seq2xy_dump.c"], build.dir)
    _run(
        [cc, "-o", "seq2xy_dump", "seq2xy_dump.o", "common.o", "golay_codes.o", "parity.o",
         "-lm", *extra_ld],
        build.dir,
    )  # fmt: skip
    return build.dir / "seq2xy_dump"
