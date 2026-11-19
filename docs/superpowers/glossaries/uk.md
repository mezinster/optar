# Ukrainian glossary (`uk`)

Working paper for the Ukrainian translation of optar: the catalogue
`src/optar/locale/uk.toml` and the pages `docs/<page>.uk.md`. It follows
section 1 of `docs/superpowers/translation-brief.md`. The explanations are in
English; the terms are Ukrainian. Once a term is chosen here it is used the
same way in the window, the command line and every page.

The terms were chosen from English and from Ukrainian technical writing
(Ukrainian Windows, GNOME/KDE, Ukrainian computing literature). The Russian
glossary was read for the *concepts* only; where the Russian word has a
Ukrainian look-alike that Ukrainian writing does not use (for example
«співпадати», «в порядку», «по замовчуванню», «опція», «при»), the native word
is chosen and the rejected one is named below.

## General conventions

- **Address.** Polite «ви», written lower-case (the norm in Ukrainian
  software; capital «Ви» is for letters to one person). Used the same way
  everywhere.
- **Buttons, menu items, dialog titles** use the infinitive: «Зберегти
  файл…», «Додати скани…», «Замінити скан…», «Вибрати файл для запису на
  папір». **Instructions** in messages and pages use the polite imperative:
  «Відскануйте сторінку повторно», «Скануйте з роздільною здатністю 600 dpi»,
  «Друкуйте у фактичному розмірі».
- **Status words** in rows and in the bottom bar are short adjectives or
  invariant phrases agreeing with «сторінка» («Справна», «Пошкоджена»,
  «Відсутня», «Не зчитується»), not full sentences.
- **Impersonal -но/-то forms** («виправлено», «зчитано», «втрачено») are the
  first choice for "was repaired", "N read" and the like: they are idiomatic
  Ukrainian, invariant, and avoid both the Russian-style passive in -ся and
  agreement with a noun the template does not contain.
- **"Default"** is «типово» (`типово: a4`). Rejected: «за замовчуванням» /
  «по замовчуванню» (calques).
- **Euphony.** The alternations у/в, і/й, з/із/зі are observed as Ukrainian
  spelling requires: «із самоідентифікацією», «зі стандартними точками»,
  «із середніми точками», «з великими точками», «у фактичному розмірі»,
  «відновлено й перевірено». A placeholder that starts the next word is
  treated as starting with a consonant.
- **Typography.** Quotes «ялинки», inner quotes „лапки“. Dash «—» with spaces
  in prose; en dash «–» without spaces in number ranges («сторінки 2–4»), where
  the catalogue writes the range. Ellipsis «…» as one character, as in
  English. Apostrophe is the typographic ’ (U+2019): «ім’я».
- **Numbers.** The catalogue's thousands separator is a no-break space
  (`[format].group`, U+00A0) and the decimal mark a comma (`[format].decimal`).
  Outside code blocks, in prose and in table cells alike, write Ukrainian
  numbers: a no-break space between thousands («199 773», «200 000») and a
  decimal comma («0,36», «2,5»). Inside code blocks, commands, anything a user
  types, and in all of `format.uk.md`, numbers stay exactly as in English, as
  the brief requires. Version numbers (0.2.0) are names and do not change.
  Percent: «18%» without a space, as in the catalogue's `gui.slow.share` and
  `gui.margin.*`.
- **Multiplication sign** in sizes: «×» with spaces («100 × 141 пікс.»), as in
  the catalogue's errors.
- **optar** is always lower-case, also at the start of a sentence, as in
  English. It is not declined: «в optar», «програма optar».
- **«Сторінка»** is a sheet of paper carrying dots. A page of this website is
  «розділ», never «сторінка», so the two never meet in one sentence
  («див. розділ „Як розпізнається сторінка“»).

## Terms

### The brief's required terms

