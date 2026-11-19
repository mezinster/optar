# Georgian glossary (`ka`)

Working paper for the Georgian translation of optar: the catalogue
`src/optar/locale/ka.toml` and the pages `docs/<page>.ka.md`. It follows
section 1 of `docs/superpowers/translation-brief.md`. The explanations are in
English; the terms are Georgian (Mkhedruli). Once a term is chosen here it is
used the same way in the window, the command line and every page.

## General conventions

- **Script.** Mkhedruli has no capital letters, so "capitalised" English
  (titles, state words, selector names) needs nothing special. Latin names
  (`optar`, PDF, A4, option names) keep their own spelling.
- **Address.** Polite plural «თქვენ» (verbs in the 2nd person plural:
  «აირჩიეთ», «დაასკანერეთ», «შეინახავთ»), the norm of Georgian software.
  Used the same way everywhere.
- **Buttons, menu items, dialog and window titles, tab names, steps** use the
  verbal noun (masdar), as Georgian software does: «ფაილის შენახვა…»,
  «სკანების დამატება…», «სკანის შეცვლა…», «ქაღალდზე ჩაწერა», «გვერდის ძებნა».
  A question in a dialog title uses the 1st person: «მაინც შევინახო?».
- **Instructions** in messages and pages use the polite imperative:
  «ხელახლა დაასკანერეთ გვერდი 3».
- **Status words** in rows and in the bottom bar are short predicates
  («წესრიგშია», «აკლია», «დაზიანებულია», «ვერ იკითხება»), not full sentences.
- **Things that could not be done** are said with «… ვერ მოხერხდა» or a
  potential/passive form («ვერ იკითხება», «ვერ გამოსწორდა»), never with an
  aorist that needs an agent («ვერ წაიკითხა» — who?). **The program chose not
  to do it**: «არ იქნა შენახული» (firm: "was not saved").
- **Numerals.** A noun after a number stays singular, in the case the verb
  needs: «5 გვერდი», «5 გვერდიდან 3», «12 ბაიტი». So every plural table has one
  form (`other`), and agreement never depends on the number.
- **"X of Y"** is «Y-დან X»: with the noun «12 გვერდიდან 3» (the noun carries
  the postposition), without a noun «12-დან 3» (hyphen). Titles "Page 3 of 12"
  are «გვერდი 3 12-დან», the usual pattern of Georgian viewers.
- **Suffixes on inserted names and numbers.** A case ending or postposition
  after a number, a Latin name or a placeholder is joined with a hyphen:
  «3-ზე», «optar 0.2-თან», «PDF-ის», «{total}-დან». Where a file name would
  need one, a noun stands before it in apposition and takes the ending
  instead: «სკანი {name}», «ფაილში {name}». A page number that needs a case
  follows the truncated noun: «გვერდ {page}-ისთვის», «გვერდ {other}-ს» (the
  standard construction, as «ოთახ 5-ში»).
- **Typography.** Quotes „…“ (low-high, Georgian norm); dash «—» with spaces in
  prose; en dash «–» without spaces in number ranges («გვერდები 2–4»);
  ellipsis «…» as one character, as in English.
- **Numbers.** Thousands separator: a no-break space (U+00A0), «199 773»,
  «200 000». Decimal mark: comma, «0,36», «2,5». Inside code blocks, commands,
  anything a user types, and all of `format.ka.md`, numbers stay exactly as in
  English. Percent without a space: «18%». Ordinals are written «მე-3», «1-ლი»;
  the catalogue avoids ordinals because «1-ლი» differs from the rest.
- **optar** is always lower-case and takes endings with a hyphen: «optar-ის»,
  «optar-თან».
- **«გვერდი»** is a sheet of paper carrying dots. A page of this website is
  «განყოფილება», never «გვერდი» («იხ. განყოფილება „როგორ ამოიცნობა გვერდი“»).
  «განყოფილება» also serves for a section of the format specification
  («განყოფილება 4.2»). The two uses do not meet: the format page never refers
  to site pages, and the user pages name the specification when they refer to
  its parts («ფორმატის სპეციფიკაციის მე-8 ნაწილში»).
