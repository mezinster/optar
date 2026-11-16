# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The hidden self-test (``optar-gui --self-test``) that release builds must pass.

It runs an encode and a decode through the application's own background jobs
and document code, without showing a window, in a temporary directory. It
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

from optar.encoder import encode
from optar.format import PageFormat, get_paper
from optar.imageio import write_png
from optar.tag import make_tag, tagged_label
from optar_gui.document import DocState, Health
from optar_gui.work import encode_to_pdf

__all__ = ["run_self_test"]

SELF_TEST_BYTES = 250_000
SELF_TEST_NAME = "self-test.bin"
SELF_TEST_PAPER = "a4"
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
