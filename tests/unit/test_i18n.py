# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The catalogue module: plural rules, lookup, fallback, language choice."""

from pathlib import Path

import pytest

from optar import i18n

RU_LIKE = {0: "many", 1: "one", 2: "few", 5: "many", 11: "many", 12: "many", 14: "many",
           21: "one", 22: "few", 25: "many", 101: "one", 111: "many", 112: "many",
           1_000_000: "many", -1: "one"}


@pytest.fixture(autouse=True)
def english_after():
    yield
    i18n.set_language("en")


@pytest.mark.parametrize("code", ["ru", "uk", "be"])
def test_east_slavic_plurals(code):
    assert {c: i18n.plural_category(code, c) for c in RU_LIKE} == RU_LIKE


def test_polish_plurals():
    got = {c: i18n.plural_category("pl", c) for c in (1, 2, 5, 12, 21, 22, 25, 101, 112)}
    assert got == {1: "one", 2: "few", 5: "many", 12: "many", 21: "many", 22: "few",
                   25: "many", 101: "many", 112: "many"}


@pytest.mark.parametrize("code", ["en", "it", "es"])
def test_two_form_plurals(code):
    assert [i18n.plural_category(code, c) for c in (0, 1, 2, 21)] == [
        "other", "one", "other", "other"]


@pytest.mark.parametrize("code", ["tr", "ka"])
def test_one_form_plurals(code):
    assert {i18n.plural_category(code, c) for c in (0, 1, 2, 5, 21)} == {"other"}


@pytest.mark.parametrize("code", i18n.ORDER)
def test_every_count_has_a_known_category(code):
    for c in list(RU_LIKE) + [3, 4, 100, 10**9]:
        assert i18n.plural_category(code, c) in i18n.categories(code)


def test_categories():
    assert i18n.categories("en") == ("one", "other")
    assert i18n.categories("ru") == ("one", "few", "many")
    assert i18n.categories("pl") == ("one", "few", "many")
    assert i18n.categories("ka") == ("other",)


@pytest.mark.parametrize("names, want", [
    (["ru_RU.UTF-8"], "ru"), (["pl-PL"], "pl"), (["be@latin"], "be"),
    (["C", "POSIX", "", None], None), (["zh_CN", "uk_UA"], "uk"), (["KA_ge"], "ka"), ([], None),
])
def test_pick_language(catalogues, names, want):
    for code in i18n.ORDER:
        catalogues.add(code, {"language": {"name": code}})
    assert i18n.pick_language(names) == want


def test_pick_language_needs_a_present_catalogue(catalogues):
    catalogues.only("en")
    assert i18n.pick_language(["ru_RU"]) is None
    assert i18n.pick_language(["xx", "en_US"]) == "en"


def test_english_counts():
    assert i18n.n("count.page", 1) == "1 page"
    assert i18n.n("count.page", 1234) == "1,234 pages"
    assert i18n.number(1234567) == "1,234,567"
    for noun in ("page", "byte", "block", "dot", "scan"):
        assert i18n.n(f"count.{noun}", 2) == f"2 {noun}s"


def test_english_decimals():
    assert i18n.decimal(8.25, 1) == "8.2" and i18n.decimal(8.3, 1) == "8.3"
    assert i18n.decimal(100, 1) == "100.0"
    assert i18n.decimal(1234567.891, 2) == "1,234,567.89"
    assert i18n.decimal(0.04, 0) == "0"


def test_decimals_use_the_languages_separators(catalogues):
    catalogues.add("it", {"language": {"name": "Italiano"},
                          "format": {"group": ".", "decimal": ","}})  # fmt: skip
    i18n.set_language("it")
    assert i18n.decimal(8.3, 1) == "8,3"
    assert i18n.decimal(1234567.891, 2) == "1.234.567,89"
    assert i18n.number(1234567) == "1.234.567"


def test_decimals_fall_back_to_the_english_separator(catalogues):
    catalogues.add("ru", {"language": {"name": "Русский"}, "format": {"group": "\u00a0"}})
    i18n.set_language("ru")
    assert i18n.decimal(1234.5, 1) == "1\u00a0234.5"


