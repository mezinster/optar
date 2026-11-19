# optar in nine languages: design

Date: 2026-11-19. Status: awaiting the owner's approval.

## Intent

optar's window, its command-line messages and its documentation exist only in
English. The owner wants them in eight more languages so that people who do not
read English can print, scan and recover files, and can read every page of the
documentation: Russian (`ru`), Ukrainian (`uk`), Belarusian (`be`), Polish
(`pl`), Georgian (`ka`), Turkish (`tr`), Italian (`it`) and Spanish (`es`).
The owner asked for maximum coverage: "only CLI commands should stay English".

## Goals

- Every string the window shows is available in all nine languages.
- Everything the command line prints for a person (help texts, progress,
  warnings, errors, the closing summary) is available in all nine languages.
- Every published documentation page, including the format specification, is
  available in all nine languages on the one site, with a language switcher.
- Grammar is right, not approximated: plural forms, number grouping and word
  order follow each language.
- A language that lacks a string or a page falls back to English; nothing
  breaks or shows a key name.
- Mechanical tests keep the languages complete and in step with English.

## Non-goals

- The command names, option names, metavariables (`encode`, `--protect`,
  `BASE`), file names and exit codes stay as they are.
- Nothing printed on paper changes. The page label, its tag and the label font
  are part of the format; `docs/format.md` and `tests/vectors` are untouched in
  meaning.
- The library (`src/optar` other than `cli.py`) stays language-neutral: its
  exceptions and reason strings keep their English text, which tests pin.
- Right-to-left languages, and languages beyond these nine.
- Screenshots per language (the four in `docs/img` stay shared; their alt text
  and captions are translated). *My call; easy to add later.*
- `docs/superpowers`, code comments, docstrings, commit messages, `CLAUDE.md`.
- Translator tooling such as Weblate.

## Anti-goals

- A translated specification that disagrees with the code. English
  `docs/format.md` remains the one normative text.
- A translation that changes what a message claims ("verified" must stay as
  strong, and only as strong, in every language).
- English behaviour or wording changing as a side effect: the existing tests
  that pin English wording pass unchanged.

## Constraints (from the project rules)

- Runtime dependencies stay numpy and Pillow. `tomllib` is in the standard
  library (the project requires Python 3.12).
- `text.py`, `document.py` and `work.py` import no Qt; nothing under
  `src/optar` imports Qt or `optar_gui`.
- Every user-visible string of the window lives in `text.py`; that rule
  becomes "`text.py` is the only door to the catalogues for the window".
- Library modules never print or read the environment; only `cli.py` does.
- Untrusted text (label text, file names) is shown as plain text.
- The one-file builds already pass `--collect-data optar`, so data files under
  `src/optar` are bundled.

## Approaches

### Application and command line

- **A. Own catalogues (chosen).** One TOML file per language under
  `src/optar/locale/`, keyed by the names `text.py` already uses, with a plural
  rule per language. No dependency, no build step, plain data that tests can
  compare key by key.
- **B. gettext.** Standard and tool-friendly, but needs compiled `.mo` files
  in the wheel and the one-file builds, or a build hook; the gain (translator
  tools) is a non-goal.
- **C. A Python module per language** implementing all the text functions.
  Free with grammar, but nine copies of the logic.
- Qt's translation system was ruled out: `text.py` may not import Qt and the
  command line could not share it.

The owner left the choice to Claude, who chose A.

### Documentation

- **1. `mkdocs-static-i18n` (chosen)**, one site, a language switcher, English
  fallback for a missing page.
- **2. One MkDocs build per language.** More configuration, no fallback.

Within approach 1 the files use the plugin's *suffix* layout
(`docs/install.ru.md` beside `docs/install.md`), not a folder per language,
because the folder layout would move the English pages and `docs/format.md` is
named by tests, by `CLAUDE.md` and by the site's edit links. *My call; this
corrects "a folder per language" from the conversation.*

## Design

### The catalogue module: `src/optar/i18n.py`

- `LANGUAGES`: the nine codes, each with its own name in its own script
  ("Русский", "ქართული", …).
- `set_language(code)`, `language()`; the default is English. An unknown code
  selects English.
- `t(key, **values)`: the string for `key` in the current language, formatted
  with `str.format`. Missing in the current language: the English string.
