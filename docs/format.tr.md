---
source_hash: 90182c569913da957ad8b2b3c51203f66726cc36
---

# optar biçimi { #the-optar-format }

Bu belirtimin bağlayıcı metni İngilizce metindir: [The optar format](https://mezinster.github.io/optar/format/). Biçimi İngilizce metin ile `tests/vectors` içindeki test vektörleri tanımlar. Bu çeviri bilgilendiricidir; İngilizce metinle çeliştiği yerde İngilizce metin geçerlidir.

optar, bir dosyayı kâğıt üzerinde siyah ve beyaz noktalardan oluşan sayfalar
olarak saklar. Bu metin, bir sayfanın ve bir belgenin (tek bir dosyayı taşıyan
sayfalar kümesi) ne olduğunu tanımlar; böylece sayfalarını bu projenin okuduğu
bir kodlayıcı ve bu projenin sayfalarını okuyan bir kod çözücü yazılabilir.

Metin sekiz kısımdan oluşur:

1. Terimler ve kurallar
2. Sayfa (sürüm 0)
3. Belge künyesi (0.2.0 çıktıları)
4. Kendini tanıtan belgeler (sürüm 1)
5. Yazdırma
6. Okuyucu program ne yapmalıdır
7. Referans kod çözücü (bilgilendirici)
8. Tarihçe

1 ile 6 arasındaki kısımlar bağlayıcıdır. Gereklilik kipi (“-malı/-meli”,
İngilizcedeki “must”) yalnızca bir sayfanın ya da bir belgenin ne olduğu için
ve 6. kısımda bir okuyucu programın okuduklarıyla ne yaptığı için kullanılır.
Bir okuyucu programın bir taramada sayfayı nasıl bulduğu ve nasıl örneklediği
biçimin parçası değildir; 7. kısım bu projenin bunu nasıl yaptığını anlatır.

Biçim, `tests/vectors` içindeki test vektörleriyle sabitlenmiştir. Her
bağlayıcı bölüm, onu sabitleyen dosyaları adlandıran bir “Vektörler:”
satırıyla biter; her dosyanın nasıl okunduğunu `tests/vectors/README.md`
açıklar. Önünde bir `spec-table` yorumu bulunan tablolar ve `example` olarak
işaretlenmiş çitli bloklar, `tests/unit/test_spec.py` tarafından kodla
karşılaştırılır.

## 1. Terimler ve kurallar { #1-terms-and-conventions }

### 1.1 Sayılar, bitler ve baytlar { #11-numbers-bits-and-bytes }

- Tüm tam sayılar, `0x` önekini taşımadıkça onluk tabanda yazılır.
- `a // b` aşağı yuvarlanan bölme, `a mod b` bu bölmenin kalanı, `ceil(a / b)`
  yukarı yuvarlanan bölmedir. Üçü de yalnızca negatif olmayan tam sayılarda
  kullanılır.
- Sayımlar ve indisler 0'dan başlar; bunun istisnaları sayfa numaraları ve
  2.5 bölümündeki on iki yüzlünün yüzleridir, bunlar 1'den başlar.
- Bir **bit dizisi** en anlamlı bit önce olmak üzere okunur: bir bayt
  dizisinin `n` numaralı biti, `n // 8` numaralı baytın `7 - (n mod 8)`
  numaralı bitidir; burada bir baytın 7 numaralı biti onun en anlamlı bitidir.
  Bir bit dizisinden alınan `w` bitlik bir sözcüğün en anlamlı biti, dizinin
  ilk bitidir.
- Başlıktaki (bölüm 4.2) çok baytlı tam sayılar big-endian düzenindedir: en
  anlamlı bayt önce gelir.
- SHA-256 ve CRC-32 bilinen olağan işlevlerdir. CRC-32, zlib, PNG ve
  Ethernet'teki CRC-32'dir: yansıtılmış polinom `0xEDB88320`, başlangıç değeri
  ve son XOR `0xFFFFFFFF`.

### 1.2 Pikseller ve renkler { #12-pixels-and-colours }

- Bir **sayfa**, **sayfa piksellerinden** oluşan dikdörtgen bir görüntüdür.
  Her sayfa pikseli ya siyah ya da beyazdır.
- Siyah bir veri pikseli 1 bitidir; beyaz bir veri pikseli 0 bitidir.
- 8 bitlik gri görüntü dosyalarında siyah bir pikselin değeri 0, beyaz bir
  pikselin değeri 255'tir. Bu belirtim başka bir görüntü kodlaması kullanmaz.
- Sayfa koordinatları `(x, y)` biçimindedir: `x` sütunları sol kenardan, `y`
  satırları üst kenardan sayar, ikisi de 0'dan başlayarak. Sayfa dik konumda,
  etiket alanı (bölüm 2.8) altta olacak şekilde yazdırılır ve okunur.
- **Veri alanı koordinatları** `(u, v)` çerçeveyi (bölüm 2.2) dışarıda bırakır:
  `u = x - border`, `v = y - border`.

### 1.3 Birimler { #13-units }

- Bir **punto** (pt) 1/72 inçtir.
- Bir **yazıcı noktası** 1/600 inçtir: düzenlerin tasarlandığı 600 dpi
  yazıcının bir aygıt noktası.
- Bir **veri noktası**, yazdırılmış hâliyle bir sayfa pikselidir. Tam sayıda
  yazıcı noktasından oluşan bir karedir (bölüm 5.1). **Standart** veri noktası
  3 yazıcı noktası genişliğindedir, yani 1/200 inç.

### 1.4 Belge türleri { #14-kinds-of-document }

Bir **akış**, bir belgenin sayfalarının veri piksellerinde taşıdığı bayt
dizisidir. Üç tür belge vardır; üçü de aynı sürüm 0 sayfalarından (kısım 2)
oluşur.

| Tür | Yazan | Akış | Etiketin taşıdığı |
|---|---|---|---|
| yalın | C programı, optar 0.1.0, `--no-tag` | dosya | yalnızca serbest metin |
| künyeli | optar 0.2.0 ve sonrası (“uyumlu”) | dosya | künye (kısım 3) |
| kendini tanıtan | optar 0.3.0 ve sonrası | kapsayıcı (kısım 4) | yalnızca serbest metin |

### 1.5 Sabitler { #15-constants }

Bu tablodaki adlar metin boyunca kullanılır.

<!-- spec-table: constants -->
| Ad | Değer | Anlamı |
|---|---|---|
| `PageFormat.version` | 0 | sayfa biçiminin sürümü |
| `PageFormat.cpitch` | 24 | artı işaretlerinin başlangıç noktaları arasındaki uzaklık, sayfa pikseli olarak |
| `PageFormat.chalf` | 3 | bir artı işaretinin kenarının yarısı, sayfa pikseli olarak |
| `PageFormat.fec_order` | 1 | sayfa kodu: 1 Golay kodu, 2 ile 5 arası Hamming kodlarıdır |
| `PageFormat.border` | 2 | çerçevenin kalınlığı, sayfa pikseli olarak |
| `PageFormat.text_height` | 24 | etiket alanının satır sayısı |
| `LABEL_HEIGHT` | 24 | çizilebilen tek etiket alanı yüksekliği |
| `TEXT_WIDTH` | 13 | bir etiket karakter hücresinin genişliği, etiket pikseli olarak |
| `FIRST_CHAR` | 32 | yazı tipi şeridinin ilk hücresinin karakter kodu |
| `GLYPH_CELLS` | 95 | yazı tipi şeridindeki karakter hücresi sayısı |
| `MAX_PAGES` | 9999 | bir belgenin en fazla sayfa sayısı |
| `FINGERPRINT_DIGITS` | 8 | künyedeki parmak izinin onaltılık basamak sayısı |
| `CHECK_DIGITS` | 2 | künyedeki denetim değerinin onaltılık basamak sayısı |
| `MAX_SIZE_DIGITS` | 12 | künyedeki boyutun en fazla onluk basamak sayısı |
| `HEADER_MAGIC` | "oPt1" | bir başlığın ilk dört baytı, ASCII olarak |
| `CONTAINER_VERSION` | 1 | bir başlığın sürüm baytı |
| `HEADER_SIZE` | 38 | bir başlık kopyasının bayt sayısı |
| `HEADER_COPIES` | 5 | her sayfadaki başlık kopyası sayısı |
| `FINGERPRINT_SIZE` | 16 | başlıktaki parmak izinin bayt sayısı |
| `CODEWORD` | 255 | bir Reed-Solomon kod sözcüğünün bayt sayısı |
| `SPREAD_STEP` | 7919 | yaymanın adımı (bölüm 4.6) |
| `NAME_MAX_BYTES` | 255 | saklanan dosya adının en fazla bayt sayısı |
| `PADDING_KEY` | "optar padding" | dolgu akışının anahtarı, ASCII olarak |
| `PADDING_BLOCK` | 32 | dolgu akışının bir parçasının bayt sayısı |
| `PROTECTED_MAX_BYTES` | 268435456 | eşlikli bir belgenin en fazla sayfa baytı |
| `PROMISE_NUM` | 3 | araçların verdiği sözün dayandığı eşlik oranının payı (4.9) |
| `PROMISE_DEN` | 4 | bu oranın paydası |
| `PRINTER_DPI` | 600 | inç başına yazıcı noktası |
| `PIXELS_PER_INCH` | 200 | inç başına standart veri noktası |
| `STANDARD_PRINTER_DOTS` | 3 | bir standart veri noktasının genişliğindeki yazıcı noktası sayısı |
| `POINTS_PER_INCH` | 72 | inç başına punto |
| `SCAN_PIXELS_PER_DOT` | 3 | önerilen tarama çözünürlüğünde veri noktası başına tarama pikseli |
| `MIN_MARGIN_PT` | 12 | yazdırılmış bir sayfanın çevresindeki en küçük kenar boşluğu, punto olarak |

## 2. Sayfa (sürüm 0) { #2-the-page-version-0 }

### 2.1 Sayfa biçimi ve biçim dizesi { #21-the-page-format-and-the-format-string }

Bir **sayfa biçimi**, negatif olmayan sekiz tam sayıdır:

| Alan | Ad | Anlamı | Olmalıdır |
|---|---|---|---|
| 1 | `version` | sayfa biçiminin sürümü | 0 |
| 2 | `xcrosses` | bir satırdaki artı işareti sayısı | en az 2 |
| 3 | `ycrosses` | bir sütundaki artı işareti sayısı | en az 2 |
| 4 | `cpitch` | artı işaretlerinin başlangıç noktaları arasındaki uzaklık | `2 * chalf` değerinden büyük |
| 5 | `chalf` | bir artı işaretinin kenarının yarısı | en az 1 |
| 6 | `fec_order` | sayfa kodu | 1 ile 5 arası |
| 7 | `border` | çerçevenin kalınlığı | en az 1 |
| 8 | `text_height` | etiket alanının satır sayısı | `LABEL_HEIGHT` |

**Biçim dizesi**, bu sekiz alanın bu sırayla, başında sıfır olmadan onluk
tabanda yazılıp `-` ile birleştirilmesidir. Her sayfa kendi biçim dizesini
etiketine yazar (bölüm 2.8). Bu projenin yazdırdığı sayfalar yalnızca
`xcrosses` ve `ycrosses` alanlarında farklıdır; öteki alanlar 1.5 bölümündeki
değerleri taşır. Projenin yazdırdığı on sayfa biçimi 5.2 bölümünde
listelenmiştir. Başka değerler de geçerli sayfalardır ve okuyucu programa
biçim dizesi verildiğinde okunur.

Aşağıdaki tüm boyutlar sayfa pikseli cinsindendir.

    data_width  = cpitch * (xcrosses - 1) + 2 * chalf
    data_height = cpitch * (ycrosses - 1) + 2 * chalf
    width       = 2 * border + data_width
    height      = 2 * border + data_height + text_height

```example
a4_data_width = 1542
a4_data_height = 2214
a4_width = 1546
a4_height = 2242
```

`a4_` önekli adlar, standart A4 sayfası olan `0-65-93-24-3-1-2-24` biçimi
içindir.

Vektörler: `tests/vectors/c/encoder_pages.json`.

### 2.2 Bir sayfanın parçaları { #22-the-parts-of-a-page }

Bir sayfa `width` sütun genişliğinde ve `height` satır yüksekliğindedir.
Yukarıdan aşağıya:

| `y` satırları | İçerik |
|---|---|
| `0` ile `border - 1` arası | çerçeve: siyah |
| `border` ile `border + data_height - 1` arası | `0` ile `border - 1` arasındaki sütunlar ve son `border` sütun: siyah. Bunların arasında: `data_width` sütunluk **veri alanı** |
| `border + data_height` ile `border + data_height + text_height - 1` arası | **etiket alanı**: tüm genişlik boyunca siyah; etiket `border` ile `border + data_width - 1` arasındaki sütunlara beyaz olarak çizilir (bölüm 2.8) |
| son `border` satır | çerçeve: siyah |

```example
a4_label_top_row = 2216
```

Veri alanının her pikseli ya bir artı işaretinin parçasıdır (bölüm 2.3) ya da
bir veri pikselidir (bölüm 2.4).

Vektörler: `tests/vectors/c/encoder_pages.json`.

### 2.3 Artı işaretleri { #23-crosses }

Veri alanı `xcrosses * ycrosses` adet **artı işareti** taşır; okuyucu program
veri piksellerini bulmak için bunları kullanır. `(i, j)` artı işareti
(`0 <= i < xcrosses`, `0 <= j < ycrosses`), kenarı `2 * chalf` piksel olan ve
sol üst pikseli, yani **başlangıç noktası**, veri alanı koordinatlarında
`(i * cpitch, j * cpitch)` konumunda bulunan karedir. Kenarı `chalf` piksel
olan dört çeyreği şöyledir:

| Çeyrek | Renk |
|---|---|
| sol üst | siyah |
| sağ üst | beyaz |
| sol alt | beyaz |
| sağ alt | siyah |

İlk artı işareti veri alanının sol üst köşesine, sonuncusu sağ alt köşesine
değer. Veri alanının bir `(u, v)` pikseli, ancak ve ancak
`u mod cpitch < 2 * chalf` ve `v mod cpitch < 2 * chalf` olduğunda bir artı
işaretinin parçasıdır.

```example
a4_last_cross_x = 1538
a4_last_cross_y = 2210
```

Bunlar, son artı işaretinin başlangıç noktasının `(x, y)` sayfa
koordinatlarıdır.

Vektörler: `tests/vectors/c/encoder_pages.json`.

### 2.4 Veri pikselleri ve sıraları { #24-data-pixels-and-their-order }

**Veri pikselleri**, veri alanının bir artı işaretine ait olmayan
pikselleridir. Okuma sırasıyla 0'dan başlayarak numaralanırlar: yukarıdan
başlayarak satır satır, bir satırın içinde soldan sağa. Bir veri pikselinin
numarası onun **kanal konumudur**; `total_bits` veri piksellerinin sayısıdır.

Veri alanının satırları `cpitch` periyoduyla yinelenir:

- artı işaretlerinden geçen `2 * chalf` satırlık bir **dar şerit**. Her satır,
  artı işaretlerinin arasındaki `gap_width` piksellik `xcrosses - 1` aralıkta
  `narrow_width` veri pikseli taşır;
- artı işareti içermeyen `gap_width` satırlık bir **geniş şerit**. Her satır
  `data_width` veri pikseli taşır.

Son periyotta yalnızca dar şerit vardır.

    gap_width     = cpitch - 2 * chalf
    narrow_width  = gap_width * (xcrosses - 1)
    narrow_pixels = 2 * chalf * narrow_width
    wide_pixels   = gap_width * data_width
    rep_pixels    = narrow_pixels + wide_pixels
    total_bits    = rep_pixels * (ycrosses - 1) + narrow_pixels

`n` kanal konumunun `(u, v)` veri alanı koordinatları şunlardır:

    rep = n // rep_pixels
    s   = n mod rep_pixels
    if s < narrow_pixels:                      (narrow strip)
        row = s // narrow_width
        r   = s mod narrow_width
        u   = 2 * chalf + (r // gap_width) * cpitch + r mod gap_width
        v   = rep * cpitch + row
    else:                                      (wide strip)
        s   = s - narrow_pixels
        u   = s mod data_width
        v   = rep * cpitch + 2 * chalf + s // data_width

Sayfa koordinatları `(u + border, v + border)` olur.

```example
a4_narrow_width = 1152
a4_narrow_pixels = 6912
a4_wide_pixels = 27756
a4_rep_pixels = 34668
a4_total_bits = 3196368
a4_xy_of_0 = 6, 0
a4_xy_of_17 = 23, 0
a4_xy_of_18 = 30, 0
a4_xy_of_1152 = 6, 1
a4_xy_of_6912 = 0, 6
a4_xy_of_8454 = 0, 7
a4_xy_of_34668 = 6, 24
a4_xy_of_3196367 = 1535, 2213
```

`a4_xy_of_N`, `N` kanal konumunun `u, v` değeridir.

Vektörler: `tests/vectors/c/bit_placement.json`.

### 2.5 Sayfa kodu { #25-the-page-code }

Bir sayfanın verisi `small` bitlik **sözcüklere** bölünür. Her sözcük, birkaç
biti yanlış okunduğunda düzeltilebilen `large` bitlik bir **sembole**
kodlanır. Kodu `fec_order` seçer:

| `fec_order` | Kod | `large` | `small` |
|---|---|---|---|
| 1 | Golay (24, 12) | 24 | 12 |
| 2 ile 5 arası | genişletilmiş Hamming | `2 ^ fec_order` | `large - 1 - fec_order` |

```example
code_bits_of_order_1 = 24, 12
code_bits_of_order_2 = 4, 1
code_bits_of_order_3 = 8, 4
code_bits_of_order_4 = 16, 11
code_bits_of_order_5 = 32, 26
```

Burada bir sembol `large` bitlik bir tam sayı olarak yazılır; bitlerin sayfaya
yerleştirildiği sıradaki **`b` numaralı biti** en anlamlı bitten itibaren
sayılır: 0 numaralı bit, değeri `2 ^ (large - 1)` olan bittir.

#### Golay kodu (24, 12) { #golay-24-12 }

12 bitlik `d` sözcüğünün sembolü `d * 4096 + p(d)` olur: üst 12 bitte sözcük,
onun altında 12 eşlik biti. Eşlik bitleri, yüzleri 1'den 12'ye kadar
numaralanmış bir on iki yüzlüden gelir. `f` yüzü, `d` sözcüğünün değeri
`2 ^ (f - 1)` olan bitini temsil eder. Her yüzün beş komşusu vardır:

<!-- spec-table: golay -->
| Yüz | Komşular | Maske |
|---|---|---|
| 1 | 2, 3, 4, 5, 6 | `0xfc1` |
| 2 | 1, 3, 6, 7, 8 | `0xf1a` |
| 3 | 1, 2, 4, 8, 9 | `0xe74` |
| 4 | 1, 3, 5, 9, 10 | `0xcea` |
| 5 | 1, 4, 6, 10, 11 | `0x9d6` |
| 6 | 1, 2, 5, 7, 11 | `0xbac` |
| 7 | 2, 6, 8, 11, 12 | `0x35d` |
| 8 | 2, 3, 7, 9, 12 | `0x6b9` |
| 9 | 3, 4, 8, 10, 12 | `0x573` |
| 10 | 4, 5, 9, 11, 12 | `0x2e7` |
| 11 | 5, 6, 7, 10, 12 | `0x58f` |
| 12 | 7, 8, 9, 10, 11 | `0x83f` |

`r` yüzünün maskesinde, `r` yüzünün komşusu olmayan her yüz için (`r` yüzünün
kendisi dâhil) bir 1 bulunur. `d AND mask` değerinde tek sayıda 1 biti varsa
`r` yüzünün eşlik biti 1'dir. Bu bit, `p(d)` değerinin `2 ^ (12 - r)` değerli
bitidir: 1. yüz en anlamlı eşlik bitini, 12. yüz en az anlamlı eşlik bitini
verir.

```example
golay_0x001 = 0x00183f
golay_0x800 = 0x800fc1
golay_0xabc = 0xabca13
golay_0xfff = 0xffffff
```

Kod doğrusaldır, 0 sözcüğünün sembolü 0'dır ve herhangi iki sembol en az 8
bitte birbirinden farklıdır. Bu nedenle en fazla 3 biti yanlış okunmuş bir
sembolün 3 bit uzaklığında tam olarak bir sembol bulunur: yazdırılmış olan.
Vektör dosyası 4096 sembolün tümünü sabitler.

#### Genişletilmiş Hamming kodu (`fec_order` 2 ile 5 arası) { #extended-hamming-fec_order-2-to-5 }

Sembolün bitlerini değerlerine göre numaralayın: `q` konumu, değeri `2 ^ q`
olan bittir, `0 <= q < large`.

1. Sözcüğün bitleri, en anlamlısı önce olmak üzere, ne 0 ne de ikinin kuvveti
   olan konumlara, `large - 1` konumundan aşağıya doğru yerleştirilir.
2. 0'dan `fec_order - 1` değerine kadar her `i` için `2 ^ i` konumu,
   numarasında `i` numaralı bit 1 olan konumlar çift sayıda 1 biti taşıyacak
   şekilde ayarlanır.
3. 0 konumu, sembolün tamamı çift sayıda 1 biti taşıyacak şekilde ayarlanır.

Böyle bir sembolde bir bit yanlışsa sembol düzeltilebilir, iki yanlış bit ise
fark edilir. `fec_order` 2 olduğunda sembol, sözcüğün tek bitinin dört kez
yinelenmesidir.

```example
hamming_2_of_1 = 1111
hamming_3_of_1011 = 10101010
hamming_4_of_10000000001 = 1000000100011000
hamming_5_of_1 = 00000000000000000000000000001111
```

Her satır, `of_` ifadesinden sonra ikili tabanda bir sözcüğü ve ikili tabanda
onun sembolünü, en anlamlı bit önce olmak üzere verir.

Vektörler: `tests/vectors/c/golay.json`, `tests/vectors/c/encoder_pages.json`.

### 2.6 Sayfadaki semboller { #26-symbols-on-the-page }

Bir sayfa için:

    symbols   = total_bits // large
    used_bits = symbols * large
    net_bits  = symbols * small

`net_bits`, bir sayfanın taşıdığı veri biti sayısıdır. Semboller, komşu
pikseller farklı sembollere ait olacak şekilde serpiştirilir:

    bit b of symbol s is at channel position  s + b * symbols

Bu, `0 <= s < symbols` ve `0 <= b < large` için geçerlidir. Böylece Golay
koduyla veri pikselleri, her biri `symbols` pikselden oluşan art arda 24 grup
oluşturur ve her sembolün her grupta, hepsinde aynı yerde olmak üzere, bir
pikseli vardır.

`used_bits` ve üzerindeki kanal konumlarında bulunan veri pikselleri hiçbir
sembole ait değildir ve beyazdır.

```example
a4_symbols = 133182
a4_used_bits = 3196368
a4_net_bits = 1598184
a4_position_of_symbol_1000_bit_5 = 666910
a4_xy_of_666910 = 1306, 462
a4_medium_total_bits = 1838484
a4_medium_symbols = 76603
a4_medium_unused_bits = 12
a4_medium_net_bits = 919236
hamming_2_net_bits = 799092
hamming_3_net_bits = 1598184
hamming_4_net_bits = 2197503
hamming_5_net_bits = 2597036
```

`a4_medium_` önekli adlar `0-50-70-24-3-1-2-24` biçimi içindir;
`hamming_N_net_bits` değerleri, `fec_order` değeri N olan A4 ızgarası
içindir.

Vektörler: `tests/vectors/c/bit_placement.json`, `tests/vectors/c/encoder_pages.json`.

### 2.7 Akıştan sayfalara { #27-from-a-stream-to-pages }

Akış `nbytes` bayt olsun ve bir bit dizisi olarak okunsun (bölüm 1.1).

    pages = ceil(8 * nbytes / net_bits)

`p` sayfası (1'den başlayarak) akışın `(p - 1) * net_bits` ile
`p * net_bits - 1` arasındaki bitlerini taşır. Sayfanın `s` sözcüğü, sayfanın
bitlerinin `s * small` numaralı bitinden başlayan `small` bittir; `s` sembolü
de bu sözcüğün kodudur (bölüm 2.5).

- Akışın sonundan sonraki bitler 0'dır. Böylece akış bitleri taşıyan son
  sözcük alt ucunda 0 bitleriyle doldurulur ve son sayfanın ondan sonraki her
  sözcüğü 0 olur. 0 sözcüğünün sembolü 0'dır; bu yüzden bu sözcükler beyaz
  piksel olarak yazdırılır.
- Bir belge en fazla `MAX_PAGES` sayfadır; daha uzun bir akış kodlanamaz.
- Boş bir akış (`nbytes = 0`) `pages = 0` verir. Bu akış, veri piksellerinin
  tümü beyaz olan ve etiketinde sayfa numarası olarak 1, sayfa sayısı olarak 0
  (`1/0`) yazan tek bir sayfa olarak yazdırılır.

Sayfaları sırayla okuyup `net_bits` bitlerini birleştirmek, akışı ve ardından
gelen 0 bitlerini verir. Bir sayfa akışın nerede bittiğini kaydetmez: yalın bir
belge, dosyasını son sayfasının sonuna kadar sıfır baytlarla tamamlanmış
olarak geri verir (`net_bits` 8'in katı değilse, bir baytı doldurmayan bitler
hariç). Künye (kısım 3) ve kapsayıcı (kısım 4) dosyanın boyutunu kaydeder.

```example
a4_pages_for_0_bytes = 0
a4_pages_for_1_byte = 1
a4_pages_for_199773_bytes = 1
a4_pages_for_199774_bytes = 2
a4_words_for_1000_bytes = 667
```

1000 baytlık bir akış, ilk sayfanın 667 sözcüğünü doldurur; bunların sonuncusu
akışın 8 bitini ve dört 0 biti taşır.

Vektörler: `tests/vectors/c/encoder_pages.json`.

### 2.8 Etiket { #28-the-label }

Etiket alanı, insanlar için ve künyeli bir belgede okuyucu program için tek
satırlık bir metin taşır. Sabit bir yazı tipiyle çizilir.

**Yazı tipi şeridi**, `LABEL_HEIGHT` satır ve 1500 sütundan oluşan, her pikseli
siyah ya da beyaz olan bir görüntüdür. `0` ile `TEXT_WIDTH * GLYPH_CELLS - 1`
arasındaki sütunlar, her biri `TEXT_WIDTH` sütunluk `GLYPH_CELLS` adet karakter
hücresi taşır: kodu `c` olan karakterin hücresi (`32 <= c <= 126`)
`TEXT_WIDTH * (c - FIRST_CHAR)` sütununda başlar. Kalan sütunlar bir logo
taşır. Glifler ve logo siyah üzerine beyazdır. Şerit, bu projenin
`src/optar/data/font.png` dosyasıdır (bir pikseli, gri değeri 128 veya
üzerindeyse beyazdır); aşağıdaki özeti, piksellerinin satır satır 0 (siyah) ve
255 (beyaz) baytları olarak alınmış hâlinin SHA-256 değeridir.

```example
strip_width = 1500
logo_width = 265
glyph_column_of_capital_a = 429
font_strip_sha256 = 481c0abd7884afb5ab6d958fbb95c0d6be97b0e2a7124f57e1abcd118d7d4bc4
```

`total` sayfalık belgenin `page` sayfası için, serbest metni `text` olan
**etiket satırı** şudur:

    two spaces, the format string, a space, page, "/", total, a space, text

`page` ve `total` başında sıfır olmadan onluk tabanda yazılır.
`total` değerinden sonraki boşluk, `text` boş olsa bile bulunur. Satır daha
sonra ilk `data_width // TEXT_WIDTH - 1` karakterine (Unicode kod noktası)
kısaltılır.

**Çizim.** Alan `data_width` sütun genişliğindedir ve sütunları `border` sayfa
sütunundan başlayarak 0'dan numaralanır; içinde çizilmeyen her şey siyahtır.

1. `logo_width <= data_width` ise logo, alanın `0` ile `logo_width - 1`
   arasındaki sütunlarına kopyalanır.
2. Logo çizilmiş olsun ya da olmasın, bir imleç alanın `logo_width`
   sütunundan başlar.
3. Kısaltılmış satırın her karakteri için, sırayla: kodu 32'den küçük ya da
   127'den büyük olan bir karakter atlanır. Aksi hâlde, imleç artı
   `TEXT_WIDTH` en fazla `data_width` ise, şeridin
   `TEXT_WIDTH * (code - FIRST_CHAR)` sütunundan başlayan `TEXT_WIDTH` sütunu
   alana, imlecin bulunduğu yere kopyalanır; her iki durumda da imleç
   `TEXT_WIDTH` kadar ilerler.

Aynı sayfaları yazdırmak için bir kodlayıcının yeniden üretmesi gereken üç
sonuç:

- Bir sayfa en fazla `(data_width - logo_width) // TEXT_WIDTH` karakter
  gösterir; bu, satırın kısaltıldığı uzunluktan azdır; kalanı çizilmez.
- 32 ile 127 arası kodların dışındaki karakterler hücre kaplamaz, ama satırın
  kısaltıldığı uzunluğun hesabına katılır.
- 127 kodu bir hücre kaplar ve logonun ilk `TEXT_WIDTH` sütununu çizer. Böyle
  bir etiket geri okunamaz.

```example
a4_label_line = "  0-65-93-24-3-1-2-24 3/7 backup.tar"
a4_label_characters = 117
a4_label_cells = 98
a4_xlarge_label_cells = 18
```

`a4_label_characters` satırın kısaltıldığı uzunluk, `a4_label_cells` ise bir
sayfanın gösterdiği karakter sayısıdır. `0-22-31-24-3-1-2-24` biçimindeki bir
sayfa 18 karakter gösterir; bu, biçim dizesinin karakter sayısından azdır. Bu
tür sayfaların çıktıda nasıl etiketlendiğini 5.4 bölümü anlatır.

Vektörler: `tests/vectors/c/label.json`, `tests/vectors/c/encoder_pages.json`.

## 3. Belge künyesi (0.2.0 çıktıları) { #3-the-document-tag-020-printouts }

Yalın bir belge, dosyasının ne kadar uzun olduğunu, hangi sayfaların birbirine
ait olduğunu ya da dosyanın doğru okunup okunmadığını söylemez. **Künyeli bir
belge** bunları her etiketin serbest metninde söyler. Akışı dosyanın
kendisidir; bu yüzden sayfaları künyeden haberi olmayan programlar tarafından
da okunur.

### 3.1 Künye { #31-the-tag }

`size` baytlık bir dosya için:

- `SIZE`, başında sıfır olmadan onluk tabanda yazılmış `size` değeridir (boş
  dosya için `0`), en fazla `MAX_SIZE_DIGITS` basamak;
- `FINGERPRINT`, dosyanın SHA-256 değerinin küçük harfli onaltılık olarak
  yazılmış ilk `FINGERPRINT_DIGITS` karakteridir;
- `CHECK`, `total` sayfalık belgenin `page` sayfası için,
  `SIZE:FINGERPRINT:page/total` ASCII metninin küçük harfli onaltılık SHA-256
  değerinin ilk `CHECK_DIGITS` karakteridir; `page` ve `total` burada etiket
  satırının yazdığı gibi yazılır.

Bir sayfanın künyesi `[SIZE:FINGERPRINT:CHECK]` metnidir. Sayfanın etiketindeki
serbest metin ya künyedir ya da künye, bir boşluk ve bir addır. `SIZE` ve
`FINGERPRINT` bir belgenin her sayfasında aynıdır; `CHECK` sayfadan sayfaya
değişir.

Boş bir dosya, `1/0` olarak etiketlenmiş tek bir sayfadır (bölüm 2.7);
denetim değeri `page` 1 ve `total` 0 ile hesaplanır.

```example
tag_fingerprint_of_x = 2d711642
tag_check_input = "1:2d711642:1/1"
tag_check_of_x_page_1_of_1 = ca
tag_free_text = "[1:2d711642:ca] name.tar"
tag_of_empty_file = "[0:e3b0c442:e0]"
```

İlk dört satır, `name.tar` adıyla yazdırılmış tek baytlık `x` dosyası
içindir.

Vektörler: `tests/vectors/py/tag.json`.

### 3.2 Bir künye ne zaman geçerlidir { #32-when-a-tag-is-valid }

Bir etiketin serbest metni; `[`, yukarıdaki gibi bir boyut, `:`, `0-9a-f`
arasından tam 8 karakter, `:`, `0-9a-f` arasından tam 2 karakter ve `]` ile
başlıyorsa ve künyeden sonra bir boşluk ya da metnin sonu geliyorsa **bir
künyeyle başlar**.

`F` sayfa biçiminde, `total` sayfalık belgenin `page` sayfasından okunan bir
künye, şu ikisi birlikte sağlandığında **geçerlidir**:

- denetim değeri, okunan boyut, parmak izi, `page` ve `total` değerlerinden
  hesaplanan denetim değerine eşittir;
- boyut sayfa sayısına uyar: `size = 0` ve `total = 0`, ya da `size > 0`,
  `total > 0` ve `(total - 1) * capacity < size <= total * capacity`; burada
  `capacity`, `F` biçiminin `net_bits // 8` değeridir.

İki `standard` düzende (bölüm 5.2) `net_bits` 8'in katıdır; bu yüzden bir
boyut, tam olarak 2.7 bölümünün ona verdiği sayfa sayısına uyar. Bu projenin
okuyucu programı sayfaları künyeleriyle yalnızca bu iki düzende tanır.

Vektörler: `tests/vectors/py/tag.json`.

## 4. Kendini tanıtan belgeler (sürüm 1) { #4-self-identifying-documents-version-1 }

**Kendini tanıtan bir belge**, her sayfanın verisinde, sayfanın hangi belgeye
ait olduğunu ve kaçıncı sayfa olduğunu söyleyen bir başlık taşır; hasarlı
sayfaların onarılmasını ve eksik sayfaların yeniden oluşturulmasını sağlayan
eşlik de taşıyabilir. Dosya, adı ve eşlik bir akışa, yani **kapsayıcıya**
paketlenir ve bu akış sıradan sürüm 0 sayfaları (kısım 2) olarak yazdırılır.
Sürüm 1 kapsayıcının sürümüdür; sayfa biçimi sürüm 0 olarak kalır.

### 4.1 Boyutlar { #41-sizes }

`F` sayfa biçimi, `parity` eşlik düzeyi (bölüm 4.4) ve `T` sayfa sayısı için:

    page_bytes = net_bits // 8                         payload of one page
    page_body  = page_bytes - HEADER_COPIES * HEADER_SIZE
    k          = CODEWORD - parity                     data bytes of a codeword
    m(T)       = T * page_body // CODEWORD             codewords
    D(T)       = m(T) * k                              bytes of the data region

Bir sayfanın **yükü**, onun ilk `page_bytes * 8` veri bitinin bayt olarak
alınmış hâlidir. Bir sayfanın **gövdesi**, başlık kopyaları (bölüm 4.3)
çıkarılmış yüküdür, `page_body` bayt. **Belgenin gövdesi**, 1 ile `T`
arasındaki sayfaların gövdelerinin birleştirilmesidir, `T * page_body` bayt.

Bir sayfa biçimi ancak `page_bytes // HEADER_COPIES >= HEADER_SIZE` ise bir
kapsayıcı taşıyabilir.

```example
a4_page_bytes = 199773
a4_page_body = 199583
```

Vektörler: `tests/vectors/py/container.json`.

### 4.2 Başlık { #42-the-header }

Bir başlık `HEADER_SIZE` bayttır:

<!-- spec-table: header-fields -->
| Başlangıç | Boyut | Alan | Tür | İçerik |
|---|---|---|---|---|
| 0 | 4 | `magic` | bayt dizisi | `HEADER_MAGIC` |
| 4 | 1 | `version` | tam sayı | `CONTAINER_VERSION` |
| 5 | 1 | `parity` | tam sayı | kod sözcüğü başına eşlik baytı: 0, 32 veya 64 |
| 6 | 2 | `page` | tam sayı | bu sayfanın numarası, 1'den başlayarak |
| 8 | 2 | `total` | tam sayı | belgedeki sayfa sayısı |
| 10 | 8 | `size` | tam sayı | dosyanın bayt cinsinden boyutu |
| 18 | 16 | `fingerprint` | bayt dizisi | dosyanın SHA-256 değerinin ilk `FINGERPRINT_SIZE` baytı |
| 34 | 4 | `crc` | tam sayı | 0 ile 33 arasındaki baytların CRC-32 değeri |

Tam sayılar big-endian düzenindedir. `page` (ve onunla birlikte `crc`) dışındaki
tüm alanlar bir belgenin her sayfasında aynıdır.

```example
header_bytes = 6f5074310140000300070000000000086e3c000102030405060708090a0b0c0d0e0f1ef0ca9d
header_crc = 0x1ef0ca9d
```

Bu, 552508 baytlık, eşliği 64 olan ve parmak izi `00` ile `0f` arasındaki
baytlardan oluşan bir dosyanın, 7 sayfalık belgesindeki 3. sayfanın
başlığıdır.

Vektörler: `tests/vectors/py/container.json`.

### 4.3 Bir sayfanın yükü { #43-the-payload-of-a-page }

Sayfa başlığının `c` kopyası (`0 <= c < HEADER_COPIES`) yükün şu baytlarında
bulunur:

    c * (page_bytes // HEADER_COPIES)   to   c * (page_bytes // HEADER_COPIES) + HEADER_SIZE - 1

Öteki yük baytları, sırasıyla, sayfanın gövdesidir.

```example
a4_header_offsets = 0, 39954, 79908, 119862, 159816
```

Vektörler: `tests/vectors/py/container.json`.

### 4.4 Eşlik düzeyleri { #44-parity-levels }

<!-- spec-table: parity -->
| Ad | Eşlik baytı | Veri baytı |
|---|---|---|
| none | 0 | 255 |
| standard | 32 | 223 |
| high | 64 | 191 |

“Eşlik baytı” sütunu başlıktaki `parity` alanıdır; “Veri baytı” sütunu `k`
değeridir. Eşliği 0 olan bir belgede başlıklar ve ad bulunur, ama hiçbir şey
onarılmaz.

Vektörler: `tests/vectors/py/container.json`.

### 4.5 Reed-Solomon kodu { #45-the-reed-solomon-code }

Bir **kod sözcüğü** `CODEWORD` bayttır: `k` veri baytı ve ardından `parity`
eşlik baytı.

- Baytlar, cisim polinomu `x^8 + x^4 + x^3 + x^2 + 1` (`0x11D`) olan GF(256)
  cisminin elemanlarıdır: bir bayt, GF(2) üzerinde, `x^7` katsayısı en anlamlı
  biti olan bir polinomdur; toplama XOR, çarpma ise cisim polinomuna göre
  modüler polinom çarpımıdır.
- `alpha`, `0x02` elemanıdır.
- Üreteç polinomu
  `g(x) = (x - alpha^0)(x - alpha^1) ... (x - alpha^(parity - 1))` olur.
- Bir kod sözcüğünün `i` numaralı baytı (`0 <= i <= 254`), kod sözcüğü
  polinomu `c(x)` içindeki `x^(254 - i)` teriminin katsayısıdır.
- Veri baytları, `x^254` teriminden `x^parity` terimine kadar inen
  katsayılardır. Eşlik baytları, `g(x)` polinomu `c(x)` polinomunu bölecek
  şekilde seçilir: bunlar, veri polinomunun (`x^parity` altındaki katsayıları
  sıfır alınarak) `g(x)` ile bölümünden kalanın katsayılarıdır, önce
  `x^(parity - 1)` katsayısı gelmek üzere.

Bir kod sözcüğü `2 * e + f <= parity` olduğunda onarılabilir; burada `f`,
okunamadığı bilinen baytlarının (silintilerin) sayısı, `e` ise yanlış olan
öteki baytlarının sayısıdır.

```example
gf_alpha_8 = 0x1d
gf_alpha_254 = 0x8e
rs_32_parity_of_one = 744034ae367e10c2a221219db0c5e10c3b37fde4942fb3b9188afd148e37ac58
rs_32_parity_of_counting = 41841183b11fdb537421939696cda70e1db5c86684af222564b89cc6069f172e
```

`rs_32_parity_of_one`, son baytı 1 olan ve geri kalanı sıfır olan 223 veri
baytının, eşlik 32 için eşliğidir; bunlar `g(x)` polinomunun `x^31` teriminden
`x^0` terimine kadar inen katsayılarıdır. `rs_32_parity_of_counting`, 0, 1, 2,
..., 222 veri baytlarının eşliğidir.

Vektörler: `tests/vectors/py/reed_solomon.json`.

### 4.6 Veri bölgesi ve yayma { #46-the-data-region-and-the-spread }

**Veri bölgesi** `D(T)` bayttır:

| Bayt | İçerik |
|---|---|
| `size` | dosya |
| 1 | `L`, adın bayt cinsinden uzunluğu, 0 ile `NAME_MAX_BYTES` arası |
| `L` | dosyanın UTF-8 olarak adı |
| geri kalanı | dolgu (bölüm 4.7) |

UTF-8 olarak `NAME_MAX_BYTES` bayttan uzun bir ad, sığan en uzun tam karakter
sayısına kısaltılır. Ad parmak izinin kapsamında değildir. Adın UTF-8 ile
kodlanamayan bir karakteri (tek başına duran bir vekil kod noktası, U+D800 ile
U+DFFF arası) `?` olarak saklanır.

`j` kod sözcüğü (`0 <= j < m`), veri baytları olarak veri bölgesinin `j * k`
ile `j * k + k - 1` arasındaki baytlarını alır. Eşlik 0 olduğunda bir kod
sözcüğü kendi 255 veri baytından ibarettir.

**Yayma.** `j` kod sözcüğünün `i` numaralı baytı, belge gövdesinin şu
konumdaki baytıdır:

    i * m + (j + i * SPREAD_STEP) mod m

Böylece her kod sözcüğünün `i` numaralı baytı gövdenin `i * m` ile
`(i + 1) * m - 1` arasındaki diliminde bulunur ve bir kod sözcüğünün 255 baytı,
belgenin tamamına yayılmış 255 farklı dilimde yer alır: bir yerdeki hasar,
birkaç kod sözcüğünün her şeyini kaybettirmek yerine her kod sözcüğüne birkaç
bayta mal olur.

Gövdenin son `T * page_body - CODEWORD * m` baytı (`CODEWORD` değerinden az)
hiçbir kod sözcüğüne ait değildir ve dolgudur.

Vektörler: `tests/vectors/py/container.json`.

### 4.7 Dolgu { #47-padding }

Dolgu hiçbir şey taşımaz. İki içerik vardır ve ikisi de geçerlidir:

- optar 0.3.0 sıfır baytlar yazıyordu;
- optar 0.3.1 ve sonrası **dolgu akışını** yazar: akışın `n` numaralı parçası
  (`n = 0, 1, 2, ...`) şöyle elde edilen `PADDING_BLOCK` bayttır:
  `PADDING_KEY` baytlarının ardına `n` değeri 8 bayt big-endian olarak eklenir
  ve bu bayt dizisinin tamamının SHA-256 değeri alınır; akış, parçaların
  birleştirilmesidir. Veri bölgesinin dolgusu, akışın 0 numaralı
  baytından başlar; gövdenin sonundaki dolgu, akışı veri bölgesinin dolgusunun
  bittiği yerden sürdürür. (Sıfır baytlar her sayfada boydan boya beyaz
  çizgiler olarak yazdırılır; akış ise veri gibi yazdırılır.)

Dolgusu başka herhangi bir şey olan bir belge de okuyucu program için yine
geçerli bir belgedir (bölüm 6.4), ama bu projenin yazdırdığı sayfaları yalnızca
dolgu akışı verir.

```example
padding_block_0 = d518824e181c15b2f69e390066efbfa00d73eb8f0c3d932313396940eedd1286
padding_bytes_30_to_33 = 12863e00
```

Vektörler: `tests/vectors/py/container.json`.

### 4.8 Sayfa sayısı ve sınırlar { #48-the-page-count-and-the-limits }

Bir belge, dosyayı, uzunluk baytını ve adı taşıyabilen en az sayıda sayfadan
oluşur:

    need = size + 1 + L
    T    = the smallest T >= 1 with D(T) >= need

Sınırlar şunlardır:

- `T <= MAX_PAGES`;
- `parity > 0` ise: `T * page_bytes <= PROTECTED_MAX_BYTES`;
- `size < 2^64`, `L <= NAME_MAX_BYTES`.

Daha fazlasını gerektiren bir dosya bir belgeye konamaz.

```example
plan_need = 1000011
plan_codewords_needed = 4485
plan_pages = 6
plan_codewords = 4696
plan_data_bytes = 1047208
plan_body_bytes = 1197498
plan_spare_bytes = 18
plan_padding_in_region = 47197
plan_position_of_codeword_0_byte_0 = 0
plan_position_of_codeword_5_byte_0 = 5
plan_position_of_codeword_5_byte_1 = 7924
plan_position_of_codeword_5_byte_254 = 1194327
plan_page_of_codeword_5_byte_254 = 6
```

Örnek, eşlik 32 ile standart A4 sayfalarına yazılan, `vector.bin` adlı
1000000 baytlık bir dosyadır. Dosya 4485 kod sözcüğü gerektirir; beş sayfa daha
azını taşır, altı sayfa ise `m = 4696` kod sözcüğü taşır. Belgede 4696 kod
sözcüğünün tümü bulunur; dosyanın gerek duymadıkları dolgu taşır.
`plan_spare_bytes` gövdenin sonundaki dolgu, `plan_padding_in_region` ise veri
bölgesinin dolgusudur. Konumlar, belgenin gövdesindeki konumlardır (bölüm
4.6).

Vektörler: `tests/vectors/py/container.json`.

### 4.9 Belge neye dayanır (bilgilendirici) { #49-what-the-document-withstands-informative }

Kaybolan bir sayfa, bir kod sözcüğüne en fazla `ceil(page_body / m) + 1` bayta
mal olur. Bu proje, `n * (ceil(page_body / m) + 1) <= PROMISE_NUM * parity // PROMISE_DEN`
olduğunda kullanıcısına herhangi `n` sayfanın kaybolabileceğini söyler; bu,
eşliğin dörtte birini kalan sayfalardaki hasar için bırakır. Bu, araçların
verdiği bir sözdür; bir okuyucu programın güvenebileceği ya da denetlemesi
gereken bir özellik değildir.

### 4.10 Kapsayıcıdan sayfalara { #410-from-the-container-to-pages }

Akış `T * net_bits // 8` bayttır. Bir bit dizisi olarak okunduğunda, `p`
sayfasının (1'den başlayarak) yükü `(p - 1) * net_bits` numaralı bitte başlar;
öteki tüm bitler 0'dır. `net_bits` 8'in katı olduğunda akış, yüklerin
birleştirilmesinden ibarettir. Değilse her sayfada yükünden sonra
`net_bits mod 8` kullanılmayan bit bulunur ve bazı sayfaların yükü akışın bir
baytının başında başlamaz.

Akış 2.7 bölümünde anlatıldığı gibi yazdırılır; bu, tam olarak `T` sayfa
verir. Bir sayfanın etiketi, serbest metni insanlar için olan sıradan bir
etiket satırıdır: serbest metin dosyanın adıdır (kullanıcının verdiği etiket
ya da dosyanın adı), her sayfada aynıdır ve künye taşımaz. (Geçerli bir künye,
okuyucu programın sayfayı künyeli bir belgenin sayfası sanmasına yol açardı,
bölüm 6.1.)

Golay koduyla `net_bits mod 8` 0 ya da 4'tür ve son yük her zaman akışın
içinde biter. Bu proje kendini tanıtan belgeleri yalnızca 5.2 bölümündeki on
sayfa biçiminde yazdırır ve okuyucu programı başlıkları yalnızca bu
biçimlerde arar.

```example
a4_medium_stream_bytes_for_3_pages = 344713
a4_medium_page_2_starts_at = 114904, 4
a4_medium_page_3_starts_at = 229809, 0
```

`0-50-70-24-3-1-2-24` biçimindeki bir sayfada `net_bits = 919236` olur; bu,
114904 baytlık yükünden sonra 4 bit bırakır. İki değer, sayfanın yükünün
başladığı akış baytı ve o bayt içindeki bittir (0 en anlamlısıdır).

Vektörler: `tests/vectors/py/container.json`, `tests/vectors/c/container_pages.json`.

## 5. Yazdırma { #5-printing }

### 5.1 Nokta boyutları { #51-dot-sizes }

Bir sayfa beş nokta boyutundan biriyle yazdırılır. Bir veri noktası tam sayıda
yazıcı noktasından oluşan bir karedir; böylece her sayfa pikseli, yazıcı
noktalarından oluşan aynı kare olarak yazdırılır.

<!-- spec-table: dot-sizes -->
| Ad | Veri noktası başına yazıcı noktası | İnç başına veri noktası | Nokta boyutu (pt) | Önerilen tarama (dpi) |
|---|---|---|---|---|
| standard | 3 | 200 | 0.36 | 600 |
| medium | 4 | 150 | 0.48 | 450 |
| big | 5 | 120 | 0.6 | 360 |
| large | 6 | 100 | 0.72 | 300 |
| xlarge | 9 | 200/3 | 1.08 | 200 |

Önerilen tarama çözünürlüğü, veri noktası başına `SCAN_PIXELS_PER_DOT` tarama
pikseli verir. Bu bir öneridir; bir sayfa, hangi tarama çözünürlüğünde olursa
olsun aynı sayfadır.

### 5.2 Düzenler { #52-layouts }

Bir **düzen**; bir kâğıt, bir nokta boyutu ve bunun üzerine yazdırılan sayfa
biçimidir. On düzen vardır. Kâğıtlar `a4` ve `letter` olarak adlandırılır.

<!-- spec-table: layouts -->
| Kâğıt | Noktalar | Yatay artı işareti | Dikey artı işareti | Biçim dizesi | Genişlik (px) | Yükseklik (px) | Net bit | Sayfa baytı | Gövde baytı |
|---|---|---|---|---|---|---|---|---|---|
| a4 | standard | 65 | 93 | `0-65-93-24-3-1-2-24` | 1546 | 2242 | 1598184 | 199773 | 199583 |
| a4 | medium | 50 | 70 | `0-50-70-24-3-1-2-24` | 1186 | 1690 | 919236 | 114904 | 114714 |
| a4 | big | 40 | 56 | `0-40-56-24-3-1-2-24` | 946 | 1354 | 584220 | 73027 | 72837 |
| a4 | large | 33 | 46 | `0-33-46-24-3-1-2-24` | 778 | 1114 | 392952 | 49119 | 48929 |
| a4 | xlarge | 22 | 31 | `0-22-31-24-3-1-2-24` | 514 | 754 | 172848 | 21606 | 21416 |
| letter | standard | 67 | 87 | `0-67-87-24-3-1-2-24` | 1594 | 2098 | 1540728 | 192591 | 192401 |
| letter | medium | 51 | 66 | `0-51-66-24-3-1-2-24` | 1210 | 1594 | 883704 | 110463 | 110273 |
| letter | big | 41 | 52 | `0-41-52-24-3-1-2-24` | 970 | 1258 | 555708 | 69463 | 69273 |
| letter | large | 34 | 44 | `0-34-44-24-3-1-2-24` | 802 | 1066 | 387228 | 48403 | 48213 |
| letter | xlarge | 23 | 29 | `0-23-29-24-3-1-2-24` | 538 | 706 | 169020 | 21127 | 20937 |

“Sayfa baytı” ve “Gövde baytı”, 4.1 bölümündeki `page_bytes` ve `page_body`
değerleridir. Bu proje yalın ya da künyeli bir belgeyi bir `standard` düzende
(ya da kendisine elle bir biçim dizesi verildiğinde, her kenar boşluğunun en
az `MIN_MARGIN_PT` olması koşuluyla, o sayfa biçiminde, standart nokta
boyutunda ve kâğıdın `standard` düzeninin kaydırmalarıyla), kendini tanıtan
bir belgeyi ise on düzenden herhangi birinde yazdırır.

Vektörler: `tests/vectors/c/bit_placement.json`, `tests/vectors/py/container.json`.

Sayfa görüntüsü kâğıda, sol alt köşesi aşağıdaki kaydırmalarda olacak şekilde
yerleştirilir; kaydırmalar kâğıdın sol alt köşesinden ölçülür. Kenar
boşlukları, her kenarda kalan kısımdır.

<!-- spec-table: layouts -->
| Kâğıt | Noktalar | Kâğıt genişliği (pt) | Kâğıt yüksekliği (pt) | Kaydırma x (pt) | Kaydırma y (pt) | Sol (mm) | Alt (mm) | Sağ (mm) | Üst (mm) |
|---|---|---|---|---|---|---|---|---|---|
| a4 | standard | 595.28 | 841.89 | 19.20 | 17.40 | 6.77 | 6.14 | 6.89 | 6.13 |
| a4 | medium | 595.28 | 841.89 | 12.96 | 15.24 | 4.57 | 5.38 | 4.60 | 5.45 |
| a4 | big | 595.28 | 841.89 | 13.80 | 14.64 | 4.87 | 5.16 | 4.90 | 5.24 |
| a4 | large | 595.28 | 841.89 | 17.52 | 19.80 | 6.18 | 6.99 | 6.21 | 7.06 |
| a4 | xlarge | 595.28 | 841.89 | 20.04 | 13.68 | 7.07 | 4.83 | 7.10 | 4.90 |
| letter | standard | 612 | 792 | 19.08 | 18.36 | 6.73 | 6.48 | 6.73 | 6.48 |
| letter | medium | 612 | 792 | 15.60 | 13.44 | 5.50 | 4.74 | 5.50 | 4.74 |
| letter | big | 612 | 792 | 15.00 | 18.60 | 5.29 | 6.56 | 5.29 | 6.56 |
| letter | large | 612 | 792 | 17.28 | 12.24 | 6.10 | 4.32 | 6.10 | 4.32 |
| letter | xlarge | 612 | 792 | 15.48 | 14.76 | 5.46 | 5.21 | 5.46 | 5.21 |

Her kaydırma tam sayıda yazıcı noktasıdır; böylece görüntünün kenarları aygıt
noktalarına denk gelir. İki `standard` düzenin ızgaraları ve kaydırmaları
devralınmıştır (kısım 8). Öteki sekizi türetilmiştir: ızgara, sayfanın kendi
nokta boyutunda her kenarda en az `MIN_MARGIN_PT` bıraktığı en büyük
`xcrosses` ve `ycrosses` değerleridir; her kaydırma, boş uzunluğun yarısının
tam bir yazıcı noktasına aşağı yuvarlanmış hâlidir. Düzenleri bu kural değil,
tablolar tanımlar.

Bir sayfanın kimliği, sayfanın kâğıt üzerinde nerede durduğuna bağlı değildir:
okuyucu program sayfayı çerçevesinden bulur. Yerleşim yalnızca yazdırma için
önemlidir: başka bir ölçekte yazdırılan bir sayfanın noktaları başka
boyuttadır, kenara daha yakın yazdırılan bir sayfa ise kırpılabilir.

### 5.3 Bu projenin yazdığı PDF { #53-the-pdf-this-project-writes }

Belgenin her sayfası bir PDF sayfasıdır; bu PDF sayfasının medya kutusu
kâğıttır: punto cinsinden `[0 0 width height]`. Sayfa görüntüsü, piksel başına
1 bitlik (1 beyazdır), `width` genişliğinde ve `height` yüksekliğinde sayfa
pikselinden oluşan tek bir görüntüdür; ara değerleme olmadan, sol alt köşesi
düzenin kaydırmalarında olacak şekilde çizilir ve bir sayfa pikseli bir veri
noktası olacak şekilde ölçeklenir:

    image width in points  = width  * dot size in points
    image height in points = height * dot size in points

```example
a4_large_image_width_pt = 560.16
a4_large_image_height_pt = 802.08
```

PDF, gerçek boyutta (%100) yazdırılmak üzere hazırlanmıştır. PDF'yi hiçbir
vektör sabitlemez; bunu `tests/unit/test_pdf.py` yapar.

Sayfa görüntüleri, sayfa pikseli başına bir görüntü pikseli olacak şekilde PNG
ya da PGM dosyası olarak da yazılır; vektörler bir sayfayı, ikili PGM (`P5`)
dosyasının SHA-256 değeriyle tanımlar. Bu dosyanın tam baytlarını
`tests/vectors/README.md` verir: ASCII olarak `P5\n<width> <height>\n255\n`
başlığı, ardından satır satır piksel baytları.

### 5.4 Etiket şeridi { #54-the-label-strip }

Bir etiket sayfa pikselleriyle çizilir (bölüm 2.8); bu yüzden daha büyük
noktalı bir sayfada daha az karakter taşır: en büyük noktalarda kendi biçim
dizesine bile yetmeyecek kadar az. Bu nedenle bir PDF'de, nokta boyutu
`standard` olmayan bir düzenin sayfasında etiket, standart veri noktalarıyla
çizilen ikinci bir görüntü olan **etiket şeridiyle** değiştirilir:

- şerit `LABEL_HEIGHT` satır ve
  `floor(data_width * printer dots per data dot / STANDARD_PRINTER_DOTS)`
  sütun şerit pikselinden oluşur;
- şerit, sayfanın etiket satırını taşır; satır, `data_width` yerine şeridin
  genişliği alınarak 2.8 bölümündeki gibi kısaltılır ve çizilir;
- sayfa görüntüsünde etiket alanı, `border` ile `border + data_width - 1`
  arasındaki sütunlarda siyah yapılır;
- şerit, şerit pikseli başına 0.36 pt ile, sol kenarı alanın veri
  sütunlarının sol kenarında olacak ve alanın yüksekliği içinde ortalanacak
  şekilde alanın üzerine çizilir.

Kısım 2'deki sayfadan yalnızca etiket alanı farklıdır; veri alanına ve
çerçeveye dokunulmaz. Böyle bir düzenin PNG ya da PGM sayfası 2.8 bölümündeki
etiketi korur. Kendini tanıtan bir sayfanın etiketi o sayfayı tanımak için
kullanılmaz (bölüm 6.2); bu yüzden bir okuyucu programın şeridi okuması
gerekmez.

```example
a4_large_strip_width = 1548
a4_large_strip_characters = 118
a4_large_strip_width_pt = 557.28
```

Vektörler: `tests/vectors/c/container_pages.json`, daha büyük noktalı iki
düzenin sayfalarını sıradan sayfalar olarak sabitler; şeridi
`tests/unit/test_font.py` ve `tests/unit/test_pdf.py` sabitler.

## 6. Okuyucu program ne yapmalıdır { #6-what-a-reader-must-do }

Bir okuyucu programın elinde taranmış sayfalar vardır ve program, herhangi bir
yöntemle, her birinden veri bitlerini ve yapabildiği yerde etiketini okumuştur.
Bu kısım, programın bunlardan hangi sonucu çıkarması gerektiğini söyler.
Taramalar güvenilmezdir: tek bir sayfayı herkes yazdırabilir ve bu sayfa her
şeyi iddia edebilir.

### 6.1 Geçerli bir künye başlığa üstün gelir { #61-a-valid-tag-wins-over-a-header }

Bir `standard` düzendeki bir sayfa için okuyucu program önce etikete
bakmalıdır. Etiket 2.8 bölümündeki biçimdeyse, düzenin biçim dizesini, en
fazla `MAX_PAGES` olan bir sayfa sayısını, 1 ile sayfa sayısı arasında bir
sayfa numarasını (ya da sayfa sayısı 0 ile birlikte 1) taşıyorsa ve serbest
metni bu sayfa numarası ve sayısı için geçerli olan bir künyeyle başlıyorsa
(bölüm 3.2), sayfa künyeli bir belgenin sayfasıdır. Sayfa, verisi geçerli bir
başlık taşısa bile böyle ele alınmalıdır.

Nedeni: kendini tanıtan bir belgenin akışı, eski bir programın geri verdiği
hâliyle, künyeli bir belge olarak yeniden yazdırılabilir. Bu sayfaların
verisinde eski başlıklar bulunur ve bu sayfalar, dosyası o akış olan künyeli
belgenin sayfalarıdır.

### 6.2 Başlık güvenilmezdir { #62-a-header-is-untrusted }

Bir başlık kopyası; CRC değeri doğruysa, sihirli değeri `HEADER_MAGIC`,
sürümü `CONTAINER_VERSION`, eşliği 0, 32 ya da 64 ise ve `1 <= page <= total`
ise **iyi biçimlidir**.

**Bir sayfanın başlığı**, sayfanın `HEADER_COPIES` kopyasından en az biri iyi
biçimliyse ve iyi biçimli kopyaların tümü eşitse vardır. İyi biçimli kopyaları
birbirinden farklı olan bir sayfanın başlığı yoktur.

`F` biçimindeki bir sayfadan okunan bir başlık, 4.8 bölümünün izin verdiği bir
belgeyi tanımlıyorsa, yani şunların tümü sağlanıyorsa (`m`, `D` ve
`page_bytes`, 4.1 bölümündeki gibi, `F` ve başlığın eşliği için) **kabul
edilebilirdir**:

1. `total <= MAX_PAGES`;
2. `page_bytes // HEADER_COPIES >= HEADER_SIZE`;
3. `parity > 0` ise: `total * page_bytes <= PROTECTED_MAX_BYTES`;
4. `size + 1 <= D(total)`: sayfalar dosyayı ve uzunluk baytını taşır;
5. `total > 1` ise: `size + 1 + NAME_MAX_BYTES > D(total - 1)`: hiçbir ad,
   dosyanın daha az sayfaya sığmasına izin vermezdi.

Bir okuyucu program kabul edilebilir olmayan bir başlığı kullanmamalıdır. 4.
ve 5. kurallar sayfa sayısını boyuta bağlar; böylece bir başlık küçük bir dosya
için çok sayfa ya da büyük bir dosya için az sayfa iddia edemez.

Bir okuyucu program belleğini ve süresini bir başlığın iddia ettiğiyle değil,
kendisine verilen sayfalarla orantılı tutmalıdır: 9999 sayfalık bir belge
iddia eden tek bir sayfa, okuyucu programa 9999 sayfa için bellek ayırtmamalı
ya da 9999 sayfa işletmemelidir.

Başlıkları `fingerprint`, `size`, `total` ve `parity` alanlarında uyuşan ve
aynı sayfa biçimine sahip sayfalar tek bir belgeye aittir. Başka bir belgenin
sayfaları kullanılmamalıdır.

### 6.3 Bir dosyayı yalnızca parmak izi doğrular { #63-only-the-fingerprint-verifies-a-file }

- **Kendini tanıtan belge.** Bir yük baytı, bitlerinden biri sayfa kodunun
  düzeltemediği bir sembolde bulunuyorsa bir silintidir; verilmemiş bir
  sayfanın her baytı bir silintidir. Dosya, veri bölgesinin ilk `size`
  baytıdır ve ancak bu baytlardan birini taşıyan her kod sözcüğü okunduysa ya
  da onarıldıysa (eşlik 0 ile: hiç silintisi yoksa) kurtarılmıştır. Dosya
  kurtarılmışsa ve SHA-256 değerinin ilk `FINGERPRINT_SIZE` baytı başlıktaki
  parmak izine eşitse **doğrulanmıştır**.
- **Künyeli belge.** Dosya, akışın ilk `SIZE` baytıdır. Dosya `SIZE` bayt
  uzunluğundaysa ve SHA-256 değerinin ilk `FINGERPRINT_DIGITS` onaltılık
  karakteri künyedeki parmak izine eşitse **doğrulanmıştır**.
- **Yalın belge.** Onu hiçbir şey doğrulamaz ve uzunluğu bilinmez (bölüm 2.7).

Bir okuyucu program bir dosyayı başka hiçbir nedenle doğrulanmış olarak
nitelememelidir. Özellikle, başarısızlık bildirmeyen bir onarım dosyayı
doğrulamaz: eşliğinin onarabileceğinden daha fazla yanlış baytı olan bir kod
sözcüğü başka bir geçerli kod sözcüğüne dönüşebilir ve eşlik 0 ile hiçbir şey
denetlenmez.

Dosyanın adı (bölüm 4.6) parmak izinin dışındadır. Dosya doğrulanmış olsa bile
ad, her etiket gibi, güvenilmez bir metindir.

### 6.4 Dolgu hiçbir zaman okunmaz { #64-padding-is-never-read }

Bir okuyucu program 4.7 bölümündeki dolguyu okumamalı, denetlememeli ve ona
bağlı olmamalıdır. Sıfır baytlar (0.3.0) ve dolgu akışı (0.3.1) ikisi de
geçerlidir ve bunlardan hangisini taşırsa taşısın bir belge, okuyucu program
için aynı belgedir.

Veri bölgesinde addan sonraki baytlar dolgudur. Uzunluk baytı veri bölgesinin
sonunun ötesini gösteren, baytları UTF-8 olmayan ya da onarılmamış bir kod
sözcüğünde bulunan bir ad kaydı hiçbir ad vermez; dosyayı geçersiz kılmaz.

Vektörler: `tests/vectors/py/container.json`, `tests/vectors/py/tag.json`.

## 7. Referans kod çözücü (bilgilendirici) { #7-reference-decoder-informative }

Bu kısım, bu projenin bir taramayı nasıl okuduğunu anlatır. Bunların hiçbiri
zorunlu değildir: bir okuyucu program bir sayfayı herhangi bir yolla bulabilir
ve örnekleyebilir. Adımlar ve sabitleri, `unoptar` adlı C programınınkilerdir
(kısım 8); bu kod çözücünün belirlenmiş taramalardaki sonuçları, sonda adı
geçen vektörlerle sabitlenmiştir; böylece kod çözücü kazara değişmez.

### 7.1 Tarama { #71-the-scan }

Bir tarama, doğrusal ışıkta 8 bitlik gri bir görüntü olarak okunur. Dosyanın
bir `v` örneği `floor(255 * (v / 255) ^ (1 / gamma) + 0.5)` olur; burada
`gamma`, dosyanın gama değeri (PNG `gAMA`) ya da dosya hiçbir değer vermiyorsa
0.454545'tir. Renkli bir görüntü kanal kanal dönüştürülür, ardından 0.212671
kırmızı, 0.715160 yeşil, 0.072169 mavi ağırlıklarıyla birleştirilir ve en
yakın tam sayıya yuvarlanır. 16 bitlik bir örneğin üst 8 biti alınır.

```example
linear_light_of_128 = 56
linear_light_of_200 = 149
```

### 7.2 Sayfayı bulma { #72-finding-the-page }

Kod çözücüye sayfa biçimi verilir. Kod çözücü dik konumdaki görüntü üzerinde
çalışır.

1. **Gri düzeyleri.** Eşik düzeyi ortalama gri değerden başlar. En fazla 32
   kez: `black`, eşik eksi eşiğin altındaki piksellerin eşiğe olan
   uzaklıklarının karesel ortalamasıdır; `white`, eşik artı eşiğin üstündeki
   piksellerin aynı değeridir; yeni eşik
   `sync_white_cut * white + (1 - sync_white_cut) * black` olur ve yuvarlanır;
   eşik artık değişmediğinde işlem durur. İkinci bir düzey olan doldurma
   eşiği, `black` ile `white` arasının tam ortasındadır.
2. **Sayfayı ayırma.** Sayfanın çevresindeki beyaz, doldurma eşiğinde ya da
   üstünde olan ve taramanın dört köşesinden ya da dört kenar orta noktasından
   birine (köşelerle değil, kenarlarla) bağlı her pikseldir. Sayfa, taramanın
   merkezine bağlı olan geri kalan her şeydir. Öteki tüm pikseller (sayfa ile
   taramanın kenarı arasındaki kir) beyaz yapılır.
3. **Çerçevede bir boşluk.** Bir yazıcı sayfanın bir kenarını kırptıysa,
   çerçevede bir boşluk olur; sayfanın çevresindeki beyaz da noktaların
   arasına sızar ve 2. adım sayfanın yalnızca bir parçasını bulur. Bulunan alan,
   beyaz kenar olmayan kısmın yarısından azsa, sayfanın çevresindeki beyaz
   bunun yerine en az `2 * r + 1` piksel genişliğindeki geçitlerden
   ulaşılabilen kısım olarak alınır; burada
   `r = max(5, longest side // 250) // 2`; noktaların arasındaki beyaz bundan
   daha dardır. Bu sonuç yalnızca bütün bir sayfa veriyorsa kullanılır. Bu,
   biçimin bir özelliği değil, bu kod çözücünün bir toleransıdır: bir sayfanın
   çerçevesi bütündür.
4. **Köşeler.** Kod çözücü taramanın her köşesinden köşegenler boyunca içeri
   doğru ilerler ve eşiğin altındaki ilk pikseli alır. Bu, sayfanın dik ve
   yüksekliğinin genişliğinden büyük olmasını gerektirir; genişliği
   yüksekliğinden büyük bir tarama önce döndürülür (7.5).
5. **Piksel boyutu.** Sayfa pikseli başına tarama pikseli sayısı, yatay ve
   dikey olarak, köşeler arasındaki uzaklıkların `width` ve `height`
   değerlerine bölünmesiyle bulunur; sayfanın satırlarının ve sütunlarının
   yönleri karşılıklı kenarların ortalamalarından gelir. (Yatay boyut sol üst
   köşeyi iki kez kullanır, sol alt köşeyi hiç kullanmaz. Bu, devralınmış bir
   kod çözücü davranışıdır ve biçimin parçası değildir.)

### 7.3 Artı işaretleri { #73-crosses }

İlk artı işareti, sol üst köşeden `border + chalf` sayfa pikseli içeride
beklenir. Öteki her artı işareti sol komşusunun bir aralık (pitch) sağında,
bir satırın ilki ise üstündekinin bir aralık altında beklenir; böylece her
arama daha önce bulunmuş bir artı işaretinden başlar. Her artı işareti için:

1. görüntünün artı işareti deseniyle (koyu, açık, açık, koyu) en iyi
   korelasyonu verdiği yeri bulmak için, her yönde bir artı işareti
   yarısının yarısına kadar, tam tarama pikselleri üzerinde kaba bir arama;
2. her kenarından `cross_trim` sayfa pikseli küçültülmüş bir artı işareti
   üzerinde, yarım tarama pikseli içinde, çeyrek piksellik adımlarla ince bir
   arama;
3. kendine ait bir eşik düzeyi: artı işaretinin piksellerinden, 7.2'deki gibi
   `white` ve `black`, `white_cut * white + (1 - white_cut) * black` olarak
   birleştirilir.

### 7.4 Örnekleme ve kod çözme { #74-sampling-and-decoding }

1. **Filtreler.** Bir sayfa pikselinin boyutunun `minmax_filter` katından dar
   koyu lekeler kaldırılır (bir maksimum filtresinin geçişleri, ardından aynı
   sayıda minimum filtresi geçişi); görüntü sonra 3'e 3'lük bir çekirdekle
   (1 2 1 / 2 4 2 / 1 2 1) `round(pixel area * pixel_blur ^ 2)` kez
   bulanıklaştırılır.
2. **Örnekleme.** Her veri pikselinin taramadaki konumu, çevresindeki dört artı
   işareti arasında ara değerlemeyle bulunur; eşik düzeyi de öyle. Örnek
   keskinleştirilir: `value + unsharp_mask * (value - mean of the four
   neighbours at unsharp_dist page pixels)`. Sonuç eşik düzeyinin altındaysa
   bit 1'dir.
3. **Kod çözme.** Bitler yeniden sembollere yerleştirilir (bölüm 2.6). Bir
   Golay sembolü, en fazla 3 bitte farklıysa en yakın sembolle değiştirilir;
   aksi hâlde sembol düzeltilemez ve üst 12 biti okunduğu gibi alınır. Bir
   Hamming sembolünün tek yanlış biti düzeltilir; iki yanlış bit sembolü
   düzeltilemez kılar.
4. Bir sayfanın sözcükleri birleştirilerek sayfanın `net_bits` veri biti elde
   edilir. Yalın ya da künyeli bir belge için sayfaların bitleri sayfa
   sırasıyla birleştirilir ve baytlara bölünür; son bir baytı doldurmayan
   bitler atılır.

```example
decoder_unsharp_mask = 7
decoder_unsharp_dist = 1
decoder_sync_white_cut = 0.1
decoder_white_cut = 0.06
decoder_minmax_filter = 0.5
decoder_pixel_blur = 0.25
decoder_cross_trim = 0.75
```

### 7.5 Bir taramayı tanıma { #75-identifying-a-scan }

Sayfa biçimi kendisine bildirilmediğinde bu proje onu kendisi bulur:

1. Sayfanın dış hatları (7.2, 1 ile 4 arası adımlar) sayfanın şeklini verir.
   İki kâğıt, şeklin onların `standard` sayfasına ne kadar yakın olduğuna göre
   sırayla denenir; her biri dik konumda ve yarım tur döndürülmüş olarak
   (genişliği yüksekliğinden büyük bir tarama için iki yönden birine çeyrek
   tur döndürülmüş olarak) denenir.
2. Her kâğıt için önce `standard` sayfası: sayfanın yeri bulunur ve etiketi,
   her karakter hücresi yazı tipiyle eşleştirilerek okunur. Geçerli bir künye
   hemen karar verir (bölüm 6.1). Künyesiz bir etiket yalnızca açıkça
   okunduysa kabul edilir ve o zaman da veride yine bir başlık aranır; çünkü
   standart noktalı kendini tanıtan bir sayfanın da böyle bir etiketi vardır.
3. Ardından kâğıdın düzenleri, şekli en yakın olandan başlayarak: sayfanın
   yeri bulunur, kodu çözülür ve kabul edilebilir bir başlık (bölüm 6.2) karar
   verir.

Yanlış okunmuş bir künye, denetimden yaklaşık 256 denemede bir geçer; künyesiz bir etiketin ise hiç denetimi yoktur; bu yüzden böyle bir etiket açıkça okunmalıdır ve geçerli bir künyeden yalnızca bir karakterlik yanlış okumayla ayrılan serbest metin reddedilir. Bu kabul eşikleri biçime değil, bu okuyucu programa aittir.

### 7.6 Yavaş okuma yöntemi { #76-the-slower-reader }

7.5'teki adımlar hiçbir şey tanımadığında ama bir sayfanın dış hatları
bulunduğunda, ya da veri pikseli başına 2.5'ten az tarama pikseli düşen bir
taramada, sayfanın sembollerinin %1'i veya daha fazlası düzeltilemezken bir
sayfa yalnızca künyesiz bir etiketle kabul edildiğinde, bu proje ikinci, daha
yavaş bir okuma yöntemi (`src/optar/decoder/soft.py`) dener; bu yöntem,
nokta boyutuna göre çözünürlüğü çok düşük bir tarama için tasarlanmıştır.
Yöntem, 7.5'teki sırayla, her aday düzen ve döndürme için:

1. taramayı bir veri pikseli yaklaşık dört tarama pikseli genişliğinde olacak
   şekilde büyütür ve sayfanın yerini 7.2 ve 7.3'teki gibi bulur;
2. sayfayı 7.4'teki gibi okur ve en fazla bir biti düzeltilerek çözülen
   sembolleri bilinen olarak alır;
3. her veri pikselinin çevresinde, aralarında yarım veri pikseli bulunan
   7'ye 7'lik bir nokta ızgarasını örnekler ve bu örneklerden bilinen bitlere
   giden bir filtreyi en küçük kareler yöntemiyle uydurur; sayfanın 16'ya
   22'lik bölgelerinin her biri için bir filtre;
4. filtreleri her veri pikseline uygular; bu, her bit için işaretli bir güven
   değeri verir; her Golay sembolü için 24 güven değerine en iyi uyan kod
   sözcüğünü seçer;
5. sembollerin güveni daha yüksek olan %60'ını bilinen olarak alır ve 3.
   adımdan itibaren yineler; toplam beş uydurma.

Bir sayfa yalnızca kabul edilebilir bir başlıkla kabul edilir (bölüm 6.2).
Etiket okunmaz; bu yüzden başlığı olmayan bir sayfa (yalın ya da künyeli bir
belge, kısım 3) bu yolla tanınmaz. Künyesi kabul edilmiş bir sayfa hiçbir
zaman bu yolla okunmaz; böylece 6.1 bölümü geçerliliğini korur. Sonuç, normal
okuma yönteminin sonucu gibi aynen kapsayıcıya gider ve dosyayı yalnızca
parmak izi doğrular (bölüm 6.3). Bu yöntemdeki hiçbir şey biçimin parçası
değildir ve yöntem, 7.1 ile 7.5 arasındaki kod çözücünün sonuçlarını
değiştirmez.

Vektörler: `tests/vectors/c/decoder.json`, `tests/vectors/c/decoder_internals.json`
(bunlar biçimi değil, bu kod çözücünün belirlenmiş taramalardaki sonuçlarını
sabitler).

## 8. Tarihçe { #8-history }

Kısım 2'deki sayfa, Karel Kulhavy'nin 2007'de yazdığı ve 2012'den beri
`colindean/optar` adresinde bakımı yapılan C programı Twibright Optar'ın
biçimidir. Programın kaynak kodu, bu projenin `lega-c` klasöründe, o deponun
`9c8379c25466bf142459a26b0f34521bdde2af12` işlemesindeki hâliyle,
değiştirilmeden saklanır. `tests/vectors/c` içindeki vektörler o programdan,
`tests/vectors/py` içindekiler ise bu projeden kaydedilmiştir.

| Sürüm | Eklediği |
|---|---|
| C programı | sayfa (kısım 2); A4 ya da Letter derleme sırasında seçilir |
| 0.1.0 | aynı sayfalar, bu proje tarafından yazılır ve okunur |
| 0.2.0 | künye (kısım 3) |
| 0.3.0 | kapsayıcı, nokta boyutları ve düzenler (kısım 4 ve 5), sıfır dolguyla |
| 0.3.1 | dolgu akışı (bölüm 4.7) |

Biçimin C programından koruduğu şeyler:

- çerçeve, artı işaretleri, veri piksellerinin sırası ve serpiştirme;
- on iki yüzlüden kurulan Golay tablosu ve Hamming kodları;
- yazı tipi şeridi, etiket satırı ve onun üç tuhaflığı (bölüm 2.8);
- 9999 sayfa sınırı ve tek bir `1/0` sayfası olarak yazdırılan boş dosya;
- bir sayfanın kendi akışının uzunluğunu kaydetmemesi;
- iki `standard` düzenin ızgaraları ve Letter düzeninin kaydırmaları.
  C araçları A4 sayfasını 19.22 ve 17.44 pt konumuna yerleştiriyordu; bu
  konum tam yazıcı noktalarına denk gelmez; bu proje sayfayı 5.2 bölümündeki
  kaydırmalara yerleştirir.

C programında derlenmiş tek bir sayfa biçimi vardır. Programın kod çözücüsü
biçim dizesini argüman olarak alır ama yalnızca son alanı kullanır.

Etikette C programından bir fark kalmıştır: C programı etiket satırını bayt
olarak kısaltıyordu, bu biçim karakter olarak kısaltır. Satır kısaltılmıyorsa
ya da kısaltma noktasından önce ASCII dışında karakter içermiyorsa ikisi aynı
sayfayı verir.

C programından devralınan ve biçimin parçası olmayan kod çözücü davranışları
(kısım 7): 7.4 bölümündeki yedi sabit, piksel boyutunda bir köşenin iki kez
kullanılması, dik ve yüksekliği genişliğinden büyük bir sayfa gerektiren köşe
araması ve kod çözücü vektörlerinin sabitlediği 32 bitlik kayan noktalı
aritmetik.
