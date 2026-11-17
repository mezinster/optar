# Format specification and end of the C comparison: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the live comparison with the C tools by frozen conformance vectors, remove everything that needs a C compiler, and write a specification of the format for implementers.

**Architecture:** A recording script (kept as history under `lega-c/record_vectors/`) runs the C tools one last time and writes vector files to `tests/vectors/`. Plain pytest tests in the default suite compare the Python code with those files. A second set of vectors, made by the Python code, pins the Reed-Solomon code, the container and the tag. `docs/format.md` is the specification; a test compares its tables with `src/optar/format.py`.

**Tech Stack:** Python 3.12+, numpy, Pillow, pytest. The C tools are built once more through the existing `tests/cbuild.py`.

**Spec:** `docs/superpowers/specs/2026-11-17-format-spec-design.md`

## Global Constraints

- No change to the format, to any page the tools print, or to what they read. No file under `src/` changes except where a task says so.
- No retuning of the decoder.
- Nothing under `lega-c/` is edited: files may only be added under `lega-c/record_vectors/`.
- `tests/vectors/` stays under 2 MB in total (`du -sb tests/vectors`).
- The owner's real scans are never used, copied or referenced.
- Vector tests need no compiler and carry no `oracle` or `gs` marker; only the full-size decode cases other than plain A4 are marked `slow`.
- Vectors recorded from C carry the C commit `9c8379c…` as recorded today by `tests/golden/make_fixtures.py` (`c_commit`).
- Format numbers live only in `src/optar/format.py`.
- Commit subjects are capitalised, third-person present, no prefix, no attribution lines.
- Every vector file is JSON written with `json.dumps(..., sort_keys=True, indent=1) + "\n"`, or a PNG.
- Bulky results are stored as SHA-256 hex digests of exactly defined bytes; the definition is written in `tests/vectors/README.md`.

## Review Focus

1. **A numpy or Pillow upgrade changes a generated scan.** Every decoder vector whose scan involves random numbers, rotation or blur must read a stored PNG; only scans made without them (`fake_scan(page, scale=1)` and `scale=3` with no other argument) may be regenerated. Test: `test_stored_scans_are_the_only_random_inputs` (Task 2).
2. **A vector that pins nothing.** A vector test that passes when the Python result is replaced by zeros is worthless. Task 4's break list covers every comparison; each break must make a vector test fail.
3. **The C tool cannot handle a small format.** If C `unoptar` fails or decodes wrongly on the small format chosen for stored scans, pick the next larger one; never record a wrong C result. The recorder asserts that C's output starts with the input data (Task 2).
4. **The specification states a number that is not in the code.** `test_spec_tables_match_the_code` (Task 6) parses every marked table.
5. **Collection breaks on a machine without a compiler.** After Task 5, `pytest --co -q` must import nothing from `lega-c` and nothing named `cbuild`. Test: `test_no_test_imports_the_c_harness` (Task 5).

## File structure

- `tests/vectors/README.md`: what each file pins, how each digest is defined, the break list (Task 4), the outside Reed-Solomon check (Task 3).
- `tests/vectors/c/*.json`, `tests/vectors/c/scans/*.png`: recorded from C.
- `tests/vectors/py/*.json`: made by the Python code.
- `tests/vectors/__init__.py`, `tests/vectors/load.py`: `load(name) -> dict`, `digest(data: bytes) -> str`, `array_digest(a: np.ndarray) -> str`.
- `tests/vectors/test_vectors_c.py`, `tests/vectors/test_vectors_py.py`.
- `lega-c/record_vectors/`: `record.py`, `cbuild.py`, `seq2xy_dump.c`, `README.md` (history; not run, not imported by tests).
- `docs/format.md`, `tests/unit/test_spec.py`.

Lanes: Task 1 first. Then Tasks 2, 3 and 6 are file-disjoint and run in parallel. Then Task 4, Task 5, Task 7 in order.

---

### Task 1: Vector loader and the existing fixtures

