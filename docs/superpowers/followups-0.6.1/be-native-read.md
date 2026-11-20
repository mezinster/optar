# Belarusian (`be`): independent native read

Read against English: `src/optar/locale/be.toml` (every key, every plural form tried
with 0, 1, 2, 5, 11, 21, 22, 25, 101, 111; every `single`/`several` entry with one page
and with several; the phrases joined by « · » and the inserted parts) and the eleven
`docs/*.be.md`. The glossary and the brief were read first. The translators' reports
were read only after this review was done.

Overall: a careful translation in the official orthography. The ў/у rule holds
everywhere (checked by script across lines). The apostrophe is consistent, quotation
marks are «» with „“ inside, and the no-break thousands separator and decimal comma are
correct outside code. No plural or agreement error was found in any template. No claim
is stronger or weaker than the English. Interface strings quoted on the pages match the
catalogue exactly. `tests/unit/test_catalogues.py` and `test_doc_translations.py` pass
for `be`. The findings below are mostly about wording. One is about meaning in a
normative sentence (format F1), and one breaks the brief's rule for macOS names
(install N1).

Kinds: 1 mistranslation, 2 strength, 3 grammar, 4 unnatural phrasing,
5 glossary or consistency, 6 typography, 7 should or should not stay English,
8 too long.

---

## `docs/format.be.md`

