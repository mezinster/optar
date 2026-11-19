---
source_hash: f5551682033e226e7bf557d24edd97efecf26b2d
---

# Sviluppo { #development }

I sorgenti sono su [github.com/mezinster/optar](https://github.com/mezinster/optar).

## Configurazione e test { #setup-and-tests }

    python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
    .venv/bin/pytest -q
    .venv/bin/ruff check .

Nessun test richiede un compilatore C.

| Comando | Che cosa esegue |
|---|---|
| `.venv/bin/pytest -q` | la serie di test predefinita |
| `.venv/bin/pytest -q -m gs` | i controlli dell'output PDF; richiede Ghostscript |
| `.venv/bin/pytest -q -m slow` | i test lunghi; aggiungi `-n auto` per usare tutti i core |
| `.venv/bin/pytest -q -m slow tests/unit/test_claims.py` | i test su scansioni simulate alla base di [Che cosa è stato mostrato e che cosa no](evidence.md) |
| `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui` | i test dell'applicazione |

I test dell'applicazione richiedono PySide6 e pytest-qt
(`pip install -e '.[dev,gui-dev]'`) e senza di essi vengono saltati.

## Che cosa definisce il formato { #what-defines-the-format }

Il formato di pagina è definito dalla [specifica del formato](format.md) e
dai vettori di conformità in `tests/vectors`. `tests/unit/test_spec.py`
confronta le tabelle e gli esempi della specifica con il codice, quindi il
documento e il codice si modificano insieme.

## Compilare i programmi in un unico file { #building-the-one-file-programs }

    .venv/bin/pyinstaller --onefile --name optar --collect-data optar packaging/entry.py
    python packaging/smoke.py dist/optar

L'applicazione:

    .venv/bin/pyinstaller --onefile --name optar-gui --collect-data optar packaging/gui_entry.py

Il workflow di rilascio compila entrambi per Linux, macOS e Windows quando
viene inviato un tag di versione.

## Questo sito { #this-site }

Le sezioni sono i file Markdown in `docs/`, generati con MkDocs:

    .venv/bin/pip install -e '.[docs]'
    .venv/bin/mkdocs serve

Un push su `master` che modifica `docs/` pubblica il sito.

## Traduzioni { #translations }

L'applicazione e questo sito sono disponibili in nove lingue: `en`, `ru`,
`uk`, `be`, `pl`, `ka`, `tr`, `it`, `es`. L'inglese è la fonte.

**I testi dei programmi** sono in `src/optar/locale/<code>.toml`, un file per
lingua con le stesse chiavi. Per aggiungere o modificare una stringa, modifica
`en.toml` e tutti gli altri cataloghi nella stessa pull request; una voce con
forme plurali ha le categorie della sua lingua
(`optar.i18n.categories(code)`). `tests/unit/test_catalogues.py` controlla che
i cataloghi siano coerenti. Per vedere il programma a riga di comando in
un'altra lingua imposta `OPTAR_LANG`, per esempio `OPTAR_LANG=ru optar --help`;
l'applicazione ha un menu della lingua.

**Le sezioni** sono `docs/<page>.<code>.md` accanto alle `docs/<page>.md`
inglesi. Una sezione tradotta ha `source_hash` nel front matter, l'id inglese
su ogni titolo e blocchi di codice identici all'inglese. Per vedere quali
sezioni sono rimaste indietro, esegui `python tools/translation_status.py`.
Per aggiornare una sezione non più attuale, leggi che cosa è cambiato nella
sezione inglese (`git diff` rispetto al commit del suo `source_hash`), adegua
la traduzione, poi imposta `source_hash` a `git hash-object docs/<page>.md`.
`tests/unit/test_doc_translations.py` controlla il resto. Le regole per chi
traduce sono in `docs/superpowers/translation-brief.md`.

**Che cosa ne fa il sito**, scoperto con una sezione e una voce di lingua in
russo usa e getta (poi rimosse):

- Una sezione senza traduzione compare in inglese sotto `/ru/`, con la
  navigazione tradotta attorno (`fallback_to_default`).
- Il selettore della lingua compare nell'intestazione quando c'è una seconda
  lingua.
- La ricerca è un unico indice per tutto il sito. Elenca insieme i risultati
  di tutte le lingue; una sezione non tradotta viene indicizzata una sola
  volta, al suo indirizzo inglese, e non di nuovo sotto `/ru/`.
