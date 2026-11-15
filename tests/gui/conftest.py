# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Fixtures for the application tests; the directory is skipped without PySide6.

Every test module here is skipped at collection, before it is imported, when
PySide6 or pytest-qt is missing, so the modules may import Qt at the top.
Qt runs off-screen (QT_QPA_PLATFORM=offscreen unless already set), and every
test here carries the ``gui`` marker and fails on any Qt warning.
"""

import importlib.util
import itertools
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from optar import PAPERS, PageFormat, encode  # noqa: E402
from optar.tag import make_tag, tagged_label  # noqa: E402
from tests.helpers import fake_scan, save_scan, seeded_bytes  # noqa: E402

_HERE = Path(__file__).parent
_REASON = "the GUI tests need PySide6 and pytest-qt (pip install -e '.[gui-dev]')"
_HAVE_QT = all(importlib.util.find_spec(m) is not None for m in ("PySide6", "pytestqt"))


class _QtModule(pytest.Module):
    """A test module that is skipped, without being imported, when Qt is missing."""

    def collect(self):
        pytest.importorskip("PySide6.QtCore", reason=f"PySide6 is not installed: {_REASON}")
        pytest.importorskip("pytestqt", reason=f"pytest-qt (with PySide6) is missing: {_REASON}")
        return super().collect()


def pytest_pycollect_makemodule(module_path, parent):
    return _QtModule.from_parent(parent, path=module_path)


def pytest_collection_modifyitems(config, items):
    for item in items:
        if _HERE in Path(item.path).parents:
            item.add_marker(pytest.mark.gui)
            if _HAVE_QT:
                item.add_marker(pytest.mark.qt_log_level_fail("WARNING"))


@pytest.fixture
def scan_files(tmp_path):
    """Factory writing an encoded document as PNG scans, one per page.

    scan_files(nbytes=250_000, paper="a4", name="doc.tar", seed=1, scale=1,
    untagged=False, **fake_scan_kwargs) -> (data, [path of page 1, page 2, ...]).
    Pages carry the per-page tagged label, or just ``name`` when untagged.
    """
    calls = itertools.count(1)

    def make(nbytes=250_000, paper="a4", name="doc.tar", seed=1, scale=1, untagged=False,
             **fake_scan_kwargs):  # fmt: skip
        data = seeded_bytes(seed, nbytes)
        fmt = PageFormat.for_paper(PAPERS[paper])
        if untagged:
            label = name
        else:
            tag = make_tag(data)

            def label(page, total):
                return tagged_label(tag, name, page, total)

        folder = tmp_path / f"scans-{next(calls)}"
        folder.mkdir()
        paths = []
        for page in encode(data, fmt, label):
            path = folder / f"page-{page.number}.png"
            save_scan(path, fake_scan(page.pixels, scale=scale, **fake_scan_kwargs))
            paths.append(str(path))
        return data, paths

    return make
