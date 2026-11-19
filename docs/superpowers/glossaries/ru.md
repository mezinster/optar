# Russian glossary (`ru`)

Working paper for the Russian translation of optar: the catalogue
`src/optar/locale/ru.toml` and the pages `docs/<page>.ru.md`. It follows
section 1 of `docs/superpowers/translation-brief.md`. The explanations are in
English; the terms are Russian. Once a term is chosen here it is used the same
way in the window, the command line and every page.

Russian is the pilot language. The Ukrainian and Belarusian translators may
take the *concept* choices from here (which idea each word carries, which
words were rejected and why); the morphology notes are Russian-only.

## General conventions

- **Address.** Polite «вы», written lower-case (the norm in Russian software;
  capital «Вы» is for personal letters). Used the same way everywhere.
- **Buttons and menu items** use the infinitive: «Сохранить файл…»,
  «Добавить сканы…», «Заменить скан…». **Instructions** in messages and pages
  use the polite imperative: «Отсканируйте страницу заново».
- **Status words** in rows and in the bottom bar are short participles or
  invariant phrases («Повреждена», «В порядке»), not full sentences.
- **Typography.** Quotes «ёлочки»; dash «—» with spaces in prose; en dash «–»
  without spaces in number ranges («страницы 2–4») where the catalogue writes
  the range; ellipsis «…» as one character, as in English. The letter «ё» is
  written («повреждён», «ещё»).
- **Numbers.** The catalogue's thousands separator is a no-break space
  (`[format].group`). Outside code blocks, in prose and in table cells
  alike, write Russian numbers: a no-break space between thousands
  («199 773», «200 000») and a decimal comma («0,36»). Inside code blocks,
  commands and anything a user types, and in all of `format.ru.md`, numbers
  stay exactly as in English, as the brief requires. Percent: «18%» without
  a space, as most Russian software does.
- **optar** is always lower-case, also at the start of a sentence, as in
  English. It is not declined: «в optar», «программа optar».
- **«Страница»** is a sheet of paper carrying dots. A page of this website is
  «раздел», never «страница», so the two never meet in one sentence
  («см. раздел „Как опознаётся страница“»).

## Terms

### The brief's required terms