| English | Ukrainian | Notes |
|---|---|---|
| dot | точка | точка / точки / точок. "Data dot" «точка даних», "printer dot" «точка принтера». Not «піксель»: pixels are separate. |
| dot size | розмір точок | «Розмір точок:», «з цим розміром точок». |
| block | блок | Masculine: блок / блоки / блоків. One error-correction unit; the window repairs or loses blocks. The "block of device dots" in the spec is «квадрат точок принтера», to keep «блок» for the window's meaning. |
| protection | захист | Masculine; window label «Захист:». "Protected document" is «документ із захистом», "unprotected" «без захисту». **Never the adjective «захищений»**: it suggests a password or encryption. Rejected: «надлишковість» (correct but technical), «резерв» (vague). |
| fingerprint | відбиток | Masculine: відбиток / відбитка. The established Ukrainian word for a key or hash fingerprint («відбиток ключа»). Rejected: «геш» / «хеш» (names the method, not the role), «контрольна сума» (claims a checksum, a weaker thing). Full form «відбиток файлу» where needed. |
| tag | мітка | Feminine: мітка / мітки / міток. The bracketed `[SIZE:FINGERPRINT:CC]` at the start of a label: «напис із міткою», «без мітки». Rejected: «тег» (HTML or hashtag), «ярлик» (a Windows shortcut). Because «мітка» is taken, the marks on the scan preview are «позначено» / «позначка», never «мітка». |
| label | напис | Masculine: напис / написи / написів. The line printed at the bottom of every page. Rejected: «підпис» (next to "fingerprint" and "verified" it reads as a digital signature), «етикетка» (a sticker), «мітка» (taken by "tag"). "Label band" «смуга напису», "label strip" «стрічка напису» (spec). |
| spare | запасний скан | Row title «Запасний», detail tag «запасний» (masculine, agreeing with «скан»). Rejected: «зайвий» (sounds like a mistake), «резервний» (a backup made on purpose). |
| scan (noun) | скан | Masculine: скан / скани / сканів; locative «на скані». The usual word in Ukrainian scanning software. Rejected: «відскановане зображення» (too long for buttons), «зображення» (loses the meaning). |
| scan (verb), rescan | сканувати / відсканувати; повторно відсканувати | "Scan at 600 dpi" «скануйте з роздільною здатністю 600 dpi» (short «з 600 dpi»). "Rescan" is always «повторно відсканувати» («Повторно відскануйте сторінку 3»); the noun is «повторне сканування». Rejected: «пересканувати» (colloquial), «відсканувати знову / ще раз» (kept free so that one word means one thing). |
| printout | роздруківка | Feminine: роздруківка / роздруківки / роздруківок. The pages as printed, the physical set. Kept apart from «документ», exactly as English keeps "printout" and "document" apart. |
| document | документ | A set of pages that carries one file. Genitive «документа» (not «документу»). |
| page | сторінка | Feminine: сторінка / сторінки / сторінок; accusative сторінку. Rejected: «аркуш» (a sheet has two sides; an optar page is one printed side). See the convention on «розділ». |
| slower reader | повільний метод зчитування (short: повільний метод) | "The ordinary reader" «звичайний метод зчитування» / «звичайний метод». First mention on a page: «другий, повільніший метод зчитування». The name drops the comparative, as Ukrainian names do. Rejected: «зчитувач» (sounds like hardware, a card reader), «повільний режим» (a mode is chosen by the user; this runs by itself). "Read by the slower reader" «зчитана повільним методом»; "slower reader for coarse scans" «повільний метод для сканів із низькою роздільною здатністю». |
| self-identifying page | сторінка із самоідентифікацією | Plural «сторінки із самоідентифікацією»; "self-identifying document" «документ із самоідентифікацією». A noun phrase, because the adjective forms are heavy or wrong: «самоідентифікувальна» is bookish, «саморозпізнавана» is not used, «самоописова» means self-describing, a different idea. On first mention in a page add the gloss «(сторінки, які самі повідомляють, до якого документа належать і який мають номер)». The verb "identify" (a scan) is «розпізнати», see below. |
| verified | перевірено (файл перевірено) | Always means: the recovered file matched its fingerprint. The root **«перевір-» is reserved** for verified / verification: "not verified" «не перевірено», "did not verify" «не пройшов перевірки», "cannot be verified" «перевірити не можна», "once the document is verified" «коли документ пройде перевірку». Checking against the fingerprint is «звіряння з відбитком» (see "check"). Rejected: «підтверджено» (vaguer), «верифіковано» (bookish), «звірено» (only says it was compared, weaker), anything with «гарантовано» (stronger). |
| repaired | виправлено (repair: виправити, виправлення) | The protection or the page's error correction fixed damaged data: «виправлено 6 912 байтів», «Виправлена · 3». A *missing* page is not «виправлена»: for a missing page "repaired from the others" is «відновлено з решти» (the same verb as "recover" and "rebuild"). |
| lost | втрачено (втрачений) | Blocks that could not be repaired («втрачено 3»), and a whole page lost from the printout («можна втратити 1 сторінку з 12»). Distinct from "missing". Rejected: «загублений» (mislaid, everyday). |
| damaged | пошкоджено / пошкоджена | Page state «Пошкоджена». "Damage" «пошкодження» (plural is natural for stains, tears). |
| missing | відсутня; немає | A page of which no scan has been added. State «Відсутня»; inside a sentence «немає сторінки 3» / «немає сторінок 2 і 3». Not «втрачена»: the paper may exist, only the scan is missing. Rejected: «бракує» in templates (needs a genitive construction that does not fit every entry). |

