# Optar Robust Format Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Printouts that read back from 200–300 dpi scans: a choice of larger dots, and Reed-Solomon parity spread over the whole document, carried in a container whose pages identify themselves from their data.

**Architecture:** Pages stay ordinary version-0 optar pages. A new library layer wraps the file into a stream (page headers, file, name, parity) before `encode()`, and unwraps and repairs it after `decode`. `format.py` gains dot sizes (a print scale and a grid per paper). Identification tries each (paper, dot size, rotation), lets a valid label tag win, then looks for a header in the decoded data. The application groups version-1 pages by header and saves through the unwrapper.

**Tech Stack:** Python 3.12+, numpy, Pillow, PySide6, pytest, pytest-qt, ruff.

**Spec:** `docs/superpowers/specs/2026-11-16-robust-format-design.md`. Read it before starting any task.

## Global Constraints

- Nothing under `src/optar` imports Qt or `optar_gui`. Runtime dependencies stay numpy and Pillow. Reed-Solomon is written on numpy.
- `optar_gui/document.py`, `work.py` and `text.py` import no Qt. Rules live in `document.py`; every user-visible string in `text.py`; no scan is read, decoded, repaired, hashed or saved on the interface thread.
- Format numbers (grids, dot scales, offsets, parity sizes, header sizes) live only in `src/optar/format.py`.
- The decoder's algorithm and constants are not retuned. The C sources, `Makefile` and `pgm2ps` are not edited.
- Every page is a valid version-0 optar page: `encode(stream, fmt, label)` is used unchanged.
- Printouts from 0.1.0, 0.2.0 and the C tool behave exactly as now. Existing tests and `tests/golden/fixtures.json` stay unchanged.
- A codeword that cannot be corrected is reported, never guessed. The fingerprint decides "Verified".
- Every new `.py` file starts with `# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026`.
- Tests write only under pytest's `tmp_path`.
- Commit subjects are capitalised, third-person present, no prefix, no attribution lines. Work on branch `robust-format`. Do not push or open a pull request without the owner saying so.

**Reference values**

| Dots | name | printer dots | printed dpi | advised scan dpi | A4 grid | A4 format string | A4 page bytes | Letter grid | Letter format string | Letter page bytes |
|---|---|---|---|---|---|---|---|---|---|---|
| Standard | `standard` | 3 | 200 | 600 | 65 × 93 | `0-65-93-24-3-1-2-24` | 199,773 | 67 × 87 | `0-67-87-24-3-1-2-24` | 192,591 |
| Medium | `medium` | 4 | 150 | 450 | 50 × 70 | `0-50-70-24-3-1-2-24` | 114,904 | 51 × 66 | `0-51-66-24-3-1-2-24` | 110,463 |
| Big | `big` | 5 | 120 | 360 | 40 × 56 | `0-40-56-24-3-1-2-24` | 73,027 | 41 × 52 | `0-41-52-24-3-1-2-24` | 69,463 |
| Large | `large` | 6 | 100 | 300 | 33 × 46 | `0-33-46-24-3-1-2-24` | 49,119 | 34 × 44 | `0-34-44-24-3-1-2-24` | 48,403 |
| Extra large | `xlarge` | 9 | 66.67 | 200 | 22 × 31 | `0-22-31-24-3-1-2-24` | 21,606 | 23 × 29 | `0-23-29-24-3-1-2-24` | 21,127 |

