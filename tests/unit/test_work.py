# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The background work functions (no Qt)."""

import gc
import os
import pickle
import stat
import subprocess
import sys
import types
from functools import cache

import numpy as np
import pytest
from PIL import Image

import optar.encoder
import optar_gui.work as work
from optar import PAPERS, PageFormat, encode
from optar.decoder import PageGrid
from optar.errors import DecodeError, OptarError
from optar.layout import channel_xy
from optar.tag import make_tag, tagged_label
from optar_gui import text
from optar_gui.document import PageOutcome, ScanInfo
from optar_gui.work import (
    NOT_DECODABLE,
    Cancelled,
    ScanWork,
    encode_to_pdf,
    process_scan,
    process_unlabelled,
)
from tests.helpers import fake_scan, parse_pdf, save_scan, seeded_bytes

A4 = PageFormat.for_paper(PAPERS["a4"])
NAME = "doc.tar"
MARGIN = 60


@cache
def document():
    """Two tagged A4 pages: (data, pages)."""
    data = seeded_bytes(1, 250_000)
    tag = make_tag(data)
    pages = tuple(encode(data, A4, lambda p, t: tagged_label(tag, NAME, p, t)))
    return data, pages


@cache
def flipped_positions():
    """60 channel positions in 60 different symbols: all correctable."""
    rng = np.random.default_rng(9)
    syms = rng.choice(A4.fec_syms, 60, replace=False)
    bits = rng.integers(0, A4.fec_largebits, 60)
    return np.sort(syms + bits * A4.fec_syms)


def flipped_page():
    """Page 1 with the cells of flipped_positions() inverted."""
    _, pages = document()
    xs, ys = channel_xy(A4)
    pos = flipped_positions()
    out = pages[0].pixels.copy()
    out[ys[pos] + A4.border, xs[pos] + A4.border] ^= 255
    return out


def cell_centres(scale):
    """Scan pixel-centre coordinates (x, y) of the flipped cells, upright."""
    xs, ys = channel_xy(A4)
    pos = flipped_positions()
    cx = MARGIN + scale * (xs[pos] + A4.border) + (scale - 1) / 2
    cy = MARGIN + scale * (ys[pos] + A4.border) + (scale - 1) / 2
    return np.column_stack([cx, cy])


def write(tmp_path, name, image):
    path = tmp_path / name
    save_scan(path, image)
    return str(path)


@pytest.fixture(scope="module")
def clean_work(tmp_path_factory):
    _, pages = document()
    path = write(tmp_path_factory.mktemp("clean"), "p1.png", fake_scan(pages[0].pixels, scale=1))
    return process_scan(path)


@pytest.fixture(scope="module")
def flipped_works(tmp_path_factory):
    """process_scan of the flipped page at scale 1: upright, upside down, landscape."""
    d = tmp_path_factory.mktemp("flipped")
    upright = fake_scan(flipped_page(), scale=1, margin=MARGIN)
    return {
        turns: process_scan(write(d, f"r{turns}.png", np.rot90(upright, -turns)))
        for turns in (0, 2, 1)
    }


def check_identified(w, page=1):
    data, _ = document()
    assert isinstance(w, ScanWork)
    assert w.info == ScanInfo(A4.to_string(), 2, page, NAME, make_tag(data))
    assert w.reason == ""
    assert isinstance(w.outcome, PageOutcome)
    assert w.outcome.lost == 0
    assert w.marks is not None and w.marks.dtype == np.float32 and w.marks.ndim == 2


# --- process_scan -----------------------------------------------------------------


