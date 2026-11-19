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

## Translations

The application and this site are available in nine languages: `en`, `ru`,
`uk`, `be`, `pl`, `ka`, `tr`, `it`, `es`. English is the source.

**The wording of the programs** is in `src/optar/locale/<code>.toml`, one file
per language with the same keys. To add or change a string, edit
`en.toml` and every other catalogue in the same pull request; a plural entry
has the categories of its language (`optar.i18n.categories(code)`).
`tests/unit/test_catalogues.py` checks that the catalogues agree. To see the
command-line program in another language set `OPTAR_LANG`, for example
`OPTAR_LANG=ru optar --help`; the application has a language menu.

**The pages** are `docs/<page>.<code>.md` beside the English `docs/<page>.md`.
A translated page has `source_hash` in its front matter, the English id on
every heading and code blocks equal to English. To see which pages are
behind, run `python tools/translation_status.py`. To refresh a stale page,
read what changed in the English page (`git diff` against the commit of its
`source_hash`), change the translation to match, then set `source_hash` to
`git hash-object docs/<page>.md`. `tests/unit/test_doc_translations.py` checks
the rest. The rules for translators are in
`docs/superpowers/translation-brief.md`.

**What the site does with them**, found with a throwaway Russian page and
language entry (removed again):

- A page with no translation appears in English under `/ru/`, with the
  translated navigation around it (`fallback_to_default`).
- The language switcher appears in the header once there is a second
  language.
- Search is one index for the whole site. It lists results of every language
  together; an untranslated page is indexed once, under its English address,
  not again under `/ru/`.
