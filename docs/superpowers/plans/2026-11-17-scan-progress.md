# Scan progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every scan being read is listed in the application with a drawn progress bar and the name of its current step.

**Architecture:** The readers report step keys through an optional callback; `work.py` turns them into a fraction; `document.py` holds which scans are being read and their progress; `text.py` the words; a list delegate in `read_tab.py` draws the bar.

**Tech Stack:** Python, numpy, PySide6, pytest, pytest-qt.

**Spec:** `docs/superpowers/specs/2026-11-17-scan-progress-design.md`

## Global Constraints

- No reader's result changes; with no callback the library behaves exactly as before. `optar decode` prints what it printed before.
- Library modules hold no user-visible words, never print, import no Qt. `document.py`, `work.py`, `text.py` import no Qt. Every user-visible string is in `text.py`. Nothing slow on the interface thread.
- The bar never moves backwards for one scan.
- Untrusted text (file names) is shown as plain text.
- The owner's real scans are never copied into the repository. No push. Commit subjects capitalised, third-person present, no prefix, no attribution lines.
- `tests/vectors` and `lega-c/` are not edited.

## Review Focus

- A scan removed while "Waiting" (its job not started) and while in any step: its row disappears and its job is cancelled.
- A scan whose label was read and which then goes to the slower reader (the label-only path of `identify_any`): the bar must not jump backwards, and the row ends as a page row.
- Many scans added at once (30): the list stays responsive; progress reports are not emitted more often than about ten times a second per scan.
- A file that is not an image, or cannot be opened: its row ends as "Not readable" with today's reason.
- A file name with HTML in it: shown as plain text in the row.

---

### Task 1: Progress from the readers to a drawn bar

**Files:**
- Modify: `src/optar/identify.py`, `src/optar/decoder/soft.py`, `src/optar_gui/work.py`, `src/optar_gui/document.py`, `src/optar_gui/text.py`, `src/optar_gui/read_tab.py`, `src/optar_gui/jobs.py` only if needed, `README.md` (the application's description)
- Test: `tests/unit/test_soft.py`, `tests/unit/test_work.py`, `tests/unit/test_document.py`, `tests/unit/test_gui_text.py`, `tests/gui/`

**Interfaces:**
- Produces:
  - Library: `identify_any(..., on_progress: Callable[[str, int, int], None] | None = None)`, the same parameter on `identify_coarse` and `read_soft`. It is called as `on_progress(step, done, of)` with step keys defined as constants in `optar/identify.py`: `STEP_FIND` ("find"), `STEP_IDENTIFY` ("identify"), `STEP_SLOW_SAMPLE` ("slow-sample"), `STEP_SLOW_FIT` ("slow-fit"; `done` fits of `of`). `on_slow` stays as it is.
  - `work.py`: `Progress(step: str, done: int, of: int, fraction: float)` (frozen dataclass), steps `STEP_OPEN` ("open") and `STEP_READ` ("read") added to the library's; `process_scan(path, cancelled, on_slow=None, on_progress: Callable[[Progress], None] | None = None)`; `fraction` in [0, 1], never decreasing within one call.
  - `document.py`: every scan that is added and not yet identified, unreadable or assigned by hand is listed by `being_read()` with its latest `Progress` or None (waiting); `set_progress(scan_id, progress)`; row kind `Row.BEING_READ` replaces `Row.READING_COARSE` (its only action is Remove). `Summary` gains what the bottom bar needs for "Working… 3 of 6 scans read".
  - `text.py`: `BEING_READ_SECTION`, `WAITING`, `step_text(progress) -> str`, `being_read_row(name, progress) -> str` (the row's plain text, "name · step words"), the summary's count.
  - `read_tab.py`: a delegate that draws, for a being-read row, the bar (from a fraction the model exposes through a custom role) and the text; other rows are drawn as before.

- [ ] **Step 1:** Tests first: the sequence of progress reports for an ordinary scan and for a coarse one (keys in order, fraction never decreasing, ends at or near 1); nothing reported and identical results when no callback is given; `document` rules (listed from add until identified/unreadable/removed; Remove cancels); the words; the summary count.
- [ ] **Step 2:** Implement library, work, document, text.
- [ ] **Step 3:** GUI tests (marked gui): with a fake reader that reports steps, the rows show "Waiting", then each step's words; the model's fraction role follows; removing a waiting and a running scan; the delegate paints a being-read row without error and paints more filled pixels for a larger fraction (render the row to a QImage); an HTML file name is plain text; the bottom bar's count. Then implement the delegate and the wiring.
- [ ] **Step 4:** README: the application's description says that each scan is listed with a bar while it is read. `ruff check .`; default suite; `QT_QPA_PLATFORM=offscreen pytest -q -m gui` pass. Commit "Shows the progress of each scan while it is read".
