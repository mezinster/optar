# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Every translated documentation page is complete and in step with English.

The checks are plain functions on page text that return a list of problems
(empty when the page is fine); the parametrised tests run them on the real
pages, and the fault tests below run them on small made-up pages to show they
bite. English pages are the ``docs/*.md`` whose stem has no dot; a translation
is ``docs/<page>.<code>.md``. ``docs/superpowers`` is not part of the site and
is ignored. There is no language but English until translations arrive, so the
per-language tests are an empty set today.
"""

import functools
import importlib.util
import posixpath
import re
from pathlib import Path

import pytest

from optar import i18n

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
FORMAT_URL = "https://mezinster.github.io/optar/format/"


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "translation_status", ROOT / "tools" / "translation_status.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


status = _load_tool()
LANGUAGES = [c for c in i18n.languages() if c != "en"]
PAGES = [p.stem for p in status.english_pages(DOCS)]
CODE_AND_PAGE = [pytest.param(c, p, id=f"{c}-{p}") for c in LANGUAGES for p in PAGES]


def translated_path(code: str, page: str) -> Path:
    return DOCS / f"{page}.{code}.md"


# --- Reading a page -----------------------------------------------------------------

FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*$")
HEADING_ID = re.compile(r"\{[ \t]*#([^\s}]+)[ \t]*\}$")
ATTR_ID = re.compile(r"\{[^}\n]*?#([\w:.\-]+)[^}\n]*\}")


def body_of(text: str) -> str:
    """The page without its front matter."""
    lines = text.split("\n")
    if lines and lines[0].rstrip() == "---":
        for i, line in enumerate(lines[1:], 1):
            if line.rstrip() == "---":
                return "\n".join(lines[i + 1:])
    return text


def _closes(m, marker: str) -> bool:
    """Whether the fence-like line (match ``m``) closes the block opened by ``marker``."""
    return bool(
        m
        and m.group(1)[0] == marker[0]
        and len(m.group(1)) >= len(marker)
        and not m.group(2).strip()
    )


def outside_fences(body: str):
    """(line, is_fence_line) pairs for each line outside a fenced code block."""
    marker = None
    for line in body.split("\n"):
        m = FENCE.match(line)
        if marker is None:
            if m:
                marker = m.group(1)
                continue
            yield line
        elif _closes(m, marker):
            marker = None


def fenced_blocks(body: str) -> list[tuple[str, str]]:
    """(info string, content) of each fenced block, in order."""
    blocks, marker, info, current = [], None, "", []
    for line in body.split("\n"):
        m = FENCE.match(line)
        if marker is None:
            if m:
                marker, info, current = m.group(1), m.group(2).strip(), []
        elif _closes(m, marker):
            blocks.append((info, "\n".join(current)))
            marker = None
        else:
            current.append(line)
    if marker is not None:
        blocks.append((info, "\n".join(current)))
    return blocks


def headings(body: str) -> list[tuple[int, str, str | None]]:
    """(level, text without its id, explicit id or None) of each heading."""
    found = []
    for line in outside_fences(body):
        m = HEADING.match(line)
        if m:
            text = re.sub(r"[ \t]+#+$", "", m.group(2))  # closing hashes
            ident = HEADING_ID.search(text)
            found.append((len(m.group(1)), text[: ident.start()].rstrip() if ident else text,
                          ident.group(1) if ident else None))
    return found


@functools.cache
def english_anchors(body: str) -> list[str]:
    """The ids the site gives the headings of an English page, in order.

    This runs Python-Markdown's own ``toc`` extension with the settings of
    ``mkdocs.yml`` (default slugify, ``_1`` suffixes for repeats, explicit
    ``{ #id }`` kept), so the result is what the site produces.
    """
    markdown = pytest.importorskip("markdown")
    md = markdown.Markdown(extensions=["toc", "attr_list", "fenced_code", "tables", "admonition"])
    md.convert(body)
    found = []

    def walk(tokens):
        for token in tokens:
            found.append(token["id"])
            walk(token["children"])

    walk(md.toc_tokens)
    return found


# --- The checks ---------------------------------------------------------------------


def missing_pages(code: str, docs: Path = DOCS) -> list[str]:
    return [
        f"docs/{p.stem}.{code}.md"
        for p in status.english_pages(docs)
        if not (docs / f"{p.stem}.{code}.md").exists()
    ]


def code_block_problems(english: str, translated: str) -> list[str]:
    en, tr = fenced_blocks(body_of(english)), fenced_blocks(body_of(translated))
    problems = []
    if len(en) != len(tr):
        problems.append(f"{len(tr)} fenced code blocks, English has {len(en)}")
    for i, (a, b) in enumerate(zip(en, tr, strict=False), 1):
        if a != b:
            problems.append(f"code block {i} differs from English")
    return problems


def heading_id_problems(english: str, translated: str) -> list[str]:
    wanted = english_anchors(body_of(english))
    found = headings(body_of(translated))
    problems = [
        f"heading {text!r} does not end with {{ #id }}" for _, text, ident in found if ident is None
    ]
    ids = [ident for _, _, ident in found if ident is not None]
    if len(found) != len(wanted):
        problems.append(f"{len(found)} headings, English has {len(wanted)}")
    elif not problems and ids != wanted:
        for i, (got, want) in enumerate(zip(ids, wanted, strict=True), 1):
            if got != want:
                problems.append(f"heading {i} has id {got!r}, English has {want!r}")
    return problems


def _split_row(line: str) -> list[str]:
    cells, current, code = [], [], False
    chars = iter(line.strip())
    for ch in chars:
        if ch == "\\":
            current.append(ch + next(chars, ""))
        elif ch == "`":
            code = not code
            current.append(ch)
        elif ch == "|" and not code:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    cells.append("".join(current).strip())
    if line.strip().startswith("|"):
        cells = cells[1:]
    if line.strip().endswith("|") and cells and cells[-1] == "":
        cells = cells[:-1]
    return cells


def tables(body: str) -> list[list[list[str]]]:
    """Each table as rows of cells, separator rows left out."""
    found, current = [], []
    for line in list(outside_fences(body)) + [""]:
        if line.strip().startswith("|"):
            cells = _split_row(line)
            if not all(re.fullmatch(r":?-+:?", c) for c in cells if c) or not any(cells):
                current.append(cells)
        elif current:
            found.append(current)
            current = []
    return found


_NUMBER = re.compile(r"[\d.,+\-−–×*/%()=<>^:;]*\d[\d.,+\-−–×*/%()=<>^:;a-fA-FxX_]*")
_CODE = re.compile(r"(`[^`]+`[\s,/]*)+")


