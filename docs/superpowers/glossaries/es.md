# Spanish glossary (`es`)

Working paper for the Spanish translation of optar: the catalogue
`src/optar/locale/es.toml` and the pages `docs/<page>.es.md`. It follows
section 1 of `docs/superpowers/translation-brief.md`. The explanations are in
English; the terms are Spanish. Once a term is chosen here it is used the same
way in the window, the command line and every page.

The Spanish is neutral international Spanish as software localisation writes
it: no regionalisms, no voseo, no forms tied to Spain («ordenador», «fichero»)
or to one American country. Where Spain and America differ, the word chosen is
the one both understand (see "add" and "file" below).

## General conventions

- **Address.** Formal **usted**, used the same way everywhere. It is the form
  that reads as neutral on both sides of the Atlantic in software for a general
  public (tú is common in Spain's consumer software but reads as casual in much
  of America; vosotros/ustedes plurals never arise). Possessives follow it
  («su página», never «tu página»).
- **Buttons, menu entries and dialog titles** use the **infinitive**:
  «Guardar archivo…», «Añadir escaneos…», «Reemplazar escaneo…», «Elegir un
  escaneo de la página {page}», «Guardar el PDF». Command-line option help
  (argparse) is also infinitive and lower-case: «mostrar este mensaje de ayuda
  y salir», «no probar el lector lento…».
- **Instructions** in messages and pages use the **usted imperative**:
  «Escanee la página 3 y vuelva a decodificar», «Elija otro nombre»,
  «Escanéela a 600 dpi». Inside a list after a colon they stay lower-case
  («…: añada la página 3 y vuelva a escanear la página 5, que es la más
  dañada»).
- **Status words** in rows and in the bottom bar are participles or adjectives
  that agree with the noun named in the `en.toml` comment («Reparada»,
  «Dañada», «Ausente», «Correcta» agree with *página*, feminine; «3
  reparados», «2 perdidos» agree with *bloque*, masculine), or invariant
  phrases («En espera», «En lectura», «Procesando…»).
- **Impersonal se** for what the program did: «se escribió x.pdf», «se reparó
  1 byte», «no se pudo leer», «se guardó de todos modos». A refusal by choice
  stays firm: «no se ha guardado» (was not saved), never «no se pudo
  guardar» (could not be saved) when the program chose not to.
