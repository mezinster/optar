"""docs/format.md must agree with the code.

Every table that follows a `<!-- spec-table: NAME -->` comment is parsed and
compared with the code, and every `name = value` line of a fenced block with
the info string `example` is recomputed.
"""

from __future__ import annotations

import dataclasses
import hashlib
import re
import struct
import zlib
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from optar import container, encoder, font, tag
from optar import format as fmt_module
from optar.container import Header, padding, plan, plan_for, positions
from optar.decoder.options import DecodeOptions
from optar.encoder import page_count
from optar.fec import encode_symbols, golay_table
from optar.font import fine_label, glyph_strip, label_text
from optar.format import (
    CODEWORD,
    DOT_SIZES,
    HEADER_COPIES,
    HEADER_SIZE,
    LAYOUTS,
    PARITY,
    PageFormat,
    get_layout,
)
from optar.imageio import DEFAULT_FILE_GAMMA, _gamma_table
from optar.label import label_capacity
from optar.layout import channel_xy
from optar.rs import _EXP, RSCode
from optar.tag import make_tag, tagged_label

SPEC = Path(__file__).resolve().parents[2] / "docs" / "format.md"
TABLE_NAMES = {"constants", "dot-sizes", "layouts", "header-fields", "parity"}
MM_PER_PT = 25.4 / 72
# Where a name in the constants table may be defined, in this order.
CONSTANT_MODULES = (fmt_module, encoder, font, tag)

_MARKER = re.compile(r"<!--\s*spec-table:\s*([a-z-]+)\s*-->")


def _text() -> str:
    assert SPEC.exists(), f"{SPEC} is missing"
    return SPEC.read_text(encoding="utf-8")


def _cells(line: str) -> list[str]:
    return [c.strip().replace("`", "") for c in line.strip().strip("|").split("|")]


def _tables() -> dict[str, list[list[dict[str, str]]]]:
    """Every marked table: name -> tables, each a list of rows keyed by column title."""
    lines = _text().splitlines()
    found: dict[str, list[list[dict[str, str]]]] = {}
    for at, line in enumerate(lines):
        m = _MARKER.search(line)
        if m is None:
            continue
        name = m.group(1)
        assert name in TABLE_NAMES, f"line {at + 1}: unknown table name {name!r}"
        at += 1
        while at < len(lines) and not lines[at].strip():
            at += 1
        block = []
        while at < len(lines) and lines[at].lstrip().startswith("|"):
            block.append(lines[at])
            at += 1
        assert len(block) >= 3, f"no table follows the marker {name!r}"
        titles = _cells(block[0])
        assert re.fullmatch(r"[|\s:-]+", block[1]), f"table {name!r} has no separator row"
        rows = []
        for row in block[2:]:
            cells = _cells(row)
            assert len(cells) == len(titles), f"table {name!r}: ragged row {row!r}"
            rows.append(dict(zip(titles, cells, strict=True)))
        found.setdefault(name, []).append(rows)
    return found


def _one(name: str) -> list[dict[str, str]]:
    tables = _tables().get(name, [])
    assert len(tables) == 1, f"expected one table marked {name!r}, found {len(tables)}"
    return tables[0]


def _constant(name: str):
    """The value the code gives a name of the constants table."""
    if name.startswith("PageFormat."):
        fields = {f.name: f.default for f in dataclasses.fields(PageFormat)}
        value = fields[name.removeprefix("PageFormat.")]
        assert value is not dataclasses.MISSING, f"{name} has no default"
        return value
    for module in CONSTANT_MODULES:
        if hasattr(module, name):
            return getattr(module, name)
    raise AssertionError(f"the code has no constant named {name}")


def _written(value) -> str:
    """How the constants table writes a value."""
    if isinstance(value, bytes):
        return '"' + value.decode("ascii") + '"'
    if isinstance(value, float):
        return f"{value:g}"
    assert isinstance(value, int) and not isinstance(value, bool)
    return str(value)


def test_every_marked_table_is_present():
    assert set(_tables()) == TABLE_NAMES


