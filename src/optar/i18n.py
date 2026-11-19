# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Message catalogues and plural rules.

A catalogue is a TOML file under ``optar/locale``, one per language. Keys are
flat dotted names; a table whose keys are all plural categories is one plural
message. English is the fallback for every key a language lacks.
"""

import tomllib
from collections.abc import Iterable
from importlib import resources

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


def number(value: int) -> str:
    group = ","
    for code in (_current, "en"):
        flat = _load(code)
        if flat is not None and "format.group" in flat:
            group = flat["format.group"]
            break
    return f"{value:,}".replace(",", group)


def n(key: str, count: int, /, **values: object) -> str:
    entry, code = _lookup(key)
    if isinstance(entry, dict):
        category = plural_category(code, count)
        entry = entry.get(category) or entry.get("other") or next(iter(entry.values()))
    return _fill(entry, key, code, {"n": number(count), "count": count, **values})


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