def is_plain_value(cell: str) -> bool:
    """A cell that is only numbers, hex values or code: it must not be translated."""
    if not cell:
        return False
    if _CODE.fullmatch(cell):
        return True
    return all(_NUMBER.fullmatch(token) for token in cell.split())


def format_number_problems(english: str, translated: str) -> list[str]:
    en, tr = tables(body_of(english)), tables(body_of(translated))
    if len(en) != len(tr):
        return [f"{len(tr)} tables, English has {len(en)}"]
    problems = []
    for t, (table_en, table_tr) in enumerate(zip(en, tr, strict=True), 1):
        if len(table_en) != len(table_tr):
            problems.append(f"table {t} has {len(table_tr)} rows, English has {len(table_en)}")
            continue
        for r, (row_en, row_tr) in enumerate(zip(table_en, table_tr, strict=True), 1):
            if len(row_en) != len(row_tr):
                problems.append(
                    f"table {t} row {r} has {len(row_tr)} cells, English has {len(row_en)}"
                )
                continue
            for c, (a, b) in enumerate(zip(row_en, row_tr, strict=True), 1):
                if is_plain_value(a) and a != b:
                    problems.append(f"table {t} row {r} cell {c} is {b!r}, English has {a!r}")
    return problems


def normative_problems(translated: str) -> list[str]:
    """The first paragraph after the title must link the English format page."""
    lines = body_of(translated).split("\n")
    for i, line in enumerate(lines):  # noqa: B007 - i is used after the loop
        m = HEADING.match(line)
        if m and len(m.group(1)) == 1:
            break
    else:
        return ["no title"]
    paragraph = []
    for line in lines[i + 1:]:
        if not line.strip():
            if paragraph:
                break
            continue
        paragraph.append(line)
    if not re.search(re.escape(FORMAT_URL) + r"?(?![\w-])", " ".join(paragraph)):
        return [f"the first paragraph does not link {FORMAT_URL}"]
    return []


def hash_problems(translated: str) -> list[str]:
    if status.source_hash(translated) is None:
        return ["front matter has no source_hash of 40 hex digits"]
    return []


_LINK = re.compile(r"""(?<!\\)\]\(\s*<?([^)\s>]+)>?(?:\s+(?:"[^"]*"|'[^']*'))?\s*\)""")
_REFERENCE = re.compile(r"^ {0,3}\[[^\]]+\]:\s*<?(\S+?)>?(?:\s+.*)?$")
_ABSOLUTE = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.\-]*:|//)")


