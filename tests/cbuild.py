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
C_SOURCES = [
    "common.c", "golay.c", "optar.c", "parity.c", "unoptar.c",
    "optar.h", "font.h", "parity.h",
]  # fmt: skip
CFLAGS = ["-O3", "-Wall", "-DNODEBUG"]


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
    return subprocess.run(cmd, cwd=cwd, check=True, text=True, **kw)


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


def build_c_tools(dest: Path, format_overrides: dict[str, int] | None = None) -> CBuild:
    """Copy the C sources into dest, apply overrides, and build the tools there."""
    cc = compiler()
    if cc is None:
        raise RuntimeError("no C compiler found")
    dest.mkdir(parents=True, exist_ok=True)
    for name in C_SOURCES:
        shutil.copy(REPO_ROOT / name, dest / name)
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
        _run(["./golay"], dest, stdout=f)
    codes = compile_("golay_codes.c", extra_c)
    _run([cc, "-o", "optar", optar_o, common, codes, parity, "-lm", *extra_ld], dest)

    unoptar = None
    if has_png:
        unoptar_o = compile_("unoptar.c", png_flags)
        _run(
            [cc, "-o", "unoptar", unoptar_o, common, codes, parity,
             *extra_ld, "-lm", "-lpng", "-lz"],
            dest,
        )  # fmt: skip
        unoptar = dest / "unoptar"
    return CBuild(dest, dest / "optar", unoptar, dest / "golay_codes.c")
