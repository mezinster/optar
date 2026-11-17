# Format specification and the end of the C comparison: design

Date: 2026-11-17. Status: approved and built.

## Intent

optar is a Python product now. Its definition is still the C program: the tests
build the C tools from `lega-c` and compare against them on every pull request,
and the project notes describe the Python code as a port. The owner's words:
"If you're missing specification - create one. I believe we have to end the C
product era", and "Keep them in lega-c as history".

After this work the format is defined by a written specification and by frozen
test vectors. Nothing in the tests or in CI needs a C compiler. The C sources
stay in `lega-c`, untouched, as history.

## Goals

1. A specification written for implementers: someone who has never seen this
   repository can write an encoder whose pages this project reads, and a
   decoder for this project's pages, from the document and the vectors alone.
2. Conformance vectors, frozen in the repository, that pin everything the live
   C comparison pins today.
3. The C comparison, its build harness and the C-only tooling are removed.
4. The specification cannot drift from the code unnoticed.

## Non-goals

- No change to the format, to any page the tools print, or to what they read.
- No retuning of the decoder.
- The decoding *algorithm* is not made normative. A reader may find and sample
  a page any way it likes; the specification says what a page is.
- `lega-c` is not removed, edited or reformatted.

## Anti-goals

- A specification that restates the code loosely. Every number in it must be
  checked against `format.py` by a test, or it is not in the document.
- Losing coverage silently. Each C comparison that is deleted must have a
  vector that fails for the same mistake, shown before the deletion.

## Approaches considered

**A. Freeze the C outputs as vectors, then remove the live comparison (chosen).**
One last run of the C tools records their outputs for a fixed set of inputs.
From then on the Python tests compare against the recorded files. The format
is pinned as firmly as today, the checks run in seconds, and no compiler,
libpng headers or build harness are needed. Cost: the vectors must be chosen
well once, because they cannot be regenerated without reviving the C build.

**B. Keep the C comparison as an optional, manually started job.** Nothing is
lost, but the harness (`tests/cbuild.py`, header overrides, libpng handling)
must be kept working for a job nobody runs, and the C program remains the
definition in practice. This is the era the owner asked to end.

**C. Remove the comparison and rely on the existing unit tests.** Cheapest, but
compatibility with pages printed by the C tool and by 0.1.0 and 0.2.0 would
rest on eight recorded pages and nothing for the decoder.

The owner handed over the how ("we have to go"); A is the author's choice.

## What is built

### 1. The specification: `docs/format.md`

One document, normative language ("must", "may") kept to statements a test can
check. Parts:

1. **Terms and conventions.** Bit and byte order (most significant bit first),
   black is 1, coordinates, units (page pixel, printer dot, point).
2. **The page (version 0).** Page size from the cross counts; border; cross
   pattern and pitch; the data area and which pixels are data; the order in
   which data bits fill the page (the interleave over 24 bands, given as a
   formula and as a table of vectors); the Golay (24,12) code, by its
   generator and with the full table published as a vector; how a byte stream
   becomes pages, including the partly filled last page; the label band, the
   font strip, the label line and its truncation; the format string.
3. **The document tag (0.2.0 printouts).** The tag in the label, its check
   code, and when a reader may accept it.
4. **Self-identifying documents (version 1).** The header and its five copies;
   Reed-Solomon over GF(256): field polynomial, generator roots, codeword
   layout; where each codeword byte lies (the spread); the data region: file,
   name record, padding stream; the fewest-pages rule; the limits.
5. **Printing.** The five dot sizes, the ten layouts (grid, offsets, margins,
   bytes per page), the PDF placement, the fixed-size label strip.
6. **What a reader must do.** A valid tag wins over a header; a header is
   untrusted and what it may claim; only the fingerprint verifies a file;
   padding is never read; 0.3.0 zero padding is valid.
7. **Reference decoder (informative).** How this project finds and samples a
   page, including the tolerance for a gap in the frame, stated as a
   description and not as a requirement.
8. **History.** The C program, its commit, what in this format comes from it
   and its quirks that the format keeps (for example the double use of one
   corner in the pixel-size estimate is decoder behaviour and is *not* format).

### 2. Conformance vectors: `tests/vectors/`

Small files, JSON plus a few PNG pages, each with a one-line statement of what
it pins. Budget: under 2 MB in total. Bulky results are stored as SHA-256
hashes; a handful of whole pages and scans are stored as images so that a
failure can be looked at.