def test_spec_tables_match_the_code():
    # constants: every name exists with that value, and every scalar constant
    # of format.py is named.
    rows = _one("constants")
    named = [row["Name"] for row in rows]
    assert len(set(named)) == len(named), "a constant is listed twice"
    for row in rows:
        assert row["Value"] == _written(_constant(row["Name"])), row["Name"]
    scalars = {
        name
        for name, value in vars(fmt_module).items()
        if name.isupper()
        and not name.startswith("_")
        and isinstance(value, int | float | bytes)
        and not isinstance(value, bool)
    }
    assert scalars <= set(named), f"not in the table: {sorted(scalars - set(named))}"
    defaults = {
        f"PageFormat.{f.name}"
        for f in dataclasses.fields(PageFormat)
        if f.default is not dataclasses.MISSING
    }
    assert defaults <= set(named), f"not in the table: {sorted(defaults - set(named))}"

    # dot-sizes: the five sizes in order.
    rows = _one("dot-sizes")
    assert [row["Name"] for row in rows] == list(DOT_SIZES)
    for row, dots in zip(rows, DOT_SIZES.values(), strict=True):
        assert int(row["Printer dots per data dot"]) == dots.printer_dots, dots.name
        assert Fraction(row["Data dots per inch"]) == dots.pixels_per_inch, dots.name
        assert float(row["Dot size (pt)"]) == pytest.approx(dots.size_pt, abs=1e-9), dots.name
        assert int(row["Advised scan (dpi)"]) == dots.scan_dpi, dots.name

    # layouts: every table has the ten layouts; together they give every column.
    checks = {
        "Crosses across": lambda lay: lay.xcrosses,
        "Crosses down": lambda lay: lay.ycrosses,
        "Format string": lambda lay: lay.fmt.to_string(),
        "Width (px)": lambda lay: lay.fmt.width,
        "Height (px)": lambda lay: lay.fmt.height,
        "Net bits": lambda lay: lay.fmt.net_bits,
        "Page bytes": lambda lay: plan_for(1, lay.fmt, 0).page_bytes,
        "Body bytes": lambda lay: plan_for(1, lay.fmt, 0).page_body,
        "Paper width (pt)": lambda lay: lay.paper.width_pt,
        "Paper height (pt)": lambda lay: lay.paper.height_pt,
        "Offset x (pt)": lambda lay: lay.offset_x_pt,
        "Offset y (pt)": lambda lay: lay.offset_y_pt,
        "Left (mm)": lambda lay: lay.margins()[0] * MM_PER_PT,
        "Bottom (mm)": lambda lay: lay.margins()[1] * MM_PER_PT,
        "Right (mm)": lambda lay: lay.margins()[2] * MM_PER_PT,
        "Top (mm)": lambda lay: lay.margins()[3] * MM_PER_PT,
    }
    seen: set[str] = set()
    tables = _tables()["layouts"]
    for rows in tables:
        assert [(row["Paper"], row["Dots"]) for row in rows] == list(LAYOUTS)
        for row in rows:
            layout = LAYOUTS[row["Paper"], row["Dots"]]
            for title, cell in row.items():
                if title in ("Paper", "Dots"):
                    continue
                assert title in checks, f"layouts: unknown column {title!r}"
                seen.add(title)
                want = checks[title](layout)
                where = f"{row['Paper']} {row['Dots']} {title}"
                if isinstance(want, str):
                    assert cell == want, where
                elif isinstance(want, int):
                    assert int(cell) == want, where
                elif title.endswith("(mm)"):
                    assert re.fullmatch(r"[0-9]+\.[0-9]{2}", cell), where
                    assert abs(float(cell) - want) <= 0.005 + 1e-9, where
                else:
                    assert float(cell) == pytest.approx(want, abs=1e-9), where
    assert seen == set(checks), f"layouts: columns missing: {sorted(set(checks) - seen)}"

    # header-fields: order, offsets and sizes, checked on a packed header.
    rows = _one("header-fields")
    sample = Header(page=3, total=7, size=552508, fingerprint=bytes(range(16)), parity=64)
    packed = sample.pack()
    content = {
        "magic": fmt_module.HEADER_MAGIC,
        "version": bytes([fmt_module.CONTAINER_VERSION]),
        "parity": bytes([sample.parity]),
        "page": struct.pack(">H", sample.page),
        "total": struct.pack(">H", sample.total),
        "size": struct.pack(">Q", sample.size),
        "fingerprint": sample.fingerprint,
        "crc": struct.pack(">I", zlib.crc32(packed[:-4])),
    }
    assert [row["Field"] for row in rows] == list(content)
    sizes = [struct.calcsize(">" + code) for code in re.findall(r"[0-9]*[a-zA-Z]",
             container._FIELDS.format.lstrip(">"))] + [container._CRC.size]  # fmt: skip
    assert [int(row["Size"]) for row in rows] == sizes
    offset = 0
    for row in rows:
        assert int(row["Offset"]) == offset, row["Field"]
        size = int(row["Size"])
        assert packed[offset : offset + size] == content[row["Field"]], row["Field"]
        offset += size
    assert offset == HEADER_SIZE == len(packed)

    # parity: the three levels in order.
    rows = _one("parity")
    assert [row["Name"] for row in rows] == list(PARITY)
    for row in rows:
        assert int(row["Parity bytes"]) == PARITY[row["Name"]], row["Name"]
        assert int(row["Data bytes"]) == CODEWORD - PARITY[row["Name"]], row["Name"]


