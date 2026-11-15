# Optar Python port: design

Date: 2026-11-15
Status: awaiting approval

## Intent

Optar stores binary data on paper: `optar` turns a file into page images, `unoptar` turns scans of the printed pages back into the file. Today it is about 2,300 lines of C from 2007 with no tests and a dead CI.

The owner wants to treat it as a product to develop further. Two later projects are already in view:

1. A new page format with extra redundancy, in the spirit of dvdisaster (for example spare pages that can rebuild a lost or damaged page).
2. A flexible, cross-platform user interface.

This project is the foundation for both: a Python port, built test-first against the C binaries, shipped as a single bundled executable, with a GitHub Actions pipeline. It does not change the format or add a GUI, but it must not block either.

## Goals

- A Python library and command-line tool that encode and decode the existing optar format ("version 0").
- Print-ready output straight from the encoder: a PDF by default, PNG pages as an alternative, with no ImageMagick or `pgm2ps` step. (Owner's decision.)
- Proven compatibility with the C tools: identical encoder output, and each decoder reads the other encoder's pages.
- The page format is runtime data, not compile-time constants, and the decoder honours the format string it is given.
- Every piece of behaviour is written test-first.
- One self-contained executable per operating system (Linux, macOS, Windows), with Python, numpy and Pillow bundled.
- GitHub Actions: tests on every push and pull request; executables published on a version tag.

## Non-goals (this project)

- Any change to the on-paper format, including storing the file length. Decoded output stays zero-padded to a whole page, as in C.
- New redundancy or error-correction schemes.
- A graphical interface.
- Removing the C sources. They stay in place as the reference.

## Anti-goals

- A line-by-line translation that keeps C's global state and compiled-in format. That would force a rewrite before project 2.
- "Improving" the decoder's image processing or its tuned constants. They were tuned on real scans, and this repo has no real scans to re-tune against. The port reproduces the C algorithm stage by stage.
- Library code that prints, exits the process, or reads `sys.argv`. A later GUI must be able to call it.
- Tests that only pass when a C compiler is present. The default test run must work on a plain Python install.

## Constraints

- **License:** the C code is GPL v2 (`COPYING`), so the port is GPL-2.0. Keep the attribution to Karel 'Clock' Kulhavy, Twibright Labs.
- **Dependencies:** numpy and Pillow at runtime, nothing else. Development adds pytest, ruff and PyInstaller.
- **Python:** 3.10 or newer.
- **Repository:** work lands on `mezinster/optar` only. The C sources, `Makefile` and `pgm2ps` stay at the repo root untouched.
- **No real scans exist in the repo.** Decoder confidence comes from the C oracle and synthetic degradation, which is weaker than a real print-and-scan. See Risks.

## Approaches considered

- **A. Line-by-line port.** Translate the C as it stands, restructure later. Quickest to green tests, but inherits the compiled-in format and global state.
- **B. Library first (chosen by the owner).** A core package where the page format is a data object passed at runtime. The current format is "version 0", verified byte-for-byte against C. The command line is a thin layer; a later GUI or new format plugs into the same library.
- **C. Keep the C engine, wrap it in Python.** Least work and fastest decoding, but format work stays in C and bundling gets harder. It works against the reason for the port.

B was chosen because projects 2 and 3 both need the format and the pipeline to be reachable from Python as data and functions.

## How the C version works (what is being ported)

**Page layout.** A page is a grayscale image, black 0 and white 255. With the default A4 format it is 1546 x 2242 pixels: a 2-pixel black border, a grid of 65 x 93 registration crosses 24 pixels apart (each cross is 6 x 6, two black and two white 3 x 3 quadrants), data pixels everywhere between the crosses, and a 24-pixel text label along the bottom. Black is bit 1, white is bit 0.

**Label.** `  0-65-93-24-3-1-2-24 1/2 name`: the format string, page number / page count, and the label. The format fields are, in order: a leading `0`, XCROSSES, YCROSSES, CPITCH, CHALF, FEC_ORDER, BORDER, TEXT_HEIGHT. This design treats the leading `0` as the format version. The label is rendered from a bitmap font in `font.h` (13 pixels per glyph, 24 high).

**Bit placement.** `seq2xy` in `common.c` maps a channel bit number to a pixel, walking alternating narrow strips (rows that contain crosses) and wide strips (rows that do not).

**Error correction.** Payload is split into 12-bit words, each expanded to a 24-bit Golay codeword (`golay.c` builds the 4096-entry table from a dodecahedron construction). `FEC_ORDER` 2 to 5 select Hamming codes instead. Codewords are interleaved across the page: bit `b` of symbol `s` goes to channel position `s + b*FEC_SYMS`, most significant bit first. Bytes are fed most significant bit first. The last page is flushed with zero bits.

**Decoder pipeline** (`unoptar.c`, per page): read PNG, histogram and black/white cut level, flood-fill dirt out of the white border, find the four corners, locate every cross by correlation search, min/max filter then blur, sample each data pixel with interpolation and an unsharp mask, de-interleave, Golay or Hamming decode, emit bytes. Seven hand-tuned "magic constants" control it. It writes decoded bytes to stdout, diagnostics to stderr, and a debug image per page.

**Quirks the port must know about:**

- `unoptar` parses the format argument but ignores every field except text height. Everything else is compiled in.
- The original file length is not stored. Output is padded with zeros to a whole page.
- Both tools stop at 9,999 pages.
- `optar` writes `<base>_NNNN.pgm`; `unoptar` reads `<base>_NNNN.png` until the first missing number.

## Design

### Package layout

```
pyproject.toml
src/optar/
    __init__.py        public API re-exports, __version__
    format.py          PageFormat: the format as data
    fec.py             Golay and Hamming encode/decode
    layout.py          channel bit number <-> pixel coordinates
    font.py            label rendering; glyph data loaded from a package data file
    encoder.py         bytes -> page images
    decoder/           scan image -> bytes, one module per pipeline stage
    imageio.py         PGM and PNG reading and writing
    cli.py             argument parsing and console output only
tests/
    unit/  golden/  oracle/  fixtures/
```

Module boundaries are the builder's to adjust; the rules that matter are below.

### The format as data

`PageFormat` is an immutable object holding version, xcrosses, ycrosses, cpitch, chalf, fec_order, border, text_height and text_width. Every size the C header derives with macros (`WIDTH`, `TOTALBITS`, `FEC_SYMS`, `NETBITS`, and so on) is a computed property.

- `PageFormat.parse("0-65-93-24-3-1-2-24")` and `fmt.to_string()` round-trip the label's format string.
- Named presets: `A4` (65 x 93) and `LETTER` (67 x 87), both from the comments in `optar.h`.
- An unknown version, or a field combination that cannot work, raises a clear error. This version check is the extension point for project 2: a new format becomes a new version with its own codec, and version 0 keeps working.
- No module other than `format.py` contains a format number. Encoder, layout, FEC and decoder all take a `PageFormat`.

Unlike the C decoder, the Python decoder uses every field of the format it is given.

### Library API

Shape, not final signatures:

- `encode(data, fmt, label) -> iterator of pages`. Each page is a numpy `uint8` array plus its page number. Accepts bytes or a binary stream, so large files do not have to be held in memory twice.
- `decode_page(image, fmt, options) -> PageResult`. Returns that page's payload as a bit array of exactly `NETBITS` bits, plus statistics (codewords read, bits corrected, uncorrectable codewords), and optionally the debug image. A page is decodable on its own.
- `decode(images, fmt, options) -> bytes` concatenates the pages' bits in order and packs them into bytes, most significant bit first.

Pages carry bits, not bytes (my call). A page does not always hold a whole number of bytes: on A4, Hamming orders 2, 4 and 5 give 799,092, 2,197,503 and 2,597,036 net bits per page. C handles this by carrying a partial byte from one page to the next in static state. The Python library keeps each page independent at the bit level and does the byte packing in one place, which gives the same output and leaves room for per-page recovery in project 2. The encoder is the mirror image: one continuous bit stream cut into pages of `NETBITS` bits.
- `DecodeOptions` holds the seven magic constants, defaulting to the C values.

The library raises exceptions and reports progress through return values or an optional callback. It never prints or exits.

### Command line

One program with subcommands (my call: one executable is simpler to bundle and to grow than two):

```
optar encode INPUT [-o BASE] [--paper A4|letter] [--to pdf|png|pgm] [--label TEXT]
                   [--format FORMAT_STRING]
optar decode BASE [-o OUTPUT] [--paper A4|letter] [--debug-images]
                  [--format FORMAT_STRING]
optar --version
```

- `encode` writes `BASE.pdf` by default (my call: the print-ready file is what most people want). `--to png` writes `BASE_0001.png`, ...; `--to pgm` writes `BASE_0001.pgm`, ... exactly as C does. `BASE` defaults to `optar_out`.
- `decode` reads `BASE_0001.png`, ... until the first missing number, and writes to `OUTPUT` or stdout. Stdout is put in binary mode on Windows.
- `--paper A4|letter` is the user-facing choice of paper, on both commands (owner's decision). It defaults to A4 and selects everything that depends on the paper: the cross grid (65 x 93 for A4, 67 x 87 for Letter), the PDF page size and the image placement. The label printed on each page shows the resulting format string, so a Letter printout identifies itself.
- `--format FORMAT_STRING` is the advanced override for a custom grid or error-correction mode. Combined with `--paper`, it uses that paper's page size and placement.
- If decoding fails to find the page corners or the cross grid, the error message suggests checking `--paper`.
- Diagnostics go to stderr. Debug images are written only with `--debug-images` (C always writes them; my call to make that opt-in).
- Exit status is non-zero if any codeword was uncorrectable, with the count on stderr. The decoded data is still written.

### Print-ready output

The owner wants files that can be sent straight to a printer, PDF preferred.

**What "print-ready" means here.** `pgm2ps` places the page image so that one data pixel is exactly 3 x 3 printer dots at 600 dpi, which is 200 pixels per inch. For A4 the 1546 x 2242 image becomes 556.56 x 807.12 points, at offset 19.22, 17.44 on a 595.28 x 841.89 point page. The unfinished `archive_pdf` Makefile target failed on exactly this: the image was cut off and the PDF had no margins.

**PDF (default).** One PDF for the whole file, one page per optar page. Requirements:

- The PDF page is the real paper size (A4 or US Letter), with the image placed at the size and offset above. For Letter the `pgm2ps` comment gives 573.84 x 755.28 points at 19.08, 18.36.
- The image is stored losslessly as 1 bit per pixel at its native resolution, with interpolation switched off, so the printer driver does the 3x scaling and no viewer smooths the pixels.
- No JPEG compression anywhere. JPEG blurs the pixel edges the decoder depends on, which is why JPEG is not offered as an output format.

How the PDF is produced is the builder's choice, with one constraint: Pillow's own PDF export sizes the page to the image and can pick a lossy encoding for grayscale, so it is not acceptable as-is. A small hand-written PDF writer using only the standard library is the expected route.

**PNG pages.** `BASE_0001.png`, ...: the same 1-bit image with its resolution recorded as 200 pixels per inch, for people who print from an image viewer. These have no page margins of their own, so the PDF is the recommended path.

**PGM pages.** The C-compatible output, kept for the oracle tests and for anyone still using `pgm2ps`.

**Paper size.** The user picks A4 or US Letter with `--paper` (default A4). Each paper is a preset carrying its cross grid, page size and image placement. A custom `--format` string is placed on the selected paper, and the encoder refuses a format whose image does not fit that paper at 200 pixels per inch.

**Printing note.** The page must be printed at actual size (100%, no "fit to page"). The README says so, and `encode` prints a one-line reminder on stderr.

### Decoder fidelity and speed

The decoder mirrors the C pipeline stage by stage, with the same constants and the same order of operations, vectorised with numpy instead of per-pixel loops.

How closely it tracks C (my call): it matches C in outcome, not in arithmetic. C mixes `float` and `double`, sums correlations sequentially and breaks ties by loop order; natural numpy code will round differently, and the port does not emulate that. The requirement is that on every image in the test suite the Python decoder returns the same bytes as the C decoder. The degraded test images are chosen with margin, meaning C decodes them with no codeword needing its full three-bit correction, so a rounding difference cannot decide the result. If the two decoders disagree on an image that has that margin, it is a bug in the port; if they disagree on an image without it, the image is replaced.

When a codeword is uncorrectable, the Python decoder emits its 12 raw data bits, as C does.

Speed targets on an ordinary laptop (my call): encode a page in under 5 seconds; decode a 600 dpi A4 scan (about 4960 x 7016 pixels) in under 60 seconds. If the correlation search or sampling cannot be vectorised to meet this, say so and stop rather than adding a compiled dependency.

### Error-correction scope

Golay (`FEC_ORDER` 1) is required. Hamming orders 2 to 5 are ported only where the C tools, built with that order, round-trip their own output; if a C variant is broken, that order is rejected by `PageFormat` with a clear error and noted in the README. (My call: a runtime format that accepts a field must honour it or refuse it.)

The design reviewer built the C tools with each of orders 2 to 5 and reports that all four round-trip at scale 1, single-page and multi-page. So expect to port all four; the oracle tests confirm it.

## Testing

Test-first throughout: each behaviour gets a failing test before its code. Three tiers.

### 1. Unit tests (plain Python, run everywhere)

- **Format:** parse/format round trip, derived sizes for A4 equal the known C values (1546 x 2242 page), bad input rejected.
- **Golay:** 4096 codewords, weights only 0/8/12/16/24, minimum distance 8, every pattern of up to 3 bit errors in a codeword is corrected, 4 errors are detected.
- **Layout:** every channel bit maps to a distinct pixel that is inside the data area and not on a cross; the count equals `TOTALBITS`; out-of-range is rejected.
- **Encoder:** border, crosses and label land where the format says; page count for a given input length.
- **Decoder stages:** each stage tested on small synthetic arrays.
- **Round trip:** encode, then decode the clean pages, at scan scales 1, 2 and 3.
- **Paper option:** `--paper A4` and `--paper letter` each give the right format string, page size and placement; an unknown paper is rejected; a full encode/decode round trip passes for both.
- **PDF output:** the page box equals the paper size; the image is placed at the expected size and offset to within 0.01 point; the embedded image data, decompressed, equals the encoder's page bit for bit; a multi-page input gives one PDF with the right number of pages.
- **PNG output:** pixel data equals the encoder's page; the recorded resolution is 200 pixels per inch.
- **Degraded round trip:** the same after synthetic damage: a small rotation, blur, noise, speckles in the border, a few flipped data pixels. Parameters are seeded so runs are repeatable.

### 2. Golden tests (plain Python, run everywhere)

Small fixtures generated once from the C tools and committed, so compatibility is checked without a compiler:

- SHA-256 of the C Golay table.
- SHA-256 of each C-encoded page for a set of seeded inputs: empty file, one byte, exactly one page of payload, one page plus one byte, a multi-page file, and a custom label.
- A sample of `seq2xy` outputs.

A script in `tests/` regenerates the fixtures from the C build; the fixtures record the C commit they came from.

### 3. Oracle tests (need a C compiler and libpng; skipped automatically otherwise)

A test harness builds the C tools in a temporary copy of the sources, optionally with a different format patched into `optar.h`, and then checks live:

- Python and C encoders produce byte-identical pages for random inputs.
- The C decoder reads Python pages; the Python decoder reads C pages.
- For the same degraded image, wherever the C decoder recovers the data, the Python decoder does too.
- The above for A4 and US Letter, and for each Hamming order that C supports.
- Where Ghostscript is installed: render the PDF at 600 dpi, check the raster is the full paper size, and decode it back to the original data. This is the closest thing to a print-and-scan the suite has. It is skipped automatically where Ghostscript is missing, and runs in CI on Ubuntu.

### Real scans

`tests/scans/` is a slot for real scanned pages with their original files. Any pair placed there is picked up automatically as a decoder test. None exist today.

## Packaging and CI

- **Build:** PyInstaller, one-file mode, entry point `optar.cli`. Output name `optar` (`optar.exe` on Windows).
- **`ci.yml`** (push and pull request):
  - lint with ruff;
  - unit and golden tests on Ubuntu, macOS and Windows, on the oldest and newest supported Python;
  - oracle tests on Ubuntu with `libpng-dev` and Ghostscript installed.
- **`release.yml`** (tag `v*`): on Ubuntu, macOS and Windows runners, build the executable, run a round trip with the built executable as a smoke test, and attach the three files to a GitHub Release named after the tag.
- The version comes from one place and matches the tag.
- `.travis.yml` is deleted.

## Order of work

1. Project skeleton, pytest, ruff, the oracle harness.
2. `format`, `fec`, `layout`.
3. Encoder, to byte identity with C.
4. Image reading and writing, including the print-ready PDF and PNG output.
5. Decoder, stage by stage, then the cross-decoding and degraded tests.
6. Command line.
7. PyInstaller build and the two workflows.
8. Update `README.md` and `CLAUDE.md` for the new layout and commands.

Each step ends with all tests green.

## Risks

- **Decoder on real paper is unproven.** Synthetic degradation is not a scanner. Until a real scan is added to `tests/scans/`, "the Python decoder reads real printouts" is an expectation, not a tested fact. The C decoder remains available as a fallback.
- **Decoder speed.** The C code samples about 3.2 million data pixels per page with per-pixel interpolation. The target above may need care to reach.
- **Executable size.** Bundling numpy gives a file of tens of megabytes, against about 100 KB for each C binary.

## Left to the builder

- Exact module split, function names and signatures.
- Build backend and how the single version source is implemented.
- How the font bitmap is stored as package data.
- Which synthetic degradations and strengths make the degraded tests meaningful but stable.
- Ruff rule selection.
- Whether the Claude Code edit hook in `.claude/` should also lint Python.

## Calls made by the author, not the owner

These were decided while writing and are open to correction:

- numpy and Pillow as the only runtime dependencies; Python 3.10+.
- One executable with `encode`/`decode` subcommands instead of two programs.
- Debug images are opt-in.
- The Python decoder honours the whole format string.
- Hamming orders are ported only where C proves them working.
- `encode` writes a PDF by default; PGM and PNG are options.
- No JPEG output, because it is lossy.
- The PDF is written by a small hand-rolled writer, not by Pillow's PDF export.
- C sources stay at the repo root.
- Speed targets: 5 seconds to encode a page, 60 seconds to decode one.
- The leading `0` of the format string is treated as the format version.
- Pages carry bits, not bytes; byte packing happens once, across pages.
- The decoder matches C in decoded output on the test images, not in floating-point arithmetic.
- Uncorrectable codewords emit their raw data bits, as in C.
