# Final whole-branch review: `multilingual`, 3dc7571..2a73506

Verdict: **ready to merge with fixes**. No Critical issue. Four Important ones: the command line never follows the system language on Windows, one test fails on a machine whose `LANG` is one of the eight languages, the packaged-build check guesses an encoding that only the Windows release build can confirm, and `--help` can crash where stdout and stderr have different encodings.

## Scope read

**Read in full**
- Design: `docs/superpowers/specs/2026-11-19-multilingual-design.md`; the deferred list; `CLAUDE.md`.
- Library: `src/optar/i18n.py`, `errors.py`, `locale/en.toml`, `cli.py` (file and diff), and every raise-site diff (`container`, `decoder/__init__`, `geometry`, `soft`, `encoder`, `fileio`, `font`, `format`, `identify`, `imageio`, `label`, `pdf`).
- Window: diffs of `text.py`, `__main__.py`, `dialogs.py`, `document.py`, `flow.py`, `jobs.py`, `language.py`, `main_window.py`, `preview.py`, `read_tab.py`, `selftest.py`, `work.py`, `write_tab.py`.
- Tooling: all four workflow files, the `mkdocs.yml` diff, `packaging/smoke.py`, `pyproject.toml`, `tools/translation_status.py`, the English doc diffs.
- Tests: both `conftest.py` files, `test_jobs.py` (diff), `test_language.py`, `test_catalogues.py`, `test_errors.py`, `test_gui_entry.py`.

**Sampled**
- `tests/gui/test_language_switch.py` (first half), `tests/gui/test_read_layout.py` (first third and the tooltip test).
- `tests/unit/test_cli.py` (the language fixture, the help pin, `choose_language`), `test_gui_text.py` (removed lines and the language tests), `test_i18n.py` (plural and `pick_language` parts).
- `test_doc_translations.py`, `test_translation_text.py`, the translators' brief and the plan: by search only.

