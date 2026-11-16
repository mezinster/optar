# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The hidden self-test (``optar-gui --self-test``) that release builds must pass.

It runs an encode and a decode through the application's own background jobs
and document code, without showing a window, in a temporary directory, creates
a PDF of each kind (protected, and compatible with optar 0.2), and wraps,
encodes, decodes and unwraps a small protected document with large dots. It
prints one line per check; a windowed program on Windows has no console
(``sys.stdout`` is None), so there the lines go to ``SELF_TEST_LOG`` in the
system's temporary directory instead.
"""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import time

import numpy as np

from optar.container import page_payload, read_header, unwrap, wrap
from optar.decoder import decode_page
from optar.encoder import encode
from optar.format import PARITY, PageFormat, get_layout, get_paper
from optar.imageio import write_png
from optar.tag import make_tag, tagged_label
from optar_gui.document import DocState, Health
from optar_gui.work import encode_to_pdf

__all__ = ["run_self_test"]

SELF_TEST_BYTES = 250_000
SELF_TEST_NAME = "self-test.bin"
SELF_TEST_PAPER = "a4"
# The protected document: dot size, protection and size.
SELF_TEST_DOTS = "large"
SELF_TEST_PROTECT = "standard"
SELF_TEST_PROTECTED_BYTES = 60_000
# Where the report goes when there is no console, in tempfile.gettempdir().
SELF_TEST_LOG = "optar-gui-self-test.log"
# How long reading the scans may take: generous, for slow or loaded machines.
SELF_TEST_TIMEOUT_MS = 600_000
# White margin around each page, as a scanner leaves around the paper.
_MARGIN = 60

_app = None  # the QApplication the self-test made, kept alive
_log = None  # the open log file while a self-test without a console runs


def _seeded_bytes(n: int) -> bytes:
    """Deterministic pseudo-random bytes: SHA-256 in counter mode."""
    out = bytearray()
    i = 0
    while len(out) < n:
        out += hashlib.sha256(f"optar-gui self-test:{i}".encode()).digest()
        i += 1
    return bytes(out[:n])


def _application():
    global _app
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = _app = QApplication(["optar-gui"])
    return app


def _report(name: str, ok: bool) -> bool:
    out = _log if _log is not None else sys.stdout
    print(f"{'ok' if ok else 'FAIL'} {name}", file=out, flush=True)
    return ok


def _wait_checked(controller, deadline: float) -> bool:
    """Process events until the controller's fingerprint check has delivered.

    The check runs in the background; False if it is still running at
    ``deadline`` (a ``time.monotonic()`` value).
    """
    from PySide6.QtCore import QCoreApplication, QEventLoop

    while controller.checking:
        if time.monotonic() >= deadline:
            return False
        QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
        time.sleep(0.01)
    QCoreApplication.processEvents()
    return True


def _protected_check() -> bool:
    """Wrap a file for Large dots with Standard protection, encode it, decode
    each page image exactly as encoded, and unwrap it: it must verify."""
    data = _seeded_bytes(SELF_TEST_PROTECTED_BYTES)
    fmt = get_layout(SELF_TEST_PAPER, SELF_TEST_DOTS).fmt
    stream = wrap(data, SELF_TEST_NAME, fmt, PARITY[SELF_TEST_PROTECT])
    header = None
    payloads = {}
    for page in encode(stream, fmt, SELF_TEST_NAME):
        image = np.pad(page.pixels, _MARGIN, constant_values=255)
        payload = page_payload(decode_page(image, fmt, detail=True), fmt)
        found = read_header(payload.data)
        if found is None or (header is not None and found.total != header.total):
            return _report("read the headers of the Large, Standard-protection pages", False)
        header = found
        payloads[found.page] = payload
    out = unwrap(header, fmt, payloads)
    ok = (
        len(payloads) == header.total > 1
        and out.verified
        and out.data == data
        and out.name == SELF_TEST_NAME
    )
    return _report(
        f"verified a {header.total}-page Large, Standard-protection document", ok
    )


def _checks(folder: str) -> bool:
    from optar_gui.read_tab import ReadController

    data = _seeded_bytes(SELF_TEST_BYTES)
    src = os.path.join(folder, SELF_TEST_NAME)
    with open(src, "wb") as f:
        f.write(data)
    fmt = PageFormat.for_paper(get_paper(SELF_TEST_PAPER))
    tag = make_tag(data)
    paths = []
    for page in encode(data, fmt, lambda p, t: tagged_label(tag, SELF_TEST_NAME, p, t)):
        path = os.path.join(folder, f"scan_{page.number:04d}.png")
        write_png(path, np.pad(page.pixels, _MARGIN, constant_values=255))
        paths.append(path)
    results = [_report(f"encoded {len(paths)} scans", len(paths) > 0)]

    controller = ReadController()
    try:
        controller.add_paths(paths)
        deadline = time.monotonic() + SELF_TEST_TIMEOUT_MS / 1000
        idle = controller.runner.wait_idle(SELF_TEST_TIMEOUT_MS)
        controller.refresh()  # starts the fingerprint check of a complete document
        checked = _wait_checked(controller, deadline)
        controller.refresh()
        results.append(_report("checked the fingerprint", checked))
        doc = controller.document
        pages = doc.pages()
        good = idle and len(pages) == len(paths) and all(p.health == Health.GOOD for p in pages)
        results.append(_report(f"read {len(pages)} pages", good))
        results.append(_report("verified", controller.summary.state == DocState.VERIFIED))
        same = doc.can_save and doc.assemble() == data
        results.append(_report("recovered file equals the original", same))
    finally:
        controller.shutdown()

    pdf = os.path.join(folder, "self-test.pdf")
    encode_to_pdf(src, pdf, SELF_TEST_PAPER, SELF_TEST_NAME)
    with open(pdf, "rb") as f:
        head = f.read(4)
    results.append(_report("created a PDF", head == b"%PDF"))
    # The printout optar 0.2 reads: as many pages as the scans encoded above.
    old = os.path.join(folder, "self-test-compatible.pdf")
    count = encode_to_pdf(src, old, SELF_TEST_PAPER, SELF_TEST_NAME, compatible=True)
    with open(old, "rb") as f:
        head = f.read(4)
    results.append(
        _report("created a compatible PDF", head == b"%PDF" and count == len(paths))
    )
    results.append(_protected_check())
    return all(results)


def run_self_test() -> int:
    """Run the self-test off-screen; print one line per check (to SELF_TEST_LOG
    when there is no console); 0 if all pass, else 1."""
    global _log
    if sys.stdout is None:
        _log = open(os.path.join(tempfile.gettempdir(), SELF_TEST_LOG), "w", encoding="utf-8")
    try:
        _application()
        try:
            with tempfile.TemporaryDirectory(prefix="optar-gui-self-test-") as folder:
                passed = _checks(folder)
        except Exception as e:  # any failure is a failed self-test, reported in one line
            _report(f"self-test stopped: {type(e).__name__}: {e}", False)
            return 1
        return 0 if passed else 1
    finally:
        if _log is not None:
            _log.close()
            _log = None