- **«ზოლი»** (band, strip, bar) is always qualified: «წარწერის ზოლი» (label
  band), «ქვედა ზოლი» (bottom bar), «პროგრესის ზოლი», «ვიწრო ზოლი», «საიტის
  ზედა ზოლი». It never stands alone for a new referent.
- **«სათაური»** means only a title or a heading (a page title, a Markdown
  heading, a dialog title). The format's *header* is «თავსართი» (see the
  format terms); the two are never mixed.
- **Operating system names** on the install page: macOS has no Georgian
  interface, so its menus and buttons are given in English as the system shows
  them, followed by a Georgian translation in brackets: «System Settings
  (სისტემის პარამეტრები)», «Privacy & Security (კონფიდენციალურობა და
  უსაფრთხოება)», «„Open Anyway“ („მაინც გახსნა“)», «Open (გახსნა)». Windows
  ships a Georgian interface; if its dialogs are ever quoted, use the names it
  really shows.

## Terms

### The brief's required terms

| English | Georgian | Notes |
|---|---|---|
| dot | წერტილი | "Data dot" «მონაცემთა წერტილი», "printer dot" «პრინტერის წერტილი». Not «პიქსელი»: pixels are separate. |
| dot size | წერტილის ზომა | Singular, as Georgian says of a property: «წერტილის ზომა:», «ამ წერტილის ზომით». |
| block | ბლოკი | One error-correction unit; the window repairs or loses blocks. |
| protection | დაცვა | Window label «დაცვა:». First mention on a page: «დაზიანებისგან დაცვა». **Avoid the adjective «დაცული»** for a printout: it suggests a password. Adverbial «დაცვით» («შექმნილია დაცვით», «სტანდარტული დაცვით»), «დაცვის გარეშე». A printout or document made with protection is «დაცვით შექმნილი ამონაბეჭდი / დოკუმენტი» (never the bare attributive «დაცვით ამონაბეჭდი», which is unidiomatic; «დაცვიანი» is colloquial). Rejected: «ზედმეტობა» (redundancy; correct but technical), «რეზერვი» (vague, suggests a backup copy). |
| fingerprint | ანაბეჭდი | The usual Georgian word for a key or hash fingerprint (from «თითის ანაბეჭდი»). Full form «ფაილის ანაბეჭდი» where the sentence needs it, and always near «ამონაბეჭდი» (printout), which shares the root, and next to «დაბეჭდილი»: «ქაღალდზე დაბეჭდილი ფაილის ანაბეჭდი» (never «დაბეჭდილი ანაბეჭდი» alone). Rejected: «ჰეში» (names the method), «საკონტროლო ჯამი» (a checksum, a different and weaker thing). |
| tag | ჭდე | The bracketed `[SIZE:FINGERPRINT:CC]` at the start of a label; «ჭდე» is the word Georgian software (Mozilla) uses for tags. «ჭდით», «ჭდის გარეშე», «ჭდე არ აქვს» (untagged). Rejected: «ტეგი» (colloquial loan, reads as an HTML tag), «ნიშანი» (too general; also used for label characters), «იარლიყი» (a sticker, a shortcut). Marks on the scan preview are «მონიშნულია», never «ჭდე». |
| label | წარწერა | The line printed at the bottom of every page. "Label band" «წარწერის ზოლი», "label strip" «წარწერის ლენტი» (spec). Rejected: «ხელმოწერა» (signature, clashes with fingerprint/verified), «იარლიყი», «ეტიკეტი» (a stuck-on sticker). |
| spare | სათადარიგო (სკანი) | Row title and detail tag «სათადარიგო». Invariant adjective. Rejected: «ზედმეტი» (sounds like an error), «სარეზერვო» (sounds like a backup made on purpose). |
| scan (noun) | სკანი | The usual word in Georgian scanning talk; short enough for buttons and rows. Plural «სკანები». Rejected: «დასკანერებული გამოსახულება» (too long), «გამოსახულება» (loses the meaning; used only for "image"). |
| scan (verb) | დასკანერება (სკანირება) | Imperative «დაასკანერეთ»; "rescan" «ხელახლა დაასკანერეთ», noun «ხელახლა დასკანერება». "Scan at 600 dpi" «დაასკანერეთ 600 dpi გარჩევადობით». Participle «დასკანერებული». |
| printout | ამონაბეჭდი | The pages as printed, the physical set. Kept apart from «დოკუმენტი» exactly as English keeps "printout" and "document" apart. |
| document | დოკუმენტი | A set of pages that carries one file. |
| page | გვერდი | Rejected: «ფურცელი» (a sheet has two sides; an optar page is one printed side). See the convention on «განყოფილება». |
| slower reader | წაკითხვის ნელი მეთოდი (short: ნელი მეთოდი) | "The ordinary reader" «წაკითხვის ჩვეულებრივი მეთოდი» / «ჩვეულებრივი მეთოდი». First mention on a page: «წაკითხვის მეორე, უფრო ნელი მეთოდი» (the adjectives stand next to «მეთოდი»). "Read by the slower reader" «წაკითხულია ნელი მეთოდით»; "the slower reader for coarse scans" «დაბალი გარჩევადობის სკანების ნელი მეთოდი». As an agent: «ნელმა მეთოდმა». Rejected: «წამკითხველი» (a device), «ნელი რეჟიმი» (a mode is chosen by the user; this runs by itself). |
| self-identifying page | თვითამოცნობადი გვერდი | Built on «ამოცნობა» (identify), which the window uses for scans («სკანი ამოუცნობია»), so the term and the verb share a root. On first mention in a page add the gloss «(გვერდი, რომელიც თავად მიუთითებს, რომელ დოკუმენტს ეკუთვნის და რომელი გვერდია)». Rejected: «თვითიდენტიფიცირებადი» (correct but heavy), «თვითაღწერადი» (self-describing, a different idea). |
| verified | შემოწმებული (ფაილი შემოწმებულია) | Always means: the recovered file matched its fingerprint. The root «შემოწმ-» is **reserved** for verified / verification: "not verified" «შემოწმებული არ არის», "did not verify" «შემოწმება ვერ გაიარა», "cannot be verified" «შემოწმება შეუძლებელია», "once verified" «შემოწმების შემდეგ». Checking the fingerprint is «ანაბეჭდთან შედარება» (see "check"). Rejected: «დადასტურებული» (confirmed; vaguer, and needed for "confirmed" in the cautions), «ვერიფიცირებული» (bookish), anything with «გარანტირებული» (stronger). |
| repaired | გამოსწორებული (repair: გამოსწორება, გამოსწორდა) | The protection or the page's error correction fixed damaged data: «გამოსწორებულია 6 912 ბაიტი», «გამოსწორებულია · 3». A *missing* page is not «გამოსწორებული»: "repaired from the others" is «აღდგენილია დანარჩენი გვერდებით» (the verb of "recover"). |
| lost | დაკარგული (იკარგება, დაიკარგა) | Blocks that could not be repaired («დაიკარგა 3»), and a whole page lost («12 გვერდიდან შეიძლება დაიკარგოს 1»). Distinct from "missing". |
| damaged | დაზიანებული | Page state «დაზიანებულია». "Damage" «დაზიანება». |
| missing | აკლია | A page of which no scan has been added. State «აკლია»; in a sentence «აკლია გვერდი 3», «აკლია გვერდები 2 და 3». Not «დაკარგულია»: the paper may exist, only the scan is missing. |

