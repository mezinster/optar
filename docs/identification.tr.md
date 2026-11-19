---
source_hash: 2249212b8920c7b2d504e467f61c20e86e4b2d9d
---

# Sayfa kendini nasıl tanıtır { #how-a-page-identifies-itself }

Program, her tarama için onun hangi belgeye ait olduğunu ve kaçıncı sayfa
olduğunu bilmek zorundadır. Bir sayfa bunu, çıktının nasıl yapıldığına bağlı
olarak iki yoldan biriyle söyleyebilir.

| Çıktı | Neyle tanınır |
|---|---|
| Koruma eklenerek ya da standart dışında bir nokta boyutuyla yapılmış | sayfanın verilerindeki bir başlıkla (“kendini tanıtan sayfalar”) |
| 0.2.0 ya da daha yeni bir sürümün uyumlu çıktısı | alttaki etiketteki künyeyle |
| 0.1.0 ile ya da C aracıyla yapılmış | yalnızca etiketle; etiketin karşılaştırılabileceği hiçbir şey yoktur |

Etiketteki geçerli bir künye her zaman önceliklidir: etiketinde geçerli bir
künye bulunan sayfa, verileri ne içerirse içersin 0.2.0 sayfası olarak
okunur.

## Kendini tanıtan sayfalar { #self-identifying-pages }

Koruma eklenerek ya da standart dışında bir nokta boyutuyla yapılmış bir
çıktının sayfaları, belgenin bilgilerini verilerinde taşır: hangi çıktıya ait
oldukları, numaraları, sayfa sayısı, dosyanın boyutu ve parmak izi.

Altta yazdırılan etiket insanlar içindir ve sayfaları tanımak için
kullanılmaz. PDF'de, nokta boyutu ne olursa olsun tek bir boyutta (standart
bir sayfanın etiketinin boyutunda) yazdırılır; böylece satırın tamamı sığar.
Bu durumda düşük çözünürlüklü bir taramadan okunamayacak kadar küçüktür ve
pencere, dosya kurtarılıp kendi adı öğrenilene kadar “(adsız)” gösterir. PNG
ve PGM sayfalarında nokta başına bir piksel vardır; bu yüzden etiketleri
sayfanın noktalarıyla çizilir ve noktalarla birlikte büyür.

Böyle bir belgenin kullanmadığı yer, veriye benzeyen sabit bir desenle
doldurulur; böylece her sayfa eşit biçimde basılır. 0.3.0 sürümü bu yeri
sıfırlarla dolduruyordu ve bu, sayfalarda boydan boya beyaz çizgiler olarak
basılıyordu. İkisi de okunur, 0.3.0 tarafından da: hiçbir okuyucu program
dolguya bakmaz.

Bir sayfa başlığına kendi başına güvenilmez: taranmış tek bir sayfa
herhangi bir belgeye ait olduğunu iddia edebilir. Kurtarılan dosyayı
doğrulanmış yapan yalnızca parmak izidir.

## Etiket { #the-label }

Her sayfanın altında bir etiket vardır: sayfa biçimi, sayfa numarası ve
sayfa sayısı, ardından serbest metin. 0.2.0 ve önceki sürümlerin
çıktılarında uygulama bu etiketi taramadan okur.

- Künyeli bir etiket şu durumda kabul edilir: inandırıcı biçimde okunuyorsa,
  künyenin denetim değeri sayfa numarası ve sayfa sayısıyla eşleşiyorsa ve
  künyedeki dosya boyutu bu sayfa sayısına uyuyorsa.
- Künyesiz bir etiketin (0.1.0 ile ya da C aracıyla yapılmış çıktılar)
  karşılaştırılabileceği hiçbir şey yoktur; bu yüzden yalnızca açıkça
  okunduğunda kabul edilir.
- Tek bir karakteri hasarlı bir künyeye benzeyen etiket reddedilir.

Reddedilen bir tarama, nedeniyle birlikte “Okunamıyor” olarak listelenir ve
onu elle bir sayfaya atayabilirsiniz.

## Künye { #the-tag }

0.2.0 sürümünden itibaren `optar encode` ve uygulama, uyumlu bir çıktının
her sayfasındaki serbest metnin başına `[SIZE:FINGERPRINT:CC]` biçiminde bir
künye yazdırır.

| Kısım | Anlamı |
|---|---|
| `SIZE` | dosyanın bayt cinsinden boyutu |
| `FINGERPRINT` | dosyanın SHA-256 değerinin ilk 8 onaltılık basamağı |
| `CC` | sayfa numarasına ve sayfa sayısına bağlı, iki onaltılık basamaktan oluşan bir denetim değeri |

Künye sayesinde uygulama şunları yapabilir:

- farklı çıktıların sayfalarını birbirinden ayırmak;
- boyutu sayfa sayısına uymayan künyeli bir etiketi reddetmek;
- etiketi yanlış okunmuş bir taramayı yanlış sayfaya yerleştirmek yerine
  reddetmek (yaklaşık 256 yanlış okumadan 1'i yine de denetimden
  geçebilir);
- kurtarılan dosyayı gerçek boyutuna kesmek; böylece dosyada sıfır dolgusu
  kalmaz;
- kurtarılan dosyayı parmak iziyle karşılaştırmak; bu, dosyanın özgün dosya
  olduğuna dair son denetimdir.

Künyesiz yazdırmak için `optar encode --no-tag` kullanın. Kendini
verilerinden tanıtan sayfalara künye yazdırılmaz.

Kesin tanımlar [biçim belirtiminde](format.md) yer alır: künye için 3. kısım,
kendini tanıtan belgeler için 4. kısım.
