---
source_hash: fc438b9b7896988d42b22d54829293c774aa20c2
---

# Komut satırı { #command-line }

`optar` komutu bir dosyayı sayfalara kodlar ve taramaların kodunu çözerek
dosyayı geri verir. C derleyicisi, libpng ya da ImageMagick gerektirmez.

    optar encode INPUT [-o BASE] [--paper a4|letter] [--to pdf|png|pgm] [--label TEXT] [--no-tag]
                 [--dots standard|medium|big|large|xlarge] [--protect none|standard|high]
                 [--compatible] [--format STRING]
    optar decode BASE [-o OUTPUT] [--paper a4|letter] [--format STRING] [--debug-images] [--force]
                 [--no-slow-reader]
    optar --version

## encode { #encode }

`encode` varsayılan olarak `BASE.pdf` dosyasını yazar (`BASE` verilmezse
`optar_out` olur); `--to` ile ise `BASE_0001.png` (ya da `.pgm`),
`BASE_0002.png`, ... sayfalarını yazar.

| Verdiğiniz | Aldığınız |
|---|---|
| ne `--dots` ne de `--protect`, ya da `--compatible` | 0.2.0 ile C aracının okuyabildiği bir çıktı: standart noktalar, koruma yok |
| yalnızca `--dots X` | bu nokta boyutu, standart korumayla |
| yalnızca `--protect LEVEL` | standart noktalar, bu korumayla |
| `--protect none` | koruma yok |

Son üçünden herhangi biri kendini tanıtan sayfalar üretir; bunları okumak
için optar 0.3 ya da daha yeni bir sürüm gerekir. Örneğin:

    optar encode photo.jpg -o photo --dots large --protect high

Nokta boyutları ve koruma düzeyleri
[Dosyayı kâğıda yazma](put-on-paper.md#dot-size) bölümünde açıklanmıştır.

Uyumlu bir çıktının her sayfasında bir [künye](identification.md#the-tag)
bulunur; künyeyi çıkarmak için `--no-tag` ekleyin.

`--paper` seçeneğinin varsayılan değeri A4'tür.

## decode { #decode }

`decode`, `BASE_0001.png`, `BASE_0002.png`, ... dosyalarını okur ve
verileri `-o OUTPUT` ile verilen dosyaya ya da standart çıktıya (stdout)
yazar. Yalnızca bu adlara sahip dosyaları okur.

Ne yapacağı çıktıya bağlıdır. Bunu ilk üç taramaya bakarak belirler:
bunlardan hiçbiri kendini tanıtan sayfa olarak tanınamazsa tarama kümesini
0.2.0 ya da daha önceki bir sürümün çıktısı sayar.

### Kendini tanıtan sayfalar { #self-identifying-pages }

`decode`, taramaların ne olduğunu taramaların kendisinden öğrenir.

- Taramaları herhangi bir sırada ve herhangi bir yönde alır.
- Okuyamadığı bir tarama eksik sayfa sayılır.
- Normal okuma yönteminin tanıyamadığı bir tarama, `--no-slow-reader`
  vermediğiniz sürece önce [yavaş okuma yöntemine](slower-reader.md)
  verilir.
- Verileri onarır, gerçek boyutuna keser ve parmak iziyle karşılaştırır.
- Dosyayı yalnızca parmak izi eşleşirse yazar; ancak `--force` verirseniz,
  doğrulamadan geçmese bile kurtarılanı kaydeder. `--force` ile bile,
  sayfaların yarısından azı okunduysa hiçbir şey kaydedilmez.

### 0.2.0 ya da daha önceki sürümlerin çıktıları { #printouts-from-020-or-earlier }

- `--paper`, kodlamada kullanılanla aynı olmalıdır.
- Sayfa dik durmalıdır (dikey yönde, etiket altta). Yatay taramalar burada
  desteklenmez; bu, C kod çözücüsünden kalmadır. Masaüstü uygulaması her
  çıktıda her yönü kabul eder.
- `decode` çıktıyı künyedeki boyuta kesmez ve parmak iziyle karşılaştırmaz:
  çıktı her zaman sıfırlarla tam bir sayfaya tamamlanır. Masaüstü uygulaması
  ikisini de yapar. Verileriniz buna duyarlıysa onları tar ile paketleyin.
- `--force` hiçbir şeyi değiştirmez ve `decode` bunu söyler.

## Çıkış kodu { #exit-status }

| Kod | Anlamı |
|---|---|
| 0 | Başarılı. Kendini tanıtan sayfalarda: dosya doğrulandı. |
| 1 | Verilerin kodu çözüldü ama düzeltilemiyor, ya da sayfa numaralarında boşluk var, ya da (kendini tanıtan sayfalarda) dosya doğrulamadan geçmedi. |
| 2 | Kullanım ya da girdi hatası. |

## Hata düzelten kod { #the-error-correcting-code }

Varsayılan, Golay 24/12 kodudur. 2 ile 5 arası derecelerdeki Hamming
kodları da desteklenir; bunlar `--format` ile (biçim dizesinin altıncı
alanı) seçilir. Biçim dizesini [biçim belirtimi](format.md) tanımlar.