def test_process_scan_good_page(clean_work):
    data, _ = document()
    w = clean_work
    check_identified(w)
    assert len(w.outcome.data) == A4.net_bits // 8 == 199773
    assert w.outcome.data == data[: A4.net_bits // 8]
    assert w.outcome.histogram == (A4.fec_syms, 0, 0, 0)
    assert w.marks.shape == (0, 2)
    assert w.rotation == 0
    assert w.size == (A4.width + 2 * MARGIN, A4.height + 2 * MARGIN)


def test_process_scan_marks_flipped_bits(tmp_path):
    scale = 3
    path = write(tmp_path, "flipped.png", fake_scan(flipped_page(), scale=scale, margin=MARGIN))
    w = process_scan(path)
    check_identified(w)
    data, _ = document()
    assert w.outcome.data == data[: A4.net_bits // 8]
    assert w.outcome.histogram[1] == 60 and sum(w.outcome.histogram[2:]) == 0
    centres = cell_centres(scale)
    assert w.marks.shape == (len(centres), 2)
    # Every mark is at a flipped cell, and every flipped cell has its mark.
    dist = np.hypot(*(w.marks[:, None, :] - centres[None, :, :]).transpose(2, 0, 1))
    assert dist.min(axis=1).max() <= 1.5
    assert dist.min(axis=0).max() <= 1.5


def test_process_scan_rotated_reports_upright_marks(flipped_works):
    upright = flipped_works[0]
    check_identified(upright)
    assert upright.rotation == 0
    assert upright.marks.shape == (60, 2)
    dist = np.hypot(*(upright.marks[:, None, :] - cell_centres(1)[None]).transpose(2, 0, 1))
    assert dist.min(axis=1).max() <= 1.5
    for turns in (2, 1):
        w = flipped_works[turns]
        check_identified(w)
        assert w.rotation == turns
        assert w.size == upright.size
        assert w.outcome == upright.outcome
        # Both in channel order, so row i is the same bit in both.
        assert w.marks.shape == upright.marks.shape
        assert np.abs(w.marks - upright.marks).max() <= 1.5


def blank_png(tmp_path):
    return write(tmp_path, "blank.png", np.full((1100, 800), 255, np.uint8))


def text_file_named_png(tmp_path):
    path = tmp_path / "notes.png"
    path.write_text("not an image\n")
    return str(path)


def random_noise_png(tmp_path):
    rng = np.random.default_rng(3)
    return write(tmp_path, "noise.png", rng.integers(0, 256, (1100, 800), dtype=np.uint8))


def gif_file(tmp_path):
    path = tmp_path / "scan.gif"
    Image.fromarray(np.full((40, 30), 255, np.uint8)).save(path, format="GIF")
    return str(path)


def directory(tmp_path):
    path = tmp_path / "folder.png"
    path.mkdir()
    return str(path)


def missing_file(tmp_path):
    return str(tmp_path / "missing.png")


BAD_INPUTS = [blank_png, text_file_named_png, random_noise_png, gif_file, directory, missing_file]


@pytest.mark.parametrize("make", BAD_INPUTS, ids=lambda f: f.__name__)
def test_process_scan_never_raises_for_bad_input(tmp_path, make):
    path = make(tmp_path)
    w = process_scan(path)
    assert w.info is None and w.outcome is None and w.marks is None
    assert w.reason
    if make in (blank_png, random_noise_png):
        assert w.reason in ("no page found", "label unreadable")
        assert w.size == (800, 1100)
    else:
        assert w.reason.startswith("cannot read image ")
        assert w.size == (0, 0)


def test_process_scan_decode_failure_keeps_identity(tmp_path, monkeypatch):
    data, pages = document()
    path = write(tmp_path, "p2.png", fake_scan(pages[1].pixels, scale=1))

    def fail(grid, **kw):
        raise DecodeError("sampling went wrong")

    monkeypatch.setattr(work, "decode_located", fail)
    w = process_scan(path)
    assert w.info == ScanInfo(A4.to_string(), 2, 2, NAME, make_tag(data))
    assert w.outcome is None and w.marks is None
    assert w.reason == "sampling went wrong"


def turns_true_after(n):
    calls = []

    def cancelled():
        calls.append(None)
        return len(calls) > n

    cancelled.calls = calls
    return cancelled


class FakeStages:
    """Stand-ins for the library stages, recording which ones ran."""

    def __init__(self, monkeypatch, clean_work):
        self.ran = []
        self.work = clean_work
        monkeypatch.setattr(work, "read_scan", self.read_scan)
        monkeypatch.setattr(work, "identify_scan", self.identify_scan)
        monkeypatch.setattr(work, "decode_located", self.decode_located)
        monkeypatch.setattr(work, "decode_unlabelled", self.decode_unlabelled)
        monkeypatch.setattr(work, "_outcome", lambda result: (self.work.outcome, self.work.marks))

    def read_scan(self, path):
        self.ran.append("read")
        return np.zeros((20, 10), np.uint8)

    def identify_scan(self, image):
        self.ran.append("identify")

        class Identity:
            fmt, rotation, page, total, name, tag, grid = A4, 0, 1, 2, NAME, None, object()

        return Identity()

    def decode_located(self, grid, detail):
        self.ran.append("decode")
        return object()

    def decode_unlabelled(self, image, fmt, detail):
        self.ran.append("decode")

        class Result:
            class stats:
                symbols, uncorrectable = A4.fec_syms, 0

        return 0, Result()


@pytest.mark.parametrize("n,ran", [
    (0, ["read"]),
    (1, ["read", "identify"]),
    (2, ["read", "identify", "decode"]),
])
def test_process_scan_cancelled(monkeypatch, clean_work, n, ran):
    stages = FakeStages(monkeypatch, clean_work)
    cancelled = turns_true_after(n)
    with pytest.raises(Cancelled):
        process_scan("scan.png", cancelled)
    assert stages.ran == ran and len(cancelled.calls) == n + 1


def test_process_scan_not_cancelled_checks_three_times(monkeypatch, clean_work):
    FakeStages(monkeypatch, clean_work)
    cancelled = turns_true_after(3)
    w = process_scan("scan.png", cancelled)
    assert w.outcome is clean_work.outcome and len(cancelled.calls) == 3


def test_process_scan_cancelled_for_real(tmp_path):
    _, pages = document()
    path = write(tmp_path, "p1.png", fake_scan(pages[0].pixels, scale=1))
    with pytest.raises(Cancelled):
        process_scan(path, lambda: True)


def reachable(root):
    """Every object reachable from root through gc referents, not via classes or modules."""
    seen, stack = {}, [root]
    while stack:
        obj = stack.pop()
        if id(obj) in seen or isinstance(obj, type | types.ModuleType):
            continue
        seen[id(obj)] = obj
        stack.extend(gc.get_referents(obj))
    return seen.values()


def test_result_is_small_and_holds_no_grid(clean_work, flipped_works):
    for w in (clean_work, flipped_works[2]):
        assert len(pickle.dumps(w)) < 1_000_000
        objects = list(reachable(w))
        assert not any(isinstance(o, PageGrid) for o in objects)
        big = [o for o in objects if isinstance(o, np.ndarray) and o.nbytes > 100_000]
        assert big == []


# --- process_unlabelled -----------------------------------------------------------


def blacken_label(pixels):
    out = np.array(pixels, copy=True)
    top = A4.border + A4.data_height
    out[top : top + A4.text_height, A4.border : A4.width - A4.border] = 0
    return out


@pytest.mark.parametrize("turns", [0, 2])
def test_process_unlabelled(tmp_path, turns):
    data, pages = document()
    upright = fake_scan(blacken_label(pages[0].pixels), scale=1, margin=MARGIN)
    path = write(tmp_path, "black.png", np.rot90(upright, -turns))
    assert process_scan(path).reason == "label unreadable"
    w = process_unlabelled(path, A4.to_string())
    assert w.info is None and w.reason == ""
    assert w.rotation == turns
    assert w.size == (upright.shape[1], upright.shape[0])
    assert w.outcome.data == data[: A4.net_bits // 8] and w.outcome.lost == 0
    assert w.marks.shape == (0, 2)


def test_process_unlabelled_blank_image(tmp_path):
    w = process_unlabelled(blank_png(tmp_path), A4.to_string())
    assert w.info is None and w.outcome is None and w.marks is None and w.reason


def test_process_unlabelled_unreadable_file(tmp_path):
    w = process_unlabelled(text_file_named_png(tmp_path), A4.to_string())
    assert w.outcome is None and w.reason.startswith("cannot read image ")


def test_process_unlabelled_garbage_in_every_rotation(monkeypatch, clean_work):
    stages = FakeStages(monkeypatch, clean_work)

    def decode_unlabelled(image, fmt, detail):
        stages.ran.append("decode")

        class Result:
            class stats:
                symbols, uncorrectable = A4.fec_syms, A4.fec_syms // 4 + 1

        return 2, Result()

    monkeypatch.setattr(work, "decode_unlabelled", decode_unlabelled)
    w = process_unlabelled("scan.png", A4.to_string())
    assert w.outcome is None and w.marks is None and w.reason == NOT_DECODABLE
    assert w.rotation == 2 and w.size == (10, 20)


@pytest.mark.parametrize("n,ran", [(0, ["read"]), (1, ["read", "decode"])])
def test_process_unlabelled_cancelled(monkeypatch, clean_work, n, ran):
    stages = FakeStages(monkeypatch, clean_work)
    with pytest.raises(Cancelled):
        process_unlabelled("scan.png", A4.to_string(), turns_true_after(n))
    assert stages.ran == ran


# --- encode_to_pdf ----------------------------------------------------------------


def write_source(tmp_path, data):
    src = tmp_path / "source.bin"
    src.write_bytes(data)
    return str(src)


def test_encode_to_pdf_round_trip(tmp_path):
    data = seeded_bytes(7, 250_000)
    dest = tmp_path / "out.pdf"
    assert encode_to_pdf(write_source(tmp_path, data), str(dest), "a4", "my file") == 2
    pdf = parse_pdf(dest)
    tag = make_tag(data)
    want = list(encode(data, A4, lambda p, t: tagged_label(tag, "my file", p, t)))
    assert len(pdf) == len(want) == 2
    for got, page in zip(pdf, want, strict=True):
        assert np.array_equal(got["pixels"], page.pixels)
    assert sorted(os.listdir(tmp_path)) == ["out.pdf", "source.bin"]


def test_encode_to_pdf_letter_empty_file(tmp_path):
    dest = tmp_path / "out.pdf"
    assert encode_to_pdf(write_source(tmp_path, b""), str(dest), "letter", "empty") == 1
    letter = PageFormat.for_paper(PAPERS["letter"])
    want = next(encode(b"", letter, lambda p, t: tagged_label(make_tag(b""), "empty", p, t)))
    assert np.array_equal(parse_pdf(dest)[0]["pixels"], want.pixels)


@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0, reason="root can write")
def test_encode_to_pdf_failure_leaves_existing_file(tmp_path):
    dest = tmp_path / "out.pdf"
    dest.write_bytes(b"precious")
    dest.chmod(stat.S_IRUSR)
    try:
        with pytest.raises(OptarError, match="cannot write"):
            encode_to_pdf(write_source(tmp_path, b"x" * 1000), str(dest), "a4", "x")
        assert dest.read_bytes() == b"precious"
        assert sorted(os.listdir(tmp_path)) == ["out.pdf", "source.bin"]
    finally:
        dest.chmod(stat.S_IRUSR | stat.S_IWUSR)


def test_encode_to_pdf_too_many_pages(tmp_path, monkeypatch):
    monkeypatch.setattr(optar.encoder, "MAX_PAGES", 1)
    dest = tmp_path / "out.pdf"
    with pytest.raises(OptarError, match="too many pages"):
        encode_to_pdf(write_source(tmp_path, seeded_bytes(2, 250_000)), str(dest), "a4", "x")
    assert sorted(os.listdir(tmp_path)) == ["source.bin"]


@pytest.mark.parametrize("existing", [False, True])
def test_encode_to_pdf_cancelled_midway(tmp_path, existing):
    dest = tmp_path / "out.pdf"
    if existing:
        dest.write_bytes(b"precious")
    src = write_source(tmp_path, seeded_bytes(2, 250_000))
    cancelled = turns_true_after(1)  # the first page is written, the second is not
    with pytest.raises(Cancelled):
        encode_to_pdf(src, str(dest), "a4", "x", cancelled)
    assert len(cancelled.calls) == 2
    if existing:
        assert dest.read_bytes() == b"precious"
        assert sorted(os.listdir(tmp_path)) == ["out.pdf", "source.bin"]
    else:
        assert sorted(os.listdir(tmp_path)) == ["source.bin"]


def test_encode_to_pdf_refuses_the_source_as_destination(tmp_path):
    data = seeded_bytes(3, 1000)
    src = write_source(tmp_path, data)
    spellings = [src, os.path.join(str(tmp_path), ".", "source.bin")]
    if hasattr(os, "link"):
        os.link(src, tmp_path / "hard.bin")  # another name for the same file
        spellings.append(str(tmp_path / "hard.bin"))
    for dest in spellings:
        with pytest.raises(OptarError, match=text.DEST_IS_SOURCE):
            encode_to_pdf(src, dest, "a4", "x")
    assert (tmp_path / "source.bin").read_bytes() == data
    expected = ["hard.bin", "source.bin"] if hasattr(os, "link") else ["source.bin"]
    assert sorted(os.listdir(tmp_path)) == expected


def test_same_file_compares_files_and_spellings(tmp_path):
    a = write_source(tmp_path, b"a")
    assert work.same_file(a, os.path.join(str(tmp_path), "x", "..", "source.bin"))
    assert not work.same_file(a, str(tmp_path / "other.bin"))  # does not exist
    (tmp_path / "copy.bin").write_bytes(b"a")
    assert not work.same_file(a, str(tmp_path / "copy.bin"))


def test_encode_to_pdf_missing_source(tmp_path):
    src = tmp_path / "missing.bin"
    with pytest.raises(OptarError, match=f"cannot read {src}"):
        encode_to_pdf(str(src), str(tmp_path / "out.pdf"), "a4", "x")
    assert os.listdir(tmp_path) == []


# --- module -----------------------------------------------------------------------


def test_work_module_does_not_import_qt():
    code = (
        "import sys, optar_gui.work\n"
        "bad = [m for m in sys.modules if m.split('.')[0] in ('PySide6', 'shiboken6')]\n"
        "print(','.join(bad))\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_library_does_not_import_the_application():
    code = (
        "import sys, pkgutil, importlib, optar\n"
        "for m in pkgutil.walk_packages(optar.__path__, 'optar.'):\n"
        "    if m.name != 'optar.__main__':\n"
        "        importlib.import_module(m.name)\n"
        "bad = [m for m in sys.modules if m.split('.')[0] in ('PySide6', 'optar_gui')]\n"
        "print(','.join(bad))\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


# --- Preparing a file to put on paper and how its name prints -------------------------


@pytest.mark.parametrize("nbytes", [0, 1000, 3 * 2**20 + 5])
def test_prepare_file_gives_size_and_tag(tmp_path, nbytes):
    data = seeded_bytes(11, nbytes)
    assert work.prepare_file(write_source(tmp_path, data)) == work.FileFacts(
        nbytes, make_tag(data))


def test_prepare_file_cancelled_and_unreadable(tmp_path):
    src = write_source(tmp_path, seeded_bytes(12, 3 * 2**20))
    with pytest.raises(Cancelled):
        work.prepare_file(src, turns_true_after(1))
    with pytest.raises(OptarError, match="missing.bin"):
        work.prepare_file(str(tmp_path / "missing.bin"))


def test_name_preview_matches_the_label_the_encoder_prints():
    from optar.font import label_text
    from optar.label import printed_label

    data = seeded_bytes(13, 250_000)
    tag = make_tag(data)
    preview = work.name_preview("a4", tag, "data.bin")
    assert preview.total == 2
    full = printed_label(A4, label_text(A4, 1, 2, tagged_label(tag, "data.bin", 1, 2)))
    assert full == f"  {A4.to_string()} 1/2 {preview.printed}"
    assert preview.printed == f"{tag.page_text(1, 2)} data.bin"
    assert (preview.dropped, preview.cut) == ("", False)


def test_name_preview_drops_and_cuts():
    tag = make_tag(b"x" * 1000)
    foreign = work.name_preview("a4", tag, "отпуск.tar")
    assert foreign.printed == f"{tag.page_text(1, 1)} .tar"
    assert (foreign.dropped, foreign.cut) == ("отпуск", False)
    assert work.name_preview("letter", tag, "о\tо").dropped == "о\t"
    long_name = "y" * 200
    cut = work.name_preview("a4", tag, long_name)
    assert cut.cut and cut.dropped == ""
    assert long_name.startswith(cut.printed[len(tag.page_text(1, 1)) + 1:])
    empty = work.name_preview("letter", make_tag(b""), "")
    assert (empty.total, empty.printed, empty.cut) == (0, make_tag(b"").page_text(1, 0), False)


def test_name_preview_cut_on_a_later_page_only():
    # A name that just fits page 1 of 10 is cut on page 10, whose number is longer.
    from optar.label import label_capacity
    from optar.tag import Tag

    tag = Tag(10 * (A4.net_bits // 8), "0123abcd")  # a ten-page file
    used = len(f"  {A4.to_string()} 1/10 {tag.page_text(1, 10)} ")
    name = "z" * (label_capacity(A4) - used)
    preview = work.name_preview("a4", tag, name)
    assert preview.printed.endswith(name)
    assert preview.cut