**Checks I ran** (small, Python 3.12.3, nothing heavy)
- English output of every public `text.py` function at base and at head, over the example inputs of `test_catalogues.py` widened with 0, 1, 999, 1000, 1,234,567 and names holding `{0}`, `{page}`, `%s`, `<b>` and newlines: 6,943 common calls, 0 differences; all 59 surviving constants equal.
- Command-line output at base and at head over 29 scenarios (three help texts, option conflicts, format and paper errors, compatible and version-1 encodes, decodes with a missing page, a duplicate, junk, another document's scan, too few pages, `--force`, a gap): identical.
- Three focused pytest runs under `LANG=ru_RU.UTF-8`; `tools/translation_status.py --check` (0 stale, 0 missing); layering checks by import.

**Left behind in the scratchpad** (safe to delete; no worktree, no git state touched)
- `/tmp/claude-1000/-home-mezinster-optar/61be2066-a588-4715-8f48-363f21db6ff0/scratchpad/review-3dc7571` (a `git archive` extract of the base `src`)
- `/tmp/claude-1000/-home-mezinster-optar/61be2066-a588-4715-8f48-363f21db6ff0/scratchpad/rv` (my scripts and their output)

## Strengths

- **English is unchanged, and I could not break it.** Both differential runs above came out identical. The existing English-pinning tests were not edited to pass: the only removed lines in old tests are one `BY_PROTECTION` assertion and the moved `NOT_DECODABLE` import.
- **Untrusted text is handled correctly.** Every template is filled once and values are never re-formatted, so a file name with `{0}` or `{path}` is inert. `value_problems` forbids attribute and positional placeholders in catalogues. Argparse help is `%`-escaped (`cli._help`, `text.cli_version_help`). Tooltips are escaped when Qt would read them as rich text; labels and message boxes are `PlainText`.
- **Threads are clean.** Worker code builds only `Words` and `_KeptError` (facts, no traceback, no exception object); wording happens when shown, on the interface thread. `document.py` only stores reasons and never compares them.
- **Layering holds.** Of the library only `cli.py` imports `i18n`; nothing under `src/optar` imports Qt or `optar_gui`; importing `text.py` loads neither numpy nor `optar`; no library module prints, exits or reads `sys.argv`.
- **The format is untouched.** `tests/vectors`, `lega-c` and `docs/format.md` have an empty diff. `format.py` changed only how `__post_init__` raises, in the same order with the same conditions. `unwrap()` changed only its raise.
- **The error inventory is real.** `test_errors.py` walks the AST, so a new unkeyed raise, a key that drifts from `en.toml`, or an unused `err.*` key fails a test.
- `tools/translation_status.py --check` reports all 88 pages fresh at head.

## Issues

### Critical (Must Fix)

None.

### Important (Should Fix)

**I1. On Windows the command line never follows the system language.** `src/optar/cli.py:84-91`
- `_system_language()` returns `locale.getlocale()[0]`, which on Windows is the C runtime's name (`Russian_Russia`, `Polish_Poland`, `Georgian_Georgia`), not `ru_RU`.
- `i18n.pick_language` cuts at `_` and looks for `russian`. I ran it with these names: all eight give `None`, so `choose_language` gives `en`.
- That value is also the format locale (LC_CTYPE), not the interface language the design asks for.
- `test_choose_language_uses_the_system_language_last` passes `tr_TR`, a name Windows never gives, so the suite cannot see this.
- I could not run Windows; the name form is CPython's documented behaviour.
- This is a plan defect too: the plan prescribes `locale.getlocale()`.
- Effect: a Windows user gets English unless they set `OPTAR_LANG`, against the design's "else, on Windows, the user's interface language".
- Fix: `ctypes.windll.kernel32.GetUserDefaultUILanguage()` mapped through `locale.windows_locale` (gives `ru_RU`), and a test with real Windows names. `optar_gui/__main__.py:41` passes no system language at all; give it the same.

**I2. A default-suite test fails on a machine whose language is one of the eight.** `tests/unit/test_gui_entry.py:47`
- Reproduced: `LANG=ru_RU.UTF-8 .venv/bin/pytest tests/unit/test_gui_entry.py` gives 1 failed, 5 passed. `test_missing_pyside6_says_how_to_get_it` gets the Russian message.
- `test_cli.py` protects itself with an autouse fixture (`OPTAR_LANG=en`); the other files do not.
- The contributors this branch invites are the people with those locales.
- Fix: one autouse fixture in `tests/conftest.py` that removes `OPTAR_LANG`, `LC_ALL`, `LC_MESSAGES` and `LANG` (or sets `OPTAR_LANG=en`) and resets `i18n` to English; then drop the copy in `test_cli.py`.

**I3. The packaged-build check may fail or pass for the wrong reason on the Windows release build.** `packaging/smoke.py:76-126`
- `output_encoding()` guesses the child's pipe encoding with `locale.getpreferredencoding(False)`. Under Python 3.15 (UTF-8 mode by default) that says UTF-8 whatever the machine's code page is.
- With that guess the loop takes `ru` first and also requires Georgian. If the frozen executable's pipes are in fact cp1252, the program rightly answers in English and the check fails with "the catalogues are not in the build".
- The other way round, `encodable()` returns False for an unreadable catalogue file, which prints a note and passes: the check cannot fail then.
- `build.yml` runs only on a tag or a manual run, so a merge does not exercise it; the first signal would be a failed release.
- Fix: try `it` and `es` first (encodable in cp1252, cp1254 and UTF-8, measured), make Georgian a note unless the output is Georgian, and fail when a catalogue file cannot be read.
- Before tagging, run the Release workflow by hand (`workflow_dispatch` rehearses it) on Windows and macOS.

**I4. `--help` can end in a traceback where stdout and stderr have different encodings.** `src/optar/cli.py:578`
- The language is chosen from `sys.stderr.encoding` alone, but `--help` and `--version` go to stdout, whose error handler is strict (stderr's is `backslashreplace`).
- On Windows with Python 3.12 to 3.14 (which `requires-python` allows), a console stderr is UTF-8 while a redirected stdout is the ANSI code page. So `optar --help > help.txt` or `| more` in Georgian, or in Russian on a cp1252 machine, raises `UnicodeEncodeError`.
- Not reproducible on Linux. Today it needs `OPTAR_LANG`; after I1 it is reachable by default.
- Fix: require the language to be encodable in both streams' encodings, with a test.
- This was deferred from Task 3 as Minor; I raise it because I1's fix makes it reachable.

### Minor (Nice to Have)

- **M1. The fallback to English is wider than it needs to be.** `i18n.encodable` (`src/optar/i18n.py:227`) tests the whole catalogue, window strings included.
  - `ru`, `uk` and `be` fall back on cp1251 only because of U+00D7 in four `err.*` messages (English writes `x`).
  - `it` and `es` fall back on cp850 only because of window strings (`…`, `·`).
  - Limit the test to `cli.*`, `err.*`, `count.*`, `alternatives.*`, `format.*`, `gui.cli.*`. This is the ledger's "product note for the owner".
- **M2. `LC_ALL=C` does not give English.** With `LANG=it_IT` set it gives Italian, pinned by `test_cli.py:1038` ("C is skipped, not final"). `LC_ALL=C` is the usual way to ask for untranslated output in scripts and bug reports. `OPTAR_LANG=en` works. Owner's decision; if kept, say it in `docs/command-line.md`.
- **M3. Every `optar` start parses all nine catalogues.** `pick_language` calls `languages()`, which loads every file: `choose_language` measured 53 ms after a 210 ms import. A malformed catalogue of any language would also stop English runs. Check that the file exists and load only the chosen language and English.
- **M4. `main_window.py:44`, `language.py`, `selftest.py` and `__main__.py` call `optar.i18n` directly** (language names, `set_language`). `CLAUDE.md` says `text.py` is the window's only door to the catalogue. Route them through `text.py`, or reword the rule to "the only door for wording".
- **M5. `WindowError.__str__` (`work.py:128`) words itself on whichever thread calls it.** `jobs._run` logs `exc_info=e` on the worker thread, so a sentence is rendered there. It is read-only and for the log only, but it is the one place the rule is bent.
- **M6. `text.Words` has no `__bool__`.** `if scan.reason:` and `reason or page.reason` (`text.py`, `replace_rejected` and `detail_text`) are true for any `Words`, even one that words to "". None does today.
- **M7. `tests/gui/test_read_layout.py:74-86` swallows exceptions.** `loadable_languages()` skips any language that raises, and the test requires only `en` and `ru`. Now that all nine exist it should require `i18n.ORDER`.
- **M8. Stale comments.**
  - `tests/unit/test_catalogues.py:6-8` and `:408`: "no language but English until translations arrive".
  - `mkdocs.yml`: "Each further language is one entry like the Russian one".
- **M9. `mkdocs.yml` palette toggle names** ("Switch to dark mode", "Switch to light mode") are literal English in every language.
- **M10. `tools/translation_status.py` hashes the working file's bytes.** On a Windows checkout with `core.autocrlf` every page reads as stale. Normalise CRLF before hashing or add `.gitattributes` (`*.md text eol=lf`). CI is unaffected: the docs job runs on Linux and no test compares the hash.
- **M11. `text.with_reading` compares the line with the worded `gui.WORKING`** (`text.py`, `line in ("", _t("gui.WORKING"))`). It is safe as called, but it is a comparison of rendered text; the state is at hand.
- **M12. What a tenth language would trip over with no test telling them:**
  - `i18n.ORDER`: a `de.toml` not listed there is silently not a language, and `test_catalogues._started()` filters by `ORDER`, so it is not checked either.
  - `i18n._CATEGORIES` and `plural_category`: both fall back silently to the English rule.
  - `packaging/smoke.py` `ORDER`: a copy.
  - `test_catalogues.LANGUAGE_GROUP`: checked only for codes it lists.
  - `test_translation_text.OWN_SCRIPT`: defaults to Latin.
  - `mkdocs.yml`: no test compares its `languages` entries or `nav_translations` keys with `ORDER` and `nav`.
  - The lists in `CLAUDE.md`, `docs/development.md` and `README.md`.
  - Cheap guards: a test that the `*.toml` files equal `ORDER`, that `_CATEGORIES` has every code, and that `smoke.ORDER == i18n.ORDER`.

## Triage of the deferred points

"Verified" means I checked it against the code at 2a73506.

| Point | Call | Reason |
|---|---|---|
| Brief self-check should use `-k <code>`; "copy the id" | fine to leave | Working paper; `translation-brief.md:215` still lacks `-k` (verified). |
| `n()` raises TypeError on `n`/`count` in values | fine to leave | Moot: values now merge over them (verified, `i18n.py:200`). |
| `number()` re-reads the language | fine to leave | Wording happens on the interface thread only. |
| `_flatten` treats an all-category table as plural | fine to leave | A wrong table makes a key vanish, which `test_every_text_function_answers` catches. |
| `languages()` falls back to the code for a missing name | fine to leave | `name_and_separator_problems` requires the name. |
| Task 6: shared name pool, break at first problem, key order, own-script name | fine to leave | |
| Task 6: non-strict xfail | already fixed | No `xfail` left in `tests` (verified). |
| Bare `%` in a translated help text | already fixed | `cli._help` and `text.cli_version_help` escape it, with a test (verified). |
| Language chosen from stderr while `--help` goes to stdout | **fix before merge** | Issue I4 (verified present). |
| `ENGLISH_HELP` pin depends on the Python version | fine to leave | CI runs 3.15 only and local evidence is 3.12, so only CI can show it. |
| Full stops and range hyphen added in code | already fixed | Templates carry them (`gui.sentence`, `gui.list.range`, `gui.run.*.range`) (verified). |
| `BY_PROTECTION`, `READ_SLOWLY_SHORT` unused | already fixed | Both gone (verified by the base/head comparison). |
| Unknown dot size raises KeyError | fine to leave | Names come only from `DOT_SIZES`, which the tests cover. |
| `[gui.cli]` table position; "1 languages" | already fixed | Verified in `en.toml` and `selftest.py:137-140`. |
| Standard buttons lose Qt's mnemonics in English | owner's decision | A small English behaviour change (Alt+Y, Alt+N). |
| Self-test sets English twice | fine to leave | Harmless. |
| `identify.py:159` `_check` could be keyed | fine to leave | Listed in `INTERNAL` with a reason. |
| `identify_any` local named `error` shadows `errors.error` | fine to leave | `identify.py:467`; rename when next touched (verified present). |
| `OptarError.values` is a shared mutable `{}` | fix before merge (one line) | `errors.py:18`; `MappingProxyType({})` removes a trap (verified present). |
| `io_error` drops the key for an unknown verb | fine to leave | Only `read` (8) and `write` (3) are used (verified). |
| Dot-size items re-worded by position | fine to leave | Same `dot_choices()` order both times. |
| `jobs._one_line` used only by a test | fine to leave | |
| `document.py` hints say `str` where `Words` travels | fine to leave | Docstrings say it; `document.py` cannot import `text`. |
| Stub fixture calls `catalogues._real` | fine to leave | |
| Scroll position and current tab not asserted after a switch | fine to leave | `retranslate` only sets texts. |
| `GROUPS` lists "" while `value_problems` rejects it | fine to leave | The stricter check wins. |
| Odd wrapping at `docs/read-from-paper.md:102` | fine to leave | Touching the English page makes eight translations stale for a cosmetic gain. |
| "BASE_0002.png, ..." against «и т. д.» | fine to leave | |
| `gui.rejected.unusable_reason` capitalised reason mid-sentence | owner's decision | English is byte-for-byte what it was. |
| `gui.reason.not_decodable` lower case; ambiguous sentences of `format.md` | owner's decision | As already set aside. |
| `i18n.number` groups four-digit numbers ("1.000") | owner's decision | Spanish, Polish and Georgian usage want no separator below 10,000; can follow the merge. |
| Task 8b: `handle(1).isEnabled()`, `_process`, share after maximise, middle elision | fine to leave | |
| Font-dependent pixel bounds in `test_read_layout.py` | fine to leave | Only the Windows and macOS gui jobs can show it. The same file's "exactly two lines in Russian" (line 120) is equally font-dependent. |
| Reads private `ReadTab._shared` | fine to leave | |
| `formats` is a tuple subclass; comment tying `Alternatives.__format__` to `[alternatives]` | fine to leave | Tests pin both to "A, B or C". |
| `work.py:658` `_parity` raises an unkeyed error | fine to leave | Unreachable from the window. |
| Test pinning `smoke.ORDER` to `i18n.ORDER` | **fix before merge** | Cheap; part of M12 (verified absent). |
| `smoke.py` should fail on an unreadable catalogue | **fix before merge** | Issue I3 (verified: `OSError` gives False, then a note). |
| `smoke.py` trusts the encoding it guesses | **fix before merge** | Issue I3. |
| `script_of` gives º/ª their own script | fine to leave | The suite passes on Spanish as written. |
| Summary label unwrapped; widens the minimum width | fix before merge (small) | Verified: no word wrap at `read_tab.py:970`. The mechanism was there before the branch, but the eight languages make it visible (ka 607 to 757 px) and a long file name is unbounded. Wrap it, or elide with a tooltip. |
| Dialog prompts cut at `minimumSizeHint` | fine to leave | English too, and present before the branch; a minimum width is a cheap follow-up. |
| Save-failure message carries OS text; "Remove" orphaned on a second line | owner's decision | As already set aside. |

## Declined to judge

- The wording of the eight catalogues, the 88 translated pages and the glossaries: outside my package by instruction.
- Bidirectional control characters and newlines in file names and in a version-1 header's stored name, as shown in rows, tooltips and terminal lines: present before the branch, and the branch does not change how names are shown.
- Terminal escape sequences in file names printed by the command line: present before the branch.
- Right-to-left languages and screenshots per language: non-goals of the design.
- The intermittent `test_a_repair_that_raises_is_shown_as_plain_text_and_not_retried`: stated as failing at the base.
- Site search across languages and stemming: accepted in the design.
- Whether Material ships interface translations for `be` and `ka`, and whether `mkdocs build --strict` passes for nine languages: the controller's running verification and `docs.yml` show it. I did not run a build.
- The native file dialogs' language and the macOS menu bar's placement of the Language menu: the operating system's, and not observable here.
- Safety of the `i18n` cache on a free-threaded Python build: not a supported target that I can see.
- Colour in argparse's error line on Python 3.14 and later: the overridden `Parser.error` may drop the colour of "error:" on a terminal. I could not run 3.14 or 3.15.
- The browser-version spike in the ledger: outside the plan.

## Recommendations

1. Fix I1, I2 and I4 together; they are small and touch `cli.py`, `__main__.py` and `tests/conftest.py`. Then harden `smoke.py` (I3) and add the three guard tests of M12.
2. Before merging, let the pull request's CI run on all three systems. Every local result, mine and the controller's, is from Python 3.12 on Linux, and CI runs 3.15 only. It alone can show:
   - the `ENGLISH_HELP` pin and argparse's behaviour on 3.15;
   - the font-dependent layout tests on Windows and macOS;
   - the default suite on Windows.
3. Before tagging, run the Release workflow by hand. It alone can show the catalogues inside the three one-file builds, the Windows smoke check and the windowed self-test.
4. Put M1, M2 and the four-digit grouping to the owner as one decision about how the command line behaves in non-English terminals.
5. A human native read of Georgian and Belarusian before publishing, as the ledger already recommends.

## Assessment

**Ready to merge?** With fixes.

**Reasoning:** The core claims hold under test: English is byte-for-byte unchanged in both the window and the command line, the format is untouched, and untrusted text, threads and layering are handled correctly. What remains is at the edges the Linux, Python 3.12 runs could not reach (Windows language detection, differing stream encodings, the packaged-build check) plus one test that depends on the developer's locale.
