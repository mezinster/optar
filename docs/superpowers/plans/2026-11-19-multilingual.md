# optar in Nine Languages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The window, the command line's messages and every documentation page are available in English, Russian, Ukrainian, Belarusian, Polish, Georgian, Turkish, Italian and Spanish.

**Architecture:** One TOML catalogue per language under `src/optar/locale/`, read by a small `optar.i18n` module with a plural rule per language. `text.py` and `cli.py` keep their names and logic and look wording up in the current language; English is one catalogue among nine and its output does not change. The site uses `mkdocs-static-i18n` with translated pages beside the English ones (`install.ru.md`).

**Tech Stack:** Python 3.12 standard library (`tomllib`, `importlib.resources`), PySide6 (`QSettings`, `QLocale`) in the window only, MkDocs Material with `mkdocs-static-i18n`, Opus agents for translation.

**Spec:** `docs/superpowers/specs/2026-11-19-multilingual-design.md`. Read it with `CLAUDE.md` before any task.

## Global Constraints

- Languages and codes: `en`, `ru`, `uk`, `be`, `pl`, `ka`, `tr`, `it`, `es`.
- Command names, option names, metavariables, file names and exit codes stay English.
- Nothing printed on paper changes; `tests/vectors` and the meaning of `docs/format.md` are untouched.
- English output of every existing function and command is byte-for-byte what it is today. Existing tests that pin English wording are not edited to pass.
- Runtime dependencies stay numpy and Pillow.
- `text.py`, `document.py`, `work.py` import no Qt. Nothing under `src/optar` imports Qt or `optar_gui`.
- Of the library, only `cli.py` imports `optar.i18n`. `i18n.py` never prints, exits or reads the environment.
- `text.py` imports `optar.i18n` lazily (inside functions): importing `text.py` must not load numpy.
- The text of a library exception (`str(e)`) stays English and unchanged.
- Untrusted text (label text, file names) is shown as plain text and may contain any character, braces included.
- Tests write only under `tmp_path`. No test may read or write the user's real settings.
- Commit subjects: capitalised, third-person present, no prefix ("Adds the catalogue module").
- Work on a new branch `multilingual` made from `docs-site`. Pull requests go to the fork only (`gh pr create --repo mezinster/optar`).
- Tasks marked **parallel** touch disjoint files and are run concurrently (the owner's standing preference).

## Review Focus

1. **Odd system locales** (`C`, `POSIX`, empty, `ru_RU.UTF-8`, `pl-PL`, `be@latin`, `zh_CN`, `None`): the program starts in the matching supported language or in English, never crashes. Test in Task 1 (`pick_language`).
2. **Braces in untrusted values** (a scan named `{0}.png`, a label `{name}`): shown literally, no formatting error. Tests in Task 1 (`t`) and Task 2 (`text.unreadable_row`, `text.saved_message`).
3. **A console that cannot show the language** (stderr in `cp1252` with Georgian chosen): the command line prints English, no `UnicodeEncodeError`. Test in Task 3.
4. **A bad saved choice** (settings hold `xx`, a number, or an empty string): the window starts in the system's language. Test in Task 5.
5. **Plural edge counts** (0, 1, 2, 5, 11, 12, 14, 21, 22, 25, 101, 111, 112, 1,000,000, and a negative number): every language returns a category its catalogue has. Test in Task 1.

---

## File map

| File | Responsibility |
|---|---|
| `src/optar/i18n.py` (new) | Languages, current language, lookups, plural rules, number grouping, locale matching, translating a library error |
| `src/optar/locale/<code>.toml` (new, nine) | One language's wording |
| `src/optar/errors.py` | Exceptions carry a message key and values beside the English text |
| `src/optar/cli.py` | Chooses the language from the environment; all wording from the catalogue |
| `src/optar_gui/text.py` | The window's only door to the catalogue |
| `src/optar_gui/language.py` (new, Qt) | Saved choice, system language, the choice at start |
| `src/optar_gui/main_window.py`, `dialogs.py`, `__main__.py` | Language menu, button labels, start-up |
| `tests/unit/test_i18n.py`, `test_catalogues.py`, `test_doc_translations.py` (new) | Mechanics, completeness, docs in step |
| `tools/translation_status.py` (new) | Lists stale translated pages |
| `docs/<page>.<code>.md` (new, 88) | Translated pages |
| `docs/superpowers/glossaries/<code>.md`, `docs/superpowers/translation-brief.md` (new) | Terms per language; the rules every translating agent follows |

Catalogue layout (the same tables in every language):

```toml
[language]
name = "English"          # the language's own name, in its own script

[format]
group = ","               # thousands separator

[count.page]              # one table per counted noun; {n} is the grouped number
one = "{n} page"
other = "{n} pages"

[gui]                     # keys are the names text.py already uses
READ_TAB = "Read from paper"

[cli]
[err]
```

A key is written dotted (`gui.READ_TAB`, `count.page`, `err.cannot_read`). A value that is a table of `one`/`few`/`many`/`other` is a plural entry.

---

### Task 1: The catalogue module

**Files:**
- Create: `src/optar/i18n.py`, `src/optar/locale/en.toml` (only `[language]`, `[format]` and the five `count.*` nouns for now), `tests/unit/test_i18n.py`

**Interfaces:**
- Produces:
  - `ORDER: tuple[str, ...] = ("en", "ru", "uk", "be", "pl", "ka", "tr", "it", "es")`
  - `languages() -> dict[str, str]`: code to own name, for every code in `ORDER` whose catalogue file exists, in `ORDER`.
  - `set_language(code: str | None) -> str`: sets and returns the language in effect (`"en"` for unknown or `None`).
  - `language() -> str`
  - `t(key: str, /, **values: object) -> str`
  - `n(key: str, count: int, /, **values: object) -> str`: picks the category for `count`, formats with `n=number(count)`, `count=count` and `values`.
  - `number(value: int) -> str`
  - `plural_category(code: str, count: int) -> str`
  - `categories(code: str) -> tuple[str, ...]`
  - `pick_language(candidates: Iterable[str | None]) -> str | None`
  - `catalogue(code: str) -> dict[str, str | dict[str, str]]`: flat dotted keys; a fresh copy.
  - `encodable(code: str, encoding: str) -> bool`: whether every string of that catalogue encodes in `encoding`.
  - A key missing in the current language is taken from English; missing in English raises `KeyError`.

- [ ] **Step 1: Write the failing tests** in `tests/unit/test_i18n.py`. Each test restores English afterwards (a fixture that calls `i18n.set_language("en")` on teardown). Catalogues for the tests that need a second language are written to `tmp_path` and reached by monkeypatching the module's one private loader function, `_read(code) -> dict | None`.

```python
RU_LIKE = {0: "many", 1: "one", 2: "few", 5: "many", 11: "many", 12: "many", 14: "many",
           21: "one", 22: "few", 25: "many", 101: "one", 111: "many", 112: "many",
           1_000_000: "many", -1: "one"}

@pytest.mark.parametrize("code", ["ru", "uk", "be"])
def test_east_slavic_plurals(code):
    assert {c: i18n.plural_category(code, c) for c in RU_LIKE} == RU_LIKE

def test_polish_plurals():
    got = {c: i18n.plural_category("pl", c) for c in (1, 2, 5, 12, 21, 22, 25, 101, 112)}
    assert got == {1: "one", 2: "few", 5: "many", 12: "many", 21: "many", 22: "few",
                   25: "many", 101: "many", 112: "many"}

@pytest.mark.parametrize("code", ["en", "it", "es"])
def test_two_form_plurals(code):
    assert [i18n.plural_category(code, c) for c in (0, 1, 2, 21)] == ["other", "one", "other", "other"]

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
def test_pick_language(names, want): ...   # with all nine catalogues stubbed present

def test_english_counts():
    assert i18n.n("count.page", 1) == "1 page"
    assert i18n.n("count.page", 1234) == "1,234 pages"
    assert i18n.number(1234567) == "1,234,567"

def test_values_with_braces_are_literal():      # Review Focus 2
    # stub key "x.y" = "Saved {name}"
    assert i18n.t("x.y", name="{0}{name}.png") == "Saved {0}{name}.png"

def test_missing_key_falls_back_to_english(): ...   # ru stub lacks the key -> English string
def test_unknown_key_raises(): ...                  # KeyError
def test_unknown_language_is_english():
    assert i18n.set_language("xx") == "en" and i18n.set_language(None) == "en"
def test_languages_lists_only_present_catalogues_in_order(): ...
def test_encodable():
    assert i18n.encodable("en", "utf-8")
    # stub "ka" with a Georgian string: encodable("ka", "utf-8") and not encodable("ka", "cp1252")
def test_module_reads_no_environment_and_imports_no_qt(): ...  # source scan: no "os.environ", "PySide6", "print("
```

- [ ] **Step 2: Run** `.venv/bin/pytest -q tests/unit/test_i18n.py`. Expected: FAIL, `No module named 'optar.i18n'`.

- [ ] **Step 3: Implement `src/optar/i18n.py` and `en.toml`.** Rules: `ru`/`uk`/`be`: `one` if `n%10==1 and n%100!=11`; `few` if `n%10 in 2..4 and n%100 not in 12..14`; else `many`. `pl`: `one` if `n==1`; `few` as above; else `many`. `en`/`it`/`es`: `one` if `n==1` else `other`. `tr`/`ka`: `other`. Rules use `abs(count)`. `pick_language` lowercases, cuts at the first of `_ - . @`, and returns the first code that `languages()` has. Catalogues load lazily through `importlib.resources.files("optar") / "locale"` and are cached.
- [ ] **Step 4: Run** the same command. Expected: PASS. Then `.venv/bin/pytest -q` and `.venv/bin/ruff check .`: clean.

- [ ] **Step 5: Check the wheel carries the catalogue.** Run `.venv/bin/python -m build --wheel -o /tmp/claude-1000/-home-mezinster-optar/ea31e5d6-e10e-4fc2-97ce-842c1ad41cef/scratchpad/whl 2>/dev/null || .venv/bin/pip wheel --no-deps -w <same dir> .` then `unzip -l <wheel> | grep locale/en.toml`. Expected: one line. If absent, add the include to `[tool.hatch.build.targets.wheel]`.

- [ ] **Step 6: Commit** "Adds the catalogue module and its plural rules".

---

### Task 2: The window's wording through the catalogue (**parallel** with Task 3)

**Files:**
- Modify: `src/optar_gui/text.py`, `src/optar/locale/en.toml` (`[gui]` and `count.*` only)
- Modify (only if needed): any `src/optar_gui/*.py` that reads a `text` constant at import time
- Test: `tests/unit/test_gui_text.py` (additions only)

**Interfaces:**
- Consumes: `i18n.t`, `i18n.n`, `i18n.number` from Task 1.
- Produces: every public name of `text.py` unchanged in name, signature and English result. New: `text.button(name: str) -> str` for `name` in `"ok"`, `"cancel"`, `"save"`, `"yes"`, `"no"` (English: `OK`, `Cancel`, `Save`, `Yes`, `No`); `text.LANGUAGE_MENU` (`"Language"`), `text.SYSTEM_LANGUAGE` (`"System default"`), `text.LANGUAGE_RESTART` (`"The language changes the next time optar starts."`).

- [ ] **Step 1: Record today's English.** Before touching `text.py`, write `tests/unit/test_gui_text.py::test_english_constants_are_unchanged`: a literal dict of every public upper-case string constant of `text.py` (name to value), generated once from the current module and pasted in, asserted against `getattr(text, name)`. Run it: PASS (it pins the present).

- [ ] **Step 2: Write the failing tests.**

```python
def test_text_module_does_not_load_numpy():
    # subprocess: python -c "import sys, optar_gui.text; print('numpy' in sys.modules)" -> False

def test_constants_follow_the_language(monkeypatch):
    # stub a "ru" catalogue with gui.READ_TAB = "Чтение"; set_language("ru")
    assert text.READ_TAB == "Чтение"
    # and English again after set_language("en")

def test_unknown_constant_is_an_attribute_error():
    with pytest.raises(AttributeError): text.NO_SUCH_NAME

def test_untrusted_names_with_braces(tmp_path):          # Review Focus 2
    assert text.saved_message("/x/{0}.bin", 5) == "Saved 5 bytes to {0}.bin"
    assert "{name}.png" in text.assign_prompt("{name}.png")

def test_buttons():
    assert [text.button(b) for b in ("ok", "cancel", "save", "yes", "no")] == ["OK", "Cancel", "Save", "Yes", "No"]

def test_text_source_holds_no_wording():
    # AST scan of text.py: no string literal containing a space outside docstrings,
    # catalogue keys and the " · " / "; " / " — " joiners.
```

- [ ] **Step 3: Run** `.venv/bin/pytest -q tests/unit/test_gui_text.py`. Expected: the new tests FAIL; all old ones PASS.

- [ ] **Step 4: Move the wording.**
  - Constants: delete the assignments, add a module `__getattr__(name)` that returns `i18n.t("gui." + name)` for a public upper-case name and raises `AttributeError` otherwise. `MAX_RUNS` and `SCAN_EXTENSIONS` stay real values.
  - `ACTUAL_SIZE` stays equal to `cli.ACTUAL_SIZE` in English (`test_gui_text.py:212-213`); both read key `cli.ACTUAL_SIZE`.
  - Private tables become key lookups: `gui.health.<name>`, `gui.reason.<n>`, `gui.problem.<name>`, `gui.paper.<name>`, `gui.dots.<name>`.
  - `count(n, noun)` becomes `i18n.n("count." + noun, n)`; nouns `page`, `byte`, `block`, `dot`, `scan`. Every other `{x:,}` becomes `i18n.number(x)`.
  - Every sentence built from fragments becomes one template per whole sentence or whole phrase, with plural tables where a count decides the form. In particular `_run_text` gets three templates per problem (`one page`, `two pages`, `a range`), `save_warning`'s "and N more page(s) missing or damaged" is a plural entry, `name_warning`'s parts and endings are whole sentences, `_state_line`'s variants are one template each. Joining finished phrases with `" · "`, `"; "` and `" — "` stays in code.
  - A template never contains another language's grammar: no `{s}`, no `{is_are}` placeholders.
  - Check for import-time reads: `grep -n "text\.[A-Z_]\+" src/optar_gui/*.py` and move any that sit at module or class level (or in default arguments) into the function that uses them; `grep -rn "from optar_gui.text import\|from .text import" src tests` and replace constant imports with `text.NAME`.

- [ ] **Step 5: Run** `.venv/bin/pytest -q tests/unit/test_gui_text.py tests/unit/test_work.py tests/unit/test_identify.py` then `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui`. Expected: PASS, with no existing assertion edited.

- [ ] **Step 6: Commit** "Moves the window's wording into the English catalogue".

---

### Task 3: The command line's wording and its language (**parallel** with Task 2)

**Files:**
- Modify: `src/optar/cli.py`, `src/optar/locale/en.toml` (`[cli]` only)
- Test: `tests/unit/test_cli.py` (additions only)

**Interfaces:**
- Consumes: Task 1.
- Produces: `cli.choose_language(environ: Mapping[str, str], encoding: str | None, system: str | None = None) -> str`: order `OPTAR_LANG`, `LC_ALL`, `LC_MESSAGES`, `LANG`, then `system` (Windows: the user's interface language, found by `main` with `locale.getlocale()`), else `"en"`; a language that is not `i18n.encodable(code, encoding or "utf-8")` gives `"en"`. `main()` calls it with `os.environ` and `sys.stderr.encoding` before building the parser. `cli.ACTUAL_SIZE` and `cli.PAPER_HINT` remain readable names (module `__getattr__`).

- [ ] **Step 1: Record today's English.** Add `test_english_help_is_unchanged`: capture `optar --help`, `optar encode --help`, `optar decode --help` now and pin them as literals (with `COLUMNS=100` set). Run: PASS.

- [ ] **Step 2: Write the failing tests.**

```python
@pytest.mark.parametrize("env, enc, want", [
    ({"OPTAR_LANG": "ru"}, "utf-8", "ru"),
    ({"OPTAR_LANG": "xx", "LANG": "pl_PL.UTF-8"}, "utf-8", "pl"),
    ({"LC_ALL": "C", "LANG": "it_IT"}, "utf-8", "it"),        # C is skipped, not final
    ({"LANG": "ka_GE.UTF-8"}, "cp1252", "en"),                 # Review Focus 3
    ({"LANG": "ka_GE.UTF-8"}, None, "ka"),
    ({}, "utf-8", "en"),
])
def test_choose_language(env, enc, want): ...   # with stub catalogues present

def test_choose_language_uses_the_system_language_last():
    assert cli.choose_language({}, "utf-8", system="tr_TR") == "tr"

def test_messages_follow_the_language(tmp_path, capsys, monkeypatch):
    # stub "ru" with cli.wrote = "записан {path}"; OPTAR_LANG=ru; run an encode to tmp_path
    # assert "записан" in captured.err and the option names in --help are still "--protect"

def test_cli_source_holds_no_wording():
    # AST scan: no help=, description=, _eprint( or parser.error( argument that is a
    # literal or f-string containing a space
```

- [ ] **Step 3: Run** `.venv/bin/pytest -q tests/unit/test_cli.py`. Expected: new tests FAIL, old PASS.

- [ ] **Step 4: Move the wording.** Every `help=`, `description=`, `_eprint`, `parser.error` and summary fragment goes through `i18n.t`/`i18n.n` with `cli.*` keys, as whole sentences (the same rules as Task 2 step 4). `_plural` becomes `i18n.n("count." + word, n)`. argparse's own words: pass translated titles for the positional and option groups and a `usage` prefix through a small `ArgumentParser` subclass that overrides `format_usage`/`format_help`/`error`; keys `cli.argparse.usage`, `cli.argparse.options`, `cli.argparse.positionals`, `cli.argparse.error`. Words argparse builds internally and does not expose stay English.

- [ ] **Step 5: Run** `.venv/bin/pytest -q tests/unit/test_cli.py` and `.venv/bin/pytest -q`. Expected: PASS, no existing assertion edited.

- [ ] **Step 6: Commit** "Moves the command line's wording into the catalogue and chooses its language".

---

### Task 4: Library errors that can be translated

**Files:**
- Modify: `src/optar/errors.py`, `src/optar/fileio.py`, every `src/optar/**/*.py` raise site a person can reach (about 61; list them with `grep -rn "raise \|io_error(" src/optar --include=*.py | grep -v cli.py`), `src/optar/i18n.py`, `src/optar/cli.py` (`main`, `_probe`), `src/optar_gui/text.py` (`unreadable_reason`, `save_failed`, `create_failed`, `check_failed`, `file_unreadable`, `preview_failed`, `repair_failed`) and their callers in `work.py`/`jobs.py` where only `str(e)` is passed on today, `src/optar/locale/en.toml` (`[err]`)
- Test: `tests/unit/test_errors.py` (new)

**Interfaces:**
- Produces:
  - `OptarError.key: str | None` and `OptarError.values: dict[str, object]` (defaults `None`, `{}`).
  - `errors.error(cls: type[E], key: str, english: str, /, **values: object) -> E`: returns `cls(english.format(**values))` with `key` and `values` set. `english` is always a string literal at the call site.
  - `i18n.error_text(e: BaseException) -> str`: `t(e.key, **e.values)` when `e` has a key the catalogue knows, else `str(e)`.
  - `fileio.io_error` keeps its signature; keys `err.cannot_read`, `err.cannot_write` (one per verb in use; the verb is not a value).
  - Where the window passes a reason on as a string today, it passes the exception (or `(key, values)`) far enough that `text.py` can call `error_text`. The six entries of today's `_REASONS` become `err.*` keys with the window's longer wording kept as `gui.reason.*` overrides.

- [ ] **Step 1: Write the failing tests.**

```python
def test_every_error_call_matches_the_english_catalogue():
    # AST scan of src/optar: for each call errors.error(cls, key, english, ...):
    #   key and english are literals; i18n.catalogue("en")[key] == english

def test_no_reachable_raise_is_left_without_a_key():
    # AST scan of src/optar (not cli.py): every `raise X(...)` where X is OptarError,
    # FormatError, DecodeError or IdentifyError is a call to errors.error(...),
    # except sites listed in INTERNAL (a literal set of "file:function" names in this
    # test, each a programming error no input can reach, with a one-line reason).

def test_error_text_translates_and_keeps_values():
    e = errors.error(FormatError, "err.demo", "page {page} of {total}", page=3, total=2)
    assert str(e) == "page 3 of 2" and e.key == "err.demo" and e.values == {"page": 3, "total": 2}
    # with a stub "ru" err.demo = "страница {page} из {total}": error_text(e) == "страница 3 из 2"

def test_error_text_of_a_plain_exception_is_its_text():
    assert i18n.error_text(ValueError("x {y}")) == "x {y}"

def test_cli_prints_the_translated_error(tmp_path, capsys, monkeypatch):
    # stub ru err.cannot_read; OPTAR_LANG=ru; optar encode <missing file>; exit code 2;
    # stderr has the Russian text and the path
```

- [ ] **Step 2: Run** `.venv/bin/pytest -q tests/unit/test_errors.py`. Expected: FAIL.

- [ ] **Step 3: Implement.** Convert each raise site without changing its English text (the existing tests pin many of them). `ValueError`/`TypeError` raised for programming errors stay as they are and go in `INTERNAL` only if they are one of the four classes. The library does not import `i18n`.

- [ ] **Step 4: Run** `.venv/bin/pytest -q`, `.venv/bin/pytest -q -m slow -n auto tests/unit/test_container.py`, `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui`, `.venv/bin/ruff check .`. Expected: PASS.

- [ ] **Step 5: Commit** "Gives library errors a message key so they can be translated".

---

### Task 5: The window's language (**parallel** with Task 4 except for `text.py`: run after Task 4 if both are in flight)

**Files:**
- Create: `src/optar_gui/language.py`, `tests/gui/test_language.py`
- Modify: `src/optar_gui/__main__.py`, `main_window.py`, `dialogs.py`, `selftest.py`, `tests/gui/conftest.py`, `src/optar/locale/en.toml` (`gui.cli.*` for `optar-gui`'s terminal messages)

**Interfaces:**
- Consumes: `text.button`, `text.LANGUAGE_MENU`, `text.SYSTEM_LANGUAGE`, `text.LANGUAGE_RESTART` (Task 2); `i18n.languages`, `i18n.pick_language`, `i18n.set_language`; `cli.choose_language` (Task 3).
- Produces (`language.py`, Qt allowed):
  - `saved() -> str | None`: the saved code if it is a string in `i18n.languages()`, else `None`.
  - `save(code: str | None) -> None`: `None` removes the choice.
  - `system() -> str | None`: `i18n.pick_language(QLocale.system().uiLanguages())`.
  - `at_start() -> str`: `saved() or system() or "en"`.
  - Settings: `QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, "optar", "optar-gui")`, key `language`.

- [ ] **Step 1: Isolate the settings in tests.** In `tests/gui/conftest.py` add an autouse fixture that calls `QSettings.setPath(IniFormat, UserScope, str(tmp_path))` and restores English after each test.

- [ ] **Step 2: Write the failing tests** in `tests/gui/test_language.py`.

```python
def test_nothing_saved_gives_the_system_language(monkeypatch): ...
@pytest.mark.parametrize("raw", ["xx", "", 7, "RU "])        # Review Focus 4
def test_bad_saved_choice_is_ignored(raw): ...               # write raw to the ini; saved() is None
def test_save_and_read_back(): ...                           # save("pl") -> saved() == "pl"; save(None) -> None
def test_menu_lists_every_language_by_its_own_name(qtbot):
    # MainWindow has a menu titled text.LANGUAGE_MENU whose actions are
    # [text.SYSTEM_LANGUAGE, *i18n.languages().values()]; exactly one is checked
def test_choosing_a_language_saves_it_and_says_restart(qtbot, monkeypatch): ...
    # trigger an action; language.saved() == its code; the message shown is text.LANGUAGE_RESTART;
    # the window's current texts did not change
def test_message_box_buttons_come_from_the_catalogue(qtbot, monkeypatch):
    # stub ru gui.button.save = "Сохранить"; the box built by dialogs.ask with Save|Cancel
    # has a button whose text is "Сохранить"; same for the QDialogButtonBox of _buttons()
def test_missing_qt_message_follows_the_environment(monkeypatch, capsys): ...
    # tests/unit/test_gui_entry.py style: PySide6 import fails, OPTAR_LANG=ru with a stub -> Russian
def test_self_test_runs_in_english_and_loads_every_catalogue(): ...
```

- [ ] **Step 3: Run** `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui tests/gui/test_language.py`. Expected: FAIL.

- [ ] **Step 4: Implement.**
  - `__main__.main`: first `i18n.set_language(cli.choose_language(os.environ, sys.stderr.encoding))` for `--help`, `--version` and `MISSING_QT`; after `QApplication` exists, `i18n.set_language(language.at_start())` before `MainWindow` is imported and built. `--self-test` sets English.
  - `main_window.py`: a menu bar with the one menu; choosing an entry calls `language.save` and shows `text.LANGUAGE_RESTART` through `dialogs.ask`.
  - `dialogs.py`: `ask` and `_buttons` set each standard button's text from `text.button`.
  - `selftest.py`: after its encode and decode, load every catalogue in `i18n.languages()` and call `text.READ_TAB` in each; report lines stay English.
  - No work on the interface thread is added; settings are read once at start.

- [ ] **Step 5: Run** `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui`, `.venv/bin/pytest -q`, `.venv/bin/optar-gui --self-test`. Expected: PASS and exit code 0.

- [ ] **Step 6: Commit** "Adds the language menu and starts the window in the saved or system language".

---

### Task 6: Tests that keep the languages complete (**parallel** with Tasks 4, 5, 7)

**Files:**
- Create: `tests/unit/test_catalogues.py`, `tests/unit/test_doc_translations.py`, `tools/translation_status.py`

**Interfaces:**
- Consumes: `i18n.languages`, `i18n.catalogue`, `i18n.categories`.
- Produces: a page's front matter key `source_hash` (40 hex digits: `git hash-object` of the English page it was translated from). `tools/translation_status.py` prints one line per stale or missing page (`docs/install.ru.md: stale`) and exits 0; `--check` exits 1 if any page is missing (not for stale).

Every test is parametrized over `[c for c in i18n.languages() if c != "en"]`, so it is empty now and grows as catalogues arrive.

- [ ] **Step 1: Write `test_catalogues.py`.**

```python
def test_same_keys_as_english(code)                 # set equality, message lists the difference
def test_same_placeholders_as_english(code)         # string.Formatter().parse field names, per key;
                                                    # for plural entries: every form uses a subset of
                                                    # the English forms' union and contains {n} iff English does
def test_plural_entries_have_exactly_the_language_categories(code)
def test_no_empty_strings_and_no_stray_braces(code) # every value formats with dummy values
def test_language_name_and_group_separator(code)    # [language].name non-empty; [format].group one of
                                                    # ",", ".", " ", " ", " ", ""
def test_every_text_function_answers(code)          # set_language(code); call each public function of
                                                    # text.py with the representative inputs the English
                                                    # tests already build (reuse the helpers of
                                                    # test_gui_text.py); every result non-empty str/None
def test_all_nine_languages_are_present()           # marked xfail(strict=False) until Task 10 removes the mark
```

- [ ] **Step 2: Write `test_doc_translations.py`.** English pages are `docs/*.md` whose stem has no dot.

```python
def test_every_page_exists(code)                    # docs/<page>.<code>.md for each English page
def test_code_blocks_equal_english(code, page)      # fenced blocks, in order, byte-equal
def test_heading_ids_equal_english_anchors(code, page)
    # every heading line ends with "{ #id }"; the ids, in order, equal the English page's
    # anchors computed with markdown.extensions.toc.slugify (and its _1 suffixes for duplicates)
def test_format_page_numbers_equal_english(code)    # for format.<code>.md: every table cell that is
                                                    # purely numeric/hex/code in English is equal
def test_format_page_says_english_is_normative(code)  # the first paragraph links to the English format page
def test_source_hash_is_present(code, page)         # front matter, 40 hex digits
def test_links_point_at_existing_pages_and_ids(code, page)  # relative .md links resolve to the same
                                                    # language's page; #fragments are ids of that page
```

- [ ] **Step 3: Write `tools/translation_status.py`** (library-style functions plus a `main`; it may print, being a tool).

- [ ] **Step 4: Prove the tests bite.** In `tmp_path`, build a tiny fake catalogue and a fake page with one fault each (missing key, extra placeholder, wrong category, changed code block, missing id) and assert the checking functions report it: the checks are plain functions the parametrized tests call, tested directly here.

- [ ] **Step 5: Run** `.venv/bin/pytest -q tests/unit/test_catalogues.py tests/unit/test_doc_translations.py`. Expected: PASS (fault tests) with the per-language tests collected as empty.

- [ ] **Step 6: Commit** "Adds the tests that keep catalogues and translated pages in step with English".

---

### Task 7: The site's machinery and the translators' brief (**parallel** with Tasks 4, 5, 6)

**Files:**
- Modify: `pyproject.toml` (`docs` extra gains `mkdocs-static-i18n>=1.2`), `mkdocs.yml`, `CLAUDE.md`, `README.md`, `docs/development.md`
- Create: `docs/superpowers/translation-brief.md`

- [ ] **Step 1: Configure the plugin** in `mkdocs.yml`: `plugins: [search, i18n]` with `docs_structure: suffix`, `fallback_to_default: true`, `reconfigure_material: true`, `reconfigure_search: true`, and one language entry for now: `en` (default, name "English", `build: true`). Add `validation: {anchors: warn, links: {not_found: warn}}` so `--strict` fails on a dead anchor. Check each option name against the installed plugin's documentation before relying on it (the names here are from memory). Leave a comment showing where each further language and its `nav_translations` go.

- [ ] **Step 2: Run** `.venv/bin/pip install -e '.[docs]' && .venv/bin/mkdocs build --strict`. Expected: builds; `site/index.html` exists; English URLs unchanged (`site/install/index.html`).

- [ ] **Step 3: Spike the fallback and search once**, with a throwaway `docs/install.ru.md` and a throwaway `ru` language entry: build, look at `site/ru/`, confirm (a) an untranslated page appears in English under `/ru/`, (b) the switcher is in the header, (c) whether search results mix languages. Remove the throwaway file and entry. Record the three answers in `docs/development.md` under a new "Translations" section.

- [ ] **Step 4: Write `docs/superpowers/translation-brief.md`**, the one document every translating and reviewing agent is given. It states:
  - Who reads the result: ordinary people printing and scanning at home; plain words, the polite form of address normal for software in that language, no literal calques, the same strength of claim as English ("verified" is never softened or strengthened).
  - Glossary first: the terms dot, block, protection, fingerprint, tag, label, spare, scan, printout, page, slower reader, self-identifying page, verified, repaired, lost, damaged, missing; one chosen word each, with a line of reasoning, in `docs/superpowers/glossaries/<code>.md`; plus a "Site navigation" section translating the eleven nav titles and three section titles of `mkdocs.yml` and the site description.
  - Catalogue rules: copy `en.toml`, keep every key, translate every value, keep every `{placeholder}` name, give plural entries exactly the categories `i18n.categories(code)` returns, set `[language].name` and `[format].group` (`ru`, `uk`, `be`, `pl`, `ka`: no-break space; `it`, `es`, `tr`: `.`), never translate option names, command names, file extensions or `optar`.
  - Page rules: file `docs/<page>.<code>.md`; front matter `source_hash` from `git hash-object docs/<page>.md`; every heading ends with `{ #<english-anchor> }`; fenced code blocks are copied unchanged; links keep their targets; image paths unchanged with alt text translated; `format.<code>.md` opens with the note that the English page is normative and keeps every number, constant, table cell of numbers and worked example unchanged.
  - Self-check before finishing: `.venv/bin/pytest -q tests/unit/test_catalogues.py tests/unit/test_doc_translations.py` passes for the language.
  - What to hand back: the files, and a short list of English strings whose template shape did not fit the language's grammar.

- [ ] **Step 5: Update the rules.** `CLAUDE.md`: under Rules add the catalogue rules (only `cli.py` imports `i18n`; `text.py` is the window's only door to the catalogue and imports it lazily; a new or changed string is added to all nine catalogues in the same pull request; translated pages carry `source_hash`, English ids on headings and unchanged code blocks; `docs/format.md` in English is the normative one; `tools/translation_status.py` lists stale pages). `README.md`: one line linking the site's other languages. `docs/development.md`: the "Translations" section (how to add a string, how to refresh a stale page, `OPTAR_LANG`).

- [ ] **Step 6: Run** `.venv/bin/mkdocs build --strict` and `.venv/bin/pytest -q`. Expected: PASS.

- [ ] **Step 7: Commit** "Sets up the site for translated pages and writes the translators' brief".

---

### Task 8: Russian, the pilot

**Files:**
- Create: `docs/superpowers/glossaries/ru.md`, `src/optar/locale/ru.toml`, `docs/<page>.ru.md` for the eleven pages
- Modify: `mkdocs.yml` (the `ru` entry and its `nav_translations`), and, where the pilot shows a template does not fit, `text.py`/`cli.py`/`en.toml` with English output unchanged

- [ ] **Step 1: Glossary and catalogue.** Dispatch one agent on the **opus** model with the brief, `en.toml` and the English pages as reading; it writes `glossaries/ru.md` and `ru.toml` and reports misfitting templates.

- [ ] **Step 2: Fix template shapes.** For each reported misfit (a sentence whose word order or agreement cannot be expressed), reshape the template in `en.toml` and its caller so that both English (unchanged output) and Russian read correctly. Run `.venv/bin/pytest -q` and the GUI suite. This is the step that protects the other seven languages; do not skip it if the list is non-empty.

- [ ] **Step 3: Pages.** Dispatch two **opus** agents in parallel with the brief and the glossary: one for the ten ordinary pages, one for `format.ru.md`.

- [ ] **Step 4: Wire the site.** Add `ru` to `mkdocs.yml` with the nav translations from the glossary.

- [ ] **Step 5: Verify.** `.venv/bin/pytest -q tests/unit/test_catalogues.py tests/unit/test_doc_translations.py` (now collecting `ru`), `.venv/bin/pytest -q`, `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui`, `.venv/bin/mkdocs build --strict`, `OPTAR_LANG=ru .venv/bin/optar encode --help`. Expected: PASS; help in Russian with English option names.

- [ ] **Step 6: Independent read.** Dispatch a fresh **opus** agent as a native Russian reader with the brief, the glossary, the English and the Russian: it reports mistranslations, unnatural phrasing, glossary breaches and any claim that changed strength. Apply the fixes; re-run step 5.

- [ ] **Step 7: Look at it.** Start the window with the saved language set to Russian (offscreen screenshot of each tab into the scratchpad) and check for clipped or overflowing labels; widen or wrap in the widgets where needed, without changing English layout tests.

- [ ] **Step 8: Commit** "Adds Russian".

---

### Task 9: The other seven languages (seven **parallel** lines, one per language)

**Files (per language `<code>` in `uk`, `be`, `pl`, `ka`, `tr`, `it`, `es`):**
- Create: `docs/superpowers/glossaries/<code>.md`, `src/optar/locale/<code>.toml`, `docs/<page>.<code>.md` for the eleven pages
- No other file is touched by a language line; `mkdocs.yml` is edited by the coordinator in Task 10.

For each language, the same sequence as Task 8 steps 1, 3 and 6, all on the **opus** model:

- [ ] **Step 1:** one agent: glossary and catalogue. `uk` and `be` agents are also given the reviewed Russian glossary as a reference for term choices, not as a source to transliterate.
- [ ] **Step 2:** two agents in parallel: the ten ordinary pages; `format.<code>.md`.
- [ ] **Step 3:** the language's tests pass: `.venv/bin/pytest -q tests/unit/test_catalogues.py tests/unit/test_doc_translations.py -k <code>`.
- [ ] **Step 4:** a fresh agent reads as a native reader and reports; fixes applied; step 3 again.
- [ ] **Step 5:** if an agent reports a template that does not fit its grammar, stop that language's line and bring the report to the coordinator: a template change touches every catalogue and is made once, centrally, with all catalogues updated together.
- [ ] **Step 6: Commit** "Adds <Language>" (one commit per language).

---

### Task 10: Bring it together

**Files:**
- Modify: `mkdocs.yml`, `tests/unit/test_catalogues.py` (remove the `xfail` mark), `.github/workflows/docs.yml` only if the build needs a change, `packaging/smoke.py`

- [ ] **Step 1:** Add the seven languages and their `nav_translations` to `mkdocs.yml`, in `i18n.ORDER`.
- [ ] **Step 2:** Remove the `xfail` from `test_all_nine_languages_are_present`; it asserts `tuple(i18n.languages()) == i18n.ORDER`.
- [ ] **Step 3:** `packaging/smoke.py` additionally runs the built `optar --help` with `OPTAR_LANG=ka` and checks the output is not the English help (proves the one-file build carries the catalogues).
- [ ] **Step 4: Full verification.**
  - `.venv/bin/pytest -q`
  - `.venv/bin/pytest -q -m slow -n auto` (not the timing files) and `.venv/bin/pytest -q -m slow tests/unit/test_claims.py`
  - `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui`
  - `.venv/bin/ruff check .`
  - `.venv/bin/mkdocs build --strict`
  - `.venv/bin/optar-gui --self-test`
  - `.venv/bin/pyinstaller --onefile --name optar --collect-data optar packaging/entry.py && .venv/bin/python packaging/smoke.py dist/optar`
  - `.venv/bin/python tools/translation_status.py --check`
  - `git diff docs-site -- tests/vectors lega-c` is empty.
  Expected: all pass.
- [ ] **Step 5:** Offscreen screenshots of both tabs in each of the nine languages into the scratchpad; fix any clipped label.
- [ ] **Step 6: Commit** "Publishes the site and the application in nine languages".
- [ ] **Step 7:** Report to the owner: what was verified, what the search spike showed, the list of template changes, and any language whose reviewer left doubts.
