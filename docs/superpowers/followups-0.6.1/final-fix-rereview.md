# Re-review of the final fix wave: `multilingual`, 44b4e58..c9cd426

**The wave is not clean: one Important finding, six Minor ones.** Every item of the brief is addressed in the code. The Important finding is in the new tests, not the product: the wider-font variants of `tests/gui/test_read_layout.py` will most likely fail on the Windows gui job.

Read-only review. I read the whole diff and the files as they stand, and ran small scripts and focused test files only. Nothing in the tree, index or branch was changed. My scripts are in `/tmp/claude-1000/-home-mezinster-optar/61be2066-a588-4715-8f48-363f21db6ff0/scratchpad/rr` (safe to delete).

## Findings, in order of severity

### Important

**F1. The 1.5x and 2x font variants scale the platform's own font, so on Windows they go far past what was calibrated.** `tests/gui/test_read_layout.py:44-54`
- The fixture multiplies `qapp.font()`. The Windows log shows that font is already about 1.6 times (window minimum 922 against 577) to 1.9 times (12 px a character) as wide as the Linux one. So `font-2x` on Windows is about 3 to 4 times the Linux font, not 2.
- I reproduced it on Linux with a plugin that widens the application font before the fixture runs. All `font-1x` tests pass at both factors, so the layout fix itself holds for what Windows measured.
  - Platform font 1.6 times as wide: 7 of 48 fail.
  - Platform font 1.9 times as wide: 8 of 48 fail.
- The failing tests, at `font-1.5x` and `font-2x`:
  - `test_the_minimum_size_of_the_window_is_within_its_default_size` (`('ru', QSize(1028, 591))`, `('en', QSize(1052, 730))`).
  - `test_the_list_has_its_share_at_the_default_size_in_every_language` (line 117: the window cannot be 1000 wide).
  - `test_a_step_wraps_and_its_row_grows_when_the_list_is_made_narrow` (line 450: its own font arithmetic stops wrapping).
  - `test_the_window_still_fits_a_small_screen` (line 206) at `font-2x` only.
  - `test_the_buttons_wrap…` at `font-2x` under the 1.9 factor only.
- On Linux the window's minimum passes 1000 px between 2.0 times (be 875) and 2.4 times (ru 1028). macOS at `font-2x` is borderline if its font is more than about 1.15 times the Linux one.
- This assumes the Windows offscreen font scales with point size. Only the Windows gui job can confirm it.
- Fix (test only): scale to a target average character width measured at run time and cap it at what Windows measured (about 12 px), instead of multiplying whatever the platform has. Or skip a scale at which the reference text is already wider than that cap.

### Minor

**F2. At the window's minimum size a note of three or more lines cuts the action buttons.** `src/optar_gui/read_tab.py:1002-1003`, `src/optar_gui/flow.py:59-64`
- The wrapped summary takes its height from the splitter, and the right pane falls below its minimum height.
- Measured at 1x: English 370x331 with a long many-word path gives summary 98 px, pane 162 against a minimum of 230, and `switchButton`, `assignButton` and `removeButton` outside the pane. Turkish (minimum width 298) loses `removeButton` with an ordinary 80-character path.
- At 640x400 and at the default size nothing is cut, in any language. At the base nothing was cut, because the note widened the window instead.
- `test_a_saved_file_note_does_not_widen_the_window` checks width only.

**F3. `WrapLongRows` squeezes the Write tab's rows at the window's minimum size in six languages.** `src/optar_gui/write_tab.py:162`
- The form's minimum height does not count the wrapped rows. Examples at 1x: ka and tr have the choose button 16 px high against 22 and the paper buttons 15 against 19; ru, uk, be and pl have the choose button at 19 against 22.
- English is unaffected at 1x, 1.5x and 2x. Nothing overlaps. At the base nothing was squeezed.

**F4. `packaging/smoke.py` still fails for the pipe's encoding alone when the pipe is ASCII or cp1251.** `packaging/smoke.py:77`, `:145-148`
- It then reports "the catalogues are not in the build". Reproduced against `.venv/bin/optar` with `PYTHONIOENCODING=ascii`, with `PYTHONIOENCODING=cp1251`, and with `LC_ALL=C PYTHONCOERCECLOCALE=0 PYTHONUTF8=0`.
- It passes under utf-8, cp1252, cp437 (through `es`), cp1250 (through `pl`) and plain `LC_ALL=C` (Python coerces to UTF-8).
- This is as the brief specified (plausible encodings are utf-8 and cp1252), and the CI runners are UTF-8 or cp1252. A frozen build started in a bare C locale, or a Russian Windows machine on Python 3.14 or earlier, would get a false failure.

**F5. An unreadable catalogue of the chosen language still ends in a traceback.** `src/optar/cli.py:86-94`
- `choose_language` catches `LookupError` and `ValueError` only. A `PermissionError` from `_read` propagates (reproduced). The docstring says "as does one whose catalogue cannot be read".

