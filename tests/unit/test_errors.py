# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Library errors carry a message key, so the command line and the window can
show them in the user's language while ``str(e)`` stays English."""

import ast
from pathlib import Path
from string import Formatter

import pytest

from optar import errors, i18n
from optar.errors import DecodeError, FormatError, IdentifyError, OptarError

SRC = Path(__file__).resolve().parents[2] / "src" / "optar"
CLASSES = {"OptarError", "FormatError", "DecodeError", "IdentifyError"}

# Raise sites that give no key: each a programming error that no file, scan or
# option a person gives can reach ("file:function", the function's qualified name).
INTERNAL = {
    # The image is always read_scan's 2-D uint8 grey image.
    "identify.py:_check",
    # Only identify_coarse reads softly, with a layout's format (data words of at
    # most 8 bits, data on every page) and read_scan's image.
    "decoder/soft.py:_Reader.__init__",
}


def _sources():
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC).as_posix()
        if rel not in ("cli.py", "errors.py"):
            yield rel, ast.parse(path.read_text(encoding="utf-8"))


def _is_error_call(node) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "error"
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "error"
        and isinstance(func.value, ast.Name)
        and func.value.id == "errors"
    )


def _error_calls():
    for rel, tree in _sources():
        for node in ast.walk(tree):
            if _is_error_call(node):
                yield rel, node


