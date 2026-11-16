# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The hidden self-test that release builds run."""

from optar_gui.selftest import run_self_test


def test_self_test_passes(qapp, capsys):
    assert run_self_test() == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) >= 3
    assert all(line.startswith("ok ") for line in lines)
    assert any("Large" in line and "protection" in line for line in lines)
    assert "ok created a PDF" in lines and "ok created a compatible PDF" in lines


def test_self_test_fails_when_a_check_fails(qapp, capsys, monkeypatch):
    import optar_gui.selftest as selftest

    def broken_pdf(src, dest, paper_name, name, cancelled=None, **choices):
        with open(dest, "wb") as f:
            f.write(b"not a pdf")
        return 1

    monkeypatch.setattr(selftest, "encode_to_pdf", broken_pdf)
    assert run_self_test() == 1
    out = capsys.readouterr().out
    assert "FAIL" in out


def test_self_test_fails_when_the_compatible_pdf_is_wrong(qapp, capsys, monkeypatch):
    import optar_gui.selftest as selftest

    real = selftest.encode_to_pdf

    def one_page_too_many(*args, compatible=False, **kw):
        return real(*args, compatible=compatible, **kw) + (1 if compatible else 0)

    monkeypatch.setattr(selftest, "encode_to_pdf", one_page_too_many)
    assert run_self_test() == 1
    fails = [line for line in capsys.readouterr().out.splitlines() if line.startswith("FAIL")]
    assert fails == ["FAIL created a compatible PDF"]


def test_self_test_fails_when_protected_pages_do_not_verify(qapp, capsys, monkeypatch):
    import dataclasses

    import optar_gui.selftest as selftest

    real = selftest.unwrap

    def unverified(*args, **kw):
        return dataclasses.replace(real(*args, **kw), verified=False)

    monkeypatch.setattr(selftest, "unwrap", unverified)
    assert run_self_test() == 1
    fails = [line for line in capsys.readouterr().out.splitlines() if line.startswith("FAIL")]
    assert len(fails) == 1 and "Large" in fails[0]


def test_without_a_console_the_report_goes_to_a_log_file(qapp, monkeypatch, tmp_path):
    import sys
    import tempfile

    import optar_gui.selftest as selftest

    def checks(folder):
        return selftest._report("first check", True) and selftest._report("second", True)

    monkeypatch.setattr(selftest, "_checks", checks)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(sys, "stdout", None)  # a windowed program on Windows
    assert run_self_test() == 0
    log = tmp_path / selftest.SELF_TEST_LOG
    assert log.read_text(encoding="utf-8") == "ok first check\nok second\n"

    def failing(folder):
        raise RuntimeError("boom")

    monkeypatch.setattr(selftest, "_checks", failing)
    assert run_self_test() == 1
    assert log.read_text(encoding="utf-8") == "FAIL self-test stopped: RuntimeError: boom\n"
