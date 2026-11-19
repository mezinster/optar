---
source_hash: f5551682033e226e7bf557d24edd97efecf26b2d
---

# შემუშავება { #development }

საწყისი კოდი მდებარეობს მისამართზე
[github.com/mezinster/optar](https://github.com/mezinster/optar).

## გამართვა და ტესტები { #setup-and-tests }

    python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
    .venv/bin/pytest -q
    .venv/bin/ruff check .

არცერთ ტესტს C კომპილატორი არ სჭირდება.

| ბრძანება | რას უშვებს |
|---|---|
| `.venv/bin/pytest -q` | ნაგულისხმევ ნაკრებს |
| `.venv/bin/pytest -q -m gs` | PDF შედეგის ტესტებს; საჭიროა Ghostscript |
| `.venv/bin/pytest -q -m slow` | ხანგრძლივ ტესტებს; ყველა ბირთვის გამოსაყენებლად დაამატეთ `-n auto` |
| `.venv/bin/pytest -q -m slow tests/unit/test_claims.py` | სიმულირებული სკანების ტესტებს, რომლებსაც ეყრდნობა განყოფილება [„რა არის ნაჩვენები და რა — არა“](evidence.md) |
| `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui` | აპლიკაციის ტესტებს |

აპლიკაციის ტესტებს სჭირდება PySide6 და pytest-qt
(`pip install -e '.[dev,gui-dev]'`); მათ გარეშე ეს ტესტები გამოიტოვება.

## რა განსაზღვრავს ფორმატს { #what-defines-the-format }

გვერდის ფორმატს განსაზღვრავს [ფორმატის სპეციფიკაცია](format.md) და
შესაბამისობის ვექტორები `tests/vectors`-ში. `tests/unit/test_spec.py`
სპეციფიკაციის ცხრილებსა და მაგალითებს კოდს ადარებს, ამიტომ დოკუმენტი და კოდი
ერთად იცვლება.

## ერთფაილიანი პროგრამების აგება { #building-the-one-file-programs }

    .venv/bin/pyinstaller --onefile --name optar --collect-data optar packaging/entry.py
    python packaging/smoke.py dist/optar

აპლიკაცია:

    .venv/bin/pyinstaller --onefile --name optar-gui --collect-data optar packaging/gui_entry.py

როცა ვერსიის git-ტეგი იტვირთება, გამოშვების სამუშაო პროცესი (release
workflow) ორივე პროგრამას Linux-ისთვის, macOS-ისა და Windows-ისთვის აგებს.

## ეს საიტი { #this-site }

განყოფილებები `docs/` საქაღალდის Markdown ფაილებია, რომლებსაც MkDocs აგებს:

    .venv/bin/pip install -e '.[docs]'
    .venv/bin/mkdocs serve

`master` ტოტში ატვირთული ცვლილება (push), რომელიც `docs/`-ს ეხება, საიტს
აქვეყნებს.

## თარგმანები { #translations }

აპლიკაცია და ეს საიტი ხელმისაწვდომია ცხრა ენაზე: `en`, `ru`, `uk`, `be`,
`pl`, `ka`, `tr`, `it`, `es`. წყარო ინგლისურია.

**პროგრამების ტექსტი** მოცემულია ფაილებში `src/optar/locale/<code>.toml`,
თითო ფაილი თითო ენისთვის, ერთნაირი გასაღებებით. სტრიქონის დასამატებლად ან
შესაცვლელად შეცვალეთ `en.toml` და ყველა სხვა კატალოგი იმავე pull request-ში;
მრავლობითი ფორმის ჩანაწერს მისი ენის კატეგორიები აქვს
(`optar.i18n.categories(code)`). `tests/unit/test_catalogues.py` აკონტროლებს,
რომ კატალოგები ერთმანეთს შეესაბამება. ბრძანების სტრიქონის პროგრამის სხვა ენაზე
სანახავად დააყენეთ `OPTAR_LANG`, მაგალითად `OPTAR_LANG=ru optar --help`;
აპლიკაციას ენის მენიუ აქვს.

**საიტის განყოფილებები** არის ფაილები `docs/<page>.<code>.md` ინგლისური
`docs/<page>.md`-ის გვერდით. ნათარგმნ განყოფილებას front matter-ში აქვს
`source_hash`, ყოველ სათაურზე — ინგლისური id, ხოლო კოდის ბლოკები ინგლისურის
იდენტურია. იმის სანახავად, რომელი განყოფილებები ჩამორჩება, გაუშვით
`python tools/translation_status.py`. მოძველებული განყოფილების განსაახლებლად
წაიკითხეთ, რა შეიცვალა ინგლისურ განყოფილებაში (`git diff` მისი
`source_hash`-ის კომიტთან), შესაბამისად შეცვალეთ თარგმანი, შემდეგ
`source_hash`-ს მიანიჭეთ `git hash-object docs/<page>.md`-ის მნიშვნელობა.
დანარჩენს `tests/unit/test_doc_translations.py` აკონტროლებს. მთარგმნელების
წესები მოცემულია ფაილში `docs/superpowers/translation-brief.md`.

**რას აკეთებს მათთან საიტი** — დადგენილია დროებითი რუსული განყოფილებითა და
ენის ჩანაწერით (შემდეგ ისევ წაიშალა):

- განყოფილება, რომელსაც თარგმანი არ აქვს, `/ru/`-ში ინგლისურად ჩანს, მის
  გარშემო კი ნავიგაცია ნათარგმნია (`fallback_to_default`).
- ენის გადამრთველი საიტის ზედა ზოლში ჩნდება, როგორც კი მეორე ენა ემატება.
- ძიება მთელი საიტისთვის ერთ ინდექსს იყენებს. ის ყველა ენის შედეგებს ერთად
  აჩვენებს; უთარგმნელი განყოფილება ინდექსირდება ერთხელ, თავისი ინგლისური
  მისამართით, და არა კიდევ ერთხელ `/ru/`-ში.
