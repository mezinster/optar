# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Python package (primary code)

`src/optar` is the Python port; the C sources are its read-only test oracle. Setup and commands:

- `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`
- `.venv/bin/pytest -q`: default suite, needs no C compiler.
- `.venv/bin/pytest -q -m "oracle or gs or slow"`: compares against the C tools; needs a C compiler, libpng headers and Ghostscript. Without system libpng headers, point at them with `OPTAR_TEST_CFLAGS` / `OPTAR_TEST_LDFLAGS`.
- `.venv/bin/ruff check .`
- One-file build: `.venv/bin/pyinstaller --onefile --name optar --collect-data optar packaging/entry.py`, then `python packaging/smoke.py dist/optar`.
- Regenerate `tests/golden/fixtures.json` with `.venv/bin/python -m tests.golden.make_fixtures` (needs a C compiler). The output must be unchanged unless the C sources changed.

Rules:

- Format numbers (65, 93, 24, 3, 2, 13, 200, paper sizes) live only in `src/optar/format.py`.
- The C sources, `Makefile` and `pgm2ps` are the test oracle. Do not edit them.
- Library modules never print, call `sys.exit` or read `sys.argv`; only `cli.py` does.
- The decoder mirrors the C algorithm and its constants. Do not retune it without real scans.
- Tests write only under pytest's `tmp_path`, because `make clean` deletes `*.pgm` and `*.ps` in the repo root.
- Runtime dependencies are numpy and Pillow only. No JPEG output.
- A `.py` edit is linted by the PostToolUse hook with `.venv/bin/ruff`.

## C build notes (oracle)

- `make` builds `optar` (encoder, libc only) and `unoptar` (decoder, needs libpng + zlib). The Makefile finds libpng headers only through `libpng-config`; there is no pkg-config fallback, so `unoptar` fails to compile without it.
- `golay_codes.c` is generated at build time by the host program `golay` (`golay.c` + `parity.c`). Never edit or commit it; change `golay.c` instead.
- `pgm2ps` needs ImageMagick `convert` at runtime.
- `make clean` deletes every `*.pgm` and `*.ps` in the repo root. Keep test inputs and outputs elsewhere.
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
