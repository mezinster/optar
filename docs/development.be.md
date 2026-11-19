---
source_hash: f5551682033e226e7bf557d24edd97efecf26b2d
---

# Распрацоўка { #development }

Зыходны код знаходзіцца на [github.com/mezinster/optar](https://github.com/mezinster/optar).

## Падрыхтоўка і тэсты { #setup-and-tests }

    python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
    .venv/bin/pytest -q
    .venv/bin/ruff check .

Ніводнаму тэсту не патрэбны кампілятар C.

| Каманда | Што яна запускае |
|---|---|
| `.venv/bin/pytest -q` | асноўны набор тэстаў |
| `.venv/bin/pytest -q -m gs` | кантроль выніку ў PDF; патрэбны Ghostscript |
| `.venv/bin/pytest -q -m slow` | доўгія тэсты; дадайце `-n auto`, каб задзейнічаць усе ядры |
| `.venv/bin/pytest -q -m slow tests/unit/test_claims.py` | тэсты на імітаваных сканах, на якіх грунтуецца раздзел [«Што паказана, а што не»](evidence.md) |
| `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui` | тэсты праграмы з акном |

Тэстам праграмы з акном патрэбныя PySide6 і pytest-qt
(`pip install -e '.[dev,gui-dev]'`); без іх гэтыя тэсты прапускаюцца.

## Што вызначае фармат { #what-defines-the-format }

Фармат старонкі вызначаюць [спецыфікацыя фармату](format.md) і вектары
адпаведнасці ў `tests/vectors`. `tests/unit/test_spec.py` параўноўвае табліцы
і прыклады са спецыфікацыі з кодам, таму дакумент і код мяняюцца разам.

## Зборка праграм з аднаго файла { #building-the-one-file-programs }

    .venv/bin/pyinstaller --onefile --name optar --collect-data optar packaging/entry.py
    python packaging/smoke.py dist/optar

Праграма з акном:

    .venv/bin/pyinstaller --onefile --name optar-gui --collect-data optar packaging/gui_entry.py

Працоўны працэс выпуску збірае абедзве праграмы для Linux, macOS і Windows,
калі адпраўляецца тэг версіі.

## Гэты сайт { #this-site }

Раздзелы сайта — гэта файлы Markdown у `docs/`, сабраныя з дапамогай MkDocs:

    .venv/bin/pip install -e '.[docs]'
    .venv/bin/mkdocs serve

Пасля push у `master`, які змяняе `docs/`, сайт публікуецца.

## Пераклады { #translations }

Праграма з акном і гэты сайт даступныя на дзевяці мовах: `en`, `ru`, `uk`,
`be`, `pl`, `ka`, `tr`, `it`, `es`. Крыніца ўсяго — англійская.

**Тэксты праграм** знаходзяцца ў `src/optar/locale/<code>.toml`, па адным
файле на мову з аднолькавымі ключамі. Каб дадаць або змяніць радок, змяніце
`en.toml` і ўсе астатнія каталогі ў адным pull request; запіс з формамі множнага
ліку мае катэгорыі сваёй мовы (`optar.i18n.categories(code)`).
`tests/unit/test_catalogues.py` сочыць, каб каталогі адпавядалі адзін
аднаму. Каб убачыць праграму каманднага радка на іншай мове, задайце
`OPTAR_LANG`, напрыклад `OPTAR_LANG=ru optar --help`; у праграмы з акном
ёсць меню мовы.

**Раздзелы сайта** — гэта `docs/<page>.<code>.md` побач з англійскімі
`docs/<page>.md`. У перакладзеным раздзеле ёсць `source_hash` у пачатковым
блоку метаданых, англійскі id у кожным загалоўку і блокі кода, роўныя
англійскім. Каб убачыць, якія раздзелы адсталі, выканайце
`python tools/translation_status.py`. Каб абнавіць састарэлы раздзел,
прачытайце, што змянілася ў англійскім раздзеле (`git diff` адносна каміта
з яго `source_hash`), абнавіце пераклад адпаведна і задайце `source_hash`
роўным `git hash-object docs/<page>.md`. Астатняе кантралюе
`tests/unit/test_doc_translations.py`. Правілы для перакладчыкаў — у
`docs/superpowers/translation-brief.md`.

**Што сайт робіць з перакладамі** — высветлена з дапамогай часовага рускага
раздзела і моўнага запісу (потым выдаленых):

- Раздзел без перакладу паказваецца па-англійску пад `/ru/`, а навігацыя
  вакол яго — перакладзеная (`fallback_to_default`).
- Пераключальнік моў з'яўляецца ў шапцы, як толькі ёсць другая мова.
- Пошук — адзін індэкс на ўвесь сайт. Ён паказвае вынікі на ўсіх мовах
  разам; неперакладзены раздзел індэксуецца адзін раз, пад яго англійскім
  адрасам, а не яшчэ раз пад `/ru/`.
