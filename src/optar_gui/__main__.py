# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The entry point ``optar-gui``: the window, ``--version`` and ``--self-test``."""

from __future__ import annotations

import argparse
import os
import sys

from optar import __version__

__all__ = ["main"]

MISSING_QT = "optar-gui needs PySide6: pip install 'optar[gui]'"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="optar-gui", description="Store files on paper and read them back."
    )
    parser.add_argument("--version", action="store_true", help="print the version and exit")
    parser.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
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
        print(MISSING_QT, file=sys.stderr)
        return 2
    if args.self_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from optar_gui.selftest import run_self_test

        return run_self_test()

    from PySide6.QtWidgets import QApplication

    from optar_gui.main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv[:1] or ["optar-gui"])
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
