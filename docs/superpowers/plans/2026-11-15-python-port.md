# Optar Python Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A tested Python library and `optar` command that encode files to print-ready pages and decode scans, compatible with the C tools, shipped as a one-file executable by GitHub Actions.

**Architecture:** A `src/optar` package where the page format is an immutable `PageFormat` object passed to every function. Encoder, error correction, layout, output writers and the decoder pipeline are separate modules; `cli.py` is the only code that prints or exits. The C sources stay at the repo root and act as the test oracle.

**Tech Stack:** Python 3.10+, numpy, Pillow, pytest, ruff, PyInstaller, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-15-python-port-design.md`. Read it before starting any task.

## Global Constraints

- Runtime dependencies are numpy and Pillow only. No scipy, no OpenCV, no compiled extension.
- Python 3.10 or newer.
- License GPL-2.0. Every new source file starts with `# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026`.
- Do not modify or move `optar.c`, `unoptar.c`, `common.c`, `golay.c`, `parity.c`, `optar.h`, `parity.h`, `font.h`, `Makefile`, `pgm2ps`. Tests build C in a temporary copy.
- Library modules never print, call `sys.exit`, or read `sys.argv`. Only `cli.py` does.
- No module except `format.py` contains a format number (65, 93, 24, 3, 2, 13, 200, paper sizes).
- The decoder reproduces the C algorithm and its seven constants. Do not retune or "improve" it.
- The default test run (`pytest`) must pass with no C compiler, no libpng and no Ghostscript. Tests that need them carry the `oracle` or `gs` marker and skip themselves.
- Tests write only under pytest's `tmp_path`. `make clean` deletes `*.pgm` and `*.ps` in the repo root.
- No JPEG output anywhere.
- Work on branch `python-port` of `mezinster/optar`. Do not push, and do not open a pull request, without the owner saying so.
- Commit subjects are capitalised, third-person present, no prefix: "Adds page format object".

**Reference values** (computed from `optar.h`; use them in tests):

| | A4 | US Letter |
|---|---|---|
| format string | `0-65-93-24-3-1-2-24` | `0-67-87-24-3-1-2-24` |
| page pixels (W x H) | 1546 x 2242 | 1594 x 2098 |
| `total_bits` | 3,196,368 | 3,081,456 |
| `fec_syms` (Golay) | 133,182 | 128,394 |
| `net_bits` (Golay) | 1,598,184 | 1,540,728 |
| image size in points | 556.56 x 807.12 | 573.84 x 755.28 |
| paper in points | 595.28 x 841.89 | 612 x 792 |
| image offset in points (x, y) | 19.20, 17.40 (snapped to the 600 dpi grid; pgm2ps used 19.22, 17.44) | 19.08, 18.36 |

A4 `net_bits` for Hamming orders 2, 3, 4, 5: 799,092; 1,598,184; 2,197,503; 2,597,036.

## Review Focus

Inputs the spec implies but does not spell out, most likely first. Each has a test in the task named.

1. **A scan that is not an optar page** (blank sheet, photo): `decode_page` raises `DecodeError` naming the corner it could not find; the CLI prints one line and exits 2, with no traceback. (Tasks 9, 13)
2. **Decoding with the wrong `--paper`:** no crash; the result reports uncorrectable codewords, and the CLI exits 1 with a hint to check `--paper`. (Task 13)
3. **A gap in the scan numbering** (`scan_0001.png`, `scan_0003.png`): the CLI decodes page 1, then warns on stderr that `scan_0003.png` exists but `scan_0002.png` is missing, and exits 1. C stops silently. (Task 13)
4. **Colour, 16-bit or alpha-channel scans:** `read_scan` returns the same array, to within 1 grey level, as for the 8-bit grayscale version. (Task 6)
5. **Awkward labels:** a label with non-ASCII characters or longer than the page is wide encodes without error; characters outside 32..127 are dropped and the text is cut at the page edge, as in C. (Task 5)

---

## File Structure

```
pyproject.toml                    package metadata, pytest and ruff config
src/optar/__init__.py             __version__, public re-exports
src/optar/__main__.py             python -m optar
src/optar/errors.py               OptarError, FormatError, DecodeError
src/optar/format.py               PageFormat, Paper, PAPERS, PIXELS_PER_INCH, TEXT_WIDTH
src/optar/fec.py                  Golay table, Golay and Hamming encode/decode
src/optar/layout.py               channel bit number -> pixel coordinates
src/optar/font.py                 glyph strip loading, label rendering
src/optar/data/font.png           1500 x 24 glyph strip extracted from font.h
src/optar/encoder.py              blank page, bit stream, encode()
src/optar/imageio.py              write_pgm, write_png, read_scan
src/optar/pdf.py                  write_pdf
src/optar/decoder/__init__.py     decode_page, decode, PageResult, PageStats, DecodeResult
src/optar/decoder/options.py      DecodeOptions
src/optar/decoder/levels.py       histogram and cut levels
src/optar/decoder/dirt.py         border dirt removal
src/optar/decoder/geometry.py     corners, pixel vectors
src/optar/decoder/crosses.py      cross synchronisation
src/optar/decoder/filters.py      min/max and blur
src/optar/decoder/sample.py       pixel sampling to channel bits
src/optar/cli.py                  argument parsing, files, console output
tools/extract_font.py             one-off: font.h -> font.png
tests/helpers.py                  seeded_bytes, fake_scan, pdf parsing
tests/conftest.py                 C build fixtures, markers
tests/unit/ tests/golden/ tests/oracle/ tests/scans/
packaging/entry.py                PyInstaller entry script
.github/workflows/ci.yml  .github/workflows/release.yml
```

---

### Task 1: Project skeleton and C build harness

**Files:**
- Create: `pyproject.toml`, `src/optar/__init__.py`, `src/optar/errors.py`, `tests/conftest.py`, `tests/helpers.py`, `tests/unit/test_skeleton.py`, `tests/oracle/test_harness.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces:
  - `optar.__version__: str` (`"0.1.0"`), the single version source; `pyproject.toml` reads it dynamically.
  - `optar.errors`: `OptarError(Exception)`, `FormatError(OptarError, ValueError)`, `DecodeError(OptarError)`.
  - `tests/helpers.py`: `seeded_bytes(seed: int, n: int) -> bytes`: SHA-256 in counter mode, block `i` is `sha256(f"{seed}:{i}".encode()).digest()`, concatenated and cut to `n`.
  - `tests/conftest.py` fixtures, session-scoped:
    - `c_build(format_overrides: dict[str, int] | None = None) -> CBuild` as a factory fixture. It copies the C sources to a temp directory, rewrites `#define NAME value` lines in the copied `optar.h` for each override (names `XCROSSES`, `YCROSSES`, `FEC_ORDER`), compiles with `cc` directly (not `make`): builds `golay`, runs it to produce `golay_codes.c`, links `optar`; links `unoptar` only if `png.h` is found via `libpng-config --I_opts` or `pkg-config --cflags libpng`. Results are cached per override set.
    - `CBuild` has `dir: Path`, `optar: Path`, `unoptar: Path | None`, `golay_codes_c: Path`.
    - Fixtures skip the requesting test when `cc` is missing; tests needing `unoptar` call `pytest.skip` when it is `None`.
  - Markers registered in `pyproject.toml`: `oracle` (needs C compiler), `gs` (needs Ghostscript), `slow`.
  - Extras: `pip install -e '.[dev]'` installs pytest, ruff, pyinstaller.

- [ ] **Step 1:** Create branch `python-port`. Commit the existing untracked `CLAUDE.md`, `.claude/` and `docs/` as "Adds Claude Code setup and Python port design".
- [ ] **Step 2:** Create the virtualenv: `python3 -m venv .venv && .venv/bin/pip install -U pip`. If `venv` is unavailable, stop and report; do not install into the system Python.
- [ ] **Step 3: Write the failing tests**

```python
# tests/unit/test_skeleton.py
def test_version_and_errors():
    import optar
    from optar.errors import OptarError, FormatError, DecodeError
    assert optar.__version__ == "0.1.0"
    assert issubclass(FormatError, OptarError) and issubclass(FormatError, ValueError)
    assert issubclass(DecodeError, OptarError)

def test_seeded_bytes_is_stable():
    from tests.helpers import seeded_bytes
    assert seeded_bytes(1, 40).hex().startswith(
        __import__("hashlib").sha256(b"1:0").hexdigest())
    assert len(seeded_bytes(7, 100_001)) == 100_001
    assert seeded_bytes(7, 10) == seeded_bytes(7, 100)[:10]

# tests/oracle/test_harness.py
import pytest
pytestmark = pytest.mark.oracle

def test_c_optar_builds_and_encodes(c_build, tmp_path):
    build = c_build()
    (tmp_path / "in.bin").write_bytes(b"hello")
    import subprocess
    subprocess.run([build.optar, "in.bin", "page"], cwd=tmp_path, check=True)
    assert (tmp_path / "page_0001.pgm").read_bytes().startswith(b"P5\n1546 2242\n255\n")

def test_c_build_with_letter_override(c_build, tmp_path):
    build = c_build({"XCROSSES": 67, "YCROSSES": 87})
    (tmp_path / "in.bin").write_bytes(b"hello")
    import subprocess
    subprocess.run([build.optar, "in.bin", "page"], cwd=tmp_path, check=True)
    assert (tmp_path / "page_0001.pgm").read_bytes().startswith(b"P5\n1594 2098\n255\n")
```

