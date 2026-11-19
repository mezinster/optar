# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The window's language: the saved choice, the system's language, and the start.

The choice is kept in the user's settings (``QSettings``, key ``language``). It
is read once, at start; a changed choice takes effect the next time the program
starts.
"""

from __future__ import annotations

from PySide6.QtCore import QLocale, QSettings

from optar import i18n

__all__ = ["at_start", "save", "saved", "system"]

KEY = "language"


def _settings() -> QSettings:
    return QSettings(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, "optar", "optar-gui"
    )


def saved() -> str | None:
    """The saved language code if it names a language present, else None."""
    value = _settings().value(KEY)
    if isinstance(value, str) and value in i18n.languages():
        return value
    return None


def save(code: str | None) -> None:
    """Remembers ``code``; None removes the choice (follow the system)."""
    settings = _settings()
    if code is None:
        settings.remove(KEY)
    else:
        settings.setValue(KEY, code)
    settings.sync()


def system() -> str | None:
    """The system's interface language if a catalogue exists for it."""
    return i18n.pick_language(QLocale.system().uiLanguages())


def at_start() -> str:
    return saved() or system() or "en"