| Vector set | Pins | Source |
|---|---|---|
| Golay table | all 4096 codewords | C (already recorded) |
| Bit placement | page position of data bit n, every layout and three custom formats | C |
| Encoder pages | whole pages for fixed inputs: empty file, one byte, exactly one page, one bit over, multi-page; A4 and Letter; custom formats | C |
| Label | label band pixels for fixed texts, including truncation and non-ASCII | C |
| Decoder results | decoded bytes and per-page statistics for fixed clean and degraded scans | C |
| Decoder internals | cross positions and sampled bits for fixed scans | C |
| Reed-Solomon | codewords for fixed messages at parity 32 and 64; repairs of fixed damage | Python, cross-checked once against an independent implementation |
| Container | streams for fixed files at each parity and layout; header bytes; spread positions; padding stream | Python |
| Tag | tags and check codes for fixed files | Python |

Vectors recorded from C carry the C commit they came from.

Decoder inputs (author's call). The scans are made once by the project's own
`fake_scan` helper, with the eight cases of `tests/helpers.DEGRADED` (clean,
rotated, blurred, noisy, specks, flipped bits, combined), and committed as PNG
files; they are not regenerated, so that a change in a random number library
cannot change the inputs. To stay within the budget the degraded scans are of
small custom page formats, and the full A4 and Letter pages are stored as
clean two-level scans, which compress well. (As built: the full-size and clean cases are made again by the tests from a recipe that uses no randomness, with the page pinned by its hash, and only the degraded scans are stored; `tests/vectors/README.md` explains why.) No real scan is used: the owner's
scans never enter the repository.

Independence (author's call). The Reed-Solomon vectors are checked once
against a third-party implementation by a throwaway script that is not
committed and adds no dependency; `tests/vectors/README.md` names the library
and version used. The container and tag vectors have no outside reference:
they pin what 0.3.0 and 0.2.0 print, and the specification says so.

`tests/golden/` (eight pages, some bit positions and the Golay hash) is folded
into `tests/vectors/`.

### 3. Tests against the vectors

`tests/vectors/test_vectors.py` runs every vector against the Python code in
the default suite, with no markers and no compiler. A second test reads the
tables in `docs/format.md` (layouts, dot sizes, header fields, constants) and
compares them with `format.py`, so the document fails CI when it drifts.

### 4. Removal

- `tests/oracle/` except the Ghostscript rendering test, which moves to
  `tests/unit/` and keeps its `gs` marker. `test_harness.py` goes with the
  harness; `seq2xy_dump.c` moves to `lega-c/record_vectors/`.
- `tests/cbuild.py`, `tests/golden/make_fixtures.py`, the `oracle` marker, the
  `c_build` fixtures, `OPTAR_TEST_CFLAGS` / `OPTAR_TEST_LDFLAGS`.
- The CI job installs Ghostscript only and runs the `gs` tests; it is renamed.
- The `/roundtrip` skill and the C syntax-check hook (both tracked under
  `.claude/`, with the hook's entry in `.claude/settings.json`): they exist to
  edit C, which no longer happens.
- `tools/extract_font.py` stays (it documents where the font came from) but
  reads `lega-c/font.h` only on request.
- `.superpowers/libpng` (local headers for the C build) is git-ignored local
  state: it is no longer needed and is deleted only with the owner's
  housekeeping go-ahead.

The recording script that produced the C vectors is kept under
`lega-c/record_vectors/` with a note that it is history and is not run.

### 5. Documents

- `README.md`: the format is defined by `docs/format.md`; the C program is its
  origin. The sections that describe building and using the C tools move under
  a "History" heading and point at `lega-c`.
- `CLAUDE.md`: "the C sources are the test oracle" becomes "the specification
  and the vectors define the format; `lega-c` is history and is never edited".
  "The decoder mirrors the C algorithm" becomes "decoder results are pinned by
  the vectors; change them only with real scans, and then deliberately".
  The sections on the C build and on keeping the C encoder and decoder in sync
  shrink to a pointer.

## Order of work

1. Record the vectors from C while the harness still exists, and add the tests
   that read them. The live comparisons still run.
2. For each live comparison, break the Python code the way that comparison
   would catch and show that a vector test fails too. The breaks are a
   hand-picked list, at least one for each comparison test function, made and
   reverted by hand. The list and its results are kept in
   `tests/vectors/README.md` and repeated in the pull request.
3. Remove the comparisons, the harness and the C tooling; change CI.
4. Write the specification, with the drift test, against the code.
5. Update `README.md` and `CLAUDE.md`.

Steps 1 to 3 are one pull request; the specification (steps 4 and 5) is a
second one, stacked on the first.

## Left to the builder

- The exact inputs for each vector set, within the budget.
- The file layout inside `tests/vectors/`.
- How the specification's tables are marked so that the drift test finds them.

## Risks

- **A vector set that is too thin.** Mitigated by step 2: no comparison is
  deleted until a vector fails for the same mistake.
- **The specification claims more than the tests check.** Mitigated by the
  rule that normative statements are checkable, and by the drift test.
- **Decoder behaviour frozen that should change.** The vectors pin today's
  results on fixed scans; a deliberate decoder change updates them in the same
  pull request, with real scans as the reason.
