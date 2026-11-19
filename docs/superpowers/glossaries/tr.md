# Turkish glossary (`tr`)

Working paper for the Turkish translation of optar: the catalogue
`src/optar/locale/tr.toml` and the pages `docs/<page>.tr.md`. It follows
section 1 of `docs/superpowers/translation-brief.md`. The explanations are in
English; the terms are Turkish. Once a term is chosen here it is used the same
way in the window, the command line and every page.

## General conventions

- **Address.** Polite plural «siz», implied by the verb ending, as Turkish
  software does: «Sayfayı yeniden tarayın», «başka bir ad seçin». Never the
  familiar «sen» form in a sentence addressed to the user.
- **Buttons, menu entries and dialog titles** use the bare imperative stem, as
  in Windows, macOS and GNOME in Turkish: «Kaydet», «Tarama ekle…»,
  «Taramayı değiştir…», «Sayfaya ata», «PDF'yi kaydet». **Instructions** in
  messages and pages use the polite imperative in «-in / -ın / -un / -ün»:
  «Gerçek boyutunda yazdırın», «… dpi ile tarayın». **Questions** to the user
  use the passive with «mi»: «Yine de kaydedilsin mi?», «Bitene kadar
  beklensin mi?».
- **Progress and steps** use the passive present continuous without a
  subject: «Dosya açılıyor», «Sayfa tanınıyor», «İşleniyor…».
- **Status words** in rows and the bottom bar are adjectives or short
  participles: «Sağlam», «Hasarlı», «Eksik», «Okunamıyor», «Onarıldı».
- **Command-line help** (argparse) uses the bare imperative, the convention of
  Turkish command-line tools: «bu yardım iletisini gösterip çık», «… deneme»
  (do not try).
- **Typography.** Double quotes “…” (Turkish typography; never «» or „“ in Turkish text; the guillemets in this glossary only mark examples).
  Dash in prose «—» with spaces, used sparingly. Page ranges with an en dash
  and no spaces: «2–4», as `gui.list.range` writes it. Ellipsis «…» as one
  character, as in English. Circumflex where TDK writes it: «kâğıt», «hâlâ», «dâhil». Compounds spelt as TDK spells them: «tam sayı», «on iki yüzlü».
- **Numbers.** Thousands separator «.» (`[format].group`), decimal comma «,»
  (`[format].decimal`): «199.773», «0,36». Outside code blocks, in prose and
  table cells alike, numbers are written this way; inside code blocks,
  commands, anything a user types and the whole of `format.tr.md` they stay
  exactly as in English. **The percent sign stands before the number**, as
  Turkish writes it: «%100», «%57», «%0,1». The catalogue does this in
  `cli.ACTUAL_SIZE`, `gui.slow.share` («%{share}»), `gui.slow.share_small`
  and `gui.margin.*` («%{percent}»). A count of something is written «3/12»
  (done/total) in the bar and the detail panel.
- **optar** stays lower-case, also at the start of a sentence. It takes no
  suffix in the catalogue; in pages, where unavoidable, the apostrophe form is
  «optar'ı», «optar'la», «optar'ın», but prefer «optar programı» + suffix on
  «program».
- **«Sayfa»** is a sheet of paper carrying dots. A page of this website is
  «bölüm», never «sayfa» («“Sayfa kendini nasıl tanıtır” bölümüne bakın»).
  The site's home page is «Giriş».

## Suffixes on inserted values: the device used

Turkish case and possessive suffixes follow vowel harmony and the final sound
of the word they attach to, so a suffix cannot be written after a placeholder
whose value is not known (a file name, a number, an option name, a list). No
placeholder in `tr.toml` carries a suffix. The devices, in order of
preference:

1. **Colon before the value.** «Oluşturuldu: {name}», «eksik sayfalar:
   {list}», «Dosya kaydedilemedi: {message}», «düzeltilen: {count}».