### The window's vocabulary

| English | Georgian | Notes |
|---|---|---|
| good (page state) | წესრიგშია | "Is in order": a predicate that needs no agreement: «წესრიგშია», «6 გვერდიდან 4 წესრიგშია». Rejected: «კარგი» (sounds like praise). |
| not readable, unreadable | ვერ იკითხება | State and section «ვერ იკითხება»; "could not be read" «წაკითხვა ვერ მოხერხდა»; "bytes unreadable" «ბაიტი ვერ იკითხება». |
| recoverable (document state) | აღდგენადია | Used for both states whose English label is "Recoverable". |
| recovered | აღდგენილი | «აღდგენილი ფაილი», «ფაილი აღდგენილი და შემოწმებულია». "What was recovered" «რაც აღდგა». |
| rebuild (a lost page) | აღდგენა | Docs only; same verb as "recover". |
| corrected (dots, symbols, bits) | შესწორებული (შესწორდა) | Kept apart from "repaired" as English keeps them apart: «შესწორდა 265 112 წერტილი · დოკუმენტის დაცვით გამოსწორდა 6 912 ბაიტი». "Error correction" «შეცდომების შესწორება», "error-correcting code" «შეცდომების შემსწორებელი კოდი». |
| uncorrectable, beyond correction | შეუსწორებელი | |
| a repair that reports no failure; the repair reported no failure | გამოსწორება, რომელიც მარცხს არ აცხადებს; გამოსწორებამ მარცხი არ განაცხადა | Says only that the repair did not report failure. Never «შეცდომა არ გამოვლენილა» (no error was found): finding and fixing wrong bytes is what a repair does. Such a file is still not «შემოწმებული». |
| repair capacity, budget | გამოსწორების რესურსი | "Used 18 of 32" «32-დან 18». "The worst spot" «ყველაზე უარესი ადგილი». |
| margin (wide, moderate, close to the limit) | მარაგი (დიდი მარაგი, ზომიერი მარაგი, ზღვართან ახლოს) | |
| check the fingerprint, checking | ანაბეჭდთან შედარება | «მიმდინარეობს ანაბეჭდთან შედარება…». Keeps «შემოწმ-» free for "verified". |
| matches / does not match the fingerprint | ემთხვევა / არ ემთხვევა ანაბეჭდს | |
| mismatch | შეუსაბამობა | |
| identify (a scan), identified | ამოცნობა, ამოცნობილი; not identified: ამოუცნობია | Step «გვერდის ამოცნობა». Rejected: «იდენტიფიკაცია» (bookish), «განსაზღვრა» (vague). |
| assign (a scan) to a page | გვერდის მითითება | Button «გვერდის მითითება…»; prose «სკანისთვის გვერდის ხელით მითითება». |
| start a document by hand, put together by hand | დოკუმენტის ხელით აწყობა, ხელით აწყობილი | One verb for both. |
| replace (scan) | შეცვლა | |
| use this scan | ამ სკანის გამოყენება | |
| switch to this document | ამ დოკუმენტზე გადასვლა | |
| add scans | სკანების დამატება | |
| remove | ამოღება | Takes a scan out of the list, does not delete the file. «წაშლა» would suggest deleting from disk. |
| being read, waiting, working | იკითხება, რიგში, მუშავდება | Section «იკითხება», row «იკითხება…»; step «რიგში»; «მუშავდება…». |
| step (of reading) | ეტაპი | Steps: «ფაილის გახსნა», «გვერდის ძებნა», «გვერდის ამოცნობა», «მონაცემების წაკითხვა», «ნელი მეთოდი: ნიმუშების აღება», «ნელი მეთოდი: გავლა {current} {total}-დან». |
| pass (of the slower reader) | გავლა | |
| coarse scan, too coarse | დაბალი გარჩევადობის სკანი; ზედმეტად დაბალი გარჩევადობით | Georgian speaks of resolution, not coarseness. Rejected: «უხეში სკანი» (a calque). |
| resolution | გარჩევადობა | dpi stays «dpi». |
| put on paper | ქაღალდზე ჩაწერა | Tab «ქაღალდზე ჩაწერა». |
| read from paper | ქაღალდიდან წაკითხვა | Tab «ქაღალდიდან წაკითხვა». |
| prints as | დაიბეჭდება | Field «დაიბეჭდება:». |
| name (on the label) | სახელი | Field «სახელი:», «(უსახელო)». |
| compatible (printout) | თავსებადი | Checkbox «თავსებადობა optar 0.2-თან და თავდაპირველ optar-თან». |
| original optar, the C program | თავდაპირველი optar, C-ზე დაწერილი პროგრამა | Rejected: «ორიგინალური» (also "unusual"). "The original file" is likewise «თავდაპირველი ფაილი». |
| dot size names: Standard, Medium, Big, Large, Extra large | სტანდარტული, საშუალო, დიდი, მსხვილი, ძალიან მსხვილი | Adjectives with «წერტილები»: «სტანდარტული წერტილებით», «მსხვილი წერტილებისთვის». Large / Extra large keep the English pair as «მსხვილი» / «ძალიან მსხვილი». |
| protection levels: None, Standard, High | არა, სტანდარტული, მაღალი | In prose «სტანდარტული დაცვა», «მაღალი დაცვა», «დაცვის გარეშე». |
| paper names: A4, US Letter | A4, US Letter | Names of paper sizes; in prose «Letter ქაღალდი». |
| actual size (100%), fit to page | რეალური ზომა (100%), „გვერდზე მორგება“ | The second is quoted as print dialogs name it; drivers vary. |
| grayscale, colour, black and white | ნაცრისფერი ტონები, ფერადი, შავ-თეთრი | |
| bottom bar | ქვედა ზოლი | |
| progress bar | პროგრესის ზოლი | |
| row, list of scans | სტრიქონი, სკანების სია | Rows of pixels (label band, font) are also «სტრიქონი», never «მწკრივი». |
| preview, marked | გადახედვა, მონიშნულია | |
| another printout | სხვა ამონაბეჭდი | «ამ ფაილს არ ეკუთვნის». |
| untagged, no tag | ჭდის გარეშე, ჭდე არ აქვს | |
| confirm (cannot be confirmed) | დადასტურება (ვერ დადასტურდება) | Only in the cautions about untagged pages; never for "verified". |
| padded with zeros to a whole page | ნულებით შეივსება მთელ გვერდამდე | |
| default (system) | როგორც სისტემაში | Language menu item. |

