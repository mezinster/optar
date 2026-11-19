# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Message catalogues and plural rules.

A catalogue is a TOML file under ``optar/locale``, one per language. Keys are
flat dotted names; a table whose keys are all plural categories is one plural
message. English is the fallback for every key a language lacks.
"""

import tomllib
from collections.abc import Iterable
from importlib import resources

from .errors import Alternatives, Grouped

ORDER: tuple[str, ...] = ("en", "ru", "uk", "be", "pl", "ka", "tr", "it", "es")

_CATEGORIES = {
    "en": ("one", "other"),
    "it": ("one", "other"),
    "es": ("one", "other"),
    "ru": ("one", "few", "many"),
    "uk": ("one", "few", "many"),
    "be": ("one", "few", "many"),
    "pl": ("one", "few", "many"),
    "tr": ("other",),
    "ka": ("other",),
}
_ALL_CATEGORIES = frozenset(("zero", "one", "two", "few", "many", "other"))
_SEPARATORS = "_-.@"

_current = "en"
_cache: dict[str, dict | None] = {}


def _read(code: str) -> dict | None:
    """The nested catalogue of a language, or None when it has no file."""
    try:
        path = resources.files("optar") / "locale" / f"{code}.toml"
        with path.open("rb") as f:
            return tomllib.load(f)
    except (FileNotFoundError, NotADirectoryError):
        return None


def _flatten(data: dict, prefix: str = "") -> dict:
    flat: dict = {}
    for key, value in data.items():
        name = prefix + key
        if not isinstance(value, dict):
            flat[name] = value
        elif value and set(value) <= _ALL_CATEGORIES:
            flat[name] = dict(value)
        else:
            flat.update(_flatten(value, name + "."))
    return flat


def _load(code: str) -> dict | None:
    if code not in _cache:
        data = _read(code) if code in ORDER else None
        _cache[code] = None if data is None else _flatten(data)
    return _cache[code]


def catalogue(code: str) -> dict[str, str | dict[str, str]]:
    """The flat catalogue of a language (a fresh copy); empty when absent."""
    flat = _load(code) or {}
    return {k: dict(v) if isinstance(v, dict) else v for k, v in flat.items()}


def languages() -> dict[str, str]:
    """Language code to its own name, for each catalogue present, in ORDER."""
    found = {}
    for code in ORDER:
        flat = _load(code)
        if flat is not None:
            found[code] = flat.get("language.name", code)
    return found


def set_language(code: str | None) -> str:
    """Select the language; unknown or None gives English. Returns it."""
    global _current
    _current = code if code is not None and _load(code) is not None else "en"
    return _current


def language() -> str:
    return _current


def categories(code: str) -> tuple[str, ...]:
    return _CATEGORIES.get(code, _CATEGORIES["en"])


def plural_category(code: str, count: int) -> str:
    c = abs(count)
    if code in ("ru", "uk", "be"):
        if c % 10 == 1 and c % 100 != 11:
            return "one"
        if 2 <= c % 10 <= 4 and not 12 <= c % 100 <= 14:
            return "few"
        return "many"
    if code == "pl":
        if c == 1:
            return "one"
        if 2 <= c % 10 <= 4 and not 12 <= c % 100 <= 14:
            return "few"
        return "many"
    if code in ("tr", "ka"):
        return "other"
    return "one" if c == 1 else "other"


def _lookup(key: str):
    for code in (_current, "en"):
        flat = _load(code)
        if flat is not None and key in flat:
            return flat[key], code
    raise KeyError(key)


def _fill(template: str, key: str, code: str, values: dict) -> str:
    try:
        return template.format(**values)
    except (KeyError, IndexError) as e:
        name = e.args[0] if isinstance(e, KeyError) else "(positional)"
        raise KeyError(
            f"catalogue key {key!r} in language {code!r} names the placeholder "
            f"{name!r}, which was not supplied") from None


def t(key: str, /, **values: object) -> str:
    entry, code = _lookup(key)
    if isinstance(entry, dict):
        raise KeyError(key)
    return _fill(entry, key, code, values)


def _format_entry(name: str, default: str) -> str:
    """The ``[format]`` entry ``name`` of the current language, else English's."""
    for code in (_current, "en"):
        flat = _load(code)
        if flat is not None and f"format.{name}" in flat:
            return flat[f"format.{name}"]
    return default


def number(value: int) -> str:
    return f"{value:,}".replace(",", _format_entry("group", ","))


def decimal(value: float, places: int) -> str:
    """``value`` with ``places`` decimals, in the language's decimal separator
    (and its thousands separator, as ``number``)."""
    marks = {ord(","): _format_entry("group", ","), ord("."): _format_entry("decimal", ".")}
    return f"{value:,.{places}f}".translate(marks)


def error_text(e: BaseException) -> str:
    """A library error's message in the current language: the catalogue's entry
    for its key (``optar.errors``) filled with its values, else ``str(e)``."""
    key = getattr(e, "key", None)
    if key is None:
        return str(e)
    try:
        entry, code = _lookup(key)
    except KeyError:
        return str(e)
    if isinstance(entry, dict):
        return str(e)
    given = getattr(e, "values", {})
    return _fill(entry, key, code, {k: _worded(v) for k, v in given.items()})


def _worded(value: object) -> object:
    """An error's value as the current language shows it."""
    if isinstance(value, Grouped):
        return number(value)
    if isinstance(value, Alternatives):
        return alternatives(value)
    return value


def alternatives(names: Iterable[object]) -> str:
    """Names of which one is meant, joined in the current language: the earlier
    ones by ``alternatives.separator``, the last added by ``alternatives.last``."""
    names = [str(name) for name in names]
    if len(names) < 2:
        return "".join(names)
    return t("alternatives.last", items=t("alternatives.separator").join(names[:-1]),
             last=names[-1])


def n(key: str, count: int, /, **values: object) -> str:
    entry, code = _lookup(key)
    if isinstance(entry, dict):
        category = plural_category(code, count)
        entry = entry.get(category) or entry.get("other") or next(iter(entry.values()))
    return _fill(entry, key, code, {"n": number(count), "count": count, **values})


def listing(key: str, count: int, /, **values: object) -> str:
    """An entry about a list of ``count`` pages: its ``single`` form when the list
    names exactly one page, else its ``several`` form. Not a plural rule: in some
    languages the plural form for 1 also serves 21, which a list of 21 pages must
    not take."""
    return t(f"{key}.{'single' if count == 1 else 'several'}", **values)


def pick_language(candidates: Iterable[str | None]) -> str | None:
    """The first candidate (such as ``ru_RU.UTF-8``) that names a language present."""
    present = languages()
    for name in candidates:
        if not name:
            continue
        code = name.lower()
        for i, ch in enumerate(code):
            if ch in _SEPARATORS:
                code = code[:i]
                break
        if code in present:
            return code
    return None


def encodable(code: str, encoding: str) -> bool:
    """Whether every string of the catalogue encodes in ``encoding``."""
    for value in catalogue(code).values():
        for text in value.values() if isinstance(value, dict) else (value,):
            try:
                text.encode(encoding)
            except UnicodeEncodeError:
                return False
    return True
