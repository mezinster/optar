# Belarusian glossary (`be`)

Working paper for the Belarusian translation of optar: the catalogue
`src/optar/locale/be.toml` and the pages `docs/<page>.be.md`. It follows
section 1 of `docs/superpowers/translation-brief.md`. The explanations are in
English; the terms are Belarusian. Once a term is chosen here it is used the
same way in the window, the command line and every page.

Terms were chosen from the English, as Belarusian technical writing and
software localisation (Firefox, GNOME, Windows in Belarusian) say them. The
Russian glossary was read for the *concepts* (which idea each word must carry
and which roots must stay free); no Russian word was carried over because it
is Russian, and Russian-looking calques were avoided (no «метка» for tag, no
«опознающийся» shapes, no «дадзеныя»/«данные» hybrids).

## General conventions

- **Orthography.** The official orthography (the 1959 rules as revised by the
  2008 law, in force since 2010), the one Belarusian software localisation
  normally uses. Not the classical orthography (тарашкевіца): no «дакумэнт»,
  no «сьвет» (no soft signs marking assimilative softness), no classical
  loanword spellings. Spellings follow the official dictionary
  forms: «даныя» (not «дадзеныя»), «раздзяляльнасць», «па змаўчанні»,
  genitive «дакумента», «файла», «скана».
- **ў after a vowel.** Word-initial «у» becomes «ў» after a word ending in a
  vowel inside one phrase («не ўдалося», «і ўсё роўна», «старонкі ў
  парадку», «сабраны ўручную»), and stays «у» after a consonant or at the
  start of a phrase («Сабраць дакумент уручную», «старонак у парадку», «У
  чарзе»). A page translator who moves a word must re-check this.
- **Address.** Polite «вы», written lower-case (the norm in Belarusian
  software; capital «Вы» is for letters). Used the same way everywhere.
- **Buttons, menu items and dialog titles** use the infinitive: «Захаваць
  файл…», «Дадаць сканы…», «Замяніць скан…», «Выбраць скан старонкі 3».
  **Instructions** in messages and pages use the polite imperative:
  «Адскануйце старонку нанова», «Скануйце з раздзяляльнасцю 600 dpi»,
  «Пераканайцеся, што…».
- **Status words** in rows and in the bottom bar are short participles or
  invariant phrases («Пашкоджана», «У парадку», «Адсутнічае»), not full
  sentences. A page state takes the neuter/feminine short form agreeing with
  «старонка» («Выпраўлена», «Пашкоджана»).
- **Names of the operating system's own menus and dialogs** (install page).
  macOS has no Belarusian interface, so the page gives the English name the
  user will see first and the Belarusian translation in brackets: System
  Settings («Сістэмныя налады»), Privacy & Security («Прыватнасць і
  бяспека»), Open Anyway («Усё роўна адкрыць»), Open («Адкрыць»). No quotation
  marks around the English names.
