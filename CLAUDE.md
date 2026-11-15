# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build

- `make` builds `optar` (encoder, libc only) and `unoptar` (decoder, needs libpng + zlib). The Makefile finds libpng headers only through `libpng-config`; there is no pkg-config fallback, so `unoptar` fails to compile without it.
- `golay_codes.c` is generated at build time by the host program `golay` (`golay.c` + `parity.c`). Never edit or commit it; change `golay.c` instead.
- `pgm2ps` needs ImageMagick `convert` at runtime.
- `make clean` deletes every `*.pgm` and `*.ps` in the repo root. Keep test inputs and outputs elsewhere.
- `make archive` names the tarball from `git describe`, which fails because the repo has no tags.
- `archive_pdf` is unfinished (issue #11): the PS/PDF dimensions are wrong.
- `CFLAGS` has `-DNODEBUG`, not `-DNDEBUG`, so `assert()` is active in normal builds.
- `.travis.yml` is dead (travis-ci.org) and its deploy step is tied to `colindean/optar`. Nothing runs in CI.

## Testing

There is no test suite. Verify changes to the encoder or decoder with the `/roundtrip` skill. `unoptar` output is zero-padded to a full page, so compare only the first N bytes of the original.

## Encoder and decoder must stay in sync

The page format is compiled in from `optar.h`. `unoptar` parses the format string argument (`0-65-93-24-3-1-2-24`) but ignores every field except the last (text height), so the two binaries only interoperate when built from the same `optar.h`. Format changes are in scope, but apply each one to both sides and rebuild both binaries:

- Geometry and FEC macros in `optar.h` (`BORDER`, `CHALF`, `CPITCH`, `XCROSSES`, `YCROSSES`, `FEC_ORDER`) drive static array sizes in `unoptar.c` and the `#if FEC_ORDER` branches in both `optar.c` and `unoptar.c`.
- Paper size is set in two places: `XCROSSES`/`YCROSSES` in `optar.h` and the `convert -page` geometry in `pgm2ps`.
- Bit interleaving: `write_payloadbit` in `optar.c` and `read_syms` in `unoptar.c`. Byte order is MSB first on both sides. Black is 1, white is 0.
- Text height is 24 in three places: `TEXT_HEIGHT` in `optar.c`, the `text_height` default in `unoptar.c`, and the bitmap in `font.h` (a GIMP export; `TEXT_WIDTH` 13 in `optar.h` must match its glyph layout).

`unoptar` writes decoded data to stdout and diagnostics to stderr. It reads `<base>_0001.png`, `<base>_0002.png`, ... while `optar` writes `<base>_0001.pgm`, ...

## Code style

Match the existing C, which no formatter enforces:

- Hard tabs for indentation.
- Function bodies open with `{` on its own line; control statements keep it on the same line with no space: `for (p=0;p<12;p++){`, `}else{`.
- Tight spacing around operators (`in^=in>>16;`).
- `/* */` comments only, C89-style declarations at the top of a block.
- Keep the `/* (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs */` header on source files.

## Git

- `origin` is `mezinster/optar`, a fork of `colindean/optar`. Open branches and pull requests against the fork only (`gh pr create --repo mezinster/optar`); `gh` defaults to the upstream parent.
- Commit subjects are capitalised, third-person present, with no prefix: "Adds OS and architecture to archive name", "Fixes YAML for travis". Prefix unfinished work with `WIP:` and reference the issue in the body ("Work towards #11").
