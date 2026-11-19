# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""No word of a translation mixes scripts, and each language's name is in its own script.

A Latin letter inside a Cyrillic word (or the reverse) looks right to the eye and
is a different letter; a reader cannot see it and a search cannot find it. The
check covers the catalogues and the translated pages. Code, placeholders, URLs and
link targets are not prose and are skipped; a hyphen or an apostrophe ends a word,
so ``PDF-файл`` and ``optar-ით`` are two words.
"""

import re
import tomllib
import unicodedata
from pathlib import Path

import pytest

from optar import i18n
from tests.unit.test_doc_translations import body_of, outside_fences

ROOT = Path(__file__).resolve().parents[2]
LOCALE = ROOT / "src" / "optar" / "locale"
DOCS = ROOT / "docs"
CODES = [c for c in i18n.ORDER if c != "en"]
SCRIPTS = ("LATIN", "CYRILLIC", "GEORGIAN")
OWN_SCRIPT = {"ru": "CYRILLIC", "uk": "CYRILLIC", "be": "CYRILLIC", "ka": "GEORGIAN"}

INLINE_CODE = re.compile(r"(`+)(?:(?!\1).)+?\1")
PLACEHOLDER = re.compile(r"\{[^{}]*\}")
URL = re.compile(r"(?:https?://|www\.)\S+|<[^<>\s]+@[^<>\s]+>")
LINK_TARGET = re.compile(r"(?<=\])\([^)\s]*(?:\s+\"[^\"]*\")?\)")
LETTERS = re.compile(r"[^\W\d_]+")


def script_of(ch: str) -> str | None:
    word = unicodedata.name(ch, "").split(" ", 1)[0]
    return word if word in SCRIPTS else None


def mixed_words(text: str) -> list[str]:
    """Words of prose with letters of more than one script, each with its foreign letters."""
    for pattern in (INLINE_CODE, URL, LINK_TARGET, PLACEHOLDER):
        text = pattern.sub(" ", text)
    found = []
    for word in LETTERS.findall(text):
        scripts = [(ch, script_of(ch)) for ch in word]
        present = {s for _, s in scripts if s}
        if len(present) > 1:
            main = max(present, key=lambda s: sum(1 for _, t in scripts if t == s))
            foreign = ", ".join(
                f"{ch} U+{ord(ch):04X}" for ch, s in scripts if s and s != main
            )
            found.append(f"{word!r} ({foreign})")
    return found


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)


def catalogue_problems(code: str) -> list[str]:
    path = LOCALE / f"{code}.toml"
    lines = path.read_text(encoding="utf-8").split("\n")
    problems = []
    # Per line of the file, so a failure names the line; keys are ASCII and skipped.
    for number, line in enumerate(lines, 1):
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        value = line.split("=", 1)[1]
        for word in mixed_words(value.replace("\\n", " ")):
            problems.append(f"{path.name}:{number}: {word}")
    # The same on the parsed strings, for values that span lines or use escapes.
    for string in _strings(tomllib.loads(path.read_text(encoding="utf-8"))):
        for word in mixed_words(string):
            entry = f"{path.name}: {word}"
            if not any(p.endswith(word) for p in problems):
                problems.append(entry)
    return problems


def page_problems(path: Path) -> list[str]:
    body = body_of(path.read_text(encoding="utf-8"))
    offset = path.read_text(encoding="utf-8").count("\n") - body.count("\n")
    problems = []
    for number, line in enumerate(outside_fences(body), 1):
        for word in mixed_words(line):
            problems.append(f"{path.name}:{number + offset}: {word}")
    return problems


@pytest.mark.parametrize("code", CODES)
def test_no_catalogue_word_mixes_scripts(code):
    assert not catalogue_problems(code)


@pytest.mark.parametrize("code", CODES)
def test_no_page_word_mixes_scripts(code):
    problems = []
    for path in sorted(DOCS.glob(f"*.{code}.md")):
        problems += page_problems(path)
    assert not problems


@pytest.mark.parametrize("code", CODES)
def test_language_name_is_written_in_its_own_script(code):
    name = tomllib.loads((LOCALE / f"{code}.toml").read_text(encoding="utf-8"))["language"]["name"]
    wanted = OWN_SCRIPT.get(code, "LATIN")
    scripts = {script_of(ch) for ch in name if ch.isalpha()}
    assert scripts == {wanted}, f"{code}: {name!r} uses {sorted(map(str, scripts))}, not {wanted}"


# --- The check bites ------------------------------------------------------------------


def test_a_latin_letter_in_a_cyrillic_word_is_reported():
    found = mixed_words("слoво")  # the o is Latin
    assert len(found) == 1 and "U+006F" in found[0]


def test_a_cyrillic_letter_in_a_georgian_word_is_reported():
    assert mixed_words("ქართулиი")


def test_native_endings_after_a_hyphen_and_skipped_text_are_fine():
    text = "PDF-файл, A4-формат, optar-ით, `код x` {name} https://a.b/хх ](http://x/y) it's"
    assert mixed_words(text) == []