| English | Russian | Notes |
|---|---|---|
| dot | точка | Plural forms: точка / точки / точек. "Data dot" «точка данных», "printer dot" «точка принтера» (spec only). Not «пиксель»: pixels are separate (see the spec terms). |
| dot size | размер точек | Plural «точек», because a page has many dots: «Размер точек:», «для этого размера точек». |
| block | блок | Masculine: блок / блока / блоков. One error-correction unit; the window repairs or loses blocks. In the spec the "padding block" is «блок заполнения»; the "block of device dots" in 5.1 is rendered «квадрат точек принтера», to keep «блок» for the window's meaning. |
| protection | защита | Window label «Защита:». In prose the first mention on a page is «защита от повреждений». **Never the adjective «защищённый»**: in Russian it suggests a password or encryption. Say «документ с защитой», «распечатка с защитой», «без защиты». Rejected: «избыточность» (correct but technical), «резерв» (vague). |
| fingerprint | отпечаток | Masculine. The established Russian word for a key or hash fingerprint («отпечаток ключа»). Rejected: «хеш» (names the method, not the role), «контрольная сумма» (claims a checksum, which is a different and weaker thing). Full form «отпечаток файла» where the sentence needs it. |
| tag | метка | Feminine: метка / метки / меток. The bracketed `[SIZE:FINGERPRINT:CC]` at the start of a label. «надпись с меткой», «без метки» (untagged). Rejected: «тег» (reads as an HTML or hashtag tag), «ярлык» (a shortcut in Windows). Because «метка» is taken, the marks on the scan preview are «выделены» / «выделение», never «метка» or «отметка». |
| label | надпись | Feminine. The line printed at the bottom of every page. Rejected: «подпись» (in this program, next to "fingerprint" and "verified", it would read as a digital signature), «этикетка» (a stuck-on sticker), «метка» (taken by "tag"). "Label band" is «полоса надписи», "label strip" «лента надписи» (spec). |
| spare | запасной скан | Row title «Запасной», detail tag «запасной». Masculine, agreeing with «скан». Rejected: «лишний» (sounds like a mistake), «резервный» (sounds like a backup copy made on purpose). |
| scan (noun) | скан | Masculine: скан / скана / сканов. Usual word in Russian scanning software. Rejected: «отсканированное изображение» (too long for buttons and rows), «изображение» (loses the meaning). |
| scan (verb) | отсканировать (сканировать) | "Rescan" «отсканировать заново»; «пересканировать» is avoided as colloquial. "Scan at 600 dpi" «сканируйте с разрешением 600 dpi» / short «сканировать при 600 dpi». |
| printout | распечатка | Feminine. The pages as printed, the physical set. Kept apart from «документ» (the logical set of pages carrying one file) exactly as English keeps "printout" and "document" apart. |
| document | документ | A set of pages that carries one file. |
| page | страница | Feminine: страница / страницы / страниц; accusative страницу / страницы / страниц. Rejected: «лист» (a sheet has two sides; an optar page is one printed side). See the general convention on «раздел». |
| slower reader | медленный метод чтения (short: медленный метод) | "The ordinary reader" is «обычный метод чтения» / «обычный метод». First mention on a page: «второй, более медленный метод чтения». The English comparative is dropped in the name because Russian names do not carry it. Rejected: «считыватель» (sounds like hardware), «медленный режим» (a mode is something the user chooses; this runs by itself). "Read by the slower reader" «прочитана медленным методом». "Slower reader for coarse scans" «медленный метод для сканов с низким разрешением». |
| self-identifying page | самоопознающаяся страница | Plural «самоопознающиеся страницы». Built on «опознать» (identify), which the window uses for scans («скан не опознан»), so the term and the verb share a root. On first mention in a page add the gloss «(страницы, которые сами сообщают, к какому документу они относятся и какой у них номер)». Rejected: «самоидентифицирующаяся» (correct but heavy and bookish), «самоописывающаяся» (means self-describing, a different idea), «страница с заголовком» (loses the name used in option help and headings). |
| verified | проверен (файл проверен) | The established rendering of "verified" in Russian software («проверенный издатель»). Always means: the recovered file matched its fingerprint. To keep it exact, the root «провер-» is **reserved** for verified / verification: "not verified" «не проверен», "did not verify" «не прошёл проверку», "cannot be verified" «проверить нельзя». Checking the fingerprint is «сверка с отпечатком» (see "check"). Rejected: «подтверждён» (vaguer), «верифицирован» (bookish), «сверен» (only says it was compared, which is weaker), anything with «гарантированно» (stronger). |
| repaired | исправлен (repair: исправить, исправление) | The protection or the page's error correction fixed damaged data: «исправлено 6 912 байт», «Исправлена · 3». Exception that Russian forces: a *missing* page cannot be «исправлена»; for a missing page "repaired from the others" is «восстановлена по остальным» (the same verb as "rebuild" and "recover"). |
| lost | потерян (потерянный) | Blocks that could not be repaired («потеряно 3»), and a whole page lost from the printout («можно потерять 1 страницу из 12»). Distinct from "missing". Rejected: «утерян» (official register, documents lost by an office). |
| damaged | повреждён / повреждена | Page state «Повреждена». "Damage" «повреждения» (plural is the natural Russian for stains, tears). |
| missing | отсутствует; нет | A page of which no scan has been added. State «Отсутствует»; inside a sentence «нет страницы 3» / «нет страниц 2 и 3». Not «потеряна»: the paper may exist, only the scan is missing. |

### The window's vocabulary

