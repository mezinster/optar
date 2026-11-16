---
name: roundtrip
description: Verify optar and unoptar with a synthetic encode/decode round trip (no printer or scanner). Use after any change to optar.c, unoptar.c, common.c, golay.c, parity.c, optar.h or font.h, and whenever asked to test or verify the encoder or decoder.
---

# Round-trip test

The repo has no test suite. This is the check that the encoder and decoder still agree.

## Run

From `lega-c`, where the C sources and their Makefile live:

```sh
cd lega-c && make && ../.claude/skills/roundtrip/roundtrip.sh
```

It encodes a file with `./optar`, turns each `.pgm` page into a PNG "scan" with `pgm2png.py` (standard-library Python, no ImageMagick), decodes with `./unoptar`, and compares the first N bytes with the input. It prints `PASS: ...` or `FAIL: ...` and exits non-zero on failure. All files go to a temporary directory, never the repository.

Options:

- `-s SCALE`: pixels per data pixel in the fake scan. The default is 3, which matches a 600 dpi scan of a 600 dpi print. Scales 1 and 2 also decode.
- `-k`: keep the work directory. It holds `optar.log`, `unoptar.log` and the `page_NNNN_debug.pgm` images `unoptar` writes, which show where it found the crosses.
- `INPUT_FILE`: encode this file instead of 300000 random bytes (two A4 pages).

## What to check for a given change

- Any change to the format (`optar.h` macros, FEC, bit layout): run at `-s 1` and `-s 3`.
- A change to paper size: also update `pgm2ps`. The round trip does not exercise `pgm2ps`.
- A change that affects page count or the last page: pass a file whose size is not a multiple of the page capacity, and one small file that fits on a single page.

## Limits

- This is a clean, noise-free image. It proves the two sides agree on the format; it does not prove the decoder still copes with a real scan (skew, blur, dirt). Say so when reporting results on changes to the decoder's image processing or its magic constants.
- `unoptar` output is zero-padded to a whole page, so the script compares only the input's length.
- `unoptar` ignores every field of its format argument except the last (text height), so the script passes zeros for the rest.

## If the build fails

`unoptar` needs libpng headers and `libpng-config` (`sudo apt install libpng-dev` on Debian/Ubuntu, `brew install libpng` on macOS). `optar` alone builds without them, but the round trip needs both binaries.
