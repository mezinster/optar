# Georgian (`ka`): independent native read

Reader: native-level reader and technical editor of modern Georgian. I read the
catalogue and the eleven pages beside the English, formed a view of each file, then read
the three translators' reports and judged their open questions (last section).

Overall: a careful, mostly natural translation. The polite plural «თქვენ» is used everywhere
with no break. Placeholders with hyphenated endings («{total}-დან», «გვერდ {page}-ისთვის»,
«`BASE.pdf`-ს», «PDF-ის») are handled correctly throughout. Numerals take singular nouns
everywhere, so the single `other` form is right for 0, 1, 2, 5, 11, 21, 22, 25, 101 and 111.
`single`/`several` entries read right with one page and with several. Typography is correct:
„…“ quotes, no-break-space thousands separators, decimal comma outside the format page,
en dash in ranges. The few real faults are listed below.

Kinds: 1 mistranslation, 2 change of strength, 3 grammar, 4 unnatural phrasing,
5 glossary/consistency, 6 typography, 7 should/should not stay English, 8 length.

---

## src/optar/locale/ka.toml

1. `cli.protection.within` — «დაცვის დონე {level}: გვერდების შიგნით დაზიანება სწორდება, მაგრამ
   დაკარგულ გვერდს ვერ ანაზღაურებს.» — The second verb has no subject. Grammatically its subject
   is «დაზიანება» ("damage cannot make up for a lost page"). In English the subject is the
   protection. — «დაცვის დონე {level}: გვერდების შიგნით დაზიანებას ასწორებს, მაგრამ დაკარგულ
   გვერდს ვერ ანაზღაურებს.» — 3
2. `gui.rejected.other_document` — «… გვერდ {page}-ისთვის: ის სხვა ამონაბეჭდის გვერდ {other}-ს
   ეკუთვნის: {printout}.» — Two colons in one sentence. The second one reads as though the
   printout were an explanation of the first. — «… გვერდ {other}-ს ეკუთვნის ({printout}).» or
   «… ეკუთვნის — {printout}.» — 4/6
3. `cli.force_saved.unrepaired`, `cli.force_saved.mismatch` — «…: მან შემოწმება ვერ გაიარა …» —
   The pronoun «მან» is a calque of English "it". Georgian drops it here. — «…: შემოწმება ვერ
   გაიარა და შეიძლება დაზიანებული იყოს.» — 4
4. `gui.SLOW_TRIED` — «დაბალი გარჩევადობის სკანების ნელი მეთოდიც იქნა ნაცადი, მაგრამ მანაც ვერ
   წაიკითხა.» — «იქნა ნაცადი» is a bureaucratic passive (a calque of Russian «был испробован»),
   and the sentence is heavy. — «ნელი მეთოდითაც (დაბალი გარჩევადობის სკანებისთვის) წაკითხვა ვერ
   მოხერხდა.» — 4
5. `cli.probe.coarse_tried` — «(ნელი მეთოდიც იქნა ნაცადი)» — Same passive. — «(ნელი მეთოდითაც
   ვერ მოხერხდა)» — 4
6. `cli.help.no_slow_reader` — «ნელი მეთოდი არ იქნეს ნაცადი სკანებზე, …» — The passive optative
   «არ იქნეს ნაცადი» is archaic and stiff. The other help lines use a masdar or an active form. —
   «ნელი მეთოდი არ გამოიყენოს სკანებზე, რომლებსაც ჩვეულებრივი მეთოდი ვერ ამოიცნობს» — 4
7. `err.too_few_dots` — «… ზედმეტად ცოტაა, რომ მათგან ისწავლოს» — «ისწავლოს» has no subject
   (who learns?). This calques "to learn from". — «გვერდზე ზედმეტად ცოტა ცნობილი წერტილია მათზე
   დასაყრდნობად» — 4
8. `err.page_clipped` — «… ველს ტოვებს და პრინტერი მას მოჭრის» — The English "would be
   clipped" is conditional, and «მას» could refer to «ველს». — «… ველს ტოვებს, ამიტომ პრინტერი
   გვერდს მოჭრიდა» — 4
