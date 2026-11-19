# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The ``optar-gui`` entry point where it needs no Qt: ``--version``, bad arguments
and the message when PySide6 is missing (run without PySide6 in CI)."""

import sys

import optar_gui.__main__ as entry
from optar import __version__


def test_version_and_bad_arguments(capsys):
    assert entry.main(["--version"]) == 0
    assert capsys.readouterr().out == f"optar-gui {__version__}\n"
    assert entry.main(["--no-such-option"]) == 2
    assert "--no-such-option" in capsys.readouterr().err


def test_help_is_worded_by_the_catalogue(catalogues, monkeypatch, capsys):
    """optar-gui --help says usage, headings and -h in the chosen language, as optar
    --help does; a bare % in a translation (argparse expands it) is shown as it is."""
    catalogues.add("ru", {
        "language": {"name": "Русский"},
        "cli": {"argparse": {"usage": "использование: ", "options": "параметры",
                             "help": "показать справку"}},
        "gui": {"cli": {"description": "описание", "version_help": "версия на 100%"}},
    })  # fmt: skip
    monkeypatch.setenv("OPTAR_LANG", "ru")
    assert entry.main(["--help"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("использование: optar-gui [-h] [--version]\n")
    assert "\nпараметры:\n" in out and "показать справку" in out
    assert "описание" in out and "версия на 100%" in out
    assert "usage" not in out and "options:" not in out


def test_help_and_bad_arguments_survive_a_windowed_build_with_no_stdout_or_stderr(
    catalogues, monkeypatch
):
    catalogues.add("ru", {"language": {"name": "Русский"}})
    monkeypatch.setenv("OPTAR_LANG", "ru")
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    assert entry.main(["--help"]) == 0
    assert entry.main(["--no-such-option"]) == 2


def test_missing_pyside6_says_how_to_get_it(capsys, monkeypatch):
    monkeypatch.setitem(sys.modules, "PySide6", None)  # as if it were not installed
    assert entry.main([]) == 2
    assert capsys.readouterr().err == (
        "optar-gui needs PySide6: run pip install '.[gui]' in a checkout of the source, "
        "or download optar-gui from the project's Releases page.\n"
    )


def test_the_entry_point_does_not_import_qt():
    import subprocess

    code = (
        "import sys, optar_gui.__main__\n"
        "print(','.join(m for m in sys.modules if m.split('.')[0] in ('PySide6', 'shiboken6')))\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_main_survives_a_windowed_build_with_no_stderr(catalogues, monkeypatch, capsys):
    """A windowed build has sys.stderr None: main must still run, and the language
    is the environment's (the encoding is taken as UTF-8)."""
    catalogues.add(
        "ru", {"language": {"name": "Русский"}, "gui": {"cli": {"missing_qt": "Нужен PySide6."}}}
    )
    monkeypatch.setenv("OPTAR_LANG", "ru")
    monkeypatch.setitem(sys.modules, "PySide6", None)
    monkeypatch.setattr(sys, "stderr", None)
    assert entry.main(["--version"]) == 0
    assert entry.main([]) == 2  # print(file=None) goes to stdout, harmlessly
    out = capsys.readouterr().out
    assert out == f"optar-gui {__version__}\nНужен PySide6.\n"


def test_terminal_messages_follow_the_system_language(monkeypatch, capsys):
    """As optar does: with no language in the environment, the system's (on
    Windows the interface language) words optar-gui's terminal messages."""
    import optar.cli
    from optar import i18n

    monkeypatch.delenv("OPTAR_LANG")
    monkeypatch.setattr(optar.cli, "system_language", lambda: "ru_RU")
    monkeypatch.setitem(sys.modules, "PySide6", None)
    assert entry.main([]) == 2
    assert capsys.readouterr().err == i18n.catalogue("ru")["gui.cli.missing_qt"] + "\n"
