# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""List the translated documentation pages that are missing or stale.

A translated page ``docs/<page>.<code>.md`` opens with front matter holding
``source_hash``: the git blob hash of the English page it was translated from.
The page is stale when that no longer equals the hash of the English page.

    python tools/translation_status.py [--check] [CODE ...]

One line per problem page, such as ``docs/install.ru.md: stale``; the exit
status is 0, or with ``--check`` 1 if any page is missing (stale is not an
error). Without codes, the languages looked at are those that have a catalogue
under ``src/optar/locale`` or any translated page.
"""

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HASH = re.compile(r"[0-9a-f]{40}")


def blob_hash(content: bytes) -> str:
    """What ``git hash-object`` prints for a file with this content."""
    return hashlib.sha1(b"blob %d\0" % len(content) + content).hexdigest()


def page_hash(path: Path) -> str:
    """The git blob hash of a page as git stores it: a checkout that turned its line
    ends into CRLF (``core.autocrlf`` on Windows) gives the hash of the LF file."""
    return blob_hash(path.read_bytes().replace(b"\r\n", b"\n"))


def english_pages(docs: Path) -> list[Path]:
    """The English pages: the Markdown files of ``docs`` whose stem has no dot."""
    return sorted(p for p in docs.glob("*.md") if "." not in p.stem)


def source_hash(text: str) -> str | None:
    """The ``source_hash`` of a page's front matter, or None."""
    lines = text.split("\n")
    if not lines or lines[0].rstrip() != "---":
        return None
    for line in lines[1:]:
        if line.rstrip() == "---":
            return None
        key, _, value = line.partition(":")
        if key.strip() == "source_hash":
            value = value.strip().strip("\"'")
            return value if HASH.fullmatch(value) else None
    return None


def started_languages(root: Path) -> list[str]:
    """Codes of the languages with a catalogue or a translated page."""
    codes = {p.stem for p in (root / "src" / "optar" / "locale").glob("*.toml")}
    codes |= {p.stem.partition(".")[2] for p in (root / "docs").glob("*.*.md")}
    codes.discard("en")
    return sorted(codes)


def problems(root: Path, codes: list[str] | None = None) -> list[tuple[str, str]]:
    """(path relative to the root, "missing" or "stale") for each problem page."""
    docs = root / "docs"
    found = []
    for code in started_languages(root) if codes is None else codes:
        for english in english_pages(docs):
            page = docs / f"{english.stem}.{code}.md"
            relative = page.relative_to(root).as_posix()
            if not page.exists():
                found.append((relative, "missing"))
                continue
            current = page_hash(english)
            written = source_hash(page.read_text(encoding="utf-8"))
            if written != current:
                found.append((relative, "stale"))
    return found


def main(argv: list[str]) -> int:
    check = "--check" in argv
    codes = [a for a in argv if not a.startswith("--")] or None
    found = problems(ROOT, codes)
    for path, state in found:
        print(f"{path}: {state}")
    return 1 if check and any(state == "missing" for _, state in found) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