"Page bytes" is `fmt.net_bits // 8`. A data dot is `printer dots` wide on a 600 dpi printer; `scale = printer_dots / 3` (a `Fraction`); printed resolution is `600 / printer_dots` dots per inch; the advised scan resolution is 3 scan pixels per dot, `1800 // printer_dots`. Wherever a task below says "standard|large|xlarge" or "scale: int", the five names and the fractional scale of this table apply (owner's change of 2026-11-16). Parity bytes per 255-byte codeword: `none` 0, `standard` 32, `high` 64.

Header (38 bytes, big-endian): magic `b"oPt1"` (4), container version `1` (1), parity bytes (1), page number from 1 (2), page count (2), file size (8), first 16 bytes of the file's SHA-256 (16), CRC-32 of the preceding 34 bytes (4). `HEADER_COPIES = 5`; copy *c* starts at byte `c * (page_bytes // 5)` of the page payload. The body of a page is the payload bytes not covered by a header copy, in order.

Body layout: `B` = body bytes of all pages; `m = B // 255` codewords; the last `B - 255*m` body bytes are zero and unused. Data region (`m * (255 - parity)` bytes) = file, then one length byte, then the file name in UTF-8 (cut to 255 bytes on a character boundary), then zeros. Byte *i* of codeword *j* sits at body position `i*m + (j + i*SPREAD_STEP) % m`, `SPREAD_STEP = 7919`. With parity 0 the same layout is used with 255 data bytes per codeword. The page count is the smallest `N` whose data region holds the file and the name record.

Rotation convention as before: `upright = np.rot90(image, rotation)`.

## Review Focus

1. **A 0.2.0 printout, or a reprint of a stream saved by an old tool, is added**: it is identified by its tag and handled by the 0.2.0 rules, even though its data may contain header bytes. (Tasks 6, 8)
2. **A scan too coarse to read** (the owner's 200 dpi scans of Standard dots): it is listed as not readable with the resolution it was scanned at and the resolution needed, not "label could not be read". (Tasks 6, 9)
3. **Pages of two documents with the same file but different dot size or protection are mixed**: they form separate documents; none is used in the other. (Task 8)
4. **A protected document with too many pages missing or too much damage**: saving says it could not be repaired and which pages to rescan; no file is written as "Verified", and nothing is guessed. (Tasks 5, 8, 9)
5. **A very large file with protection chosen**: the window and `optar encode` refuse before reading it all, with the limit stated. (Tasks 4, 7, 10)

## Parallel lanes

Task 1 first. Then three lanes on different files: **A** = 2 (print scale); **B** = 3, 4, 5 (Reed-Solomon, container); **C** = the scan simulator of Task 6 step 1. Task 6 needs 1 and 4. Task 7 needs 2, 5, 6. Tasks 8, 9, 10 edit the application in order and need 5 and 6. Task 11 last.

## File Structure

```
src/optar/format.py        DotSize, Layout, LAYOUTS, get_layout, PARITY, header and spread numbers
src/optar/rs.py            GF(256) Reed-Solomon, errors and erasures, vectorised      new
src/optar/container.py     Header, plan, wrap, page payloads, unwrap                   new
src/optar/pdf.py, imageio.py   print scale
src/optar/identify.py      layouts as candidates, tag wins, header route, scan resolution
src/optar/cli.py           --dots, --protect, --compatible; decode of version-1 pages
src/optar_gui/document.py  version-1 documents, recoverable state, repair results
src/optar_gui/work.py      header and payload in ScanWork, repair in the save job
src/optar_gui/text.py      new strings
src/optar_gui/write_tab.py dot size and protection choices
tests/helpers.py           simulate_scan
tests/unit/test_rs.py, test_container.py, test_claims.py                              new
```

---

### Task 1: Dot sizes and layouts

**Files:** Modify `src/optar/format.py`, `src/optar/__init__.py`. Test `tests/unit/test_format.py`.

**Interfaces — produces:**

```python
@dataclass(frozen=True)
class DotSize:
    name: str    # "standard" | "large" | "xlarge"
    scale: int   # 1, 2, 3: printed dot = scale/200 inch
DOT_SIZES: dict[str, DotSize]

@dataclass(frozen=True)
class Layout:
    paper: Paper
    dots: DotSize
    xcrosses: int
    ycrosses: int
    offset_x_pt: float
    offset_y_pt: float
    @property
    def fmt(self) -> PageFormat: ...
    @property
    def pixels_per_inch(self) -> Fraction: ...          # Fraction(200, scale)
    def margins(self) -> tuple[float, float, float, float]: ...  # left, bottom, right, top, points
    @property
    def scan_dpi(self) -> int: ...                       # 600, 300, 200: the advised scan resolution

LAYOUTS: dict[tuple[str, str], Layout]                   # (paper name, dot size name)
def get_layout(paper: str, dots: str = "standard") -> Layout   # FormatError for unknown names
def layout_for_format(format: str) -> Layout | None            # by format string
PARITY: dict[str, int] = {"none": 0, "standard": 32, "high": 64}
HEADER_SIZE = 38; HEADER_COPIES = 5; SPREAD_STEP = 7919; CODEWORD = 255
```

- [ ] **Step 1: Failing tests.** For each row of Reference values: `get_layout(p, d).fmt.to_string()` and `fmt.net_bits // 8` equal the table. `get_layout("a4").fmt == PageFormat.for_paper(get_paper("a4"))` and its offsets equal the paper's (19.20, 17.40); the same for Letter. Every layout: all four margins ≥ `MIN_MARGIN_PT`; `offset * 600 / 72` is a whole number for both offsets (within 1e-9); left and right margins differ by less than one 600 dpi dot plus rounding (0.25 pt), likewise bottom and top, for `large` and `xlarge`. `layout_for_format("0-33-46-24-3-1-2-24").dots.name == "large"`; `layout_for_format("0-1-2-3-4-1-2-24") is None`. Each larger-dot grid is the largest that fits: adding one cross in either direction breaks a margin. Format strings of the six layouts are distinct.
- [ ] **Step 2:** Run `pytest tests/unit/test_format.py -q`. Expected: FAIL (names not defined).
- [ ] **Step 3: Implement.** Standard layouts take grid and offsets from the existing `PAPERS` entries. Larger-dot offsets: centre the image, then round down to a multiple of `72/600` pt. `Paper` and `PAPERS` keep their fields.
- [ ] **Step 4:** Run the test file, then `pytest -q`. Expected: PASS.
- [ ] **Step 5:** Commit: "Adds dot sizes and their page layouts".

### Task 2: Printing at a dot size

**Files:** Modify `src/optar/pdf.py`, `src/optar/imageio.py`. Test `tests/unit/test_pdf.py`, `tests/unit/test_imageio.py`.

**Interfaces — consumes** `Layout`. **Produces:** `write_pdf(path, pages, paper: Paper | Layout) -> int` (a `Paper` means its standard layout; existing calls unchanged); `write_png(path, pixels, pixels_per_inch=PIXELS_PER_INCH)`.

- [ ] **Step 1: Failing tests.** A `large` A4 page written with `write_pdf(..., get_layout("a4", "large"))`: parsed with `tests.helpers.parse_pdf`, the image is placed at the layout's offsets with width `fmt.width * 72 * 2 / 200` pt and height likewise; the media box is A4. An image whose size is not the layout's page size is refused as today. `write_png(path, px, get_layout("a4", "xlarge").pixels_per_inch)` stores a dpi within 0.01 of 66.667. Existing PDF tests pass unchanged (byte-identical output for a `Paper`).
- [ ] **Step 2–4:** Run to fail, implement, run to pass (`pytest tests/unit/test_pdf.py tests/unit/test_imageio.py -q`).
- [ ] **Step 5:** Commit: "Prints pages at the dot size of their layout".

### Task 3: Reed-Solomon

**Files:** Create `src/optar/rs.py`. Test `tests/unit/test_rs.py`.

**Interfaces — produces:**

```python
class RSCode:
    def __init__(self, parity: int): ...          # 1 <= parity <= 254; n = 255, k = 255 - parity
    def encode(self, data: np.ndarray) -> np.ndarray:
        """data uint8 (w, k) -> parity uint8 (w, parity). Systematic: codeword = data then parity."""
    def decode(self, words: np.ndarray, erased: np.ndarray | None = None) -> RSResult:
        """words uint8 (w, 255); erased bool (w, 255), True where the byte is known bad."""

@dataclass(frozen=True)
class RSResult:
    words: np.ndarray     # corrected codewords (w, 255); rows that failed are returned as received
    ok: np.ndarray        # bool (w,)
    errors: np.ndarray    # int (w,): bytes changed at places not marked erased
    erasures: np.ndarray  # int (w,): bytes marked erased (whether or not their value changed)
```

GF(256) with polynomial 0x11D, generator roots α^0 … α^(parity−1). A row is `ok` only if `2*errors + erasures <= parity` and the corrected word has zero syndromes.

- [ ] **Step 1: Failing tests.** (a) Known answer: `RSCode(32).encode` of the 223 bytes `0..222` equals a vector computed in the test by plain polynomial division written independently (a 15-line reference in the test file). (b) Clean words decode `ok` with zero counts. (c) For parity 32 and 64, 200 random words each: `t` random errors and `e` random erasures with `2t + e <= parity` (include `t = parity//2, e = 0` and `t = 0, e = parity`) are corrected exactly; counts match. (d) `2t + e = parity + 1` and `parity + 8`: the row is not `ok`, or, if it decodes to another codeword, `words` differs from the original (assert that no row is both `ok` and equal to the original, and that fewer than 5% of rows are `ok`). (e) More erasures than parity: not `ok`, no exception. (f) Mixed batch: failing rows do not disturb good rows. (g) 20,000 words with ≤ 4 errors decode in under 5 seconds (mark `slow` if the machine needs it).
- [ ] **Step 2–4:** Run to fail, implement (syndromes for all rows with numpy; rows with zero syndromes and no erasures skip the solver; Berlekamp–Massey with erasure locator and Forney, or an equivalent, over the remaining rows), run to pass.
- [ ] **Step 5:** Commit: "Adds a Reed-Solomon code with errors and erasures".

### Task 4: Container, writing side

**Files:** Create `src/optar/container.py`; modify `src/optar/__init__.py`. Test `tests/unit/test_container.py`.

**Interfaces — consumes** `RSCode`, format numbers. **Produces:**

```python
PROTECTED_MAX_BYTES: int = 256 * 1024 * 1024     # largest stream of a document with parity

@dataclass(frozen=True)
class Header:
    page: int; total: int; size: int; fingerprint: bytes; parity: int   # fingerprint: 16 bytes
    def pack(self) -> bytes                                             # HEADER_SIZE bytes

def read_header(payload: bytes) -> Header | None
    """The header of a page payload: the copies whose CRC passes must agree; else None."""

@dataclass(frozen=True)
class Plan:
    fmt: PageFormat; parity: int; total: int        # pages
    page_bytes: int; page_body: int                 # per page
    codewords: int; data_bytes: int                 # m, m * (255 - parity)
def plan(size: int, name: str, fmt: PageFormat, parity: int) -> Plan
    """OptarError if more than MAX_PAGES pages, or parity > 0 and the stream exceeds PROTECTED_MAX_BYTES."""
def plan_for(total: int, fmt: PageFormat, parity: int) -> Plan     # from a header's page count
def positions(p: Plan) -> np.ndarray                               # int64 (m, 255): body position of each codeword byte
def wrap(data: bytes, name: str, fmt: PageFormat, parity: int) -> bytes
    """The stream to give encode(): each page's payload, padded to fmt.net_bits bits."""
def pages_promised(p: Plan) -> int
    """Whole pages the window may promise can be lost: the largest n with
    ceil(n * 255 / total) <= 3 * parity // 4; 0 without parity."""
def fingerprint(data: bytes) -> bytes                              # sha256(data).digest()[:16]
```

- [ ] **Step 1: Failing tests.** `Header.pack` round-trips through `read_header` on a payload built with five copies; one, then four copies corrupted still reads; all five corrupted → `None`; two valid copies that differ → `None`; random payloads (10,000) → `None`. For every layout and parity: `page_count(len(wrap(data, name, fmt, parity)), fmt) == plan(...).total`; decoding each page's bits with no scan (take `stream` bits `[p*net_bits, (p+1)*net_bits)`, drop the odd bits) gives a payload whose header has the right page, total, size, parity and fingerprint. `positions` is a bijection onto `range(255*m)` and row `j` has exactly one position in each slice `[i*m, (i+1)*m)`. Page counts: a 552,508-byte file gives 3 pages on Standard A4 with parity 0 and 4 with parity 32 (verify by computing from the plan in the test rather than hard-coding more). `plan` picks the smallest total: `plan(...).data_bytes >= size + 1 + len(name_bytes)` and the same with `total - 1` fails. Name longer than 255 bytes is cut on a character boundary. Empty file: one page. `pages_promised`: Standard parity, 10 pages → 0, 11 → 1, 22 → 2; High, 5 → 0, 6 → 1. A size that needs more than `MAX_PAGES` pages, and a protected stream over `PROTECTED_MAX_BYTES`, raise `OptarError` from `plan` without building anything.
- [ ] **Step 2–4:** Run to fail, implement, run to pass.
- [ ] **Step 5:** Commit: "Adds the container that wraps a file with page headers and parity".

### Task 5: Container, reading side

**Files:** Modify `src/optar/container.py`, `src/optar/__init__.py`. Test `tests/unit/test_container.py`.

**Interfaces — produces:**

```python
@dataclass(frozen=True)
class PagePayload:
    data: bytes            # fmt.net_bits // 8 bytes
    erased: np.ndarray     # bool, same length: bytes inside codewords Golay could not correct
def page_payload(result: PageResult, fmt: PageFormat) -> PagePayload
    """From decode_located(..., detail=True): bits packed MSB first, odd bits dropped;
    a byte is erased if any of its bits lies in a symbol listed in result.lost_symbols."""

@dataclass(frozen=True)
class Unwrapped:
    data: bytes | None        # the file, cut to size; None if any codeword holding file bytes failed
    name: str                 # "" if unreadable
    verified: bool            # data is not None and its fingerprint equals the header's
    repaired_bytes: int       # bytes parity changed or filled
    worst_used: int           # max over codewords of 2*errors + erasures
    budget: int               # parity bytes per codeword
    failed: int               # codewords not corrected
    page_damage: dict[int, int]   # page number -> body bytes of that page that were wrong or erased
    missing: tuple[int, ...]  # page numbers not supplied
def unwrap(header: Header, fmt: PageFormat, pages: Mapping[int, PagePayload]) -> Unwrapped
```

Missing pages are all-erased. With parity 0 nothing is repaired: `data` is taken as read and `verified` is the fingerprint's word.

- [ ] **Step 1: Failing tests.** Round trip (wrap → split into page payloads → unwrap) for every layout and parity: `verified`, `data == original`, `name` right, `repaired_bytes == 0`. Random byte errors at 2% of body bytes, Standard parity: verified, `repaired_bytes` equals the number of corrupted bytes, `worst_used <= 32`. The same bytes marked erased: `worst_used` about half. A 12-page document with one page missing: verified, `missing == (n,)`. An 8-page document with one page missing and 1% random errors elsewhere: `verified` False, `failed > 0`, `data is None`, and `page_damage` names the missing page as worst. **Blot:** build a 12-page Large A4 document, encode page 5 with `encode`, paint a filled disc (radius 12% of the page width) white in the page image, decode it (no scan simulation; `decode_page(..., detail=True)`), and unwrap with the other pages clean: verified, and `worst_used <= 24`. Repeat with the disc at three other places. If the bound fails, change the permutation (not the bound) until it holds, keeping the one-byte-per-slice property. A header from another document passed with these pages → not verified, no exception. Parity 0 with one page missing → `data is None`.
- [ ] **Step 2–4:** Run to fail, implement, run to pass.
- [ ] **Step 5:** Commit: "Unwraps and repairs a document from its page payloads".

### Task 6: Identification, scan resolution and the claims

**Files:** Modify `src/optar/identify.py`, `src/optar/__init__.py`, `tests/helpers.py`. Test `tests/unit/test_identify.py`; create `tests/unit/test_claims.py`.

**Interfaces — consumes** `LAYOUTS`, `read_header`, `page_payload`. **Produces:**

```python
# tests/helpers.py
def simulate_scan(pixels: np.ndarray, layout: Layout, dpi: float, *, rotate_deg=0.4,
                  blur=2.0, noise=6.0, seed=1, quarter_turns=0) -> np.ndarray
    """A grey scan of a printed page: 600 dpi print, Gaussian blur (sigma in 600 dpi dots),
    rotation, white border, box resampling to dpi, noise. The harness behind the spec's Evidence."""

# identify.py
@dataclass(frozen=True)
class ScanIdentity:      # existing fields kept; new ones have defaults
    ...
    layout: Layout | None = None
    header: Header | None = None          # set for a version-1 page
    payload: PagePayload | None = None    # set with header: the page is already decoded
    result: PageResult | None = None      # set with header (detail=True)
    scan_dpi: float | None = None         # estimated resolution of the scan
def scan_dpi(grid: PageGrid, layout: Layout) -> float
    """Scan pixels per inch: mean distance between neighbouring cross centres / cpitch * layout.pixels_per_inch."""
class IdentifyError:     # gains attribute scan_dpi: float | None, estimated from the outline
```

`identify_scan` order, per spec: outline; layouts sorted by shape distance (ties: standard, large, xlarge); for each layout and rotation: locate; for a standard layout read the label and accept a valid tag exactly as today (0.2.0 page); otherwise decode with detail and accept a header whose `page`/`total` are in range and for which `plan_for(header.total, fmt, header.parity)` holds a file of `header.size`; otherwise, for a standard layout, the existing untagged rules. `page`, `total` come from the header; `tag` is `None`; `name` is the label's free text if the label parses, else `""`. When nothing is accepted the `IdentifyError` carries `scan_dpi` estimated as outline width in pixels divided by the page image's printed width in inches (the same for all dot sizes to within a few percent; use the closest paper's standard layout).

- [ ] **Step 1:** Add `simulate_scan`; test it: a Standard A4 page at 600 dpi decodes with no uncorrectable symbols; output size is within 2% of `paper inches * dpi` plus the border.
- [ ] **Step 2: Failing identification tests.** A wrapped Large A4 page scanned at 300 dpi, in each quarter turn: `header.page`, `layout.dots.name == "large"`, `rotation`, `payload` set, `scan_dpi` within 5% of 300. The same for Extra large Letter at 200 dpi. A 0.2.0 tagged page: identity as before, `header is None`. **Reprinted stream:** `wrap` a file, then encode that stream with the 0.2.0 tagged label (`make_tag` of the stream): identified by tag, `header is None`. A Standard-dot version-1 page at 600 dpi: `header` set, `tag is None`. A Standard page scanned at 200 dpi: `IdentifyError` with `scan_dpi` within 10% of 200. A photo-like random image: `IdentifyError`, no exception of another kind. A Large page tried as Extra large must not produce a header (covered by the cases above passing with the right layout; add one explicit assertion that `identify_scan` of a Large page never returns `xlarge`).
- [ ] **Step 3: Failing claims tests** (`test_claims.py`, marked `slow`; each builds a 3-page document, scans every page with a different seed, identifies, unwraps, asserts `verified`): Large at 300 dpi; Large at 200 dpi; Extra large at 200 dpi; Standard dots with Standard parity at 300 dpi and at 250 dpi; a 12-page Large document at 300 dpi with one page withheld. Protection is Standard throughout. If a claim fails, do not loosen the simulation or the assertion: report it (`DONE_WITH_CONCERNS`) with the measured numbers.
- [ ] **Step 4:** Implement; run `pytest tests/unit/test_identify.py -q` and `pytest tests/unit/test_claims.py -q -m slow`. Expected: PASS. Run `pytest -q` (existing identification tests unchanged).
- [ ] **Step 5:** Commit: "Identifies version-1 pages from their data and estimates scan resolution".

### Task 7: Command line

**Files:** Modify `src/optar/cli.py`. Test `tests/unit/test_cli.py`.

**Interfaces — produces:** `optar encode INPUT [--dots standard|large|xlarge] [--protect none|standard|high] [--compatible]`; `optar decode` reading version-1 pages.

Rules. Encode: without the new options the command behaves as 0.2.0 (tagged, compatible) — the command line's default does not change, so scripts keep working; `--dots` other than `standard`, or `--protect` given at all (including `none`), selects the container; `--compatible` with either is an error; `--format` with either is an error. PDF and PNG output use the layout's scale. The message printed after encoding names the scan resolution to use (`layout.scan_dpi`). Decode: every `BASE_NNNN.png` is read; if the first identifies as a version-1 page, all scans are identified (any order, any orientation), grouped by header, unwrapped; the file is written only if verified, or with `--force` (new option) when not; exit status 0 only if verified; a summary line reports repaired bytes, `worst_used`/`budget`, missing pages. Otherwise the existing path runs unchanged.

- [ ] **Step 1: Failing tests.** `encode --dots large --protect standard --to png`, then `decode` of the written PNGs (they are exact pages; rename two files to swap their order): output equals input, exit 0. One page deleted from a 12-page document: exit 0, output equal, stderr names the missing page. One page deleted from a 3-page document: exit 1, no output file. `--compatible --dots large` → usage error. Plain `encode` output is byte-identical to before (existing tests). `--protect standard` on an input over the size limit fails before writing anything.
- [ ] **Step 2–4:** Run to fail, implement, run to pass (`pytest tests/unit/test_cli.py -q`).
- [ ] **Step 5:** Commit: "Adds dot size and protection to the command line".

### Task 8: Version-1 documents in the application's rules

**Files:** Modify `src/optar_gui/document.py`. Test `tests/unit/test_document.py`.

**Interfaces — consumes** `Header`, `PagePayload`, `unwrap`, `Unwrapped`, `plan_for`, `pages_promised`. **Produces:** `ScanInfo` gains `header: Header | None = None` and `scan_dpi: float | None = None`; `Document.set_payload(scan_id: int, payload: PagePayload) -> None`; `DocState.RECOVERABLE`; `Summary` gains `protection: int`, `missing_pages: tuple[int, ...]`, `repair: Unwrapped | None`; `Document.repair_job() -> Callable | None` (a Qt-free callable taking `cancelled`, returning `Unwrapped`, as `verdict_job` does for tagged documents) and `Document.accept_repair(result)`; `Document.save_bytes() -> bytes | None` (the unwrapped file once a repair result is accepted).

Rules. A version-1 scan's document identity is `(fingerprint, size, total, parity, format string)`; such scans never join a tagged or untagged group, and the reverse. Page slots, duplicates, "better scan wins" and switching work as for tagged documents; "better" for version-1 scans is fewer erased bytes, then fewer corrected bits. State: all pages present → as today, with the verdict coming from the repair result (`verified`); pages missing and `parity > 0` and missing count ≤ `pages_promised` or a repair result already says verified → `RECOVERABLE`; otherwise incomplete as today. The repair job is offered whenever the set of used scans changed since the last accepted result and at least one page is present. `can_save` for a version-1 document requires an accepted result with `data is not None`; an unverified result follows today's "does not match" confirmation path. Hand assignment and "start by hand" do not apply to version-1 documents (their pages always identify themselves); an unidentified scan cannot be assigned into one.

- [ ] **Step 1: Failing tests** (payloads built with `wrap`, no images): three pages added in any order → complete; repair job result accepted → verified, `save_bytes()` equals the file. 12-page Standard-parity document with page 7 absent → `RECOVERABLE`, `missing_pages == (7,)`, job verifies, save allowed. 3-page document with one absent → incomplete, save not offered as verified. Pages of the same file wrapped with `parity=32` and `parity=64` → two groups, neither uses the other's scans. A tagged 0.2.0 scan and a version-1 scan of the same file → two groups. Two scans of one page → the one with fewer erased bytes is used, the other is a spare; replacing invalidates the accepted result and the job is offered again. Removing a scan after a result → result dropped. Failed repair → `Summary.repair.page_damage` available and state not verified. Existing document tests pass unchanged.
- [ ] **Step 2–4:** Run to fail, implement, run to pass (`pytest tests/unit/test_document.py -q`).
- [ ] **Step 5:** Commit: "Groups version-1 pages into documents and repairs them".

### Task 9: Reading tab: version-1 scans, repair, coarse scans

**Files:** Modify `src/optar_gui/work.py`, `src/optar_gui/read_tab.py`, `src/optar_gui/text.py`. Test `tests/unit/test_work.py`, `tests/unit/test_gui_text.py`, `tests/gui/test_read_tab.py`.

**Interfaces — consumes** Task 6 and Task 8. **Produces:** `ScanWork` carries `header`, `payload`, `scan_dpi`; a failed identification carries `scan_dpi`; `text.coarse_scan(scan_dpi: float, layout: Layout | None) -> str`; `text.repair_line(u: Unwrapped) -> str`; `text.rescan_advice(u: Unwrapped) -> str`.

Behaviour. `process_scan` uses the identity's decoded result for a version-1 page (no second decode). The controller runs the repair job on the existing background runner whenever the document offers one, shows "Checking…" meanwhile as for fingerprints, and passes the result to `accept_repair`. Saving a version-1 document writes `save_bytes()` through the existing save path and signals. Strings (exact wording is the implementer's, these facts are fixed): the scan note for a version-1 page whose `scan_dpi` is below twice the layout's printed resolution states the resolution scanned and `layout.scan_dpi`; an unreadable scan whose error carries `scan_dpi < 400` says it was scanned at about that resolution and that Standard dots need 600, Large 300, Extra large 200; the document line states bytes repaired and `worst_used of budget`; `RECOVERABLE` names the missing pages; a failed repair names the pages with the most damage to rescan (up to three, by `page_damage`).

- [ ] **Step 1: Failing tests.** `process_scan` on a simulated Large page at 300 dpi returns header and payload, and `decode_located` is called once (count with a monkeypatched wrapper). `process_scan` on a Standard page at 200 dpi fails with `scan_dpi` near 200, and `text` for it contains "200" and "600". `repair_line`/`rescan_advice` unit tests on hand-built `Unwrapped` values (including `budget == 0`). Off-screen: three version-1 scans added → the tab reaches Verified; with one of twelve missing → the recoverable wording and Save enabled; save writes the original bytes; a failed repair shows the rescan advice and no "Verified". All text is plain text.
- [ ] **Step 2–4:** Run to fail, implement, run `pytest -q` and `QT_QPA_PLATFORM=offscreen pytest -q -m gui`. Expected: PASS.
- [ ] **Step 5:** Commit: "Reads, repairs and saves version-1 documents in the window".

### Task 10: Putting on paper: dot size and protection

**Files:** Modify `src/optar_gui/write_tab.py`, `src/optar_gui/work.py`, `src/optar_gui/text.py`, `src/optar_gui/selftest.py`. Test `tests/gui/test_write_tab.py`, `tests/unit/test_work.py`, `tests/gui/test_selftest.py`.

**Interfaces — consumes** `get_layout`, `plan`, `pages_promised`, `wrap`. **Produces:** `encode_to_pdf(src, dest, paper_name, name, cancelled, *, dots="standard", protect="standard", compatible=False)`; `WriteTab` properties `dots`, `protect`, `compatible`.

Behaviour. Two selectors (dot size with the advised scan resolution in each entry; protection) and a "Compatible with optar 0.2 and the C tool" checkbox. Defaults: Standard dots, Standard protection, not compatible. Checking Compatible sets and disables both selectors (Standard, None) and produces today's tagged printout. The summary line updates on every change: page count, and the promise from `pages_promised` ("can lose 1 page of 12", or that damage within pages is repaired, or nothing for None). A file too large for the choice (over `MAX_PAGES`, or over the protected limit) disables Create with the reason; the check uses `plan` on the size from `prepare_file` and does not read the file again. The label of a version-1 page is the name only (no tag); the label preview reflects the layout's label capacity.

- [ ] **Step 1: Failing tests.** `encode_to_pdf` with `dots="large", protect="standard"` writes a PDF whose page count equals `plan(...).total` and whose image placement matches the layout (via `parse_pdf`); with `compatible=True` the output is byte-identical to the 0.2.0 output for the same input. Off-screen: defaults as stated; toggling Compatible disables and restores the selectors; the summary shows the plan's page count for each of the nine combinations of a fixed file; the oversize case disables Create. The self-test additionally encodes and decodes a Large, Standard-protection document through `simulate`-free exact pages and verifies it.
- [ ] **Step 2–4:** Run to fail, implement, run both test commands. Expected: PASS.
- [ ] **Step 5:** Commit: "Offers dot size and protection when putting a file on paper".

### Task 11: C comparison for larger dots, documentation, version

**Files:** Modify `tests/cbuild.py`, add a test under `tests/oracle/`; modify `README.md`, `CLAUDE.md`, `src/optar/__init__.py`.

- [ ] **Step 1: Oracle test** (marked `oracle`): `cbuild` gains an optional grid (`xcrosses`, `ycrosses`) applied to the temporary copy of `optar.h` it already builds from (text substitution in the copy; the repository's C files are not edited; if the copy cannot be patched cleanly the build raises `CBuildError`). Test: a wrapped Large A4 stream encoded by Python is byte-identical to C `optar` built with 33 × 46 for the same stream and label, and C `unoptar` returns the stream from Python's pages. If the C build cannot take the grid, skip with a reason and say so in the report and in the README's list of unproven points.
- [ ] **Step 2: README.** What dot size and protection are, the table of scan resolutions and capacities, what "can lose a page" means and when it is promised, that version-1 printouts need optar 0.3 or newer and how to make a compatible one, the new command-line options, scanner advice (true gray, no clean-up, PNG or TIFF), and the unproven points in one sentence each: no real scan has yet been read at any dot size; sheet-fed scanners are untested.
- [ ] **Step 3: CLAUDE.md.** Rules an assistant would break: pages stay version-0 pages and `encode()` is not changed for the container; header, spread and parity numbers live in `format.py`; a valid tag wins over a header; the claims tests are not to be loosened.
- [ ] **Step 4:** `__version__ = "0.3.0"`. Run `pytest -q`, `pytest -q -m "oracle or gs or slow"`, `QT_QPA_PLATFORM=offscreen pytest -q -m gui`, `ruff check .`. Expected: PASS; golden fixtures unchanged.
- [ ] **Step 5:** Commit: "Documents dot sizes and protection and compares larger-dot pages with C".
