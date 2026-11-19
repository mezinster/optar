# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The places a new language must be added to, each checked against ``i18n.ORDER``:
a translator adding ``de.toml`` gets a failing test naming every place left."""

import importlib.util
import re
from pathlib import Path

from optar import cli, i18n
from tests.unit import test_catalogues, test_translation_text

ROOT = Path(__file__).resolve().parents[2]
TRANSLATED = set(i18n.ORDER) - {"en"}


def _smoke():
    spec = importlib.util.spec_from_file_location("smoke", ROOT / "packaging" / "smoke.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_catalogue_files_are_the_languages_of_order():
    files = {p.stem for p in (ROOT / "src" / "optar" / "locale").glob("*.toml")}
    assert files == set(i18n.ORDER), (
        "src/optar/locale/*.toml and i18n.ORDER differ: "
        f"files not in ORDER {sorted(files - set(i18n.ORDER))}, "
        f"ORDER without a file {sorted(set(i18n.ORDER) - files)}"
    )


def test_every_language_has_its_plural_categories():
    assert set(i18n._CATEGORIES) == set(i18n.ORDER), (
        f"i18n._CATEGORIES lacks {sorted(set(i18n.ORDER) - set(i18n._CATEGORIES))} "
        "(and plural_category its rule)"
    )
    for code in i18n.ORDER:
        used = {i18n.plural_category(code, n) for n in range(200)}
        assert used == set(i18n.categories(code)), (code, used)


def test_the_packaged_build_check_knows_every_language():
    smoke = _smoke()
    assert smoke.ORDER == i18n.ORDER, "packaging/smoke.py ORDER is not i18n.ORDER"
    assert smoke.TERMINAL_TABLES == cli.TERMINAL_TABLES, (
        "packaging/smoke.py TERMINAL_TABLES is not optar.cli.TERMINAL_TABLES"
    )


def test_every_language_has_its_group_separator():
    assert set(test_catalogues.LANGUAGE_GROUP) == TRANSLATED, (
        "tests/unit/test_catalogues.py LANGUAGE_GROUP does not list every translated "
        f"language: {sorted(TRANSLATED ^ set(test_catalogues.LANGUAGE_GROUP))}"
    )


def test_every_language_has_its_script():
    assert set(test_translation_text.OWN_SCRIPT) == TRANSLATED, (
        "tests/unit/test_translation_text.py OWN_SCRIPT does not list every translated "
        f"language: {sorted(TRANSLATED ^ set(test_translation_text.OWN_SCRIPT))}"
    )


# --- mkdocs.yml, read as text (the default suite has no YAML reader) ----------------


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _value(text: str) -> str:
    return text.strip().strip("\"'")


def _site_languages(lines: list[str]) -> list[tuple[str, set[str] | None]]:
    """(locale, the keys of its nav_translations or None) for each entry of the
    i18n plugin's ``languages``, in order."""
    start = next(i for i, line in enumerate(lines) if line.strip() == "languages:")
    base = _indent(lines[start])
    entries: list[tuple[str, set[str] | None]] = []
    keys: set[str] | None = None
    nav_indent = None
    for line in lines[start + 1:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if _indent(line) <= base:
            break
        stripped = line.strip()
        match = re.fullmatch(r"- locale:\s*(\S+)", stripped)
        if match:
            keys, nav_indent = None, None
            entries.append((_value(match.group(1)), None))
        elif stripped == "nav_translations:":
            keys, nav_indent = set(), _indent(line)
            entries[-1] = (entries[-1][0], keys)
        elif nav_indent is not None and _indent(line) > nav_indent:
            keys.add(_value(stripped.partition(":")[0]))
        else:
            nav_indent = None
    return entries


def _nav_titles(lines: list[str]) -> set[str]:
    start = lines.index("nav:")
    titles = set()
    for line in lines[start + 1:]:
        if line.strip() and not line.startswith(" "):
            break
        match = re.match(r"\s*- ([^:]+):", line)
        if match:
            titles.add(_value(match.group(1)))
    return titles


def test_the_site_has_every_language_in_order_with_every_title():
    lines = (ROOT / "mkdocs.yml").read_text(encoding="utf-8").splitlines()
    entries = _site_languages(lines)
    assert [code for code, _ in entries] == list(i18n.ORDER), (
        "mkdocs.yml languages are not i18n.ORDER in order"
    )
    titles = _nav_titles(lines)
    assert len(titles) == 14  # the eleven pages and the three sections
    for code, keys in entries[1:]:
        assert keys == titles, (
            f"mkdocs.yml {code}: nav_translations keys differ from the nav titles: "
            f"missing {sorted(titles - (keys or set()))}, extra {sorted((keys or set()) - titles)}"
        )
