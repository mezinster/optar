---
source_hash: f5551682033e226e7bf557d24edd97efecf26b2d
---

# Розробка { #development }

Вихідний код розміщено на [github.com/mezinster/optar](https://github.com/mezinster/optar).

## Підготовка й тести { #setup-and-tests }

    python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
    .venv/bin/pytest -q
    .venv/bin/ruff check .

Жодному тесту не потрібен компілятор C.

| Команда | Що вона запускає |
|---|---|
| `.venv/bin/pytest -q` | типовий набір тестів |
| `.venv/bin/pytest -q -m gs` | контроль PDF, який створює програма; потрібен Ghostscript |
| `.venv/bin/pytest -q -m slow` | довгі тести; додайте `-n auto`, щоб використати всі ядра |
| `.venv/bin/pytest -q -m slow tests/unit/test_claims.py` | тести на змодельованих сканах, на яких ґрунтується розділ [Що показано, а що ні](evidence.md) |
| `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui` | тести застосунку |

Тестам застосунку потрібні PySide6 і pytest-qt
(`pip install -e '.[dev,gui-dev]'`); без них ці тести пропускаються.

## Що визначає формат { #what-defines-the-format }

Формат сторінки визначають [специфікація формату](format.md) і вектори
відповідності в `tests/vectors`. `tests/unit/test_spec.py` порівнює таблиці й
приклади специфікації з кодом, тож документ і код змінюють разом.

## Збирання однофайлових програм { #building-the-one-file-programs }

    .venv/bin/pyinstaller --onefile --name optar --collect-data optar packaging/entry.py
    python packaging/smoke.py dist/optar

Застосунок:

    .venv/bin/pyinstaller --onefile --name optar-gui --collect-data optar packaging/gui_entry.py

Коли надсилається тег версії, робочий процес випуску збирає обидві програми
для Linux, macOS і Windows.

## Цей сайт { #this-site }

Розділи сайту — це файли Markdown у `docs/`, які збирає MkDocs:

    .venv/bin/pip install -e '.[docs]'
    .venv/bin/mkdocs serve

Надсилання (push) у `master`, яке змінює `docs/`, публікує сайт.

## Переклади { #translations }

Застосунок і цей сайт доступні дев’ятьма мовами: `en`, `ru`, `uk`, `be`,
`pl`, `ka`, `tr`, `it`, `es`. Мова оригіналу — англійська.

**Тексти програм** містяться в `src/optar/locale/<code>.toml`, по одному файлу
на мову з однаковими ключами. Щоб додати або змінити рядок, відредагуйте
`en.toml` і всі інші каталоги в одному pull request; запис із формами множини
має категорії своєї мови (`optar.i18n.categories(code)`).
`tests/unit/test_catalogues.py` контролює, щоб каталоги були узгоджені. Щоб
побачити програму командного рядка іншою мовою, задайте `OPTAR_LANG`,
наприклад `OPTAR_LANG=ru optar --help`; у застосунку є меню вибору мови.

**Розділи сайту** — це `docs/<page>.<code>.md` поруч з англійськими
`docs/<page>.md`. Перекладений розділ має `source_hash` у вступному блоці
(front matter), англійський ідентифікатор у кожного заголовка й блоки коду,
що збігаються з англійськими. Щоб дізнатися, які розділи відстали, виконайте
`python tools/translation_status.py`. Щоб оновити застарілий розділ,
подивіться, що змінилося в англійському розділі (`git diff` відносно коміту з
його `source_hash`), відповідно змініть переклад, а тоді запишіть у
`source_hash` результат `git hash-object docs/<page>.md`. Решту контролює
`tests/unit/test_doc_translations.py`. Правила для перекладачів наведено в
`docs/superpowers/translation-brief.md`.

**Що сайт робить із перекладами** — з’ясовано за допомогою тимчасового
російського розділу й мовного запису (згодом їх видалено):

- Розділ без перекладу показується під `/ru/` англійською, а навігація
  довкола нього — перекладена (`fallback_to_default`).
- Перемикач мов з’являється в заголовку сайту, щойно з’являється друга мова.
- Пошук — це один індекс для всього сайту. Він показує результати всіх мов
  разом; неперекладений розділ індексується один раз, за своєю англійською
  адресою, а не ще раз під `/ru/`.
