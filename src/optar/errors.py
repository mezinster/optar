# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Exception hierarchy for optar.

An error a person can meet carries a message key (``key``, under ``err`` in the
catalogues) and the values its message is made from (``values``), so that the
command line and the window can show it in the user's language
(``optar.i18n.error_text``). ``str(e)`` is always the English message. The
library never looks the key up itself: only ``cli.py`` and the window do.
"""

from __future__ import annotations


class OptarError(Exception):
    """Base class for all optar errors."""

    key: str | None = None
    values: dict[str, object] = {}  # replaced per instance, never changed in place


class Grouped(int):
    """A count shown with thousands separators: ``1,234`` in the English text,
    the language's own separator in a translation."""

    def __format__(self, spec: str) -> str:
        return format(int(self), spec or ",")

    def __str__(self) -> str:
        return format(self)


class Alternatives(tuple):
    """Names of which one is meant (the image formats a scan may be in): ``A, B or
    C`` in the English text, the language's separator and word for "or" in a
    translation (``optar.i18n.alternatives``)."""

    def __format__(self, spec: str) -> str:
        names = [str(name) for name in self]
        text = "".join(names) if len(names) < 2 else ", ".join(names[:-1]) + " or " + names[-1]
        return format(text, spec)

    def __str__(self) -> str:
        return format(self)


def keyed[E: OptarError](err: E, key: str | None, values: dict[str, object]) -> E:
    """``err`` given the message key and values (a key of None leaves it without)."""
    err.key = key
    err.values = dict(values)
    return err


def error[E: OptarError](cls: type[E], key: str, english: str, /, **values: object) -> E:
    """``cls(english.format(**values))`` carrying ``key`` and ``values``.

    ``english`` is a string literal at every call, equal to the catalogue's
    English entry for ``key`` (a test checks both).
    """
    return keyed(cls(english.format(**values)), key, values)


class FormatError(OptarError, ValueError):
    """Invalid or unsupported page format."""


class DecodeError(OptarError):
    """Decoding failed. `page` is the 1-based page number when it is known."""

    def __init__(self, *args: object, page: int | None = None) -> None:
        super().__init__(*args)
        self.page = page


class IdentifyError(DecodeError):
    """A scan could not be identified from its label.

    `reason` is "no page found" (no page outline in any orientation) or
    "label unreadable" (a page was found, but no orientation and paper gave
    a label that reads, parses and agrees with itself, nor a version-1
    header in its data).

    `scan_dpi` is the scan's resolution estimated from the page outline, or
    None when no outline was found.

    `slow_tried` is True when identify.identify_any also tried the slow
    reader (decoder.soft) and it failed too.
    """

    def __init__(
        self, reason: str, scan_dpi: float | None = None, slow_tried: bool = False
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.scan_dpi = scan_dpi
        self.slow_tried = slow_tried
