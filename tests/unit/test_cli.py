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


HINT = "Check that --paper matches the printout."


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