def links(body: str) -> list[str]:
    found = []
    for line in outside_fences(body):
        line = re.sub(r"(`+)[^`]*?\1", "", line)
        found += _LINK.findall(line)
        m = _REFERENCE.match(line)
        if m:
            found.append(m.group(1))
    return found


def page_ids(body: str) -> set[str]:
    """Explicit ids on a translated page: heading ids and other ``{ #id }`` marks."""
    ids = {ident for _, _, ident in headings(body) if ident}
    for line in outside_fences(body):
        ids.update(ATTR_ID.findall(line))
    return ids


def link_problems(
    code: str, page: str, translated: dict[str, str], english: set[str], ids_of=page_ids
) -> list[str]:
    """Links of ``translated[page]``. ``translated`` maps stem to text; ``english`` is the
    set of English page stems; ``ids_of`` gives the ids of a page body."""
    problems = []
    for target in links(body_of(translated[page])):
        if _ABSOLUTE.match(target):
            continue
        path, _, fragment = target.partition("#")
        if not path:
            stem = page
        elif path.endswith(".md"):
            stem = posixpath.normpath(path)[: -len(".md")]
            if "." in stem or "/" in stem:
                problems.append(f"{target}: link to the English page's name, such as install.md")
                continue
            if stem not in english:
                problems.append(f"{target}: no such page")
                continue
            if stem not in translated:
                problems.append(f"{target}: page {stem}.{code}.md does not exist")
                continue
        else:
            continue
        if fragment and fragment not in ids_of(body_of(translated[stem])):
            problems.append(f"{target}: no heading or id {fragment!r} on {stem}.{code}.md")
    return problems


def translated_pages(code: str) -> dict[str, str]:
    return {
        p: translated_path(code, p).read_text(encoding="utf-8")
        for p in PAGES
        if translated_path(code, p).exists()
    }


def english_text(page: str) -> str:
    return (DOCS / f"{page}.md").read_text(encoding="utf-8")


# --- The per-language tests (an empty set until translations arrive) -----------------


@pytest.mark.parametrize("code", LANGUAGES)
def test_every_page_exists(code):
    assert not missing_pages(code)


@pytest.mark.parametrize(("code", "page"), CODE_AND_PAGE)
def test_code_blocks_equal_english(code, page):
    translated = translated_path(code, page).read_text(encoding="utf-8")
    assert not code_block_problems(english_text(page), translated)


@pytest.mark.parametrize(("code", "page"), CODE_AND_PAGE)
def test_heading_ids_equal_english_anchors(code, page):
    translated = translated_path(code, page).read_text(encoding="utf-8")
    assert not heading_id_problems(english_text(page), translated)


@pytest.mark.parametrize("code", LANGUAGES)
def test_format_page_numbers_equal_english(code):
    translated = translated_path(code, "format").read_text(encoding="utf-8")
    assert not format_number_problems(english_text("format"), translated)


@pytest.mark.parametrize("code", LANGUAGES)
def test_format_page_says_english_is_normative(code):
    translated = translated_path(code, "format").read_text(encoding="utf-8")
    assert not normative_problems(translated)


@pytest.mark.parametrize(("code", "page"), CODE_AND_PAGE)
def test_source_hash_is_present(code, page):
    assert not hash_problems(translated_path(code, page).read_text(encoding="utf-8"))


@pytest.mark.parametrize(("code", "page"), CODE_AND_PAGE)
def test_links_point_at_existing_pages_and_ids(code, page):
    assert not link_problems(code, page, translated_pages(code), set(PAGES))


# --- The English pages themselves pass the checks that can apply to them ---------------


def test_english_pages_are_found_without_the_working_papers():
    assert "index" in PAGES and "format" in PAGES
    assert all("." not in p for p in PAGES)
    assert len(PAGES) == 11


@pytest.mark.parametrize("page", PAGES)
def test_english_page_compared_with_itself_is_clean(page):
    text = english_text(page)
    assert not code_block_problems(text, text)
    assert not format_number_problems(text, text)
    assert len(headings(body_of(text))) == len(english_anchors(body_of(text)))


@pytest.mark.parametrize("page", PAGES)
def test_english_links_resolve(page):
    texts = {p: english_text(p) for p in PAGES}

    def ids_of(body):
        return set(english_anchors(body)) | page_ids(body)

    assert not link_problems("en", page, texts, set(PAGES), ids_of)


# --- The checks bite ----------------------------------------------------------------

EN_PAGE = """# Title

## Put a file on paper

Some text with [a link](other.md#where-to-go).

```bash
optar --protect high file
```

## Put a file on paper

| Name | Value | Note |
|---|---|---|
| width | 65 | `ROWS` |
| mask | 0x1F | a word |

### Where to go

```
# not a heading
```
"""

