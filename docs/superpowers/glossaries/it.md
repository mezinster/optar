# Italian glossary (`it`)

Working paper for the Italian translation of optar: the catalogue
`src/optar/locale/it.toml` and the pages `docs/<page>.it.md`. It follows
section 1 of `docs/superpowers/translation-brief.md`. The explanations are in
English; the terms are Italian. Once a term is chosen here it is used the same
way in the window, the command line and every page. The translation was made
from English; the Russian glossary was used only as a model of shape.

## General conventions

- **Address.** Informal «tu», as in current Italian software (Apple, Google,
  Microsoft, Mozilla all address the user with «tu»). Used everywhere, also in
  the pages: «Scansiona la pagina», «Se chiudi ora…», «Vuoi attendere…?».
  Never «Lei», never the plural «voi».
- **Buttons, menu entries, tab names and dialog titles** use the «tu»
  imperative, as Italian software does: «Salva file…», «Aggiungi scansioni…»,
  «Sostituisci scansione…», «Scrivi su carta», «Scegli un file da scrivere su
  carta». A dialog title that asks a yes/no question uses the infinitive, the
  usual Italian form: «Salvare comunque?».
- **Instructions** in messages and pages: «tu» imperative («Scansiona di nuovo
  la pagina 3 e ripeti la decodifica»).
- **Command-line option help** (`--help`): third-person indicative, as the
  Italian translation of Python's argparse writes its own lines («mostra questo
  messaggio di aiuto ed esce»): «codifica un file in pagine da stampare»,
  «non aggiunge…». Option descriptions that name a thing are noun phrases
  («formato della carta (predefinito: a4)»).
- **Status words** in rows and in the bottom bar are past participles or
  adjectives that agree with the page («Riparata», «Danneggiata», «Mancante»,
  «Illeggibile»), or invariant label forms with a colon («Pagine buone: 4 su
  6», «Scansioni lette: 3 su 6»), never full sentences. A phrase the window
  only ever shows after « · » in the bottom bar starts lower-case, as Italian
  does mid-line («… · scansioni lette: 3 su 6», «… · stampato senza
  protezione…»); the row-state labels after «Pagina 3 · » stay capitalised,
  as labels, and so does «Scansioni» after «Elaborazione…».
- **Headings of pages and site navigation** use the infinitive or a noun, as
  Italian manuals do («Scrivere un file su carta», «Installazione»).
- **Articles before a number or a placeholder.** Italian elides the article
  before a number that starts with a vowel sound («l'8%», «l'11%», «gli 11»,
  but «il 57%», «i 12»). A template cannot know which, so the catalogue never
  puts an article directly before a number placeholder: it puts a noun in
  between («la pagina {page}», «il limite di {limit}») or uses a label form
  with a colon («capacità di riparazione usata nella zona peggiore: {percent}%»).
  Plural «le» and «delle» before a number are always safe, but «tutte le
  {n} pagine» is avoided: with 2 Italian says «tutte e due», so the
  catalogue writes «Lette tutte le pagine ({n})». A file name (`{name}`, `{path}`) is never the bare subject of an
  agreeing participle: a noun stands before it («La scansione {name} non è
  stata usata…», «File {name} creato»).
- **Typography.** Quotes «caporali» for quoting interface wording and words
  in running text, as Italian typesetting does («Salva file…»); nested quotes
  “alte”. Parenthetical dash: en dash with spaces « – ». Number ranges: en
  dash without spaces («pagine 2–4»), in `gui.list.range` and every
  `gui.run.*.range`. Ellipsis «…» as one character, as in English. Accented
  capital «È» is written as such, never «E'».
- **Numbers.** `[format].group` is «.» and `[format].decimal` is «,». Outside
  code blocks, in prose and in table cells alike: «199.773», «200.000»,
  «2,5», «0,1%». Version numbers (0.2.0) and anything typed by the user stay
  as in English, and so does every number of `format.it.md`. Percent is
  written without a space («57%», «14%»), as most Italian software and
  newspapers do. «×» for dimensions in messages («100 × 141 pixel»).
