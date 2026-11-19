# Polish glossary (`pl`)

Working paper for the Polish translation of optar: the catalogue
`src/optar/locale/pl.toml` and the pages `docs/<page>.pl.md`. It follows
section 1 of `docs/superpowers/translation-brief.md`. The explanations are in
English; the terms are Polish. Once a term is chosen here it is used the same
way in the window, the command line and every page. Terms were chosen from the
English pages and from Polish software usage, not from the Russian glossary.

## General conventions

- **Address.** Informal second person singular («ty»), as Windows, macOS,
  Android and most current Polish software address the user. The pronoun
  itself is avoided where the verb says enough («Jeśli zamkniesz okno teraz…»,
  not «Jeśli ty zamkniesz…»). Never «Pan/Pani», never the impersonal «należy»
  in instructions.
- **Buttons, menu entries, file-dialog titles** use the imperative singular,
  the Polish UI norm: «Zapisz plik…», «Dodaj skany…», «Zastąp skan…»,
  «Wybierz plik do zapisania na papierze», «Przypisz do strony». Tabs too:
  «Zapisz na papierze», «Odczytaj z papieru».
- **Instructions** in messages and pages: the same imperative singular
  («Zeskanuj ponownie stronę 3»). Command-line help lines are imperative as
  well («wyświetl tę pomoc i zakończ», «nie dodawaj…»), as Python's own
  Polish argparse messages are.
- **Status words** in rows and in the bottom bar are participles or invariant
  phrases agreeing with *strona* (feminine): «W porządku», «Nieczytelna»,
  «Uszkodzona», «Brak».
- **Progress and steps** use verbal nouns: «Przetwarzanie…», «Wczytywanie…»,
  «Otwieranie pliku», «Identyfikacja strony».
- **Typography.** Quotes „…” (low-high), nested «…». Dash: en dash «–» with
  spaces in prose (Polish typesetting practice; the em dash is not used).
  Ranges: en dash without spaces, «strony 2–4» (`gui.list.range`,
  `gui.run.*.range`). Ellipsis «…» as one character, as in English. Polish
  letters always written (ą, ę, ł, ó, ś, ź, ż, ć, ń).
- **Numbers.** Thousands separator a no-break space (U+00A0) in the catalogue
  (`[format].group`) and in prose and tables: «199 773», «200 000». Decimal
  comma: «0,36», «2,5» (`[format].decimal` = «,»). Percent without a space:
  «18%» (the usual practice in Polish software). Inside code blocks, commands,
  anything a user types, and all of `format.pl.md`, numbers stay exactly as in
  English.
- **Units.** «dpi» stays; «px» for pixels and «B» for bytes after a bare
  number in error messages (no agreement needed); «pt» for points; «MiB».
- **optar** is always lower-case, even at the start of a sentence, and is not
  declined: «w optar», «program optar», «wersja optar 0.3».
- **«Strona»** is a sheet of paper carrying dots (one printed side). A page
  of this website is «rozdział», never «strona», so the two never meet in one
  sentence («zob. rozdział „Jak strona się identyfikuje”»).

## Terms

### The brief's required terms