# Worked examples. Each name maps to a function of the code that returns the
# value exactly as the document writes it.

A4 = get_layout("a4").fmt
A4_LARGE = get_layout("a4", "large")
A4_MEDIUM = get_layout("a4", "medium").fmt


def _xy(fmt: PageFormat, seq: int) -> str:
    x, y = channel_xy(fmt)
    return f"{int(x[seq])}, {int(y[seq])}"


def _hex(data) -> str:
    return bytes(data).hex()


def _golay(word: int) -> str:
    return f"0x{int(golay_table()[word]):06x}"


def _hamming(order: int, word: int) -> str:
    f = PageFormat(65, 93, fec_order=order)
    code = int(encode_symbols(np.array([word], dtype=np.uint32), f)[0])
    return format(code, f"0{f.fec_largebits}b")


def _code_bits(order: int) -> str:
    f = PageFormat(65, 93, fec_order=order)
    return f"{f.fec_largebits}, {f.fec_smallbits}"


def _rs_parity_of_one(parity: int) -> str:
    """The parity bytes of the message that is zero but for a last byte of 1."""
    message = np.zeros((1, CODEWORD - parity), dtype=np.uint8)
    message[0, -1] = 1
    return _hex(RSCode(parity).encode(message)[0])


def _rs_parity_of_counting() -> str:
    message = np.arange(CODEWORD - 32, dtype=np.uint8)[None, :]
    return _hex(RSCode(32).encode(message)[0])


def _plan_example():
    return plan(1_000_000, "vector.bin", A4, 32)


def _stream_shift(page: int) -> str:
    byte, shift = divmod((page - 1) * A4_MEDIUM.net_bits, 8)
    return f"{byte}, {shift}"


def _strip_text() -> str:
    width = int(A4_LARGE.fmt.data_width * A4_LARGE.dots.scale)
    return str(len(label_text(A4_LARGE.fmt, 1, 1, "x" * 300, width)))


_SAMPLE_HEADER = Header(page=3, total=7, size=552508, fingerprint=bytes(range(16)), parity=64)

