# Development

The source is at [github.com/mezinster/optar](https://github.com/mezinster/optar).

## Setup and tests

    python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
    .venv/bin/pytest -q
    .venv/bin/ruff check .

No test needs a C compiler.

| Command | What it runs |
|---|---|
| `.venv/bin/pytest -q` | the default suite |
| `.venv/bin/pytest -q -m gs` | the checks of the PDF output; needs Ghostscript |
| `.venv/bin/pytest -q -m slow` | the long tests; add `-n auto` to use every core |
| `.venv/bin/pytest -q -m slow tests/unit/test_claims.py` | the simulated-scan tests behind [What has and has not been shown](evidence.md) |
| `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui` | the application's tests |

The application's tests need PySide6 and pytest-qt
(`pip install -e '.[dev,gui-dev]'`) and are skipped without them.

## What defines the format

The page format is defined by the [format specification](format.md) and by the
conformance vectors in `tests/vectors`. `tests/unit/test_spec.py` compares the
specification's tables and examples with the code, so the document and the
code are changed together.

## Building the one-file programs

    .venv/bin/pyinstaller --onefile --name optar --collect-data optar packaging/entry.py
    python packaging/smoke.py dist/optar

The application:

    .venv/bin/pyinstaller --onefile --name optar-gui --collect-data optar packaging/gui_entry.py

The release workflow builds both for Linux, macOS and Windows when a version
tag is pushed.

## This site

The pages are the Markdown files in `docs/`, built with MkDocs:

    .venv/bin/pip install -e '.[docs]'
    .venv/bin/mkdocs serve

A push to `master` that changes `docs/` publishes the site.
