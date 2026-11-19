---
source_hash: f5551682033e226e7bf557d24edd97efecf26b2d
---

# Rozwój { #development }

Kod źródłowy znajduje się w [github.com/mezinster/optar](https://github.com/mezinster/optar).

## Przygotowanie i testy { #setup-and-tests }

    python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
    .venv/bin/pytest -q
    .venv/bin/ruff check .

Żaden test nie wymaga kompilatora C.

| Polecenie | Co uruchamia |
|---|---|
| `.venv/bin/pytest -q` | domyślny zestaw testów |
| `.venv/bin/pytest -q -m gs` | sprawdzenie wyniku w PDF; wymaga Ghostscript |
| `.venv/bin/pytest -q -m slow` | długie testy; dodaj `-n auto`, by użyć wszystkich rdzeni |
| `.venv/bin/pytest -q -m slow tests/unit/test_claims.py` | testy na symulowanych skanach, na których opiera się rozdział [Co wykazano, a czego nie](evidence.md) |
| `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui` | testy aplikacji |

Testy aplikacji wymagają PySide6 i pytest-qt
(`pip install -e '.[dev,gui-dev]'`), a bez nich są pomijane.

## Co definiuje format { #what-defines-the-format }

Format strony definiują [specyfikacja formatu](format.md) i wektory zgodności
w `tests/vectors`. `tests/unit/test_spec.py` porównuje tabele i przykłady
specyfikacji z kodem, więc dokument i kod zmienia się razem.

## Budowanie programów jednoplikowych { #building-the-one-file-programs }

    .venv/bin/pyinstaller --onefile --name optar --collect-data optar packaging/entry.py
    python packaging/smoke.py dist/optar

Aplikacja:

    .venv/bin/pyinstaller --onefile --name optar-gui --collect-data optar packaging/gui_entry.py

Proces wydania (release workflow) buduje oba programy dla systemów Linux,
macOS i Windows, gdy zostanie wypchnięty tag wersji.

## Ta witryna { #this-site }

Rozdziały to pliki Markdown w `docs/`, budowane za pomocą MkDocs:

    .venv/bin/pip install -e '.[docs]'
    .venv/bin/mkdocs serve

Wypchnięcie do `master` zmian w `docs/` publikuje witrynę.

## Tłumaczenia { #translations }

Aplikacja i ta witryna są dostępne w dziewięciu językach: `en`, `ru`, `uk`,
`be`, `pl`, `ka`, `tr`, `it`, `es`. Źródłem jest angielski.

**Teksty programów** znajdują się w `src/optar/locale/<code>.toml`, po
jednym pliku na język, z tymi samymi kluczami. Aby dodać lub zmienić tekst,
zmień `en.toml` i wszystkie pozostałe katalogi w tym samym pull requeście;
wpis z liczbą mnogą ma kategorie swojego języka
(`optar.i18n.categories(code)`). `tests/unit/test_catalogues.py` sprawdza,
czy katalogi są zgodne. Aby zobaczyć program wiersza poleceń w innym języku,
ustaw `OPTAR_LANG`, na przykład `OPTAR_LANG=ru optar --help`; aplikacja ma
menu wyboru języka.

**Rozdziały** to pliki `docs/<page>.<code>.md` obok angielskich
`docs/<page>.md`. Przetłumaczony rozdział ma `source_hash` w bloku front
matter, angielski identyfikator przy każdym nagłówku i bloki kodu takie same
jak w wersji angielskiej. Aby zobaczyć, które rozdziały są nieaktualne,
uruchom `python tools/translation_status.py`. Aby odświeżyć nieaktualny
rozdział, przeczytaj, co zmieniło się w rozdziale angielskim (`git diff`
względem commita z jego `source_hash`), dostosuj tłumaczenie, a potem ustaw
`source_hash` na wynik `git hash-object docs/<page>.md`.
`tests/unit/test_doc_translations.py` sprawdza resztę. Zasady dla tłumaczy
są w `docs/superpowers/translation-brief.md`.

**Co witryna z nimi robi** – ustalone za pomocą próbnego rosyjskiego
rozdziału i wpisu języka (potem usuniętych):

- Rozdział bez tłumaczenia pojawia się po angielsku pod `/ru/`, otoczony
  przetłumaczoną nawigacją (`fallback_to_default`).
- Przełącznik języków pojawia się w nagłówku witryny, gdy jest drugi język.
- Wyszukiwanie ma jeden indeks dla całej witryny. Wyniki ze wszystkich
  języków pokazuje razem; nieprzetłumaczony rozdział jest indeksowany raz,
  pod swoim angielskim adresem, a nie ponownie pod `/ru/`.