**F6. The Windows call relies on the default `c_int` return type for a 16-bit LANGID.** `src/optar/cli.py:112-115`
- The x64 calling convention does not promise that the upper bits of the register are zero for a 16-bit result. In practice the function returns it zero-extended, and this is the common recipe.
- If the bits were not zero the id would miss the table and the result would be English, not a crash. `& 0xFFFF` would remove the doubt.

**F7. A long unbreakable file name in the summary is cut at the label's edge with no ellipsis.** `src/optar_gui/read_tab.py:1002`
- The whole text is in the plain-text tooltip, as the brief allowed.

## Verdict per item

| Item | Verdict | Where | Can its test fail on the real path? |
|---|---|---|---|
| I1 | ADDRESSED | `src/optar/cli.py:104-131`, `src/optar_gui/__main__.py:38-52` | Yes for the mapping and the order: real `locale.windows_locale`, real `main()`. The real `ctypes` call's return value is asserted nowhere (F6). |
| I2 | ADDRESSED | `tests/conftest.py:13-25` | Yes. I ran four unit files under `LANG=LC_ALL=ru_RU.UTF-8 LANGUAGE=ru` (88 passed) and the language tests of `test_cli.py` under `LANG=tr_TR.UTF-8` (35 passed). |
| I3 | ADDRESSED as briefed | `packaging/smoke.py:71-155` | No test in the suite; it was demonstrated by hand. See F4. |
| I4 | ADDRESSED | `src/optar/cli.py:75-101`, `:613-626` | Yes: `test_cli.py:1074` runs real `main(["--help"])` on a strict cp1252 stdout. |
| M1 | ADDRESSED | `src/optar/i18n.py:240-253`, `src/optar/cli.py:72` | Yes: `test_cli.py:1321` derives the keys from the AST of every `src/optar` module and of the `text.py` functions the entry point calls. |
| M3 | ADDRESSED for the command line | `src/optar/i18n.py:222-237`, `src/optar/cli.py:86-94` | Yes: `test_cli.py:1092`, real `main()`. The window is unchanged (see below). |
| M7 | ADDRESSED | `tests/gui/test_read_layout.py:108-110` | Yes. |
| M8 | ADDRESSED | `tests/unit/test_catalogues.py:5-6`, `:407`; `mkdocs.yml:45-50` | Comments only. |
| M10 | ADDRESSED | `tools/translation_status.py:30-34`, `:75` | Yes: the pinned hash is `git hash-object` of the LF file. |
| M12 | ADDRESSED, in two steps | `tests/unit/test_tenth_language.py` | Yes (see below). |
| D1 | ADDRESSED | `src/optar/errors.py:21` | Yes. |
| D2 | ADDRESSED | `src/optar_gui/read_tab.py:1000-1003`, `:1179-1181` | Yes, for width. See F2 and F7. |
| D3 | ADDRESSED | `src/optar_gui/dialogs.py:92-97` | Yes: real dialogs, nine languages; also passes under a font 1.9 times as wide. |
| W1 | ADDRESSED | `tests/unit/test_cli.py` (`test_a_message_with_braces…`) | A test fix; only Windows shows it. |
| W2 | ADDRESSED in the product; tests see F1 | `flow.py:59-64`, `write_tab.py:162`, `read_tab.py:838-872` | The 1x variants pass under a font 1.6 and 1.9 times as wide. The 1.5x and 2x variants are miscalibrated for Windows. |

## The points of section 2

**I1, the Windows language**
- The call is correct in form: no arguments, a LANGID back. A LANGID is numerically the LCID with the default sort, which is what `locale.windows_locale` is keyed by (ints).
- All nine ids are in the table, and so are 0x040A (`es_ES`) and 0x080A (`es_MX`). An id it lacks (0x580A, 0x1000) gives None, then English.
- Nothing can raise at import: `ctypes` is imported inside `_user_ui_language`, and `locale.windows_locale` exists on every platform.
- Nothing can raise at call: the call and the lookup are inside `windows_language`'s `try … except Exception`. That covers a missing `windll`, a missing `ctypes` in a frozen build, an unknown id and an unhashable result.
- The order is unchanged: `OPTAR_LANG`, `LC_ALL`, `LC_MESSAGES`, `LANG`, then the system.
- `optar_gui/__main__.py` uses the same `system_language()` and both streams.
- `optar_gui/language.py` is untouched. `language.system()` gives the same answers through the new `pick_language`.
- The fixer's report says no test calls the unpatched function on Windows. In fact every `main()` in the Windows job calls it, since `OPTAR_LANG=en` only outranks its result. A crash would show there; a wrong value would not.

