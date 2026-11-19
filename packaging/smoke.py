# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Smoke test for the built one-file executable.

Usage: python packaging/smoke.py EXECUTABLE

Standard library only: it runs the executable and never imports optar (it reads
the catalogue files as data).
"""

import hashlib
import locale
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


def output_encoding():
    """The encoding the executable's output pipe will have.

    A frozen build does not reliably honour PYTHONIOENCODING or PYTHONUTF8, so none is
    forced: PYTHONIOENCODING counts only when the caller set it (an unfrozen test of
    this script), otherwise a pipe has the preferred (ANSI) encoding of the machine.
    """
    named = os.environ.get("PYTHONIOENCODING", "").split(":")[0]
    return named or locale.getpreferredencoding(False)


def encodable(code, encoding):
    """What ``optar.i18n.encodable`` says, read from the catalogue file (optar is not imported)."""
    path = LOCALE / f"{code}.toml"
    try:
        catalogue = tomllib.loads(path.read_text(encoding="utf-8"))
        strings = []
        stack = [catalogue]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                stack.extend(item.values())
            elif isinstance(item, str):
                strings.append(item)
        for string in strings:
            string.encode(encoding)
    except (UnicodeEncodeError, LookupError, OSError):
        return False
    return True


def help_in(exe, code):
    """The text of ``--help`` with OPTAR_LANG=code, as a string."""
    env = {**os.environ, "OPTAR_LANG": code}
    result = run_ok(exe, "--help", env=env)
    return result.stdout.decode(errors="replace") + result.stderr.decode(errors="replace")


def check_catalogues(exe):
    """The build carries the catalogues.

    The command line answers in English when its output encoding cannot hold the
    language, so a language is required to differ from English only when the output
    encoding can encode it. The first such language proves the catalogues are in the
    build; Georgian is checked as well when it can be encoded, else noted.
    """
    encoding = output_encoding()
    english = help_in(exe, "en")
    for code in ORDER:
        if code != "en" and encodable(code, encoding):
            if help_in(exe, code) == english:
                fail(f"--help with OPTAR_LANG={code} is the English help: "
                     "the catalogues are not in the build")
            print(f"ok: --help in {code} differs from English")
            break
    else:
        print(f"note: no language fits the output encoding {encoding}; catalogues not checked")
    if encodable("ka", encoding):
        georgian = help_in(exe, "ka")
        if georgian == english or not any("\u10a0" <= ch <= "\u10ff" for ch in georgian):
            fail("--help with OPTAR_LANG=ka is not Georgian")
        print("ok: --help in Georgian differs from English")
    else:
        print(f"note: output encoding {encoding} cannot hold Georgian; not required here")


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
