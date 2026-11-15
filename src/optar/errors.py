# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Exception hierarchy for optar."""


class OptarError(Exception):
    """Base class for all optar errors."""


class FormatError(OptarError, ValueError):
    """Invalid or unsupported page format."""


class DecodeError(OptarError):
    """Decoding failed."""