### The window's vocabulary

| English | Ukrainian | Notes |
|---|---|---|
| good (page state) | справна | Row state «Справна»; bottom bar «Справних сторінок: 4 з 6» (an invariant counter, since English "good" there also counts repaired pages). Rejected: «в порядку» / «у порядку» (a Russianism), «гаразд» (colloquial, and used for OK buttons), «без помилок» (wrong for the counter, which includes repaired pages), «ціла» (clashes with "whole page", «ціла сторінка»). Such a page is never called «Справна» when the slower reader read it. |
| read (a scan, a page, data, a file) | зчитати, зчитувати | One verb for every reading the program does: «Зчитати з паперу», «зчитано», «не вдалося зчитати». Rejected: «прочитати» (fine for a person reading text; «зчитувати» is the Ukrainian technical word for a device or program reading data). |
| not readable, unreadable | не зчитується | State «Не зчитується»; list section «Не зчитуються»; "could not be read" «не вдалося зчитати»; "bytes unreadable" «байт не зчитується / байти не зчитуються». |
| being read, waiting, working | зчитується, у черзі, обробка | Section «Зчитуються», row «Зчитується…»; step «У черзі»; «Обробка…». |
| recoverable (document state) | відновлення можливе | Used for both states whose English label is "Recoverable" (to be repaired, and already repaired), because English keeps one label for both: «Відновлення можливе: немає сторінки 3, її можна відновити з решти» / «…, її відновлено з решти». |
| recovered | відновлений, відновлено | The file obtained from the pages: «відновлений файл», «Файл відновлено й перевірено». "What was recovered" «те, що вдалося відновити». |
| rebuild (a lost page) | відновити | Docs only. Same verb as "recover". |
| from the others | з решти | «відновити з решти» (from the remaining pages). |
| corrected (dots, symbols, bits) | скориговано (скоригувати) | Kept apart from "repaired" as English keeps them apart: «скориговано 265 112 точок · захист документа виправив 6 912 байтів». "Error correction" «корекція помилок», "error-correcting code" «код із корекцією помилок». |
| uncorrectable, beyond correction | невиправний; не піддається корекції | Short «невиправних: 3» in command-line statistics; «не піддається корекції» in prose. |
| repair capacity, budget | ресурс виправлення | "used 18 of 32" «використано 18 з 32». "The worst spot" «найгірше місце». |
| margin (wide, moderate, close to the limit) | запас (великий запас, помірний запас, на межі) | |
| check the fingerprint, checking | звірити з відбитком, звіряння | «Звіряння з відбитком…». Keeps «перевір-» free for "verified". Rejected: «звірка» (colloquial). |
| matches / does not match the fingerprint | збігається / не збігається з відбитком | Rejected: «співпадає» (a Russianism). |
| identify (a scan), identified | розпізнати, розпізнано | Step «Розпізнавання сторінки», «скан не розпізнано». Rejected: «ідентифікувати» (bookish in running text; kept only inside the term «самоідентифікація»), «визначити» (too vague). |
| assign (a scan) to a page | вказати сторінку | Button «Вказати сторінку…»; prose «вручну вказати для скану сторінку». Rejected: «призначити» (bureaucratic), «прив’язати». |
| start a document by hand, put together by hand | зібрати документ вручну, зібрано вручну | One verb for both, so the button and the later caution match. |
| replace (scan) | замінити | «Замінити скан…». |
| use this scan | взяти цей скан | Button «Взяти цей скан»: shorter than «Використати цей скан». |
| switch to this document | перейти до цього документа | |
| add scans | додати скани | |
| remove | прибрати | Removes a scan from the list, does not delete the file. «Видалити» would suggest deleting the file from disk. |
| step (of reading) | етап | Steps: «Відкриття файлу», «Пошук сторінки», «Розпізнавання сторінки», «Зчитування даних», «Повільний метод: вибірка», «Повільний метод: прохід {current} з {total}». |
| pass (of the slower reader) | прохід | |
| coarse scan, too coarse | скан із низькою роздільною здатністю; надто низька роздільна здатність | Ukrainian speaks of resolution, not coarseness: "scanned too coarsely" «роздільна здатність скану надто низька». Rejected: «грубий скан» (a calque). |
| resolution | роздільна здатність | The standard term. dpi stays «dpi». Rejected: «розширення» (wrong word, a common error), «роздільність» (acceptable but less usual). |
| put on paper | записати на папір | Tab «Записати на папір». |
| read from paper | зчитати з паперу | Tab «Зчитати з паперу». |
| prints as | друкується як | Field «Друкується як:». |
| name (of the document, printed on the label) | назва | Field «Назва:», «(без назви)». The name of a file on disk is «ім’я файлу» («виберіть інше ім’я»); the two are kept apart. |
| compatible (printout) | сумісна (роздруківка) | Checkbox «Сумісність з optar 0.2 і оригінальним optar»: a noun, because a short adjective on a checkbox has no visible subject. Shortened after the native read: the checkbox says «оригінальним optar» (the program name stands for the program), prose keeps «оригінальна програма optar». |
| original optar, the C program | оригінальна програма optar, програма на C | «Первісна» was rejected: it also means primitive. Only the checkbox `gui.COMPATIBLE` uses the short «оригінальний optar». |
| dot size names: Standard, Medium, Big, Large, Extra large | Стандартні, Середні, Великі, Крупні, Дуже крупні | Plural adjectives agreeing with «точки». Big / Large / Extra large map to Великі / Крупні / Дуже крупні, so the last two keep the English pair "Large" / "Extra large". Capitalised only as a selector entry or at the start; in running text lower-case («стандартні точки», «зі стандартними точками», «для крупних точок»). |
| protection levels: None, Standard, High | Немає, Стандартний, Високий | Masculine, agreeing with «захист». In prose «стандартний захист», «високий захист», «без захисту». |
| paper names: A4, US Letter | A4, US Letter | Kept; in prose «папір Letter». |
| actual size (100%), fit to page | у фактичному розмірі (100%), «За розміром сторінки» | The second is quoted as print dialogs name the option; the exact wording depends on the driver. |
| grayscale, colour, black and white | у відтінках сірого, кольоровий, чорно-білий | |
| bottom bar | рядок унизу (рядок стану) | |
| progress bar | індикатор виконання | |
| row, list of scans | рядок, список сканів | |
| preview, marked | перегляд, позначено | Marks on the preview are «позначено», never «мітка». |
| outline of a page | контур сторінки | |
| another printout | інша роздруківка | «не належить до цього файлу». |
| untagged, no tag | без мітки, немає мітки | |
| folder | тека | Rejected: «папка» (acceptable, but «тека» is the native word in Ukrainian desktop software). |
| Language (menu), System default | Мова, Як у системі | |
| OK, Cancel, Yes, No | OK, Скасувати, Так, Ні | |