EXAMPLES = {
    # the page
    "a4_data_width": lambda: A4.data_width,
    "a4_data_height": lambda: A4.data_height,
    "a4_width": lambda: A4.width,
    "a4_height": lambda: A4.height,
    "a4_label_top_row": lambda: A4.border + A4.data_height,
    "a4_last_cross_x": lambda: A4.border + A4.cpitch * (A4.xcrosses - 1),
    "a4_last_cross_y": lambda: A4.border + A4.cpitch * (A4.ycrosses - 1),
    "a4_narrow_width": lambda: A4.narrow_width,
    "a4_narrow_pixels": lambda: A4.narrow_pixels,
    "a4_wide_pixels": lambda: A4.wide_pixels,
    "a4_rep_pixels": lambda: A4.rep_pixels,
    "a4_total_bits": lambda: A4.total_bits,
    "a4_symbols": lambda: A4.fec_syms,
    "a4_used_bits": lambda: A4.used_bits,
    "a4_net_bits": lambda: A4.net_bits,
    "a4_medium_total_bits": lambda: A4_MEDIUM.total_bits,
    "a4_medium_symbols": lambda: A4_MEDIUM.fec_syms,
    "a4_medium_unused_bits": lambda: A4_MEDIUM.total_bits - A4_MEDIUM.used_bits,
    "a4_medium_net_bits": lambda: A4_MEDIUM.net_bits,
    "a4_xy_of_0": lambda: _xy(A4, 0),
    "a4_xy_of_17": lambda: _xy(A4, 17),
    "a4_xy_of_18": lambda: _xy(A4, 18),
    "a4_xy_of_1152": lambda: _xy(A4, 1152),
    "a4_xy_of_6912": lambda: _xy(A4, 6912),
    "a4_xy_of_8454": lambda: _xy(A4, 8454),
    "a4_xy_of_34668": lambda: _xy(A4, 34668),
    "a4_xy_of_3196367": lambda: _xy(A4, 3196367),
    "a4_position_of_symbol_1000_bit_5": lambda: 1000 + 5 * A4.fec_syms,
    "a4_xy_of_666910": lambda: _xy(A4, 666910),
    "golay_0x001": lambda: _golay(0x001),
    "golay_0x800": lambda: _golay(0x800),
    "golay_0xabc": lambda: _golay(0xABC),
    "golay_0xfff": lambda: _golay(0xFFF),
    "hamming_2_of_1": lambda: _hamming(2, 1),
    "hamming_3_of_1011": lambda: _hamming(3, 0b1011),
    "hamming_4_of_10000000001": lambda: _hamming(4, 0b10000000001),
    "hamming_5_of_1": lambda: _hamming(5, 1),
    "hamming_2_net_bits": lambda: PageFormat(65, 93, fec_order=2).net_bits,
    "hamming_3_net_bits": lambda: PageFormat(65, 93, fec_order=3).net_bits,
    "hamming_4_net_bits": lambda: PageFormat(65, 93, fec_order=4).net_bits,
    "hamming_5_net_bits": lambda: PageFormat(65, 93, fec_order=5).net_bits,
    "code_bits_of_order_1": lambda: _code_bits(1),
    "code_bits_of_order_2": lambda: _code_bits(2),
    "code_bits_of_order_3": lambda: _code_bits(3),
    "code_bits_of_order_4": lambda: _code_bits(4),
    "code_bits_of_order_5": lambda: _code_bits(5),
    "a4_pages_for_0_bytes": lambda: page_count(0, A4),
    "a4_pages_for_1_byte": lambda: page_count(1, A4),
    "a4_pages_for_199773_bytes": lambda: page_count(199773, A4),
    "a4_pages_for_199774_bytes": lambda: page_count(199774, A4),
    "a4_words_for_1000_bytes": lambda: -(-1000 * 8 // A4.fec_smallbits),
    # the label
    "strip_width": lambda: glyph_strip().shape[1],
    "logo_width": lambda: glyph_strip().shape[1] - fmt_module.TEXT_WIDTH * font.GLYPH_CELLS,
    "font_strip_sha256": lambda: hashlib.sha256(glyph_strip().tobytes()).hexdigest(),
    "glyph_column_of_capital_a": lambda: fmt_module.TEXT_WIDTH * (ord("A") - font.FIRST_CHAR),
    "a4_label_line": lambda: '"' + label_text(A4, 3, 7, "backup.tar") + '"',
    "a4_label_characters": lambda: len(label_text(A4, 1, 1, "x" * 300)),
    "a4_label_cells": lambda: label_capacity(A4),
    "a4_xlarge_label_cells": lambda: label_capacity(get_layout("a4", "xlarge").fmt),
    # the tag
    "tag_fingerprint_of_x": lambda: make_tag(b"x").fingerprint,
    "tag_check_input": lambda: '"' + f"1:{make_tag(b'x').fingerprint}:1/1" + '"',
    "tag_check_of_x_page_1_of_1": lambda: make_tag(b"x").check(1, 1),
    "tag_free_text": lambda: '"' + tagged_label(make_tag(b"x"), "name.tar", 1, 1) + '"',
    "tag_of_empty_file": lambda: '"' + tagged_label(make_tag(b""), "", 1, 0) + '"',
    # the container
    "header_bytes": lambda: _hex(_SAMPLE_HEADER.pack()),
    "header_crc": lambda: f"0x{zlib.crc32(_SAMPLE_HEADER.pack()[:-4]):08x}",
    "a4_page_bytes": lambda: plan_for(1, A4, 0).page_bytes,
    "a4_header_offsets": lambda: ", ".join(
        str(c * (plan_for(1, A4, 0).page_bytes // HEADER_COPIES)) for c in range(HEADER_COPIES)
    ),
    "a4_page_body": lambda: plan_for(1, A4, 0).page_body,
    "gf_alpha_8": lambda: f"0x{int(_EXP[8]):02x}",
    "gf_alpha_254": lambda: f"0x{int(_EXP[254]):02x}",
    "rs_32_parity_of_one": lambda: _rs_parity_of_one(32),
    "rs_32_parity_of_counting": _rs_parity_of_counting,
    "plan_need": lambda: 1_000_000 + 1 + len("vector.bin"),
    "plan_codewords_needed": lambda: -(-(1_000_000 + 1 + len("vector.bin")) // (CODEWORD - 32)),
    "plan_pages": lambda: _plan_example().total,
    "plan_codewords": lambda: _plan_example().codewords,
    "plan_data_bytes": lambda: _plan_example().data_bytes,
    "plan_body_bytes": lambda: _plan_example().total * _plan_example().page_body,
    "plan_spare_bytes": lambda: _plan_example().total * _plan_example().page_body
    - CODEWORD * _plan_example().codewords,
    "plan_padding_in_region": lambda: _plan_example().data_bytes - (1_000_000 + 1 + 10),
    "plan_position_of_codeword_0_byte_0": lambda: int(positions(_plan_example())[0, 0]),
    "plan_position_of_codeword_5_byte_0": lambda: int(positions(_plan_example())[5, 0]),
    "plan_position_of_codeword_5_byte_1": lambda: int(positions(_plan_example())[5, 1]),
    "plan_position_of_codeword_5_byte_254": lambda: int(positions(_plan_example())[5, 254]),
    "plan_page_of_codeword_5_byte_254": lambda: int(positions(_plan_example())[5, 254])
    // _plan_example().page_body
    + 1,
    "padding_block_0": lambda: hashlib.sha256(b"optar padding" + bytes(8)).hexdigest(),
    "padding_bytes_30_to_33": lambda: _hex(padding(30, 4)),
    "a4_medium_stream_bytes_for_3_pages": lambda: 3 * A4_MEDIUM.net_bits // 8,
    "a4_medium_page_2_starts_at": lambda: _stream_shift(2),
    "a4_medium_page_3_starts_at": lambda: _stream_shift(3),
    # printing and reading
    "a4_large_image_width_pt": lambda: f"{A4_LARGE.fmt.width * A4_LARGE.dots.size_pt:.2f}",
    "a4_large_image_height_pt": lambda: f"{A4_LARGE.fmt.height * A4_LARGE.dots.size_pt:.2f}",
    "a4_large_strip_width": lambda: fine_label(A4_LARGE, 1, 1, "").shape[1],
    "a4_large_strip_characters": _strip_text,
    "a4_large_strip_width_pt": lambda: f"{fine_label(A4_LARGE, 1, 1, '').shape[1] * 0.36:.2f}",
    "linear_light_of_128": lambda: int(_gamma_table(DEFAULT_FILE_GAMMA)[128]),
    "linear_light_of_200": lambda: int(_gamma_table(DEFAULT_FILE_GAMMA)[200]),
    **{
        f"decoder_{f.name}": (lambda name=f.name: f"{getattr(DecodeOptions(), name):g}")
        for f in dataclasses.fields(DecodeOptions)
    },
}

_EXAMPLE_LINE = re.compile(r"([a-z0-9_]+) = (.+)")


def _examples() -> list[tuple[str, str]]:
    pairs = []
    inside = False
    for number, line in enumerate(_text().splitlines(), start=1):
        if not inside:
            inside = line.strip() == "```example"
            continue
        if line.strip() == "```":
            inside = False
            continue
        if not line.strip():
            continue
        m = _EXAMPLE_LINE.fullmatch(line.strip())
        assert m is not None, f"line {number}: not a `name = value` line: {line!r}"
        pairs.append((m.group(1), m.group(2)))
    assert not inside, "an example block is not closed"
    return pairs


def test_spec_worked_examples():
    pairs = _examples()
    names = [name for name, _ in pairs]
    assert len(set(names)) == len(names), "an example name is used twice"
    unknown = sorted(set(names) - set(EXAMPLES))
    assert not unknown, f"the test cannot recompute: {unknown}"
    absent = sorted(set(EXAMPLES) - set(names))
    assert not absent, f"examples the document no longer gives: {absent}"
    for name, written in pairs:
        assert written == str(EXAMPLES[name]()), name


def test_sections_name_their_vectors():
    """Each `Vectors:` line names files of tests/vectors, by the agreed names."""
    known = {
        "c/golay.json",
        "c/bit_placement.json",
        "c/encoder_pages.json",
        "c/label.json",
        "c/container_pages.json",
        "c/decoder.json",
        "c/decoder_internals.json",
        "py/reed_solomon.json",
        "py/container.json",
        "py/tag.json",
    }
    lines = [line for line in _text().splitlines() if line.startswith("Vectors:")]
    assert lines, "no section names its vectors"
    named: set[str] = set()
    for line in lines:
        files = re.findall(r"`tests/vectors/([a-z_/]+\.json)`", line)
        assert files, f"no vector file in {line!r}"
        assert set(files) <= known, f"unknown vector file in {line!r}"
        named.update(files)
    assert named == known, f"vector files no section names: {sorted(known - named)}"