- **Typography.**
    - Opening marks are always written: «¿Guardar de todos modos?», «¿Qué
      página de este documento es {name}?»; ¡ is not used (the program does not
      exclaim).
    - Quotes: angle quotes « » first level (RAE's first choice), “ ” inside
      them. A nickname inside a name takes curly single quotes: Karel ‘Clock’
      Kulhavy. Names of window elements quoted in pages use « »: «Guardar
      archivo…».
    - Dash: raya «—» for an aside in prose, closed on both sides
      («—así—»), sparingly; plain commas are often better.
    - Ranges of pages: hyphen without spaces, «2-4», in `gui.list.range` and
      every `gui.run.*.range` (the RAE accepts the hyphen for ranges and it
      matches the page lists the program builds).
    - Ellipsis «…» as one character, as in English, with no space before it.
    - Capital letters: only the first word of a title, heading, button or menu
      entry («Pasar al papel», «Cómo se identifica una página»), not every
      word as English titles do.
- **Numbers.** `[format].group` is «.» and `[format].decimal` is «,».
  Outside code blocks, in prose and in table cells alike, write Spanish
  numbers: «199.773», «200.000», «0,36», «2,5». Inside code blocks, commands
  and anything a user types, and in all of `format.es.md`, numbers stay
  exactly as in English, as the brief requires. Versions (0.2.0) are names
  and stay. (The RAE prefers no separator in four-digit numbers, «1000»; the
  program groups every number above 999 the same way, so pages should write
  «1.000» too only where they quote the program; in prose «1000» is fine.)
- **Percent.** A no-break space (U+00A0) before the sign, as the RAE and
  Fundéu require: «57 %», «menos del 0,1 %». The catalogue writes it as
  ` ` in `gui.slow.share`, `gui.slow.share_small`, `gui.margin.*` and
  `cli.ACTUAL_SIZE`. With an article: «usó el 57 %».
- **dpi** stays «dpi» (not «ppp»): «puntos por pulgada» would put a second
  meaning on «punto», which here is the optar dot. Scanner drivers in Spanish
  show both; «dpi» is understood everywhere.
- **optar** is always lower-case, also at the start of a sentence. It takes
  the masculine article when one is needed: «el optar original», «una página
  de optar».
- **«Página»** is a sheet of paper carrying dots. A page of this website is
  «sección», never «página», so the two never meet in one sentence
  («véase la sección «Cómo se identifica una página»»).
- **Conjunctions:** «y» becomes «e» before a word starting with the sound /i/
  and «o» becomes «u» before /o/; a number, an option name or a placeholder
  does not trigger this in the catalogue's templates.

## Terms

### The brief's required terms

| English | Spanish | Notes |
|---|---|---|
| dot | punto (m) | «punto» / «puntos». "Data dot" «punto de datos», "printer dot" «punto de impresora» (spec only). Not «píxel»: pixels are separate. |
| dot size | tamaño de punto | Singular «punto», as Spanish says «tamaño de letra»: «Tamaño de punto:», «con este tamaño de punto». |
| block | bloque (m) | One error-correction unit; the window repairs or loses blocks. In the spec "padding block" is «bloque de relleno»; the "block of device dots" of 5.1 is «cuadro de puntos de impresora», to keep «bloque» for the window's meaning. |
| protection | protección (f) | Window label «Protección:». Prefer «con protección», «sin protección», «impresión con protección» to the participle «protegida», which in Spanish software suggests a password («archivo protegido»). The verb «protegerlo» is acceptable where English uses the verb ("too large to protect"). Rejected: «redundancia» (technical), «respaldo» (backup). |
| fingerprint | huella (f) | Short for «huella digital», the established term for a key or certificate fingerprint in Spanish software. «huella digital» may be used at the first mention on a page. Rejected: «hash» (names the method), «suma de comprobación» (a checksum is a different, weaker thing), «firma» (a signature). |
| tag | etiqueta (f) | The bracketed `[SIZE:FINGERPRINT:CC]` at the start of a label. «sin etiqueta» (untagged), «páginas sin etiqueta». The usual word for a tag in Spanish software (HTML tags, tags on files). Because «etiqueta» is taken, the label is «rótulo». |
| label | rótulo (m) | The line printed at the bottom of every page. «Rótulo» is a printed line of text that names something, which is exactly this. Rejected: «etiqueta» (taken by "tag"), «leyenda» (a caption under a picture, or a map key), «pie» (pie de página is a footer of a document, close but suggests page numbering only). "Label band" «banda del rótulo», "label strip" «tira del rótulo» (spec). The `--label` option help says «texto impreso en cada página». |
| spare | de repuesto (escaneo de repuesto) | Row title «De repuesto», detail tag «de repuesto». «De repuesto» is exactly "spare" (rueda de repuesto): there, ready, not in use. Invariant, so no agreement. Rejected: «sobrante» (sounds like waste), «de reserva» / «copia de seguridad» (sounds like a backup made on purpose), «duplicado» (implies identical). |
| scan (noun) | escaneo (m) | «escaneo» / «escaneos». The usual noun in scanning software for both the act and the image. Rejected: «imagen escaneada» (too long for buttons and rows), «digitalización» (formal, long). |
| scan (verb) | escanear | "Rescan" «volver a escanear». "Scan at 600 dpi" «escanee a 600 dpi». Rejected: «reescanear» (not standard). |
| printout | impresión (f) | The pages as printed, the physical set. Kept apart from «documento» (the logical set of pages carrying one file), exactly as English keeps "printout" and "document" apart. |
| document | documento (m) | A set of pages that carries one file. |
| page | página (f) | Rejected: «hoja» (a sheet has two sides; an optar page is one printed side). See the convention on «sección». |
| slower reader | lector lento | "The ordinary reader" is «lector normal». First mention on a page: «un segundo lector, más lento». The comparative is dropped in the name because Spanish names do not carry it («el lector más lento» would mean "the slowest reader"). "Read by the slower reader" «leída por el lector lento». "Slower reader for coarse scans" «lector lento para escaneos de baja resolución». Rejected: «modo lento» (a mode is something the user chooses; this runs by itself), «método de lectura lento» (long for rows). |
| self-identifying page | página autoidentificable | Plural «páginas autoidentificables». On first mention on a page add the gloss «(páginas que dicen por sí mismas a qué documento pertenecen y qué número tienen)». Built on «identificar», the verb the window uses for scans («no identificado»). Rejected: «autodescriptiva» (self-describing, another idea), «página con cabecera» (loses the name used in option help and headings). |
| verified | verificado | Always means: the recovered file matched its fingerprint. The root **«verific-» is reserved** for this: "not verified" «no verificado», "did not verify" «no superó la verificación», "cannot be verified" «no se puede verificar», "after verification" «tras la verificación». Checking the fingerprint is «comprobar la huella» (see "check"). Rejected: «comprobado» (only says it was compared), «validado» (vaguer), anything with «garantizado» (stronger). |
| repaired | reparado (repair: reparar, reparación) | The protection or the page's error correction fixed damaged data: «se repararon 6.912 bytes», «Reparada · 3». Exception Spanish forces: a *missing* page is not «reparada»; for a missing page "repaired from the others" is «reconstruida a partir de las demás». |
| lost | perdido | Blocks that could not be repaired («Dañada · 3 perdidos»), and a whole page lost from the printout («puede perder 1 página de 12»). Distinct from "missing". Rejected: «extraviado» (mislaid by a person). |
| damaged | dañado / dañada | Page state «Dañada». "Damage" «daños» (plural is the natural Spanish for stains and tears). Rejected: «corrupto» (computing jargon, and a moral word). |
| missing | ausente; falta | A page of which no scan has been added. Row state «Ausente» (an adjective, invariant in gender); in a sentence «falta la página 3», «faltan las páginas 2 y 3». Not «perdida»: the paper may exist, only the scan is missing. |

### The window's vocabulary

| English | Spanish | Notes |
|---|---|---|
| good (page state) | correcta | Agrees with «página»: «Correcta», «4 de 6 páginas correctas». Rejected: «buena» (sounds like praise), «bien» (adverb, odd as a state). |
| not readable, unreadable | ilegible | Row «Ilegible»; list section «Ilegibles»; "could not be read" «no se pudo leer»; "bytes unreadable" «bytes ilegibles». |
| recoverable (document state) | recuperable | Used for both bar states whose English label is "Recoverable". |
| recovered | recuperado | The file obtained from the pages: «el archivo recuperado», «Archivo recuperado y verificado». "What was recovered" «lo que se recuperó». |
| rebuild (a lost page) | reconstruir | «reconstruida a partir de las demás». |
| corrected (dots, symbols, bits) | corregido | The page code or the slower reader fixed a dot, bit or symbol. Kept apart from "repaired" as English keeps them apart: «265.112 puntos corregidos · 6.912 bytes reparados por la protección del documento». "Error correction" «corrección de errores», "error-correcting code" «código corrector de errores». |
| uncorrectable | no corregible | «3 no corregibles», «palabras de código no corregibles». Rejected: «incorregible» (said of people). |
| repair capacity, budget | capacidad de reparación | "Used 18 of 32" «usó 18 de 32». |
| the worst spot | la peor zona | Not «punto», which is the dot. |
| margin (wide, moderate, close to the limit) | margen (un margen amplio, un margen moderado, cerca del límite) | |
| check the fingerprint, checking | comprobar la huella, comprobación | «Comprobando la huella…». Keeps «verific-» free for "verified". |
| matches / does not match the fingerprint | coincide / no coincide con la huella | |
| identify (a scan), identified | identificar, identificado | «Identificando la página» (step), «no identificado». Reserved for the program identifying a scan: where English says the printed name "identifies the pages" for people, Spanish says «permitirá reconocer las páginas» (`gui.name.printed`). |
| assign (a scan) to a page | asignar a una página | Button «Asignar a página…». |
| start a document by hand, put together by hand | componer un documento a mano, se compuso a mano | One verb for both, so the button and the later caution match. Rejected: «armar» (American colloquial), «montar» (Spain colloquial), «crear» (suggests making a new file). |
| replace (scan) | reemplazar | |
| use this scan | usar este escaneo | |
| switch to this document | cambiar a este documento | |
| add | añadir | «Añadir escaneos…», «añada la página 3». Understood everywhere; «agregar» (more American) is equally correct but one word is kept. |
| remove | quitar | Removes a scan from the list, does not delete the file. «Eliminar» / «Borrar» would suggest deleting the file from disk. |
| being read, waiting, working | en lectura, en espera, procesando | Section «En lectura», detail «Leyendo…»; step «En espera»; «Procesando…». |
| step (of reading) | paso | Steps: «Abriendo el archivo», «Buscando la página», «Identificando la página», «Leyendo los datos», «Lector lento: muestreo», «Lector lento: pasada {current} de {total}». |
| pass (of the slower reader) | pasada | |
| coarse scan, too coarse | escaneo de baja resolución; resolución demasiado baja | Spanish speaks of resolution: "scanned too coarsely" «escaneo de resolución demasiado baja». Rejected: «escaneo grueso» (a calque). |
| resolution | resolución | |
| put on paper | pasar al papel | Tab «Pasar al papel»; "the file being put on paper" «el archivo que se está pasando al papel». Idiomatic («pasar al papel», like «pasar a limpio»). Rejected: «poner en papel» (calque), «imprimir» (the tab makes a PDF, it does not print). |
| read from paper | leer del papel | Tab «Leer del papel». |
| prints as | se imprime como | Field «Se imprime como:». |
| name (on the label) | nombre | Field «Nombre:», «(sin nombre)». |
| file | archivo | Not «fichero» (Spain only). |
| compatible | compatible | Checkbox «Compatible con optar 0.2 y el optar original». |
| original optar, the C program | el optar original, la herramienta en C | |
| dot size names: Standard, Medium, Big, Large, Extra large | Estándar, Mediano, Grande, Muy grande, Extragrande | In the selector and on the command line, singular, agreeing with «tamaño»: «Tamaño de punto: Mediano». With «puntos» in sentences, plural and lower-case: «puntos estándar, medianos, grandes, muy grandes, extragrandes» («Cabe con puntos medianos», «A4, puntos grandes»). Big / Large / Extra large are Grande / Muy grande / Extragrande, which keep the English order visible. |
| protection levels: None, Standard, High | Ninguna, Estándar, Alta | Feminine, agreeing with «protección». In prose «protección estándar», «protección alta», «sin protección». |
| protection level `{level}` on the command line | Nivel de protección {level} | The option value stays English and reads as a name: «Nivel de protección standard: …». |
| paper names: A4, US Letter | A4, US Letter | In prose «papel A4», «papel Letter». |
| actual size (100%), fit to page | tamaño real (100 %), «Ajustar a la página» | The second is the print-dialog wording; it varies by driver. |
| grayscale, colour, black and white | escala de grises, color, blanco y negro | |
| bottom bar | barra inferior | |
| progress bar | barra de progreso | |
| row, list of scans | fila, lista de escaneos | |
| preview, marked | vista previa, marcados | Damaged places on the preview are «marcados» (no clash: «marca» is not used for "tag"). |
| another printout | otra impresión | «no pertenece a este archivo». |
| Language (menu), System default | Idioma, Idioma del sistema | |
| sentence end (`gui.sentence`) | «{words}.» | Spanish full stop. |
| window titles of file dialogs | infinitive | «Elegir un archivo para pasar al papel», «Elegir un escaneo de la página {page}», «Añadir escaneos», «Guardar el PDF». |
| could not be decoded in any orientation (`gui.reason.not_decodable`) | No se pudo decodificar el escaneo en ninguna orientación | A full sentence with a capital letter. |
| scanned upright | escaneada derecha, sin girar | Covers both upside down and turned by 90°. |
| pixels in error messages | píxeles | Numbers there are always large; «píxel» / «píxeles» with the accent. |
| bytes in error messages | B | `err.*` cannot inflect; the symbol «B» is invariant: «{size} B en papel». «pág.» likewise in `err.impossible_document`. |
| OK / Cancel / Yes / No / Save (buttons) | Aceptar / Cancelar / Sí / No / Guardar | |

### The command line's vocabulary

| English | Spanish | Notes |
|---|---|---|
| symbol (code symbol) | símbolo (m) | Label characters are «carácter», so «símbolo» is only ever the code symbol. |
| codeword | palabra de código (f) | «palabras de código no corregibles». |
| byte | byte (m) | «1 byte», «5 bytes». |
| encode / decode | codificar / decodificar | Command names `encode`, `decode` stay English. "Decode again" «volver a decodificar». |
| command | comando (m) | «El comando `optar`», column «Comando»; matches «Línea de comandos». Not «orden» (mostly peninsular). |
| option (of a command) | opción | argparse heading «opciones». |
| usage, positional arguments | uso, argumentos posicionales | |
| exit status | código de salida | |
| stdout, stderr | stdout, stderr | Kept; «salida estándar» may be added in prose. |
| gap (in page numbering) | hueco | «falta x_0002.png, pero existe x_0003.png». |
| ignored | ignorado | «se ignoraron 2 escaneos de otro documento». |
| default | predeterminado | «(predeterminado: a4)». |
| override (`--format`) | imponer otro | «imponer otro formato de página». |

### Format specification terms (`format.md`)

| English | Spanish | Notes |
|---|---|---|
| page pixel, data pixel, scan pixel | píxel de página, píxel de datos, píxel de escaneo | |
| page format, format string | formato de página, cadena de formato | |
| page count | total de páginas | Also in headings (4.8 «El total de páginas y los límites»); kept apart from «número de página». |
| root mean square | media cuadrática (RMS) | Not «distancia cuadrática media», which reads as the mean squared distance. |
| layout | diseño | Paper + dot size + page format: «el diseño de puntos medium en papel a4». |
| grid | cuadrícula | |
| cross, origin, pitch | cruz, origen, paso | |
| border, frame | borde, marco | |
| data area | área de datos | Geometric area of page pixels (2.2). |
| data region | región de datos | Bytes of the container (4.6). Kept apart from «área». |
| label band, label strip, font strip | banda del rótulo, tira del rótulo, tira de la fuente | |
| character, character cell, glyph, logo | carácter, celda de carácter, glifo, logotipo | |
| interleave | entrelazado | |
| spread | dispersión | Container spread (4.6); kept apart from «entrelazado». |
| page code | código de página | |
| Golay code, (extended) Hamming code, Reed-Solomon code | código de Golay, código de Hamming (extendido), código Reed-Solomon | |
| parity, parity bytes, parity level | paridad, bytes de paridad, nivel de paridad | Never shown in the window. |
| check (of a tag), check digits | control, dígitos de control | Rejected: «suma de comprobación». |
| header, header copy | cabecera, copia de la cabecera | |
| magic | firma mágica (`magic`) | Field name stays in code font. |
| well-formed, acceptable, valid | bien formada, aceptable, válido | "Valid" is «válido» everywhere in `format.es.md`, never «bien formado» or «aceptable», which are the defined terms of 6.2. |
| untrusted | no fiable | Heading «La cabecera no es fiable». |
| container, stream | contenedor, flujo | |
| payload, body | carga útil, cuerpo | |
| padding, padded with zeros | relleno, rellenado con ceros | «se rellenará con ceros hasta completar una página entera». |
| erasure | borrado | Coding-theory term. |
| generator polynomial, field polynomial | polinomio generador, polinomio del cuerpo | GF(256) stays. |
| big-endian | big-endian (byte más significativo primero) | |
| normative, informative | normativo, informativo | |
| test vectors, conformance vectors | vectores de prueba, vectores de conformidad | |
| encoder, decoder, reader | codificador, decodificador, lector | "Reader" in parts 6 and 7 is any program that reads pages. |
| reference decoder | decodificador de referencia | |
| promise | promesa | |
| plain, tagged, self-identifying document | documento simple, documento con etiqueta, documento autoidentificable | |

## Strength of claims

- **Verified** — «verificado», with the reserved root. Never softened
  («probablemente correcto») and never strengthened («garantizado»). "Only
  the fingerprint makes a file verified" «Solo la huella hace que un archivo
  quede verificado».
- **Recoverable vs recovered** — «recuperable» says the pages read should be
  enough; «se puede reconstruir» (possibility) versus «reconstruida» (done).
- **Promise of the tools** — «puede perder N páginas», «se pueden perder»:
  the modal «poder», not «resiste» (stronger).
- **"Has been shown"** — «muestran las pruebas» (title «Qué muestran las
  pruebas y qué no», last heading «Qué no muestran las pruebas»); in a sentence
  «se ha visto». Not «se ha demostrado» or «está probado» (proved), and not
  «se ha mostrado», which first suggests "displayed".
- **"May contain wrong parts", "may be damaged"** — keep «puede»: «puede
  contener partes erróneas», «puede estar dañado».
- **Warnings** stay as firm as English: «no se ha guardado».

## Never translated

- The words `optar`, `optar-gui`.
- Command names `encode`, `decode`; option names (`--paper`, `--dots`,
  `--protect`, `--compatible`, `--format`, `--to`, `--label`, `--no-tag`,
  `--force`, `--debug-images`, `--no-slow-reader`, `--self-test`,
  `--version`, `-o`, …).
- Option values: `none`, `standard`, `high`, `a4`, `letter`, `pdf`, `png`,
  `pgm`, `medium`, `big`, `large`, `xlarge`. (The window's selector names are
  translated, see above.)
- Metavariables: `INPUT`, `BASE`, `OUTPUT`, `LABEL`, `STRING`,
  `BASE_NNNN_debug.png`.
- File names and extensions, environment variables, code, constants, header
  field names, the tag parts `SIZE`, `FINGERPRINT`, `CC`, format strings,
  hex values.
- Product and standard names: PySide6, Ghostscript, MkDocs, PyInstaller,
  SHA-256, CRC-32, PNG, TIFF, BMP, PGM/PPM, JPEG, PDF, GF(256), dpi;
  «Releases» (the GitHub page name).
- Version numbers.

## Agreement patterns the templates need

Spanish has two plural categories: `one` (exactly 1) and `other` (0, 2, 5,
11, 21, 101, …). Nouns: página / páginas (f), escaneo / escaneos (m), bloque
/ bloques (m), byte / bytes (m), punto / puntos (m), símbolo / símbolos (m),
palabra de código / palabras de código (f), píxel / píxeles (m).

Participles and adjectives after a number agree with the noun named in the
`en.toml` comment, which is often not in the string:

- pages (feminine): `gui.state.repaired` «2 reparadas», `gui.state.slow`
  «2 leídas por el lector lento», `gui.state.damaged` «1 dañada»,
  `gui.health.*` state word «Reparada», «Dañada», `gui.READ_SLOWLY*`
  «Leída…», `cli.scan.note_slow` «(leída…)»;
- blocks (masculine): `gui.detail.repaired` «3 reparados», `gui.detail.lost`,
  `gui.detail.restored`, the «perdidos» in `gui.health.damaged`;
- symbols (masculine): `cli.stat_corrected` «5 corregidos»,
  `cli.stat_uncorrectable`;
- scans (masculine): `cli.probe.*` «no identificado», `gui.coarse.unreadable`
  «Escaneado…».

Verbs agree with the counted noun: «se reparó 1 byte» / «se repararon 2
bytes»; «falta la página 3» / «faltan las páginas 3 y 4». In «{read} de
{count} páginas» the verb takes the plural of «páginas» («solo se han leído
1 de 4 páginas»), which Spanish accepts.

## Site navigation

For `mkdocs.yml`, `nav_translations` of the `es` entry (keys are the English
titles exactly as written) and `site_description`.

| English | Spanish |
|---|---|
| Home | Inicio |
| Using optar | Uso de optar |
| Install | Instalación |
| Put a file on paper | Pasar un archivo al papel |
| Read it back | Recuperar el archivo |
| Scans that are too coarse | Escaneos de resolución demasiado baja |
| Command line | Línea de comandos |
| Reference | Referencia |
| How a page identifies itself | Cómo se identifica una página |
| What has and has not been shown | Qué muestran las pruebas y qué no |
| Format specification | Especificación del formato |
| Project | Proyecto |
| Development | Desarrollo |
| History | Historia |

- **site_description:** Guardar archivos en papel con una impresora láser y
  un escáner
- **site_name:** optar (unchanged)
- **Language name** (`[language].name` and the switcher): Español

## Interface strings the pages quote

Page translators copy these from `src/optar/locale/es.toml` exactly (the
English page quotes the English in the same place). The most quoted ones:

| English (as the page quotes it) | Spanish (catalogue) | Key |
|---|---|---|
| Put on paper | Pasar al papel | `gui.WRITE_TAB` |
| Read from paper | Leer del papel | `gui.READ_TAB` |
| + Add scans… | + Añadir escaneos… | `gui.ADD_SCANS` |
| Remove | Quitar | `gui.REMOVE_SCAN` |
| Save file… | Guardar archivo… | `gui.SAVE_FILE` |
| Replace scan… | Reemplazar escaneo… | `gui.REPLACE_SCAN` |
| Use this scan | Usar este escaneo | `gui.USE_SPARE` |
| Switch to this document | Cambiar a este documento | `gui.SWITCH_DOCUMENT` |
| Assign to page… | Asignar a página… | `gui.ASSIGN_PAGE` |
| Start a document by hand… | Componer documento a mano… | `gui.START_BY_HAND` |
| Being read | En lectura | `gui.BEING_READ_SECTION` |
| Not part of this file | No pertenecen a este archivo | `gui.NOT_PART_OF_THIS_FILE` |
| File:, Paper:, Name:, Prints as:, Dot size:, Protection: | Archivo:, Papel:, Nombre:, Se imprime como:, Tamaño de punto:, Protección: | `gui.*_FIELD` |
| Choose… | Elegir… | `gui.CHOOSE_FILE` |
| Create PDF… | Crear PDF… | `gui.CREATE_PDF` |
| Compatible with optar 0.2 and the original optar | Compatible con optar 0.2 y el optar original | `gui.COMPATIBLE` |
| Standard, Medium, Big, Large, Extra large (dot sizes) | Estándar, Mediano, Grande, Muy grande, Extragrande | `gui.dots.*` |
| None, Standard, High (protection) | Ninguna, Estándar, Alta | `gui.protection.*` |
| Waiting | En espera | `gui.WAITING` |
| Opening the file / Finding the page / Identifying the page / Reading the data | Abriendo el archivo / Buscando la página / Identificando la página / Leyendo los datos | `gui.step.*` |
| Slower reader: sampling; pass 4 of 5 | Lector lento: muestreo; Lector lento: pasada 4 de 5 | `gui.step.slow-sample`, `gui.step.slow-fit` |
| Good | Correcta | `gui.health.good` |
| Repaired · N | Reparada · N | `gui.health.repaired` |
| Damaged · N lost | Dañada · N perdidos | `gui.health.damaged` |
| Read by the slower reader | Leída por el lector lento | `gui.READ_SLOWLY_ROW` |
| Not readable | Ilegible | `gui.health.unreadable` |
| Missing | Ausente | `gui.health.missing` |
| Spare | De repuesto | `gui.row.spare` |
| Scanned at about 200 dpi, which is too coarse to read | Escaneado a unos 200 dpi, una resolución demasiado baja para leerlo | `gui.coarse.unreadable` |
| File recovered and verified · N bytes | Archivo recuperado y verificado · N bytes | `gui.VERIFIED`, `count.byte` |
| Does not match the fingerprint on the paper | No coincide con la huella del papel | `gui.state.mismatch` |
| Recoverable: page 3 missing, can be repaired from the others | Recuperable: falta la página 3, se puede reconstruir a partir de las demás | `gui.state.recoverable` |
| Recoverable: page 3 missing, repaired from the others · matches the fingerprint | Recuperable: falta la página 3, reconstruida a partir de las demás · coincide con la huella | `gui.state.recovered`, `gui.state.matches` |
| Working… 3 of 6 scans read | Procesando… 3 de 6 escaneos leídos | `gui.scans_read_working` |
| Checking the fingerprint… | Comprobando la huella… | `gui.state.checking` |
| All N pages read · cannot be verified (no tag) | Leídas las N páginas · no se puede verificar (sin etiqueta) | `gui.state.all_read`, `gui.state.no_tag` |
| 4 of 6 pages good · 1 damaged · 1 missing | 4 de 6 páginas correctas · 1 dañada · 1 ausente | `gui.state.good`, `.damaged`, `.missing` |
| the worst spot used 57% of its repair capacity (18 of 32): a moderate margin | la peor zona usó el 57 % de su capacidad de reparación (18 de 32): un margen moderado | `gui.margin.moderate` |
| Reading a coarse scan with the slower reader; this takes about a minute | Leyendo un escaneo de baja resolución con el lector lento; esto lleva alrededor de un minuto | `gui.READING_COARSE` |
| Language / System default | Idioma / Idioma del sistema | `gui.LANGUAGE_MENU`, `gui.SYSTEM_LANGUAGE` |
| Print at actual size (100%), not "fit to page". | Imprima a tamaño real (100 %), no con «Ajustar a la página». | `cli.ACTUAL_SIZE` |
| the ordinary reader could not read this scan's data; trying the slower reader, which takes about a minute | el lector normal no pudo leer los datos de este escaneo; se prueba el lector lento, que tarda alrededor de un minuto | `cli.slow_reader` |
| file verified (N bytes) | archivo verificado (N bytes) | `cli.verified` |
| Saved anyway because of --force. | Se guardó de todos modos por --force. | `cli.force_saved.*` |
| Protection standard: can lose 1 page of 12 and still recover the file. | Nivel de protección standard: se puede perder 1 página de 12 y aun así recuperar el archivo. | `cli.protection.lose` |

Command output inside code blocks on the pages stays English, as the brief
requires.

## Templates to watch

Solved in Spanish without a template change:

1. **`gui.state.all_read`** is used only for more than one page, so its
   `one` form is never shown; it repeats `gui.state.read`'s singular. The
   `other` form is «Leídas las {n} páginas».
2. **`cli.too_few.read`**: «solo se han leído {read} de {count} páginas»
   keeps the plural verb also for `{read}` = 1, which Spanish accepts with
   «X de Y páginas».
3. **`gui.health.restored`**: «Reparada · {n} por la protección» would read
   as "by {n} protections"; the count goes last: «Reparada por la protección
   del documento · {n}».
4. **File names as subject**: `gui.rejected.*` start «El escaneo {name}…» so
   the verb has a noun to agree with.
5. **`cli.dot_need`** «{name} {dpi}» uses the singular selector names
   («Estándar 600, Mediano 400…»), as label-like items of a list.
6. **`err.*`**: «B» for bytes and «pág.» for pages where a raw number stands
   before the noun.
7. **Grouping of four-digit numbers**: the program writes «1.000»; the RAE
   prefers «1000». Not a template matter; noted for the reviewer.