### The command line's vocabulary

| English | Ukrainian | Notes |
|---|---|---|
| symbol (code symbol on a page) | символ | символ / символи / символів. Label characters are «знак», so «символ» is only ever the code symbol. |
| codeword | кодове слово | кодове слово / кодові слова / кодових слів. |
| byte | байт | байт / байти / байтів («5 байтів»: the Ukrainian genitive plural, unlike Russian «5 байт»). |
| pixel | піксель | піксель / пікселі / пікселів. In error messages with a raw number before the noun: «пікс.». |
| encode / decode | закодувати / декодувати | Command names `encode`, `decode` stay English. "Decode again" «декодуйте знову». |
| option (of a command) | параметр | «параметр --protect». Rejected: «опція» (colloquial), «ключ» (old-fashioned). |
| usage, positional arguments, options | використання, позиційні аргументи, параметри | argparse headings. |
| exit status | код завершення | |
| stdout, stderr | stdout, stderr | Kept; «стандартний вивід» may be added in prose. |
| gap (in page numbering) | пропуск | |
| ignored | пропущено | «пропущено 2 скани іншого документа». |
| protection level `{level}` | Рівень захисту {level} | The option value stays English and reads as a name: «Рівень захисту standard: …». |
| force | (option `--force`, not translated) | "Saved anyway because of --force" «Усе одно збережено через --force». |
| allowed at most | дозволено щонайбільше | Errors: «дозволено щонайбільше {limit}». |