def _walk_functions(node, prefix=""):
    """(qualified name of the enclosing function, raise node) for every raise."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield from _walk_functions(child, f"{prefix}{child.name}.")
        elif isinstance(child, ast.Raise):
            yield prefix.rstrip("."), child
            yield from _walk_functions(child, prefix)
        else:
            yield from _walk_functions(child, prefix)


def test_every_error_call_matches_the_english_catalogue():
    english = i18n.catalogue("en")
    calls = list(_error_calls())
    assert len(calls) > 30  # the scan finds the call sites
    problems = []
    for rel, node in calls:
        where = f"{rel}:{node.lineno}"
        key, text = node.args[1], node.args[2]
        if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
            problems.append(f"{where}: the key is not a literal")
            continue
        if not (isinstance(text, ast.Constant) and isinstance(text.value, str)):
            problems.append(f"{where}: the English text is not a literal")
            continue
        if not key.value.startswith("err."):
            problems.append(f"{where}: {key.value} is not under err.")
        if english.get(key.value) != text.value:
            problems.append(f"{where}: catalogue {key.value} is {english.get(key.value)!r}")
        fields = {f for _, f, _, _ in Formatter().parse(text.value) if f is not None}
        given = {k.arg for k in node.keywords}
        if fields != given:
            problems.append(f"{where}: placeholders {sorted(fields)}, values {sorted(given)}")
    assert not problems, problems


def test_every_err_key_is_used():
    used = {node.args[1].value for _, node in _error_calls()}
    english = {k for k in i18n.catalogue("en") if k.startswith("err.")}
    assert english == used


def test_no_reachable_raise_is_left_without_a_key():
    found, internal_seen = [], set()
    for rel, tree in _sources():
        for function, node in _walk_functions(tree):
            exc = node.exc
            if not (isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name)):
                continue
            if exc.func.id not in CLASSES:
                continue
            site = f"{rel}:{function}"
            if site in INTERNAL:
                internal_seen.add(site)
            else:
                found.append(f"{site} (line {node.lineno})")
    assert not found, found
    assert internal_seen == INTERNAL  # no stale entries


def test_identify_reasons_are_the_catalogue_entries():
    from optar import identify

    english = i18n.catalogue("en")
    assert english["err.no_page"] == identify.NO_PAGE
    assert english["err.label_unreadable"] == identify.LABEL_UNREADABLE


def test_error_text_translates_and_keeps_values(catalogues):
    e = errors.error(FormatError, "err.demo", "page {page} of {total}", page=3, total=2)
    assert str(e) == "page 3 of 2" and e.key == "err.demo" and e.values == {"page": 3, "total": 2}
    assert isinstance(e, FormatError)
    catalogues.add("en", {"err": {"demo": "page {page} of {total}"}})
    catalogues.add("ru", {"language": {"name": "Русский"},
                          "err": {"demo": "страница {page} из {total}"}})  # fmt: skip
    i18n.set_language("ru")
    assert i18n.error_text(e) == "страница 3 из 2"
    assert str(e) == "page 3 of 2"


def test_error_text_falls_back_to_english_and_to_the_text(catalogues):
    catalogues.add("ru", {"language": {"name": "Русский"}})
    i18n.set_language("ru")
    e = errors.error(OptarError, "err.too_many_pages", "too many pages: {total} needed, "
                     "at most {limit}", total=70000, limit=65535)  # fmt: skip
    assert i18n.error_text(e) == str(e) == "too many pages: 70000 needed, at most 65535"
    unknown = errors.error(OptarError, "err.no_such_key", "x {y}", y="{z}")
    assert i18n.error_text(unknown) == "x {z}"


def test_error_text_of_a_plain_exception_is_its_text():
    assert i18n.error_text(ValueError("x {y}")) == "x {y}"
    assert i18n.error_text(OptarError("plain")) == "plain"
    assert OptarError("plain").key is None and OptarError("plain").values == {}


def test_a_broken_translation_names_its_key(catalogues):
    catalogues.add("ru", {"language": {"name": "Русский"}, "err": {"no_page": "{oops}"}})
    i18n.set_language("ru")
    e = errors.error(IdentifyError, "err.no_page", "no page found")
    with pytest.raises(KeyError, match="err.no_page"):
        i18n.error_text(e)


def test_identify_error_keeps_its_fields():
    e = errors.error(IdentifyError, "err.label_unreadable", "label unreadable")
    assert e.reason == "label unreadable" and e.scan_dpi is None and not e.slow_tried
    assert e.key == "err.label_unreadable"


def test_counts_are_grouped_in_the_language(catalogues):
    e = errors.error(OptarError, "err.demo", "{pixels} pixels",
                     pixels=errors.Grouped(123456789))  # fmt: skip
    assert str(e) == "123,456,789 pixels"
    catalogues.add("en", {"err": {"demo": "{pixels} pixels"}})
    catalogues.add("ru", {"language": {"name": "Русский"}, "format": {"group": " "},
                          "err": {"demo": "{pixels} пикселей"}})  # fmt: skip
    i18n.set_language("ru")
    assert i18n.error_text(e) == "123 456 789 пикселей"


def test_io_error_keys(tmp_path):
    from optar.fileio import io_error

    missing = tmp_path / "missing"
    try:
        open(missing, "rb")
    except OSError as os_error:
        read, write = io_error("read", missing, os_error), io_error("write", missing, os_error)
    assert str(read) == f"cannot read {missing}: No such file or directory"
    assert read.key == "err.cannot_read" and write.key == "err.cannot_write"
    assert str(write) == f"cannot write {missing}: No such file or directory"


def test_a_key_survives_the_rotations_of_an_unlabelled_decode():
    import numpy as np

    from optar.format import PageFormat
    from optar.identify import decode_unlabelled

    image = np.full((50, 40), 255, dtype=np.uint8)
    with pytest.raises(DecodeError) as caught:
        decode_unlabelled(image, PageFormat.parse("0-65-93-24-3-1-2-24"))
    assert caught.value.key is not None and i18n.error_text(caught.value) == str(caught.value)


RU_READ = {"language": {"name": "Русский"},
           "err": {"cannot_read": "не удаётся прочитать {path}: {reason}",
                   "not_an_image": "не удаётся прочитать изображение {path}: это не {formats}"}}


def test_cli_prints_the_translated_error(tmp_path, capsys, monkeypatch, catalogues):
    from optar.cli import main

    catalogues.add("ru", RU_READ)
    monkeypatch.setenv("OPTAR_LANG", "ru")
    missing = tmp_path / "missing.bin"
    assert main(["encode", str(missing)]) == 2
    err = capsys.readouterr().err
    assert f"не удаётся прочитать {missing}: " in err


def test_cli_translates_errors_from_scans(tmp_path, capsys, monkeypatch, catalogues):
    from optar.cli import main

    catalogues.add("ru", RU_READ)
    monkeypatch.setenv("OPTAR_LANG", "ru")
    base = tmp_path / "scan"
    (tmp_path / "scan_0001.png").write_bytes(b"not an image")
    assert main(["decode", str(base)]) == 2
    err = capsys.readouterr().err
    assert f"не удаётся прочитать изображение {base}_0001.png: это не " in err


def test_cli_probe_translates_the_reason(tmp_path, catalogues):
    from optar import cli

    catalogues.add("ru", RU_READ)
    i18n.set_language("ru")
    path = tmp_path / "x.png"
    path.write_bytes(b"not an image")
    assert f"не удаётся прочитать изображение {path}: это не " in cli._probe(str(path))


def test_the_window_shows_the_translated_reason(tmp_path, catalogues):
    from optar_gui import work

    catalogues.add("ru", RU_READ)
    i18n.set_language("ru")
    path = tmp_path / "x.png"
    path.write_bytes(b"not an image")
    assert work.process_scan(str(path)).reason.startswith(
        f"не удаётся прочитать изображение {path}: это не ")


@pytest.fixture(autouse=True)
def english_after():
    yield
    i18n.set_language("en")


def test_an_error_without_values_shares_no_mutable_dict():
    plain = OptarError("plain")
    assert dict(plain.values) == {}
    with pytest.raises(TypeError):
        plain.values["x"] = 1
    assert OptarError("other").values == {}
