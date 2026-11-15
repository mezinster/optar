# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Python port of optar: store files on paper."""

__version__ = "0.1.0"

from optar.decoder import (  # noqa: E402
    DecodeOptions,
    DecodeResult,
    PageResult,
    PageStats,
    decode,
    decode_page,
)
from optar.encoder import Page, encode  # noqa: E402
from optar.errors import DecodeError, FormatError, OptarError  # noqa: E402
from optar.format import PAPERS, PageFormat, Paper, get_paper  # noqa: E402
from optar.imageio import read_scan, write_pgm, write_png  # noqa: E402
from optar.pdf import write_pdf  # noqa: E402

__all__ = [
    "PageFormat",
    "Paper",
    "PAPERS",
    "get_paper",
    "encode",
    "Page",
    "decode",
    "decode_page",
    "DecodeOptions",
    "DecodeResult",
    "PageResult",
    "PageStats",
    "write_pdf",
    "write_png",
    "write_pgm",
    "read_scan",
    "OptarError",
    "FormatError",
    "DecodeError",
]