### The command line's vocabulary

| English | Georgian | Notes |
|---|---|---|
| symbol (code symbol) | სიმბოლო | Coding-theory term. Label characters are «ნიშანი», so «სიმბოლო» is only the code symbol. |
| codeword | კოდური სიტყვა | |
| byte | ბაიტი | |
| encode / decode | კოდირება / დეკოდირება | Command names `encode`, `decode` stay English. "Decode again" «გაიმეორეთ დეკოდირება». |
| option (of a command) | პარამეტრი | «--protect პარამეტრი». Rejected: «ოფცია» (colloquial). |
| usage, positional arguments, options | გამოყენება, პოზიციური არგუმენტები, პარამეტრები | argparse headings. |
| default | ნაგულისხმევი | «(ნაგულისხმევი: a4)». |
| exit status | დასრულების კოდი | |
| portrait, landscape | წიგნისებრი, ალბომური (ორიენტაცია) | As Georgian office software names page orientation. |
| setup (of a development environment) | გარემოს მომზადება | Not «გამართვა», which is *debugging*. |
| stdout, stderr | stdout, stderr | Kept. |
| gap (in page numbering) | გამოტოვება | |
| ignored | გამოტოვებულია | |
| protection level `{level}` | დაცვის დონე {level} | The value stays English and reads as a name: «დაცვის დონე standard: …». |
| force | (`--force`, not translated) | "Saved anyway because of --force" «მაინც შენახულია --force პარამეტრის გამო». |

