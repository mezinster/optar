---
source_hash: f5551682033e226e7bf557d24edd97efecf26b2d
---

# Geliştirme { #development }

Kaynak kod [github.com/mezinster/optar](https://github.com/mezinster/optar)
adresindedir.

## Kurulum ve testler { #setup-and-tests }

    python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
    .venv/bin/pytest -q
    .venv/bin/ruff check .

Hiçbir test C derleyicisi gerektirmez.

| Komut | Ne çalıştırır |
|---|---|
| `.venv/bin/pytest -q` | varsayılan test takımı |
| `.venv/bin/pytest -q -m gs` | PDF çıktısının denetimleri; Ghostscript gerektirir |
| `.venv/bin/pytest -q -m slow` | uzun testler; tüm çekirdekleri kullanmak için `-n auto` ekleyin |
| `.venv/bin/pytest -q -m slow tests/unit/test_claims.py` | [Neler gösterildi, neler gösterilmedi](evidence.md) bölümünün dayandığı simüle edilmiş tarama testleri |
| `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui` | uygulamanın testleri |

Uygulamanın testleri PySide6 ve pytest-qt gerektirir
(`pip install -e '.[dev,gui-dev]'`); bunlar yoksa testler atlanır.

## Biçimi ne tanımlar { #what-defines-the-format }

Sayfa biçimini [biçim belirtimi](format.md) ve `tests/vectors` içindeki
uygunluk vektörleri tanımlar. `tests/unit/test_spec.py` belirtimdeki
tabloları ve örnekleri kodla karşılaştırır; bu yüzden belirtim ve kod birlikte
değiştirilir.

## Tek dosyalık programları derleme { #building-the-one-file-programs }

    .venv/bin/pyinstaller --onefile --name optar --collect-data optar packaging/entry.py
    python packaging/smoke.py dist/optar

Uygulama:

    .venv/bin/pyinstaller --onefile --name optar-gui --collect-data optar packaging/gui_entry.py

Bir sürüm için git etiketi (tag) gönderildiğinde, sürüm iş akışı ikisini de
Linux, macOS ve Windows için derler.

## Bu site { #this-site }

Bölümler, `docs/` içindeki Markdown dosyalarıdır ve MkDocs ile derlenir:

    .venv/bin/pip install -e '.[docs]'
    .venv/bin/mkdocs serve

`master` dalına gönderilen (push) ve `docs/` içeriğini değiştiren bir
değişiklik siteyi yayımlar.

## Çeviriler { #translations }

Uygulama ve bu site dokuz dilde kullanılabilir: `en`, `ru`, `uk`, `be`,
`pl`, `ka`, `tr`, `it`, `es`. Kaynak İngilizcedir.

**Programların metinleri** `src/optar/locale/<code>.toml` dosyalarındadır:
her dil için aynı anahtarlara sahip bir dosya. Bir metni eklemek ya da
değiştirmek için `en.toml` dosyasını ve diğer tüm katalogları aynı çekme
isteğinde (pull request) düzenleyin; çoğul bir girdi kendi dilinin
kategorilerine sahiptir (`optar.i18n.categories(code)`).
`tests/unit/test_catalogues.py` katalogların birbiriyle uyumlu olduğunu
denetler. Komut satırı programını başka bir dilde görmek için `OPTAR_LANG`
değişkenini ayarlayın, örneğin `OPTAR_LANG=ru optar --help`; uygulamanın bir
dil menüsü vardır.

**Sitenin bölümleri**, İngilizce `docs/<page>.md` dosyalarının yanındaki
`docs/<page>.<code>.md` dosyalarıdır. Çevrilmiş bir bölümün ön bilgisinde
(front matter) `source_hash` bulunur, her başlıkta İngilizce kimlik yer alır
ve kod blokları İngilizcedekiyle aynıdır. Hangi bölümlerin geride kaldığını
görmek için `python tools/translation_status.py` komutunu çalıştırın.
Eskimiş bir bölümü güncellemek için İngilizce bölümde neyin değiştiğini
okuyun (`source_hash` değerindeki işlemeye (commit) karşı `git diff`), çeviriyi buna
göre değiştirin, ardından `source_hash` değerini
`git hash-object docs/<page>.md` çıktısıyla değiştirin. Gerisini
`tests/unit/test_doc_translations.py` denetler. Çevirmenler için kurallar
`docs/superpowers/translation-brief.md` dosyasındadır.

**Sitenin bunlarla ne yaptığı**, geçici bir Rusça bölüm ve dil girdisiyle
(sonra yeniden kaldırıldı) bulundu:

- Çevirisi olmayan bir bölüm `/ru/` altında İngilizce görünür; çevresinde
  çevrilmiş gezinme menüsü bulunur (`fallback_to_default`).
- Dil değiştirici, ikinci bir dil olduğunda üst bilgide görünür.
- Arama, tüm site için tek bir dizindir. Her dilin sonuçlarını birlikte
  listeler; çevrilmemiş bir bölüm yalnızca bir kez, İngilizce adresiyle
  dizinlenir, `/ru/` altında bir daha dizinlenmez.
