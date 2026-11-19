# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Every language's catalogue is complete and in step with English.

The checks are plain functions that return a list of problems (empty when the
catalogue is fine); the parametrised tests run them on the real catalogues, and
the fault tests below run them on small made-up ones to show they bite. The
per-language tests run on each of the eight translated languages.
"""

import importlib.util
import inspect
import itertools
from pathlib import Path
from string import Formatter

import pytest

from optar import i18n

ROOT = Path(__file__).resolve().parents[2]


def _started() -> list[str]:
    """Languages with a catalogue or any translated page, in the order of ``i18n.ORDER``.

    A language that has only one of the two is still listed, so the tests of the
    other fail with a clear message instead of the language going unchecked.
    """
    spec = importlib.util.spec_from_file_location(
        "translation_status", ROOT / "tools" / "translation_status.py"
    )
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    known = set(tool.started_languages(ROOT)) | set(i18n.languages())
    return [c for c in i18n.ORDER if c != "en" and c in known]


LANGUAGES = _started()
GROUPS = (",", ".", " ", "\u00a0", "\u202f", "")
# The thousands separator each language must use (the translators' brief).
LANGUAGE_GROUP = {
    "ru": "\u00a0", "uk": "\u00a0", "be": "\u00a0", "pl": "\u00a0", "ka": "\u00a0",
    "it": ".", "es": ".", "tr": ".",
}


def _fields(template: str) -> set[str]:
    return {name for _, name, _, _ in Formatter().parse(template) if name is not None}


def _forms(entry) -> dict[str, str]:
    return entry if isinstance(entry, dict) else {"": entry}


def key_problems(english: dict, other: dict) -> list[str]:
    missing = sorted(set(english) - set(other))
    extra = sorted(set(other) - set(english))
    problems = []
    if missing:
        problems.append(f"missing keys: {missing}")
    if extra:
        problems.append(f"extra keys: {extra}")
    return problems


def placeholder_problems(english: dict, other: dict) -> list[str]:
    problems = []
    for key in sorted(set(english) & set(other)):
        en, tr = english[key], other[key]
        if isinstance(en, dict) != isinstance(tr, dict):
            problems.append(f"{key}: plural entry in one catalogue and a plain string in the other")
            continue
        try:
            if isinstance(en, dict):
                union = set().union(*(_fields(s) for s in en.values()))
                en_n = any("n" in _fields(s) for s in en.values())
                for category, form in tr.items():
                    fields = _fields(form)
                    if not fields <= union:
                        unknown = sorted(fields - union)
                        problems.append(f"{key}.{category}: unknown placeholders {unknown}")
                    if ("n" in fields) != en_n:
                        problems.append(
                            f"{key}.{category}: {{n}} must be {'present' if en_n else 'absent'}"
                        )
            elif _fields(en) != _fields(tr):
                have, want = sorted(_fields(tr)), sorted(_fields(en))
                problems.append(f"{key}: placeholders {have} but English has {want}")
        except ValueError as e:
            problems.append(f"{key}: malformed placeholder ({e})")
    return problems


def category_problems(code: str, catalogue: dict) -> list[str]:
    wanted = set(i18n.categories(code))
    return [
        f"{key}: categories {sorted(entry)} but {code} has {sorted(wanted)}"
        for key, entry in sorted(catalogue.items())
        if isinstance(entry, dict) and set(entry) != wanted
    ]


def value_problems(catalogue: dict) -> list[str]:
    """Empty values, malformed or literal braces: each value formats with dummy values."""
    problems = []
    for key, entry in sorted(catalogue.items()):
        for category, form in _forms(entry).items():
            where = f"{key}.{category}" if category else key
            # The thousands separator may be a space (name_and_separator_problems checks it).
            blank_ok = key == "format.group" and form in GROUPS and form != ""
            if not isinstance(form, str) or not (form.strip() or blank_ok):
                problems.append(f"{where}: empty or not a string")
                continue
            try:
                fields = _fields(form)
                shown = form.format(**{name: "1" for name in fields})
            except (ValueError, KeyError, IndexError, AttributeError) as e:
                problems.append(f"{where}: does not format ({e})")
                continue
            if any(not name.isidentifier() for name in fields):
                problems.append(f"{where}: placeholder names must be plain names")
            if "{" in shown or "}" in shown:
                problems.append(f"{where}: contains a literal brace")
    return problems


def name_and_separator_problems(catalogue: dict, code: str | None = None) -> list[str]:
    problems = []
    if not catalogue:
        return ["there is no catalogue (src/optar/locale/<code>.toml)"]
    name = catalogue.get("language.name")
    if not isinstance(name, str) or not name.strip():
        problems.append("[language].name is missing or empty")
    if catalogue.get("format.group") not in GROUPS:
        problems.append(f"[format].group is {catalogue.get('format.group')!r}, not a separator")
    elif code in LANGUAGE_GROUP and catalogue["format.group"] != LANGUAGE_GROUP[code]:
        problems.append(
            f"[format].group is {catalogue['format.group']!r}, {code} uses "
            f"{LANGUAGE_GROUP[code]!r}"
        )
    return problems


DECIMALS = (".", ",")


def decimal_problems(catalogue: dict) -> list[str]:
    """``[format].decimal`` is a decimal mark that is not the thousands separator."""
    decimal = catalogue.get("format.decimal")
    if decimal not in DECIMALS:
        return [f"[format].decimal is {decimal!r}, not one of {DECIMALS}"]
    if decimal == catalogue.get("format.group"):
        return [f"[format].decimal is the same as [format].group ({decimal!r})"]
    return []


# --- Every function of text.py answers ---------------------------------------------

A = "0-65-93-24-3-1-2-24"


def _document(pages, tag, name="doc.tar"):
    from optar_gui.document import Document, PageOutcome, ScanInfo

    doc = Document()
    for number, item in enumerate(pages, 1):
        if item is None:
            continue
        scan_id = doc.add_scan(f"/scans/{number}.png")
        doc.set_identified(scan_id, ScanInfo(A, len(pages), number, name, tag))
        data, lost = item
        doc.set_outcome(scan_id, PageOutcome(data, (1000, 0, 0, 0), lost))
    return doc


def _unwrapped(**kw):
    from optar.container import Unwrapped

    fields = dict(
        data=b"file", best_effort=b"file", name="doc.bin", verified=True,
        repaired_bytes=1234, worst_used=18, budget=32, failed=0, page_damage={}, missing=(),
    )
    fields.update(kw)
    return Unwrapped(**fields)


def _object_examples() -> dict[str, list]:
    """Representative inputs, by the annotation of the parameter that takes them."""
    from optar.errors import Grouped, OptarError, error
    from optar.format import LAYOUTS
    from optar.tag import make_tag
    from optar_gui.document import (
        DocState,
        Document,
        GroupView,
        Health,
        PageView,
        Progress,
        ScanInfo,
        ScanView,
        Summary,
    )

    data = bytes(range(256)) * 19
    padded = data.ljust(5 * 1000, b"\0")
    five = [(padded[i * 1000:(i + 1) * 1000], 0) for i in range(5)]
    tag = make_tag(data)
    pages = [
        PageView(3, health, 1, (), repaired, lost, histogram, reason, slow, 900, 12)
        for health in (
            Health.GOOD, Health.REPAIRED, Health.DAMAGED, Health.UNREADABLE,
            Health.MISSING, Health.WAITING, Health.WORKING,
        )
        for repaired, lost, histogram, reason, slow in (
            (0, 0, None, "", False),
            (198, 0, (1000, 3, 2, 1), "", False),
            (9, 37, (1000, 3, 2, 1), "label unreadable", True),
            (1234, 1, None, "no page found", False),
        )
    ]
    info = ScanInfo(A, 3, 1, "doc.tar", None)
    scans = [
        ScanView(4, "/x/new.png", state, i, None, reason)
        for state in ("waiting", "working", "done", "unreadable")
        for i in (None, info)
        for reason in ("", "label unreadable", "no page found")
    ]
    summaries = [
        Summary(state, 2, 1, 1, 1, 3, size, protection, missing, repair, "", slow, 2, 4)
        for state in (
            DocState.EMPTY, DocState.WORKING, DocState.INCOMPLETE, DocState.UNVERIFIABLE,
            DocState.VERIFIED, DocState.MISMATCH, DocState.CHECKING, DocState.RECOVERABLE,
        )
        for size, protection, missing, repair, slow in (
            (None, 0, (), None, 0),
            (4864, 32, (2, 4, 5), _unwrapped(), 1),
            (2481152, 32, (1,), _unwrapped(verified=False, failed=2, data=None), 0),
        )
        # Only a document that has not been read as far as its size has none.
        if size is not None or state in (DocState.EMPTY, DocState.WORKING, DocState.INCOMPLETE)
    ]
    steps = ["find", "identify", "slow-sample", "slow-fit", "open", "read", "other"]
    return {
        "PageView": pages,
        "ScanView": scans,
        "Summary": summaries,
        "GroupView": [
            GroupView(1, "doc.tar", 5, A, None, (1, 2)),
            GroupView(2, "", 1, A, tag, (3,)),
        ],
        "Document": [
            Document(),
            _document(five, tag),
            _document([five[0], None, five[2], (b"x" * 1000, 3), None], tag),
            _document([five[0], five[1]], None),
        ],
        "Progress|None": [None] + [Progress(s, 2, 5, 0.5) for s in steps],
        "Unwrapped": [
            _unwrapped(),
            _unwrapped(verified=False, failed=3, data=None, worst_used=40),
            _unwrapped(missing=(2, 3, 7), page_damage={1: 5, 4: 1}, repaired_bytes=1),
            _unwrapped(budget=0, worst_used=0, repaired_bytes=0),
        ],
        "Layout|None": [None, LAYOUTS[("a4", "standard")]],
        "Summary|None": [None, summaries[3]],
        "BaseException": [
            ValueError("boom {braces}"),
            error(OptarError, "err.cannot_read", "cannot read {path}: {reason}",
                  path="/x/{y}.png", reason="No such file or directory"),  # fmt: skip
            error(OptarError, "err.image_too_large", "cannot read image {path}: {pixels} "
                  "pixels is more than the {limit} a scan may have", path="/x/a.png",
                  pixels=Grouped(123_456_789), limit=Grouped(100_000_000)),  # fmt: skip
        ],
    }


def _scalar_examples() -> dict[str, list]:
    from optar.format import DOT_SIZES, LAYOUTS, PAPERS
    from optar_gui.document import Fit

    layouts = list(LAYOUTS.values())[:3]
    formats = [A, *(layout.fmt.to_string() for layout in layouts), "not a format"]
    return {
        "format": formats,
        "fit": [v for k, v in vars(Fit).items() if k.isupper()],
        "reason": [
            "no page found", "label unreadable", "page number out of range",
            "too many pages", "too large to protect", "something else",
        ],
        "dots": [*DOT_SIZES, "odd"],
        "smaller_dots": [None, *DOT_SIZES],
        "protect": ["none", "standard", "high", "odd"],
        "paper": [*PAPERS, "odd"],
        "noun": ["page", "byte", "block", "dot", "scan"],
        "scan_name": [None, "scan.png"],
        "name": ["doc.tar", "ok", "save", "<b>x</b> {y}"],
        "dropped": ["", "о т"],
        "message": ["boom", "{braces} <b>"],
        "path": ["/x/out.pdf"],
        "line": ["3 of 5 pages good"],
        "note": ["", "a note"],
        "budget": [32],
        "used": [0, 18, 32, 40],
        "pixels": [100_000_000],
        "limit": [20_000_000, 1000],
        "page": [1, 2, 7],
        "other_page": [None, 4],
        "total": [1, 5, 1200],
        "pages": [1, 5],
        "size": [0, 1, 4864, 2481152],
        "promised": [0, 2],
        "reading": [1, 3],
        "batch": [3],
        "scan_dpi": [300, 600],
        "n": [0, 1, 2, 5, 11, 21, 1234],
        "count": [0, 1, 2, 5, 11, 21, 1234],
        "repaired_bytes": [None, 0, 1234],
    }


def _values_for(name: str, annotation: str, objects: dict, scalars: dict) -> list:
    key = annotation.replace(" ", "")
    if key in objects:
        return objects[key]
    if key == "bool":
        return [False, True]
    if key == "float":
        return [150.0, 290.0]
    if name in scalars:
        return scalars[name]
    if key in ("str", "str|None"):
        return ["text"]
    if key in ("int", "int|None"):
        return [1, 5]
    raise LookupError(
        f"no example for parameter {name!r} of type {annotation}: add one to "
        "_object_examples or _scalar_examples in tests/unit/test_catalogues.py"
    )


def _answer_problem(where: str, annotation: str, result) -> str | None:
    items = result if isinstance(result, tuple) else (result,)
    if annotation.replace(" ", "") == "bool":
        return None if isinstance(result, bool) else f"{where}: not a bool"
    if result is None and "None" in annotation:
        return None
    # A detail may hold an empty line between its lines, but never be empty itself.
    if isinstance(result, tuple):
        ok = all(isinstance(item, str) for item in items) and any(i.strip() for i in items)
    else:
        ok = isinstance(result, str) and bool(result.strip())
    if ok:
        return None
    return f"{where}: answered {result!r}"


COMBINATION_LIMIT = 20_000


def text_function_problems(code: str, limit: int = COMBINATION_LIMIT) -> list[str]:
    """Call every public function of text.py in language ``code`` with examples."""
    from optar_gui import text

    objects, scalars = _object_examples(), _scalar_examples()
    problems = []
    previous = i18n.language()
    i18n.set_language(code)
    try:
        for fname, func in sorted(inspect.getmembers(text, inspect.isfunction)):
            if fname.startswith("_") or func.__module__ != text.__name__:
                continue
            params = list(inspect.signature(func).parameters.values())
            try:
                pools = [_values_for(p.name, str(p.annotation), objects, scalars) for p in params]
            except LookupError as e:
                problems.append(f"{fname}: {e}")
                continue
            returns = str(inspect.signature(func).return_annotation)
            combinations = 1
            for pool in pools:
                combinations *= len(pool)
            if combinations > limit:
                problems.append(
                    f"{fname}: {combinations} input combinations exceed the limit {limit}; "
                    "shorten its example lists so nothing is silently skipped"
                )
                continue
            for combo in itertools.islice(itertools.product(*pools), limit):
                where = f"{fname}{tuple(map(repr, combo))}"[:200]
                given = list(zip(params, combo, strict=True))
                args = [v for p, v in given if p.kind != p.KEYWORD_ONLY]
                kwargs = {p.name: v for p, v in given if p.kind == p.KEYWORD_ONLY}
                try:
                    result = func(*args, **kwargs)
                except Exception as e:  # noqa: BLE001 - any failure is a finding
                    problems.append(f"{where}: raised {type(e).__name__}: {e}")
                    break
                problem = _answer_problem(where, returns, result)
                if problem:
                    problems.append(problem)
                    break
    finally:
        i18n.set_language(previous)
    return problems


# --- The per-language tests (each translated language) -------------------------------


@pytest.fixture
def english():
    return i18n.catalogue("en")


@pytest.mark.parametrize("code", LANGUAGES)
def test_the_language_has_a_catalogue(code):
    assert code in i18n.languages(), f"{code} has pages but no src/optar/locale/{code}.toml"


@pytest.mark.parametrize("code", LANGUAGES)
def test_same_keys_as_english(code, english):
    assert not key_problems(english, i18n.catalogue(code))


@pytest.mark.parametrize("code", LANGUAGES)
def test_same_placeholders_as_english(code, english):
    assert not placeholder_problems(english, i18n.catalogue(code))


@pytest.mark.parametrize("code", LANGUAGES)
def test_plural_entries_have_exactly_the_language_categories(code):
    assert not category_problems(code, i18n.catalogue(code))


@pytest.mark.parametrize("code", LANGUAGES)
def test_no_empty_strings_and_no_stray_braces(code):
    assert not value_problems(i18n.catalogue(code))


@pytest.mark.parametrize("code", LANGUAGES)
def test_language_name_and_group_separator(code):
    assert not name_and_separator_problems(i18n.catalogue(code), code)


@pytest.mark.parametrize("code", LANGUAGES)
def test_decimal_separator(code):
    assert not decimal_problems(i18n.catalogue(code))


@pytest.mark.parametrize("code", LANGUAGES)
def test_every_text_function_answers(code):
    assert not text_function_problems(code)


def test_all_nine_languages_are_present():
    assert tuple(i18n.languages()) == i18n.ORDER


# --- English is itself a valid catalogue, and the checks bite -----------------------


def test_english_passes_every_catalogue_check(english):
    assert not key_problems(english, english)
    assert not placeholder_problems(english, english)
    assert not category_problems("en", english)
    assert not value_problems(english)
    assert not name_and_separator_problems(english)
    assert not decimal_problems(english)


def test_every_text_function_answers_in_english():
    assert not text_function_problems("en")


PLURAL = {"one": "{n} page", "other": "{n} pages"}
EN = {"a.b": "Hello {name}", "count.page": PLURAL, "language.name": "English", "format.group": ","}


def test_a_missing_and_an_extra_key_are_reported():
    problems = key_problems(EN, {"a.b": "x {name}", "z": "y"})
    assert any("missing" in p and "count.page" in p for p in problems)
    assert any("extra" in p and "'z'" in p for p in problems)


def test_a_changed_placeholder_is_reported():
    other = dict(EN, **{"a.b": "Salut {nom}"})
    assert any("a.b" in p for p in placeholder_problems(EN, other))
    assert any("a.b" in p for p in placeholder_problems(EN, dict(EN, **{"a.b": "Salut"})))
    assert any("a.b" in p for p in placeholder_problems(EN, dict(EN, **{"a.b": "{name} {x}"})))


def test_plural_placeholders_follow_the_english_forms():
    ok = dict(EN, **{"count.page": {"one": "{n} a", "few": "{n} b", "many": "{n} c"}})
    assert not placeholder_problems(EN, ok)
    no_n = dict(EN, **{"count.page": {"one": "stránka", "other": "{n} x"}})
    assert any("count.page.one" in p for p in placeholder_problems(EN, no_n))
    extra = dict(EN, **{"count.page": {"one": "{n} {k}", "other": "{n}"}})
    assert any("unknown placeholders" in p for p in placeholder_problems(EN, extra))
    flat = dict(EN, **{"count.page": "{n} pages"})
    assert any("count.page" in p for p in placeholder_problems(EN, flat))


def test_a_wrong_plural_category_is_reported():
    assert not category_problems("ru", {"p": {"one": "a", "few": "b", "many": "c"}})
    assert category_problems("ru", {"p": {"one": "a", "other": "c"}})
    assert category_problems("tr", {"p": {"one": "a", "other": "c"}})
    assert not category_problems("tr", {"p": {"other": "c"}})
    assert category_problems("it", {"p": {"one": "a"}})


def test_empty_values_and_braces_are_reported():
    assert value_problems({"a": "  "})
    assert value_problems({"a": ""})
    assert value_problems({"a": "open { brace"})
    assert value_problems({"a": "close } brace"})
    assert value_problems({"a": "literal {{ brace"})
    assert value_problems({"a": "{0} positional"})
    assert value_problems({"a": {"one": "{n}", "other": ""}})
    assert not value_problems({"a": "fine {name}", "b": {"one": "{n} x", "other": "{n} y"}})
    assert not value_problems({"format.group": " "})  # a space is a separator
    assert value_problems({"format.group": ""}) and value_problems({"other": " "})
    # Only one separator character may be blank: two spaces or a tab are not one.
    assert value_problems({"format.group": "  "})
    assert value_problems({"format.group": "\t"})


def test_language_name_and_separator_are_checked():
    assert not name_and_separator_problems({"language.name": "Русский", "format.group": " "})
    assert not name_and_separator_problems({"language.name": "Italiano", "format.group": "."})
    assert name_and_separator_problems({"language.name": "", "format.group": ","})
    assert name_and_separator_problems({"format.group": ","})
    assert name_and_separator_problems({"language.name": "X", "format.group": ";"})
    assert name_and_separator_problems({"language.name": "X", "format.group": "  "})
    assert name_and_separator_problems({"language.name": "X", "format.group": "\t"})
    assert name_and_separator_problems({"language.name": "X"})
    assert name_and_separator_problems({})


def test_the_decimal_separator_is_checked():
    assert not decimal_problems({"format.group": ".", "format.decimal": ","})
    assert not decimal_problems({"format.group": "\u00a0", "format.decimal": ","})
    assert decimal_problems({"format.group": ","})
    assert decimal_problems({"format.group": ",", "format.decimal": ","})
    assert decimal_problems({"format.group": ".", "format.decimal": ";"})


def test_each_language_must_use_its_own_group_separator():
    nbsp = {"language.name": "X", "format.group": "\u00a0"}
    dot = {"language.name": "X", "format.group": "."}
    for code in ("ru", "uk", "be", "pl", "ka"):
        assert not name_and_separator_problems(nbsp, code)
        assert name_and_separator_problems(dot, code)
    for code in ("it", "es", "tr"):
        assert not name_and_separator_problems(dot, code)
        assert name_and_separator_problems(nbsp, code)
        assert name_and_separator_problems({"language.name": "X", "format.group": ","}, code)


def test_a_function_with_too_many_combinations_is_reported():
    problems = text_function_problems("en", limit=3)
    assert any("exceed the limit 3" in p for p in problems)


def test_a_text_function_failing_in_a_language_is_reported(catalogues, monkeypatch):
    from optar_gui import text

    catalogues.add("it", {"language": {"name": "Italiano"}, "format": {"group": "."}})
    assert not text_function_problems("it")  # keys it lacks fall back to English

    def broken(page: "PageView"):  # noqa: F821 - only the annotation text is read
        raise KeyError("x")

    monkeypatch.setattr(text, "health_label", broken)
    monkeypatch.setattr(broken, "__module__", text.__name__)
    assert any("health_label" in p and "raised" in p for p in text_function_problems("it"))
    assert i18n.language() == "en"
