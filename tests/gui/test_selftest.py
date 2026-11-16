# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The hidden self-test that release builds run."""

from optar_gui.selftest import run_self_test


def test_self_test_passes(qapp, capsys):
    assert run_self_test() == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) >= 3
    assert all(line.startswith("ok ") for line in lines)


def test_self_test_fails_when_a_check_fails(qapp, capsys, monkeypatch):
    import optar_gui.selftest as selftest

    def broken_pdf(src, dest, paper_name, name, cancelled=None):
        with open(dest, "wb") as f:
            f.write(b"not a pdf")
        return 1

    monkeypatch.setattr(selftest, "encode_to_pdf", broken_pdf)
    assert run_self_test() == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