- `n(key, count, **values)`: chooses the plural form for `count`. Catalogues
  give plural strings as a table of categories: `one`, `few`, `many`, `other`.
  The rule per language is a small function in `i18n.py`:
  - `en`, `it`, `es`: `one`, `other`.
  - `ru`, `uk`, `be`, `pl`: `one`, `few`, `many` (integers only).
  - `tr`, `ka`: `other` only (the noun does not change after a number).
- `number(value)`: an integer with the language's thousands separator, which
  each catalogue names in a `[format]` table.
- `pick_language(candidates)`: the first supported language among locale names
  such as `ru_RU.UTF-8` or `pl-PL`.
- Catalogues are read once, lazily, with `importlib.resources` and `tomllib`.
- `i18n.py` never prints and never reads the environment. Of the library, only
  `cli.py` imports it.
- `text.py` imports `i18n` lazily, inside its lookups: importing the `optar`
  package loads numpy, which importing `text.py` must not do (the reason its
  other `optar` imports are already deferred). *Builder: add this to the rules in `CLAUDE.md`.*

### English moves into `en.toml`

English is one catalogue among nine, so there is a single path through the
code. `text.py` keeps its logic and its public names:

- Constants (`text.READ_TAB`, …) are served by a module-level `__getattr__`
  that looks the name up in the current language, so the widgets' 113 uses
  stay as written. Private tables (`_REASONS`, `_HEALTH_LABELS`, `_PROBLEMS`,
  `_PAPER_NAMES`, `_DOT_NAMES`) become lookups by key.
- Functions that glue fragments by English grammar are rewritten over
  whole-sentence templates. `count(n, noun)` becomes a plural lookup per noun
  (`page`, `byte`, `block`, `dot`, `scan`); "page 3 is missing / pages 3 and 4
  are / pages 3-7 are" become three templates per problem; and so on. Joining
  finished phrases with " · " stays.
- The English output of every function is byte-for-byte what it is today.
  `tests/unit/test_gui_text.py` and the GUI tests are the proof and are not
  edited to pass.

`cli.py` gets the same treatment: help texts, `_eprint` messages and the
`_plural` helper go through the catalogue (keys prefixed `cli.`). argparse's
own words ("usage:", "options:", "error:") are translated by passing
translated section titles and overriding the usage/error formatting where
argparse allows it; whatever argparse does not expose stays English. *My call.*

### Messages that come from the library

The owner asked for maximum coverage, so every library message a person can
reach through the window or the command line is translated, not only the six
reasons `text._REASONS` holds today (the reviewer counted about 61 raise and
`io_error` sites outside `cli.py`).

- The text of a library exception stays English and unchanged (`str(e)` is
  what tests pin). The library does not import `i18n`.
- So that wording changes cannot silently break the match, a library error
  that a person can reach carries a message key and its values beside the
  English text (for example attributes on the exception), and the English
  catalogue entry for that key, formatted with those values, must equal the
  English text exactly. *My call on the direction; the mechanics are the
  builder's.*
- A test holds the inventory: it fails when a reachable library message has no
  key, or when the English catalogue and the library's text disagree.
- A message that still arrives without a key (a third-party or unexpected
  error) is shown in English. Operating-system error text (`e.strerror`) is
  shown as the system gives it.

### Choosing the language

- **Window.** Order: the saved choice; else the system's language (Qt's
  `QLocale`, read in `__main__.py`, which is allowed Qt); else English. A
  "Language" menu lists the nine languages by their own names plus "System
  default". The choice is saved with `QSettings` and takes effect the next
  time the application starts; the menu says so in a short message. *My call:
  rebuilding a live window would have to carry loaded scans across, and that
  is not worth it for a setting changed once.*
- **Words Qt draws itself.** The standard buttons (Yes/No in
  `main_window.py`, Save/Cancel in `read_tab.py`, OK/Cancel in `dialogs.py`)
  are labelled from the catalogue, so they are right in all nine languages;
  Qt ships no Belarusian translation, and its translation files are not
  loaded. File dialogs are the operating system's own and follow the system's
  language. *My call.*
- **The Language menu is new interface**: the window has no menu bar today.
- **`optar-gui --self-test`** always runs in English, and additionally checks
  that each language's catalogue loads. Its report lines stay English.
- **`optar-gui`'s terminal messages** (`--help`, `--version`, and the
  `MISSING_QT` message in `__main__.py`) are translated and, because Qt may be
  absent at that moment, use the command line's rule below. *My call.*