- **optar** is always lower-case, also at the start of a sentence, and takes
  the masculine article when one is needed («l'optar originale»).
- **«Pagina»** is a sheet of paper carrying dots. A page of this website is
  a «sezione», never a «pagina» («vedi la sezione “Come si identifica una
  pagina”»). The project's web page on GitHub is likewise «la sezione Releases».
- **Units.** «byte» and «pixel» are invariable in Italian («1 byte», «5
  byte», «1 pixel», «3 pixel»), which spares agreement in the `err.*` texts.
  «dpi» stays «dpi»; «pt» (points) stays «pt»; «pag.» is the standard
  abbreviation for page(s) when a raw number stands before it.

## Terms

### The brief's required terms

| English | Italian | Notes |
|---|---|---|
| dot | punto (pl. punti) | Masculine. "Data dot" «punto di dati», "printer dot" «punto della stampante». Not «pixel»: pixels are separate (see the spec terms). |
| dot size | dimensione dei punti | Feminine. The window's field is the short «Punti:», so that the plural size names agree with it («Punti: Grossi (scansione a 300 dpi)»). |
| block | blocco (pl. blocchi) | Masculine. One error-correction unit. Participles after a count of blocks are masculine: «3 riparati · 1 perso». |
| protection | protezione | Field «Protezione:», levels «Nessuna», «Standard», «Alta». Prefer «con protezione», «senza protezione», «una stampa con protezione»; avoid the adjective «protetto» for printouts and documents: «stampa protetta» is the name of printer «secure print» (PIN-locked printing) and suggests a password. Rejected: «ridondanza» (correct but technical). |
| fingerprint | impronta | Feminine. The usual Italian word for a key or hash fingerprint («impronta SHA-256», «impronta digitale» of a certificate). Short «impronta»; «impronta del file» where needed. Rejected: «hash» (names the method), «checksum» / «somma di controllo» (a different, weaker thing). |
| tag | contrassegno | Masculine. The bracketed `[SIZE:FINGERPRINT:CC]` at the start of a label. «etichetta con contrassegno», «senza contrassegno» (untagged), «nessun contrassegno». Rejected: «tag» (reads as an HTML tag or hashtag), «etichetta» (taken by "label"), «marcatura» (sounds like a CE marking). |
| label | etichetta | Feminine. The line printed at the bottom of every page. "Label band" «banda dell'etichetta», "label strip" «striscia dell'etichetta» (spec). Rejected: «didascalia» (a caption of a picture), «dicitura» (correct but rare in software). |
| spare | scansione di riserva | Row title «Di riserva», detail tag «di riserva». Rejected: «doppione» (sounds like a mistake), «copia di backup» (suggests a deliberate backup). |
| scan (noun) | scansione (pl. scansioni) | Feminine. The usual word in Italian scanning software. Participles about a scan are feminine («scansione non identificata»). |
| scan (verb) | scansionare | "Rescan" «scansionare di nuovo» («scansiona di nuovo la pagina»); «riscansionare» is avoided as colloquial. "Scan at 600 dpi" «scansiona a 600 dpi». |
| printout | stampa | Feminine. The pages as printed, the physical set: «un'altra stampa», «stampa compatibile». Kept apart from «documento» (the logical set of pages carrying one file). The act of printing is «stampare» / «la stampa» only where it cannot be confused («Come stampare»); "printer" is «stampante». |
| document | documento | A set of pages that carries one file. |
| page | pagina (pl. pagine) | Feminine. Participles about pages are feminine: «1 riparata», «2 danneggiate». Not «foglio»: a sheet has two sides; an optar page is one printed side. See the general convention on «sezione». |
| slower reader | metodo di lettura lento (short: metodo lento) | "The ordinary reader" is «metodo di lettura normale» / «metodo normale». First mention on a page: «un secondo metodo di lettura, più lento». The English comparative is dropped in the name: «il metodo più lento» would read as "the slowest method". Rejected: «lettore» (a device: «lettore CD», «lettore di schede»), «modalità lenta» (a mode the user picks; this runs by itself). "Read by the slower reader" «letta con il metodo lento». "Slower reader for coarse scans" «metodo lento per le scansioni a bassa risoluzione». |
| self-identifying page | pagina autoidentificante (pl. pagine autoidentificanti) | A regular Italian technical formation (like «autoesplicativo»), built on «identificare», the verb the window uses for scans («scansione non identificata»). On first mention in a page add the gloss «(pagine che dicono da sole a quale documento appartengono e che numero hanno)». Rejected: «pagina autodescrittiva» (self-describing, a different idea). |
| verified | verificato (file verificato) | Always means: the recovered file matched its fingerprint. The root «verific-» is **reserved** for verified / verification: "not verified" «non verificato», "did not verify" «non ha superato la verifica», "cannot be verified" «non verificabile», "once the document is verified" «quando il documento sarà verificato». Checking the fingerprint is «controllo dell'impronta» (see "check"). Rejected: «confermato» (vaguer), «convalidato» (sounds administrative), anything with «garantito» (stronger). |
| repaired | riparato (repair: riparare, riparazione) | The protection or the page's error correction fixed damaged data: «6.912 byte riparati», «Riparata · 3». Exception that Italian forces: a *missing* page cannot be «riparata»; for a missing page "repaired from the others" is «ricostruita dalle altre» (the verb of "rebuild"). |
| lost | perso (persa, persi, perse) | Blocks that could not be repaired («Danneggiata · 3 persi»), and a whole page lost from the printout («si può perdere 1 pagina su 12»). Distinct from "missing". «perduto» is literary. |
| damaged | danneggiato / danneggiata | Page state «Danneggiata». "Damage" «danni» (plural, as Italian says of stains and tears). |
| missing | mancante; manca / mancano | A page of which no scan has been added. State «Mancante»; in a sentence «manca la pagina 3», «mancano le pagine 2 e 3». Not «persa»: the paper may exist, only the scan is missing. |

### The window's vocabulary

| English | Italian | Notes |
|---|---|---|
| good (page state) | buona | Agrees with «pagina»: row «Buona»; in the bar the invariant label «Pagine buone: {good} su {n}». Rejected: «integra» (the docs say of a *repaired* page that its data is intact, «i dati sono integri», so it would blur Good and Repaired), «in ordine» (also means "in sequence", confusing for pages), «OK». |
| not readable, unreadable | illeggibile (pl. illeggibili) | Invariable in gender. Row «Illeggibile», list section «Illeggibili»; "could not be read" «non è stato possibile leggere…». |
| recoverable (document state) | recuperabile | Used for both states whose English label is "Recoverable". |
| recovered | recuperato | The file obtained from the pages: «file recuperato», «File recuperato e verificato». "What was recovered" «quanto è stato recuperato», «ciò che è stato possibile recuperare». |
| rebuild (a lost page) | ricostruire | «ricostruita dalle altre». |
| corrected (dots, symbols, bits) | corretto | Kept apart from "repaired": «265.112 punti corretti · 6.912 byte riparati dalla protezione del documento». "Error correction" «correzione degli errori», "error-correcting code" «codice a correzione d'errore». |
| uncorrectable, beyond correction | non correggibile | Not «incorreggibile» (said of incorrigible people). |
| repair capacity, budget | capacità di riparazione | "Used 18 of 32" «18 su 32». "The worst spot" «la zona peggiore» (agreement: «troppo per ripararla»). Not «il punto peggiore»: «punto» is reserved for a dot, and the same line can stand near «… punti corretti». «zona» is also the pages' word for damaged places («zone danneggiate»). |
| margin (wide, moderate, close to the limit) | margine (margine ampio, margine moderato, vicino al limite) | |
| check the fingerprint, checking | controllare l'impronta, controllo dell'impronta | «Controllo dell'impronta…». Keeps «verific-» free for "verified". |
| matches / does not match the fingerprint | corrisponde / non corrisponde all'impronta | |
| identify (a scan), identified | identificare, identificata | «Identificazione della pagina» (the step), «scansione non identificata». Reserved for the program identifying a scan: the printed name that lets people tell pages apart «permette di riconoscere le pagine» (`gui.name.printed`). |
| assign (a scan) to a page | assegnare a una pagina | Button «Assegna a una pagina…». |
| start a document by hand, put together by hand | comporre un documento a mano, composto a mano | One verb for both, so the button and the later caution match. |
| replace (scan) | sostituire | |
| use this scan | usare questa scansione | Button «Usa questa scansione». |
| switch to this document | passare a questo documento | |
| add scans | aggiungere scansioni | |
| remove | rimuovere | Removes a scan from the list; does not delete the file («Elimina» would). |
| being read, waiting, working | in lettura, in attesa, elaborazione | Section «In lettura», detail «Lettura in corso…», step «In attesa», bar «Elaborazione…». |
| step (of reading) | fase | Steps: «Apertura del file», «Ricerca della pagina», «Identificazione della pagina», «Lettura dei dati», «Metodo lento: campionamento», «Metodo lento: passata {current} di {total}». |
| pass (of the slower reader) | passata | |
| coarse scan, too coarse | scansione a bassa risoluzione; risoluzione troppo bassa | Italian speaks of resolution: "scanned too coarsely" «risoluzione troppo bassa». Rejected: «scansione grossolana» (a calque, and «grossolano» also means crude). |
| resolution | risoluzione | dpi stays «dpi». |
| put on paper | scrivere su carta | Tab «Scrivi su carta». |
| read from paper | leggere dalla carta | Tab «Leggi da carta». |
| printed name, prints as | stampato come | Field «Stampato come:». |
| name (of the file, on the label) | nome | Field «Nome:», «(senza nome)». |
| compatible (printout) | compatibile | Checkbox «Compatibile con optar 0.2 e con l'optar originale». |
| original optar, the C program | l'optar originale, il programma in C | |
| dot size names: Standard, Medium, Big, Large, Extra large | Standard, Medi, Grandi, Grossi, Molto grossi | Masculine plural, agreeing with «punti». «Grossi» / «Molto grossi» keep the English pair "Large" / "Extra large". Capitalised only as a selector entry; in running text lower-case («punti standard», «con i punti grossi», «per i molto grossi»). |
| protection levels: None, Standard, High | Nessuna, Standard, Alta | Feminine, agreeing with «protezione». In prose «protezione standard», «protezione alta», «senza protezione». |
| paper names: A4, US Letter | A4, US Letter | Names of paper sizes; in prose «carta Letter». |
| actual size (100%), fit to page | dimensione reale (100%), «Adatta alla pagina» | The second is quoted as Italian print dialogs usually name it. |
| grayscale, colour, black and white | scala di grigi, a colori, bianco e nero | |
| bottom bar | barra in basso | |
| System default (entry of the language menu) | Lingua del sistema | `gui.SYSTEM_LANGUAGE`. The usual Italian entry; «Predefinita del sistema» was a long calque. |
| progress bar | barra di avanzamento | |
| row, list of scans | riga, elenco delle scansioni | |
| preview, marked | anteprima, evidenziati | Marks on the preview are «evidenziati», never «contrassegnati» (see "tag"). |
| outline of a page | contorno della pagina | |
| another printout | un'altra stampa | «non fa parte di questo file». |
| padded with zeros | completato con zeri (fino a una pagina intera) | |
| file verified · N bytes | File recuperato e verificato · N byte | |
| untagged, no tag | senza contrassegno, nessun contrassegno | |

### The command line's vocabulary

| English | Italian | Notes |
|---|---|---|
| symbol (code symbol on a page) | simbolo (pl. simboli) | Masculine; participles masculine («3 corretti»). Label characters are «carattere», so «simbolo» is only the code symbol. |
| codeword | parola di codice (pl. parole di codice) | Standard Italian coding-theory term. |
| byte | byte | Invariable. |
| encode / decode | codificare / decodificare; codifica / decodifica | Command names `encode`, `decode` stay English. "Decode again" «ripeti la decodifica». |
| option (of a command) | opzione | «l'opzione --protect». |
| usage, positional arguments, options | uso, argomenti posizionali, opzioni | As Python's own Italian argparse translation. |
| default | predefinito / predefinita | «(predefinito: a4)», agreeing with the noun described. |
| output (file) | file di uscita | |
| exit status | codice di uscita | |
| stdout, stderr | stdout, stderr | Kept; «standard output» may be added in prose. |
| gap (in page numbering) | buco nella numerazione | |
| ignored | ignorato | «2 scansioni di un altro documento sono state ignorate». |
| force | (option `--force`, not translated) | "Saved anyway because of --force" «Salvato comunque per via di --force». |
| protection level `{level}` on the command line | Livello di protezione {level} | The option value stays English and reads as a name: «Livello di protezione standard: …». |

### Format specification terms (`format.md`)

| English | Italian | Notes |
|---|---|---|
| page pixel, data pixel, scan pixel | pixel della pagina, pixel di dati, pixel della scansione | «pixel» invariable. |
| page format | formato di pagina | |
| format string | stringa di formato | |
| layout | layout | Paper + dot size + page format. The Italian IT loanword. |
| grid | griglia | |
| cross, origin, pitch | croce, origine, passo | |
| border, frame | bordo, cornice | "Page frame" «cornice della pagina». |
| data area | area dei dati | Geometric area (2.2). |
| data region | regione dei dati | Bytes of the container (4.6). Kept apart from «area dei dati». |
| label band, label strip, font strip | banda dell'etichetta, striscia dell'etichetta, striscia del font | |
| character, character cell, glyph, logo | carattere, cella del carattere, glifo, logo | |
| word | parola | |
| interleave | interlacciamento | |
| spread | distribuzione | Container spread (4.6); kept apart from «interlacciamento». |
| page code | codice di pagina | |
| Golay code, (extended) Hamming code, Reed-Solomon code | codice di Golay, codice di Hamming (esteso), codice di Reed-Solomon | |
| parity, parity bytes, parity level | parità, byte di parità, livello di parità | Never shown in the window. |
| check (of a tag), check digits | controllo, cifre di controllo | Not «verifica» (reserved). |
| header, header copy | intestazione, copia dell'intestazione | |
| magic | numero magico | Field name `magic` stays in code font. |
| well-formed, acceptable, valid | ben formato, accettabile, valido | "Valid" is «valido» everywhere ("invalid" «non valido»). |
| untrusted | non affidabile; di cui non ci si può fidare | Heading «Un'intestazione non è affidabile». |
| container | contenitore | |
| stream | flusso | |
| payload, body | carico utile, corpo | |
| padding, padding stream | riempimento, flusso di riempimento | The noun; a file is «completato con zeri». |
| fill cut | soglia di propagazione | The level for the flood fill from the edges (7.2). Not «diffusione» (suggests error diffusion, and is close to «distribuzione»). "Connected by edges, not corners" «connesso attraverso i lati dei pixel, non i vertici» («angoli» is kept for the corners of the scan). |
| erasure | cancellazione | Coding-theory term («correzione di cancellazioni»). |
| generator polynomial, field polynomial | polinomio generatore, polinomio del campo | |
| big-endian | big-endian (byte più significativo per primo) | |
| most significant bit | bit più significativo | |
| normative, informative | normativo, informativo | |
| test vectors, conformance vectors | vettori di test, vettori di conformità | |
| encoder, decoder, reader | codificatore, decodificatore, programma di lettura | "Reader" in parts 6–7 is any program that reads pages; this project's two readers are «metodo normale» and «metodo lento». |
| reference decoder | decodificatore di riferimento | |
| promise (of the tools) | promessa | |
| plain, tagged, self-identifying document | documento semplice, documento con contrassegno, documento autoidentificante | |

## Strength of claims

- **Verified** — «verificato», with the reserved root. Never softened
  («probabilmente integro») and never strengthened («garantito»). "Only the
  fingerprint makes a file verified" «Solo l'impronta rende un file
  verificato».
- **Recoverable vs recovered** — «recuperabile» says the pages read *should*
  be enough; «si può ricostruire dalle altre» (possibility) vs «ricostruita
  dalle altre» (done).
- **Promise of the tools** — «si può perdere N pagina/e su T» keeps the modal
  «può», not «resiste a» (stronger).
- **"One document, one printer, one scanner"** (the evidence page) — «un solo
  documento, una sola stampante, un solo scanner»: the bare article «un/una»
  would lose the stress on how narrow the evidence is.
- **"Is meant to be printed"** (format page, PDF) — «è pensato per essere
  stampato», not «va stampato» (a requirement).
- **"Has been shown", "is expected"** — «è stato mostrato», not «è stato
  dimostrato» (proved, stronger); "is expected not to be enough" «non
  dovrebbe bastare».
- **"May contain wrong parts", "may be damaged"** — «potrebbe contenere parti
  errate», «potrebbe essere danneggiato».
- **Warnings** stay as firm: "was not saved" «non è stato salvato» when the
  program chose not to save.

## Never translated

- The words `optar`, `optar-gui`.
- Command names: `encode`, `decode`.
- Option names: `--paper`, `--dots`, `--protect`, `--compatible`, `--format`,
  `--to`, `--label`, `--no-tag`, `--force`, `--debug-images`,
  `--no-slow-reader`, `--self-test`, `--version`, `-o`, and all others.
- Option values: `none`, `standard`, `high`, `a4`, `letter`, `pdf`, `png`,
  `pgm`, `medium`, `big`, `large`, `xlarge`. (The window's selector names are
  translated; a value typed on the command line is not.)
- Metavariables: `INPUT`, `BASE`, `OUTPUT`, `LEVEL`, `TEXT`, `STRING`, `X`,
  `BASE_NNNN_debug.png`, and the `N` / `T` of "can lose N page(s) of T".
- File names and extensions, environment variables, code, constants, header
  field names, the tag parts `SIZE`, `FINGERPRINT`, `CC`, `CHECK`, format
  strings, hex values.
- Product and standard names: PySide6, Ghostscript, MkDocs, PyInstaller,
  SHA-256, CRC-32, PNG, TIFF, BMP, PGM/PPM, JPEG, PDF, GF(256), dpi.
- Version numbers (0.2.0, v0.5.0).

## Agreement patterns the templates need

Italian has two plural forms (`one` exactly 1; `other` everything else,
including 0). Participles and adjectives after a number agree with a noun
that is often not in the string; the comment above each entry in `en.toml`
names it:

| Noun (gender) | `one` | `other` | used in |
|---|---|---|---|
| pagina (f) | 1 riparata, letta, danneggiata, mancante, illeggibile | 2 riparate, lette, danneggiate, mancanti, illeggibili | `gui.state.*` |
| blocco (m) | 1 riparato, perso | 2 riparati, persi | `gui.detail.*`, `gui.health.*` |
| simbolo (m) | 1 corretto, non correggibile | 2 corretti, non correggibili | `cli.stat_*` |
| byte (m, invariable) | 1 byte riparato | 2 byte riparati | |
| punto (m) | 1 punto corretto | 2 punti corretti | |

Counters whose form is chosen by one number while a participle would agree
with another use an invariant label form: «Pagine buone: {good} su {n}»,
«scansioni lette: {done} su {n}», «pagine lette: solo {read} su {count}».

## Site navigation

For `mkdocs.yml`, `nav_translations` of the `it` entry (keys are the English
titles exactly as written) and `site_description`.

| English | Italian |
|---|---|
| Home | Home |
| Using optar | Uso di optar |
| Install | Installazione |
| Put a file on paper | Scrivere un file su carta |
| Read it back | Rileggere il file |
| Scans that are too coarse | Scansioni a risoluzione troppo bassa |
| Command line | Riga di comando |
| Reference | Riferimento |
| How a page identifies itself | Come si identifica una pagina |
| What has and has not been shown | Che cosa è stato mostrato e che cosa no |
| Format specification | Specifica del formato |
| Project | Progetto |
| Development | Sviluppo |
| History | Storia |

- **site_description:** Conservare file su carta con una stampante laser e
  uno scanner
- **site_name:** optar (unchanged)
- **Language name** (`[language].name` and the switcher): Italiano

## Interface strings the pages quote

Copy these exactly from `src/optar/locale/it.toml` (quoted here as they are
there; a page puts them in «caporali»).

| English (as the English pages quote it) | Italian (catalogue key) |
|---|---|
| Put on paper | Scrivi su carta (`gui.WRITE_TAB`) |
| Read from paper | Leggi da carta (`gui.READ_TAB`) |
| Prints as: | Stampato come: (`gui.PRINTS_AS_FIELD`) |
| Dot size: | Punti: (`gui.DOTS_FIELD`) |
| Protection: | Protezione: (`gui.PROTECT_FIELD`) |
| Create PDF… | Crea PDF… (`gui.CREATE_PDF`) |
| Compatible with optar 0.2 and the original optar | Compatibile con optar 0.2 e con l'optar originale (`gui.COMPATIBLE`) |
| + Add scans… | + Aggiungi scansioni… (`gui.ADD_SCANS`) |
| Save file… | Salva file… (`gui.SAVE_FILE`) |
| Remove | Rimuovi (`gui.REMOVE_SCAN`) |
| Being read | In lettura (`gui.BEING_READ_SECTION`) |
| Not readable | Illeggibile (`gui.health.unreadable`), section Illeggibili (`gui.NOT_READABLE`) |
| Standard, Medium, Big, Large, Extra large (dots) | Standard, Medi, Grandi, Grossi, Molto grossi (`gui.dots.*`) |
| None, Standard, High (protection) | Nessuna, Standard, Alta (`gui.protection.*`) |
| can lose N page(s) of T | si può perdere N pagina su T / si possono perdere N pagine su T (`gui.write.promise`) |
| Waiting | In attesa (`gui.WAITING`) |
| Opening the file | Apertura del file (`gui.step.open`) |
| Finding the page | Ricerca della pagina (`gui.step.find`) |
| Identifying the page | Identificazione della pagina (`gui.step.identify`) |
| Reading the data | Lettura dei dati (`gui.step.read`) |
| Slower reader: sampling; pass 4 of 5 | Metodo lento: campionamento; Metodo lento: passata 4 di 5 (`gui.step.slow-sample`, `gui.step.slow-fit`) |
| Good | Buona (`gui.health.good`) |
| Repaired · N | Riparata · N (`gui.health.repaired`) |
| Damaged · N lost | Danneggiata · N persi (one: N perso) (`gui.health.damaged`) |
| Read by the slower reader | Letta con il metodo lento (`gui.READ_SLOWLY_ROW`) |
| Missing | Mancante (`gui.health.missing`) |
| Scanned at about 200 dpi, which is too coarse to read | Scansione fatta a circa 200 dpi, risoluzione troppo bassa per leggerla (`gui.coarse.unreadable`) |
| File recovered and verified · N bytes | File recuperato e verificato · N byte (`gui.VERIFIED` + `count.byte`) |
| Does not match the fingerprint on the paper | Non corrisponde all'impronta sulla carta (`gui.state.mismatch`) |
| Recoverable: page 3 missing, can be repaired from the others | Recuperabile: manca la pagina 3, si può ricostruire dalle altre (`gui.state.recoverable`) |
| Recoverable: page 3 missing, repaired from the others · matches the fingerprint | Recuperabile: manca la pagina 3, ricostruita dalle altre · corrisponde all'impronta (`gui.state.recovered`, `gui.state.matches`) |
| Working… 3 of 6 scans read | Elaborazione… Scansioni lette: 3 su 6 (`gui.scans_read_working`) |
| 3 of 6 scans read | scansioni lette: 3 su 6 (`gui.scans_read`; only ever after « · », hence lower case) |
| Checking the fingerprint… | Controllo dell'impronta… (`gui.state.checking`) |
| All N pages read · cannot be verified (no tag) | Lette tutte le pagine (N) · non verificabile (nessun contrassegno) (`gui.state.all_read`, `gui.state.no_tag`) |
| 4 of 6 pages good · 1 damaged · 1 missing | Pagine buone: 4 su 6 · 1 danneggiata · 1 mancante (`gui.state.good`, `.damaged`, `.missing`) |
| the worst spot used 57% of its repair capacity (18 of 32): a moderate margin | capacità di riparazione usata nella zona peggiore: 57% (18 su 32), margine moderato (`gui.margin.moderate`) |
| Page 3 · Read by the slower reader · 265,112 dots corrected | Pagina 3 · Letta con il metodo lento · 265.112 punti corretti (`gui.row.page`, `gui.READ_SLOWLY_ROW`, `gui.health.dots_corrected`) |
| · 6,912 bytes repaired by the document's protection | · 6.912 byte riparati dalla protezione del documento (`gui.health.bytes_repaired`) |
| fit to page | Adatta alla pagina (`cli.ACTUAL_SIZE`) |