- [ ] **Step 4:** Run `.venv/bin/pytest -q`. Expected: FAIL, `ModuleNotFoundError: optar`.
- [ ] **Step 5:** Implement the files above. Add to `.gitignore`: `.venv/`, `dist/`, `build/`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/`, `.ruff_cache/`, `*.spec`.
- [ ] **Step 6:** Run `.venv/bin/pip install -e '.[dev]' && .venv/bin/pytest -q && .venv/bin/ruff check .`. Expected: all pass (oracle tests pass where `cc` exists).
- [ ] **Step 7:** Commit: "Adds Python project skeleton and C build harness".

---

### Task 2: Page format and paper

**Files:**
- Create: `src/optar/format.py`, `tests/unit/test_format.py`

**Interfaces:**
- Produces:
  - `PIXELS_PER_INCH = 200`, `TEXT_WIDTH = 13`.
  - `Paper` (frozen dataclass): `name: str`, `width_pt: float`, `height_pt: float`, `offset_x_pt: float` (from the left edge), `offset_y_pt: float` (from the bottom edge), `xcrosses: int`, `ycrosses: int`.
  - `PAPERS: dict[str, Paper]` with keys `"a4"` and `"letter"`, values from the reference table. `get_paper(name: str) -> Paper` is case-insensitive and raises `FormatError` for unknown names.
  - `PageFormat` (frozen dataclass, hashable): `xcrosses`, `ycrosses`, `cpitch=24`, `chalf=3`, `fec_order=1`, `border=2`, `text_height=24`, `version=0`.
    - Properties, each mirroring the macro of the same name in `optar.h`: `data_width`, `data_height`, `width`, `height`, `narrow_height`, `gap_width`, `narrow_width`, `narrow_pixels`, `wide_height`, `wide_width`, `wide_pixels`, `rep_height`, `rep_pixels`, `total_bits`, `fec_largebits`, `fec_smallbits`, `fec_syms`, `net_bits`, `used_bits`.
    - `PageFormat.parse(text: str) -> PageFormat`, `to_string() -> str`, `PageFormat.for_paper(paper: Paper) -> PageFormat`.
    - `fits(paper: Paper) -> bool`: the image at 200 pixels per inch plus its offsets fits inside the paper.
    - Validation in `__post_init__`, raising `FormatError`: `version == 0`; `fec_order` in 1..5; `xcrosses >= 2`; `ycrosses >= 2`; `chalf >= 1`; `cpitch > 2*chalf`; `border >= 1`; `text_height >= 1`.

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from optar.errors import FormatError
from optar.format import PageFormat, PAPERS, get_paper

A4 = "0-65-93-24-3-1-2-24"

def test_a4_derived_sizes():
    f = PageFormat.for_paper(PAPERS["a4"])
    assert f.to_string() == A4
    assert (f.width, f.height) == (1546, 2242)
    assert (f.total_bits, f.fec_syms, f.net_bits) == (3196368, 133182, 1598184)
    assert (f.fec_largebits, f.fec_smallbits) == (24, 12)

def test_letter_derived_sizes():
    f = PageFormat.for_paper(get_paper("Letter"))
    assert f.to_string() == "0-67-87-24-3-1-2-24"
    assert (f.width, f.height, f.total_bits, f.net_bits) == (1594, 2098, 3081456, 1540728)

@pytest.mark.parametrize("order,net", [(2, 799092), (3, 1598184), (4, 2197503), (5, 2597036)])
def test_hamming_net_bits(order, net):
    assert PageFormat(65, 93, fec_order=order).net_bits == net

def test_parse_round_trip_and_hashable():
    f = PageFormat.parse(A4)
    assert f == PageFormat.for_paper(PAPERS["a4"]) and hash(f) == hash(PageFormat.parse(A4))
    assert PageFormat.parse(f.to_string()) == f

@pytest.mark.parametrize("bad", ["", "0-65-93", "1-65-93-24-3-1-2-24", "0-65-93-24-3-6-2-24",
                                 "0-1-93-24-3-1-2-24", "0-65-93-6-3-1-2-24", "0-a-93-24-3-1-2-24"])
def test_bad_format_rejected(bad):
    with pytest.raises(FormatError):
        PageFormat.parse(bad)

def test_paper_placement_and_fit():
    a4 = PAPERS["a4"]
    assert (a4.width_pt, a4.height_pt, a4.offset_x_pt, a4.offset_y_pt) == (595.28, 841.89, 19.22, 17.44)
    assert PageFormat.for_paper(a4).fits(a4)
    assert not PageFormat(80, 93).fits(a4)
    with pytest.raises(FormatError):
        get_paper("legal")
```

- [ ] **Step 2:** Run `pytest tests/unit/test_format.py -q`. Expected: FAIL on import.
- [ ] **Step 3:** Implement `format.py`. Copy each derived formula from `optar.h` lines 16-64.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit: "Adds page format and paper presets".

---

### Task 3: Error correction

**Files:**
- Create: `src/optar/fec.py`, `tests/unit/test_fec.py`

**Interfaces:**
- Consumes: `PageFormat.fec_order`, `fec_largebits`, `fec_smallbits`.
- Produces:
  - `golay_table() -> np.ndarray`, shape `(4096,)`, dtype `uint32`, cached. Entry `d` is `(d << 12) | parity12`, built exactly as `golay.c` does (dodecahedron masks, `prty` shifted in most significant first).
  - `encode_symbols(words: np.ndarray, fmt: PageFormat) -> np.ndarray` (`uint32` in, `uint32` out). Order 1 is a table lookup; orders 2 to 5 port `hamming()` and `split()` from `optar.c:53-87`.
  - `decode_symbols(codewords: np.ndarray, fmt: PageFormat) -> tuple[np.ndarray, np.ndarray]`: `(words uint32, errors int8)`. `errors` is the number of bits corrected in that symbol, or `-1` if uncorrectable. Golay: nearest codeword within distance 3 (`unoptar.c:1031-1067`); uncorrectable returns `codeword >> 12`. Hamming: port `unhamming()` and `shrink()` (`unoptar.c:887-896`, `1074-1129`); a corrected single bit or a flipped parity bit counts as 1; uncorrectable returns the C value.
  - `serialize_table(table: np.ndarray) -> bytes`: each entry as 4 big-endian bytes, concatenated. Used for the golden hash.

- [ ] **Step 1: Write the failing tests**

```python
import numpy as np, pytest
from optar.fec import golay_table, encode_symbols, decode_symbols
from optar.format import PageFormat

G = PageFormat(65, 93)

def test_golay_table_shape_and_weights():
    t = golay_table()
    assert t.shape == (4096,) and t.dtype == np.uint32
    assert np.array_equal(t >> 12, np.arange(4096))
    weights = {bin(int(v)).count("1") for v in t}
    assert weights <= {0, 8, 12, 16, 24}

def test_golay_minimum_distance_is_8():
    t = golay_table().astype(np.uint32)
    x = t[:, None] ^ t[None, :256]          # linear code: distances to 256 words suffice
    pop = np.array([bin(i).count("1") for i in range(4096)], dtype=np.uint8)
    d = pop[x >> 12] + pop[x & 0xFFF]
    assert d[d > 0].min() == 8

@pytest.mark.parametrize("nerr", [0, 1, 2, 3])
def test_golay_corrects_up_to_three_errors(nerr):
    rng = np.random.default_rng(nerr)
    words = rng.integers(0, 4096, 2000, dtype=np.uint32)
    cw = encode_symbols(words, G)
    for i in range(len(cw)):
        for b in rng.choice(24, nerr, replace=False):
            cw[i] ^= np.uint32(1 << int(b))
    out, errs = decode_symbols(cw, G)
    assert np.array_equal(out, words) and np.all(errs == nerr)

def test_golay_four_errors_reported_uncorrectable():
    cw = encode_symbols(np.array([0x123], dtype=np.uint32), G)
    cw[0] ^= np.uint32(0b1111)
    out, errs = decode_symbols(cw, G)
    assert errs[0] == -1 and out[0] == cw[0] >> 12

@pytest.mark.parametrize("order", [2, 3, 4, 5])
def test_hamming_round_trip_and_single_error(order):
    f = PageFormat(65, 93, fec_order=order)
    words = np.arange(1 << min(f.fec_smallbits, 12), dtype=np.uint32)
    cw = encode_symbols(words, f)
    assert np.all(cw < (1 << f.fec_largebits))
    out, errs = decode_symbols(cw.copy(), f)
    assert np.array_equal(out, words) and np.all(errs == 0)
    for bit in range(f.fec_largebits):
        out, errs = decode_symbols(cw ^ np.uint32(1 << bit), f)
        assert np.array_equal(out, words) and np.all(errs == 1)
```

- [ ] **Step 2:** Run `pytest tests/unit/test_fec.py -q`. Expected: FAIL on import.
- [ ] **Step 3:** Implement `fec.py`. Golay decoding must be vectorised for the clean case (compare `table[cw >> 12] == cw`) and only search for the symbols that differ.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit: "Adds Golay and Hamming error correction".

---

### Task 4: Bit layout

**Files:**
- Create: `src/optar/layout.py`, `tests/unit/test_layout.py`