def test_values_with_braces_are_literal(catalogues):
    catalogues.add("en", {"x": {"y": "Saved {name}"}})
    assert i18n.t("x.y", name="{0}{name}.png") == "Saved {0}{name}.png"


def test_missing_key_falls_back_to_english(catalogues):
    catalogues.add("en", {"x": {"y": "English"}})
    catalogues.add("ru", {"language": {"name": "Русский"}})
    assert i18n.set_language("ru") == "ru"
    assert i18n.t("x.y") == "English"


def test_present_key_wins_and_plurals_use_the_language(catalogues):
    catalogues.add("ru", {
        "language": {"name": "Русский"}, "format": {"group": " "},
        "count": {"page": {"one": "{n} страница", "few": "{n} страницы", "many": "{n} страниц"}},
    })
    i18n.set_language("ru")
    assert [i18n.n("count.page", c) for c in (1, 2, 5)] == [
        "1 страница", "2 страницы", "5 страниц"]
    assert i18n.n("count.page", 1234) == "1 234 страницы"
    assert i18n.language() == "ru"


def test_a_page_list_takes_single_only_for_exactly_one_page(catalogues):
    """``listing`` is not a plural rule: in Russian the plural form for 1 also serves 21,
    a list of 21 pages takes ``several``."""
    catalogues.add("ru", {
        "language": {"name": "Русский"},
        "x": {"pages": {"single": "страница {pages}", "several": "страницы {pages}"}},
    })
    i18n.set_language("ru")
    assert i18n.listing("x.pages", 1, pages="3") == "страница 3"
    assert i18n.listing("x.pages", 21, pages="1–21") == "страницы 1–21"
    assert i18n.listing("x.pages", 2, pages="3, 4") == "страницы 3, 4"


def test_unknown_key_raises():
    with pytest.raises(KeyError):
        i18n.t("no.such.key")
    with pytest.raises(KeyError):
        i18n.n("no.such.key", 1)


def test_unknown_language_is_english():
    assert i18n.set_language("xx") == "en" and i18n.set_language(None) == "en"


def test_languages_lists_only_present_catalogues_in_order(catalogues):
    catalogues.only("en")
    assert i18n.languages() == {"en": "English"}
    catalogues.add("es", {"language": {"name": "Español"}})
    catalogues.add("ru", {"language": {"name": "Русский"}})
    assert list(i18n.languages().items()) == [
        ("en", "English"), ("ru", "Русский"), ("es", "Español")]


def test_catalogue_is_a_fresh_flat_copy():
    cat = i18n.catalogue("en")
    assert cat["language.name"] == "English"
    assert cat["count.page"] == {"one": "{n} page", "other": "{n} pages"}
    cat["count.page"]["one"] = "changed"
    assert i18n.catalogue("en")["count.page"]["one"] == "{n} page"
    assert i18n.catalogue("xx") == {}


def test_encodable(catalogues):
    assert i18n.encodable("en", "utf-8")
    catalogues.add("ka", {"language": {"name": "ქართული"}})
    assert i18n.encodable("ka", "utf-8")
    assert not i18n.encodable("ka", "cp1252")


def test_encodable_looks_only_at_the_tables_named(catalogues):
    catalogues.add("it", {"language": {"name": "Italiano"}, "cli": {"x": "uno"},
                          "gui": {"y": "due\u2026", "cli": {"z": "tre"}}})  # fmt: skip
    catalogues.add("ru", {"gui": {"cli": {"z": "\u0442\u0440\u0438"}}})
    assert not i18n.encodable("it", "cp850")  # the window's "…"
    assert i18n.encodable("it", "cp850", ("cli", "language"))
    assert not i18n.encodable("it", "cp850", ("cli", "gui"))
    assert i18n.encodable("ru", "cp1251", ("gui.cli",))
    assert not i18n.encodable("ru", "cp1252", ("gui.cli",))
    assert i18n.encodable("ru", "cp1252", ("gui.c",))  # a table, not a prefix of a name


