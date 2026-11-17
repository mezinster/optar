# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Python package

The page format is defined by `docs/format.md` and the conformance vectors in `tests/vectors`. The original C program in `lega-c/` is history and is never edited. Setup and commands:

- `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`
- `.venv/bin/pytest -q`: default suite. No test needs a C compiler.
- `.venv/bin/pytest -q -m gs`: checks the PDF output; needs Ghostscript. `.venv/bin/pytest -q -m slow`: the long tests.
- Add `-n auto` (pytest-xdist) to run tests on every core; CI does this for the three big slow files. Tests that measure time or memory (`test_speed.py` and the like) must run without it.
- `.venv/bin/ruff check .`
- GUI tests: `.venv/bin/pip install -e '.[dev,gui-dev]'`, then `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui`. The `gui` marker is applied to all of `tests/gui`, and those tests are skipped without PySide6 and pytest-qt, so the default suite needs neither.
- `optar-gui --self-test` runs an encode and a decode without a window; the release build must pass it.
- One-file build: `.venv/bin/pyinstaller --onefile --name optar --collect-data optar packaging/entry.py`, then `python packaging/smoke.py dist/optar`.

Rules:

- Format numbers (65, 93, 24, 3, 2, 13, 200, paper sizes, dot sizes, grids per dot size, header, spread and parity numbers) live only in `src/optar/format.py`. The few numbers that belong to one algorithm stay with it (`MAX_PAGES` in `encoder.py`, the font and tag sizes, the field polynomial in `rs.py`); the constants table of `docs/format.md` names each one.
- `docs/format.md` and `tests/vectors` define the format. `tests/unit/test_spec.py` compares the specification's tables and examples with the code: change the document and the code together.
- The vectors under `tests/vectors/c` were recorded from the C tools once and cannot be recorded again without reviving the C build. Never edit them to make a test pass. `tests/vectors` stays under 2,000,000 bytes (a test checks it).
- Library modules never print, call `sys.exit` or read `sys.argv`; only `cli.py` does.
- Decoder results are pinned by the vectors. Change them only with real scans as the reason, and then deliberately, updating the vectors in the same pull request.
- The second, slower reader for coarse scans lives in `decoder/soft.py` (its tuning numbers are named constants there, not in `format.py`). It is tried only after the ordinary reader has failed, or has read no more than an untagged label on a coarse scan whose data it could not read well (`identify.identify_any`); a valid tag is never questioned. It must not change the ordinary reader's results or the vectors that pin them.
- `decoder.dirt.remove_border_dirt` is the exact step of the original C decoder; the readers call `isolate_page`, which differs only for a scan whose page frame has a gap (a printer clipped an edge). That came from the owner's real scans.
- Tests write only under pytest's `tmp_path`.
- Runtime dependencies are numpy and Pillow only. No JPEG output.
- GUI build (`optar-gui`, as in `.github/workflows/build.yml`, which the release workflow calls; macOS uses `--windowed` without `--onefile`): `.venv/bin/pyinstaller --onefile --name optar-gui --collect-data optar packaging/gui_entry.py`.
- A `.py` edit is linted by the PostToolUse hook with `.venv/bin/ruff`.
- Every page, whatever the dot size or protection, stays an ordinary version-0 optar page. `encode()` is not changed for the self-identifying (version 1) printouts: the container wraps the stream before it and unwraps it after.
- The label of a larger-dot page is printed at the standard size by a strip the PDF draws over the label band (`font.fine_label`, `write_pdf`); the page pixels from `encode()` are not changed, and nothing may depend on reading that label from a scan.
- The unused room of a version-1 document is filled by `container.padding` (fixed, defined in `format.py`), never with zeros. Readers must not look at it: 0.3.0 printouts hold zeros there.
- A valid label tag wins over a header found in the data (a re-printed old stream must stay a 0.2.0 page).
- Only the fingerprint makes a file "verified"; a repair that reports no failure does not.
- A page header is untrusted: one scanned page can claim any document. `container.document_plan` is the one check of what a header may claim, and `unwrap()` must keep its memory and time in proportion to the pages supplied, never to the claim.
- The claims tests (`tests/unit/test_claims.py`, marked `slow`) are the project's claims about simulated scans. Do not loosen them or change the simulator's defaults to make them pass. Run them with `.venv/bin/pytest -q -m slow tests/unit/test_claims.py`.
- The user's real scans are never copied into the repository, so `tests/scans` stays empty of scans.

## Desktop application (`src/optar_gui`)

- Nothing under `src/optar` imports Qt or `optar_gui`. `document.py`, `work.py` and `text.py` import no Qt either.
- Rules (placement of scans, page health, document state) live in `document.py`; widgets only show them.
- No scan is read, decoded, hashed or saved on the interface thread; use the jobs.
- Every user-visible string lives in `text.py`.
- Untrusted text (label text, file names) is shown as plain text, never as rich text.

## History: `lega-c`

`lega-c/` holds the original C program (`optar`, `unoptar`, `pgm2ps`) as history. Nothing builds or runs it. Do not edit, reformat or delete anything in it. `lega-c/record_vectors/` is the script that recorded the C vectors; it is kept as a record and is not run. `tools/extract_font.py` and `tests/unit/test_font.py` read `lega-c/font.h` as data.

## Git

- `origin` is `mezinster/optar`, a fork of `colindean/optar`. Open branches and pull requests against the fork only (`gh pr create --repo mezinster/optar`); `gh` defaults to the upstream parent.
- Commit subjects are capitalised, third-person present, with no prefix: "Adds OS and architecture to archive name", "Fixes YAML for travis". Prefix unfinished work with `WIP:` and reference the issue in the body ("Work towards #11").