### Format specification terms (`format.md`)

| English | Georgian | Notes |
|---|---|---|
| page pixel, data pixel, scan pixel | გვერდის პიქსელი, მონაცემთა პიქსელი, სკანის პიქსელი | |
| page format, format string | გვერდის ფორმატი, ფორმატის სტრიქონი | |
| layout | განლაგება | Paper + dot size + page format. |
| grid | ბადე | |
| cross, origin, pitch | ჯვარი, ჯვრის სათავე, ჯვრების ბიჯი | |
| border, frame | ჩარჩო | |
| data area / data region | მონაცემთა არე / მონაცემთა ზონა | Kept apart as in Russian: geometric area (2.2) vs bytes of the container (4.6). |
| label band, label strip, font strip | წარწერის ზოლი, წარწერის ლენტი, შრიფტის ლენტი | |
| character (of the label), glyph, logo | ნიშანი, გლიფი, ლოგო | |
| interleave, spread | გადანაწილება, გაფანტვა | Kept apart. |
| page code | გვერდის კოდი | |
| Golay, Hamming, Reed-Solomon code | გოლეის კოდი, ჰემინგის კოდი, რიდ-სოლომონის კოდი | |
| parity, parity bytes, parity level | ლუწობა, ლუწობის ბაიტები, ლუწობის დონე | Never shown in the window. |
| check (of a tag) | საკონტროლო მნიშვნელობა | Not «შემოწმება» (reserved). |
| header, header copy | თავსართი, თავსართის ასლი | The word Georgian software uses for data headers (also the PGM file header). Not «სათაური», which means a title or heading. |
| magic | სიგნატურა | Field name `magic` stays in code font. |
| well-formed, acceptable, valid | სწორად აგებული, მისაღები, მართებული | "Valid" is «მართებული» everywhere in `format.ka.md` ("invalid" «არამართებული»); the other two are the defined terms of 6.2. |
| untrusted | არასანდო | |
| container, stream, payload, body | კონტეინერი, ნაკადი, სასარგებლო დატვირთვა, ტანი | |
| padding | შევსება | |
| erasure | წაშლილი ბაიტი (erasure) | The erasures of this format are bytes; «სიმბოლო» is reserved for the page-code symbol. |
| generator polynomial, field polynomial | წარმომქმნელი მრავალწევრი, ველის მრავალწევრი | |
| blur (the image is blurred) | გაბუნდოვნება (ბუნდოვანდება) | Not «იბინდება» (grows dim). |
| tolerance (of the decoder) | შემწყნარებლობა | Not «დაშვება», which also reads as "assumption". |
| try (a paper, a reader) | სინჯავს, ისინჯება; ცდის | Not «იცდება». |
| can / may (format page) | შეუძლია / შეიძლება | «შეიძლება» is reserved for the requirement word *may*; English *can* is «შეუძლია». |
| normative, informative | ნორმატიული, ინფორმაციული | |
| test vectors | სატესტო ვექტორები | |
| encoder, decoder, reader | კოდერი, დეკოდერი, წამკითხავი პროგრამა | "Reader" in parts 6 and 7 is any program; this project's two readers are «ჩვეულებრივი მეთოდი» and «ნელი მეთოდი». |

