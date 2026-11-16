# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import os

import numpy as np
import pytest
from PIL import Image

from optar.cli import main
from optar.encoder import encode
from optar.format import PAPERS, PageFormat
from tests.helpers import fake_scan, parse_pdf, save_scan, seeded_bytes


@pytest.fixture
def infile(tmp_path):
    p = tmp_path / "in.bin"
    p.write_bytes(seeded_bytes(4, 3000))
    return p


HINT = "Check that --paper matches the printout and that the page is scanned upright."


@pytest.fixture(scope="module")
def a4_scan(tmp_path_factory):
    """One encoded A4 page scan shared by the decode tests: (base, data)."""
    d = tmp_path_factory.mktemp("a4scan")
    data = seeded_bytes(4, 3000)
    return scans(d, data), data


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
    data = seeded_bytes(4, 3000)
    base = scans(tmp_path, data)
    assert main(["decode", base, "-o", str(tmp_path / "out.bin")]) == 0
    assert (tmp_path / "out.bin").read_bytes()[:3000] == data
    assert main(["decode", base]) == 0
    assert capsysbinary.readouterr().out[:3000] == data


def test_letter_round_trip_through_cli(tmp_path):
    data = seeded_bytes(6, 3000)
    base = scans(tmp_path, data, paper="letter")
    assert main(["decode", base, "--paper", "letter", "-o", str(tmp_path / "o")]) == 0
    assert (tmp_path / "o").read_bytes()[:3000] == data


def test_wrong_paper_exits_1_with_hint(a4_scan, tmp_path, capsys):
    base, _ = a4_scan
    assert main(["decode", base, "--paper", "letter", "-o", str(tmp_path / "o")]) == 1
    err = capsys.readouterr().err
    assert err.rstrip().endswith(HINT) and "Traceback" not in err


def test_blank_scan_exits_2_without_traceback(tmp_path, capsys):
    save_scan(tmp_path / "s_0001.png", np.full((500, 400), 255, np.uint8))
    assert main(["decode", str(tmp_path / "s"), "-o", str(tmp_path / "o")]) == 2
    err = capsys.readouterr().err
    assert err.startswith("optar: ") and "Traceback" not in err
    assert HINT in err