**Interfaces:**
- Consumes: `PageFormat` geometry properties.
- Produces:
  - `channel_xy(fmt: PageFormat) -> tuple[np.ndarray, np.ndarray]`: `x` and `y` (`int32`, length `fmt.total_bits`) for channel bit numbers `0..total_bits-1`, relative to the top-left pixel of the top-left cross (no border), exactly as `seq2xy` in `common.c:18-64`. Cached per format; the arrays are read-only.
  - `is_cross(fmt: PageFormat, x, y) -> np.ndarray` (bool), as `common.c:9-14`.

- [ ] **Step 1: Write the failing tests**

```python
import numpy as np
from optar.format import PageFormat
from optar.layout import channel_xy, is_cross

F = PageFormat(65, 93)

def test_every_bit_has_a_distinct_data_pixel():
    x, y = channel_xy(F)
    assert len(x) == len(y) == F.total_bits == 3196368
    assert x.min() == 0 and y.min() == 0
    assert x.max() == F.data_width - 1 and y.max() == F.data_height - 1
    assert not is_cross(F, x, y).any()
    assert len(np.unique(y.astype(np.int64) * F.data_width + x)) == F.total_bits

def test_data_pixels_plus_cross_pixels_fill_the_data_area():
    cross_pixels = F.xcrosses * F.ycrosses * (2 * F.chalf) ** 2
    assert F.total_bits + cross_pixels == F.data_width * F.data_height

def test_first_positions_match_seq2xy():
    x, y = channel_xy(F)
    assert (x[0], y[0]) == (6, 0)            # first gap, after the first cross
    assert (x[17], y[17]) == (23, 0) and (x[18], y[18]) == (30, 0)   # jumps the next cross
    n = F.narrow_pixels
    assert (x[n], y[n]) == (0, 6)            # first wide strip starts at the left edge

def test_arrays_are_read_only():
    x, _ = channel_xy(F)
    assert not x.flags.writeable
```

- [ ] **Step 2:** Run `pytest tests/unit/test_layout.py -q`. Expected: FAIL on import.
- [ ] **Step 3:** Implement `layout.py`, vectorised over `np.arange(total_bits)`.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit: "Adds channel bit layout".

---

### Task 5: Label font and encoder

**Files:**
- Create: `tools/extract_font.py`, `src/optar/data/font.png`, `src/optar/font.py`, `src/optar/encoder.py`, `tests/unit/test_font.py`, `tests/unit/test_encoder.py`