2. **The value in the nominative, as subject or before a noun that takes the
   suffix.** «{path} okunamıyor», «{path} görüntüsü okunamıyor», «{missing}
   dosyası eksik», «{format} sayfa biçimi», «{limit} sınırını aşıyor»,
   «{size} baytlık bir dosya». A numeral before a noun needs no suffix at all
   («{n} sayfa», «{total} sayfadan»).
3. **«adlı» after a file name.** «{name} adlı tarama {page}. sayfa için
   kullanılmadı». «adlı» (named) is invariant and lets «tarama» take every
   suffix.
4. **Ordinal dot after a single page number.** «{page}. sayfa»,
   «{first}–{last}. sayfalar»: Turkish reads «3. sayfa» as «üçüncü sayfa», and
   the suffixes go on «sayfa» («{page}. sayfayı», «{page}. sayfanın»). Used only
   where the value is exactly one number (`single` forms, `{page}`, runs).
5. **Parentheses for a list of pages.** A list can end in «12 sayfa daha»
   (`gui.list.more`), so it cannot take an ordinal dot: «eksik sayfalar (2–4,
   7 ve 9) diğerlerinden yeniden oluşturulabilir», «sayfaları ({pages})
   ekleyin».
6. **Slash for "N of T".** «Sayfa {page}/{total}», «{done}/{n} tarama
   okundu», «{good}/{n} sayfa sağlam».
7. **Invariant postpositions written apart.** «ile», «için», «gibi», «kadar»
   do not harmonise when written as separate words: «{options} ile birlikte»,
   «{dpi} dpi ile tarayın», «Standart için 600».
8. **Percentages** with «oranında»: «%{percent} oranında kullanıldı».