## Strength of claims

- **Verified** — «შემოწმებული», with the reserved root. Never softened
  («ალბათ მთელია») and never strengthened («გარანტირებულად»).
- **Recoverable vs recovered** — «აღდგენადია» says the pages read *should be
  enough*. "Can be repaired from the others" «შეიძლება აღდგეს დანარჩენი
  გვერდებით» (possibility); "repaired from the others" «აღდგენილია დანარჩენი
  გვერდებით» (done).
- **Promise of the tools** — «შეიძლება დაიკარგოს N» keeps the modal (may).
- **"May contain wrong parts", "may be damaged"** — keep «შეიძლება».
- **"Was not saved"** when the program chose so — «არ იქნა შენახული», not
  «ვერ შეინახა».

## Never translated

As in the Russian glossary: `optar`, `optar-gui`; command names; option names
and values (`none`, `standard`, `high`, `a4`, `letter`, `pdf`, `png`, `pgm`,
`medium`, `big`, `large`, `xlarge`); metavariables (`INPUT`, `BASE`, `OUTPUT`,
`LEVEL`, `TEXT`, `STRING`, `X`, `BASE_NNNN_debug.png`); file names and
extensions; environment variables; code, constants, header field names, the tag
parts `SIZE`, `FINGERPRINT`, `CC`; format strings; product and standard names
(PySide6, Ghostscript, SHA-256, PNG, TIFF, PDF, GF(256), dpi); version numbers.

## Site navigation

For `mkdocs.yml`, `nav_translations` of the `ka` entry and `site_description`.

| English | Georgian |
|---|---|
| Home | მთავარი |
| Using optar | optar-ით მუშაობა |
| Install | ინსტალაცია |
| Put a file on paper | ფაილის ქაღალდზე ჩაწერა |
| Read it back | ფაილის უკან წაკითხვა |
| Scans that are too coarse | ზედმეტად დაბალი გარჩევადობის სკანები |
| Command line | ბრძანების სტრიქონი |
| Reference | ცნობარი |
| How a page identifies itself | როგორ ამოიცნობა გვერდი |
| What has and has not been shown | რა არის ნაჩვენები და რა — არა |
| Format specification | ფორმატის სპეციფიკაცია |
| Project | პროექტი |
| Development | შემუშავება |
| History | ისტორია |