**Files:**
- Create: `tests/vectors/__init__.py`, `tests/vectors/load.py`, `tests/vectors/README.md`, `tests/vectors/c/golay.json`, `tests/vectors/c/bit_placement.json`, `tests/vectors/c/encoder_pages.json`, `tests/vectors/test_vectors_c.py`
- Delete: `tests/golden/fixtures.json`, `tests/golden/test_golden.py` (keep `make_fixtures.py` until Task 2 replaces it)

**Interfaces:**
- Produces: `tests.vectors.load.load(name: str) -> dict` (name relative to `tests/vectors`, without `.json`); `digest(data: bytes) -> str` (SHA-256 hex); `array_digest(a: np.ndarray) -> str` = `digest(np.ascontiguousarray(a).tobytes())` after asserting the dtype the caller names: `array_digest(a, dtype)`.
- Every vector file has top-level keys `"pins"` (one sentence), `"source"` (`"c"` or `"python"`), `"c_commit"` when the source is C, and `"cases"`.

- [ ] **Step 1:** Write `load.py` and the three JSON files by converting `tests/golden/fixtures.json` (`golay_sha256` → `golay.json`; `seq2xy` → `bit_placement.json`; `pages` → `encoder_pages.json`), keeping every value.
- [ ] **Step 2:** Move the three tests of `test_golden.py` into `test_vectors_c.py`, reading the new files: `test_golay_table`, `test_bit_placement`, `test_encoder_pages`.
- [ ] **Step 3:** `README.md`: one section per file with what it pins and how its digests are defined.
- [ ] **Step 4:** Run `.venv/bin/pytest -q tests/vectors`. Expected: same number of passing cases as `tests/golden/test_golden.py` had. `.venv/bin/ruff check .` clean.
- [ ] **Step 5:** Commit "Moves the recorded C fixtures to tests/vectors".

### Task 2: Vectors recorded from C

**Files:**
- Create: `lega-c/record_vectors/record.py` (may import `tests.cbuild` for now), `tests/vectors/c/decoder.json`, `tests/vectors/c/decoder_internals.json`, `tests/vectors/c/container_pages.json`, `tests/vectors/c/label.json`, `tests/vectors/c/scans/*.png`
- Modify: `tests/vectors/c/bit_placement.json`, `tests/vectors/c/encoder_pages.json`, `tests/vectors/test_vectors_c.py`, `tests/vectors/README.md`
- Delete: `tests/golden/` (the rest of it)

**Interfaces:**
- Consumes: `tests.vectors.load`; `tests.cbuild.build_c_tools`, `build_patched_unoptar`, `build_seq2xy_dump`; `tests.helpers.fake_scan`, `save_scan`, `seeded_bytes`, `DEGRADED`.
- Produces: the vector files above. Run with `.venv/bin/python lega-c/record_vectors/record.py` from the repository root (needs a C compiler and libpng headers; locally `OPTAR_TEST_CFLAGS=-I.superpowers/libpng/include OPTAR_TEST_LDFLAGS=-L.superpowers/libpng/lib`, see `CLAUDE.md`).

What to record, each mirroring a comparison in `tests/oracle/` (read those files first; the inputs below are theirs):

| Vector file | Cases | Recorded from C |
|---|---|---|
| `encoder_pages.json` | formats a4, letter, a4 with `fec_order` 2, 3, 4, 5; inputs `seeded_bytes(seed, size)` for seed, size in `enumerate([0, 1, 777, 2 * net_bytes + 5])` | SHA-256 of each page's PGM bytes (`optar.imageio.pgm_bytes`) |
| `container_pages.json` | a4-large and letter-medium, stream `wrap(seeded_bytes(31, 100_000), "name.bin", fmt, 32)`, label `"doc"` | SHA-256 of each C page's PGM bytes; SHA-256 of C `unoptar`'s output for the Python pages scanned with `fake_scan(page, scale=1)` |
| `bit_placement.json` | all ten layouts of `optar.format.LAYOUTS` plus formats 4x4, 7x5 and 65x93 with `fec_order` 3 | `(seq, x, y)` for the 2000 sequence numbers `make_fixtures.seq_choices` picks |
| `label.json` | page 1 of `encode(b"x", A4, text)` for texts `""`, `"my label"`, a 200-character text, `"naïve ☃"` | SHA-256 of the label band rows of the C page (C called with the same label) |
| `decoder.json`, full size | `test_c_decodes_python_pages` and `test_python_decodes_c_pages` inputs for a4, letter, fec2..5 (scans `fake_scan(page, scale=1)`); a4 at `fake_scan(page, scale=3)` | SHA-256 of C `unoptar`'s output; for the C-made pages, SHA-256 of each page |
| `decoder.json`, stored scans | a small format (start with `PageFormat(6, 8)`; see Review Focus 3): the eight `DEGRADED` cases with `seed=1`; noise 60 `seed=2` for `fec_order` 1 (default), 2 and 5; one `scale=6, rotate=0.2, blur=1.5, noise=8, seed=1` | the scan as `scans/<case>.png` (written with `save_scan`); SHA-256 of C `unoptar`'s output; the count of uncorrectable symbols is *not* recorded (C does not print it) |
| `decoder_internals.json` | the small format, `dict(scale=3)` regenerated and `dict(scale=3, margin=120, rotate=0.4, blur=1.0, noise=8.0, seed=3)` stored | cross positions and cut levels (the instrumented build of `test_crosses_oracle.py`), as lists of C hex floats; sampled bits (the instrumented build of `test_sample_oracle.py`), as SHA-256 of the uint8 bit array in the order that test compares |

