# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Python package (primary code)

`src/optar` is the Python port; the C sources, in `lega-c/`, are its read-only test oracle. Setup and commands:

- `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`
- `.venv/bin/pytest -q`: default suite, needs no C compiler.
- `.venv/bin/pytest -q -m "oracle or gs or slow"`: compares against the C tools; needs a C compiler, libpng headers and Ghostscript. Without system libpng headers, point at them with `OPTAR_TEST_CFLAGS` / `OPTAR_TEST_LDFLAGS`.
- Add `-n auto` (pytest-xdist) to run tests on every core; CI does this for the three big slow files. Tests that measure time or memory (`test_speed.py` and the like) must run without it.
- `.venv/bin/ruff check .`
- GUI tests: `.venv/bin/pip install -e '.[dev,gui-dev]'`, then `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui`. The `gui` marker is applied to all of `tests/gui`, and those tests are skipped without PySide6 and pytest-qt, so the default suite needs neither.
- `optar-gui --self-test` runs an encode and a decode without a window; the release build must pass it.
- One-file build: `.venv/bin/pyinstaller --onefile --name optar --collect-data optar packaging/entry.py`, then `python packaging/smoke.py dist/optar`.
- Regenerate `tests/golden/fixtures.json` with `.venv/bin/python -m tests.golden.make_fixtures` (needs a C compiler). The output must be unchanged unless the C sources changed.

Rules:

- Format numbers (65, 93, 24, 3, 2, 13, 200, paper sizes, dot sizes, grids per dot size, header, spread and parity numbers) live only in `src/optar/format.py`.
- Everything in `lega-c/` (the C sources, `Makefile` and `pgm2ps`) is the test oracle. Do not edit it.
- Library modules never print, call `sys.exit` or read `sys.argv`; only `cli.py` does.
- The decoder mirrors the C algorithm and its constants. Do not retune it without real scans.
- `decoder.dirt.remove_border_dirt` is the exact C step; the readers call `isolate_page`, which differs only for a scan whose page frame has a gap (a printer clipped an edge). That came from the owner's real scans.
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

## C build notes (oracle)

The C sources live in `lega-c/`; run `make` there.

- `make` builds `optar` (encoder, libc only) and `unoptar` (decoder, needs libpng + zlib). The Makefile finds libpng headers only through `libpng-config`; there is no pkg-config fallback, so `unoptar` fails to compile without it.
- `golay_codes.c` is generated at build time by the host program `golay` (`golay.c` + `parity.c`). Never edit or commit it; change `golay.c` instead.
- `pgm2ps` needs ImageMagick `convert` at runtime.
- `make clean` deletes every `*.pgm` and `*.ps` in `lega-c/`. Keep test inputs and outputs elsewhere.
- `make archive` names the tarball from `git describe`, which fails because the repo has no tags.
- `archive_pdf` is unfinished (issue #11): the PS/PDF dimensions are wrong.
- `CFLAGS` has `-DNODEBUG`, not `-DNDEBUG`, so `assert()` is active in normal builds.
- The `/roundtrip` skill checks the C tools only.

## C encoder and decoder must stay in sync

The page format is compiled in from `optar.h`. `unoptar` parses the format string argument (`0-65-93-24-3-1-2-24`) but ignores every field except the last (text height), so the two binaries only interoperate when built from the same `optar.h`. The C sources are frozen as the oracle, so this only describes how they work. If they are ever changed deliberately, apply each change to both sides and rebuild both binaries:

- Geometry and FEC macros in `optar.h` (`BORDER`, `CHALF`, `CPITCH`, `XCROSSES`, `YCROSSES`, `FEC_ORDER`) drive static array sizes in `unoptar.c` and the `#if FEC_ORDER` branches in both `optar.c` and `unoptar.c`.
- Paper size is set in two places: `XCROSSES`/`YCROSSES` in `optar.h` and the `convert -page` geometry in `pgm2ps`.
- Bit interleaving: `write_payloadbit` in `optar.c` and `read_syms` in `unoptar.c`. Byte order is MSB first on both sides. Black is 1, white is 0.
- Text height is 24 in three places: `TEXT_HEIGHT` in `optar.c`, the `text_height` default in `unoptar.c`, and the bitmap in `font.h` (a GIMP export; `TEXT_WIDTH` 13 in `optar.h` must match its glyph layout).

`unoptar` writes decoded data to stdout and diagnostics to stderr. It reads `<base>_0001.png`, `<base>_0002.png`, ... while `optar` writes `<base>_0001.pgm`, ...

## Code style

For C, match the existing code, which no formatter enforces:

- Hard tabs for indentation.
- Function bodies open with `{` on its own line; control statements keep it on the same line with no space: `for (p=0;p<12;p++){`, `}else{`.
- Tight spacing around operators (`in^=in>>16;`).
- `/* */` comments only, C89-style declarations at the top of a block.
- Keep the `/* (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs */` header on source files.

## Git

- `origin` is `mezinster/optar`, a fork of `colindean/optar`. Open branches and pull requests against the fork only (`gh pr create --repo mezinster/optar`); `gh` defaults to the upstream parent.
- Commit subjects are capitalised, third-person present, with no prefix: "Adds OS and architecture to archive name", "Fixes YAML for travis". Prefix unfinished work with `WIP:` and reference the issue in the body ("Work towards #11").
