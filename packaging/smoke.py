# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Smoke test for the built one-file executable.

Usage: python packaging/smoke.py EXECUTABLE

Standard library only: it runs the executable and never imports optar (it reads
the catalogue files as data).
"""

import hashlib
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

TIMEOUT = 600
PAYLOAD_SIZE = 50_000
SOURCE = Path(__file__).resolve().parent.parent / "src" / "optar"
INIT_FILE = SOURCE / "__init__.py"
LOCALE = SOURCE / "locale"
ORDER = ("en", "ru", "uk", "be", "pl", "ka", "tr", "it", "es")


def fail(message):
    print(f"SMOKE FAIL: {message}", file=sys.stderr)
    sys.exit(1)


def expected_version():
    text = INIT_FILE.read_text(encoding="utf-8")
    match = re.search(r"""^__version__\s*=\s*["']([^"']+)["']""", text, re.MULTILINE)
    if not match:
        fail(f"cannot find __version__ in {INIT_FILE}")
    return match.group(1)


def payload():
    out = bytearray()
    counter = 0
    while len(out) < PAYLOAD_SIZE:
        out += hashlib.sha256(b"optar-smoke" + counter.to_bytes(4, "big")).digest()
        counter += 1
    return bytes(out[:PAYLOAD_SIZE])


def run(exe, *args, env=None):
    cmd = [exe, *map(str, args)]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT, env=env)
    except subprocess.TimeoutExpired:
        fail(f"timed out after {TIMEOUT}s: {' '.join(cmd)}")
    except OSError as exc:
        fail(f"cannot run {exe}: {exc}")
    return result


def run_ok(exe, *args, env=None):
    result = run(exe, *args, env=env)
    if result.returncode != 0:
        fail(
            f"exit code {result.returncode} from: {exe} {' '.join(map(str, args))}\n"
            f"stdout: {result.stdout.decode(errors='replace')}\n"
            f"stderr: {result.stderr.decode(errors='replace')}"
        )
    return result


# The catalogue tables the command line prints (optar.cli.TERMINAL_TABLES; a test
# keeps the two equal, as it keeps ORDER equal to optar.i18n.ORDER).
TERMINAL_TABLES = ("cli", "err", "count", "alternatives", "format", "gui.cli", "language")
# The encodings the executable's output pipe may plausibly have: UTF-8, and the
# ANSI code page of a Western Windows machine. The pipe's real encoding is not
# guessed; a language that fits all of these must be shown whatever it is.
PLAUSIBLE_ENCODINGS = ("utf-8", "cp1252")
# Tried first: their terminal words fit every plausible encoding.
FIRST = ("it", "es")


def terminal_strings(code):
    """The strings of the catalogue's terminal tables, read from the source file
    (optar is not imported). A missing or unreadable catalogue fails the check."""
    path = LOCALE / f"{code}.toml"
    try:
        catalogue = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        fail(f"cannot read the catalogue {path}: {exc}")
    strings = []
    for table in TERMINAL_TABLES:
        item = catalogue
        for part in table.split("."):
            item = item.get(part, {}) if isinstance(item, dict) else {}
        stack = [item]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                stack.extend(item.values())
            elif isinstance(item, str):
                strings.append(item)
    return strings


def fits(strings, encoding):
    try:
        for string in strings:
            string.encode(encoding)
    except UnicodeEncodeError:
        return False
    return True


def help_in(exe, code):
    """The text of ``--help`` with OPTAR_LANG=code, as a string."""
    env = {**os.environ, "OPTAR_LANG": code}
    result = run_ok(exe, "--help", env=env)
    return result.stdout.decode(errors="replace") + result.stderr.decode(errors="replace")


def is_georgian(text):
    return any("\u10a0" <= ch <= "\u10ff" for ch in text)


def check_catalogues(exe):
    """The build carries the catalogues.

    The command line answers in English when its output encoding cannot hold the
    language, and the pipe's encoding is not guessed: the languages are tried, those
    that fit every plausible encoding first, and the first whose --help differs from
    the English help proves the catalogues are in the build. The check fails when
    none differs although one fits every plausible encoding. Georgian is an
    informative line: shown in Georgian, or not (an encoding that cannot hold it).
    """
    terminal_strings("en")  # every source catalogue must be readable
    english = help_in(exe, "en")
    order = [*FIRST, *(code for code in ORDER if code not in ("en", *FIRST))]
    sure = [code for code in order
            if all(fits(terminal_strings(code), e) for e in PLAUSIBLE_ENCODINGS)]  # fmt: skip
    for code in order:
        if help_in(exe, code) != english:
            print(f"ok: --help in {code} differs from English")
            break
    else:
        if sure:
            fail(f"--help is the English help in every language, though {', '.join(sure)} "
                 f"fit{'s' if len(sure) == 1 else ''} every plausible output encoding "
                 f"({', '.join(PLAUSIBLE_ENCODINGS)}): the catalogues are not in the build")
        print("note: no language fits every plausible output encoding; catalogues not checked")
    georgian = help_in(exe, "ka")
    if is_georgian(georgian) and not is_georgian(english):
        print("ok: --help in Georgian shows Georgian letters")
    else:
        print("note: --help with OPTAR_LANG=ka is not in Georgian here "
              "(the output encoding cannot hold it); not required")


def main(argv):
    if len(argv) != 2:
        print("usage: smoke.py EXECUTABLE", file=sys.stderr)
        return 2
    exe = argv[1]
    version = expected_version()
    data = payload()

    result = run_ok(exe, "--version")
    shown = result.stdout.decode(errors="replace") + result.stderr.decode(errors="replace")
    if version not in shown:
        fail(f"--version output {shown.strip()!r} does not contain {version!r}")
    print(f"ok: --version ({version})")

    check_catalogues(exe)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        source = tmp / "input.bin"
        source.write_bytes(data)

        run_ok(exe, "encode", source, "--to", "png", "-o", tmp / "page")
        pages = sorted(tmp.glob("page_*.png"))
        if not pages:
            fail("encode --to png produced no page_*.png files")
        if not (tmp / "page_0001.png").exists():
            fail("encode --to png did not produce page_0001.png")
        print(f"ok: encode --to png ({len(pages)} page(s))")

        decoded = tmp / "out.bin"
        run_ok(exe, "decode", tmp / "page", "-o", decoded)
        if not decoded.exists():
            fail("decode did not create the output file")
        if decoded.read_bytes()[:PAYLOAD_SIZE] != data:
            fail(f"decoded first {PAYLOAD_SIZE} bytes differ from the input")
        print("ok: decode round trip")

        run_ok(exe, "encode", source, "-o", tmp / "doc")
        pdf = tmp / "doc.pdf"
        if not pdf.exists():
            fail("encode (default) did not produce doc.pdf")
        if not pdf.read_bytes().startswith(b"%PDF"):
            fail("doc.pdf does not start with %PDF")
        print("ok: encode to pdf")

    print("smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
