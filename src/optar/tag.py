# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The document tag printed in the free-text part of every page label.

The tag records the true size and a fingerprint of the file, so that pages of
different printouts cannot be mixed, the recovered file can be cut to its true
size and the result can be verified. Each page's tag ends in a check of the
size, fingerprint, page number and page count, so that a label misread from a
scan is caught when the scan is identified. Its syntax is strict because the
label is read back from scans by character matching.
"""
import hashlib
import re
from dataclasses import dataclass

from .format import PageFormat

FINGERPRINT_DIGITS = 8
CHECK_DIGITS = 2
# Sizes are written with at most this many decimal digits. Generous for any
# encodable file; the bound keeps parsing of unreadable labels from raising.
MAX_SIZE_DIGITS = 12

_FINGERPRINT = re.compile(rf"[0-9a-f]{{{FINGERPRINT_DIGITS}}}")
# ASCII digits only, no leading zeros except "0" itself; then end or one space.
_TAG = re.compile(
    rf"\[(0|[1-9][0-9]{{0,{MAX_SIZE_DIGITS - 1}}})"
    rf":([0-9a-f]{{{FINGERPRINT_DIGITS}}})"
    rf":([0-9a-f]{{{CHECK_DIGITS}}})\](?: |\Z)", re.ASCII)


@dataclass(frozen=True)
class Tag:
    size: int
    fingerprint: str

    def __post_init__(self):
        if not isinstance(self.size, int) or isinstance(self.size, bool):
            raise ValueError(f"size must be an int: {self.size!r}")
        if not 0 <= self.size < 10 ** MAX_SIZE_DIGITS:
            raise ValueError(
                f"size must be between 0 and 10**{MAX_SIZE_DIGITS} - 1: {self.size}")
        if not isinstance(self.fingerprint, str) or not _FINGERPRINT.fullmatch(self.fingerprint):
            raise ValueError(
                f"fingerprint must be {FINGERPRINT_DIGITS} lower-case hex digits: "
                f"{self.fingerprint!r}")

    def check(self, page: int, total: int) -> str:
        """The check printed in the tag of page `page` of `total`."""
        text = f"{self.size}:{self.fingerprint}:{page}/{total}".encode("ascii")
        return hashlib.sha256(text).hexdigest()[:CHECK_DIGITS]

    def page_text(self, page: int, total: int) -> str:
        """The tag as printed on page `page` of `total`: [SIZE:FINGERPRINT:CHECK]."""
        return f"[{self.size}:{self.fingerprint}:{self.check(page, total)}]"

    def fits(self, total: int, fmt: PageFormat) -> bool:
        """Whether a file of this size is printed on `total` pages of `fmt`.

        An empty file is printed as one page labelled 1/0, so it fits only
        total == 0, and total == 0 fits only an empty file.
        """
        if self.size == 0 or total == 0:
            return self.size == 0 and total == 0
        capacity = fmt.net_bits // 8
        return (total - 1) * capacity < self.size <= total * capacity

    def matches(self, data: bytes) -> bool:
        return len(data) == self.size and _fingerprint(data) == self.fingerprint


def _fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:FINGERPRINT_DIGITS]


def make_tag(data: bytes) -> Tag:
    return Tag(len(data), _fingerprint(data))


def tagged_label(tag: Tag, name: str, page: int, total: int) -> str:
    """The free text of page `page` of `total`: the page's tag, then the name."""
    text = tag.page_text(page, total)
    return f"{text} {name}" if name else text


def split_label(text: str) -> tuple[Tag | None, str, str]:
    """(tag, check, name) from a label's free text, or (None, "", text) without a tag.

    The check is returned as read; whether it is right for a page is for the
    caller, who knows the page number and count.
    """
    m = _TAG.match(text)
    if m is None:
        return None, "", text
    return Tag(int(m.group(1)), m.group(2)), m.group(3), text[m.end():]
