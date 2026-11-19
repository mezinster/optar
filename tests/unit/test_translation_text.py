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
from tests.unit.test_doc_translations import FENCE, _closes

ROOT = Path(__file__).resolve().parents[2]
LOCALE = ROOT / "src" / "optar" / "locale"
DOCS = ROOT / "docs"
CODES = [c for c in i18n.ORDER if c != "en"]
SCRIPTS = ("LATIN", "CYRILLIC", "GEORGIAN")
OWN_SCRIPT = {"ru": "CYRILLIC", "uk": "CYRILLIC", "be": "CYRILLIC", "ka": "GEORGIAN"}

URL = re.compile(r"(?:https?://|www\.)[^\s)>\]]+|<[^<>\s]+@[^<>\s]+>")
LINK_TARGET = re.compile(r"(?<=\])\([^)\s]*(?:\s+\"[^\"]*\")?\)")
PLACEHOLDER = re.compile(r"\{[^{}]*\}")
BACKTICKS = re.compile(r"`+")
ESCAPE = re.compile(r"\\(?:[uU][0-9a-fA-F]{4,8}|.)")
HINT = (
    "if this is a Latin name with a native ending written without a hyphen, "
    "write the ending after a hyphen or apostrophe"
)
UNPAIRED = "unpaired backtick (it would hide text; close it or remove it)"


def script_of(ch: str) -> str | None:
    """The script of a letter (the first word of its Unicode name), None for a non-letter."""
    if unicodedata.category(ch)[0] != "L" or unicodedata.category(ch) == "Lm":
        return None
    return unicodedata.name(ch, "").split(" ", 1)[0] or None


def words_of(text: str) -> list[str]:
    """Runs of letters (and marks); digits, punctuation and modifier letters end a word."""
    words, current = [], []
    for ch in text:
        cat = unicodedata.category(ch)
        if (cat[0] == "L" and cat != "Lm") or cat[0] == "M":
            current.append(ch)
        elif current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    return words


def strip_code(text: str) -> tuple[str, list[int]]:
    """The text without inline code, and the line index of each backtick with no partner.

    A run of backticks closes at the next run of the same length, on a later line too
    (a span may wrap); a run with no partner is left in the text. Newlines inside a
    span are kept, so line numbers still match.
    """
    runs = list(BACKTICKS.finditer(text))
    out, position, unpaired, i = [], 0, [], 0
    while i < len(runs):
        run = runs[i]
        partner = next(
            (j for j in range(i + 1, len(runs)) if len(runs[j].group()) == len(run.group())), None
        )
        if partner is None:
            unpaired.append(text.count("\n", 0, run.start()))
            i += 1
            continue
        end = runs[partner].end()
        out.append(text[position:run.start()])
        out.append(" " + "\n" * text.count("\n", run.start(), end))
        position = end
        i = partner + 1
    out.append(text[position:])
    return "".join(out), unpaired


def prose_problems(text: str) -> list[tuple[int, str]]:
    """(line index, problem) for a paragraph: words with letters of more than one script.

    A word is mixed when it has letters of two of Latin, Cyrillic and Georgian, or
    letters of one of them and of any other script (a Greek omicron in a Cyrillic
    word). A word wholly in another script is not this test's business.
    """
    text, unpaired = strip_code(text)
    for pattern in (URL, LINK_TARGET, PLACEHOLDER):
        text = pattern.sub(lambda m: " " * len(m.group()), text)
    found = [(index, UNPAIRED) for index in unpaired]
    for index, line in enumerate(text.split("\n")):
        for word in words_of(line):
            scripts = [(ch, script_of(ch)) for ch in word]
            present = {s for _, s in scripts if s}
            known = present & set(SCRIPTS)
            if len(present) > 1 and known:
                main = max(known, key=lambda s: sum(1 for _, t in scripts if t == s))
                foreign = ", ".join(
                    f"{ch} U+{ord(ch):04X}" for ch, s in scripts if s and s != main
                )
                found.append((index, f"{word!r} has foreign letters ({foreign}); {HINT}"))
    return found


def mixed_words(text: str) -> list[str]:
    """The problems of a piece of prose, without line numbers."""
    return [problem for _, problem in prose_problems(text)]


def catalogue_problems(path: Path) -> list[str]:
    """file:line: problem, for each line of a catalogue (a key is ASCII, so it is harmless)."""
    problems = []
    for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        if line.lstrip().startswith("#"):
            continue
        for problem in mixed_words(ESCAPE.sub(" ", line)):
            problems.append(f"{path.name}:{number}: {problem}")
    return problems