F1. 6.2, lines 1053–1054 — «Праграма чытання павінна трымаць расход памяці і часу
прапарцыйным колькасці старонак, якія ёй далі, а не таму, што заяўляе загаловак» —
«а не таму, што» is read by a Belarusian reader as «а не because…» ("and not because the
header claims"), so the requirement says something other than the English ("not to what a
header claims"). «Расход» is also a Russian-flavoured word; Belarusian technical writing
prefers «выдаткі». — «Праграма чытання павінна трымаць выдаткі памяці і часу
прапарцыйнымі колькасці старонак, якія ёй далі, а не колькасці, якую заяўляе
загаловак» — kind 1 (and 4).

F2. 8, line 1303 — «арыфметыка з плаваючай коскай у 32 бітах» — «плаваючая коска»
copies Russian «плавающая запятая». The established Belarusian term is «рухомая коска»
(«лікі з рухомай коскай»). — «32-бітная арыфметыка з рухомай коскай» — kind 4.

F3. 1.1, lines 43–44 — «Усе тры ўжываюцца толькі да неадмоўных цэлых лікаў» —
«ужываць да» copies Russian «применяются к». — «Усе тры ўжываюцца толькі для неадмоўных
цэлых лікаў» — kind 4.

F4. 3, lines 529–530 — «якія старонкі належаць разам» — a calque of "belong together";
«належаць» needs a complement in Belarusian. — «якія старонкі складаюць адзін
дакумент» — kind 4.

F5. 4.7, line 768 — «Нулявыя байты друкуюцца як белыя лініі праз кожную старонку» —
«праз» means "through, via" ("across" is a calque of Russian «через»). — «…як белыя
палосы ўпоперак кожнай старонкі» (also matches «палосамі» in identification.be.md) —
kind 4.

F6. 7.4 step 2, line 1181, and 7.5 steps 2–3, lines 1213 and 1218 — «Адлік павышаецца ў
рэзкасці»; «старонка знаходзіцца, і яе надпіс чытаецца…»; «старонка знаходзіцца,
раскадоўваецца…» — «старонка знаходзіцца» is read first as "the page is located
(situated)", not "is found". The first phrase is awkward. — «Рэзкасць адліку
павышаецца: …»; «старонку знаходзяць і чытаюць яе надпіс, супастаўляючы…»; «старонку
знаходзяць, раскадоўваюць, і вырашае дапушчальны загаловак» — kind 4.

F7. 8, line 1267 — «таго рэпазітарыя» — the other pages write «рэпазіторый»
(install, history ×2, evidence). — «таго рэпазіторыя» — kind 5.

Checked and correct (no finding): «павінен / павінна / павінны», «не павінен…»,
«можа», «не абавязана», «нельга» map one-to-one onto must / must not / may /
need not / cannot at every one of the English occurrences. «Правераны» appears only for
verified. «Кантраляваць / кантроль» is used for ordinary checking (4.9, 6.3, 6.4, 7.5).
«Сапраўдны» (11 occurrences) always means valid. «Карэктны» and «дапушчальны» appear
only as the defined terms of 6.2. Every number, decimal point and example is unchanged.

Verdict: **fit to publish after the listed fixes** (F1 is required; the rest are
wording).

## `docs/install.be.md`

N1. Lines 24–27 — «адкрыйце «Сістэмныя налады» (System Settings), раздзел
«Прыватнасць і бяспека» (Privacy & Security), і выберыце «Усё роўна адкрыць» (Open
Anyway). У старэйшых версіях macOS … выберыце «Адкрыць» (Open).» — breaks the brief's
rule: macOS has no Belarusian interface, so the user sees the English names. Those must
come first, with a Belarusian translation in brackets. — «адкрыйце System Settings
(«Сістэмныя налады»), раздзел Privacy & Security («Прыватнасць і бяспека») і выберыце
Open Anyway («Усё роўна адкрыць»). У старэйшых версіях macOS пстрыкніце па праграме
правай кнопкай мышы і выберыце Open («Адкрыць»).» The English names are the ones macOS
13 and later shows: System Settings, Privacy & Security, Open Anyway, and Open in the
context menu. Macs older than macOS 13 say "System Preferences" instead of "System
Settings", but the English page names only System Settings, so this is not a finding. —
kind 7 (and 5).

Verdict: **after the listed fix.**

## `src/optar/locale/be.toml`

C1. `gui.reason.size_mismatch` — «Гэты скан зроблены з паперы іншага памеру, чым у
дакумента» — «зроблены з паперы» first reads as "made of paper". — «Памер паперы на
гэтым скане не такі, як у дакумента» — kind 4.

C2. `gui.name.printed` — «Менавіта па надрукаванай назве старонкі потым апазнаюцца.» —
«апазнаць» is the glossary's verb for the *program* identifying a scan. Here it suggests
that the program identifies pages by the printed name, which the English does not say
(the name is for people; a larger-dot label is not read at all). — «Менавіта па
надрукаванай назве потым можна пазнаць старонкі.» — kind 1.

C3. `gui.rejected.other_page` — «гэта старонка {other} гэтага дакумента, і ў спісе ён
паказаны пры гэтай старонцы.» — three «гэт-» in a row, and «пры гэтай старонцы» can be
read as page {page}. — «гэта старонка {other} гэтага дакумента, і ў спісе ён стаіць пры
старонцы {other}.» — kind 4.

C4. `gui.SLOW_TRIED`, `cli.probe.coarse_tried` — «таксама быў выпрабаваны» —
«выпрабаваць» leans towards "test, put on trial"; "was tried" is «паспрабаваць». —
`gui.SLOW_TRIED`: «Павольны метад для сканаў з нізкай раздзяляльнасцю таксама
паспрабаваў прачытаць скан, але не змог.»; `cli.probe.coarse_tried`: «(павольным метадам
таксама спрабавалі)» — kind 4.

C5. `cli.help.label` — «назва файла, зададзеная ў -o» — an option is given *with* -o,
not *in* it. — «назва файла, зададзеная праз -o» — kind 4.

C6. `cli.help.base` — «і г. д.» — the abbreviation should not break across lines in
`--help` output. — «і г. д.» (no-break spaces) — kind 6.

Checked and correct: all plural tables (for example `gui.health.damaged`: «страчаны 1 / 21»,
«страчаны 3», «страчана 5 / 11»; `gui.state.repaired` feminine for pages;
`gui.detail.repaired` masculine for blocks; `cli.too_few.read` «з 1 старонкі / з 2
старонак»; `gui.write.promise` accusative «страціць 21 старонку»), every
`single`/`several` entry, the inserted dot-size names (nominative, in label-like
positions), and `gui.reason.not_decodable` (a full sentence). The translator's report
judged every template to fit, and I agree: none needs a change of the English shape.

Verdict: **after the listed fixes** (all small; C1 and C2 matter most).

## `docs/index.be.md`

I1. Line 56 — «і дадае да іх праграму з акном, большыя кропкі, абарону і адбітак» —
«да іх» refers back to «старонкі», so the sentence says the project adds the desktop
application and so on to the pages. — «і дадае праграму з акном, большыя кропкі, абарону
і адбітак» — kind 1.

Verdict: **after the listed fix.**

## `docs/slower-reader.be.md`

S1. Line 69 — «для кожнага скана, на якім ён спрабуецца» — a reflexive passive copied
from Russian. — «для кожнага скана, на якім яго спрабуюць» — kind 4.

S2. Lines 73 and 77–78 — «Старонка A4 … заняла агулам ад 40 да 70 секунд»; «Выява … займае
прыкладна на 20–35 секунд больш» — a page or an image does not "take" time in
Belarusian; reading it does. — «Чытанне старонкі A4 на камп'ютары распрацоўшчыка заняло
агулам ад 40 да 70 секунд…»; «На выяву, якая … , ідзе прыкладна на 20–35 секунд больш,
чым без павольнага метаду» — kind 4.

S3. Line 47 — «Калі выбраць радок, там сказана, што гэта зойме каля хвіліны.» — «там»
has nothing to refer to. — «Калі выбраць радок, у падрабязнасцях будзе сказана, што гэта
зойме каля хвіліны.» — kind 4.

Verdict: **after the listed fixes** (wording only).

## `docs/identification.be.md`

D1. Line 13 (first mention), heading line 21 — «самаапазнавальныя старонкі» without the
gloss the glossary requires on first mention on a page. The translator left it out
deliberately because the section explains the term. Either add it — «(«самаапазнавальныя
старонкі», якія самі паведамляюць, да якога дакумента яны належаць і які ў іх нумар)» —
or relax the glossary rule for this page. — kind 5.

D2. Line 38 — «друкаваліся белымі палосамі праз старонкі» — see F5. — «…белымі
палосамі ўпоперак старонак» — kind 4.

Verdict: **after the listed fixes.**

## `docs/evidence.be.md`

E1. Line 81 — «Кожная старонка самаапазнавальнай раздрукоўкі» — the first mention on the
page, with no gloss (glossary). — add «(старонкі якой самі паведамляюць, да якога
дакумента яны належаць і які ў іх нумар)» — kind 5.

Verdict: **after the listed fix** (otherwise fit as is).

## `docs/put-on-paper.be.md`

P1. Lines 87–88 — «дакумент можа аднавіцца лепш, чым абяцана» — the English says "may
recover more than it promises"; «аднавіцца лепш» is vague and the document does not
"recover itself". — «і з дакумента можа ўдацца аднавіць больш, чым абяцана» — kind 1
(minor).

Verdict: **fit to publish as is** (P1 optional).

## `docs/read-from-paper.be.md`

R1. Lines 40–41 — «колам мышы яго можна павялічыць» — the wheel zooms both in and out. —
«колам мышы можна змяняць маштаб» — kind 1 (minor).

Verdict: **fit to publish as is** (R1 optional).

## `docs/development.be.md`

V1. Line 53 — «Пасля push у `master`» — an English word left bare in running prose and
not in code font. — «Пасля адпраўкі (push) у `master`, якая змяняе `docs/`, …» —
kind 7.

V2. Line 43 — «Працоўны працэс выпуску» — a calque of "release workflow" that reads
oddly. — «Сцэнарый выпуску (release workflow)» — kind 4.

Verdict: **fit to publish as is** (V1 and V2 optional).

## `docs/history.be.md`

H1. Line 10 — «захоўваў зыходны код даступным» — a calque of "kept the source available".
— «падтрымліваў зыходны код у адкрытым доступе» — kind 4.

Verdict: **fit to publish as is** (H1 optional).

## `docs/command-line.be.md`

No findings. Verdict: **fit to publish as is.**

---

## Kind 8: the ten longest window strings relative to English

All are short in absolute terms and none overflows a button or a form row. No shorter
wording exists without loss, so no change is proposed.

| Ratio | Key | English | Belarusian |
|---|---|---|---|
| 2.50 | gui.button.ok | OK | Добра |
| 2.33 | gui.dots.big | Big | Вялікія |
| 2.25 | gui.health.good | Good | У парадку |
| 2.00 | gui.button.save | Save | Захаваць |
| 1.80 | gui.PAGE_FIELD | Page: | Старонка: |
| 1.75 | gui.protection.high | High | Высокая |
| 1.58 | gui.CONFIRM_SAVE_TITLE | Save anyway? | Усё роўна захаваць? |
| 1.50 | gui.button.cancel | Cancel | Скасаваць |
| 1.50 | gui.WRITE_TAB | Put on paper | Запісаць на паперу |
| 1.50 | gui.READ_SLOWLY | Read by the slower reader for coarse scans | Прачытана павольным метадам для сканаў з нізкай раздзяляльнасцю (a detail line, not a button) |

## The translators' uncertain choices, judged

- **«самаапазнавальная старонка»** — Keep it. It is built regularly, like «апазнавальны
  знак» and «самаабслугоўванне», and the double «аа» is the correct spelling. It shares
  its root with «апазнаць» in the window, and it is understandable at first sight. No
  better single word exists.
- **«Аднаўленне магчымае»** — Keep it. Rejecting «аднаўляльны» ("renewable") was right.
  The full form avoids «магчыма» meaning "maybe". The already-repaired form reads a
  little oddly, but only because the English uses one label for both states.
- **«пазнака» / «надпіс»** — Good. («Цэтлік», which Belarusian Firefox uses for
  bookmark tags, would also work, but «пазнака» is clearer here.) Banning «пазначыць» is
  harmless; I found no place where it was missed.
- **«Добра»** for OK — Correct; it matches Belarusian Firefox and GNOME.
- **«праграма з акном»** — Acceptable for this audience and used the same way on every
  page. «Настольная праграма» would be a calque, and «праграма з графічным інтэрфейсам»
  is too long for a table header. Add it to the glossary.
- **macOS names** — Do not follow the rule. See N1.
- **Requirement words in the format page** — Consistent and correct (see the note under
  format). «Правераны» versus «кантраляваць» is kept apart throughout. Valid,
  well-formed and acceptable are rendered one way each.
- **Paraphrase after the label-line formula (2.8)** — Keep it. The code block must stay
  English, and the paraphrase only restates it.
- **«раздрукоўка» added in 1.4** — Keep it. «сумяшчальная» needs a noun in Belarusian,
  and the addition does not change the meaning.
- **«праз --force»** — Correct Belarusian for "because of".

## Templates that still do not fit

None.

## Glossary terms to reconsider

None. Add one entry: "desktop application" — «праграма з акном» (already used on six
pages; no other change needed).