### Format specification terms (`format.md`)

| English | Ukrainian | Notes |
|---|---|---|
| page pixel, data pixel, scan pixel | піксель сторінки, піксель даних, піксель скану | |
| page format, format string | формат сторінки, рядок формату | |
| layout | макет | Paper + dot size + page format. |
| grid | сітка | |
| cross, origin, pitch | хрест, початок хреста, крок хрестів | |
| border, frame | рамка | The page's black border and the "page frame" are the same thing. |
| data area | область даних | Geometric area of page pixels (2.2). |
| data region | зона даних | Bytes of the container (4.6). Kept apart from «область даних». |
| label band, label strip, font strip | смуга напису, стрічка напису, стрічка шрифту | |
| character (of the label), character cell, glyph, logo | знак, комірка знака, гліф, логотип | |
| channel position | позиція в каналі | |
| narrow strip, wide strip | вузька смуга, широка смуга | |
| word | слово | Data word of `small` bits. |
| interleave | перемежування | Standard term. |
| spread | рознесення | Container spread (4.6); kept apart from «перемежування». |
| page code | код сторінки | |
| Golay code, (extended) Hamming code, Reed-Solomon code | код Голея, (розширений) код Геммінга, код Ріда — Соломона | Usual Ukrainian spellings. |
| parity, parity bytes, parity level | парність, байти парності, рівень парності | Never shown in the window. Rejected: «перевірні байти» (uses the reserved root «перевір-»), «контрольні байти» (clashes with the tag's check). |
| check (of a tag), check digits | контрольне значення, контрольні цифри | Rejected: «контрольна сума». |
| check (plain sense, not the fingerprint) | no single word: a natural turn that fits the sentence — «з’ясовує, чи…», «стежить (за тим), щоб…», noun «контроль» / «пройти контроль» | Keeps «перевір-» reserved for verified. Changed after the native read: the verb «контролювати» read like machinery in running prose («контролює, чи може він…»); it stays only in the format page's normative sentences about what a reader may or must check («повинна контролювати», «не повинна … контролювати»), where it is precise. Comparing a file with its fingerprint is verification, never «контроль» («остаточна перевірка»). |
| header, header copy | заголовок, копія заголовка | |
| magic | сигнатура | Field name `magic` stays in code font. |
| well-formed, acceptable, valid | коректний, прийнятний, дійсний | "Valid" is «дійсний» everywhere in `format.uk.md` ("invalid" «недійсний»), never «коректний» or «прийнятний»: those are the defined terms of 6.2. |
| untrusted | не заслуговує на довіру; йому не можна довіряти | Heading «Заголовку не можна довіряти». |
| container, stream | контейнер, потік | |
| payload, body | корисне навантаження, тіло | «тіло сторінки», «тіло документа». |
| padding, padding stream, padded with zeros | заповнення, потік заповнення, доповнено нулями | The noun is «заповнення»; for a file «доповнено нулями до цілої сторінки». |
| erasure | стирання | |
| generator polynomial, field polynomial | породжувальний многочлен, многочлен поля | GF(256) stays as written. |
| big-endian, most significant bit | старшим байтом уперед (big-endian), старший біт | |
| normative, informative | нормативний, довідковий | As in Ukrainian standards (ДСТУ). |
| test vectors, conformance vectors | тестові вектори, вектори відповідності | |
| encoder, decoder, reader (any implementation) | кодувальник, декодер, програма зчитування | This project's two readers are «звичайний метод» and «повільний метод». |
| reference decoder | еталонний декодер | |
| promise (of the tools) | обіцянка | "Recover more than it promises" (more lost pages): «може витримати більше втрат, ніж обіцяно». |
| leading zeros | без нулів на початку | Rejected: «ведучі нулі» (calque of Russian «ведущие нули»). |
| plain, tagged, self-identifying document | простий документ, документ із міткою, документ із самоідентифікацією | |

### Other terms for the pages

| English | Ukrainian | Notes |
|---|---|---|
| desktop application | настільний застосунок | «застосунок», not «додаток» (a Russianism in this sense). |
| version tag (git) | тег версії | Only for git tags; «мітка» stays the label tag. |
| sheet-fed scanner | протяжний сканер | |
| simulated, simulator | змодельований, симулятор | |
| withheld (page) | вилучена | |
| dot impression | власне зображення точки на скані | |
| Karel 'Clock' Kulhavy, Colin Dean | Карел «Clock» Кулгави, Колін Дін | |
| point (pt), paper margin | пункт (short «пт»), поле | |
| offset | зміщення | |
| threshold | поріг | |
| sample, sampling | відлік, взяття відліків | The slower reader's step is «вибірка» in the window. "Sharpened" (unsharp mask): «застосовують підвищення різкості». |
| progress (of a step) | хід виконання | Rejected: «поступ» (social advancement). |
| version 0.2.0 or earlier | версії 0.2.0 або ранішої / і раніших версій | The comparative «раніший» agrees with «версія», never with «роздруківки». Rejected: «ранніших». |
| MiB | МіБ | With a no-break space: «256 МіБ». dpi stays «dpi». |
| confidence | упевненість | |
| real (scan, document) | справжній | «справжні скани». |
| scanned upright | відскановано в прямому положенні (не повернуто) | Covers both upside down and turned by 90°. |
| media box | media box | Kept as the PDF term. |

## Strength of claims

- **Verified** — «перевірено», with the reserved root. Never softened
  («імовірно цілий») and never strengthened («гарантовано»). "Only the
  fingerprint makes a file verified" «Перевіреним файл робить лише відбиток».
- **Recoverable vs recovered** — «відновлення можливе» says the pages read
  *should be enough*, no more. «Відновлено» is said only of what has been
  rebuilt. "Can be repaired from the others" «можна відновити з решти»;
  "repaired from the others" «відновлено з решти».
- **Promise of the tools** — «можна втратити N сторінок» keeps the modal
  «можна» (may), not «витримає» (will withstand).
- **"Has been shown", "is expected"** — «показано», not «доведено» (proved);
  "is expected not to be enough" «очікується, що не вистачить».
- **"May contain wrong parts", "may be damaged"** — keep «можуть» / «може»:
  «можуть бути неправильні частини», «може бути пошкоджений».
- **Warnings** stay as firm as English: "was not saved" «не збережено», not
  «не вдалося зберегти» when the program chose not to save.

## Never translated

- The words `optar`, `optar-gui`.
- Command names: `encode`, `decode`.
- Option names: `--paper`, `--dots`, `--protect`, `--compatible`, `--format`,
  `--to`, `--label`, `--no-tag`, `--force`, `--debug-images`,
  `--no-slow-reader`, `--self-test`, `--version`, `-o`, and all others.
- Option values: `none`, `standard`, `high`, `a4`, `letter`, `pdf`, `png`,
  `pgm`, `medium`, `big`, `large`, `xlarge`. (The window's selector names for
  the same things are translated; a value typed on the command line is not.)
- Metavariables: `INPUT`, `BASE`, `OUTPUT`, `LEVEL`, `LABEL`, `TEXT`,
  `STRING`, `X`, `BASE_NNNN_debug.png`, and the `N` / `T` of "can lose N
  page(s) of T".
- File names and extensions: `BASE_0001.png`, `optar_out`, `.pdf`, `.png`,
  `.pgm`, `COPYING`, paths.
- Environment variables, code, constants, header field names, the tag parts
  `SIZE`, `FINGERPRINT`, `CC`, `CHECK`, format strings such as
  `0-65-93-24-3-1-2-24`, hex values.
- Product and standard names: PySide6, Ghostscript, MkDocs, PyInstaller,
  SHA-256, CRC-32, PNG, TIFF, BMP, PGM/PPM, JPEG, PDF, GF(256), dpi, Releases
  (the GitHub page name).
- Version numbers (0.2.0, v0.5.0).

## Agreement patterns the templates need

Ukrainian has three plural forms (`one` 1, 21, 101…; `few` 2–4, 22–24…;
`many` 0, 5–20, 11–14, 25…, 111). The forms of the main nouns:

| Noun | `one` | `few` | `many` |
|---|---|---|---|
| сторінка (f) | сторінка | сторінки | сторінок |
| сторінка, accusative («втратити N …», «мати N …») | сторінку | сторінки | сторінок |
| скан (m) | скан | скани | сканів |
| блок (m) | блок | блоки | блоків |
| байт (m) | байт | байти | байтів |
| точка (f), accusative after «скориговано» | точка / точку | точки | точок |
| символ (m) | символ | символи | символів |
| кодове слово (n) | кодове слово | кодові слова | кодових слів |
| піксель (m) | піксель | пікселі | пікселів |

After «з {n}» (out of) the noun follows `{n}`: «з 1 сторінки», «з 2
сторінок», «з 21 сторінки».

A participle after a bare number agrees with the unstated noun named in the
`en.toml` comment: pages are feminine («1 виправлена, 2 виправлені,
5 виправлено»), blocks masculine («1 виправлений, 2 виправлені,
5 виправлено»). The `one` form also serves 21, 31…, so it never says
«одна».

Invariant counters with the genitive plural before a colon («зчитано сканів:
{done} з {n}», lower case because it only follows « · »; «Справних сторінок: {good} з {n}») avoid agreement and are
the first choice in the bottom bar; their three forms are intentionally the
same text.

## Interface strings the pages will quote

Copy these from the catalogue exactly (they are given here as they stand in
`uk.toml`). Where a page quotes a string with a number, use the catalogue's
form for that number.

| English (as the pages quote it) | Ukrainian (catalogue) | Key |
|---|---|---|
| Put on paper | Записати на папір | `gui.WRITE_TAB` |
| Read from paper | Зчитати з паперу | `gui.READ_TAB` |
| + Add scans… | + Додати скани… | `gui.ADD_SCANS` |
| Save file… | Зберегти файл… | `gui.SAVE_FILE` |
| Remove | Прибрати | `gui.REMOVE_SCAN` |
| Replace scan… | Замінити скан… | `gui.REPLACE_SCAN` |
| Use this scan | Взяти цей скан | `gui.USE_SPARE` |
| Switch to this document | Перейти до цього документа | `gui.SWITCH_DOCUMENT` |
| Assign to page… | Вказати сторінку… | `gui.ASSIGN_PAGE` |
| Start a document by hand… | Зібрати документ вручну… | `gui.START_BY_HAND` |
| Prints as: | Друкується як: | `gui.PRINTS_AS_FIELD` |
| Dot size: / Protection: / Paper: / Name: | Розмір точок: / Захист: / Папір: / Назва: | `gui.*_FIELD` |
| Create PDF… | Створити PDF… | `gui.CREATE_PDF` |
| Compatible with optar 0.2 and the original optar | Сумісність з optar 0.2 і оригінальною програмою optar | `gui.COMPATIBLE` |
| Standard, Medium, Big, Large, Extra large (dots) | Стандартні, Середні, Великі, Крупні, Дуже крупні | `gui.dots.*` |
| None, Standard, High (protection) | Немає, Стандартний, Високий | `gui.protection.*` |
| can lose N page(s) of T | можна втратити N сторінку / сторінки / сторінок з T | `gui.write.promise` |
| Being read | Зчитуються | `gui.BEING_READ_SECTION` |
| Not readable (section) | Не зчитуються | `gui.NOT_READABLE` |
| Waiting | У черзі | `gui.WAITING` |
| Opening the file | Відкриття файлу | `gui.step.open` |
| Finding the page | Пошук сторінки | `gui.step.find` |
| Identifying the page | Розпізнавання сторінки | `gui.step.identify` |
| Reading the data | Зчитування даних | `gui.step.read` |
| Slower reader: sampling | Повільний метод: вибірка | `gui.step.slow-sample` |
| pass 4 of 5 | прохід 4 з 5 (in «Повільний метод: прохід 4 з 5») | `gui.step.slow-fit` |
| Good | Справна | `gui.health.good` |
| Repaired · N | Виправлена · N | `gui.health.repaired` |
| Damaged · N lost | Пошкоджена · втрачено N | `gui.health.damaged` |
| Read by the slower reader | Зчитана повільним методом | `gui.READ_SLOWLY_ROW` |
| Not readable (state) | Не зчитується | `gui.health.unreadable` |
| Missing | Відсутня | `gui.health.missing` |
| Scanned at about 200 dpi, which is too coarse to read | Скан зроблено з роздільною здатністю приблизно 200 dpi, а це надто мало для зчитування | `gui.coarse.unreadable` |
| File recovered and verified · N bytes | Файл відновлено й перевірено · N байтів | `gui.VERIFIED` + `count.byte` |
| Does not match the fingerprint on the paper | Не збігається з відбитком на папері | `gui.state.mismatch` |
| Recoverable: page 3 missing, can be repaired from the others | Відновлення можливе: немає сторінки 3, її можна відновити з решти | `gui.state.recoverable` |
| Recoverable: page 3 missing, repaired from the others · matches the fingerprint | Відновлення можливе: немає сторінки 3, її відновлено з решти · збігається з відбитком | `gui.state.recovered` + `gui.state.matches` |
| Working… 3 of 6 scans read | Обробка… Зчитано сканів: 3 з 6 | `gui.scans_read_working` |
| 3 of 6 scans read | зчитано сканів: 3 з 6 (lower case: only ever shown after « · ») | `gui.scans_read` |
| Checking the fingerprint… | Звіряння з відбитком… | `gui.state.checking` |
| All N pages read · cannot be verified (no tag) | Зчитано всі сторінки: N · перевірити не можна (немає мітки) | `gui.state.all_read` + `gui.state.no_tag` |
| 4 of 6 pages good · 1 damaged · 1 missing | Справних сторінок: 4 з 6 · 1 пошкоджена · 1 відсутня | `gui.state.good`, `.damaged`, `.missing` |
| the worst spot used 57% of its repair capacity (18 of 32): a moderate margin | у найгіршому місці використано 57% ресурсу виправлення (18 з 32): помірний запас | `gui.margin.moderate` |
| Page 3 · Read by the slower reader · 265,112 dots corrected | Сторінка 3 · Зчитана повільним методом · скориговано 265 112 точок | `gui.row.page` + `gui.READ_SLOWLY_ROW` + `gui.health.dots_corrected` |
| · 6,912 bytes repaired by the document's protection | · захист документа виправив 6 912 байтів | `gui.health.bytes_repaired` |
| Spare | Запасний | `gui.row.spare` |
| Language / System default | Мова / Як у системі | `gui.LANGUAGE_MENU`, `gui.SYSTEM_LANGUAGE` |
| Print at actual size (100%), not "fit to page". | Друкуйте у фактичному розмірі (100%), а не «За розміром сторінки». | `cli.ACTUAL_SIZE` |
| Protection {level}: can lose N page(s) of T and still recover the file. | Рівень захисту {level}: можна втратити N сторінку / сторінки / сторінок з T і все одно відновити файл. | `cli.protection.lose` |

## Site navigation

For `mkdocs.yml`, `nav_translations` of the `uk` entry (keys are the English
titles exactly as written) and `site_description`.

| English | Ukrainian |
|---|---|
| Home | Головна |
| Using optar | Робота з optar |
| Install | Встановлення |
| Put a file on paper | Записати файл на папір |
| Read it back | Отримати файл назад |
| Scans that are too coarse | Скани з надто низькою роздільною здатністю |
| Command line | Командний рядок |
| Reference | Довідка |
| How a page identifies itself | Як розпізнається сторінка |
| What has and has not been shown | Що показано, а що ні |
| Format specification | Специфікація формату |
| Project | Проєкт |
| Development | Розробка |
| History | Історія |

- **site_description:** Зберігання файлів на папері за допомогою лазерного
  принтера й сканера
- **site_name:** optar (unchanged)
- **Language name** (`[language].name` and the switcher): Українська

Note: «Проєкт» follows the 2019 Ukrainian orthography (not «Проект»), as the
catalogue does («розділу Releases проєкту»).
