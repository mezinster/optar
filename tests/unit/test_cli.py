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
    import optar.cli

    labels = []

    def spy(data, fmt, label=""):
        labels.append(label)
        return encode(data, fmt, label)

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
    assert labels[-2:] == [tagged_label(tag, "name"), tagged_label(tag, "my name")]
    assert labels[-1] == f"[{tag.size}:{tag.fingerprint}] my name"


def test_no_tag_keeps_plain_label(tmp_path, infile, monkeypatch):
    labels = _spy_labels(monkeypatch)
    (tmp_path / "sub").mkdir()
    assert main(_encode_args(infile, tmp_path / "sub" / "name", "--to", "pgm", "--no-tag")) == 0
    args = _encode_args(infile, tmp_path / "x", "--to", "pgm", "--label", "mine", "--no-tag")
    assert main(args) == 0
    assert main(_encode_args(infile, tmp_path / "y", "--to", "pgm", "--no-tag")) == 0
    assert labels == ["name", "mine", "y"]


def test_encode_adds_tag_by_default(tmp_path, infile):
    from optar.imageio import pgm_bytes
    from optar.tag import make_tag, tagged_label

    data = infile.read_bytes()
    assert main(_encode_args(infile, tmp_path / "out", "--to", "pgm")) == 0
    fmt = PageFormat.for_paper(PAPERS["a4"])
    want = next(encode(data, fmt, tagged_label(make_tag(data), "out"))).pixels
    assert (tmp_path / "out_0001.pgm").read_bytes() == pgm_bytes(want)


def test_no_tag_output_is_plain_label_output(tmp_path, infile):
    from optar.imageio import pgm_bytes

    fmt = PageFormat.for_paper(PAPERS["a4"])
    want = next(encode(infile.read_bytes(), fmt, "out")).pixels
    assert main(_encode_args(infile, tmp_path / "out", "--to", "pgm", "--no-tag")) == 0
    assert (tmp_path / "out_0001.pgm").read_bytes() == pgm_bytes(want)


def test_empty_input_gets_empty_tag(tmp_path, monkeypatch):
    labels = _spy_labels(monkeypatch)
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    assert main(_encode_args(empty, tmp_path / "e", "--to", "pgm")) == 0
    assert labels == ["[0:e3b0c442] e"]
    assert sorted(p.name for p in tmp_path.glob("e_*.pgm")) == ["e_0001.pgm"]


def test_written_tag_parses_back(tmp_path, monkeypatch):
    from optar.tag import split_label

    labels = _spy_labels(monkeypatch)
    data = seeded_bytes(5, 250_000)
    src = tmp_path / "big.bin"
    src.write_bytes(data)
    assert main(_encode_args(src, tmp_path / "big", "--to", "pgm")) == 0
    fmt = PageFormat.for_paper(PAPERS["a4"])
    total = len(list(encode(data, fmt)))
    assert total == 2
    tag, name = split_label(labels[-1])
    assert tag is not None and name == "big"
    assert tag.matches(data)
    assert tag.fits(total, fmt)


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
