# Coarse-scan reader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A scan the ordinary reader cannot identify gets a second, slower, blur-aware attempt in the library, the command line and the application.

**Architecture:** A new module `src/optar/decoder/soft.py` holds the second reader (`read_soft`, `identify_coarse`). A thin function `identify.identify_any` tries `identify_scan` and then the second reader; `cli.py` and `optar_gui/work.py` call it. Nothing in the ordinary decoder changes.

**Tech Stack:** Python, numpy, Pillow, pytest, PySide6 (application only).

**Spec:** `docs/superpowers/specs/2026-11-17-coarse-scan-reader-design.md`

## Global Constraints

- No change to the page format, to printed pages or to the ordinary reader; every existing test and vector passes unchanged.
- Runtime dependencies stay numpy and Pillow.
- Library modules never print; only `cli.py` does. Every application string is in `optar_gui/text.py`. Nothing slow runs on the interface thread.
- Reader tuning numbers are named constants in `soft.py`, not in `format.py`.
- The owner's real scans (a folder outside the repository, path given in the dispatch) are read in place only: never copied, committed, pushed or uploaded, and their path never appears in a committed file.
- Nothing under `lega-c/` is edited. `tests/vectors` is not edited.
- Commit subjects are capitalised, third-person present, no prefix, no attribution lines. No push.
- Do not loosen the claims tests or change the simulator's defaults.

## Review Focus

- A scan that is not an optar page at all (a photo, a blank page with a frame): the second reader must give up with `IdentifyError`, in bounded time, and never return an identity.
- A rotated coarse scan (quarter turns): identified with the right rotation.
- A coarse scan of a page with a damaged header (all five copies wrong): `IdentifyError`, not a guess.
- Cancelling the application's job while the second reader runs: stops within a few seconds.
- A page with almost no symbols the ordinary reader trusts (so the fit has too little to learn from): `read_soft` must not crash on an empty or tiny region.

---

### Task 1: The second reader in the library

**Files:**
- Create: `src/optar/decoder/soft.py`, `tests/unit/test_soft.py`
- Modify: `src/optar/identify.py` (field `reader` on `ScanIdentity`, function `identify_any`), `src/optar/__init__.py` (export `identify_any`)

**Interfaces:**
- Produces:
  - `soft.read_soft(grid: PageGrid, image: np.ndarray, cancelled: Callable[[], bool] | None = None) -> PageResult` — `image` is the upright grey scan the grid was located on; the result has `bits`, `stats`, `lost_symbols` (int64 array, may be empty), `corrected_bits=None`, `grid=grid`, as `decode_located(detail=True)` gives, so `container.page_payload` takes it. Raises `optar.errors.DecodeError("cancelled")`-free: on cancel it raises `soft.Stopped` (a plain `Exception` subclass defined there).
  - `soft.identify_coarse(image: np.ndarray, options: DecodeOptions | None = None, cancelled=None) -> ScanIdentity` — raises `IdentifyError` like `identify_scan`. The identity has `reader="slow"`, `header`, `payload`, `result`, `layout`, `rotation`, `scan_dpi` (of the scan as given, not of the enlarged image), `name=""`, `tag=None`.
  - `ScanIdentity.reader: str = "ordinary"` (new last field).
  - `identify.identify_any(image, options=None, *, slow=True, cancelled=None, on_slow: Callable[[], None] | None = None) -> ScanIdentity` — `identify_scan` first; on `IdentifyError` whose `scan_dpi` is not None (an outline was found) and `slow` is true, calls `on_slow()` if given and then `identify_coarse`; if that fails too, raises the *first* error with attribute `slow_tried = True` (add `slow_tried: bool = False` to `IdentifyError`).

- [ ] **Step 1:** Read the scratch script the dispatch names; it is the method to port (design section "What the experiment did"). Port it into `soft.py` with named constants: `ENLARGE_TO` (pixels per dot aimed at, about 4.3), `SAMPLE_OFFSETS` (-1.5 to 1.5 step 0.5 dots), `REGIONS` (16, 22), `ROUNDS` (5), `KEEP` (0.6), `RIDGE` (1e-2).
- [ ] **Step 2:** Tests in `tests/unit/test_soft.py`, on a small custom format with `tests/helpers.simulate_scan`:
  - `test_read_soft_reads_a_scan_the_ordinary_reader_cannot`: a page scanned so coarsely that `decode_located` leaves uncorrectable symbols; `read_soft` returns the exact payload bits.
  - `test_read_soft_matches_the_ordinary_reader_on_a_clean_scan`.
  - `test_read_soft_survives_a_page_with_nothing_to_learn_from` (a grey image with a frame: returns a result or raises `DecodeError`, no other exception).
  - `test_identify_coarse_finds_a_version_1_page` (with a quarter turn too), `test_identify_coarse_refuses_a_page_without_a_header`, `test_identify_coarse_refuses_a_picture`.
  - `test_identify_any_keeps_the_ordinary_result`, `test_identify_any_falls_back`, `test_identify_any_reports_the_first_error`, `test_cancel_stops_the_slow_reader`.