- [ ] **Step 1: Write the failing tests** in `test_vectors_c.py`, one per vector file, each running the Python code on the recorded input and comparing with the recorded value: `test_encoder_pages`, `test_container_pages`, `test_c_reads_container_pages` (Python `decode` of the same scans gives bytes with the recorded digest), `test_bit_placement`, `test_label_band`, `test_decodes_like_c_full_size`, `test_decodes_like_c_stored_scans`, `test_crosses_like_c`, `test_sampled_bits_like_c`. Plus `test_stored_scans_are_the_only_random_inputs`: every case in `decoder.json` and `decoder_internals.json` either names a file under `scans/` or has a recipe whose keyword arguments are a subset of `{"scale"}` with scale 1 or 3. Plus `test_vectors_are_small`: total size of `tests/vectors` under 2,000,000 bytes.
- [ ] **Step 2:** Run them. Expected: FAIL, files missing.
- [ ] **Step 3: Write `record.py`** as one function per vector file and a `main()` that writes all of them. It asserts, before writing a decoder case, that C's output starts with the input data for the cases the oracle tests assert that for (all but the noise-60 cases).
- [ ] **Step 4:** Run the recorder; run `.venv/bin/pytest -q tests/vectors`. Expected: PASS. Run the recorder a second time: `git status` shows no change (the output is deterministic).
- [ ] **Step 5:** Extend `tests/vectors/README.md` with each new file and digest definition. Delete `tests/golden/`.
- [ ] **Step 6:** `.venv/bin/ruff check .`; `.venv/bin/pytest -q -m oracle` still passes (the live comparisons stay until Task 5). Commit "Records the C tools' results as conformance vectors".

### Task 3: Vectors made by the Python code

**Files:**
- Create: `tests/vectors/py/reed_solomon.json`, `tests/vectors/py/container.json`, `tests/vectors/py/tag.json`, `tests/vectors/py/make.py`, `tests/vectors/test_vectors_py.py`
- Modify: `tests/vectors/README.md` (append only; Task 2 edits the same file, so add a section headed "Vectors made by the Python code" at the end)

**Interfaces:**
- Consumes: `tests.vectors.load`; `optar.rs.RSCode`; `optar.container` (`wrap`, `unwrap`, `plan`, `positions`, `padding`, `Header`, `read_header`, `PagePayload`); `optar.tag` (`make_tag`, `tagged_label`, `split_label`).
- Produces: `python -m tests.vectors.py.make` rewrites the three files; they pin today's behaviour (0.3.1).

Cases:

- `reed_solomon.json`: for parity 32 and 64, messages of `255 - parity` bytes: all zeros, all 0xFF, bytes 0..k-1, `seeded_bytes(1, k)`, `seeded_bytes(2, k)`; the parity bytes in hex. Repairs: `seeded_bytes(3, k)` encoded, then damaged at fixed positions (errors only at the limit `parity // 2`; erasures only at the limit `parity`; a mix `e` errors and `parity - 2e` erasures for `e = 5`; one error beyond the limit, expected to fail), with the expected outcome.
- `container.json`: header bytes in hex for `Header(page=3, total=7, size=552508, fingerprint=bytes(range(16)), parity=64)`; `padding(0, 100)` in hex; for each layout and each parity, a file of `seeded_bytes(41, 1.5 pages of data)` named `"vector.bin"`: page count, SHA-256 of the stream, and `positions(plan)` for codewords 0, 1 and the last as lists.
- `tag.json`: `make_tag` for the empty file, `b"x"`, `seeded_bytes(5, 300_000)`: the tag's fields; `tagged_label(tag, "name.tar", page, total)` for pages 1 and 2.

- [ ] **Step 1: Write the failing tests** `test_reed_solomon_parity`, `test_reed_solomon_repairs`, `test_header_bytes`, `test_padding_stream`, `test_container_streams`, `test_spread_positions`, `test_tags`, each recomputing from the inputs stored in the file.
- [ ] **Step 2:** Run. Expected: FAIL, files missing.
- [ ] **Step 3:** Write `make.py`; run it; run the tests. Expected: PASS.
- [ ] **Step 4: Outside check.** In a throwaway virtual environment outside the repository, install the `reedsolo` package and compare its parity bytes with `reed_solomon.json` for every message (field polynomial 0x11D, first consecutive root and generator as `optar/rs.py` uses them; read `rs.py` for both). Do not commit the script or add a dependency. Record in `README.md`: the library, its version, the parameters used and the result. If the parities differ, find out which convention differs and say so in `README.md` instead of claiming agreement.
- [ ] **Step 5:** `.venv/bin/ruff check .`. Commit "Adds vectors for the Reed-Solomon code, the container and the tag".

### Task 4: Show that the vectors catch what the comparisons caught

**Files:**
- Modify: `tests/vectors/README.md` (section "What was checked before the C comparison was removed")

**Interfaces:**
- Consumes: Tasks 2 and 3.

