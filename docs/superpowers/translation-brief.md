# Translation brief

This is the one document every agent that translates or reviews optar in a
new language is given, together with that language's glossary. Read all of it
before you start. The languages and their codes are: `en` English, `ru`
Russian, `uk` Ukrainian, `be` Belarusian, `pl` Polish, `ka` Georgian, `tr`
Turkish, `it` Italian, `es` Spanish. English is the source of everything.

You translate two things: the **catalogue** (`src/optar/locale/<code>.toml`,
the words of the application and the command-line program) and the **pages**
(`docs/<page>.<code>.md`, the user documentation). You also write the
**glossary** (`docs/superpowers/glossaries/<code>.md`) first.

## Who reads the result

Ordinary people who print files on a laser printer and scan them at home.
They are not programmers. Write what a careful native speaker would write
for them:

- Plain, direct words. Short sentences where the English has short sentences.
- The form of address that is normal for software in your language (for
  example the polite "you" where that is the norm). Use it everywhere, the
  same way.
- No literal calques of English sentence shapes. Say it the way your language
  says it.
- The same strength of claim as the English. "Verified" is never softened
  ("probably fine") and never strengthened ("guaranteed"). A warning stays as
  firm as it is in English; a statement that something was not shown stays as
  modest as it is.

## 1. The glossary comes first

Before translating anything else, write `docs/superpowers/glossaries/<code>.md`.
It chooses one word or short phrase in your language for each of these terms,
with a line or two of reasoning for each (why this word, which others were
rejected):

dot, block, protection, fingerprint, tag, label, spare, scan, printout, page,
slower reader, self-identifying page, verified, repaired, lost, damaged,
missing.

Read the English pages (`docs/*.md`, especially `index.md`,
`put-on-paper.md`, `read-from-paper.md`, `identification.md`) to see how each
term is used before you choose. "Page" in particular means a sheet of paper
carrying dots, not a web page. Once chosen, a term is translated the same way
in the catalogue and in every page. Never use two words for one term, and
never one word for two terms.

The glossary also has a section **Site navigation** that gives your
translation of:

- the eleven navigation titles in `mkdocs.yml` under `nav:` (Home, Install,
  Put a file on paper, Read it back, Scans that are too coarse, Command line,
  How a page identifies itself, What has and has not been shown, Format
  specification, Development, History);
- the three section titles (Using optar, Reference, Project);
- the site description (`site_description:` at the top of `mkdocs.yml`).

The site build reads these from the language's entry in `mkdocs.yml`
(`nav_translations`, keyed by the English title exactly as written, and
`site_description`). The controller copies them from your glossary; you do not
edit `mkdocs.yml`.

## 2. The catalogue

Start from a copy of `src/optar/locale/en.toml` saved as
`src/optar/locale/<code>.toml`. Then:

- Keep every key and every table. Translate every value. Do not add or remove
  keys, and do not reorder them.
- Keep every `{placeholder}` name exactly as in English. A placeholder is a
  name in braces such as `{name}` or `{n}`. You may move it to wherever your
  grammar needs it. Every placeholder the English uses must appear in your
  value, with the one exception below for plural forms. Do not use any other
  braces; a literal brace is not allowed in a value.
- Plural entries are tables with the keys `one`, `few`, `many` or `other`.
  Give each plural entry **exactly** the categories your language has, which
  are the ones `optar.i18n.categories(code)` returns:
    - `en`, `it`, `es`: `one`, `other`
    - `ru`, `uk`, `be`, `pl`: `one`, `few`, `many`
    - `tr`, `ka`: `other` only
  `{n}` is the number already written with its thousands separator. Every
  form contains `{n}` exactly when the English forms do, and uses no
  placeholder the English forms do not use (a form may use fewer of them).
  Check the numbers: in Russian-type languages `one` is 1, 21, 101 (not 11); `few`
  is 2 to 4, 22 to 24 (not 12 to 14); `many` is everything else including 0,
  5 to 20 and 11 to 14. In Polish `one` is exactly 1, `few` is as in Russian,
  `many` is the rest.