TR_PAGE = """---
source_hash: 0123456789abcdef0123456789abcdef01234567
---

# Titel { #title }

## Eine Datei { #put-a-file-on-paper }

Text mit [Link](other.md#where-to-go).

```bash
optar --protect high file
```

## Eine Datei { #put-a-file-on-paper_1 }

| Name | Wert | Hinweis |
|---|---|---|
| Breite | 65 | `ROWS` |
| Maske | 0x1F | ein Wort |

### Wohin { #where-to-go }

```
# not a heading
```
"""


def test_the_made_up_pair_is_clean():
    assert not code_block_problems(EN_PAGE, TR_PAGE)
    assert not heading_id_problems(EN_PAGE, TR_PAGE)
    assert not format_number_problems(EN_PAGE, TR_PAGE)
    assert not hash_problems(TR_PAGE)


def test_english_anchors_are_computed_as_the_site_does():
    assert english_anchors(body_of(EN_PAGE)) == [
        "title", "put-a-file-on-paper", "put-a-file-on-paper_1", "where-to-go",
    ]
    explicit = "# A\n\n## Section { #custom }\n\n## Section\n\n## Dossier élevé\n"
    assert english_anchors(explicit) == ["a", "custom", "section", "dossier-eleve"]
    assert english_anchors("# A\n\n## A\n\n## A\n") == ["a", "a_1", "a_2"]


def test_a_changed_code_block_is_reported():
    bad = TR_PAGE.replace("--protect high", "--schutz hoch")
    assert code_block_problems(EN_PAGE, bad)
    assert code_block_problems(EN_PAGE, TR_PAGE.replace("```bash", "```sh"))
    assert code_block_problems(EN_PAGE, TR_PAGE.replace("# not a heading", "# kein Titel"))
    assert code_block_problems(EN_PAGE, TR_PAGE + "\n```\nextra\n```\n")


def test_missing_wrong_and_reordered_heading_ids_are_reported():
    assert heading_id_problems(EN_PAGE, TR_PAGE.replace(" { #where-to-go }", ""))
    assert heading_id_problems(EN_PAGE, TR_PAGE.replace("#where-to-go }", "#wohin }"))
    twice = TR_PAGE.replace("#put-a-file-on-paper_1", "#put-a-file-on-paper")
    assert heading_id_problems(EN_PAGE, twice)
    assert heading_id_problems(EN_PAGE, TR_PAGE + "\n## Mehr { #more }\n")
    assert heading_id_problems(EN_PAGE, TR_PAGE.replace("### Wohin { #where-to-go }\n", ""))


def test_a_heading_inside_a_code_block_is_not_a_heading():
    found = [h[1] for h in headings(body_of(TR_PAGE))]
    assert found == ["Titel", "Eine Datei", "Eine Datei", "Wohin"]


def test_a_changed_number_or_code_cell_is_reported_but_words_are_free():
    assert format_number_problems(EN_PAGE, TR_PAGE.replace("| 65 |", "| 66 |"))
    assert format_number_problems(EN_PAGE, TR_PAGE.replace("0x1F", "0x1E"))
    assert format_number_problems(EN_PAGE, TR_PAGE.replace("`ROWS`", "`ZEILEN`"))
    assert format_number_problems(EN_PAGE, TR_PAGE.replace("| 65 | `ROWS` |\n", ""))
    assert not format_number_problems(EN_PAGE, TR_PAGE.replace("ein Wort", "anderes Wort"))
    assert not is_plain_value("a word") and not is_plain_value("bad") and not is_plain_value("")
    assert is_plain_value("0x1F") and is_plain_value("1,234") and is_plain_value("`a` / `b`")


def test_the_format_page_must_link_the_english_page():
    page = (
        f"---\nsource_hash: {'a' * 40}\n---\n\n# Format\n\n"
        f"Normativ ist [die englische Seite]({FORMAT_URL}).\n\nMehr.\n"
    )
    assert not normative_problems(page)
    assert not normative_problems(page.replace(FORMAT_URL, FORMAT_URL + "#top"))
    assert normative_problems(page.replace(FORMAT_URL, "format.md"))
    assert normative_problems(page.replace(FORMAT_URL, "https://example.org/format/"))
    later = page.replace("Normativ ist", "Text.\n\nNormativ ist")
    assert normative_problems(later)