| English | Polish | Notes |
|---|---|---|
| dot | kropka | Feminine: kropka / kropki / kropek. The natural word for a printed dot; "data dot" «kropka danych», "printer dot" «kropka drukarki». Rejected: «punkt» (also the typographic point and "point" in general), «piksel» (pixels are separate). |
| dot size | rozmiar kropek | Field «Rozmiar kropek:». |
| block | blok | Masculine inanimate: blok / bloki / bloków. One error-correction unit. In the spec "padding block" «blok dopełnienia»; the "block of device dots" of 5.1 is «kwadrat kropek drukarki», to keep «blok» for the window's meaning. |
| protection | ochrona | Field «Ochrona:». First mention on a page «ochrona przed uszkodzeniami». Say «z ochroną», «bez ochrony», «wydruk z ochroną». Rejected: «zabezpieczenie» (suggests passwords and security), «nadmiarowość» (correct but technical), «redundancja». The adjective «chroniony» is avoided for the same reason as «zabezpieczony». |
| fingerprint | odcisk | Masculine: odcisk / odciski / odcisków. The term Polish GnuPG and SSH texts use («odcisk klucza»). Full form «odcisk pliku» where the sentence needs it. Rejected: «skrót» (names the method, not the role), «suma kontrolna» (a checksum, weaker and different), «odcisk palca» (too literal). |
| tag | znacznik | Masculine: znacznik / znaczniki / znaczników. The bracketed `[SIZE:FINGERPRINT:CC]` at the start of a label. «bez znacznika» (untagged). Rejected: «tag» (anglicism, reads as a hashtag), «etykieta» (taken in spirit by "label", and a UI word), «metka» (colloquial: a price or clothing tag). Because «znacznik» is taken, the marks on the scan preview are «zaznaczone» / «zaznaczenie», never «znacznik». |
| label | napis | Masculine: napis / napisy / napisów. The line printed at the bottom of every page: «napis u dołu strony». Rejected: «etykieta» (a stuck-on sticker, and the word for a UI label), «podpis» (next to "fingerprint" and "verified" it reads as a signature). "Label band" «pas napisu», "label strip" «pasek napisu» (spec). |
| spare | zapasowy (skan) | Row «Zapasowy», detail tag «zapasowy», masculine agreeing with «skan». Rejected: «nadmiarowy» (sounds like an error), «rezerwowy» (a backup made on purpose). |
| scan (noun) | skan | Masculine inanimate: skan / skany / skanów. The usual word in Polish scanning software. |
| scan (verb) | zeskanować (skanować) | "Rescan" «zeskanować ponownie» (imperative «zeskanuj ponownie»). "Scan at 600 dpi" «skanuj w rozdzielczości 600 dpi», short «skanuj w 600 dpi». |
| printout | wydruk | Masculine. The pages as printed, the physical set. Kept apart from «dokument» (the logical set of pages carrying one file), as English keeps them apart. |
| document | dokument | A set of pages that carries one file. |
| page | strona | Feminine: strona / strony / stron; accusative stronę / strony / stron; after «z» (of): «z 1 strony», «z 5 stron». Rejected: «kartka» (a sheet has two sides). See the general convention on «rozdział». |
| slower reader | wolniejsza metoda odczytu (short: wolniejsza metoda) | Polish keeps the comparative naturally, and it says what the English says: a second method, slower than the first. "The ordinary reader" «zwykła metoda odczytu» / «zwykła metoda». "Read by the slower reader" «odczytana wolniejszą metodą» (page, feminine). "Slower reader for coarse scans" «wolniejsza metoda dla skanów o niskiej rozdzielczości». Rejected: «czytnik» (hardware), «tryb» (a mode is chosen by the user; this runs by itself), «wolna metoda» (sounds like a defect). |
| self-identifying page | strona samoidentyfikująca | Plural «strony samoidentyfikujące», document «dokument samoidentyfikujący». Built like «samoczyszczący», «samoprzylepny»: the reflexive «się» drops in a «samo-» compound. Shares its root with the verb the window uses for scans («zidentyfikować», «Identyfikacja strony»). First mention on a page adds the gloss «(strony, które same podają, do jakiego dokumentu należą i jaki mają numer)». Rejected: «samoidentyfikująca się» (heavy), «samoopisująca» (self-describing, a different idea), «samorozpoznawalna» (a coinage). |
| verified | zweryfikowany (plik zweryfikowany) | The established Polish word («zweryfikowany wydawca»). Always means: the recovered file matched its fingerprint. The root «weryfik-» is **reserved** for verified / verification: "not verified" «niezweryfikowany», "did not verify" «nie przeszedł weryfikacji», "cannot be verified" «nie można zweryfikować», "once verified" «po weryfikacji». Checking the fingerprint is «sprawdzanie odcisku» (plain «sprawdzić» is free for this). Rejected: «potwierdzony» (vaguer; «potwierdzić» is used for "confirm" in the cautions), «sprawdzony» (only says it was looked at), anything with «gwarantowany». "The repair reported no failure" (which does not verify) is «naprawa nie zgłosiła niepowodzenia» / «nie zgłasza niepowodzenia», never «nie zgłosiła błędu» («błąd» also means a wrong byte, which a repair corrects normally). The final check that the file is the original is «weryfikacja», not «sprawdzenie». |
| repaired | naprawiony (naprawić, naprawa) | The protection or the page's error correction fixed damaged data: «naprawiono 6 912 bajtów», «Naprawiona · 3». A *missing* page is not «naprawiona»: "repaired from the others" for a missing page is «odtworzona z pozostałych» (the same verb as "rebuild"). |
| lost | utracony (utracić, utrata) | Blocks that could not be repaired («3 utracone»), and a whole page lost from the printout («można utracić 1 stronę z 12»). Distinct from "missing". Rejected: «stracony» (emotional), «zgubiony» (only physical objects). |
| damaged | uszkodzony / uszkodzona | Page state «Uszkodzona». "Damage" «uszkodzenia» (plural, the natural Polish for stains and tears). |
| missing | brak; brakujący | A page of which no scan has been added. State «Brak»; inside a sentence «brak strony 3» / «brak stron 2 i 3»; counted «1 brakująca». Not «utracona»: the paper may exist, only the scan is missing. |

