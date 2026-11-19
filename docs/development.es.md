---
source_hash: f5551682033e226e7bf557d24edd97efecf26b2d
---

# Desarrollo { #development }

El código fuente está en [github.com/mezinster/optar](https://github.com/mezinster/optar).

## Preparación y pruebas { #setup-and-tests }

    python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
    .venv/bin/pytest -q
    .venv/bin/ruff check .

Ninguna prueba necesita un compilador de C.

| Comando | Qué ejecuta |
|---|---|
| `.venv/bin/pytest -q` | el conjunto de pruebas predeterminado |
| `.venv/bin/pytest -q -m gs` | las comprobaciones de la salida en PDF; necesita Ghostscript |
| `.venv/bin/pytest -q -m slow` | las pruebas largas; añada `-n auto` para usar todos los núcleos |
| `.venv/bin/pytest -q -m slow tests/unit/test_claims.py` | las pruebas con escaneos simulados en las que se basa [Qué muestran las pruebas y qué no](evidence.md) |
| `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui` | las pruebas de la aplicación |

Las pruebas de la aplicación necesitan PySide6 y pytest-qt
(`pip install -e '.[dev,gui-dev]'`) y se omiten si no están.

## Qué define el formato { #what-defines-the-format }

El formato de página lo definen la [especificación del formato](format.md) y
los vectores de conformidad de `tests/vectors`. `tests/unit/test_spec.py`
compara las tablas y los ejemplos de la especificación con el código, así que
el documento y el código se cambian juntos.

## Compilar los programas de un solo archivo { #building-the-one-file-programs }

    .venv/bin/pyinstaller --onefile --name optar --collect-data optar packaging/entry.py
    python packaging/smoke.py dist/optar

La aplicación:

    .venv/bin/pyinstaller --onefile --name optar-gui --collect-data optar packaging/gui_entry.py

El flujo de trabajo de publicación compila ambos para Linux, macOS y Windows
cuando se sube una etiqueta de versión.

## Este sitio { #this-site }

Las secciones son los archivos Markdown de `docs/`, compilados con MkDocs:

    .venv/bin/pip install -e '.[docs]'
    .venv/bin/mkdocs serve

Un push a `master` que cambia `docs/` publica el sitio.

## Traducciones { #translations }

La aplicación y este sitio están disponibles en nueve idiomas: `en`, `ru`,
`uk`, `be`, `pl`, `ka`, `tr`, `it`, `es`. El inglés es el original.

**Los textos de los programas** están en `src/optar/locale/<code>.toml`, un
archivo por idioma con las mismas claves. Para añadir o cambiar un texto,
edite `en.toml` y todos los demás catálogos en el mismo pull request; una
entrada con plural tiene las categorías de su idioma
(`optar.i18n.categories(code)`). `tests/unit/test_catalogues.py` comprueba que
los catálogos concuerdan. Para ver el programa de línea de comandos en otro
idioma, defina `OPTAR_LANG`, por ejemplo `OPTAR_LANG=ru optar --help`; la
aplicación tiene un menú de idioma.

**Las secciones** son `docs/<page>.<code>.md`, junto a la inglesa
`docs/<page>.md`. Una sección traducida tiene `source_hash` en su front
matter, el id inglés en cada encabezado y bloques de código iguales a los del
inglés. Para ver qué secciones están atrasadas, ejecute
`python tools/translation_status.py`. Para actualizar una sección atrasada,
lea lo que cambió en la sección inglesa (`git diff` contra el commit de su
`source_hash`), cambie la traducción en consecuencia y luego ponga en
`source_hash` el resultado de `git hash-object docs/<page>.md`.
`tests/unit/test_doc_translations.py` comprueba el resto. Las reglas para los
traductores están en `docs/superpowers/translation-brief.md`.

**Lo que hace el sitio con ellas**, averiguado con una sección rusa y una
entrada de idioma provisionales (ya eliminadas):

- Una sección sin traducción aparece en inglés bajo `/ru/`, con la navegación
  traducida a su alrededor (`fallback_to_default`).
- El selector de idioma aparece en la cabecera en cuanto hay un segundo
  idioma.
- La búsqueda es un único índice para todo el sitio. Muestra juntos los
  resultados de todos los idiomas; una sección sin traducir se indexa una sola
  vez, con su dirección inglesa, no otra vez bajo `/ru/`.
