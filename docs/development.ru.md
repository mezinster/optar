---
source_hash: f5551682033e226e7bf557d24edd97efecf26b2d
---

# Разработка { #development }

Исходный код находится на [github.com/mezinster/optar](https://github.com/mezinster/optar).

## Подготовка и тесты { #setup-and-tests }

    python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
    .venv/bin/pytest -q
    .venv/bin/ruff check .

Ни одному тесту не нужен компилятор C.

| Команда | Что она запускает |
|---|---|
| `.venv/bin/pytest -q` | основной набор тестов |
| `.venv/bin/pytest -q -m gs` | тесты вывода PDF; нужен Ghostscript |
| `.venv/bin/pytest -q -m slow` | долгие тесты; добавьте `-n auto`, чтобы задействовать все ядра |
| `.venv/bin/pytest -q -m slow tests/unit/test_claims.py` | тесты на имитированных сканах, на которых основан раздел [«Что показано, а что нет»](evidence.md) |
| `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui` | тесты приложения |

Тестам приложения нужны PySide6 и pytest-qt
(`pip install -e '.[dev,gui-dev]'`); без них эти тесты пропускаются.

## Что определяет формат { #what-defines-the-format }

Формат страниц определяют [спецификация формата](format.md) и векторы
соответствия в `tests/vectors`. `tests/unit/test_spec.py` сравнивает таблицы
и примеры спецификации с кодом, поэтому документ и код меняются вместе.

## Сборка однофайловых программ { #building-the-one-file-programs }

    .venv/bin/pyinstaller --onefile --name optar --collect-data optar packaging/entry.py
    python packaging/smoke.py dist/optar

Приложение:

    .venv/bin/pyinstaller --onefile --name optar-gui --collect-data optar packaging/gui_entry.py

Когда в репозиторий отправляется тег версии, рабочий процесс выпуска собирает
обе программы для Linux, macOS и Windows.

## Этот сайт { #this-site }

Разделы сайта — это файлы Markdown в `docs/`, которые собираются с помощью
MkDocs:

    .venv/bin/pip install -e '.[docs]'
    .venv/bin/mkdocs serve

Отправка в `master`, которая меняет `docs/`, публикует сайт.

## Переводы { #translations }

Приложение и этот сайт доступны на девяти языках: `en`, `ru`, `uk`, `be`,
`pl`, `ka`, `tr`, `it`, `es`. Исходный язык — английский.

**Тексты программ** находятся в `src/optar/locale/<code>.toml`, по одному
файлу на язык с одинаковыми ключами. Чтобы добавить или изменить строку,
отредактируйте `en.toml` и все остальные каталоги в одном и том же pull
request; у записи с формами множественного числа те категории, которые есть в
её языке (`optar.i18n.categories(code)`). `tests/unit/test_catalogues.py`
следит за тем, чтобы каталоги были согласованы. Чтобы увидеть программу
командной строки на другом языке, задайте `OPTAR_LANG`, например
`OPTAR_LANG=ru optar --help`; в приложении есть меню выбора языка.

**Разделы сайта** — это `docs/<page>.<code>.md` рядом с английскими
`docs/<page>.md`. В переведённом разделе есть `source_hash` в front matter,
английский идентификатор у каждого заголовка и блоки кода, совпадающие с
английскими. Чтобы узнать, какие разделы отстали, запустите
`python tools/translation_status.py`. Чтобы обновить устаревший раздел,
посмотрите, что изменилось в английском разделе (`git diff` относительно
коммита из его `source_hash`), исправьте перевод соответственно, а затем
запишите в `source_hash` результат `git hash-object docs/<page>.md`.
Остальное контролирует `tests/unit/test_doc_translations.py`. Правила для
переводчиков — в `docs/superpowers/translation-brief.md`.

**Что сайт делает с переводами** — выяснено с помощью временного русского
раздела и языковой записи (потом удалённых):

- Раздел без перевода показывается под `/ru/` на английском, а навигация
  вокруг него — переведённая (`fallback_to_default`).
- Переключатель языков появляется в шапке, как только появляется второй
  язык.
- Поиск — один индекс на весь сайт. Он показывает результаты всех языков
  вместе; непереведённый раздел индексируется один раз, по своему английскому
  адресу, а не ещё раз под `/ru/`.