- **Command line.** Order: the `OPTAR_LANG` environment variable; else
  `LC_ALL`, `LC_MESSAGES`, `LANG`; else, on Windows, the user's interface
  language; else English. If the stream being written cannot encode the
  chosen language (an old Windows console and Georgian), English is used
  instead of printing question marks. No new option is added.

### Documentation site

- `mkdocs-static-i18n` is added to the `docs` extra. English is the default
  language and keeps its URLs; other languages are served under `/ru/`,
  `/ka/` and so on.
- Navigation titles, the site description and the theme's own words are
  translated in `mkdocs.yml` (Material ships interface translations for all
  nine).
- Site search: expect one shared index, so a search may return pages in
  several languages. Stemming exists for `ru`, `it`, `es` and `tr`; `uk`,
  `be`, `pl` and `ka` get plain matching. Accepted; the builder checks the
  real behaviour in a test build and reports it.
- Every one of the eleven pages is translated into every language.
- Each translated page begins with front matter recording the English page it
  was made from (`source_hash`: the git blob hash of the English file).
- The translated `format.<lang>.md` opens with a note that the English page is
  normative. Its code blocks, tables of numbers, constants and worked examples
  are identical to the English ones.
- Heading anchors are the same in every language. The default slug of a
  Cyrillic or Georgian heading is empty (anchors become `_1`, `_2`, …) and
  Polish and Turkish headings lose letters, so every heading of a translated
  page carries an explicit id (`## Заголовок { #dot-size }`, `attr_list` is
  already on) equal to the anchor of the English heading. English pages and
  their URLs do not change. A test checks that the ids of a translated page
  equal the English page's anchors, in order, and `mkdocs.yml` turns on anchor
  validation so that `mkdocs build --strict` fails on a dead link.
- The README stays a short English overview and gains one line linking the
  site's other languages.

### Keeping translations right

Terms first. Before any string or page is translated, each language gets a
glossary of optar's terms (dot, block, protection, fingerprint, tag, label,
spare, scan, printout, page, slower reader, self-identifying page, verified,
repaired, lost). It is kept in `docs/superpowers/glossaries/<lang>.md`
(working papers, not published) and is given to every translating and
reviewing agent, so the window, the command line and the docs use the same
word for the same thing.

Who translates. Opus agents, one per language, as the owner asked. A second,
independent Opus agent per language then reads the result as a native reader
and checks it against the English and the glossary. The owner's own reading of
any language they know is welcome but is not a gate.

Mechanical tests (default suite, no Qt needed):

- Every catalogue has exactly the keys of `en.toml`; no extra, none missing.
- Every string has the same placeholders as its English counterpart.
- Every plural entry has exactly the categories its language's rule can
  return.
- Every `text.py` function and every constant returns a non-empty string in
  every language for a representative input (no `KeyError`, no stray brace).
- For every English page there is a page in every language.
- In every translated page the fenced code blocks equal the English page's,
  in order. For `format.<lang>.md` the numeric table cells also equal the
  English ones.
- A GUI test builds the window in each language offscreen.

Staleness. `tools/translation_status.py` lists translated pages whose
`source_hash` no longer matches the English page. It is a report, not a
failing test: an English fix must not wait for eight translations. *My call.*
A new or changed application string, in contrast, must be added to all nine
catalogues in the same pull request (the key test enforces it).

### Order of work

1. Machinery with English only: `i18n.py`, `en.toml`, `text.py` and `cli.py`
   over the catalogue, language choice, tests. English output unchanged.
2. Russian end to end (glossary, catalogue, docs, site switcher) as the pilot
   that proves the templates fit a language with three plural forms. Template
   shapes are corrected here, before seven more languages copy them.
3. The other seven languages in parallel, one agent per language, each
   touching only its own files.
4. Review pass per language, then the full checks: default suite, GUI suite,
   `ruff`, `mkdocs build --strict`, self-test.

The work continues on the `docs-site` branch's line (the site it translates is
not yet on `master`).

## Left to the builder

- Key naming inside the catalogues and the exact split of today's sentences
  into templates, as long as English output is unchanged.
- How argparse's own words are translated, and how far.
- The matching mechanism for library messages that contain values.
- Exact wording of the "takes effect after restart" message and the menu.
- Whether translated pages are produced page by page or in larger batches.