- **Typography.** Quotes «ёлачкі» (inner „лапкі“); dash «—» with spaces in
  prose; en dash «–» without spaces in number ranges («старонкі 2–4»), as
  `gui.list.range` writes it; ellipsis «…» as one character, as in English.
  The apostrophe in words such as «з'ява» is the straight `'` (U+0027), as
  Belarusian keyboards type it.
- **Numbers.** The catalogue's thousands separator is a no-break space
  (`[format].group`, U+00A0) and the decimal mark is the comma
  (`[format].decimal`). Outside code blocks, in prose and in table cells, write
  «199 773» (no-break space) and «0,36». Inside code blocks, commands,
  anything a user types, and in all of `format.be.md`, numbers stay exactly
  as in English. Percent: «18%» without a space, as Belarusian software does.
- **optar** is always lower-case, also at the start of a sentence, as in
  English. It is not declined: «у optar», «праграма optar».
- **«Старонка»** is a sheet of paper carrying dots. A page of this website is
  «раздзел», never «старонка» («гл. раздзел „Як старонка сябе апазнае“»).

## Terms

### The brief's required terms

| English | Belarusian | Notes |
|---|---|---|
| dot | кропка | Feminine: кропка / кропкі / кропак. Not «піксель»: pixels are separate (spec terms). "Data dot" «кропка даных», "printer dot" «кропка прынтара» (spec only). |
| dot size | памер кропак | «Памер кропак:», «пры гэтым памеры кропак». |
| block | блок | Masculine: блок / блокі / блокаў. One error-correction unit. "Block of device dots" in the spec: «квадрат кропак прынтара», to keep «блок» for the window's meaning. |
| protection | абарона | Window label «Абарона:». First mention on a page: «абарона ад пашкоджанняў». **Never the adjective «абаронены»**: it suggests a password or encryption. Say «дакумент з абаронай», «раздрукоўка з абаронай», «без абароны». The verb «абараніць файл» is used only in `gui.too_large.protect`, as the English. Rejected: «ахова» (guarding property or nature; «ахова даных» exists but reads legal), «залішнасць» (technical). |
| fingerprint | адбітак | Masculine: адбітак / адбітка. The word Belarusian localisations use for a key or certificate fingerprint («адбітак ключа»). Rejected: «хэш» (names the method), «кантрольная сума» (a different, weaker thing). |
| tag | пазнака | Feminine: пазнака / пазнакі / пазнак. The bracketed `[SIZE:FINGERPRINT:CC]` at the start of a label: «надпіс з пазнакай», «без пазнакі». Native Belarusian word for a mark that identifies something. Rejected: «метка» (reads as Russian), «тэг» (HTML or hashtag), «ярлык» (a Windows shortcut). Because of this choice the verb **«пазначыць» is not used** anywhere (it would read as "to tag"): "assign to a page" is «указаць старонку», "the label states" is «у надпісе ўказана», and the marks on the scan preview are «вылучаны» / «вылучэнне». |
| label | надпіс | Masculine: надпіс / надпісу. The line printed at the bottom of every page. Rejected: «подпіс» (next to "fingerprint" and "verified" it reads as a signature), «этыкетка» (a sticker), «пазнака» (taken by "tag"). "Label band" «паласа надпісу», "label strip" «стужка надпісу» (spec). |
| spare | запасны скан | Row title «Запасны», detail tag «запасны», agreeing with «скан». Rejected: «лішні» (sounds like a mistake), «рэзервовы» (sounds like a backup made on purpose). |
| scan (noun) | скан | Masculine: скан / сканы / сканаў; genitive singular «скана». Usual in Belarusian scanning software. Rejected: «адсканаваная выява» (too long for buttons and rows). |
| scan (verb) | сканаваць, адсканаваць | Imperative «Скануйце» (imperfective, general advice), «Адскануйце» (one page). "Rescan" «адсканаваць нанова». "Scan at 600 dpi" «скануйце з раздзяляльнасцю 600 dpi», short «сканаваць пры 600 dpi». |
| printout | раздрукоўка | Feminine. The pages as printed, the physical set. Kept apart from «дакумент» as English keeps "printout" and "document" apart. |
| document | дакумент | Genitive «дакумента» (official norm for an inanimate thing). A set of pages that carries one file. |
| page | старонка | Feminine: старонка / старонкі / старонак; accusative старонку / старонкі / старонак; locative «на старонцы». Rejected: «аркуш» (a sheet has two sides; an optar page is one printed side). See «раздзел» above. |
| slower reader | павольны метад чытання (short: павольны метад) | "The ordinary reader" «звычайны метад чытання» / «звычайны метад». First mention on a page: «другі, больш павольны метад чытання». The comparative is dropped in the name, as Belarusian names do not carry it. Rejected: «счытвальнік», «чытальнік» (sound like hardware), «павольны рэжым» (a mode is something the user chooses; this runs by itself). "Read by the slower reader" «прачытана павольным метадам». "Slower reader for coarse scans" «павольны метад для сканаў з нізкай раздзяляльнасцю». |
| self-identifying page | самаапазнавальная старонка | Plural «самаапазнавальныя старонкі». Built on «апазнаць» (identify), the verb the window uses for scans («скан не апазнаны», «Апазнанне старонкі»), so the term and the verb share a root. The double «аа» is the regular spelling of «сама-» + «апазнавальная». On first mention on a page, where the page does not explain the term itself, add the gloss «(старонкі, якія самі паведамляюць, да якога дакумента яны належаць і які ў іх нумар)» (after «раздрукоўка»: «(старонкі якой самі паведамляюць, …)»). Pages that explain it themselves and carry no gloss: `identification.be.md` (its section «Самаапазнавальныя старонкі» is the explanation) and `format.be.md` (defines it in 1.4 and part 4). The gloss is on `command-line.be.md` and `evidence.be.md`. Rejected: «самаідэнтыфікавальная» (heavy and bookish), «самавызначальная» («самавызначэнне» is political self-determination), «старонка з загалоўкам» (loses the name). |
| verified | правераны (файл правераны) | Always means: the recovered file matched its fingerprint. The root **«правер-» is reserved** for verified / verification: "not verified" «не правераны», "did not verify" «не прайшоў праверку», "cannot be verified" «праверыць нельга». "Check that…" in an instruction is «Пераканайцеся, што…»; checking the fingerprint is «звярка з адбіткам». Rejected: «пацверджаны» (vaguer), «верыфікаваны» (bookish), «звераны» (only compared, weaker), anything with «гарантавана» (stronger). |
| repaired | выпраўлены (repair: выправіць, выпраўленне) | The protection or the page's error correction fixed damaged data: «выпраўлена 6 912 байтаў», «Выпраўлена · 3». A *missing* page is not «выпраўлена»: "repaired from the others" is «адноўлена па астатніх» (same verb as "recover", "rebuild"). |
| lost | страчаны (страціць) | Blocks that could not be repaired («страчана 3»), and a whole page lost from the printout («можна страціць 1 старонку з 12»). Distinct from "missing". "A page loses part of the file" «губляецца частка файла». |
| damaged | пашкоджаны / пашкоджана | Page state «Пашкоджана». "Damage" «пашкоджанні» (plural is the natural Belarusian for stains and tears). |
| missing | адсутнічае; няма | A page of which no scan has been added. State «Адсутнічае»; in a sentence «няма старонкі 3» / «няма старонак 2 і 3»; adjective «адсутны» («старонка лічыцца адсутнай»). Not «страчана»: the paper may exist, only the scan is missing. |

### The window's vocabulary

| English | Belarusian | Notes |
|---|---|---|
| good (page state) | у парадку | Invariant, needs no agreement: «У парадку», «4 з 6 старонак у парадку». Rejected: «добрая» (agrees in gender, sounds like praise). |
| not readable, unreadable | не чытаецца (state) | State «Не чытаецца»; list section «Не чытаюцца»; "could not be read" «не ўдалося прачытаць»; "bytes unreadable" «байтаў не чытаюцца». |
| recoverable (document state) | Аднаўленне магчымае | Used for both states whose English label is "Recoverable" (still to repair, and already repaired), because English keeps one label for both. The adjective «аднаўляльны» was rejected: in Belarusian it means "renewable" («аднаўляльныя крыніцы энергіі»). «Можна аднавіць» was rejected because the sentence that follows says «яе можна аднавіць» and the doubling reads badly. The full form «магчымае» (agreeing with «аднаўленне») is used because the short «магчыма» also means "maybe". |
| recovered | адноўлены | The file obtained from the pages: «адноўлены файл», «Файл адноўлены і правераны». "What was recovered" «тое, што ўдалося аднавіць». |
| rebuild (a lost page) | аднавіць | Docs only. Same verb as "recover". |
| corrected (dots, symbols, bits) | скарэкціраваны | The page code or the slower reader fixed a dot, bit or symbol. Kept apart from "repaired" as English keeps them apart: «скарэкціравана 265 112 кропак · выпраўлена 6 912 байтаў абаронай дакумента». "Error correction" «карэкцыя памылак», "error-correcting code" «карэкцыйны код». |
| uncorrectable | невыпраўны | "Cannot be fixed at all": «невыпраўныя кодавыя словы», «невыпраўных: 3». |
| repair capacity, budget | рэсурс выпраўлення | "Used 18 of 32" «выкарыстана 18 з 32». "The worst spot" «найгоршае месца». |
| margin (wide, moderate, close to the limit) | запас (вялікі запас, умераны запас, на мяжы) | |
| check the fingerprint, checking | звярыць з адбіткам, звярка | «Звярка з адбіткам…». Keeps «правер-» free for "verified". |
| matches / does not match the fingerprint | супадае / не супадае з адбіткам | |
| identify (a scan), identified | апазнаць, апазнаны | «Апазнанне старонкі» (the step), «скан не апазнаны». Rejected: «ідэнтыфікаваць» (bookish), «вызначыць» (too vague), «распазнаць» (recognition of text or images, not of which page this is). |
| assign (a scan) to a page | указаць старонку | Button «Указаць старонку…». Not «пазначыць» (see "tag"), not «прызначыць» (bureaucratic). |
| start a document by hand, put together by hand | сабраць дакумент уручную, сабраны ўручную | One verb for both, so the button and the later caution match. |
| replace (scan) | замяніць | |
| use this scan | узяць гэты скан | Button «Узяць гэты скан»: shorter than «Выкарыстаць гэты скан». |
| switch to this document | перайсці да гэтага дакумента | |
| add scans | дадаць сканы | |
| remove | прыбраць | Removes a scan from the list, does not delete the file. «Выдаліць» would suggest deleting the file from disk. |
| being read, waiting, working | чытаецца, у чарзе, апрацоўка | Section «Чытаюцца», detail «Чытаецца…»; step «У чарзе»; «Апрацоўка…». |
| step (of reading) | этап | Steps: «Адкрыццё файла», «Пошук старонкі», «Апазнанне старонкі», «Чытанне даных», «Павольны метад: выбарка», «Павольны метад: праход {current} з {total}». |
| pass (of the slower reader) | праход | |
| coarse scan, too coarse | скан з нізкай раздзяляльнасцю; занадта нізкая раздзяляльнасць | Belarusian speaks of resolution, not of coarseness. Rejected: «грубы скан» (a calque; «грубы» also means rude). |
| resolution | раздзяляльнасць | dpi stays «dpi». |
| put on paper | запісаць на паперу | Tab «Запісаць на паперу». |
| read from paper | прачытаць з паперы | Tab «Прачытаць з паперы». |
| prints as | друкуецца як | Field «Друкуецца як:». |
| name (of the file, on the label) | назва | Field «Назва:», «(без назвы)». Belarusian says «назва» for the name of a thing and keeps «імя» for persons. Also "output base name" «базавая назва», "file name" «назва файла». |
| paper | папера | Field «Папера:». |
| compatible (printout) | сумяшчальная (раздрукоўка) | Checkbox «Сумяшчальнасць з optar 0.2 і першапачатковай праграмай optar» (a noun: a short adjective on a checkbox has no visible subject). |
| original optar, the C program | першапачатковая праграма optar на C | Rejected: «арыгінальная» (also "unusual"), «зыходная» (clashes with «зыходны код»). "The original file" (not the program) is «арыгінал» / «арыгінальны файл». |
| dot size names: Standard, Medium, Big, Large, Extra large | Стандартныя, Сярэднія, Вялікія, Буйныя, Вельмі буйныя | Plural adjectives agreeing with «кропкі». Capitalised only as a selector entry or at the start; in running text lower-case («стандартныя кропкі», «са стандартнымі кропкамі», «для буйных кропак»). Note «са» before «ст-». |
| protection levels: None, Standard, High | Няма, Стандартная, Высокая | Feminine, agreeing with «абарона». In prose «стандартная абарона», «высокая абарона», «без абароны». |
| paper names: A4, US Letter | A4, US Letter | Names of paper sizes; in prose «папера Letter». |
| actual size (100%), fit to page | у натуральную велічыню (100%), «Па памеры старонкі» | The second is quoted as a print dialog names it. |
| grayscale, colour, black and white | у адценнях шэрага, каляровы, чорна-белы | |
| image (a file to read) | выява | Feminine: выява / выявы. The Belarusian localisation word for an image file. |
| desktop application | праграма з акном | The `optar-gui` program, in the install table header and in prose. Rejected: «настольная праграма» (a calque), «праграма з графічным інтэрфейсам» (too long for a table header). |
| bottom bar | радок унізе (радок стану) | |
| progress bar | індыкатар выканання | |
| row, list of scans | радок, спіс сканаў | |
| preview, marked | прагляд, вылучаны | Marks on the preview are «вылучаны», never «пазнака» or «пазначаны» (see "tag"). |
| outline of a page | контур старонкі | |
| another printout | іншая раздрукоўка | "Not part of this file" «не належыць да гэтага файла». |
| untagged, no tag | без пазнакі, няма пазнакі | |
| settings (these choices) | налады | «з такімі наладамі». |
| Language (menu), System default | Мова, Як у сістэме | |
| OK, Cancel, Save, Yes, No | Добра, Скасаваць, Захаваць, Так, Не | «Добра» as in Firefox and GNOME in Belarusian. |
| sentence end added by the window (`gui.sentence`) | «{words}.» | Full stop, as in English. |
| page range | 2–4 | En dash without spaces, in `gui.list.range` and every `gui.run.*.range`. |
| could not be decoded in any orientation (`gui.reason.not_decodable`) | Не ўдалося раскадаваць скан ні ў адной арыентацыі | A full sentence with a capital letter, as the other reasons. |
| scanned upright | адсканавана ў прамым становішчы (не павернута) | Covers a page turned by 90° as well as upside down. |

### The command line's vocabulary

| English | Belarusian | Notes |
|---|---|---|
| symbol (code symbol on a page) | сімвал | сімвал / сімвалы / сімвалаў. Label characters are «знак», so «сімвал» is only the code symbol. |
| codeword | кодавае слова | кодавае слова / кодавыя словы / кодавых слоў. |
| byte | байт | байт / байты / байтаў («5 байтаў»; Belarusian has no short genitive plural here). |
| encode / decode | закадаваць / раскадаваць (закадаванне / раскадаванне) | Command names `encode`, `decode` stay English. "Decode again" «паўтарыце раскадаванне». Rejected: «дэкадаваць» (a needless loan where the native prefix exists). |
| option (of a command) | параметр | «параметр --protect». Rejected: «опцыя» (colloquial), «ключ». |
| default | па змаўчанні | «(па змаўчанні: a4)». |
| usage, positional arguments, options | выкарыстанне, пазіцыйныя аргументы, параметры | argparse headings. |
| exit status | код выхаду | |
| stdout, stderr | stdout, stderr | Kept. |
| gap (in page numbering) | пропуск | |
| ignored | прапушчаны | «прапушчана 5 сканаў іншага дакумента». |
| protection level `{level}` | Узровень абароны {level} | The option value stays English and reads as a name: «Узровень абароны standard: …». |
| because of --force | праз --force | «Усё роўна захаваны праз --force». |
| pixels (in error messages with a number before the noun) | пікс. | Abbreviation, needs no agreement: «скан 100 × 141 пікс.». |
| rows of pixels | у радках пікселяў | Said after the numbers: «{height} замест {rows} (у радках пікселяў)». |
| point (pt), paper margin | пункт (short «пт»), поле | |
| hyphen (in a format string) | злучок | «восем цэлых лікаў праз злучок». |
| release workflow, push (Git) | сцэнарый выпуску (release workflow), адпраўка (push) | Development page only; the English word follows in brackets on first use. |

### Format specification terms (`format.md`)

| English | Belarusian | Notes |
|---|---|---|
| page pixel, data pixel, scan pixel | піксель старонкі, піксель даных, піксель скана | піксель / пікселі / пікселяў. |
| page format, format string | фармат старонкі, радок фармату | |
| layout | макет | Paper + dot size + page format. |
| grid | сетка | |
| cross, origin, pitch | крыж, пачатак крыжа, крок крыжоў | |
| border, frame | рамка | |
| data area | вобласць даных | Geometric area of page pixels (2.2). |
| data region | зона даных | Bytes of the container (4.6). Kept apart from «вобласць даных». |
| label band, label strip, font strip | паласа надпісу, стужка надпісу, стужка шрыфту | |
| character, character cell, glyph, logo | знак, ячэйка знака, гліф, лагатып | |
| interleave | перамежаванне | |
| spread | разнясенне | Container spread (4.6), kept apart from «перамежаванне». |
| page code | код старонкі | |
| Golay code, (extended) Hamming code, Reed-Solomon code | код Голея, (пашыраны) код Хэмінга, код Рыда — Саламона | |
| parity, parity bytes, parity level | цотнасць, байты цотнасці, узровень цотнасці | Never shown in the window. Rejected: «праверачныя байты» (reserved root «правер-»). |
| check (of a tag), check digits | кантрольнае значэнне, кантрольныя лічбы | Not «кантрольная сума». |
| header, header copy | загаловак, копія загалоўка | |
| magic | сігнатура | Field name `magic` stays in code font. |
| well-formed, acceptable, valid | карэктны, дапушчальны, сапраўдны | "Valid"/"invalid" is «сапраўдны»/«несапраўдны» everywhere in `format.be.md`; the other two are the defined terms of 6.2. (In the catalogue's error messages "invalid page format" is «няправільны фармат старонкі», a user-facing error, not the spec term.) |
| untrusted | яму нельга давяраць | Heading «Загалоўку нельга давяраць». |
| container, stream | кантэйнер, паток | |
| payload, body | карысная нагрузка, цела | «цела старонкі», «цела дакумента». |
| padding, padded with zeros | запаўненне, дапоўнены нулямі | «дапоўнены нулямі да цэлай старонкі». |
| erasure | сціранне | |
| generator polynomial, field polynomial | спараджальны мнагачлен, мнагачлен поля | GF(256) as written. |
| big-endian, most significant bit | старэйшым байтам наперад (big-endian), старэйшы біт | |
| floating point | рухомая коска («32-бітная арыфметыка з рухомай коскай») | Not «плаваючая коска» (a copy of Russian). |
| (memory and time) cost | выдаткі памяці і часу | 6.2. Not «расход». |
| normative, informative | нарматыўны, даведачны | |
| test vectors, conformance vectors | тэставыя вектары, вектары адпаведнасці | |
| encoder, decoder, reader | кадавальнік, дэкодар, праграма чытання | "Reader" in parts 6 and 7 is any program that reads pages. |
| reference decoder | эталонны дэкодар | |
| plain, tagged, self-identifying document | просты дакумент, дакумент з пазнакай, самаапазнавальны дакумент | |

## Strength of claims

- **Verified** — «правераны», with the reserved root. Never softened
  («верагодна, цэлы») and never strengthened («гарантавана»). "Only the
  fingerprint makes a file verified" «Правераным файл робіць толькі
  адбітак».
- **Recoverable vs recovered** — «Аднаўленне магчымае» says the pages read
  should be enough, no more. «Адноўлены» is said only of what has been
  rebuilt. "Can be repaired from the others" «можна аднавіць па астатніх»;
  "repaired from the others" «адноўлена па астатніх».
- **Promise of the tools** — «можна страціць N старонак» keeps the modal
  «можна», not «вытрымае» (stronger).
- **"Has been shown", "is expected"** — «паказана», not «даказана»;
  "is expected not to be enough" «чакаецца, што не хопіць».
- **"May contain wrong parts", "may be damaged"** — keep «могуць», «можа»:
  «могуць быць няправільныя часткі», «можа быць пашкоджаны».
- **Warnings** stay firm: "was not saved" «не захаваны» when the program
  chose not to save; «не ўдалося захаваць» only when it tried and failed.

## Never translated

- `optar`, `optar-gui`; command names `encode`, `decode`.
- Option names (`--paper`, `--dots`, `--protect`, `--compatible`, `--format`,
  `--to`, `--label`, `--no-tag`, `--force`, `--debug-images`,
  `--no-slow-reader`, `--self-test`, `--version`, `-o`, and all others).
- Option values: `none`, `standard`, `high`, `a4`, `letter`, `pdf`, `png`,
  `pgm`, `medium`, `big`, `large`, `xlarge`. (The window's selector names
  for the same things are translated.)
- Metavariables (`INPUT`, `BASE`, `OUTPUT`, `LABEL`, `STRING`, …), file names
  and extensions (`BASE_0001.png`, `optar_out`, `.pdf`), environment
  variables, code, constants, header field names, the tag parts `SIZE`,
  `FINGERPRINT`, `CC`, format strings, hex values.
- Product and standard names: PySide6, Ghostscript, MkDocs, PyInstaller,
  SHA-256, CRC-32, PNG, TIFF, BMP, PGM/PPM, JPEG, PDF, GF(256), dpi.
  "Releases" (the GitHub page) stays as GitHub shows it.
- Version numbers (0.2.0, v0.5.0).

## Agreement patterns the templates need

Belarusian has three plural forms (`one` 1, 21, 101…; `few` 2–4, 22–24…;
`many` 0, 5–20, 11–14, 25…). With `few` the noun is nominative plural («2
старонкі», «3 сканы», «2 байты»); with `many` genitive plural.

| Noun | `one` | `few` | `many` | after «з N» (genitive) |
|---|---|---|---|---|
| старонка (f) | старонка | старонкі | старонак | старонкі / старонак / старонак |
| старонка, accusative («страціць N …», «не больш за N …») | старонку | старонкі | старонак | |
| скан (m) | скан | сканы | сканаў | |
| блок (m) | блок | блокі | блокаў | |
| байт (m) | байт | байты | байтаў | |
| кропка (f) | кропка | кропкі | кропак | |
| сімвал (m) | сімвал | сімвалы | сімвалаў | |
| кодавае слова (n) | кодавае слова | кодавыя словы | кодавых слоў | |
| піксель (m) | піксель | пікселі | пікселяў | |

A short past participle after a number agrees with the (often unstated)
noun: pages feminine («1 выпраўлена, 2 выпраўлены, 5 выпраўлена»), blocks
and bytes masculine («1 выпраўлены, 2 выпраўлены, 5 выпраўлена»). The `one`
form also serves 21, 31, …, so it never says «адна».

Invariant counters «Прачытана сканаў: {done} з {n}», «Прачытана старонак:
{n}» avoid agreement and have the same text in all three forms on purpose.

## Site navigation

For `mkdocs.yml`, `nav_translations` of the `be` entry (keys are the English
titles exactly as written) and `site_description`.

| English | Belarusian |
|---|---|
| Home | Галоўная |
| Using optar | Праца з optar |
| Install | Усталяванне |
| Put a file on paper | Запісаць файл на паперу |
| Read it back | Атрымаць файл назад |
| Scans that are too coarse | Сканы з занадта нізкай раздзяляльнасцю |
| Command line | Камандны радок |
| Reference | Даведка |
| How a page identifies itself | Як старонка сябе апазнае |
| What has and has not been shown | Што паказана, а што не |
| Format specification | Спецыфікацыя фармату |
| Project | Праект |
| Development | Распрацоўка |
| History | Гісторыя |

- **site_description:** Захоўванне файлаў на паперы з дапамогай лазернага
  прынтара і сканера
- **site_name:** optar (unchanged)
- **Language name** (`[language].name` and the switcher): Беларуская

## Interface strings the pages quote

Copy these from `be.toml` exactly (the left column is the English the
English pages quote).

| English | Belarusian (catalogue) | Key |
|---|---|---|
| Put on paper | Запісаць на паперу | `gui.WRITE_TAB` |
| Read from paper | Прачытаць з паперы | `gui.READ_TAB` |
| + Add scans… | + Дадаць сканы… | `gui.ADD_SCANS` |
| Save file… | Захаваць файл… | `gui.SAVE_FILE` |
| Remove | Прыбраць | `gui.REMOVE_SCAN` |
| Replace scan… | Замяніць скан… | `gui.REPLACE_SCAN` |
| Use this scan | Узяць гэты скан | `gui.USE_SPARE` |
| Switch to this document | Перайсці да гэтага дакумента | `gui.SWITCH_DOCUMENT` |
| Assign to page… | Указаць старонку… | `gui.ASSIGN_PAGE` |
| Start a document by hand… | Сабраць дакумент уручную… | `gui.START_BY_HAND` |
| Being read | Чытаюцца | `gui.BEING_READ_SECTION` |
| Not readable (section / row) | Не чытаюцца / Не чытаецца | `gui.NOT_READABLE`, `gui.health.unreadable` |
| Not part of this file | Не належаць да гэтага файла | `gui.NOT_PART_OF_THIS_FILE` |
| Spare | Запасны | `gui.row.spare` |
| File: / Paper: / Name: / Prints as: / Dot size: / Protection: | Файл: / Папера: / Назва: / Друкуецца як: / Памер кропак: / Абарона: | `gui.*_FIELD` |
| Choose… | Выбраць… | `gui.CHOOSE_FILE` |
| Create PDF… | Стварыць PDF… | `gui.CREATE_PDF` |
| Compatible with optar 0.2 and the original optar | Сумяшчальнасць з optar 0.2 і першапачатковай праграмай optar | `gui.COMPATIBLE` |
| Standard / Medium / Big / Large / Extra large (dots) | Стандартныя / Сярэднія / Вялікія / Буйныя / Вельмі буйныя | `gui.dots.*` |
| None / Standard / High (protection) | Няма / Стандартная / Высокая | `gui.protection.*` |
| can lose N page(s) of T | можна страціць N старонку / старонкі / старонак з T | `gui.write.promise` |
| Waiting | У чарзе | `gui.WAITING` |
| Opening the file / Finding the page / Identifying the page / Reading the data | Адкрыццё файла / Пошук старонкі / Апазнанне старонкі / Чытанне даных | `gui.step.*` |
| Slower reader: sampling / pass 4 of 5 | Павольны метад: выбарка / Павольны метад: праход 4 з 5 | `gui.step.slow-sample`, `gui.step.slow-fit` |
| Good | У парадку | `gui.health.good` |
| Repaired · N | Выпраўлена · N | `gui.health.repaired` |
| Damaged · N lost | Пашкоджана · страчана N (страчаны for 1–4, 21–24…) | `gui.health.damaged` |
| Read by the slower reader | Прачытана павольным метадам | `gui.READ_SLOWLY_ROW` |
| Missing | Адсутнічае | `gui.health.missing` |
| Scanned at about 200 dpi, which is too coarse to read | Скан зроблены прыкладна пры 200 dpi, гэта занадта нізкая раздзяляльнасць для чытання | `gui.coarse.unreadable` |
| File recovered and verified · N bytes | Файл адноўлены і правераны · N байтаў | `gui.VERIFIED` + `count.byte` |
| Does not match the fingerprint on the paper | Не супадае з адбіткам на паперы | `gui.state.mismatch` |
| Recoverable: page 3 missing, can be repaired from the others | Аднаўленне магчымае: няма старонкі 3, яе можна аднавіць па астатніх | `gui.state.recoverable` |
| Recoverable: page 3 missing, repaired from the others · matches the fingerprint | Аднаўленне магчымае: няма старонкі 3, яна адноўлена па астатніх · супадае з адбіткам | `gui.state.recovered`, `gui.state.matches` |
| Working… 3 of 6 scans read | Апрацоўка… Прачытана сканаў: 3 з 6 | `gui.scans_read_working` |
| 3 of 6 scans read | Прачытана сканаў: 3 з 6 | `gui.scans_read` |
| Checking the fingerprint… | Звярка з адбіткам… | `gui.state.checking` |
| All N pages read · cannot be verified (no tag) | Прачытаны ўсе старонкі: N · праверыць нельга (няма пазнакі) | `gui.state.all_read`, `gui.state.no_tag` |
| 4 of 6 pages good · 1 damaged · 1 missing | 4 з 6 старонак у парадку · 1 пашкоджана · 1 адсутнічае | `gui.state.good`, `.damaged`, `.missing` |
| the worst spot used 57% of its repair capacity (18 of 32): a moderate margin | у найгоршым месцы выкарыстана 57% рэсурсу выпраўлення (18 з 32): умераны запас | `gui.margin.moderate` |
| Language / System default | Мова / Як у сістэме | `gui.LANGUAGE_MENU`, `gui.SYSTEM_LANGUAGE` |
| Print at actual size (100%), not "fit to page". | Друкуйце ў натуральную велічыню (100%), а не «Па памеры старонкі». | `cli.ACTUAL_SIZE` |
