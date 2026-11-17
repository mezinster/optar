"""Check the Python code against results recorded from the C tools (no compiler needed).

The vectors were recorded by lega-c/record_vectors/record.py; tests/vectors/README.md
defines every digest.
"""

from pathlib import Path

import numpy as np
import pytest

from optar import decode, read_scan
from optar.container import wrap
from optar.decoder.crosses import sync_crosses
from optar.decoder.dirt import remove_border_dirt
from optar.decoder.filters import blur, minmax
from optar.decoder.geometry import compute_geometry, find_corners
from optar.decoder.levels import analyze_levels
from optar.decoder.options import DecodeOptions
from optar.decoder.sample import sample_bits
from optar.encoder import encode
from optar.fec import golay_table, serialize_table
from optar.format import PageFormat
from optar.imageio import pgm_bytes
from optar.layout import channel_xy
from tests.helpers import fake_scan, save_scan, seeded_bytes
from tests.vectors.load import HERE, array_digest, digest, load

GOLAY = load("c/golay")
PLACEMENT = load("c/bit_placement")
PAGES = load("c/encoder_pages")
CONTAINER = load("c/container_pages")
LABEL = load("c/label")
DECODER = load("c/decoder")
INTERNALS = load("c/decoder_internals")

C_DIR = HERE / "c"
# The only fake_scan arguments a regenerated (not stored) scan may use: these
# make no random numbers and no resampling, so no numpy or Pillow upgrade can
# change them.
REGENERATED_SCALES = (1, 3)


def _name(case):
    return case["name"]


def _scans(case, pages):
    """The scans a decoder case decodes, as decoders see them (via read_scan)."""
    if "scan_files" in case:
        return [read_scan(C_DIR / f) for f in case["scan_files"]]
    return [fake_scan(p.pixels, **case["recipe"]) for p in pages]


def _through_png(array, tmp_path: Path, n: int):
    """Save a scan with save_scan and load it with read_scan, as C reads it."""
    path = tmp_path / f"scan_{n:04d}.png"
    save_scan(path, array)
    return read_scan(path)


def test_golay_table():
    assert digest(serialize_table(golay_table())) == GOLAY["cases"]["golay_sha256"]


@pytest.mark.parametrize("fmt", PLACEMENT["cases"])
def test_bit_placement(fmt):
    case = PLACEMENT["cases"][fmt]
    x, y = channel_xy(PageFormat.parse(fmt))
    for seq, cx, cy in case["samples"]:
        assert (x[seq], y[seq]) == (cx, cy)
    assert array_digest(np.stack([x, y]).astype("<i4"), np.dtype("<i4")) == case["all_sha256"]


@pytest.mark.parametrize("case", PAGES["cases"], ids=lambda c: f'{c["name"]}-{c["format"]}')
def test_encoder_pages(case):
    fmt = PageFormat.parse(case["format"])
    pages = encode(seeded_bytes(case["seed"], case["size"]), fmt, case["label"])
    assert [digest(pgm_bytes(p.pixels)) for p in pages] == case["sha256"]


def _container_stream(case):
    fmt = PageFormat.parse(case["format"])
    stream = wrap(seeded_bytes(case["seed"], case["size"]), case["file_name"], fmt, case["parity"])
    assert digest(stream) == case["stream_sha256"]
    return fmt, stream


@pytest.mark.parametrize("case", CONTAINER["cases"], ids=_name)
def test_container_pages(case):
    fmt, stream = _container_stream(case)
    pages = encode(stream, fmt, case["label"])
    assert [digest(pgm_bytes(p.pixels)) for p in pages] == case["page_sha256"]


@pytest.mark.parametrize("case", CONTAINER["cases"], ids=_name)
def test_c_reads_container_pages(case, tmp_path):
    fmt, stream = _container_stream(case)
    pages = list(encode(stream, fmt, case["label"]))
    scans = [
        _through_png(fake_scan(p.pixels, **case["recipe"]), tmp_path, p.number) for p in pages
    ]
    res = decode(scans, fmt)
    assert res.data[: len(stream)] == stream
    assert digest(res.data) == case["c_output_sha256"]