Page translators: follow the same devices when quoting a template with a
concrete value; with a concrete value you may write the correct suffix with an
apostrophe («optar'ın», «PDF'yi», «3'ü»), but never invent a suffix in the
catalogue.

## Terms

### The brief's required terms

| English | Turkish | Notes |
|---|---|---|
| dot | nokta | "Data dot" «veri noktası», "printer dot" «yazıcı noktası». Not «piksel»: pixels are separate. |
| dot size | nokta boyutu | Field «Nokta boyutu:». |
| block | blok | One error-correction unit. «12 blok». In the spec the "block of device dots" (5.1) is «yazıcı noktalarından kare», to keep «blok» for the window's meaning. |
| protection | koruma | Field «Koruma:», levels «Yok / Standart / Yüksek». In prose «koruma eklenmiş çıktı», «korumasız». **Avoid the adjective «korumalı»**: in Turkish software («Korumalı Görünüm», «parola korumalı») it means locked or sandboxed. Rejected: «yedeklilik» (technical), «artıklık» (means waste in everyday Turkish). |
| fingerprint | parmak izi | The established Turkish term for a key or certificate fingerprint («SSH anahtar parmak izi»). Takes the compound suffix: «parmak iziyle», «parmak izini». Rejected: «özet» (names the hash method; also means "summary"), «sağlama toplamı» (a checksum, a weaker claim). |
| tag | künye | The bracketed `[SIZE:FINGERPRINT:CC]` at the start of a label. «Künye» is an identification record (a soldier's dog tag, a book's imprint), which is exactly its role. «künyesiz» / «künye yok» (untagged). Rejected: «etiket» (taken by "label"), «damga» (a stamp, suggests a seal of approval). |
| label | etiket | The line printed at the bottom of every page. "Label band" «etiket alanı», "label strip" «etiket şeridi» (spec). Rejected: «alt yazı» (subtitle, caption), «başlık» (header, clashes with the spec's header). |
| spare | yedek tarama | Row «Yedek», detail tag «yedek». «Yedek» is the everyday word for a spare (yedek lastik) and does not suggest a mistake. |
| scan (noun) | tarama | Plural «taramalar». The usual word in Turkish scanning software. Rejected: «taranmış görüntü» (too long for buttons and rows). |
| scan (verb) | taramak | "Rescan" «yeniden taramak». "Scan at 600 dpi" «600 dpi ile tarayın». |
| printout | çıktı | The pages as printed, the physical set. Kept apart from «belge». «Çıktı» also means "output" in the command-line help («çıktı dosyası», «çıktı türü»); both are the established words and the context keeps them apart. |
| document | belge | A set of pages that carries one file. |
| page | sayfa | See the convention on «bölüm». Rejected: «yaprak» (a leaf has two sides). |
| part (of a file, of a page, of a tag) | kısım | «dosyanın her kısmından», «sayfanın her kısmında», tag table header «Kısım». «Bölüm» is kept for a page of the site and a numbered section of the format page. |
| slower reader | yavaş okuma yöntemi (short: yavaş yöntem) | "The ordinary reader" «normal okuma yöntemi» / «normal yöntem». First mention on a page: «ikinci, daha yavaş okuma yöntemi». "Read by the slower reader" «yavaş yöntemle okundu». "Slower reader for coarse scans" «düşük çözünürlüklü taramalar için yavaş yöntem». Rejected: «okuyucu» (a device, as in «kart okuyucu»), «yavaş mod» (a mode is chosen by the user; this runs by itself). |
| self-identifying page | kendini tanıtan sayfa | Plural «kendini tanıtan sayfalar». Shares the root «tanı-» with "identify" («tanınamadı», «Sayfa tanınıyor»). First mention on a page may add «(hangi belgeye ait olduğunu ve kaçıncı sayfa olduğunu kendisi söyleyen sayfa)». |
| verified | doğrulandı (doğrulanmış) | "File verified" «dosya doğrulandı». The root **«doğrula-» is reserved** for verified / verification: "did not verify" «doğrulamadan geçmedi», "cannot be verified" «doğrulanamaz», "after verification" «doğrulamadan sonra». "It cannot be confirmed that…" (caution) is «teyit edilemez», never «doğrulanamaz». Checking against the fingerprint is «parmak iziyle karşılaştırma». Rejected: «onaylandı» (approved, vaguer), «garanti» (stronger). |
| repaired | onarıldı (onarmak, onarım) | Protection or page error correction fixed damaged data: «6.912 bayt onarıldı», «Onarıldı · 3». A *missing* page is not «onarıldı» but «yeniden oluşturuldu» (rebuilt): «diğerlerinden yeniden oluşturuldu». |
| lost | kayıp; kaybolmak | Blocks: «kayıp: 3», «Hasarlı · 3 kayıp». A whole page: «24 sayfadan 2 sayfa kaybolsa da kurtarılabilir». Distinct from "missing". |
| damaged | hasarlı; hasar | Page state «Hasarlı». "Damage" «hasar». |
| missing | eksik | A page of which no scan has been added. State «Eksik». Not «kayıp»: the paper may exist, only the scan is missing. |
| incomplete (a saved file) | tam olmayan; «tam olmayacak» | «Kaydedilen dosya tam olmayacak: …». Keeps «eksik» for missing pages. |

### The window's vocabulary

| English | Turkish | Notes |
|---|---|---|
| good (page state) | sağlam | Invariant adjective: «Sağlam», «4/6 sayfa sağlam». Rejected: «iyi» (sounds like a grade). |
| not readable, unreadable | okunamıyor; okunamadı | State «Okunamıyor»; "could not be read" «okunamadı». |
| recoverable | kurtarılabilir | Used for both states labelled "Recoverable", as English does. |
| recovered | kurtarıldı; kurtarılan dosya | «Dosya kurtarıldı ve doğrulandı». "What was recovered" «kurtarılabilen kısım». |
| rebuild (a lost page) | yeniden oluşturmak | |
| corrected (dots, symbols, bits) | düzeltildi; düzeltilen | Kept apart from "repaired": «265.112 nokta düzeltildi · 6.912 bayt belgenin korumasıyla onarıldı». "Error correction" «hata düzeltme». |
| uncorrectable | düzeltilemeyen | |
| repair capacity | onarım kapasitesi | "The worst spot" «en kötü nokta». "Used 18 of 32" «18/32». |
| margin (wide, moderate, close to the limit) | pay (geniş bir pay, orta bir pay, sınıra yakın) | |
| check the fingerprint, checking | parmak iziyle karşılaştırmak, karşılaştırılıyor | Keeps «doğrula-» free. |
| matches / does not match | eşleşiyor / eşleşmiyor | |
| identify, identified | tanımak, tanındı / tanınamadı | |
| assign to a page | sayfaya atamak | Button «Sayfaya ata…». |
| start a document by hand, put together by hand | belgeyi elle oluşturmak; elle oluşturuldu | One verb for the button and the caution. |
| replace (scan) | değiştirmek | «Taramayı değiştir…». |
| use this scan | bu taramayı kullan | |
| switch to this document | bu belgeye geç | |
| add scans | tarama ekle | Bare noun after the verb, as Turkish buttons do («Dosya ekle»). |
| remove | kaldır | Removes from the list; «Sil» would delete the file. |
| being read, waiting, working | okunuyor, sırada, işleniyor | |
| step (of reading) | adım | Steps: «Dosya açılıyor», «Sayfa aranıyor», «Sayfa tanınıyor», «Veriler okunuyor», «Yavaş yöntem: örnekleme», «Yavaş yöntem: geçiş 4/5». |
| pass | geçiş | |
| coarse scan, too coarse | düşük çözünürlüklü tarama; çözünürlüğü çok düşük | Turkish speaks of resolution. Rejected: «kaba tarama» (calque). |
| resolution | çözünürlük | dpi stays «dpi». |
| put on paper | kâğıda yazmak | Tab «Kâğıda yaz». |
| read from paper | kâğıttan okumak | Tab «Kâğıttan oku». |
| printed name, prints as | yazdırılacak ad | Field «Yazdırılacak ad:». |
| name | ad | «Ad:», «(adsız)». |
| compatible | uyumlu | Checkbox «optar 0.2 ve özgün optar ile uyumlu». |
| original optar, the C program | özgün optar; C ile yazılmış özgün program | |
| dot size names: Standard, Medium, Big, Large, Extra large | Standart, Orta, Büyük, İri, Çok iri | Capitalised as a selector entry or at the start; lower-case in running text («standart noktalarla», «iri noktalar»). |
| protection levels: None, Standard, High | Yok, Standart, Yüksek | In prose «standart koruma», «yüksek koruma», «korumasız». |
| paper names | A4, US Letter | Kept. In prose «A4 kâğıt», «Letter kâğıt» (no apostrophe suffix on «Letter», whose Turkish pronunciation is uncertain). The paper chosen is «kâğıt boyutu» («Çıktının kâğıt boyutunu … girin»). |
| actual size, fit to page | gerçek boyut (%100), “Sayfaya sığdır” | The latter as the Windows print dialog in Turkish names it. |
| grayscale, colour, black and white | gri tonlamalı, renkli, siyah beyaz | |
| bottom bar | alttaki çubuk (durum çubuğu) | |
| progress bar | ilerleme çubuğu | |
| row, list of scans | satır, tarama listesi | |
| preview, marked | önizleme, işaretlenmiş | |
| another printout | başka bir çıktı | |
| untagged, no tag | künyesiz, künye yok | |

### The command line's vocabulary

| English | Turkish | Notes |
|---|---|---|
| symbol | sembol | The code symbol. Label characters are «karakter». |
| codeword | kod sözcüğü | |
| byte | bayt | |
| encode / decode | kodlamak / kod çözmek | "Decode again" «kod çözmeyi yineleyin». Command names stay English. |
| option | seçenek | «--paper değeri», «--force seçeneği». |
| usage, positional arguments, options | kullanım, konumsal argümanlar, seçenekler | |
| exit status | çıkış kodu | |
| ignored | yok sayıldı | |
| protection level `{level}` | Koruma düzeyi {level} | The option value reads as a name: «Koruma düzeyi standard: …». |
| pixels (in errors) | piksel; «… piksellik» | «{width} x {height} piksellik sayfa». |
| option value quoted in help prose | 'standard', 'none' | In single quotes, so that `standard` does not read as a misspelling of «standart». |
| overwrite (a file) | üzerine yazmak | «dosyanın üzerine yazılırdı». Not «yerine geçmek» (substitute). |
| standard error (stderr) | standart hata çıkışı | Not «akış», which is the format's "stream". |
| commit (git) | işleme (commit) | «… işlemesindeki hâliyle» (format page), «işlemeye (commit) karşı» (development page). |

### Format specification terms (`format.md`)

| English | Turkish |
|---|---|
| page pixel, data pixel, scan pixel | sayfa pikseli, veri pikseli, tarama pikseli |
| integer | tam sayı |
| dodecahedron | on iki yüzlü |
| the specification (as "the document" in development) | belirtim; the format page calls itself «bu metin», the English original «İngilizce metin» |
| page format, format string | sayfa biçimi, biçim dizesi |
| layout | düzen |
| grid | ızgara |
| cross | artı işareti |
| border, frame | çerçeve |
| data area / data region | veri alanı / veri bölgesi |
| label band, label strip, font strip | etiket alanı, etiket şeridi, yazı tipi şeridi |
| character, glyph | karakter, glif |
| interleave / spread | serpiştirme / yayma |
| page code | sayfa kodu |
| Golay, Hamming, Reed-Solomon code | Golay kodu, (genişletilmiş) Hamming kodu, Reed-Solomon kodu |
| parity, parity bytes, parity level | eşlik, eşlik baytları, eşlik düzeyi |
| check (of a tag), check digits | denetim değeri, denetim basamakları |
| header | başlık |
| container, stream, payload | kapsayıcı, akış, yük |
| padding, padded with zeros | dolgu; sıfırlarla tamamlanır |
| erasure | silinti |
| valid / invalid | geçerli / geçersiz |
| untrusted | güvenilmez |
| normative, informative | bağlayıcı, bilgilendirici |
| test vectors | test vektörleri |
| encoder, decoder, reader | kodlayıcı, kod çözücü, okuyucu program |

## Strength of claims

- **Verified** — «doğrulandı», with the reserved root. Never softened
  («muhtemelen sağlam») and never strengthened («garanti edilir»).
- **Recoverable vs recovered** — «kurtarılabilir» says the pages read should
  be enough; «kurtarıldı», «yeniden oluşturuldu» only of what was done.
- **Promise** — «24 sayfadan 2 sayfa kaybolsa da kurtarılabilir» keeps the
  modal «-abilir» (can), not «dayanır» (withstands, stronger).
- **"May be damaged", "may contain wrong parts"** — «hasarlı olabilir»,
  «yanlış kısımlar içerebilir» (a part of the file is «kısım», never «bölüm»).
- **Warnings** stay firm: "was not saved" «kaydedilmedi» (the program chose
  not to), not «kaydedilemedi».

## Never translated

As in the Russian glossary: `optar`, `optar-gui`, `encode`, `decode`, every
option name and value (`--paper`, `none`, `standard`, `high`, `a4`, …),
metavariables (`INPUT`, `BASE`, `OUTPUT`, `STRING`, `LABEL`), file names and
extensions, environment variables, code and constants, header field names,
the tag parts `SIZE`, `FINGERPRINT`, `CC`, product and standard names, dpi,
version numbers.

## Plural forms

Turkish has one category, `other`, and a noun after a numeral stays singular:
«1 sayfa», «5 sayfa», «21 sayfa». So every plural table in `tr.toml` has only
`other`, and the `single` / `several` entries differ only in «sayfa» /
«sayfalar» and in the device (ordinal dot or parentheses, see above).

## Site navigation

| English | Turkish |
|---|---|
| Home | Giriş |
| Using optar | optar ile çalışma |
| Install | Kurulum |
| Put a file on paper | Dosyayı kâğıda yazma |
| Read it back | Dosyayı geri okuma |
| Scans that are too coarse | Çözünürlüğü çok düşük taramalar |
| Command line | Komut satırı |
| Reference | Başvuru |
| How a page identifies itself | Sayfa kendini nasıl tanıtır |
| What has and has not been shown | Neler gösterildi, neler gösterilmedi |
| Format specification | Biçim belirtimi |
| Project | Proje |
| Development | Geliştirme |
| History | Tarihçe |

- **site_description:** Lazer yazıcı ve tarayıcı ile dosyaları kâğıtta saklama
- **site_name:** optar (unchanged)
- **Language name** (`[language].name` and the switcher): Türkçe

## Interface strings the pages quote

Quote these exactly as `tr.toml` has them.

| English (as quoted in the pages) | Turkish |
|---|---|
| Put on paper (tab) | Kâğıda yaz |
| Read from paper (tab) | Kâğıttan oku |
| Prints as: | Yazdırılacak ad: |
| Create PDF… | PDF oluştur… |
| Compatible with optar 0.2 and the original optar | optar 0.2 ve özgün optar ile uyumlu |
| + Add scans… | + Tarama ekle… |
| Save file… | Dosyayı kaydet… |
| Remove | Kaldır |
| Being read | Okunuyor |
| Waiting / Opening the file / Finding the page / Identifying the page / Reading the data | Sırada / Dosya açılıyor / Sayfa aranıyor / Sayfa tanınıyor / Veriler okunuyor |
| Slower reader: sampling, pass 4 of 5 | Yavaş yöntem: örnekleme; Yavaş yöntem: geçiş 4/5 |
| Good / Repaired · N / Damaged · N lost / Not readable / Missing | Sağlam / Onarıldı · N / Hasarlı · N kayıp / Okunamıyor / Eksik |
| Read by the slower reader | Yavaş yöntemle okundu |
| File recovered and verified · N bytes | Dosya kurtarıldı ve doğrulandı · N bayt |
| Does not match the fingerprint on the paper | Kâğıttaki parmak iziyle eşleşmiyor |
| Recoverable: page 3 missing, can be repaired from the others | Kurtarılabilir: 3. sayfa eksik, diğerlerinden yeniden oluşturulabilir |
| Recoverable: page 3 missing, repaired from the others · matches the fingerprint | Kurtarılabilir: 3. sayfa eksik, diğerlerinden yeniden oluşturuldu · parmak iziyle eşleşiyor |
| Working… 3 of 6 scans read | İşleniyor… 3/6 tarama okundu |
| Checking the fingerprint… | Parmak iziyle karşılaştırılıyor… |
| All N pages read · cannot be verified (no tag) | N sayfanın tümü okundu · doğrulanamaz (künye yok) |
| 4 of 6 pages good · 1 damaged · 1 missing | 4/6 sayfa sağlam · 1 hasarlı · 1 eksik |
| the worst spot used 57% of its repair capacity (18 of 32): a moderate margin | en kötü noktada onarım kapasitesi %57 oranında kullanıldı (18/32): orta bir pay |
| Scanned at about 200 dpi, which is too coarse to read | Yaklaşık 200 dpi ile taranmış; bu çözünürlük okumak için çok düşük |
| can lose N page(s) of T | T sayfadan N sayfa kaybolsa da kurtarılabilir |
| Page 3 · Read by the slower reader · 265,112 dots corrected | Sayfa 3 · Yavaş yöntemle okundu · 265.112 nokta düzeltildi |
| · 6,912 bytes repaired by the document's protection | · 6.912 bayt belgenin korumasıyla onarıldı |
| Standard / Medium / Big / Large / Extra large (dots) | Standart / Orta / Büyük / İri / Çok iri |
| None / Standard / High (protection) | Yok / Standart / Yüksek |
| fit to page | “Sayfaya sığdır” |
