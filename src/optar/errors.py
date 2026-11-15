# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Exception hierarchy for optar."""

from __future__ import annotations


class OptarError(Exception):
    """Base class for all optar errors."""


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
    a label that reads, parses and agrees with itself).
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
