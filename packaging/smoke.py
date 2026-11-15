# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Smoke test for the built one-file executable.

Usage: python packaging/smoke.py EXECUTABLE

Standard library only: it runs the executable and never imports optar.
"""

import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TIMEOUT = 600
PAYLOAD_SIZE = 50_000
INIT_FILE = Path(__file__).resolve().parent.parent / "src" / "optar" / "__init__.py"


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


def run(exe, *args):
    cmd = [exe, *map(str, args)]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        fail(f"timed out after {TIMEOUT}s: {' '.join(cmd)}")
    except OSError as exc:
        fail(f"cannot run {exe}: {exc}")
    return result


def run_ok(exe, *args):
    result = run(exe, *args)
    if result.returncode != 0:
        fail(
            f"exit code {result.returncode} from: {exe} {' '.join(map(str, args))}\n"
            f"stdout: {result.stdout.decode(errors='replace')}\n"
            f"stderr: {result.stderr.decode(errors='replace')}"
        )
    return result


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