def page_problems(path: Path) -> list[str]:
    """file:line: problem, for each line of prose of a page (front matter and code skipped)."""
    lines = path.read_text(encoding="utf-8").split("\n")
    start = 0
    if lines and lines[0].rstrip() == "---":
        for i, line in enumerate(lines[1:], 1):
            if line.rstrip() == "---":
                start = i + 1
                break
    problems, marker, paragraph = [], None, []

    def flush():
        if paragraph:
            first = paragraph[0][0]
            text = "\n".join(line for _, line in paragraph)
            for index, problem in prose_problems(text):
                where = paragraph[index][0] if index < len(paragraph) else first
                problems.append(f"{path.name}:{where}: {problem}")
            paragraph.clear()

    for number, line in enumerate(lines[start:], start + 1):
        m = FENCE.match(line)
        if marker is None:
            if m:
                flush()
                marker = m.group(1)
            elif line.strip():
                paragraph.append((number, line))
            else:
                flush()
        elif _closes(m, marker):
            marker = None
    flush()
    return problems


@pytest.mark.parametrize("code", CODES)
def test_no_catalogue_word_mixes_scripts(code):
    problems = catalogue_problems(LOCALE / f"{code}.toml")
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("code", CODES)
def test_no_page_word_mixes_scripts(code):
    problems = []
    for path in sorted(DOCS.glob(f"*.{code}.md")):
        problems += page_problems(path)
    assert not problems, "\n".join(problems)


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


@pytest.mark.parametrize("word", ["слοво", "wοrd"])  # a Greek omicron, U+03BF
def test_a_letter_of_another_script_in_a_word_is_reported(word):
    found = mixed_words(word)
    assert len(found) == 1 and "U+03BF" in found[0] and "hyphen" in found[0]


def test_a_word_wholly_in_another_script_is_not_reported():
    assert mixed_words("μ") == []


@pytest.mark.parametrize("text", ["PDF-файл", "A4-формат", "optar-ით", "optar\u02bcით", "it's"])
def test_a_native_ending_after_a_hyphen_or_apostrophe_is_two_words(text):
    assert mixed_words(text) == []


def test_inline_code_is_skipped():
    assert mixed_words("`слoво` и ``a ` b``") == []


def test_a_placeholder_is_skipped():
    assert mixed_words("{слoво}") == []


def test_a_url_and_a_link_target_are_skipped():
    assert mixed_words("https://a.b/слoво ](http://x/слoво)") == []


def test_text_glued_to_a_url_is_still_read():
    assert mixed_words("(https://a.b/x)слoво") and mixed_words("<https://a.b/x>слoво")
    assert mixed_words("[x](https://a.b/x)слoво")


def test_a_code_span_may_wrap_onto_the_next_line(tmp_path):
    path = tmp_path / "x.ru.md"
    path.write_text("слово `a\nb` слoво\n", encoding="utf-8")
    problems = page_problems(path)
    assert len(problems) == 1 and problems[0].startswith("x.ru.md:2: ")


def test_an_unpaired_backtick_does_not_hide_the_line():
    found = mixed_words("слoво ` слово")
    assert any("U+006F" in f for f in found) and UNPAIRED in found


def test_a_stray_backtick_before_a_span_is_reported():
    assert UNPAIRED in mixed_words("a ` b `code` c")


def test_the_report_names_file_and_line_of_a_catalogue(tmp_path):
    path = tmp_path / "ru.toml"
    path.write_text('# comment слoво\n[a]\nx = "ok"\ny = "слoво"\n', encoding="utf-8")
    problems = catalogue_problems(path)
    assert len(problems) == 1 and problems[0].startswith("ru.toml:4: ")
    assert "U+006F" in problems[0]


def test_the_report_names_file_and_line_of_a_page(tmp_path):
    path = tmp_path / "x.ru.md"
    path.write_text(
        "---\nsource_hash: abc\n---\n# Title { #t }\n\n```\nслoво in code\n```\n\nслoво here\n",
        encoding="utf-8",
    )
    problems = page_problems(path)
    assert len(problems) == 1 and problems[0].startswith("x.ru.md:10: ")


def test_a_clean_page_and_catalogue_report_nothing(tmp_path):
    page = tmp_path / "x.ru.md"
    page.write_text("---\nk: v\n---\nслово\n", encoding="utf-8")
    toml = tmp_path / "ru.toml"
    toml.write_text('a = "слово\\u00a0слово"\n', encoding="utf-8")
    assert page_problems(page) == [] and catalogue_problems(toml) == []