def test_a_missing_or_malformed_source_hash_is_reported():
    assert hash_problems("# no front matter\n")
    assert hash_problems("---\nsource_hash: 123\n---\n# x\n")
    assert hash_problems("---\nsource_hash: " + "g" * 40 + "\n---\n# x\n")
    assert not hash_problems("---\nsource_hash: " + "a" * 40 + "\n---\n# x\n")


def _page(text: str) -> str:
    front = "---\nsource_hash: " + "a" * 40 + "\n---\n\n"
    return front + "# T { #t }\n\n" + text + "\n\n## Sec { #sec }\n"


def test_links_are_checked_against_the_pages_and_ids_of_the_language():
    pages = {"a": _page("[x](b.md#sec) [y](#sec) [z](#t)"), "b": _page("text")}
    assert not link_problems("ru", "a", pages, {"a", "b"})
    for bad in ("[x](b.md#nope)", "[x](#nope)", "[x](c.md)", "[x](b.ru.md)", "[x](../b.md)"):
        pages = {"a": _page(bad), "b": _page("text")}
        assert link_problems("ru", "a", pages, {"a", "b", "c"}), bad
    assert link_problems("ru", "a", {"a": _page("[x](c.md)")}, {"a", "c"})  # not yet translated


def test_absolute_links_images_and_code_are_skipped():
    text = (
        "[w](https://example.org/x#y) [m](mailto:a@b.c) ![i](img/p.png) "
        "`[no](nothing.md)` [f](https://mezinster.github.io/optar/format/#top)\n\n"
        "```\n[no](nothing.md)\n```\n"
    )
    assert not link_problems("ru", "a", {"a": _page(text)}, {"a"})


def test_reference_style_links_are_checked():
    pages = {"a": _page("[x][r]\n\n[r]: gone.md")}
    assert link_problems("ru", "a", pages, {"a", "gone"})


def test_missing_pages_are_listed(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    for name in ("index.md", "install.md", "index.ru.md", "x.y.md"):
        (docs / name).write_text("# T\n")
    assert missing_pages("ru", docs) == ["docs/install.ru.md"]


# --- tools/translation_status.py ----------------------------------------------------


def _tree(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "src" / "optar" / "locale").mkdir(parents=True)
    for name in ("index", "install"):
        (tmp_path / "docs" / f"{name}.md").write_text(f"# {name}\n")
    return tmp_path


def test_blob_hash_is_the_git_hash():
    # git hash-object of an empty file, and of "hello\n"
    assert status.blob_hash(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
    assert status.blob_hash(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_status_reports_stale_and_missing_pages(tmp_path):
    root = _tree(tmp_path)
    assert status.problems(root) == []  # no language has started
    (root / "src" / "optar" / "locale" / "ru.toml").write_text("")
    assert status.problems(root) == [
        ("docs/index.ru.md", "missing"), ("docs/install.ru.md", "missing"),
    ]
    good = status.blob_hash((root / "docs" / "index.md").read_bytes())
    (root / "docs" / "index.ru.md").write_text(f"---\nsource_hash: {good}\n---\n# i\n")
    (root / "docs" / "install.ru.md").write_text(f"---\nsource_hash: {'0' * 40}\n---\n# i\n")
    assert status.problems(root) == [("docs/install.ru.md", "stale")]
    (root / "docs" / "install.ru.md").write_text("# no front matter\n")
    assert status.problems(root) == [("docs/install.ru.md", "stale")]
    assert status.problems(root, ["uk"]) == [
        ("docs/index.uk.md", "missing"), ("docs/install.uk.md", "missing"),
    ]


def test_the_working_papers_are_ignored(tmp_path):
    root = _tree(tmp_path)
    (root / "docs" / "superpowers").mkdir()
    (root / "docs" / "superpowers" / "plan.md").write_text("# plan\n")
    assert [p.stem for p in status.english_pages(root / "docs")] == ["index", "install"]


def test_main_prints_lines_and_check_fails_only_for_missing(tmp_path, monkeypatch, capsys):
    root = _tree(tmp_path)
    monkeypatch.setattr(status, "ROOT", root)
    assert status.main(["ru"]) == 0
    assert capsys.readouterr().out == "docs/index.ru.md: missing\ndocs/install.ru.md: missing\n"
    assert status.main(["--check", "ru"]) == 1
    capsys.readouterr()
    for name in ("index", "install"):
        (root / "docs" / f"{name}.ru.md").write_text("# stale\n")
    assert status.main(["--check", "ru"]) == 0
    assert "stale" in capsys.readouterr().out


def test_the_real_tree_has_nothing_stale_or_missing_yet():
    assert all(state != "stale" for _, state in status.problems(ROOT, []))