- `[language].name` is the name of the language in its own script, for example
  `Русский`, `Polski`, `ქართული`, `Türkçe`.
- `[format].group` is the thousands separator. For `ru`, `uk`, `be`, `pl`,
  `ka` it is a no-break space (U+00A0). For `it`, `es`, `tr` it is `.`.
- Never translate option names (`--protect`), command names, metavariables,
  file names, file extensions (`.pdf`, `.png`) or the word `optar`. They are
  typed by the user and stay English, also inside your sentences.
- A value is shown to the user as plain text. Keep it plain: no Markdown, no
  HTML.
- Keep keyboard accelerators and similar marks (such as `&`) as the English
  has them, if any.
- Strings that appear on a button or in a menu must stay short. Do not make a
  label much longer than the English.

## 3. The pages

For each English page `docs/<page>.md` write `docs/<page>.<code>.md`. There
are eleven pages. Rules:

- **Front matter.** The file opens with
  ```
  ---
  source_hash: <40 hex digits>
  ---
  ```
  where the hash is the output of `git hash-object docs/<page>.md` run on the
  English page you translated from. It lets `tools/translation_status.py`
  tell when the English page has moved on.
- **Headings.** Every heading ends with `{ #<english-anchor> }`, where the id
  is the id that heading has on the English page (the heading text,
  lower-cased, spaces turned into hyphens, punctuation dropped; a repeated
  heading gets `_1`, `_2`). Example: the English `## Put a file on paper`
  becomes `## <your translation> { #put-a-file-on-paper }`. The number and
  order of headings equals the English page. This keeps links from other
  pages and from outside working.
- **Code blocks.** Fenced and indented code blocks, commands and their output
  are copied from the English page unchanged, byte for byte. Do not translate
  comments in them.
- **Links.** Keep every link target as it is. Translate only the link text.
  A relative link to another page (`install.md`) stays `install.md`; the
  build sends it to the same language's page.
- **Images.** Image paths stay unchanged. Translate the alt text. The pictures
  themselves stay English.
- **Tables.** Same columns and rows. Translate words; leave numbers, hex
  values, constants and code in cells unchanged.
- **Admonitions** (`!!! note "..."`): keep the type word (`note`, `warning`),
  translate the title and body.
- Names, numbers, versions, option names and file names are not translated.
- Keep the English page's order and paragraph breaks, so a reviewer can read
  the two side by side.

### The format page

`docs/format.<code>.md` is special. The English `docs/format.md` is the
normative page: it, with the vectors in `tests/vectors`, defines the format.
The translation opens with a first paragraph, right after the title, saying so in
your language and linking to the English page. A relative link `format.md`
would lead to the translated page itself, so use the full address
`https://mezinster.github.io/optar/format/`. It
then keeps **every number, constant, table cell of numbers and worked example
unchanged**. Translate the prose around them only. When in doubt about a
technical sentence, translate less, not more.

## 4. Self-check

Before you finish, run, with your language's code in place of the tests'
parametrisation (they pick up your files by themselves):

    .venv/bin/pytest -q tests/unit/test_catalogues.py tests/unit/test_doc_translations.py

They must pass for your language. They check that your catalogue has the
same keys and placeholders as English and exactly the plural categories of the
language, has no empty strings or stray braces, has a language name and a
valid thousands separator, and that every text function of the window answers;
and that every page exists, has `source_hash`, has the English heading ids in
order, has code blocks equal to English, has links that point at pages and ids
that exist, and (for the format page) says English is normative and keeps the
numbers. Do not edit the tests or the English files to make them pass. If a
test seems wrong, say so in your hand-back.

## 5. What to hand back

- The files: the glossary, `src/optar/locale/<code>.toml`, and the eleven
  `docs/<page>.<code>.md`.
- A short list of English strings whose template shape did not fit your
  language's grammar (for example a sentence built from a counted noun and a
  verb that must agree, or a placeholder that needs a case ending the
  template cannot give), with the key and what you did instead.

Do not touch any file other than these. Do not change the English.