- [ ] **Step 1:** For each test function in `tests/oracle/test_encoder_oracle.py`, `test_decoder_oracle.py`, `test_crosses_oracle.py`, `test_sample_oracle.py` and `test_container_oracle.py`, choose one break of the Python code that the function would catch (examples: swap two band offsets in `layout.py`; flip the bit order in `encoder.py`; change one Golay generator row in `fec.py`; move the label one column in `font.py`; change `sync_white_cut` in `options.py`; drop the last min/max pass in the decoder; change a rounding in `sample.py`; change `SPREAD_STEP`).
- [ ] **Step 2:** For each break: apply it, run `.venv/bin/pytest -q tests/vectors -x`, note the failing test, revert with `git checkout -- src`. A break that no vector test catches is a gap: add a vector for it (Task 2's recorder) and repeat.
- [ ] **Step 3:** Write the table (comparison, break, failing vector test) into `README.md`. `git status` must show only that file changed.
- [ ] **Step 4:** Commit "Lists what the vectors were shown to catch".

### Task 5: Remove the C comparison

**Files:**
- Move: `tests/cbuild.py` → `lega-c/record_vectors/cbuild.py`; `tests/oracle/seq2xy_dump.c` → `lega-c/record_vectors/seq2xy_dump.c`; `tests/oracle/test_pdf_render.py` → `tests/unit/test_pdf_render.py`
- Create: `lega-c/record_vectors/README.md` (what this folder is, the commit it was last run at, that it is not run)
- Delete: the rest of `tests/oracle/`, `tests/unit/test_cbuild.py`, `.claude/skills/roundtrip/`, `.claude/hooks/syntax-check.sh`
- Modify: `tests/conftest.py` (drop `c_build`), `pyproject.toml` (drop the `oracle` marker), `.github/workflows/ci.yml`, `.claude/settings.json` (drop the hook entry; keep the ruff hook), `.gitignore` (drop `/lega-c/optar` and other C build entries only if nothing else needs them), `lega-c/record_vectors/record.py` (import the moved `cbuild` by path), `tools/extract_font.py` (unchanged unless it imports `tests.cbuild`)

**Interfaces:**
- Consumes: Task 4 complete.
- Produces: CI job `ghostscript` replacing `oracle`: installs `ghostscript` only, runs `pytest -q -rs -m gs`, keeps the "fail on skipped tests" step.

- [ ] **Step 1: Write the failing test** `tests/unit/test_no_c_harness.py::test_no_test_imports_the_c_harness`: no file under `tests/` contains `cbuild` or `lega-c` except this test and `tests/vectors/README.md`; `pyproject.toml` has no `oracle` marker; `.github/workflows/ci.yml` contains neither `libpng` nor `oracle`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Do the moves, deletions and edits. In `ci.yml` the slow jobs' marker expression becomes `slow and not gs and not gui`.
- [ ] **Step 4:** Run `.venv/bin/pytest -q` (default suite), `.venv/bin/pytest -q -m gs`, `.venv/bin/pytest --co -q -m slow | tail -1`, `.venv/bin/ruff check .`. Expected: PASS; the default suite now includes the vector tests. `git status --short lega-c` shows additions under `lega-c/record_vectors/` only.
- [ ] **Step 5:** Commit "Removes the comparison with the C tools".

### Task 6: The specification

**Files:**
- Create: `docs/format.md`, `tests/unit/test_spec.py`

**Interfaces:**
- Consumes: `src/optar/format.py`, `encoder.py`, `layout.py`, `fec.py`, `font.py`, `tag.py`, `label.py`, `container.py`, `rs.py`, `pdf.py`, `identify.py`; the design's section "What is built, 1" for the eight parts and their content.
- Produces: `docs/format.md` with the eight parts of the design. Tables that state format numbers are preceded by an HTML comment `<!-- spec-table: NAME -->`; names: `constants`, `dot-sizes`, `layouts`, `header-fields`, `parity`.

Requirements for the text:

- Written for someone who has not seen the code: every term defined before use, every formula with one worked example whose numbers a test checks.
- "must" only for statements about pages and documents that a vector or test checks; decoder method is described in part 7 as informative.
- Each normative section ends with the vector files that pin it (by the names in this plan; they exist once Tasks 2 and 3 merge).
- Plain technical English, no marketing, no references to this plan or to "the port".

- [ ] **Step 1: Write the failing test** `test_spec_tables_match_the_code`: parse each marked table of `docs/format.md` and compare with the code: `constants` against the named constants of `format.py` (every constant the table names must exist with that value); `dot-sizes` against `DOT_SIZES` (name, printer dots, advised scan dpi); `layouts` against `LAYOUTS` (paper, dots, crosses across and down, page pixels, bytes per page from `plan_for(1, fmt, 0)`, margins in mm to 0.01); `header-fields` against `container._FIELDS` (field order and sizes, total `HEADER_SIZE`); `parity` against `PARITY`. Plus `test_spec_worked_examples`: each fenced block marked ```` ```example ```` holds `name = value` lines that the test recomputes (the test maps each name to a function of the code).
- [ ] **Step 2:** Run. Expected: FAIL, no document.
- [ ] **Step 3:** Write `docs/format.md`.
- [ ] **Step 4:** Run the two tests. Expected: PASS. Change one number in a table; expected: FAIL; revert.
- [ ] **Step 5:** `.venv/bin/ruff check .`. Commit "Adds the format specification".

### Task 7: README and project notes

**Files:**
- Modify: `README.md`, `CLAUDE.md`

**Interfaces:**
- Consumes: Tasks 5 and 6.

- [ ] **Step 1:** `README.md`: state near the top that the format is defined by `docs/format.md`; move the sections on building and using the C tools under a "History" heading that points at `lega-c`; remove instructions that no longer work (the oracle test command, libpng flags).
- [ ] **Step 2:** `CLAUDE.md`: replace the oracle wording as the design's section "Documents" says; remove the oracle test command and the `make_fixtures` line; reduce "C build notes" and "C encoder and decoder must stay in sync" to a short "History: lega-c" section (never edited; `lega-c/record_vectors` is not run); remove the C code style section.
- [ ] **Step 3:** `grep -n "oracle\|cbuild\|make_fixtures\|roundtrip" README.md CLAUDE.md` returns only history statements. Commit "Describes the format by its specification and the C program as history".