| English | Russian | Notes |
|---|---|---|
| good (page state) | в порядке | Invariant, so it needs no agreement: «В порядке», «4 из 6 страниц в порядке». Rejected: «хорошая» (agrees in gender and number, and sounds like praise). |
| not readable, unreadable | не читается (state); нечитаемый (attribute) | State «Не читается»; list section «Не читаются»; "could not be read" «не удалось прочитать»; "bytes unreadable" «байт не читается / не читаются». |
| recoverable (document state) | восстановимо | Neuter predicative, an invariant state word. Used for both states whose English label is "Recoverable", the one still to be repaired and the one already repaired, because English keeps one label for both. |
| recovered | восстановлен | The file obtained from the pages: «восстановленный файл», «Файл восстановлен и проверен». "What was recovered" (best effort) «то, что удалось восстановить». |
| rebuild (a lost page) | восстановить | Docs only. Same verb as "recover"; Russian has no separate everyday word, and the meaning is the same. |
| corrected (dots, symbols, bits) | скорректирован | The page code or the slower reader fixed a dot, bit or symbol. Kept apart from "repaired" as English keeps them apart: «скорректировано 265 112 точек · исправлено 6 912 байт защитой документа». "Error correction" «коррекция ошибок», "error-correcting code" «корректирующий код» (both standard Russian terms). |
| uncorrectable, beyond correction | неисправимый; не поддаётся коррекции | Means "cannot be fixed at all". Short form «неисправимый» where space is tight (command-line statistics); «не поддаётся коррекции» in prose. |
| repair capacity, budget | ресурс исправления | "Used 18 of 32" «израсходовано 18 из 32». "The worst spot" «худшее место». |
| margin (wide, moderate, close to the limit) | запас (большой запас, умеренный запас, на пределе) | |
| check the fingerprint, checking | сверить с отпечатком, сверка | «Сверка с отпечатком…». Keeps «провер-» free for "verified". |
| matches / does not match the fingerprint | совпадает / не совпадает с отпечатком | |
| mismatch | несовпадение | |
| identify (a scan), identified | опознать, опознан | «Опознание страницы» (the step), «скан не опознан». Rejected: «идентифицировать» (bookish), «определить» (too vague). |
| assign (a scan) to a page | указать страницу | Button «Указать страницу…»; prose «указать для скана страницу вручную». Rejected: «назначить» (bureaucratic), «привязать». |
| start a document by hand, put together by hand | собрать документ вручную, собран вручную | One verb for both, so the button and the later caution match. |
| replace (scan) | заменить | |
| use this scan | взять этот скан | Button «Взять этот скан»: shorter than «Использовать этот скан», which was the longest button. |
| switch to this document | перейти к этому документу | |
| add scans | добавить сканы | |
| remove | убрать | Removes a scan from the list, does not delete the file. «Удалить» would suggest deleting the file from disk. |
| being read, waiting, working | читается, в очереди, обработка | Section «Читаются», row «Читается…»; step «В очереди» (the scan waits its turn); «Обработка…». |
| step (of reading) | этап | Steps: «Открытие файла», «Поиск страницы», «Опознание страницы», «Чтение данных», «Медленный метод: выборка», «Медленный метод: проход {current} из {total}». |
| pass (of the slower reader) | проход | |
| coarse scan, too coarse | скан с низким разрешением; со слишком низким разрешением | Russian speaks of resolution, not of coarseness: "scanned too coarsely" «разрешение скана слишком низкое». Rejected: «грубый скан» (a calque; «грубый» also means rude). |
| resolution | разрешение | dpi stays «dpi». |
| put on paper | записать на бумагу | Tab «Записать на бумагу». |
| read from paper | прочитать с бумаги | Tab «Прочитать с бумаги». |
| printed name, prints as | печатается как | Field «Печатается как:». |
| name (of the file, on the label) | имя | Field «Имя:», «(без имени)». |
| compatible (printout) | совместимая (распечатка) | Checkbox «Совместимость с optar 0.2 и первоначальной программой optar»: a noun, because a short adjective on a checkbox has no visible subject. |
| original optar, the C program | первоначальная программа optar на C | Rejected: «оригинальная» (in Russian also "unusual"), «исходная» (clashes with «исходный код»). |
| dot size names: Standard, Medium, Big, Large, Extra large | Стандартные, Средние, Большие, Крупные, Очень крупные | Plural adjectives agreeing with «точки». Big / Large / Extra large map to Большие / Крупные / Очень крупные, so the last two keep the English pair "Large" / "Extra large". Capitalised only as a selector entry or at the start; in running text lower-case («стандартные точки», «со стандартными точками», «для крупных точек»). |
| protection levels: None, Standard, High | Нет, Стандартная, Высокая | Feminine, agreeing with «защита». In prose «стандартная защита», «высокая защита», «без защиты». |
| paper names: A4, US Letter | A4, US Letter | Kept: they are names of paper sizes; in prose «бумага Letter». |
| actual size (100%), fit to page | в натуральную величину (100%), «По размеру страницы» | The second is quoted as the print dialog of Russian Windows names it. |
| grayscale, colour, black and white | в оттенках серого, цветной, чёрно-белый | |
| bottom bar | строка внизу (строка состояния) | |
| progress bar | индикатор выполнения | |
| row, list of scans | строка, список сканов | |
| preview, marked | просмотр, выделены | Marks on the preview are «выделены», never «метка» (see "tag"). |
| outline of a page | контур страницы | |
| another printout | другая распечатка | «не относится к этому файлу». |
| file verified · N bytes | Файл восстановлен и проверен · N байт | |
| untagged, no tag | без метки, нет метки | |