- **site_description:** ფაილების ქაღალდზე შენახვა ლაზერული პრინტერითა და სკანერით
- **site_name:** optar (unchanged)
- **Language name** (`[language].name` and the switcher): ქართული

## Interface strings the pages quote

Copy these from `ka.toml` exactly (English → Georgian):

| English | Georgian (catalogue) |
|---|---|
| Put on paper (tab) | ქაღალდზე ჩაწერა |
| Read from paper (tab) | ქაღალდიდან წაკითხვა |
| + Add scans… | + სკანების დამატება… |
| Save file… | ფაილის შენახვა… |
| Remove | ამოღება |
| Replace scan… | სკანის შეცვლა… |
| Use this scan | ამ სკანის გამოყენება |
| Switch to this document | ამ დოკუმენტზე გადასვლა |
| Assign to page… | გვერდის მითითება… |
| Start a document by hand… | დოკუმენტის ხელით აწყობა… |
| Being read (section) | იკითხება |
| Not readable (section, state) | ვერ იკითხება |
| Not part of this file | ამ ფაილს არ ეკუთვნის |
| Prints as: | დაიბეჭდება: |
| Dot size: / Protection: | წერტილის ზომა: / დაცვა: |
| Create PDF… | PDF-ის შექმნა… |
| Compatible with optar 0.2 and the original optar | თავსებადობა optar 0.2-თან და თავდაპირველ optar-თან |
| Standard / Medium / Big / Large / Extra large (dots) | სტანდარტული / საშუალო / დიდი / მსხვილი / ძალიან მსხვილი |
| None / Standard / High (protection) | არა / სტანდარტული / მაღალი |
| Good / Missing / Waiting | წესრიგშია / აკლია / რიგში |
| Repaired · N | გამოსწორებულია · N |
| Damaged · N lost | დაზიანებულია · დაიკარგა N |
| Read by the slower reader | წაკითხულია ნელი მეთოდით |
| Page 3 · Read by the slower reader · 265,112 dots corrected | გვერდი 3 · წაკითხულია ნელი მეთოდით · შესწორდა 265 112 წერტილი |
| · 6,912 bytes repaired by the document's protection | · დოკუმენტის დაცვით გამოსწორდა 6 912 ბაიტი |
| Opening the file / Finding the page / Identifying the page / Reading the data | ფაილის გახსნა / გვერდის ძებნა / გვერდის ამოცნობა / მონაცემების წაკითხვა |
| Slower reader: sampling / pass 4 of 5 | ნელი მეთოდი: ნიმუშების აღება / გავლა 4 5-დან |
| File recovered and verified · N bytes | ფაილი აღდგენილი და შემოწმებულია · N ბაიტი |
| Does not match the fingerprint on the paper | არ ემთხვევა ქაღალდზე დაბეჭდილ ფაილის ანაბეჭდს |
| Recoverable: page 3 missing, can be repaired from the others | აღდგენადია: აკლია გვერდი 3, შეიძლება აღდგეს დანარჩენი გვერდებით |
| Recoverable: page 3 missing, repaired from the others · matches the fingerprint | აღდგენადია: აკლია გვერდი 3, აღდგენილია დანარჩენი გვერდებით · ემთხვევა ანაბეჭდს |
| Working… 3 of 6 scans read | მუშავდება… 6 სკანიდან წაკითხულია 3 |
| Checking the fingerprint… | მიმდინარეობს ანაბეჭდთან შედარება… |
| All N pages read · cannot be verified (no tag) | წაკითხულია ყველა N გვერდი · შემოწმება შეუძლებელია (ჭდის გარეშე) |
| 4 of 6 pages good · 1 damaged · 1 missing | 6 გვერდიდან 4 წესრიგშია · 1 დაზიანებულია · 1 აკლია |
| the worst spot used 57% of its repair capacity (18 of 32): a moderate margin | ყველაზე უარესმა ადგილმა გამოსწორების რესურსის 57% გამოიყენა (32-დან 18): ზომიერი მარაგი |
| can lose N page(s) of T | T გვერდიდან შეიძლება დაიკარგოს N |
| Scanned at about 200 dpi, which is too coarse to read | დასკანერებულია დაახლოებით 200 dpi გარჩევადობით, რაც წასაკითხად ზედმეტად დაბალია |