### The window's vocabulary

| English | Polish | Notes |
|---|---|---|
| good (page state) | w porządku | Invariant: «W porządku», «4 z 6 stron w porządku». Rejected: «dobra» (agrees in gender and sounds like praise). |
| not readable, unreadable | nieczytelny / nieczytelna | Page state «Nieczytelna»; list section «Nieczytelne» (scans); "could not be read" «nie udało się odczytać». |
| recoverable (document state) | do odzyskania | Invariant. Used for both states that English labels "Recoverable" (to be repaired and already repaired). |
| recovered | odzyskany | The file obtained from the pages: «odzyskany plik», «Plik odzyskany i zweryfikowany». "What was recovered" «to, co udało się odzyskać». |
| rebuild (a lost page) | odtworzyć | Also "repaired from the others" for a missing page: «można ją odtworzyć z pozostałych», «odtworzona z pozostałych». |
| corrected (dots, symbols, bits) | skorygowany | The page code or the slower reader fixed a dot, bit or symbol. Kept apart from "repaired": «265 112 kropek skorygowanych · 6 912 bajtów naprawionych przez ochronę dokumentu». "Error correction" «korekcja błędów», "error-correcting code" «kod korekcyjny». |
| uncorrectable, beyond correction | nie do skorygowania | Invariant, so it needs no agreement. |
| repair capacity | zdolność naprawcza | "used 18 of 32" «wykorzystało 18 z 32». "The worst spot" «najgorsze miejsce». |
| margin (wide, moderate, close to the limit) | zapas (duży zapas, umiarkowany zapas, blisko granicy) | |
| check the fingerprint, checking | sprawdzić odcisk, sprawdzanie odcisku | «Sprawdzanie odcisku…». |
| matches / does not match the fingerprint | zgadza się / nie zgadza się z odciskiem | A verb, so it needs no gender. In the past tense «był zgodny z odciskiem» (not «zgodził się», which means "consented"). |
| identify (a scan), identified | zidentyfikować, zidentyfikowany | «Identyfikacja strony» (step), «nie zidentyfikowano». Rejected: «rozpoznać» (fine Polish, but the term "self-identifying" needs the same root). «zidentyfikować» is reserved for the program identifying a scan; that the printed name tells the pages apart later is «rozpoznać» with the name as the means (`gui.name.printed` «Później to po wydrukowanej nazwie będzie można rozpoznać strony.»). |
| assign (a scan) to a page | przypisać do strony | Button «Przypisz do strony…». "Not used for page 3" «nie użyto jako strony 3» (not «dla strony»). |
| start a document by hand, put together by hand | złożyć dokument ręcznie, złożony ręcznie | One verb for both, so the button and the later caution match («Ten dokument złożono ręcznie»). |
| replace (scan) | zastąpić | «Zastąp skan…». |
| use this scan | użyj tego skanu | |
| switch to this document | przełącz na ten dokument | |
| add scans | dodać skany | «+ Dodaj skany…». |
| remove (a scan from the list) | usuń z listy | Button «Usuń z listy»: plain «Usuń» would suggest deleting the file from disk. |
| being read, waiting, working | w trakcie odczytu, w kolejce, przetwarzanie | Section «W trakcie odczytu», row «Odczytywanie…», step «W kolejce», «Przetwarzanie…». |
| step (of reading) | etap | Steps: «Otwieranie pliku», «Szukanie strony», «Identyfikacja strony», «Odczyt danych», «Wolniejsza metoda: próbkowanie», «Wolniejsza metoda: przebieg {current} z {total}». |
| pass (of the slower reader) | przebieg | |
| coarse scan, too coarse | skan o niskiej rozdzielczości; o zbyt niskiej rozdzielczości | Polish speaks of resolution, not coarseness. Rejected: «zgrubny skan», «gruby skan» (calques). |
| resolution | rozdzielczość | |
| put on paper | zapisać na papierze | Tab «Zapisz na papierze». |
| read from paper | odczytać z papieru | Tab «Odczytaj z papieru». |
| prints as | na wydruku | Field «Na wydruku:» ("on the printout:"), short and natural. |
| name (on the label) | nazwa | Field «Nazwa:», «(bez nazwy)». |
| compatible (printout) | zgodny (wydruk) | Checkbox «Zgodność z optar 0.2 i oryginalnym programem optar» (a noun, since a checkbox adjective has no visible subject). |
| original optar, the C program | oryginalny program optar, program w C | |
| dot size names: Standard, Medium, Big, Large, Extra large | Standardowe, Średnie, Duże, Bardzo duże, Ogromne | Plural adjectives agreeing with «kropki». Polish has no clean pair for "Large / Extra large" after «Duże» (both would be «duży»), so Large is «Bardzo duże» and Extra large «Ogromne». Not «Większe»: the pages use "larger dots" for any non-standard size («większe kropki»), which must not sound like one size. Capitalised only as a selector entry or at the start; in running text lower-case («standardowe kropki», «ze standardowymi kropkami», «dla ogromnych kropek»). |
| protection levels: None, Standard, High | Brak, Standardowa, Wysoka | Feminine, agreeing with «ochrona». In prose «standardowa ochrona», «wysoka ochrona», «bez ochrony». |
| paper names: A4, US Letter | A4, US Letter | In prose «papier Letter». |
| actual size (100%), fit to page | rozmiar rzeczywisty (100%), „Dopasuj do strony” | The second quoted as Polish print dialogs name it. |
| grayscale, colour, black and white | skala szarości, kolor, czarno-biały | «w skali szarości», «w kolorze». |
| bottom bar | pasek u dołu (pasek stanu) | |
| progress bar | pasek postępu | |
| row, list of scans | wiersz, lista skanów | |
| preview, marked | podgląd, zaznaczone | |
| another printout | inny wydruk | Section «Spoza tego pliku»; row «nie należy do tego pliku». |
| untagged, no tag | bez znacznika, brak znacznika | |
| Language (menu), System default | Język, Jak w systemie | |