def test_choosing_a_language_reads_no_catalogue(monkeypatch):
    """Only the files' presence counts: a malformed catalogue stops nothing there."""
    read = []
    monkeypatch.setattr(i18n, "_cache", {})
    monkeypatch.setattr(i18n, "_read", lambda code: read.append(code))
    assert i18n.pick_language(["ru_RU.UTF-8"]) == "ru"
    assert i18n.pick_language(["xx", "de_DE", "pl"]) == "pl"
    assert i18n.pick_language(["de_DE", None, ""]) is None
    assert read == []


def test_a_language_without_a_file_is_not_picked(catalogues):
    catalogues.only("en")
    assert i18n.pick_language(["ru_RU"]) is None
    catalogues.add("ru", {"language": {"name": "Русский"}})
    assert i18n.pick_language(["ru_RU"]) == "ru"


def test_module_reads_no_environment_and_imports_no_qt():
    source = Path(i18n.__file__).read_text(encoding="utf-8")
    for banned in ("os.environ", "getenv", "PySide6", "print(", "sys.exit", "sys.argv"):
        assert banned not in source


def test_catalogues_fixture_restores_everything(catalogues):
    catalogues.add("ru", {"language": {"name": "Русский"}})
    catalogues.add("en", {"x": {"y": "added"}})
    i18n.set_language("ru")
    assert i18n.t("x.y") == "added"
    assert i18n.n("count.scan", 3) == "3 scans"   # real English still merged in


def test_catalogues_fixture_teardown_is_clean():
    assert i18n.language() == "en"
    assert getattr(i18n._read, "__self__", None) is None
    with pytest.raises(KeyError):
        i18n.t("x.y")


def test_catalogues_only_hides_real_catalogues(catalogues):
    catalogues.only()
    assert i18n.languages() == {}
    catalogues.add("en", {"language": {"name": "E"}})
    assert i18n.languages() == {"en": "E"}


def test_unsupplied_placeholder_names_key_and_language(catalogues):
    catalogues.add("en", {"x": {"y": "Hello {who}", "z": "Bad {0}",
                                "p": {"one": "{n} {thing}", "other": "{n} {thing}s"}}})
    with pytest.raises(KeyError, match=r"'x\.y'.*'en'.*'who'"):
        i18n.t("x.y")
    with pytest.raises(KeyError, match=r"'x\.z'.*positional"):
        i18n.t("x.z")
    with pytest.raises(KeyError, match=r"'x\.p'.*'thing'"):
        i18n.n("x.p", 2)


def _not_an_image(path):
    from optar.errors import OptarError
    from optar.imageio import read_scan

    path.write_text("hello")
    with pytest.raises(OptarError) as caught:
        read_scan(path)
    return caught.value


def _expected_not_an_image(code, path, items):
    """The sentence built from the real catalogue of ``code`` alone."""
    cat = i18n.catalogue(code)
    joined = cat["alternatives.last"].format(
        items=cat["alternatives.separator"].join(items[:-1]), last=items[-1])
    return cat["err.not_an_image"].format(path=path, formats=joined)


def test_alternatives_join_in_the_language():
    assert i18n.alternatives(("A",)) == "A"
    assert i18n.alternatives(("A", "B", "C")) == "A, B or C"
    i18n.set_language("ru")
    assert i18n.alternatives(("A", "B", "C")) == "A, B или C"


@pytest.mark.parametrize("code", ["ru", "uk", "be", "pl", "ka", "tr", "it", "es"])
def test_the_accepted_formats_are_joined_in_the_language(tmp_path, code):
    e = _not_an_image(tmp_path / "t.txt")
    items = tuple(e.values["formats"])
    english = str(e)
    assert i18n.error_text(e) == english  # English: the text of the exception
    i18n.set_language(code)
    worded = i18n.error_text(e)
    assert worded == _expected_not_an_image(code, tmp_path / "t.txt", items)
    assert " or " not in worded and str(e) == english


def test_the_accepted_formats_read_as_the_native_readers_asked(tmp_path):
    e = _not_an_image(tmp_path / "t.txt")
    for code, joined in (("ru", "BMP, PGM/PPM или JPEG"), ("pl", "BMP, PGM/PPM lub JPEG"),
                         ("tr", "BMP, PGM/PPM ya da JPEG")):
        i18n.set_language(code)
        assert joined in i18n.error_text(e)