- [ ] **Step 3:** Make it fast: goal under 60 s for a full A4 Standard page on this machine, single process. Report the time measured and where it goes.
- [ ] **Step 4:** Run the owner's six scans in place through `identify_any` and `unwrap` with a scratch script (not committed). Expected: verified, 759,879 bytes. Report repaired bytes, worst block use, time per page. Decide by measurement whether marking low-confidence symbols as lost helps; record the numbers.
- [ ] **Step 5:** `.venv/bin/ruff check .`, `.venv/bin/pytest -q -n 8` (default suite) pass. Commit "Adds a second, slower reader for scans too coarse for the ordinary one".

### Task 2: Command line

**Files:**
- Modify: `src/optar/cli.py`, `tests/unit/test_cli.py`

**Interfaces:**
- Consumes: `identify_any`, `ScanIdentity.reader`, `IdentifyError.slow_tried` from Task 1.

- [ ] **Step 1:** Tests: a coarse simulated scan of a small version-1 document decodes through `optar decode`; stderr names the slower reader for that page; `--no-slow-reader` makes the same command fail as before; `optar identify` (if the sub-command lists scans) marks the page as read by the slower reader.
- [ ] **Step 2:** Replace the `identify_scan` call by `identify_any(image, slow=not args.no_slow_reader, on_slow=...)`; the note goes to stderr; the coarse advice stays and, when `slow_tried`, says the slower reader was tried.
- [ ] **Step 3:** Lint and tests pass. Commit "Tries the slower reader from the command line".

### Task 3: Application

**Files:**
- Modify: `src/optar_gui/work.py`, `src/optar_gui/text.py`, `src/optar_gui/document.py` and `read_tab.py` only as far as showing the new state needs, `tests/unit/test_work.py`, `tests/unit/test_gui_text.py`, `tests/gui/` as needed

**Interfaces:**
- Consumes: `identify_any`, `ScanIdentity.reader`, `IdentifyError.slow_tried`, `soft.Stopped` from Task 1.
- Produces: `ScanWork.slow: bool` (the page was read by the second reader); `process_scan(path, cancelled, on_slow=None)`; strings `text.READING_COARSE`, `text.read_by_slow_reader(...)`, and the coarse-scan message extended for `slow_tried`.

- [ ] **Step 1:** Tests: `process_scan` on a coarse simulated scan returns work with `slow` true and the page identified; cancelling during the second reader raises `Cancelled`; an unreadable coarse scan's reason says the slower reader was tried; the row and detail text of a slow-read page say so; the job reports "reading a coarse scan" while it runs (pytest-qt, marked gui).
- [ ] **Step 2:** Implement. The second reader runs inside the existing identification job; `on_slow` reaches the interface through the job's existing signal mechanism (add one if none fits).
- [ ] **Step 3:** Lint; default suite; `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui` pass. Commit "Tries the slower reader in the application".

### Task 4: Evidence and documents

**Files:**
- Create: `tests/unit/test_coarse_claim.py`
- Modify: `README.md`, `CLAUDE.md`, `docs/format.md` (part 7 only), `tests/unit/test_spec.py` only if a marked table changes (it should not)

**Interfaces:**
- Consumes: Tasks 1 to 3.

- [ ] **Step 1:** `test_coarse_claim.py` (marked `slow`): a Standard-dot A4 document with High protection, simulated at 300 dpi, is identified page by page with `identify_any` and unwrapped verified; the same with the slow reader off is not. Use the simulator's defaults; if the claim does not hold at the defaults, find the settings it holds for, state them in the test's docstring, and report the gap. Do not change defaults.
- [ ] **Step 2:** README: a section on the slower reader (when it runs, how long, `--no-slow-reader`), and under "What has and has not been shown" the evidence exactly: one real document (six pages, Standard dots, High protection, about 290 dpi, verified), plus what the simulated test shows; Standard protection is expected to fail at that resolution; old 0.2-style pages are not covered. `CLAUDE.md`: one rule (the second reader lives in `decoder/soft.py`, is tried only after the ordinary one fails, and must not change the ordinary reader's results). `docs/format.md` part 7: a short informative description.
- [ ] **Step 3:** Lint; default suite; the new slow test; `tests/unit/test_spec.py` pass. Commit "Documents the slower reader and what has been shown for it".
