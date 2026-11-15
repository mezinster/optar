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