def test_decode_error_names_the_failing_page(tmp_path, capsys):
    fmt = PageFormat.for_paper(PAPERS["a4"])
    base = scans(tmp_path, seeded_bytes(1, 2 * fmt.net_bits // 8 + 5), skip=(2,))
    save_scan(tmp_path / "scan_0002.png", np.full((2400, 1700), 255, np.uint8))
    assert main(["decode", base, "-o", str(tmp_path / "o")]) == 2
    assert capsys.readouterr().err.splitlines()[-1] == (
        f"optar: scan_0002.png: cannot find upper left corner. {HINT}"
    )
    assert not (tmp_path / "o").exists()


def test_numbering_gap_warns_and_exits_1(tmp_path, capsys):
    fmt = PageFormat.for_paper(PAPERS["a4"])
    base = scans(tmp_path, seeded_bytes(1, 2 * fmt.net_bits // 8 + 5), skip=(2,))
    assert main(["decode", base, "-o", str(tmp_path / "o")]) == 1
    assert "scan_0002.png is missing but scan_0003.png exists" in capsys.readouterr().err


def test_usage_errors(tmp_path, capsys):
    assert main(["decode", str(tmp_path / "nothing")]) == 2
    assert main(["encode", str(tmp_path / "missing.bin")]) == 2
    (tmp_path / "in.bin").write_bytes(b"x")
    assert (
        main(
            [
                "encode",
                str(tmp_path / "in.bin"),
                "-o",
                str(tmp_path / "o"),
                "--format",
                "0-80-93-24-3-1-2-24",
            ]
        )
        == 2
    )  # does not fit A4
    assert "fit" in capsys.readouterr().err
    assert not (tmp_path / "o.pdf").exists()
    # Inside the paper edge but with a 0.09 pt top margin: a printer would clip it.
    assert main(["encode", str(tmp_path / "in.bin"), "-o", str(tmp_path / "o"),
                 "--format", "0-65-95-24-3-1-2-24"]) == 2  # fmt: skip
    assert "fit" in capsys.readouterr().err
    assert not (tmp_path / "o.pdf").exists()
    with pytest.raises(SystemExit) as e:
        main(["encode", "x", "--paper", "legal"])
    assert e.value.code == 2


def test_version(capsys):
    import optar

    with pytest.raises(SystemExit):
        main(["--version"])
    assert optar.__version__ in capsys.readouterr().out


def test_decode_output_is_byte_exact_with_zero_padding(a4_scan, tmp_path):
    base, data = a4_scan
    fmt = PageFormat.for_paper(PAPERS["a4"])
    assert main(["decode", base, "-o", str(tmp_path / "o")]) == 0
    out = (tmp_path / "o").read_bytes()
    assert len(out) == fmt.net_bits // 8
    assert out == data + bytes(len(out) - len(data))


def test_debug_images_only_with_flag(a4_scan, tmp_path):
    base, _ = a4_scan
    debug = base + "_0001_debug.png"
    assert main(["decode", base, "-o", str(tmp_path / "o")]) == 0
    assert not os.path.exists(debug)
    assert main(["decode", base, "--debug-images", "-o", str(tmp_path / "o")]) == 0
    with Image.open(debug) as im, Image.open(base + "_0001.png") as scan:
        assert im.mode == "L" and im.size == scan.size


def test_no_pages_names_first_file(tmp_path, capsys):
    assert main(["decode", str(tmp_path / "nothing")]) == 2
    err = capsys.readouterr().err
    assert "cannot open" in err and "nothing_0001.png" in err


def test_encode_unwritable_output_names_file(tmp_path, infile, capsys):
    for extra in ([], ["--to", "png"]):
        out = str(tmp_path / "nodir" / "x")
        assert main(["encode", str(infile), "-o", out, *extra]) == 2
        err = capsys.readouterr().err
        assert err.startswith("optar: ") and "nodir" in err and "Traceback" not in err


def test_decode_unwritable_output_names_file(a4_scan, tmp_path, capsys):
    base, _ = a4_scan
    assert main(["decode", base, "-o", str(tmp_path / "nodir" / "out.bin")]) == 2
    err = capsys.readouterr().err
    assert err.splitlines()[-1].startswith("optar: ") and "nodir" in err and "Traceback" not in err


def _encode_args(infile, out, *extra):
    return ["encode", str(infile), "-o", str(out), *extra]


def _no_temp_files(directory):
    return not list(directory.glob("*.tmp"))


@pytest.mark.skipif(os.name == "nt" or os.geteuid() == 0, reason="needs POSIX permissions")
def test_failed_write_keeps_existing_read_only_pdf(tmp_path, infile, capsys):
    ro = tmp_path / "ro"
    ro.mkdir()
    existing = ro / "x.pdf"
    existing.write_bytes(b"precious")
    existing.chmod(0o444)
    ro.chmod(0o555)
    try:
        assert main(_encode_args(infile, ro / "x")) == 2
        assert existing.read_bytes() == b"precious"
        assert _no_temp_files(ro)
        assert "cannot write" in capsys.readouterr().err
    finally:
        ro.chmod(0o755)


@pytest.mark.skipif(os.name == "nt" or os.geteuid() == 0, reason="needs POSIX permissions")
def test_read_only_existing_file_in_writable_directory_is_kept(tmp_path, infile, capsys):
    existing = tmp_path / "x.pdf"
    existing.write_bytes(b"precious")
    existing.chmod(0o444)
    assert main(_encode_args(infile, tmp_path / "x")) == 2
    assert existing.read_bytes() == b"precious"
    assert _no_temp_files(tmp_path)
    assert "cannot write" in capsys.readouterr().err


def test_failed_encode_keeps_existing_pdf(tmp_path, infile, capsys, monkeypatch):
    import optar.encoder

    monkeypatch.setattr(optar.encoder, "MAX_PAGES", 0)
    existing = tmp_path / "lim.pdf"
    existing.write_bytes(b"precious")
    assert main(_encode_args(infile, tmp_path / "lim")) == 2
    assert existing.read_bytes() == b"precious"
    assert _no_temp_files(tmp_path)
    assert "too many pages" in capsys.readouterr().err


@pytest.mark.parametrize("kind", ["pdf", "png", "pgm"])
def test_page_limit_creates_no_file(tmp_path, infile, capsys, monkeypatch, kind):
    import optar.encoder

    monkeypatch.setattr(optar.encoder, "MAX_PAGES", 0)
    assert main(_encode_args(infile, tmp_path / "big", "--to", kind)) == 2
    err = capsys.readouterr().err
    assert "too many pages: 1 needed, at most 0" in err
    assert sorted(p.name for p in tmp_path.iterdir()) == ["in.bin"]


def test_failure_during_pdf_keeps_existing_file(tmp_path, infile, monkeypatch):
    import optar.cli

    def broken(data, fmt, label=""):
        yield from list(encode(data, fmt, label))[:1]
        raise RuntimeError("boom")

    existing = tmp_path / "x.pdf"
    existing.write_bytes(b"precious")
    monkeypatch.setattr(optar.cli, "encode", broken)
    with pytest.raises(RuntimeError, match="boom"):
        main(_encode_args(infile, tmp_path / "x"))
    assert existing.read_bytes() == b"precious"
    assert _no_temp_files(tmp_path)


def test_failed_page_file_write_keeps_existing_page(tmp_path, infile, monkeypatch):
    import optar.cli

    existing = tmp_path / "x_0001.png"
    existing.write_bytes(b"precious")

    def half_write(path, pixels):
        with open(path, "wb") as f:
            f.write(b"trunc")
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(optar.cli, "write_png", half_write)
    assert main(_encode_args(infile, tmp_path / "x", "--to", "png")) == 2
    assert existing.read_bytes() == b"precious"
    assert _no_temp_files(tmp_path)


def test_successful_encode_replaces_existing_file(tmp_path, infile):
    existing = tmp_path / "x.pdf"
    existing.write_bytes(b"old")
    assert main(_encode_args(infile, tmp_path / "x")) == 0
    assert existing.read_bytes().startswith(b"%PDF-")
    assert len(parse_pdf(existing)) == 1
    assert _no_temp_files(tmp_path)
    if os.name != "nt":
        umask = os.umask(0)
        os.umask(umask)
        assert existing.stat().st_mode & 0o777 == 0o666 & ~umask


def test_failed_decode_write_keeps_existing_output(a4_scan, tmp_path, monkeypatch):
    import optar.cli

    base, data = a4_scan
    out = tmp_path / "out.bin"
    out.write_bytes(b"precious")
    real_replace = os.replace

    def failing_replace(src, dst):
        raise OSError(13, "Permission denied")

    monkeypatch.setattr(optar.cli.os, "replace", failing_replace)
    assert main(["decode", base, "-o", str(out)]) == 2
    assert out.read_bytes() == b"precious"
    assert _no_temp_files(tmp_path)
    monkeypatch.setattr(optar.cli.os, "replace", real_replace)
    assert main(["decode", base, "-o", str(out)]) == 0
    assert out.read_bytes()[: len(data)] == data


def _spy_labels(monkeypatch):
    """The labels optar.cli passes to encode, each as the list of page labels it gives."""
    import optar.cli

    labels = []

    def spy(data, fmt, label=""):
        pages = list(encode(data, fmt, label))
        labels.append([label(p.number, p.total) if callable(label) else label for p in pages])
        return iter(pages)

    monkeypatch.setattr(optar.cli, "encode", spy)
    return labels


def test_default_label_is_tagged_output_file_name(tmp_path, infile, monkeypatch):
    from optar.tag import make_tag, tagged_label

    labels = _spy_labels(monkeypatch)
    tag = make_tag(infile.read_bytes())
    assert main(_encode_args(infile, tmp_path / "sub" / "name", "--to", "pgm")) == 2  # no dir
    (tmp_path / "sub").mkdir()
    assert main(_encode_args(infile, tmp_path / "sub" / "name", "--to", "pgm")) == 0
    assert main(_encode_args(infile, tmp_path / "x", "--to", "pgm", "--label", "my name")) == 0
    assert labels[-2:] == [[tagged_label(tag, "name", 1, 1)], [tagged_label(tag, "my name", 1, 1)]]
    assert labels[-1] == [f"[{tag.size}:{tag.fingerprint}:{tag.check(1, 1)}] my name"]


def test_no_tag_keeps_plain_label(tmp_path, infile, monkeypatch):
    labels = _spy_labels(monkeypatch)
    (tmp_path / "sub").mkdir()
    assert main(_encode_args(infile, tmp_path / "sub" / "name", "--to", "pgm", "--no-tag")) == 0
    args = _encode_args(infile, tmp_path / "x", "--to", "pgm", "--label", "mine", "--no-tag")
    assert main(args) == 0
    assert main(_encode_args(infile, tmp_path / "y", "--to", "pgm", "--no-tag")) == 0
    assert labels == [["name"], ["mine"], ["y"]]


def test_no_tag_passes_the_plain_string(tmp_path, infile, monkeypatch):
    import optar.cli

    passed = []

    def spy(data, fmt, label=""):
        passed.append(label)
        return encode(data, fmt, label)

    monkeypatch.setattr(optar.cli, "encode", spy)
    assert main(_encode_args(infile, tmp_path / "x", "--to", "pgm", "--no-tag")) == 0
    assert passed == ["x"]


def test_encode_adds_tag_by_default(tmp_path):
    from optar.imageio import pgm_bytes
    from optar.tag import make_tag, tagged_label

    data = seeded_bytes(5, 250_000)
    src = tmp_path / "big.bin"
    src.write_bytes(data)
    assert main(_encode_args(src, tmp_path / "out", "--to", "pgm")) == 0
    fmt = PageFormat.for_paper(PAPERS["a4"])
    tag = make_tag(data)
    want = list(encode(data, fmt, lambda p, t: tagged_label(tag, "out", p, t)))
    assert len(want) == 2 and tag.check(1, 2) != tag.check(2, 2)
    for page in want:
        got = (tmp_path / f"out_{page.number:04d}.pgm").read_bytes()
        assert got == pgm_bytes(page.pixels)


def test_no_tag_output_is_plain_label_output(tmp_path, infile):
    from optar.imageio import pgm_bytes

    fmt = PageFormat.for_paper(PAPERS["a4"])
    want = next(encode(infile.read_bytes(), fmt, "out")).pixels
    assert main(_encode_args(infile, tmp_path / "out", "--to", "pgm", "--no-tag")) == 0
    assert (tmp_path / "out_0001.pgm").read_bytes() == pgm_bytes(want)


def test_empty_input_gets_empty_tag(tmp_path, monkeypatch):
    from optar.tag import Tag

    labels = _spy_labels(monkeypatch)
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    assert main(_encode_args(empty, tmp_path / "e", "--to", "pgm")) == 0
    assert labels == [[f"[0:e3b0c442:{Tag(0, 'e3b0c442').check(1, 0)}] e"]]
    assert sorted(p.name for p in tmp_path.glob("e_*.pgm")) == ["e_0001.pgm"]


def test_written_tag_parses_back(tmp_path, monkeypatch):
    from optar.tag import split_label

    labels = _spy_labels(monkeypatch)
    data = seeded_bytes(5, 250_000)
    src = tmp_path / "big.bin"
    src.write_bytes(data)
    assert main(_encode_args(src, tmp_path / "big", "--to", "pgm")) == 0
    fmt = PageFormat.for_paper(PAPERS["a4"])
    total = len(labels[-1])
    assert total == 2
    tags = set()
    for page, label in enumerate(labels[-1], start=1):
        tag, check, name = split_label(label)
        assert tag is not None and name == "big"
        assert tag.matches(data) and tag.fits(total, fmt)
        assert check == tag.check(page, total)
        tags.add(tag)
    assert len(tags) == 1
    assert labels[-1][0] != labels[-1][1]  # the checks differ between the pages


def test_every_option_has_help():
    from optar.cli import _build_parser

    parser = _build_parser()
    subparsers = next(a for a in parser._actions if a.choices and isinstance(a.choices, dict))
    for name, sub in subparsers.choices.items():
        for action in sub._actions:
            assert action.help, f"{name} {action.option_strings or action.dest} has no help"


posix_special_files = pytest.mark.skipif(os.name == "nt", reason="uses POSIX special files")


@posix_special_files
def test_decode_to_dev_null_writes_the_device(a4_scan):
    import stat

    base, _ = a4_scan
    assert main(["decode", base, "-o", os.devnull]) == 0
    assert stat.S_ISCHR(os.stat(os.devnull).st_mode)


@posix_special_files
def test_decode_to_fifo_writes_through_the_pipe(a4_scan, tmp_path):
    import stat
    import threading

    base, data = a4_scan
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    received = []

    def reader():
        fd = os.open(fifo, os.O_RDONLY)  # blocks until the CLI opens the pipe
        with os.fdopen(fd, "rb") as f:
            received.append(f.read())

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    code = main(["decode", base, "-o", str(fifo)])
    thread.join(timeout=30)
    if thread.is_alive():
        if stat.S_ISFIFO(os.stat(fifo).st_mode):  # release the blocked reader
            os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))
        pytest.fail("the CLI never wrote to the pipe")
    assert code == 0
    assert stat.S_ISFIFO(os.stat(fifo).st_mode)
    assert received[0][: len(data)] == data
    assert received[0] == data + bytes(len(received[0]) - len(data))
    assert not list(tmp_path.glob("*.tmp"))


def test_decode_cli_matches_library_when_net_bits_not_byte_aligned(tmp_path):
    from optar.decoder import decode

    fmt = PageFormat.parse("0-65-93-24-3-2-2-24")  # Hamming order 2
    assert fmt.net_bits % 8
    data = seeded_bytes(9, fmt.net_bits // 8 + 1000)
    pages = [fake_scan(p.pixels, scale=1) for p in encode(data, fmt)]
    assert len(pages) == 2
    for number, scan in enumerate(pages, start=1):
        save_scan(tmp_path / f"h_{number:04d}.png", scan)
    out = tmp_path / "out.bin"
    assert main(["decode", str(tmp_path / "h"), "--format", fmt.to_string(), "-o", str(out)]) == 0
    got = out.read_bytes()
    assert got == decode(iter(pages), fmt).data
    assert got.startswith(data) and len(got) == 2 * fmt.net_bits // 8


# Version-1 pages: dot size and protection


def _protected_input(tmp_path, pages, dots="large", parity="standard", name="in.bin", seed=11):
    """An input file a little smaller than the most `pages` pages hold with these options."""
    from optar.container import plan
    from optar.format import PARITY, get_layout

    fmt = get_layout("a4", dots).fmt
    size = next(
        s for s in range(0, 4_000_000, 1000) if plan(s, name, fmt, PARITY[parity]).total > pages
    ) - 1000
    path = tmp_path / name
    path.write_bytes(seeded_bytes(seed, size))
    return path


def _encode_v1(tmp_path, src, base="p", *extra):
    out = tmp_path / base
    args = ["encode", str(src), "-o", str(out), "--to", "png", *extra]
    assert main(args) == 0
    return out


def test_protected_round_trip_any_order_and_orientation(tmp_path, capsys):
    src = _protected_input(tmp_path, 3)
    base = _encode_v1(tmp_path, src, "p", "--dots", "large", "--protect", "standard")
    err = capsys.readouterr().err
    assert "Scan at 300 dpi" in err and "actual size" in err
    assert sorted(p.name for p in tmp_path.glob("p_*.png")) == [
        "p_0001.png", "p_0002.png", "p_0003.png"
    ]
    one, two = tmp_path / "p_0001.png", tmp_path / "p_0002.png"
    one.rename(tmp_path / "swap")
    two.rename(one)
    (tmp_path / "swap").rename(two)
    upside = tmp_path / "p_0003.png"
    with Image.open(upside) as im:
        im.rotate(180).save(upside)
    out = tmp_path / "out.bin"
    assert main(["decode", str(base), "-o", str(out)]) == 0
    assert out.read_bytes() == src.read_bytes()
    err = capsys.readouterr().err
    assert "p_0001.png: page 2 of 3" in err and "verified" in err


def test_protected_decode_to_stdout(tmp_path, capsysbinary):
    src = _protected_input(tmp_path, 1, dots="xlarge")
    base = _encode_v1(tmp_path, src, "p", "--dots", "xlarge", "--protect", "high")
    capsysbinary.readouterr()
    assert main(["decode", str(base)]) == 0
    assert capsysbinary.readouterr().out == src.read_bytes()


def test_one_page_lost_from_twelve_is_repaired(tmp_path, capsys):
    src = _protected_input(tmp_path, 12)
    base = _encode_v1(tmp_path, src, "p", "--dots", "large", "--protect", "standard")
    assert "can lose 1 page of 12" in capsys.readouterr().err
    (tmp_path / "p_0005.png").unlink()
    out = tmp_path / "out.bin"
    assert main(["decode", str(base), "-o", str(out)]) == 0
    assert out.read_bytes() == src.read_bytes()
    err = capsys.readouterr().err
    assert "missing page 5" in err and "repaired" in err


def test_one_page_lost_from_three_is_not_saved(tmp_path, capsys):
    src = _protected_input(tmp_path, 3)
    base = _encode_v1(tmp_path, src, "p", "--dots", "large", "--protect", "standard")
    capsys.readouterr()
    (tmp_path / "p_0002.png").unlink()
    out = tmp_path / "out.bin"
    assert main(["decode", str(base), "-o", str(out)]) == 1
    assert not out.exists()
    err = capsys.readouterr().err
    assert "missing page 2" in err
    assert (
        "Rescan page 2 and decode again; --force saves what was recovered, which may be damaged."
    ) in err
    summary = next(line for line in err.splitlines() if line.startswith("optar: repaired"))
    assert "could not be repaired" in summary and "worst codeword" not in summary


@pytest.fixture(scope="module")
def twelve_pages(tmp_path_factory):
    """A 12-page Large document with Standard protection: (folder, input bytes)."""
    d = tmp_path_factory.mktemp("twelve")
    src = _protected_input(d, 12)
    _encode_v1(d, src, "p", "--dots", "large", "--protect", "standard")
    return d, src.read_bytes()


def _copy_pages(source, tmp_path):
    for page in sorted(source.glob("p_*.png")):
        (tmp_path / page.name).write_bytes(page.read_bytes())
    return tmp_path / "p"


@pytest.mark.parametrize("number", [1, 6])
def test_unreadable_file_counts_as_missing_wherever_it_is(twelve_pages, tmp_path, capsys, number):
    source, data = twelve_pages
    base = _copy_pages(source, tmp_path)
    (tmp_path / f"p_{number:04d}.png").write_text("not an image\n")
    out = tmp_path / "out.bin"
    assert main(["decode", str(base), "-o", str(out)]) == 0
    assert out.read_bytes() == data
    err = capsys.readouterr().err
    assert f"optar: p_{number:04d}.png: could not be read (cannot read image" in err
    assert "counted as a missing page." in err
    assert f"missing page {number}" in err and "file verified" in err


def test_blank_first_scan_counts_as_missing(twelve_pages, tmp_path, capsys):
    source, data = twelve_pages
    base = _copy_pages(source, tmp_path)
    save_scan(tmp_path / "p_0001.png", np.full((1200, 850), 255, np.uint8))
    out = tmp_path / "out.bin"
    assert main(["decode", str(base), "-o", str(out)]) == 0
    assert out.read_bytes() == data
    err = capsys.readouterr().err
    assert "optar: p_0001.png: not identified (no page found); counted as a missing page." in err
    assert "missing page 1" in err


def test_unreadable_first_file_of_three_pages_is_not_saved(tmp_path, capsys):
    src = _protected_input(tmp_path, 3)
    base = _encode_v1(tmp_path, src, "p", "--dots", "large", "--protect", "standard")
    capsys.readouterr()
    (tmp_path / "p_0001.png").write_text("not an image\n")
    out = tmp_path / "out.bin"
    assert main(["decode", str(base), "-o", str(out)]) == 1
    assert not out.exists()
    err = capsys.readouterr().err
    assert "p_0001.png: could not be read" in err
    assert "Rescan page 1 and decode again;" in err


def test_three_unreadable_first_files_fall_back_to_the_old_path(twelve_pages, tmp_path, capsys):
    source, _ = twelve_pages
    base = _copy_pages(source, tmp_path)
    for number in (1, 2, 3):
        (tmp_path / f"p_{number:04d}.png").write_text("not an image\n")
    assert main(["decode", str(base), "-o", str(tmp_path / "out.bin")]) == 2
    err = capsys.readouterr().err
    assert err.splitlines()[-1].startswith("optar: cannot read image")
    assert "p_0001.png" in err.splitlines()[-1]
    assert "counted as a missing page" not in err
    assert not (tmp_path / "out.bin").exists()


def test_force_saves_what_was_recovered(tmp_path, capsys):
    src = _protected_input(tmp_path, 3)
    base = _encode_v1(tmp_path, src, "p", "--dots", "large", "--protect", "standard")
    capsys.readouterr()
    (tmp_path / "p_0002.png").unlink()
    out = tmp_path / "out.bin"
    assert main(["decode", str(base), "-o", str(out), "--force"]) == 1
    got, want = np.frombuffer(out.read_bytes(), np.uint8), np.frombuffer(src.read_bytes(), np.uint8)
    assert len(got) == len(want) and (got != want).any()
    assert (got == want).mean() > 0.5  # the two pages read are in it
    err = capsys.readouterr().err
    assert "did not verify" in err and "may be damaged" in err


def test_pages_of_another_document_are_ignored(tmp_path, capsys):
    src = _protected_input(tmp_path, 1, dots="xlarge")
    base = _encode_v1(tmp_path, src, "p", "--dots", "xlarge", "--protect", "standard")
    other = _protected_input(tmp_path, 1, dots="xlarge", name="other.bin", seed=12)
    _encode_v1(tmp_path, other, "q", "--dots", "xlarge", "--protect", "standard")
    (tmp_path / "q_0001.png").rename(tmp_path / "p_0002.png")
    (tmp_path / "p_0003.png").write_bytes((tmp_path / "p_0001.png").read_bytes())  # again
    capsys.readouterr()
    out = tmp_path / "out.bin"
    assert main(["decode", str(base), "-o", str(out)]) == 0
    assert out.read_bytes() == src.read_bytes()
    err = capsys.readouterr().err
    assert "1 scan from another document was ignored: p_0002.png" in err
    assert "p_0003.png: page 1 of 1 again" in err


def test_unidentified_scan_counts_as_missing_and_names_resolution(tmp_path, capsys, monkeypatch):
    import optar.cli
    from optar.errors import IdentifyError

    src = _protected_input(tmp_path, 12)
    base = _encode_v1(tmp_path, src, "p", "--dots", "large", "--protect", "standard")
    real = optar.cli.identify_scan
    calls = []

    def flaky(image, *a, **k):
        calls.append(1)
        if len(calls) == 7:
            raise IdentifyError("label unreadable", scan_dpi=201.3)
        return real(image, *a, **k)

    monkeypatch.setattr(optar.cli, "identify_scan", flaky)
    capsys.readouterr()
    out = tmp_path / "out.bin"
    assert main(["decode", str(base), "-o", str(out)]) == 0
    assert out.read_bytes() == src.read_bytes()
    err = capsys.readouterr().err
    assert "p_0007.png: not identified (label unreadable)" in err
    assert "scanned at about 200 dpi" in err
    assert "Standard 600, Medium 450, Big 360, Large 300, Extra large 200" in err
    assert "missing page 7" in err


def test_version1_label_is_the_name_only(tmp_path, infile, monkeypatch):
    labels = _spy_labels(monkeypatch)
    assert main(_encode_args(infile, tmp_path / "x", "--to", "pgm", "--dots", "xlarge")) == 0
    assert main(_encode_args(infile, tmp_path / "y", "--to", "pgm", "--protect", "none",
                             "--label", "mine")) == 0  # fmt: skip
    assert labels == [["x"], ["mine"]]


def test_dots_alone_selects_the_container_and_pdf_uses_its_scale(tmp_path, infile, capsys):
    from optar.format import get_layout

    assert main(_encode_args(infile, tmp_path / "x", "--dots", "xlarge")) == 0
    page = parse_pdf(tmp_path / "x.pdf")[0]
    assert page["mediabox"][2:] == pytest.approx((595.28, 841.89), abs=0.01)
    assert "Scan at 200 dpi" in capsys.readouterr().err
    assert main(_encode_args(infile, tmp_path / "y", "--to", "png", "--dots", "xlarge")) == 0
    layout = get_layout("a4", "xlarge")
    with Image.open(tmp_path / "y_0001.png") as im:
        assert im.size == (layout.fmt.width, layout.fmt.height)
        assert im.info["dpi"][0] == pytest.approx(float(layout.pixels_per_inch), abs=0.01)


def _written_document(tmp_path, base):
    """(page files, header of page 1, layout) of PNG pages written as BASE_NNNN.png."""
    from optar.identify import identify_scan
    from optar.imageio import read_scan

    files = sorted(tmp_path.glob(f"{base}_*.png"))
    ident = identify_scan(read_scan(files[0]))
    assert ident.header is not None
    return files, ident.header, ident.layout


@pytest.mark.parametrize(
    "extra,parity", [([], 32), (["--protect", "none"], 0), (["--protect", "high"], 64)]
)
def test_dot_size_alone_protects_at_standard(tmp_path, capsys, extra, parity):
    from optar.container import plan
    from optar.format import get_layout

    # Fills two pages without parity, so parity needs more pages.
    src = _protected_input(tmp_path, 2, dots="large", parity="none")
    _encode_v1(tmp_path, src, "p", "--dots", "large", *extra)
    files, header, layout = _written_document(tmp_path, "p")
    fmt = get_layout("a4", "large").fmt
    assert layout.dots.name == "large"
    assert header.parity == parity
    assert len(files) == header.total == plan(src.stat().st_size, src.name, fmt, parity).total
    assert (header.total == 2) == (parity == 0)
    name = {0: "none", 32: "standard", 64: "high"}[parity]
    assert f"Protection {name}:" in capsys.readouterr().err


def test_protect_alone_uses_standard_dots(tmp_path, infile, capsys):
    from optar.format import get_layout

    _encode_v1(tmp_path, infile, "p", "--protect", "high")
    files, header, layout = _written_document(tmp_path, "p")
    standard = get_layout("a4", "standard")
    assert layout == standard and header.parity == 64 and len(files) == 1
    with Image.open(files[0]) as im:
        assert im.size == (standard.fmt.width, standard.fmt.height)
    err = capsys.readouterr().err
    assert "Scan at 600 dpi" in err and "Protection high:" in err


def test_compatible_and_dots_standard_are_the_default(tmp_path, infile):
    runs = {"a": [], "b": ["--compatible"], "c": ["--dots", "standard"]}
    for folder, extra in runs.items():
        (tmp_path / folder).mkdir()
        assert main(_encode_args(infile, tmp_path / folder / "x", "--to", "pgm", *extra)) == 0
    want = (tmp_path / "a" / "x_0001.pgm").read_bytes()
    assert (tmp_path / "b" / "x_0001.pgm").read_bytes() == want
    assert (tmp_path / "c" / "x_0001.pgm").read_bytes() == want


def test_default_encode_message_names_scan_resolution(tmp_path, infile, capsys):
    assert main(_encode_args(infile, tmp_path / "a")) == 0
    err = capsys.readouterr().err
    assert "actual size" in err and "Scan at 600 dpi" in err and "lose" not in err


@pytest.mark.parametrize(
    "extra",
    [
        ["--compatible", "--dots", "large"],
        ["--compatible", "--dots", "standard"],
        ["--compatible", "--protect", "none"],
        ["--format", "0-65-93-24-3-1-2-24", "--dots", "large"],
        ["--format", "0-65-93-24-3-1-2-24", "--protect", "standard"],
        ["--dots", "huge"],
        ["--protect", "max"],
    ],
)
def test_conflicting_options_are_usage_errors(tmp_path, infile, capsys, extra):
    with pytest.raises(SystemExit) as e:
        main(_encode_args(infile, tmp_path / "x", *extra))
    assert e.value.code == 2
    assert sorted(p.name for p in tmp_path.iterdir()) == ["in.bin"]


def test_protect_over_size_limit_fails_before_reading(tmp_path, capsys, monkeypatch):
    import builtins

    big = tmp_path / "big.bin"
    with open(big, "wb") as f:
        f.truncate(300 * 1024 * 1024)  # sparse
    real_open = builtins.open

    def no_read(path, *a, **k):
        assert os.fspath(path) != str(big), "the input was read"
        return real_open(path, *a, **k)

    monkeypatch.setattr(builtins, "open", no_read)
    assert main(_encode_args(big, tmp_path / "o", "--protect", "standard", "--to", "png")) == 2
    assert "too large to protect" in capsys.readouterr().err
    assert sorted(p.name for p in tmp_path.iterdir()) == ["big.bin"]