### The command line's vocabulary

| English | Polish | Notes |
|---|---|---|
| symbol (code symbol) | symbol | Masculine: symbol / symbole / symboli. Label characters are «znak», so «symbol» is only the code symbol. |
| codeword | słowo kodowe | Neuter: słowo kodowe / słowa kodowe / słów kodowych. |
| byte | bajt | bajt / bajty / bajtów. «B» after a bare number in error messages. |
| encode / decode | zakodować / zdekodować | Command names `encode`, `decode` stay English. "Decode again" «ponów dekodowanie». |
| option | opcja | The normal Polish word for a command-line option (Python's Polish argparse uses it). |
| usage, positional arguments, options | użycie, argumenty pozycyjne, opcje | argparse headings. |
| exit status | kod wyjścia | |
| stdout, stderr | stdout, stderr | Kept; «standardowe wyjście» may be added in prose. |
| gap (in page numbering) | luka | |
| ignored | pominięty | «pominięto 2 skany z innego dokumentu». |
| protection level `{level}` | Poziom ochrony {level} | The option value stays English and reads as a name: «Poziom ochrony standard: …». |
| … the slower reader is started | uruchamiana jest wolniejsza metoda | |
| scanned upright | zeskanowana we właściwym położeniu (nieobrócona) | Covers both upside down and a quarter turn. |

### Format specification terms (`format.md`)

| English | Polish | Notes |
|---|---|---|
| page pixel, data pixel, scan pixel | piksel strony, piksel danych, piksel skanu | piksel / piksele / pikseli. |
| page format, format string | format strony, ciąg formatu | |
| layout | układ | Paper + dot size + page format. |
| grid | siatka | |
| cross, origin, pitch | krzyżyk, początek krzyżyka, odstęp krzyżyków | |
| border, frame | ramka | |
| data area | obszar danych | Geometric (2.2). |
| data region | strefa danych | Bytes of the container (4.6); kept apart from «obszar danych». |
| label band, label strip, font strip | pas napisu, pasek napisu, pasek czcionki | |
| character, character cell, glyph, logo | znak, komórka znaku, glif, logo | |
| interleave | przeplot | Standard term. |
| spread | rozproszenie | Container spread (4.6); kept apart from «przeplot». |
| page code | kod strony | |
| Golay code, (extended) Hamming code, Reed-Solomon code | kod Golaya, (rozszerzony) kod Hamminga, kod Reeda-Solomona | Usual Polish spellings. |
| parity, parity bytes, parity level | parzystość, bajty parzystości, poziom parzystości | Never shown in the window. |
| check (of a tag), check digits | wartość kontrolna, cyfry kontrolne | Not «suma kontrolna». |
| free text (of a label) | tekst dowolny | Adjective after the noun, which marks it as a term: «tekst dowolny napisu», «w tekście dowolnym». Not «dowolny tekst», which reads as "any text". Plain «dowolny» keeps its ordinary meaning "any" elsewhere. |
| header, header copy | nagłówek, kopia nagłówka | |
| magic | sygnatura | Field name `magic` stays in code font. |
| well-formed, acceptable, valid | poprawny składniowo, dopuszczalny, ważny | "Valid" is «ważny» everywhere in `format.pl.md` ("invalid" «nieważny»); the other two are the defined terms of 6.2. |
| untrusted | niezaufany; nie można mu ufać | Heading «Nagłówkowi nie można ufać». |
| container, stream, payload, body | kontener, strumień, ładunek, treść | «treść strony», «treść dokumentu». |
| padding, padded with zeros | dopełnienie, dopełniony zerami | «dopełniony zerami do pełnej strony». |
| erasure | wymazanie | Coding-theory term. |
| generator polynomial, field polynomial | wielomian generujący, wielomian ciała | |
| big-endian, most significant bit | big-endian (najstarszy bajt pierwszy), najstarszy bit | |
| normative, informative | normatywny, informacyjny | As in Polish standards (PN). |
| test vectors, conformance vectors | wektory testowe, wektory zgodności | "Recorded" (vectors, outputs) «zarejestrowane», not «nagrane» (sound or video). |
| encoder, decoder, reader | koder, dekoder, program odczytujący | "Reader" in parts 6 and 7 is any implementation. |
| reference decoder | dekoder referencyjny | |
| plain, tagged, self-identifying document | dokument prosty, dokument ze znacznikiem, dokument samoidentyfikujący | |

## Strength of claims

- **Verified** – «zweryfikowany», with the reserved root. Never softened
  («prawdopodobnie poprawny») and never strengthened («gwarantowany»). "Only
  the fingerprint makes a file verified" «Tylko odcisk sprawia, że plik jest
  zweryfikowany».
- **Recoverable vs recovered** – «do odzyskania» says the pages read *should
  be enough*; «odzyskany» only of what was rebuilt. "Can be repaired from the
  others" «można ją odtworzyć z pozostałych»; "repaired from the others"
  «odtworzona z pozostałych».
- **Promise** – «można utracić N stron» keeps the modal «można», not
  «wytrzyma».
- **"Has been shown", "is expected"** – «wykazano» (not «udowodniono»);
  "is expected not to be enough" «najpewniej nie wystarczy» / «oczekuje się,
  że nie wystarczy».
- **"May contain wrong parts", "may be damaged"** – keep «może»: «może
  zawierać błędne fragmenty», «może być uszkodzony».
- **Warnings** stay firm: "was not saved" «nie został zapisany», not «nie
  udało się zapisać» where the program chose not to save.

## Never translated

- `optar`, `optar-gui`; command names `encode`, `decode`.
- Option names (`--paper`, `--dots`, `--protect`, `--compatible`, `--format`,
  `--to`, `--label`, `--no-tag`, `--force`, `--debug-images`,
  `--no-slow-reader`, `--self-test`, `--version`, `-o`, …).
- Option values: `none`, `standard`, `high`, `a4`, `letter`, `pdf`, `png`,
  `pgm`, `medium`, `big`, `large`, `xlarge`.
- Metavariables (`INPUT`, `BASE`, `OUTPUT`, `LEVEL`, `TEXT`, `STRING`, `X`,
  `N`, `T`), file names and extensions, environment variables, code,
  constants, header field names, tag parts (`SIZE`, `FINGERPRINT`, `CC`),
  format strings, hex values.
- Product and standard names (PySide6, Ghostscript, MkDocs, PyInstaller,
  SHA-256, CRC-32, PNG, TIFF, BMP, PGM/PPM, JPEG, PDF, GF(256), dpi), version
  numbers.

## Agreement patterns the templates need

Polish plural categories: `one` exactly 1; `few` 2–4, 22–24, 32–34… (not
12–14); `many` everything else, **including 21, 31, 101** («21 stron»).

| Noun | `one` | `few` | `many` | after «z N» (of) |
|---|---|---|---|---|
| strona (f) | strona | strony | stron | strony / stron / stron |
| strona, accusative | stronę | strony | stron | |
| skan (m) | skan | skany | skanów | skanu / skanów / skanów |
| blok (m) | blok | bloki | bloków | |
| bajt (m) | bajt | bajty | bajtów | |
| kropka (f) | kropka | kropki | kropek | |
| symbol (m) | symbol | symbole | symboli | |
| słowo kodowe (n) | słowo kodowe | słowa kodowe | słów kodowych | |
| piksel (m) | piksel | piksele | pikseli | |

A participle after a bare number takes the noun's gender in `one`, the
nominative plural in `few` and the genitive plural in `many`: pages «1
naprawiona, 2 naprawione, 5 naprawionych»; blocks and symbols «1 naprawiony,
2 naprawione, 5 naprawionych». With `many` a finite verb is neuter singular
(«5 skanów nie należy», «5 bajtów było błędnych»). The impersonal «-no/-to»
form plus the accusative («Odczytano 3 strony», «naprawiono 5 bajtów») avoids
verb agreement and is used for counters.

## Site navigation

For `mkdocs.yml`, `nav_translations` of the `pl` entry (keys are the English
titles exactly as written) and `site_description`.

| English | Polish |
|---|---|
| Home | Strona główna |
| Using optar | Korzystanie z optar |
| Install | Instalacja |
| Put a file on paper | Zapisywanie pliku na papierze |
| Read it back | Odczytywanie pliku |
| Scans that are too coarse | Skany o zbyt niskiej rozdzielczości |
| Command line | Wiersz poleceń |
| Reference | Szczegóły techniczne |
| How a page identifies itself | Jak strona się identyfikuje |
| What has and has not been shown | Co wykazano, a czego nie |
| Format specification | Specyfikacja formatu |
| Project | Projekt |
| Development | Rozwój |
| History | Historia |

"Home" is «Strona główna», the fixed Polish term for a site's home page; it is
the one place where «strona» means a web page, and it never appears in a
sentence.

- **site_description:** Przechowywanie plików na papierze za pomocą drukarki
  laserowej i skanera
- **site_name:** optar (unchanged)
- **Language name** (`[language].name` and the switcher): Polski

## Interface strings the pages quote

Page translators copy these from `pl.toml` exactly (English → Polish):

| English | Polish (catalogue) | Key |
|---|---|---|
| Put on paper | Zapisz na papierze | `gui.WRITE_TAB` |
| Read from paper | Odczytaj z papieru | `gui.READ_TAB` |
| + Add scans… | + Dodaj skany… | `gui.ADD_SCANS` |
| Save file… | Zapisz plik… | `gui.SAVE_FILE` |
| Create PDF… | Utwórz PDF… | `gui.CREATE_PDF` |
| Remove | Usuń z listy | `gui.REMOVE_SCAN` |
| Prints as: | Na wydruku: | `gui.PRINTS_AS_FIELD` |
| Compatible with optar 0.2 and the original optar | Zgodność z optar 0.2 i oryginalnym programem optar | `gui.COMPATIBLE` |
| Being read | W trakcie odczytu | `gui.BEING_READ_SECTION` |
| Waiting | W kolejce | `gui.WAITING` |
| Opening the file / Finding the page / Identifying the page / Reading the data | Otwieranie pliku / Szukanie strony / Identyfikacja strony / Odczyt danych | `gui.step.*` |
| Slower reader: sampling; pass 4 of 5 | Wolniejsza metoda: próbkowanie; Wolniejsza metoda: przebieg 4 z 5 | `gui.step.slow-sample`, `gui.step.slow-fit` |
| Good / Not readable / Missing | W porządku / Nieczytelna / Brak | `gui.health.*` |
| Repaired · N | Naprawiona · N | `gui.health.repaired` |
| Damaged · N lost | Uszkodzona · N utraconych (1 utracony, 2 utracone) | `gui.health.damaged` |
| Read by the slower reader | Odczytana wolniejszą metodą | `gui.READ_SLOWLY_ROW` |
| 265,112 dots corrected | 265 112 kropek skorygowanych | `gui.health.dots_corrected` |
| 6,912 bytes repaired by the document's protection | 6 912 bajtów naprawionych przez ochronę dokumentu | `gui.health.bytes_repaired` |
| File recovered and verified | Plik odzyskany i zweryfikowany | `gui.VERIFIED` |
| Does not match the fingerprint on the paper | Nie zgadza się z odciskiem na papierze | `gui.state.mismatch` |
| Recoverable: page 3 missing, can be repaired from the others | Do odzyskania: brak strony 3, można ją odtworzyć z pozostałych | `gui.state.recoverable` |
| … repaired from the others · matches the fingerprint | … odtworzona z pozostałych · zgadza się z odciskiem | `gui.state.recovered`, `gui.state.matches` |
| Working… 3 of 6 scans read | Przetwarzanie… Odczytano 3 z 6 skanów | `gui.scans_read_working` |
| … · 3 of 6 scans read | … · odczytano 3 z 6 skanów (lower case: it always follows « · ») | `gui.scans_read` |
| Checking the fingerprint… | Sprawdzanie odcisku… | `gui.state.checking` |
| All N pages read · cannot be verified (no tag) | Odczytano wszystkie strony: N · nie można zweryfikować (brak znacznika) | `gui.state.all_read`, `gui.state.no_tag` |
| 4 of 6 pages good · 1 damaged · 1 missing | 4 z 6 stron w porządku · 1 uszkodzona · 1 brakująca | `gui.state.good`, `gui.state.damaged`, `gui.state.missing` |
| the worst spot used 57% of its repair capacity (18 of 32): a moderate margin | najgorsze miejsce wykorzystało 57% zdolności naprawczej (18 z 32): umiarkowany zapas | `gui.margin.moderate` |
| Scanned at about 200 dpi, which is too coarse to read | Zeskanowano w rozdzielczości około 200 dpi, zbyt niskiej do odczytu | `gui.coarse.unreadable` |
| can lose N page(s) of T | można utracić N stronę / strony / stron z T | `gui.write.promise` |
| Standard, Medium, Big, Large, Extra large (dots) | Standardowe, Średnie, Duże, Bardzo duże, Ogromne | `gui.dots.*` |
| None, Standard, High (protection) | Brak, Standardowa, Wysoka | `gui.protection.*` |
| Print at actual size (100%), not "fit to page". | Drukuj w rozmiarze rzeczywistym (100%), a nie z opcją „Dopasuj do strony”. | `cli.ACTUAL_SIZE` |