9. `gui.STILL_WRITING` — «დაველოდოთ, სანამ დასრულდება?» — Uses 1st person plural, while the
   glossary rule for questions in dialogs is 1st person singular («მაინც შევინახო?»). —
   «დაველოდო, სანამ დასრულდება?» — 5
10. `gui.write.dot_size` — «{dots} (სკანირება: {dpi} dpi)» — «სკანირება» here, while the rest of
    the catalogue uses «დასკანერება / დაასკანერეთ». It also reads as a label rather than advice.
    — «{dots} (დაასკანერეთ {dpi} dpi-ით)» — 5
11. `gui.state.mismatch`, `gui.save.mismatch` — «ქაღალდზე დაბეჭდილ ანაბეჭდს» — "the imprint
    printed on the paper" can be taken as the physical print, so the sentence comes close to a
    tautology. These are the only two places where «ანაბეჭდი» sits next to «დაბეჭდილი». —
    «ქაღალდზე დაბეჭდილ ფაილის ანაბეჭდს» (the glossary's own device). — 4
12. `gui.slow.repaired` — «… {n} ბაიტი იყო არასწორი და ის დოკუმენტის დაცვამ გამოასწორა.» —
    «ის» is superfluous. — «… იყო არასწორი და დოკუმენტის დაცვამ გამოასწორა.» — 4
13. `gui.REPLACE_REJECTED_TITLE` — «სკანი არ იქნა გამოყენებული» — This dialog title is twice the
    English length (see the length list). — «სკანი არ გამოყენებულა» — 8
14. `PAPER_HINT` — «… და გვერდი სწორ მდგომარეობაშია დასკანერებული (არ არის მობრუნებული).» —
    Wordy. — «… და გვერდი დასკანერებულია სწორი ორიენტაციით (მობრუნების გარეშე).» — 4
15. Line 1 — a Georgian header comment that is not in `en.toml`. The brief wants the catalogue's
    comments identical to `en.toml`'s. — Remove the line. — 7 (trivial)
16. `err.label_band` uses «მწკრივი» for "rows", while `format.ka.md` uses «სტრიქონი» for the same
    rows of the label band. — Use «სტრიქონი» in both `err.label_band` and `err.label_font`. — 5

Length (kind 8): the ten longest relative to English among short window strings:
`gui.health.good` 2.25 «წესრიგშია»; `gui.row.spare` / `spare_tag` 2.00 «სათადარიგო»;
`gui.REPLACE_REJECTED_TITLE` 2.00 (see 13); `gui.ADD_SCANS_TITLE` 1.89 «სკანების დამატება»;
`gui.detail.lost` 1.75; `gui.button.save` 1.75 «შენახვა»; `gui.ADD_SCANS` 1.67;
`gui.DOTS_FIELD` 1.56 «წერტილის ზომა:»; `gui.USE_SPARE` 1.54. All except 13 are the shortest
correct Georgian, and in absolute length they are short (≤ 22 characters). Only 13 has a
shorter wording with no loss.

Verdict: fit to publish after the listed fixes (1 and 2 matter; the rest are polish).

## docs/index.ka.md

1. Line 17–20 — «… პროგრამა ასწორებს ლაქებს და მოგლეჯილ კუთხეებს» — Literally "corrects stains".
   The English allows this, but in Georgian it sounds odd. — «… ასწორებს ლაქებით და მოგლეჯილი
   კუთხეებით გამოწვეულ დაზიანებას» — 4 (minor)

Verdict: fit to publish as is (the change above is optional).

## docs/install.ka.md

1. Lines 24–26 — «გახსენით System Settings, შემდეგ Privacy & Security და აირჩიეთ „Open Anyway“
   (… აირჩიეთ Open)» — The rule for macOS (no Georgian interface) is the English name followed by
   a Georgian translation in brackets. The translations are missing. — «გახსენით System Settings
   (სისტემის პარამეტრები), შემდეგ Privacy & Security (კონფიდენციალურობა და უსაფრთხოება) და
   აირჩიეთ „Open Anyway“ („მაინც გახსნა“) (macOS-ის ძველ ვერსიებში დააწკაპუნეთ აპლიკაციაზე თაგვის
   მარჯვენა ღილაკით და აირჩიეთ Open (გახსნა)).» The English names are correct for macOS 13 and
   later: "System Settings", "Privacy & Security", "Open Anyway", and "Open" in the context menu.
   — 7
2. Line 47 — «აპლიკაციას ეკრანის გარეშე უშვებს და გასინჯავს, …» — Mixes tenses: present «უშვებს»
   with future «გასინჯავს». — «… უშვებს და ასინჯავს, შეუძლია თუ არა …» — 3
3. Windows: the English names no dialog wording, so there is nothing to check. Windows does ship a
   Georgian interface pack, so if SmartScreen's buttons are ever quoted, they must be checked on a
   real system.

Verdict: fit to publish after the listed fixes.

## docs/history.ka.md

1. Line 23 — «… იმავე გვერდებს კითხულობს და წერს, რასაც C პროგრამები.» — «რასაც» has a plural
   antecedent. — «…, რომლებსაც C პროგრამები.» — 3 (minor)

Verdict: fit to publish as is (the change is optional).

## docs/put-on-paper.ka.md

1. Line 114 (note title) — «თავსებად ამონაბეჭდში ფაილი შევსებულია» — Out of context «შევსებულია»
   reads as "the file is filled in / complete", which is the opposite of the warning. — «თავსებადი
   ამონაბეჭდიდან ფაილი ნულებით შევსებული ბრუნდება» — 1
2. Line 95 — «რომლის დაცვით ამონაბეჭდიც …» — An instrumental used as an attribute (see "Glossary
   terms to reconsider"). — «რომლის დაცვით შექმნილი ამონაბეჭდიც …» — 4/5
3. Line 84 (table head) — «1 გვერდის დაკარგვა შეიძლება, თუ დოკუმენტი შეიცავს» — «შეიძლება» with
   a masdar subject reads as "is allowed". — «შეიძლება დაიკარგოს 1 გვერდი, თუ დოკუმენტი შეიცავს»
   — 4 (minor)

Verdict: fit to publish after the listed fixes.

## docs/read-from-paper.ka.md

1. Line 103 — «… წაკითხული გვერდები მათი აღსადგენად საკმარისი უნდა იყოს.» — Wrong pronoun form:
   with «-ად» purpose phrases the truncated genitive is needed. — «… მათ აღსადგენად …» — 3
2. Lines 88, 103, 110, 127 — «დაცვით დოკუმენტი(ში/სთვის)» — An attributive instrumental, which
   is unidiomatic (see "Glossary terms to reconsider"). — «დაცვით შექმნილი დოკუმენტი» — 4/5
3. Line 102 — «… დაიწყეთ მათით, რომლებიც „გამოსწორებულია“ აღნიშვნით არის მონიშნული.» — Heavy, and
   «მათით» is awkward. — «… დაიწყეთ იმ გვერდებით, რომელთა მდგომარეობაა „გამოსწორებულია“.» — 4
4. Line 26 — «მეორე, უფრო ნელ წაკითხვის მეთოდს» — The adjective is separated from its noun by the
   genitive and reads as "the slower reading". — «წაკითხვის მეორე, უფრო ნელ მეთოდს» (the same
   applies in slower-reader line 7 and format 7.6). — 4
5. Line 114 — «თუ გამოსწორება ვერ მოხერხდა, ის ასახელებს …» — «ის» can refer to «გამოსწორება». —
   «…, ფანჯარა ასახელებს …» — 4
6. Line 120 — «… რომ გამოსწორებას წარუმატებლობა არ დაუფიქსირებია.» — «დააფიქსირა» is a
   Russianism. — «… რომ გამოსწორებისას შეცდომა არ გამოვლენილა.» — 4
7. Line 130 — «უფრო ნაკლებიდან» — Pleonasm. — «ნაკლებიდან» — 4

Verdict: fit to publish after the listed fixes.

## docs/slower-reader.ka.md

1. Lines 91–92 — «ის არასწორ ფაილს სწორად არ აჩვენებს» — This reads as "it does not display a
   wrong file properly". The English says the slower reader does not make a wrong file *look*
   right. — «ის არასწორ ფაილს სწორად ვერ მოაჩვენებს» or «ის არასწორ ფაილს სწორ ფაილად არ
   წარმოაჩენს» — 1
2. Lines 50–51 — «შესწორებულია წერტილი, რომლის საკუთარი კვალი … უკუგდებული აღმოჩნდა.» — This reads
   as a statement ("a dot is corrected") rather than a definition. — «შესწორებული ეწოდება
   წერტილს, რომლის საკუთარ კვალს მისი სიმბოლოს არჩევისას ანგარიში არ გაეწია.» — 4
3. Line 67 — «რომელზეც ნელი მეთოდი იცდება. `--no-slow-reader` მას გამორთავს.» — «იცდება» is a rare
   and odd passive, and the future «გამორთავს» is used for a general fact. — «რომელზეც ნელ მეთოდს
   ცდის. `--no-slow-reader` მას თიშავს.» — 4
4. Lines 76–77 — «… ვიდრე ნელი მეთოდის გაჩენამდე.» — The English says "without the slower
   reader". — «… ვიდრე ნელი მეთოდის გარეშე.» — 4
5. Line 7 — word order of «მეორე, უფრო ნელი წაკითხვის მეთოდი», as in read-from-paper 4. — 4

Verdict: fit to publish after the listed fixes.

## docs/identification.ka.md

1. Lines 81–82 — «256 არასწორი წაკითხვიდან დაახლოებით 1 მაინც შეიძლება გაიაროს საკონტროლო
   მნიშვნელობასთან შედარება» — «1 მაინც» after a numeral reads as "at least 1". That turns "about
   1 in 256 can still pass" into "at least about one". — «(256 არასწორი წაკითხვიდან დაახლოებით
   ერთმა შეიძლება ისე გაიაროს საკონტროლო მნიშვნელობასთან შედარება, რომ შეცდომა არ გამოვლინდეს)»
   — 2
2. Line 42 — «გვერდის სათაური თავისთავად არასანდოა» — For an ordinary reader «გვერდის სათაური» is
   "the page's title". See the header term under "Glossary terms to reconsider". — 5

Verdict: fit to publish after the listed fixes.

## docs/evidence.ka.md

1. Line 71 (heading) — «იგივე გვერდები, რაც C პროგრამისა» — Ungrammatical ellipsis. — «იგივე
   გვერდები, რასაც C პროგრამა ქმნის» — 3
2. Lines 19–20 — «300\n dpi-ზეც» — The number and the unit are split across a source line, so the
   page may wrap between them. — Keep «300 dpi-ზეც» on one line (or use a no-break space). — 6
   (minor)

Verdict: fit to publish after the listed fixes.

## docs/command-line.ka.md

1. Lines 65–67 — «… თუ არ მიუთითებთ `--force`-ს, რომელიც აღდგენილს ინახავს მაშინაც, როცა მან
   შემოწმება ვერ გაიარა.» — «მან» grammatically refers to `--force` (the nearest «რომელიც»), so
   the clause reads "even when --force did not verify". «თუ … თუ» is also stacked. — «ფაილს წერს
   მხოლოდ მაშინ, როცა ანაბეჭდი ემთხვევა; გამონაკლისია `--force`, რომელიც აღდგენილს ინახავს
   მაშინაც, როცა ფაილმა შემოწმება ვერ გაიარა.» — 1/3
2. Line 74 — «ლანდშაფტური სკანები» — A calque. Georgian office software says «ალბომური» for
   landscape (and «წიგნისებრი» for portrait); this needs checking against current Georgian UI
   wording. — «ალბომური ორიენტაციის სკანები» — 4

Verdict: fit to publish after the listed fixes.

## docs/development.ka.md

1. Line 10 (heading) — «გამართვა და ტესტები» — In Georgian software «გამართვა» is the established
   word for *debugging*. "Setup" is «მომზადება» / «გარემოს მომზადება». — «გარემოს მომზადება და
   ტესტები» — 1
2. Line 74 — «ყოველ სათაურზე — ინგლისური id» — Here «სათაური» means a heading, while elsewhere it
   is the format's *header*. See "Glossary terms to reconsider". — 5

Verdict: fit to publish after the listed fixes.

## docs/format.ka.md

1. 7.4 step 1, line 1207 — «შემდეგ გამოსახულება იბინდება 3-ზე 3 ბირთვით» — «იბინდება» means
   "grows dim / dusk falls". The pages use «გაბუნდოვნება» for blur. — «შემდეგ გამოსახულება
   ბუნდოვანდება 3-ზე 3 ბირთვით (1 2 1 / 2 4 2 / 1 2 1), …-ჯერ» — 1/5
2. 6.3, lines 1087–1093, and 4.5, line 718 — «სასარგებლო დატვირთვის ბაიტი წაშლილი სიმბოლოა
   (erasure), როცა მისი ერთ-ერთი ბიტი მდებარეობს სიმბოლოში, …» — «სიმბოლო» means two things in
   one sentence: an erasure and the page-code symbol of 2.5. The erasures are bytes. — «… ბაიტი
   წაშლილი ბაიტია (erasure), როცა …»; «… წაშლილი ბაიტია»; «(ლუწობა 0-ის დროს: წაშლილი ბაიტი არ
   აქვს)»; 4.5: «(წაშლილი ბაიტები, erasures)» — 5
3. 8, lines 1297–1299 — «… რომელიც 2012 წლიდან `colindean/optar`-ში ვითარდება» — The present
   tense says it is still being developed. The English says "maintained from 2012", and the
   history page gives 2012–2018. — «… რომელსაც 2012 წლიდან `colindean/optar`-ში უვლიდნენ» — 1/2
4. 6.3, line 1105 — «ვიდრე მისი ლუწობით შეიძლება გამოსწორდეს» and 4.9, line 841 — «ნებისმიერი `n`
   გვერდი შეიძლება დაიკარგოს» — Both render English *can*, but the page's own rule keeps
   «შეიძლება» for *may*. — «ვიდრე მის ლუწობას შეუძლია გამოასწოროს»; «… შესაძლებელია ნებისმიერი
   `n` გვერდის დაკარგვა» — 5
5. 7.4 step 3, line 1217 — «აიღება ისე, როგორც წაიკითხა» — An aorist with no agent ("as [who?]
   read it"). — «აიღება ისე, როგორც წაკითხულია» — 3
6. 7.5, lines 1239–1240 — «ორი ქაღალდი იცდება …; თითოეული იცდება …» — An odd passive (as in
   slower-reader 3). — «ორივე ქაღალდი ისინჯება …; თითოეული ისინჯება …» — 4
7. 7.2 step 3, line 1173 — «ეს ამ დეკოდერის დაშვებაა» — «დაშვება» also means "assumption". The
   English is "tolerance". — «ეს ამ დეკოდერის შემწყნარებლობაა (tolerance)» or «… დეკოდერის
   შეღავათია» — 4
8. 7.6, line 1263 — «მეორე, უფრო ნელ წაკითხვის მეთოდს» — Word order (as in read-from-paper 4). —
   «წაკითხვის მეორე, უფრო ნელ მეთოდს» — 4

Requirement words are otherwise consistent: must «უნდა», must not «არ უნდა», may «შეიძლება»,
need not «საჭირო არ არის» (5.4), required «სავალდებულო» (7). Valid / well-formed / acceptable
are «მართებული» / «სწორად აგებული» / «მისაღები», one way throughout. Every number, table cell
and example is unchanged.

Verdict: fit to publish after the listed fixes (1–3 should go in; 2 is a glossary change).

---

## Templates that still do not fit

None. Every template can be said naturally in Georgian. The faults above are wording inside the
existing shapes.

## Glossary terms to reconsider

- **erasure «წაშლილი სიმბოლო» → «წაშლილი ბაიტი» (erasure).** In this format the erasures are
  bytes, and «სიმბოლო» is the defined term for the page-code symbol. Cost: the glossary line plus
  4 places in `format.ka.md` (lines 718, 1087–1088, 1090, 1093).
- **«დაცვით ამონაბეჭდი / დაცვით დოკუმენტი» → «დაცვით შექმნილი ამონაბეჭდი / დოკუმენტი».** An
  instrumental noun used as an attribute is not idiomatic Georgian («დაცვით დოკუმენტში» reads as
  "in document, with protection"). «დაცვიანი» is acceptable but colloquial. Cost: 6 places
  (`gui.too_large.protect`, put-on-paper 95, read-from-paper 88, 103, 110, 127) and the glossary
  note on "protection".
- **header «სათაური» → «თავსართი» (optional, but recommended).** In everyday Georgian «სათაური»
  is "title / heading". In the user pages, «გვერდის სათაური არასანდოა» (identification 42) and
  «სათაურის გარეშე ძველი გვერდი» (slower-reader 28) read as the page's printed *title*, and
  development 74 uses «სათაური» for a Markdown heading. «თავსართი» is the word Georgian software
  localisation uses for data headers; confirm against current usage before changing. Cost: about
  41 occurrences (format.ka 34, slower-reader 3, identification 2, evidence 1, glossary). If it is
  kept, at least change development 74 so that one word does not mean two things.

---

## Judgement on the translators' open questions

- **«ანაბეჭდი» (fingerprint) beside «ამონაბეჭდი» (printout).** Workable. «ანაბეჭდი» is the normal
  word for a key or hash fingerprint, and the two words are different enough to read apart. The
  one real risk is «ქაღალდზე დაბეჭდილი ანაბეჭდი» ("the print printed on the paper"), which is
  catalogue finding 11. There, and only there, the glossary's «ფაილის ანაბეჭდი» should be used.
- **Root «შემოწმ-/ამოწმ-» reserved for verified; «აკონტროლებს/კონტროლდება» for checking;
  «საკონტროლო მნიშვნელობა» for a tag's check.** Good, and applied consistently. «ფაილს ვერ
  ამოწმებს», «დარწმუნდით, რომ დოკუმენტმა შემოწმება გაიარა» and «ფაილს მხოლოდ ანაბეჭდი ამოწმებს»
  all read naturally. One acceptable exception: identification 85, «საბოლოო შემოწმება» for the
  fingerprint comparison, is in substance verification.
- **Tag «ჭდე», «ჭდიანი დოკუმენტი», «მარტივი დოკუმენტი».** Good. «ჭდე» is the Mozilla word and has
  no collision. «ჭდიანი» forms naturally. «მარტივი» for "plain" is fine.
- **Label forms for option lists and dot-size names** («… ვერ გამოიყენება შემდეგთან ერთად:
  {options}», «წერტილები: {dots}», «სტანდარტული — 600»). Right choice: they read naturally and
  avoid endings on inserted values.
- **«გვერდ {page}-ისთვის».** Correct, standard Georgian (cf. «ოთახ 5-ში»), slightly bookish. Keep
  it: «მე-{page} გვერდისთვის» would break on 1 («1-ლი»). «გვერდი 3 12-დან» for "page 3 of 12" is
  also normal.
- **Requirement words in the format page.** Correct and consistent, except the two «შეიძლება» for
  *can* (format finding 4).
- **«მართებული» / «სწორად აგებული» / «მისაღები».** Good choices, kept distinct throughout.
- **Erasure «წაშლილი სიმბოლო».** I agree with the format translator: change it to «წაშლილი
  ბაიტი» (see "Glossary terms to reconsider").
- **«განყოფილება» for both a site page and a spec section.** Acceptable. The format page never
  refers to site pages, and the user pages never refer to spec sections without naming the
  specification («ფორმატის სპეციფიკაციის მე-8 ნაწილში»). The glossary should note the second use.
- **«ზოლი» for the label band and the narrow/wide strips.** Acceptable. It is always qualified
  («წარწერის ზოლი», «ვიწრო ზოლი», «ქვედა ზოლი»), and no sentence is ambiguous.
- **Header «სათაური».** It does collide with heading/title, in the user pages and in
  development 74. See "Glossary terms to reconsider".
- **«არა» as the protection level "None".** Acceptable in a selector next to «სტანდარტული» and
  «მაღალი» («დაცვა: არა» reads as "Protection: none").
- **Singular verbs with inanimate plural subjects** («დაზიანებულია გვერდები 5 და 6»). Normal and
  natural.
- **`cli.help.no_slow_reader` register.** Too stiff (catalogue finding 6).
- **Install page, macOS names.** The English names are right, but the bracketed Georgian
  translations that the rule requires are missing (install finding 1).