**I4 and M1, both streams and the terminal tables**
- The guard's key list is derived, not hand-written. Every key in `cli.py` is a literal; the one built key is `i18n.listing`, whose prefix the scan catches.
- I found no path that prints a key outside the tables. Library errors are all `err.*`. The entry point's three `text` functions are `gui.cli.*`. The self-test forces English. Argparse's own words come from `cli.argparse.*`.
- The English fallback for a missing key is ASCII in the terminal tables, so it can never raise.
- The guard would miss a key built with an f-string. None exists today.
- My recomputation of the encoding table matches the report in every cell I checked. Cells: `ru`/cp1251 blocked by `×` only; `it`/cp437 by `×` only; `es`/cp1250 by `ñ` only; `pl` fits utf-8 and cp1250; `tr` fits utf-8 and cp1254; `it` gains cp850; `es` gains cp850 and cp437.

**M3, a malformed catalogue**
- Command line: `pick_language` reads nothing, and `choose_language` gives English for a malformed chosen catalogue (confirmed by script). An English run never reads the others.
- Window: unchanged, as the brief allowed. `i18n.languages()` raises `TOMLDecodeError` for a malformed file of any language, and so does `MainWindow()` when it builds the menu (reproduced). A malformed catalogue therefore still stops the window with a traceback.
- `languages()` still gives the nine names in `ORDER`.

**I2, the fixture**
- It removes the four variables, sets `OPTAR_LANG=en` and sets English before and after each test. A test's own `monkeypatch` still wins.
- The gui tests' Qt locale is fixed by `tests/gui/conftest.py::private_settings`, and `language.system()` is the only reader of `QLocale.system()`.
- I found no order-dependence. The module-scoped fixtures that call `main()` produce files, not text, and `main()` restores the language.

**I3, `smoke.py`**
- It reads all nine source catalogues first and fails naming the path on a missing, undecodable or malformed one.
- It fails when no language's help differs from English.
- It is standard library only (`locale` is gone), and the version, round-trip and PDF checks are intact.
- The exception is F4.
- Georgian is now only a note, so a build holding some catalogues but not all would pass. `--collect-data` is all or nothing, so this is theoretical.

**W2, D2 and D3, the layout**
- English at the default font and size: the geometry of every named widget of both tabs is identical before and after, and the same holds in all nine languages. `WrapLongRows` moves nothing there.
- Minimum sizes: the window's minimum height is unchanged at 331. Its minimum width fell (English 577 to 370).
- The dialogs changed in English too, as D3 intends: Assign 212x107 to 292x107, Start by hand 252x163 to 292x149.
- Row heights follow every case I tried at 2x: a new step (data change), a language switch (88 px in Russian, 60 back in English), the splitter, and the window. No stale height.
- Untrusted text stays plain: the summary is `PlainText` with a `_plain_tooltip`, the step is drawn with `drawText`, and the prompt is `PlainText`.
- Nothing new reads or decodes a scan on the interface thread; the delegate only measures text.
- Pinned pixels: none measured with a font remain. What is left is the window's own start size (1000x700), the small screen (1366x768) and ratios. The start-size equality is what breaks under F1.
- The list's share above 40 % at 2x in be and it: acceptable. A button cannot be narrower than its text, and the right pane's buttons are still checked for clipping in that test. The upper bound is weak by construction (any share the list's own minimum demands passes); the lower bound of 36 % is the one that guards the Windows failure.

**M12, a tenth language**
- Adding `de.toml` alone fails exactly one test, which names `i18n.ORDER`.
- The other five (`_CATEGORIES`, `smoke.ORDER`, `LANGUAGE_GROUP`, `OWN_SCRIPT`, `mkdocs.yml`) fail only once `de` is in `ORDER`. So the places are named in two steps, not at once.
- The lists in `CLAUDE.md`, `README.md` and `docs/development.md` stay unguarded.

## Rules

No violation found.
- `ENGLISH_HELP` and `tests/unit/test_gui_text.py` are unedited. The only removed lines of `test_cli.py` are the old fixture, the stub's key moved under `cli`, and the W1 path.
- `str(e)` is unchanged. Of the library only `cli.py` imports `i18n`. `i18n.py` and `errors.py` gained only standard-library imports. No library module prints, exits or reads `sys.argv`.
- No catalogue, translated page, glossary, `docs/format.md`, `tests/vectors` or `lega-c` file is in the diff. `mkdocs.yml` changed in its comment only.
- New tests write under `tmp_path` and keep settings there.

## Unverifiable until CI and the Release workflow

- **Windows job:** the real `GetUserDefaultUILanguage` value (F6); F1; W1; `ENGLISH_HELP` and the I4 test on Python 3.15.
- **macOS job:** the form's wrap policy under the native style, and F1 at `font-2x`.
- **Release workflow by hand:** `i18n._exists` inside the one-file builds, the pipe encoding of the frozen executables (F4), and the windowed self-test.
- I did not run the default suite, the gui suite, the slow tests or PyInstaller.

## One line

Not clean: F1 (Important, tests only: the 1.5x and 2x font variants will likely fail on the Windows gui job), then F2, F3, F4, F5, F6, F7 (Minor).