@pytest.mark.parametrize("case", LABEL["cases"], ids=lambda c: f'{len(c["text"])}-chars')
def test_label_band(case):
    fmt = PageFormat.parse(case["format"])
    page = next(encode(bytes.fromhex(case["input_hex"]), fmt, case["text"])).pixels
    top = fmt.border + fmt.data_height
    band = page[top : top + fmt.text_height, :]
    assert array_digest(band, np.uint8) == case["band_sha256"]


def _decoder_case(case, tmp_path):
    fmt = PageFormat.parse(case["format"])
    data = seeded_bytes(case["seed"], case["size"])
    pages = list(encode(data, fmt))
    if "page_sha256" in case:
        # The C-made pages: the Python pages equal them, so decoding these
        # decodes the pages C made.
        assert [digest(pgm_bytes(p.pixels)) for p in pages] == case["page_sha256"]
    if "scan_files" in case:
        scans = _scans(case, pages)
    else:
        scans = [_through_png(s, tmp_path, i) for i, s in enumerate(_scans(case, pages), 1)]
    res = decode(scans, fmt)
    if case["starts_with_input"]:
        assert res.data[: len(data)] == data
    assert len(res.data) == case["c_output_size"]
    assert digest(res.data) == case["c_output_sha256"]


FULL = [c for c in DECODER["cases"] if c["group"] == "full_size"]
STORED = [c for c in DECODER["cases"] if c["group"] == "small"]


@pytest.mark.parametrize("case", FULL, ids=_name)
def test_decodes_like_c_full_size(case, tmp_path):
    _decoder_case(case, tmp_path)


@pytest.mark.parametrize("case", STORED, ids=_name)
def test_decodes_like_c_stored_scans(case, tmp_path):
    _decoder_case(case, tmp_path)


def _internal_scan(case, tmp_path):
    fmt = PageFormat.parse(INTERNALS["format"])
    if "scan_files" in case:
        (name,) = case["scan_files"]
        return fmt, read_scan(C_DIR / name)
    page = next(encode(seeded_bytes(INTERNALS["seed"], INTERNALS["size"]), fmt)).pixels
    return fmt, _through_png(fake_scan(page, **case["recipe"]), tmp_path, 1)


def _locate(img, fmt, opts):
    lv = analyze_levels(img, opts)
    img = remove_border_dirt(img, lv.fill_cut)
    geom = compute_geometry(find_corners(img, lv.cut), fmt, opts)
    pos, cuts = sync_crosses(img, geom, fmt, lv, opts)
    return img, geom, pos, cuts


@pytest.mark.parametrize("case", INTERNALS["cases"], ids=_name)
def test_crosses_like_c(case, tmp_path):
    fmt, img = _internal_scan(case, tmp_path)
    _, _, pos, cuts = _locate(img, fmt, DecodeOptions())
    # C prints crosses[x][y] with y outer and x inner, as hex floats.
    rows = [[float.fromhex(v) for v in row] for row in case["crosses"]]
    c = np.array(rows).reshape(fmt.ycrosses, fmt.xcrosses, 3).transpose(1, 0, 2)
    assert np.abs(pos - c[..., :2]).max() == 0
    assert np.abs(cuts - c[..., 2].astype(np.float32)).max() == 0


@pytest.mark.parametrize("case", INTERNALS["cases"], ids=_name)
def test_sampled_bits_like_c(case, tmp_path):
    fmt, img = _internal_scan(case, tmp_path)
    opts = DecodeOptions()
    img, geom, pos, cuts = _locate(img, fmt, opts)
    img = blur(minmax(img, geom, opts), geom, opts)
    bits = sample_bits(img, pos, cuts, geom, fmt, opts)[: fmt.used_bits]
    assert array_digest(bits, np.uint8) == case["bits_sha256"]


def test_stored_scans_are_the_only_random_inputs():
    cases = DECODER["cases"] + INTERNALS["cases"]
    assert cases
    for case in cases:
        assert ("scan_files" in case) != ("recipe" in case), case["name"]
        if "scan_files" in case:
            for name in case["scan_files"]:
                assert name.startswith("scans/") and (C_DIR / name).is_file(), name
        else:
            assert set(case["recipe"]) <= {"scale"}, case["name"]
            assert case["recipe"].get("scale", 3) in REGENERATED_SCALES, case["name"]


def test_vectors_are_small():
    files = [f for f in HERE.rglob("*") if f.is_file() and "__pycache__" not in f.parts]
    total = sum(f.stat().st_size for f in files)
    assert total < 2_000_000
