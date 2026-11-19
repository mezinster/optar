# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The entry point ``optar-gui``: the window, ``--version`` and ``--self-test``."""

from __future__ import annotations

import argparse
import os
import sys

from optar import __version__, i18n
from optar_gui import text

__all__ = ["main"]


def _parser() -> argparse.ArgumentParser:
    # The parser of optar's own --help, which words usage, headings and errors
    # from the catalogue. Imported here, as choose_language is (in _main).
    from optar.cli import Parser

    parser = Parser(prog="optar-gui", description=text.cli_description())
    parser.add_argument("--version", action="store_true", help=text.cli_version_help())
    parser.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    previous = i18n.language()
    try:
        return _main(argv)
    finally:
        i18n.set_language(previous)


def _main(argv: list[str] | None) -> int:
    # The terminal messages follow the environment; the window, once there is
    # one, follows the saved choice.
    from optar.cli import (  # not before --version needs it
        choose_language,
        stream_encoding,
        system_language,
    )

    # A windowed build has no stdout or stderr (None): it then limits nothing.
    i18n.set_language(
        choose_language(
            os.environ,
            stream_encoding(sys.stdout),
            stream_encoding(sys.stderr),
            system=system_language(),
        )
    )
    try:
        args = _parser().parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as e:  # argparse has printed the usage or the error
        return 0 if e.code in (0, None) else 2
    if args.version:
        print(f"optar-gui {__version__}")
        return 0
    try:
        import PySide6.QtWidgets  # noqa: F401
    except ImportError:
        print(text.missing_qt(), file=sys.stderr)
        return 2
    if args.self_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        i18n.set_language("en")
        from optar_gui.selftest import run_self_test

        return run_self_test()

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv[:1] or ["optar-gui"])
    from optar_gui import language

    i18n.set_language(language.at_start())
    from optar_gui.main_window import MainWindow

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