### The command line's vocabulary

| English | Russian | Notes |
|---|---|---|
| symbol (code symbol on a page) | символ | Masculine: символ / символа / символов. The coding-theory term. Label characters are «знак», so «символ» is only ever the code symbol. |
| codeword | кодовое слово | Neuter: кодовое слово / кодовых слова / кодовых слов. |
| corrected | скорректирован | See the window's vocabulary. |
| uncorrectable | неисправимый | |
| byte | байт | байт / байта / байт («5 байт», not «байтов»: the usual form with units). |
| encode / decode | закодировать / декодировать | Command names `encode`, `decode` stay English. |
| option (of a command) | параметр | «параметр --protect». Rejected: «опция» (colloquial), «ключ» (old-fashioned). |
| usage, positional arguments, options | использование, позиционные аргументы, параметры | argparse headings. |
| exit status | код возврата | |
| stdout, stderr | stdout, stderr | Kept; «стандартный вывод» may be added in prose. |
| gap (in page numbering) | пропуск | |
| ignored | пропущен | «пропущено 2 скана другого документа». |
| force | (option `--force`, not translated) | "Saved anyway because of --force" «Всё равно сохранён из-за --force». |

### Format specification terms (`format.md`)

| English | Russian | Notes |
|---|---|---|
| page pixel, data pixel, scan pixel | пиксель страницы, пиксель данных, пиксель скана | пиксель / пикселя / пикселей. |
| page format | формат страницы | |
| format string | строка формата | |
| layout | макет | Paper + dot size + page format. |
| grid | сетка | |
| cross, origin, pitch | крест, начало креста, шаг крестов | |
| border, frame | рамка | The page's black border and the "page frame" are the same thing in Russian. |
| data area | область данных | Geometric area of page pixels (section 2.2). |
| data region | зона данных | Bytes of the container (section 4.6). Kept apart from «область данных». |
| label band, label strip, font strip | полоса надписи, лента надписи, лента шрифта | |
| character (of the label), character cell, glyph, logo | знак, ячейка знака, глиф, логотип | |
| channel position | позиция в канале | |
| narrow strip, wide strip | узкая полоса, широкая полоса | |
| word | слово | data word of `small` bits. |
| interleave | перемежение | Standard term. |
| spread | разнесение | Container spread (4.6); kept apart from «перемежение». |
| page code | код страницы | |
| Golay code, (extended) Hamming code, Reed-Solomon code | код Голея, (расширенный) код Хэмминга, код Рида — Соломона | Usual Russian spellings. |
| parity, parity bytes, parity level | чётность, байты чётности, уровень чётности | The usual Russian term (as in RAID). Never shown in the window. Rejected: «проверочные байты» (uses the reserved root «провер-»), «контрольные байты» (clashes with the tag's check). |
| check (of a tag), check digits | контрольное значение, контрольные цифры | Rejected: «контрольная сумма» (a checksum of the data, which this is not). |
| header, header copy | заголовок, копия заголовка | |
| magic | сигнатура | Field name `magic` stays in code font. |
| well-formed, acceptable, valid | корректный, допустимый, действительный | A well-formed header copy, an acceptable header, a valid tag. "Valid" is «действительный» everywhere in `format.ru.md` (a valid page, tag, document, header, codeword; "invalid" «недействительный»), never «корректный» or «допустимый»: those two are the defined terms of 6.2, and using them for "valid" would narrow a rule. |
| untrusted | не заслуживает доверия; ему нельзя доверять | Heading «Заголовку нельзя доверять». Rejected: «недоверенный» (calque). |
| container | контейнер | |
| stream | поток | |
| payload, body | полезная нагрузка, тело | «тело страницы», «тело документа». |
| padding, padding stream, padded with zeros | заполнение, поток заполнения, дополнен нулями | The noun is «заполнение» (the docs' "filled with a fixed pattern" fits it); the verb for a file is «дополнен нулями до целой страницы». |
| erasure | стирание | Coding-theory term. |
| generator polynomial, field polynomial | порождающий многочлен, многочлен поля | GF(256) stays as written. |
| big-endian | старшим байтом вперёд (big-endian) | |
| most significant bit | старший бит | |
| normative, informative | нормативный, справочный | As in Russian standards. |
| test vectors, conformance vectors | тестовые векторы, векторы соответствия | |
| encoder, decoder, reader (any implementation) | кодировщик, декодер, программа чтения | "Reader" in parts 6 and 7 is any program that reads pages; this project's two readers are «обычный метод» and «медленный метод». |
| reference decoder | эталонный декодер | |
| promise (of the tools) | обещание | |
| plain, tagged, self-identifying document | простой документ, документ с меткой, самоопознающийся документ | |

### Terms added with the catalogue and the pages

Terms the page translators used beyond the list above, and terms the catalogue
needed. They are binding in the same way.

| English | Russian | Notes |
|---|---|---|
| desktop application | настольное приложение | |
| version tag (git) | тег версии | Only for git tags; «метка» stays the label tag. |
| sheet-fed scanner | протяжной сканер | |
| simulated, simulator | имитированный, имитатор | |
| withheld (page) | изъята | |
| dot impression (a dot as it looks on the scan) | собственное изображение на скане | |
| Karel "Clock" Kulhavy, Colin Dean | Карел «Clock» Кулгави, Колин Дин | |
| point (pt), paper margin | пункт (short «пт»), поле | |
| offset | смещение | |
| free text | произвольный текст | |
| check (plain sense, not the fingerprint) | контролировать | Keeps «провер-» reserved. |
| threshold, fill threshold | порог, порог заливки | |
| sample, sampling | отсчёт, снятие отсчётов | The slower reader's step is «выборка» in the window. |
| linear brightness scale | линейная шкала яркости | |
| slice | отрезок | |
| facet, neighbouring facets | грань, соседние грани | |
| confidence | уверенность | |
| media box | media box | Kept as the PDF term. |
| Language (menu), System default | Язык, Как в системе | |
| protection level `{level}` on the command line | Уровень защиты {level} | The option value stays English and reads as a name: «Уровень защиты standard: …». |
| pixels (in error messages with a number before the noun) | пикс. | Abbreviation, so it needs no agreement: «скан 100 × 141 пикс.». |
| rows of pixels | в строках пикселей | Said after the numbers: «{height} вместо {rows} (в строках пикселей)». |
| decode again | повторите декодирование | The command name `decode` is not used as a verb. |
| … the slower reader is started | запускается медленный метод | Command line, while a coarse scan is tried. |
| sentence end added by the window (`gui.sentence`) | «{words}.» | Russian full stop, as in English. |
| page range | 2–4 | En dash without spaces, in `gui.list.range` and every `gui.run.*.range`. |
| real (scan, document, printout) | реальный | Not «настоящий»: «настоящий документ» is the official phrase for "the present document". («до настоящего размера», "to its true size", stays.) |
| window titles of file dialogs | infinitive | «Выбрать файл для записи на бумагу», «Выбрать скан страницы {page}», like «Добавить сканы», «Сохранить PDF», «Указать страницу». |
| could not be decoded in any orientation (`gui.reason.not_decodable`) | Не удалось декодировать скан ни в одной ориентации | A full sentence with a subject and a capital letter, as the other reasons: the window shows it as a sentence of its own. |
| scanned upright | отсканирована в прямом положении (не повёрнута) | Not «не перевёрнута», which covers only upside down, not a page turned by 90°. |

## Strength of claims

- **Verified** — «проверен», with the reserved root (above). Never softened
  («вероятно цел», «скорее всего верен») and never strengthened
  («гарантированно», «подтверждено полностью»). "Only the fingerprint makes a
  file verified" «Проверенным файл делает только отпечаток».
- **Recoverable vs recovered** — «восстановимо» says the pages read *should
  be enough*; it promises nothing more than English does. «Восстановлен» is
  said only of what has been rebuilt. "Can be repaired from the others"
  «можно восстановить по остальным» (possibility); "repaired from the others"
  «восстановлена по остальным» (done).
- **Promise of the tools** — «можно потерять N страниц» keeps the modal
  «можно» (may), not «выдержит» (will withstand), which is stronger.
- **"Has been shown", "is expected"** — «показано» (demonstrated), not
  «доказано» (proved, stronger); "is expected not to be enough" «по-видимому,
  не хватит» / «ожидается, что не хватит», not «не хватит».
- **"May contain wrong parts", "may be damaged"** — keep «может»: «может
  содержать неверные части», «может быть повреждён».
- **Warnings** stay as firm as English: "was not saved" «не сохранён», not
  «не удалось сохранить» when the program chose not to save.

## Never translated

- The words `optar`, `optar-gui`.
- Command names: `encode`, `decode`.
- Option names: `--paper`, `--dots`, `--protect`, `--compatible`, `--format`,
  `--to`, `--label`, `--no-tag`, `--force`, `--debug-images`,
  `--no-slow-reader`, `--self-test`, `--version`, `-o`, and all others.
- Option values: `none`, `standard`, `high`, `a4`, `letter`, `pdf`, `png`,
  `pgm`, `standard`, `medium`, `big`, `large`, `xlarge`. (The window's
  *selector names* for the same things are translated, see above; a value
  typed on the command line is not.)
- Metavariables: `INPUT`, `BASE`, `OUTPUT`, `LEVEL`, `TEXT`, `STRING`, `X`,
  `BASE_NNNN_debug.png`, and the `N` / `T` of "can lose N page(s) of T".
- File names and extensions: `BASE_0001.png`, `optar_out`, `.pdf`, `.png`,
  `.pgm`, `COPYING`, paths.
- Environment variables (`OPTAR_LANG`, `QT_QPA_PLATFORM`), code, constants
  (`MAX_PAGES`, …), header field names (`magic`, `parity`, …), the tag parts
  `SIZE`, `FINGERPRINT`, `CC`, `CHECK`, format strings such as
  `0-65-93-24-3-1-2-24`, hex values.
- Product and standard names: PySide6, Ghostscript, MkDocs, PyInstaller,
  SHA-256, CRC-32, PNG, TIFF, BMP, PGM/PPM, JPEG, PDF, GF(256), dpi.
- Version numbers (0.2.0, v0.5.0).

## Agreement patterns the templates need

Russian has three plural forms (`one` 1, 21, 101…; `few` 2–4, 22–24…; `many`
0, 5–20, 11–14, 25…). The forms of the main nouns:

| Noun | `one` | `few` | `many` | after «из N» (genitive) |
|---|---|---|---|---|
| страница (f) | страница | страницы | страниц | страницы / страниц / страниц |
| страница, accusative («потерять N …») | страницу | страницы | страниц | |
| скан (m) | скан | скана | сканов | скана / сканов / сканов |
| блок (m) | блок | блока | блоков | |
| байт (m) | байт | байта | байт | |
| точка (f) | точка | точки | точек | |
| символ (m) | символ | символа | символов | |
| кодовое слово (n) | кодовое слово | кодовых слова | кодовых слов | |
| пиксель (m) | пиксель | пикселя | пикселей | |

A past participle after a number agrees with the (often unstated) noun:
pages are feminine («1 исправлена, 2 исправлены, 5 исправлено»), blocks and
symbols masculine («1 исправлен, 2 исправлены, 5 исправлено»). The `one`
form is also used for 21, 31, …, so it must not say «одна».

The invariant pattern «прочитано сканов: {done} из {n}» (noun in the genitive
plural before the colon) avoids agreement entirely and is the first choice
for counters in the bottom bar. A phrase that the window only ever shows after
« · » starts lower-case, as Russian does mid-line («… · прочитано сканов: 3 из
6», `gui.scans_read`; «документ напечатан без защиты…», `gui.repair.unprotected`).
After a closing ellipsis a new phrase is capitalised («Обработка… Прочитано
сканов: 3 из 6», `gui.scans_read_working`). Row-state labels («В порядке»,
«Исправлена», «Прочитана медленным методом») stay capitalised: they are labels.
"Identifies the pages" said of the printed name (for people, not the program)
is «узнать», not the reserved «опознать» (`gui.name.printed`).

## Site navigation

For `mkdocs.yml`, `nav_translations` of the `ru` entry (keys are the English
titles exactly as written) and `site_description`.

| English | Russian |
|---|---|
| Home | Главная |
| Using optar | Работа с optar |
| Install | Установка |
| Put a file on paper | Записать файл на бумагу |
| Read it back | Получить файл обратно |
| Scans that are too coarse | Сканы со слишком низким разрешением |
| Command line | Командная строка |
| Reference | Справка |
| How a page identifies itself | Как опознаётся страница |
| What has and has not been shown | Что показано, а что нет |
| Format specification | Спецификация формата |
| Project | Проект |
| Development | Разработка |
| History | История |

- **site_description:** Хранение файлов на бумаге с помощью лазерного
  принтера и сканера
- **site_name:** optar (unchanged)
- **Language name** (`[language].name` and the switcher): Русский

## Templates to watch

English templates in `en.toml` that cannot be said in Russian as given, or
only with care. Written before the catalogue; what became of each item when
`ru.toml` was written:

- Item 1 (and the list part of 2) is fixed in code: those seven entries now
  have the forms `single` (the list names exactly one page) and `several`,
  chosen by the count of pages, not by the plural rule. So «страницу {pages}»
  and «её» are right in `single`.
- Item 9 is fixed: `[format].decimal` gives «8,3», so `share_small` is
  «менее 0,1%».
- Item 10 is fixed: the range is `gui.list.range` («{first}–{last}»).
- Items 3 to 8 and 11 to 16 were solved in Russian as described, without a
  change to the templates.

1. **List-keyed plurals**: `gui.state.recoverable`, `gui.state.recovered`,
   `gui.rescan.add`, `gui.rescan.worst`, `cli.summary.missing`,
   `cli.rescan_advice`, `cli.too_few.rescan`. The form is chosen by *how many
   pages the list names*, but no number stands next to the noun. Russian
   `one` is also chosen for 21, 31, 101 pages, where «страница» (singular)
   and «её» would be wrong. The `one` form has to read right for one page and
   for 21: the translator will use a number-neutral wording there (for
   example «стр. {pages}», no pronoun). A code-side fix would be to choose
   these by `count == 1` rather than by the plural rule.
2. **`cli.too_few.rescan`** additionally: "fewer than one page in
   {fraction}" — a noun after «из {fraction}» would have to agree with
   `{fraction}`, while the form is chosen by the missing count. Said without
   a noun: «меньше одной страницы из каждых {fraction}».
3. **`gui.state.all_read`**: "All {n} page read" reaches `one` only for 21,
   31, …; «все 21 страница» is awkward Russian. Will use the invariant
   «Прочитаны все страницы: {n}» in all three forms.
4. **`gui.state.good`**: "{good} of {n} page good" — the predicate agrees
   with `{good}`, the form is chosen by `{n}`. Solved with the invariant
   «в порядке» and the genitive after «из»: «{good} из {n} страниц в
   порядке».
5. **`cli.too_few.read`**: "only {read} of {count} page read" — the
   participle would agree with `{read}`, the form is chosen by `{count}`.
   Will say «удалось прочитать только {read} из {count} страниц».
6. **Bare "{n} participle" entries**: `gui.state.repaired`,
   `gui.state.slow`, `gui.state.damaged`, `gui.state.unreadable`,
   `gui.state.missing`, `gui.detail.repaired`, `gui.detail.lost`,
   `gui.detail.restored`, `gui.list.more`, `cli.stat_corrected`,
   `cli.stat_uncorrectable`. English has the same text in `one` and `other`;
   Russian needs three different forms, and their gender comes from a noun
   that is not in the string (pages: feminine in `gui.state.*`; blocks:
   masculine in `gui.detail.*`; symbols: masculine in `cli.stat_*`). The
   comments in `en.toml` are the only way to know the noun; keep them.
7. **`gui.health.repaired`, `gui.health.restored`, `gui.health.damaged`**:
   the state word is about the page (feminine «Исправлена», «Повреждена»)
   while `{n}` counts blocks; "Damaged · {n} lost" becomes «Повреждена ·
   потеряно {n}» (word order changes; «потерян / потеряны / потеряно» by
   `{n}`). "Repaired · {n} by the document's protection" puts `{n}` inside a
   phrase that Russian cannot keep in that order: «Исправлена · {n} защитой
   документа» reads as «by {n} protections»; will use «Исправлена защитой
   документа · {n}».
8. **`cli.protection.nothing`, `cli.protection.within`,
   `cli.protection.lose`**: `{level}` is the untranslated option value
   (`none`, `standard`, `high`) inside a Russian sentence. «Защита standard:»
   is not Russian; will write «Уровень защиты {level}: …» so the value reads
   as a name.
9. **`gui.slow.share`, `gui.slow.share_small`**: the number in `{share}` is
   formatted by code with a decimal point («8.3»); Russian writes «8,3».
   `share_small` is free text, so «менее 0,1%» there would disagree with
   «8.3%» next to it. Needs a localised decimal separator in code
   (`[format]` has only `group`); until then the translator keeps the point
   in `share_small` for consistency.
10. **Page lists and ranges built in code** (`_page_list` in
    `optar_gui/text.py`): ranges come out as «2-4» with a hyphen, while the
    catalogue's own `gui.run.*.range` can write «2–4» with an en dash. The two
    will look different on one screen.
11. **File names as subject or object**: `gui.rejected.unusable`,
    `gui.rejected.unusable_reason`, `gui.rejected.other_page`,
    `gui.rejected.other_document`, `gui.rejected.not_used`,
    `gui.dialog.assign_prompt`, `gui.message.created`, `gui.message.saved`,
    `cli.wrote`, `cli.wrote_pdf`, `cli.cannot_open`, `cli.gap`. A file name
    does not decline and has no gender, so the verb has nothing to agree
    with. Will put a noun before it and agree with that: «Скан {name} не
    использован…», «Создан файл {name}», «в файл {name}».
12. **`gui.detail.repairs`**: "{one} one-bit, {two} two-bit, {three}
    three-bit" — three numbers that would each need noun agreement, with no
    plural table. Will use «Исправления: однобитных — {one}, двухбитных —
    {two}, трёхбитных — {three}».
13. **`gui.message.too_many_pixels`**: "{n} pixels is more than the {limit} a
    scan may have" — the form follows `{n}`, but `{limit}` has no noun and
    the sentence shape does not exist in Russian. Will say «В скане {n}
    пикселей, а допускается не больше {limit}».
14. **Dot-size names in other cases**: `gui.paper_dots.*`,
    `gui.too_large.fits_dots.*`, `gui.too_large.fits_either.*`,
    `gui.coarse.unreadable` need the names in the nominative, instrumental
    and genitive («стандартные точки», «со стандартными точками», «для
    стандартных точек»). The per-size keys make this possible; any future
    template that inserts a dot-size *name* into a sentence (as `{dots}` in
    `gui.write.dot_size` and `{name}` in `cli.dot_need` do, where only the
    nominative works) should be kept to label-like positions.
15. **`gui.state.read`, `gui.scans_read`, `gui.scans_read_working`**: the
    natural Russian counters «Прочитано страниц: {n}», «прочитано сканов:
    {done} из {n}» are invariant, so all three plural forms will be the same
    text. That is intended, not a mistake.
16. **`cli.ACTUAL_SIZE`** and the docs quote the print dialog's "fit to
    page"; the Russian wording of that option depends on the printer driver.
    Will use «По размеру страницы», the Windows wording.