**Interfaces:**
- Consumes: `PageFormat`, `TEXT_WIDTH`, `encode_symbols`, `channel_xy`.
- Produces:
  - `tools/extract_font.py`: parses `font.h` (`header_data_cmap[256][3]` at line 14, `header_data[36000]` at line 272, 1500 x 24) and writes `src/optar/data/font.png` as a 1-bit image where a pixel is white when `cmap[index][0] & 0x80`.
  - `font.glyph_strip() -> np.ndarray`: `(24, 1500)` `uint8`, values 0 or 255, loaded with `importlib.resources`, cached.
  - `font.label_text(fmt: PageFormat, page: int, total: int, label: str) -> str`: `f"  {fmt.to_string()} {page}/{total} {label}"`, cut to `fmt.data_width // TEXT_WIDTH - 1` characters (C's `snprintf` into a buffer of `DATA_WIDTH/TEXT_WIDTH`).
  - `font.render_label(fmt: PageFormat, text: str) -> np.ndarray`: `(fmt.text_height, fmt.data_width)`, as `label()` and `text_block()` in `optar.c:136-180`: first the 265-pixel logo block from strip column 1235, then one 13-pixel glyph per character in 32..127 taken from column `13*(c-32)`; other characters are skipped; a glyph that would cross `data_width` is not drawn. The background is black (0): `border()` blacks the whole label band before the glyphs are drawn, and glyph pixels are 255 where the colour map has bit 7 set. Raises `FormatError` if `fmt.text_height != 24`.
  - `encoder.Page` (frozen dataclass): `number: int` (1-based), `total: int`, `pixels: np.ndarray` (`uint8`, `(fmt.height, fmt.width)`).
  - `encoder.page_count(nbytes: int, fmt: PageFormat) -> int`: `ceil(nbytes*8 / net_bits)` (0 for an empty file, as in C).
  - `encoder.blank_page(fmt: PageFormat, label_text: str) -> np.ndarray`: white page, black border, crosses, label (`optar.c:89-185`).
  - `encoder.encode(data: bytes | BinaryIO, fmt: PageFormat, label: str = "") -> Iterator[Page]`. A stream must be seekable (its length sets `total`). Raises `OptarError` if more than 9,999 pages are needed.

**Bit stream rules** (from `optar.c:214-270`; these decide byte identity):
- Bytes are consumed most significant bit first into `fec_smallbits`-bit words, most significant bit first, continuously across pages.
- After the last byte, a trailing partial word is completed with zero bits. No extra word is added when the data ends on a word boundary.
- Word `s` of a page becomes codeword `c`; bit `b` of `c` counted from the most significant (`b = 0..fec_largebits-1`) is written to channel position `s + b*fec_syms`. Black (0) is 1, white (255) is 0. Pixel = `(x + border, y + border)`.
- A page holds `fec_syms` words. A new page starts only when another word arrives, so data of exactly `net_bits` bits gives one page, and an empty file gives one blank page labelled `1/0`.
- Channel positions never written stay white.

- [ ] **Step 1:** Run `python tools/extract_font.py` after writing it; commit the generated `font.png` with the code.
- [ ] **Step 2: Write the failing tests**

```python
# tests/unit/test_font.py
import re, numpy as np
from pathlib import Path
from optar.font import glyph_strip, label_text, render_label
from optar.format import PageFormat

F = PageFormat(65, 93)

def test_strip_matches_font_h():
    src = Path(__file__).parents[2].joinpath("font.h").read_text(errors="replace")
    cmap_txt = src[src.index("header_data_cmap[256][3]"):src.index("header_data[36000]")]
    cmap = [int(m) for m in re.findall(r"\{\s*(-?\d+),", cmap_txt)]
    body = src[src.index("header_data[36000]"):]
    data = np.array([int(m) for m in re.findall(r"-?\d+", body[body.index("{"):])][:36000])
    expect = np.where(np.array(cmap)[data % 256] & 0x80, 255, 0).reshape(24, 1500)
    assert np.array_equal(glyph_strip(), expect)

def test_label_text():
    assert label_text(F, 1, 2, "name") == "  0-65-93-24-3-1-2-24 1/2 name"
    assert len(label_text(F, 1, 2, "x" * 500)) == F.data_width // 13 - 1

def test_render_label_shape_and_odd_characters():
    img = render_label(F, label_text(F, 1, 1, "naïve ☃ ok"))
    assert img.shape == (24, F.data_width) and set(np.unique(img)) <= {0, 255}
    assert np.array_equal(img, render_label(F, label_text(F, 1, 1, "nave  ok")))

# tests/unit/test_encoder.py
import io, numpy as np, pytest
from optar.encoder import encode, page_count, blank_page
from optar.format import PageFormat
from optar.layout import channel_xy, is_cross
from tests.helpers import seeded_bytes

F = PageFormat(65, 93)
PAGE_BYTES = F.net_bits // 8        # 199773

def test_page_counts():
    assert [page_count(n, F) for n in (0, 1, PAGE_BYTES, PAGE_BYTES + 1)] == [0, 1, 1, 2]
    assert [p.number for p in encode(b"", F)] == [1]
    assert len(list(encode(seeded_bytes(1, PAGE_BYTES), F))) == 1
    pages = list(encode(seeded_bytes(1, PAGE_BYTES + 1), F))
    assert [(p.number, p.total) for p in pages] == [(1, 2), (2, 2)]

def test_blank_page_structure():
    p = blank_page(F, "")
    assert p.shape == (2242, 1546) and p.dtype == np.uint8
    assert not p[:2].any() and not p[:, :2].any() and not p[:, -2:].any() and not p[-2:].any()
    assert np.array_equal(p[2:8, 2:8] == 0, np.kron(np.eye(2, dtype=bool), np.ones((3, 3), bool)))
    x, y = channel_xy(F)
    assert (p[y + 2, x + 2] == 255).all()

def test_all_ones_data_blackens_written_symbols_only():
    page = next(encode(b"\xff" * 3, F))          # 24 bits = 2 words of 0xFFF
    x, y = channel_xy(F)
    bits = page.pixels[y + 2, x + 2] == 0
    idx = np.flatnonzero(bits)
    assert len(idx) == 48 and set(idx % F.fec_syms) == {0, 1}

def test_stream_input_equals_bytes_input():
    data = seeded_bytes(3, 5000)
    a = [p.pixels for p in encode(data, F)]
    b = [p.pixels for p in encode(io.BytesIO(data), F)]
    assert all(np.array_equal(i, j) for i, j in zip(a, b))
```

- [ ] **Step 3:** Run `pytest tests/unit/test_font.py tests/unit/test_encoder.py -q`. Expected: FAIL on import.
- [ ] **Step 4:** Implement `font.py` and `encoder.py`. Use `np.unpackbits` for the bit stream and fancy indexing with `channel_xy` to place a page's bits in one assignment.
- [ ] **Step 5:** Run the tests. Expected: PASS.
- [ ] **Step 6:** Commit: "Adds label font and page encoder".

---

### Task 6: Image files

**Files:**
- Create: `src/optar/imageio.py`, `tests/unit/test_imageio.py`

**Interfaces:**
- Consumes: `PIXELS_PER_INCH`.
- Produces:
  - `pgm_bytes(pixels: np.ndarray) -> bytes`: `b"P5\n%d %d\n255\n"` plus raw rows, byte-identical to `dump_ary` in `optar.c:30-39`. `write_pgm(path, pixels) -> None`.
  - `write_png(path, pixels) -> None`: 1-bit grayscale PNG with resolution 200 pixels per inch.
  - `read_scan(path) -> np.ndarray`: `uint8`, 2-D, linear light, as `read_png` in `unoptar.c:1496-1574`: palette and RGB are converted to gray with libpng's default weights (0.212671, 0.715160, 0.072169), alpha is dropped, 16-bit is cut to 8 bits, then every value goes through the table `floor(255 * (v/255) ** (1/g) + 0.5)` where `g` is the file's gAMA value or 0.454545 when absent. Any file Pillow can open is accepted. Raises `OptarError` if the file cannot be read.

- [ ] **Step 1: Write the failing tests**

```python
import numpy as np, pytest
from PIL import Image
from optar.imageio import pgm_bytes, write_png, read_scan

def gradient():
    return np.tile(np.arange(256, dtype=np.uint8), (4, 1))

def test_pgm_bytes():
    px = np.array([[0, 255, 7], [1, 2, 3]], dtype=np.uint8)
    assert pgm_bytes(px) == b"P5\n3 2\n255\n" + bytes([0, 255, 7, 1, 2, 3])

def test_png_is_one_bit_at_200_ppi(tmp_path):
    px = (np.indices((5, 9)).sum(0) % 2 * 255).astype(np.uint8)
    write_png(tmp_path / "p.png", px)
    im = Image.open(tmp_path / "p.png")
    assert im.mode == "1" and [round(v) for v in im.info["dpi"]] == [200, 200]
    assert np.array_equal(np.array(im.convert("L")), px)

def test_read_scan_linearises_with_default_gamma(tmp_path):
    Image.fromarray(gradient()).save(tmp_path / "g.png")
    out = read_scan(tmp_path / "g.png")
    v = np.arange(256)
    assert out.dtype == np.uint8 and out.shape == (4, 256)
    assert np.array_equal(out[0], np.floor(255 * (v / 255) ** (1 / 0.454545) + 0.5).astype(np.uint8))
    assert out[0, 0] == 0 and out[0, 255] == 255

@pytest.mark.parametrize("mode", ["RGB", "RGBA", "I;16", "P"])
def test_colour_and_deep_scans_match_gray(tmp_path, mode):
    g = Image.fromarray(gradient())
    g.save(tmp_path / "g.png")
    im = Image.fromarray(gradient().astype(np.uint16) * 257) if mode == "I;16" else g.convert(mode)
    im.save(tmp_path / "c.png")
    a, b = read_scan(tmp_path / "g.png").astype(int), read_scan(tmp_path / "c.png").astype(int)
    assert np.abs(a - b).max() <= 1

def test_unreadable_file(tmp_path):
    from optar.errors import OptarError
    (tmp_path / "x.png").write_bytes(b"not an image")
    with pytest.raises(OptarError):
        read_scan(tmp_path / "x.png")
```

- [ ] **Step 2:** Run `pytest tests/unit/test_imageio.py -q`. Expected: FAIL on import.
- [ ] **Step 3:** Implement `imageio.py`.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit: "Adds PGM, PNG and scan reading".

---

### Task 7: Golden and oracle tests for the encoder

**Files:**
- Create: `tests/golden/make_fixtures.py`, `tests/golden/fixtures.json`, `tests/golden/test_golden.py`, `tests/oracle/seq2xy_dump.c`, `tests/oracle/test_encoder_oracle.py`

**Interfaces:**
- Consumes: `c_build`, `seeded_bytes`, `encode`, `pgm_bytes`, `golay_table`, `serialize_table`, `channel_xy`.
- Produces: `tests/golden/fixtures.json`:

```json
{"c_commit": "<git rev-parse HEAD>",
 "golay_sha256": "<sha256 of serialize_table of the C table>",
 "seq2xy": {"0-65-93-24-3-1-2-24": [[seq, x, y], ...]},
 "pages": [{"name": "...", "format": "...", "seed": 0, "size": 0, "label": "",
            "sha256": ["<sha256 of page_0001.pgm>", ...]}]}
```

Page cases, each for A4, plus `one_byte` and `two_pages` for Letter: `empty` (size 0), `one_byte` (1), `exact_page` (`net_bits // 8`), `page_plus_one` (`net_bits // 8 + 1`), `two_pages` (300,000), `labelled` (5,000, label `"my label"`). Seed is the case's index. C is run as `optar in.bin` for an empty label and `optar in.bin "my label"` for the labelled case. `seq2xy` holds 2,000 values of `seq` chosen by `seeded_bytes`, produced by `seq2xy_dump.c` linked against the C `common.o`.

- [ ] **Step 1:** Write `make_fixtures.py` (run as `python -m tests.golden.make_fixtures`, uses the same build code as `conftest.py`) and generate `fixtures.json`.
- [ ] **Step 2: Write the tests**

```python
# tests/golden/test_golden.py
import hashlib, json
from pathlib import Path
import pytest
from optar.encoder import encode
from optar.fec import golay_table, serialize_table
from optar.format import PageFormat
from optar.imageio import pgm_bytes
from optar.layout import channel_xy
from tests.helpers import seeded_bytes

FX = json.loads(Path(__file__).with_name("fixtures.json").read_text())

def test_golay_table_matches_c():
    assert hashlib.sha256(serialize_table(golay_table())).hexdigest() == FX["golay_sha256"]

@pytest.mark.parametrize("fmt", FX["seq2xy"])
def test_layout_matches_c(fmt):
    x, y = channel_xy(PageFormat.parse(fmt))
    for seq, cx, cy in FX["seq2xy"][fmt]:
        assert (x[seq], y[seq]) == (cx, cy)

@pytest.mark.parametrize("case", FX["pages"], ids=lambda c: f'{c["name"]}-{c["format"]}')
def test_pages_match_c(case):
    fmt = PageFormat.parse(case["format"])
    pages = encode(seeded_bytes(case["seed"], case["size"]), fmt, case["label"])
    got = [hashlib.sha256(pgm_bytes(p.pixels)).hexdigest() for p in pages]
    assert got == case["sha256"]
```

`tests/oracle/test_encoder_oracle.py` (marker `oracle`): for A4, Letter, and A4 with each `FEC_ORDER` 2 to 5, build C with the matching overrides, encode `seeded_bytes(seed, size)` for sizes 0, 1, 777 and `2 * net_bits // 8 + 5` with both encoders, and assert the page files are byte-identical and equal in number.

- [ ] **Step 3:** Run `pytest tests/golden tests/oracle -q`. Expected: PASS. A failure here is a bug in Tasks 3 to 6; fix it there, not in the fixture.
- [ ] **Step 4:** Commit: "Adds golden fixtures and encoder oracle tests".

---

### Task 8: Print-ready PDF

**Files:**
- Create: `src/optar/pdf.py`, `tests/unit/test_pdf.py`
- Modify: `tests/helpers.py`

**Interfaces:**
- Consumes: `Paper`, `PIXELS_PER_INCH`.
- Produces:
  - `write_pdf(path, pages: Iterable[np.ndarray], paper: Paper) -> int` (pages written). Standard library only (`zlib`). One PDF page per image, `/MediaBox [0 0 W H]` equal to the paper. Each image is an XObject with `/Width`, `/Height`, `/ColorSpace /DeviceGray`, `/BitsPerComponent 1`, `/Filter /FlateDecode`, `/Interpolate false`; rows are packed most significant bit first and padded to a whole byte; 1 is white. The page content stream is exactly `q {w:.2f} 0 0 {h:.2f} {x:.2f} {y:.2f} cm /Im0 Do Q`, where `w = pixels_wide * 72 / 200`, `h = pixels_high * 72 / 200`, and `x`, `y` are the paper's offsets. Pages are consumed lazily, one at a time. A valid cross-reference table is required.
  - `tests/helpers.parse_pdf(path) -> list[dict]`: one dict per page with `mediabox: tuple[float, ...]`, `cm: tuple[float, ...]` (the six numbers before `cm`), `width`, `height`, `bits`, `interpolate: bool`, `filter: str`, `pixels: np.ndarray` (decompressed and unpacked to 0/255). A regex-based reader for this writer's output is enough.

- [ ] **Step 1: Write the failing tests**

```python
import numpy as np, pytest
from optar.encoder import encode
from optar.format import PageFormat, PAPERS
from optar.pdf import write_pdf
from tests.helpers import parse_pdf, seeded_bytes

@pytest.mark.parametrize("name,cm", [
    ("a4", (556.56, 0, 0, 807.12, 19.22, 17.44)),
    ("letter", (573.84, 0, 0, 755.28, 19.08, 18.36)),
])
def test_pdf_page_geometry_and_pixels(tmp_path, name, cm):
    paper = PAPERS[name]
    fmt = PageFormat.for_paper(paper)
    pages = [p.pixels for p in encode(seeded_bytes(1, fmt.net_bits // 8 + 10), fmt)]
    assert write_pdf(tmp_path / "o.pdf", iter(pages), paper) == 2
    raw = (tmp_path / "o.pdf").read_bytes()
    assert raw.startswith(b"%PDF-1.") and raw.rstrip().endswith(b"%%EOF") and b"DCTDecode" not in raw
    parsed = parse_pdf(tmp_path / "o.pdf")
    assert len(parsed) == 2
    for got, want in zip(parsed, pages):
        assert got["mediabox"] == pytest.approx((0, 0, paper.width_pt, paper.height_pt), abs=0.01)
        assert got["cm"] == pytest.approx(cm, abs=0.01)
        assert (got["width"], got["height"], got["bits"]) == (fmt.width, fmt.height, 1)
        assert got["filter"] == "FlateDecode" and got["interpolate"] is False
        assert np.array_equal(got["pixels"], want)

def test_xref_offsets_point_at_objects(tmp_path):
    fmt = PageFormat.for_paper(PAPERS["a4"])
    write_pdf(tmp_path / "o.pdf", (p.pixels for p in encode(b"x", fmt)), PAPERS["a4"])
    raw = (tmp_path / "o.pdf").read_bytes()
    start = int(raw[raw.rindex(b"startxref") + 9:].split()[0])
    assert raw[start:start + 4] == b"xref"
    lines = raw[start:].split(b"\n")
    count = int(lines[1].split()[1])
    for n, line in enumerate(lines[3:2 + count], start=1):
        off = int(line[:10])
        assert raw[off:].startswith(b"%d 0 obj" % n)
```

- [ ] **Step 2:** Run `pytest tests/unit/test_pdf.py -q`. Expected: FAIL on import.
- [ ] **Step 3:** Implement `pdf.py` and `parse_pdf`.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit: "Adds print-ready PDF writer".

---

### Task 9: Decoder part 1: levels, dirt, corners

**Files:**
- Create: `src/optar/decoder/__init__.py` (empty for now), `options.py`, `levels.py`, `dirt.py`, `geometry.py`, `tests/unit/test_decoder_prepare.py`
- Modify: `tests/helpers.py`

**Interfaces:**
- Consumes: `PageFormat`, `DecodeError`.
- Produces:
  - `options.DecodeOptions` (frozen dataclass), defaults from `unoptar.c:104-123`: `unsharp_mask=7.0`, `unsharp_dist=1.0`, `sync_white_cut=0.10`, `white_cut=0.06`, `minmax_filter=0.5`, `pixel_blur=0.25`, `cross_trim=0.75`.
  - `levels.Levels` (frozen): `average: int`, `cut: int`, `fill_cut: int`. `levels.analyze_levels(img, opts) -> Levels`: `calc_histogram` and `analyze_cutlevel` (`unoptar.c:181-250`), at most 32 iterations, using `np.float32` for the sums as C does.
  - `dirt.remove_border_dirt(img, fill_cut: int) -> np.ndarray`: a new array, as `remove_dirt_from_border` (`unoptar.c:1421-1493`). Region A: pixels `>= fill_cut` 4-connected to any of the eight seeds (four corners, four edge midpoints). Region B: every pixel not in A that is 4-connected, through pixels not in A, to the image centre. Pixels in neither region are set to 255. Numpy only; a per-pixel Python loop is not acceptable on a 35-megapixel scan.
  - `geometry.find_corners(img, cut: int) -> np.ndarray`: shape `(4, 2)`, `int64`, rows UL, UR, LL, LR as `(x, y)`, as `diag_scan` and `find_corners` (`unoptar.c:254-378`), including the `+1` on the right and bottom coordinates. Raises `DecodeError("cannot find upper left corner")` and likewise for `upper right`, `lower left`, `lower right`.
  - `geometry.Geometry` (frozen): `corners`, `hpixel: float`, `vpixel: float`, `ph: tuple[float, float]`, `pv: tuple[float, float]` (unit vectors), `chalf: int`, `chalf_fine: int`. `geometry.compute_geometry(corners, fmt, opts) -> Geometry` as `unoptar.c:380-428`. **Keep C's quirk:** `hpixel = (c[1].x + c[3].x - c[0].x - c[0].x) / 2 / fmt.width` (corner 0 twice). `vpixel` divides by `fmt.height`. `chalf` and `chalf_fine` truncate toward zero.
  - `tests/helpers.fake_scan(pixels, *, scale=3, margin=60, rotate=0.0, blur=0.0, noise=0.0, specks=0, flips=0, seed=0) -> np.ndarray`: repeats pixels `scale` times, adds a white margin of `margin` scan pixels, then optionally rotates by `rotate` degrees (bicubic, white fill), applies a Gaussian blur of radius `blur`, adds Gaussian noise of standard deviation `noise`, draws `specks` black 4 x 4 squares in the margin, and inverts `flips` random data cells. Deterministic for a given seed. `save_scan(path, array)` writes it as an 8-bit grayscale PNG.

- [ ] **Step 1: Write the failing tests**

```python
import numpy as np, pytest
from optar.decoder.dirt import remove_border_dirt
from optar.decoder.geometry import compute_geometry, find_corners
from optar.decoder.levels import analyze_levels
from optar.decoder.options import DecodeOptions
from optar.encoder import encode
from optar.errors import DecodeError
from optar.format import PageFormat
from tests.helpers import fake_scan, seeded_bytes

F = PageFormat(65, 93)
OPTS = DecodeOptions()

@pytest.fixture(scope="module")
def page():
    return next(encode(seeded_bytes(5, 20000), F)).pixels

def test_levels_on_black_and_white_image(page):
    lv = analyze_levels(fake_scan(page), OPTS)
    assert 0 < lv.cut < lv.fill_cut < 255
    assert lv.fill_cut in (127, 128)

def test_corners_scale_3_with_margin(page):
    scan = fake_scan(page, scale=3, margin=60)
    c = find_corners(scan, analyze_levels(scan, OPTS).cut)
    assert c.tolist() == [[60, 60], [60 + 1546 * 3, 60], [60, 60 + 2242 * 3], [60 + 1546 * 3, 60 + 2242 * 3]]
    g = compute_geometry(c, F, OPTS)
    assert g.hpixel == pytest.approx(3.0) and g.vpixel == pytest.approx(3.0)
    assert g.ph == pytest.approx((1, 0)) and g.pv == pytest.approx((0, 1))
    assert (g.chalf, g.chalf_fine) == (4, 6)

def test_blank_image_raises():
    with pytest.raises(DecodeError, match="upper left corner"):
        find_corners(np.full((400, 300), 255, np.uint8), 128)

def test_dirt_in_margin_removed_page_untouched(page):
    clean = fake_scan(page, margin=60)
    dirty = fake_scan(page, margin=60, specks=25, seed=3)
    assert (clean != dirty).any()
    assert np.array_equal(remove_border_dirt(dirty, 128), clean)

def test_dirt_removal_matches_reference_flood_fill():
    rng = np.random.default_rng(0)
    img = np.where(rng.random((60, 70)) < 0.45, 0, 255).astype(np.uint8)
    img[20:40, 20:50] = 0
    from tests.helpers import reference_remove_border_dirt   # plain BFS port of the C code
    assert np.array_equal(remove_border_dirt(img, 128), reference_remove_border_dirt(img, 128))
```

Add `reference_remove_border_dirt` to `tests/helpers.py`: a direct queue-based port of `fill`, `try_copy_white` and `erase_dirt`, for small images only.

- [ ] **Step 2:** Run `pytest tests/unit/test_decoder_prepare.py -q`. Expected: FAIL on import.
- [ ] **Step 3:** Implement the four modules. For `dirt.py`, propagate reachability along whole row and column runs per iteration until nothing changes; a clean scan converges in a handful of iterations.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit: "Adds decoder levels, dirt removal and corner finding".

---

### Task 10: Decoder part 2: cross synchronisation

**Files:**
- Create: `src/optar/decoder/crosses.py`, `tests/unit/test_decoder_crosses.py`

**Interfaces:**
- Consumes: `Geometry`, `Levels`, `DecodeOptions`, `PageFormat`.
- Produces:
  - `crosses.interp(img, x, y) -> np.ndarray` (`float32`): `get_pixel_interp` (`unoptar.c:481-494`) for arrays of coordinates with integers at pixel centres: for a negative coordinate the integer part is 0 and the weight is the (negative) coordinate itself, so the value is extrapolated, as in C; any neighbour outside the image reads as 255; bilinear weights in `float32`. Task 11 reuses it.
  - `crosses.sync_crosses(img, geom, fmt, levels, opts) -> tuple[np.ndarray, np.ndarray]`: `positions` `(xcrosses, ycrosses, 2)` `float64` (cross centres, integers at pixel corners) and `cutlevels` `(xcrosses, ycrosses)` `float32`. Port of `sync_crosses`, `resync_cross`, `load_search_area`, `integrate_search_area`, `cross_correl_search`, `cross_correl`, `cross_stats` (`unoptar.c:534-833`).

**Rules that decide the result:**
- Crosses are visited row by row, left to right. A cross's starting estimate is the already-resynced cross to its left plus the `right` pitch vector, or for the first in a row the one above plus `down`. The loop over crosses is therefore sequential; vectorise inside one cross, not across crosses.
- Coarse search: offsets `-chalf..chalf` in both axes, strict `>` comparison, `x` outer loop and `y` inner, starting from the value at offset (0, 0). Fine search: offsets `-2..2` in steps of 0.25 pixel, same ordering, starting from the value at the coarse maximum, using `chalf_fine`.
- `cross_stats` truncates each sample to an integer before comparing with `levels.cut` (C assigns the float to a `long`).

- [ ] **Step 1: Write the failing tests**

```python
import numpy as np, pytest
from optar.decoder.crosses import interp, sync_crosses
from optar.decoder.geometry import compute_geometry, find_corners
from optar.decoder.levels import analyze_levels
from optar.decoder.options import DecodeOptions
from optar.encoder import encode
from optar.format import PageFormat
from tests.helpers import fake_scan, seeded_bytes

F, OPTS = PageFormat(65, 93), DecodeOptions()

def prepared(**kw):
    scan = fake_scan(next(encode(seeded_bytes(5, 20000), F)).pixels, **kw)
    lv = analyze_levels(scan, OPTS)
    return scan, lv, compute_geometry(find_corners(scan, lv.cut), F, OPTS)

def test_interp_edges():
    img = np.array([[0, 100], [200, 50]], dtype=np.uint8)
    assert interp(img, np.array([0.5]), np.array([0.0]))[0] == pytest.approx(50)
    assert interp(img, np.array([-3.0]), np.array([0.0]))[0] == pytest.approx(-300)   # extrapolated
    assert interp(img, np.array([1.5]), np.array([0.0]))[0] == pytest.approx(177.5)   # 100 and 255

@pytest.mark.parametrize("scale", [1, 3])
def test_crosses_on_clean_scan(scale):
    scan, lv, g = prepared(scale=scale, margin=60)
    pos, cuts = sync_crosses(scan, g, F, lv, OPTS)
    assert pos.shape == (65, 93, 2) and cuts.shape == (65, 93) and cuts.dtype == np.float32
    cx, cy = np.meshgrid(np.arange(65), np.arange(93), indexing="ij")
    want_x = 60 + (2 + 3 + 24 * cx) * scale
    want_y = 60 + (2 + 3 + 24 * cy) * scale
    assert np.abs(pos[..., 0] - want_x).max() <= 0.25
    assert np.abs(pos[..., 1] - want_y).max() <= 0.25

def test_crosses_follow_a_small_rotation():
    scan, lv, g = prepared(scale=3, margin=120, rotate=0.4)
    pos, _ = sync_crosses(scan, g, F, lv, OPTS)
    step = np.diff(pos, axis=0)
    assert np.allclose(np.hypot(step[..., 0], step[..., 1]), 72, atol=0.6)
```

- [ ] **Step 2:** Run `pytest tests/unit/test_decoder_crosses.py -q`. Expected: FAIL on import.
- [ ] **Step 3:** Implement `crosses.py`.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit: "Adds decoder cross synchronisation".

---

### Task 11: Decoder part 3: filters and sampling

**Files:**
- Create: `src/optar/decoder/filters.py`, `src/optar/decoder/sample.py`, `tests/unit/test_decoder_sample.py`

**Interfaces:**
- Consumes: `interp`, `Geometry`, `DecodeOptions`, `channel_xy`.
- Produces:
  - `filters.minmax(img, geom, opts) -> np.ndarray`: `n = floor(sqrt(vpixel*hpixel) * minmax_filter)` passes of `max()` then `n` passes of `min()` (`unoptar.c:1320-1383`). One `max` pass: each pixel becomes the maximum of itself and its original left neighbour, then of itself and the original pixel above. One `min` pass: minimum with the original right neighbour, then with the original pixel below. The effect is to remove dark specks smaller than `n` pixels.
  - `filters.blur(img, geom, opts) -> np.ndarray`: `floor(vpixel*hpixel*pixel_blur**2 + 0.5)` passes of the 1-2-1 / 2-4-2 / 1-2-1 kernel with `(sum + 8) >> 4`; the outermost rows and columns are copied unchanged (`unoptar.c:1275-1318`).
  - `sample.sample_bits(img, positions, cutlevels, geom, fmt, opts) -> np.ndarray`: `uint8` array of length `fmt.total_bits`, the channel bit at each position in `channel_xy` order. Port of `bit_coord` (`unoptar.c:835-871`) and `pixel_correct_sample` (`496-524`): bilinear interpolation of the four surrounding cross positions and cut levels, the half-pixel shift to pixel centres, the unsharp mask over four neighbours at distance `hpixel*unsharp_dist` and `vpixel*unsharp_dist` along `ph` and `pv`, then `bit = value < local_cutlevel`. Process in chunks so peak memory stays under about 1 GB for a 600 dpi A4 scan.

**Order in the pipeline:** crosses are synchronised on the image after dirt removal; `minmax` and then `blur` run afterwards; sampling reads the blurred image.

- [ ] **Step 1: Write the failing tests**

```python
import numpy as np, pytest
from optar.decoder.crosses import sync_crosses
from optar.decoder.filters import blur, minmax
from optar.decoder.geometry import compute_geometry, find_corners
from optar.decoder.levels import analyze_levels
from optar.decoder.options import DecodeOptions
from optar.decoder.sample import sample_bits
from optar.encoder import encode
from optar.format import PageFormat
from optar.layout import channel_xy
from tests.helpers import fake_scan, seeded_bytes

F, OPTS = PageFormat(65, 93), DecodeOptions()

class G:  # minimal stand-in for Geometry in filter tests
    def __init__(self, s): self.hpixel = self.vpixel = float(s)

def test_minmax_scale_3_removes_a_one_pixel_dark_speck():
    img = np.full((12, 12), 255, np.uint8); img[5:11, 5:11] = 0
    specked = img.copy(); specked[2, 2] = 0
    assert np.array_equal(minmax(specked, G(3), OPTS), minmax(img, G(3), OPTS))   # 1 pass each
    assert np.array_equal(minmax(specked, G(1), OPTS), specked)   # floor(1*0.5) = 0 passes

def test_blur_passes_and_edges():
    img = np.zeros((5, 5), np.uint8); img[2, 2] = 160
    assert np.array_equal(blur(img, G(1), OPTS), img)            # round(0.0625) = 0 passes
    out = blur(img, G(3), OPTS)                                  # round(0.5625) = 1 pass
    assert out[2, 2] == 40 and out[2, 1] == 20 and out[1, 1] == 10
    edge = np.arange(25, dtype=np.uint8).reshape(5, 5)
    b = blur(edge, G(3), OPTS)
    assert np.array_equal(b[0], edge[0]) and np.array_equal(b[:, 0], edge[:, 0])

@pytest.mark.parametrize("scale", [1, 2, 3])
def test_sampled_bits_equal_the_page(scale):
    page = next(encode(seeded_bytes(9, 150000), F)).pixels
    scan = fake_scan(page, scale=scale, margin=60)
    lv = analyze_levels(scan, OPTS)
    g = compute_geometry(find_corners(scan, lv.cut), F, OPTS)
    pos, cuts = sync_crosses(scan, g, F, lv, OPTS)
    img = blur(minmax(scan, g, OPTS), g, OPTS)
    bits = sample_bits(img, pos, cuts, g, F, OPTS)
    x, y = channel_xy(F)
    assert bits.dtype == np.uint8 and len(bits) == F.total_bits
    assert np.array_equal(bits, (page[y + 2, x + 2] == 0).astype(np.uint8))
```

- [ ] **Step 2:** Run `pytest tests/unit/test_decoder_sample.py -q`. Expected: FAIL on import.
- [ ] **Step 3:** Implement `filters.py` and `sample.py`.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit: "Adds decoder filters and bit sampling".

---

### Task 12: Decoder part 4: pages to bytes, with degraded and oracle tests

**Files:**
- Modify: `src/optar/decoder/__init__.py`, `src/optar/__init__.py`
- Create: `tests/unit/test_decode.py`, `tests/oracle/test_decoder_oracle.py`, `tests/scans/README.md`, `tests/scans/test_real_scans.py`, `tests/unit/test_speed.py`

**Interfaces:**
- Consumes: everything from Tasks 2 to 11.
- Produces:
  - `PageStats` (frozen): `symbols: int`, `error_histogram: tuple[int, ...]` (symbols with 0, 1, 2, 3 corrected bits), `uncorrectable: int`; property `max_corrected: int`.
  - `PageResult` (frozen): `bits: np.ndarray` (`uint8`, length `fmt.net_bits`), `stats: PageStats`, `debug_image: np.ndarray | None`.
  - `decode_page(image: np.ndarray, fmt: PageFormat, options: DecodeOptions | None = None, *, debug: bool = False) -> PageResult`. Pipeline: `analyze_levels` -> `remove_border_dirt` -> `find_corners` -> `compute_geometry` -> `sync_crosses` -> `minmax` -> `blur` -> `sample_bits` -> de-interleave (bit `b` of symbol `s` is channel position `s + b*fec_syms`, most significant first) -> `decode_symbols` -> words to bits, most significant first. Raises `DecodeError` for an empty image, an image smaller than `fmt.width x fmt.height`, or `chalf == 0`. With `debug=True`, `debug_image` is the filtered image with a 2 x 2 checker mark at each cross centre.
  - `DecodeResult` (frozen): `data: bytes`, `pages: tuple[PageStats, ...]`; property `uncorrectable: int`.
  - `decode(images: Iterable[np.ndarray], fmt, options=None, *, progress: Callable[[int, PageStats], None] | None = None) -> DecodeResult`: concatenates the pages' bits and packs them to bytes, most significant bit first; trailing bits that do not fill a byte are dropped, as C does.
  - `optar/__init__.py` re-exports: `PageFormat`, `Paper`, `PAPERS`, `get_paper`, `encode`, `Page`, `decode`, `decode_page`, `DecodeOptions`, `DecodeResult`, `PageResult`, `PageStats`, `write_pdf`, `write_png`, `write_pgm`, `read_scan`, `OptarError`, `FormatError`, `DecodeError`.

**Degraded cases** (shared by the unit and oracle tests; defined once in `tests/helpers.py` as `DEGRADED`):

| name | fake_scan arguments |
|---|---|
| `clean1` | `scale=1` |
| `clean3` | `scale=3` |
| `rotated` | `scale=3, margin=120, rotate=0.3` |
| `blurred` | `scale=3, blur=1.0` |
| `noisy` | `scale=3, noise=12` |
| `specks` | `scale=3, specks=30` |
| `flips` | `scale=3, flips=200` |
| `combined` | `scale=3, margin=120, rotate=0.2, blur=0.8, noise=8, specks=20, flips=100` |

Each case must decode with `max_corrected <= 2` on every page (the margin the spec requires). If a case does not, weaken that case's numbers until it does; do not change the decoder.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_decode.py
import numpy as np, pytest
from optar import PageFormat, PAPERS, decode, decode_page, encode
from optar.errors import DecodeError
from tests.helpers import DEGRADED, fake_scan, seeded_bytes

A4 = PageFormat.for_paper(PAPERS["a4"])

@pytest.mark.parametrize("paper", ["a4", "letter"])
@pytest.mark.parametrize("size", [0, 1, 4321])
def test_round_trip_small(paper, size):
    fmt = PageFormat.for_paper(PAPERS[paper])
    data = seeded_bytes(size, size)
    res = decode((fake_scan(p.pixels, scale=1, margin=40) for p in encode(data, fmt)), fmt)
    assert res.data[:size] == data and not any(res.data[size:]) and res.uncorrectable == 0
    assert len(res.data) == fmt.net_bits // 8

def test_round_trip_two_pages_reports_progress():
    data = seeded_bytes(2, A4.net_bits // 8 + 999)
    seen = []
    res = decode((fake_scan(p.pixels, scale=1) for p in encode(data, A4)), A4,
                 progress=lambda n, st: seen.append(n))
    assert res.data[:len(data)] == data and seen == [1, 2] and len(res.pages) == 2

@pytest.mark.parametrize("order", [2, 3, 4, 5])
def test_round_trip_hamming_two_pages(order):
    fmt = PageFormat(65, 93, fec_order=order)
    data = seeded_bytes(order, fmt.net_bits // 8 + 2000)
    res = decode((fake_scan(p.pixels, scale=1) for p in encode(data, fmt)), fmt)
    assert res.data[:len(data)] == data

@pytest.mark.parametrize("name", list(DEGRADED))
def test_degraded_round_trip(name):
    data = seeded_bytes(11, 150000)
    page = next(encode(data, A4)).pixels
    r = decode_page(fake_scan(page, seed=1, **DEGRADED[name]), A4)
    assert r.stats.uncorrectable == 0 and r.stats.max_corrected <= 2
    assert np.packbits(r.bits)[:len(data)].tobytes() == data

@pytest.mark.parametrize("img", [np.zeros((0, 0), np.uint8), np.full((300, 200), 255, np.uint8),
                                 np.zeros((50, 50), np.uint8)])
def test_non_pages_raise(img):
    with pytest.raises(DecodeError):
        decode_page(img, A4)

def test_wrong_paper_does_not_crash():
    letter = PageFormat.for_paper(PAPERS["letter"])
    page = next(encode(seeded_bytes(1, 50000), A4)).pixels
    try:
        r = decode_page(fake_scan(page, scale=1), letter)
    except DecodeError:
        return
    assert r.stats.uncorrectable > 0

def test_debug_image_only_on_request():
    scan = fake_scan(next(encode(b"abc", A4)).pixels, scale=1)
    assert decode_page(scan, A4).debug_image is None
    assert decode_page(scan, A4, debug=True).debug_image.shape == scan.shape
```

`tests/oracle/test_decoder_oracle.py` (marker `oracle`, skips when `unoptar` was not built):
- C decodes Python pages: write Python pages for 300,000 seeded bytes as scans at scale 1, run `unoptar 0-0-0-0-0-0-0-24 base`, assert stdout's first 300,000 bytes equal the input. Repeat for Letter and for `FEC_ORDER` 2 to 5 with matching C builds.
- Python decodes C pages: run C `optar`, read the `.pgm` files, `fake_scan` them, `decode`, same assertion.
- For each `DEGRADED` case: save the scan as PNG, decode it with C and with Python via `read_scan`, and assert the two outputs are byte-identical over the whole page.

`tests/scans/test_real_scans.py`: parametrised over subdirectories of `tests/scans/`, each holding `original.bin`, `paper.txt` (`a4` or `letter`) and `scan_0001.png`, ...; decodes with `read_scan` and asserts the data matches and nothing is uncorrectable. With no subdirectories it reports one skipped test. `tests/scans/README.md` explains the layout in five lines.

`tests/unit/test_speed.py` (marker `slow`): encoding one full A4 page takes under 5 seconds; `decode_page` on `fake_scan(page, scale=3, margin=60)` takes under 60 seconds.

- [ ] **Step 2:** Run `pytest tests/unit/test_decode.py -q`. Expected: FAIL on import.
- [ ] **Step 3:** Implement `decode_page` and `decode`; update the re-exports.
- [ ] **Step 4:** Run `pytest -q && pytest -m "oracle or slow" -q`. Expected: PASS. These tests decode about 25 full pages; if the default run takes more than 10 minutes, speed up the decoder, do not thin the tests. If a `slow` test fails, profile and vectorise further. If the 60-second target cannot be met with numpy alone, stop and report the measured time and the hot spot; do not add a dependency.
- [ ] **Step 5:** Commit: "Adds page decoding with degraded and oracle tests".

---

### Task 13: Command line

**Files:**
- Create: `src/optar/cli.py`, `src/optar/__main__.py`, `tests/unit/test_cli.py`
- Modify: `pyproject.toml` (console script `optar = "optar.cli:main"`)

**Interfaces:**
- Consumes: the public API from Task 12.
- Produces: `cli.main(argv: list[str] | None = None) -> int`.

```
optar encode INPUT [-o BASE] [--paper a4|letter] [--to pdf|png|pgm] [--label TEXT] [--format STRING]
optar decode BASE [-o OUTPUT] [--paper a4|letter] [--format STRING] [--debug-images]
optar --version
```

Behaviour:
- `--paper` defaults to `a4`, case-insensitive. `--format` overrides the grid; `encode` refuses a format for which `fmt.fits(paper)` is false.
- `encode`: `BASE` defaults to `optar_out`. `--to pdf` (default) writes `BASE.pdf`; `png` and `pgm` write `BASE_0001.png` / `.pgm`, numbered with four digits. `--label` defaults to the `-o` value if given, otherwise empty. On success it prints to stderr the files written and the line `Print at actual size (100%), not "fit to page".`
- `decode`: reads `BASE_0001.png`, `BASE_0002.png`, ... until the first missing number. Writes to `OUTPUT`, or to stdout in binary mode when `-o` is absent. Prints one line per page to stderr with corrected and uncorrectable counts. `--debug-images` writes `BASE_NNNN_debug.png` beside each scan.
- Exit status: 0 success; 1 decoded with uncorrectable codewords or a numbering gap; 2 usage error, unreadable input, `OptarError` (printed as `optar: <message>`, never a traceback).
- If any page has uncorrectable codewords, or decoding raises any `DecodeError`, the message ends with `Check that --paper matches the printout.`
- Numbering gap: after the first missing number `N`, if `BASE_{N+1:04d}.png` exists, print `optar: NAME_{N:04d}.png is missing but NAME_{N+1:04d}.png exists`, where `NAME` is the file-name part of `BASE` without its directory, and exit 1 after writing the pages decoded so far.
- No pages at all: `optar: cannot open BASE_0001.png`, exit 2.

- [ ] **Step 1: Write the failing tests**

```python
import numpy as np, pytest
from optar import PAPERS, PageFormat, encode
from optar.cli import main
from tests.helpers import fake_scan, parse_pdf, save_scan, seeded_bytes

@pytest.fixture
def infile(tmp_path):
    p = tmp_path / "in.bin"; p.write_bytes(seeded_bytes(4, 3000)); return p

def scans(tmp_path, data, paper="a4", base="scan", skip=()):
    fmt = PageFormat.for_paper(PAPERS[paper])
    for p in encode(data, fmt):
        if p.number not in skip:
            save_scan(tmp_path / f"{base}_{p.number:04d}.png", fake_scan(p.pixels, scale=1))
    return str(tmp_path / base)

@pytest.mark.parametrize("paper,box", [("a4", (595.28, 841.89)), ("Letter", (612, 792))])
def test_encode_default_is_pdf_on_chosen_paper(tmp_path, infile, capsys, paper, box):
    assert main(["encode", str(infile), "-o", str(tmp_path / "out"), "--paper", paper]) == 0
    page = parse_pdf(tmp_path / "out.pdf")[0]
    assert page["mediabox"][2:] == pytest.approx(box, abs=0.01)
    assert "actual size" in capsys.readouterr().err

@pytest.mark.parametrize("kind", ["png", "pgm"])
def test_encode_page_files(tmp_path, infile, kind):
    assert main(["encode", str(infile), "-o", str(tmp_path / "out"), "--to", kind]) == 0
    assert (tmp_path / f"out_0001.{kind}").exists() and not (tmp_path / "out.pdf").exists()

def test_decode_to_file_and_stdout(tmp_path, capsysbinary):
    data = seeded_bytes(4, 3000); base = scans(tmp_path, data)
    assert main(["decode", base, "-o", str(tmp_path / "out.bin")]) == 0
    assert (tmp_path / "out.bin").read_bytes()[:3000] == data
    assert main(["decode", base]) == 0
    assert capsysbinary.readouterr().out[:3000] == data

def test_letter_round_trip_through_cli(tmp_path):
    data = seeded_bytes(6, 3000); base = scans(tmp_path, data, paper="letter")
    assert main(["decode", base, "--paper", "letter", "-o", str(tmp_path / "o")]) == 0
    assert (tmp_path / "o").read_bytes()[:3000] == data

def test_wrong_paper_exits_1_with_hint(tmp_path, capsys):
    base = scans(tmp_path, seeded_bytes(6, 3000), paper="a4")
    assert main(["decode", base, "--paper", "letter", "-o", str(tmp_path / "o")]) in (1, 2)
    assert "--paper" in capsys.readouterr().err

def test_blank_scan_exits_2_without_traceback(tmp_path, capsys):
    save_scan(tmp_path / "s_0001.png", np.full((500, 400), 255, np.uint8))
    assert main(["decode", str(tmp_path / "s"), "-o", str(tmp_path / "o")]) == 2
    err = capsys.readouterr().err
    assert err.startswith("optar: ") and "Traceback" not in err

def test_numbering_gap_warns_and_exits_1(tmp_path, capsys):
    fmt = PageFormat.for_paper(PAPERS["a4"])
    base = scans(tmp_path, seeded_bytes(1, 2 * fmt.net_bits // 8 + 5), skip=(2,))
    assert main(["decode", base, "-o", str(tmp_path / "o")]) == 1
    assert "scan_0002.png is missing but scan_0003.png exists" in capsys.readouterr().err

def test_usage_errors(tmp_path, capsys):
    assert main(["decode", str(tmp_path / "nothing")]) == 2
    assert main(["encode", str(tmp_path / "missing.bin")]) == 2
    (tmp_path / "in.bin").write_bytes(b"x")
    assert main(["encode", str(tmp_path / "in.bin"), "-o", str(tmp_path / "o"),
                 "--format", "0-80-93-24-3-1-2-24"]) == 2        # does not fit A4
    assert "fit" in capsys.readouterr().err
    with pytest.raises(SystemExit) as e:
        main(["encode", "x", "--paper", "legal"])
    assert e.value.code == 2

def test_version(capsys):
    import optar
    with pytest.raises(SystemExit):
        main(["--version"])
    assert optar.__version__ in capsys.readouterr().out
```

- [ ] **Step 2:** Run `pytest tests/unit/test_cli.py -q`. Expected: FAIL on import.
- [ ] **Step 3:** Implement `cli.py` with `argparse` and `__main__.py`.
- [ ] **Step 4:** Run `pytest -q`. Expected: PASS. Then run `.venv/bin/optar encode README.md -o /tmp/optar-demo && ls -la /tmp/optar-demo.pdf` and confirm the PDF exists.
- [ ] **Step 5:** Commit: "Adds encode and decode commands".

---

### Task 14: Ghostscript print check

**Files:**
- Create: `tests/oracle/test_pdf_render.py`
- Modify: `tests/conftest.py` (fixture `ghostscript` returning the `gs` path or skipping)

**Interfaces:**
- Consumes: `cli.main`, `read_scan`, `decode`.

- [ ] **Step 1: Write the test** (marker `gs`): for `a4` and `letter`, encode 250,000 seeded bytes to PDF through `main`, render with `gs -q -dNOPAUSE -dBATCH -sDEVICE=pnggray -r600 -sOutputFile=<tmp>/r_%04d.png out.pdf`, then assert:
  - each rendered page is the paper size at 600 dpi to within 1 pixel (A4: 4961 x 7016; Letter: 5100 x 6600);
  - `main(["decode", "<tmp>/r", "--paper", paper, "-o", out])` returns 0 and the output's first 250,000 bytes equal the input.
- [ ] **Step 2:** Run `pytest -m gs -q`. Expected: PASS where Ghostscript is installed, SKIPPED otherwise. A failure means the PDF placement or image encoding in Task 8 is wrong; fix it there.
- [ ] **Step 3:** Commit: "Adds Ghostscript render check for PDF output".

---

### Task 15: One-file executable and GitHub Actions

**Files:**
- Create: `packaging/entry.py`, `packaging/smoke.py`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`
- Delete: `.travis.yml`

**Interfaces:**
- Consumes: `optar.cli.main`, `optar.__version__`.
- Produces:
  - `packaging/entry.py`: `import sys; from optar.cli import main; sys.exit(main())`.
  - Build command (same on every OS): `pyinstaller --onefile --name optar --collect-data optar packaging/entry.py`, output `dist/optar` or `dist/optar.exe`.
  - `packaging/smoke.py EXECUTABLE`: runs the built executable only (no import of `optar`): `--version` prints the expected version; `encode` a 50,000-byte file with `--to png`; `decode` those PNG files back; asserts the first 50,000 bytes match; also checks `encode` to PDF produces a file starting with `%PDF`. Exits non-zero on any failure.
  - `ci.yml`, on `push` and `pull_request`:
    - job `lint`: Ubuntu, Python 3.13, `ruff check .`.
    - job `test`: matrix `ubuntu-latest`, `macos-latest`, `windows-latest` x Python `3.10`, `3.13`; `pip install -e '.[dev]'`; `pytest -q`.
    - job `oracle`: Ubuntu, Python 3.13; `sudo apt-get update && sudo apt-get install -y libpng-dev ghostscript`; `pytest -q -m "oracle or gs or slow"`. The job fails if any of those tests is skipped (`pytest -rs` output is checked for `SKIPPED`), except `tests/scans`.
  - `release.yml`, on tags `v*`, `permissions: contents: write`:
    - job `build`: matrix `ubuntu-latest`, `macos-latest`, `windows-latest`, Python 3.13; fail if the tag is not `v` + `optar.__version__`; build; run `packaging/smoke.py`; rename to `optar-<tag>-linux-x86_64`, `optar-<tag>-macos-arm64`, `optar-<tag>-windows-x86_64.exe`; upload as a workflow artifact.
    - job `publish`: downloads the three artifacts and runs `gh release create "$TAG" --generate-notes <files>` with `GH_TOKEN: ${{ github.token }}`.
  - Use only `actions/checkout`, `actions/setup-python`, `actions/upload-artifact`, `actions/download-artifact`.

- [ ] **Step 1:** Write `packaging/entry.py` and `packaging/smoke.py`.
- [ ] **Step 2:** Build locally: `.venv/bin/pyinstaller --onefile --name optar --collect-data optar packaging/entry.py`. Expected: `dist/optar` exists.
- [ ] **Step 3:** Run `.venv/bin/python packaging/smoke.py dist/optar`. Expected: exit 0. A failure to find `font.png` means the data file was not collected; fix the build command, and mirror the fix in `release.yml`.
- [ ] **Step 4:** Write both workflows and delete `.travis.yml`.
- [ ] **Step 5:** Check the YAML parses: `.venv/bin/pip install pyyaml -q && .venv/bin/python -c "import yaml,sys; [yaml.safe_load(open(f)) for f in sys.argv[1:]]" .github/workflows/ci.yml .github/workflows/release.yml`. Expected: no output.
- [ ] **Step 6:** Commit: "Adds one-file build and GitHub Actions workflows".
- [ ] **Step 7:** Ask the owner before pushing. The workflows are only proven once `ci.yml` runs green on GitHub; report that as unverified until it has.

---

### Task 16: Documentation

**Files:**
- Modify: `README.md`, `CLAUDE.md`, `.claude/hooks/syntax-check.sh`

- [ ] **Step 1:** `README.md`: add a "Python version" section above the C instructions covering installation (download the executable, or `pip install .`), `optar encode` and `optar decode` with `--paper` and `--to`, the "print at actual size" rule, the zero-padding of decoded output (unchanged in format version 0), supported Hamming orders, and the one-line statement that decoding real scans is not yet covered by an automated test. Replace the Travis badge with the `ci.yml` badge for `mezinster/optar`. Keep the C instructions under a "C reference implementation" heading.
- [ ] **Step 2:** `CLAUDE.md`: add the Python commands (`.venv/bin/pytest -q`, `-m "oracle or gs or slow"`, `ruff check .`, the PyInstaller build), the rule that format numbers live only in `format.py`, the rule that the C sources are the oracle and must not be edited, and how to regenerate `tests/golden/fixtures.json`. Remove the line about the dead Travis config.
- [ ] **Step 3:** `.claude/hooks/syntax-check.sh`: add a `*.py` case that runs `"$dir/.venv/bin/ruff" check "$f"` when that binary exists and exits 2 with its output on failure.
- [ ] **Step 4:** Run `pytest -q && ruff check . && shellcheck -S warning .claude/hooks/syntax-check.sh`. Expected: all pass.
- [ ] **Step 5:** Commit: "Documents the Python version".
