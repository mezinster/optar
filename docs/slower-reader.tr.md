---
source_hash: e1aa7bf9091169288d65ca97a824f48d1c05c64e
---

# Çözünürlüğü çok düşük taramalar: yavaş okuma yöntemi { #scans-that-are-too-coarse-the-slower-reader }

0.4.0 sürümünden itibaren programda, nokta boyutlarına göre çok düşük
çözünürlükte yapılmış taramalar için ikinci, daha yavaş bir okuma yöntemi
vardır; örneğin standart noktalı bir sayfanın 600 yerine 300 dpi ile
taranması.

Yapabiliyorsanız önerilen çözünürlükte tarayın. Yavaş yöntem düşük
çözünürlüklü taramaların bir kısmını kurtarır, hepsini değil
([Neler gösterildi, neler gösterilmedi](evidence.md#the-slower-reader)
bölümüne bakın).

## Ne zaman çalışır { #when-it-runs }

İki durumda kendiliğinden çalışır:

- Normal okuma yöntemi bir taramayı tanıyamaz, ama içinde bir sayfanın dış
  hatlarını bulur.
- Düşük çözünürlüklü bir tarama (nokta başına 2,5 tarama pikselinden az)
  normal yönteme yalnızca künyesiz bir etiket verdi, başlık vermedi ve
  sayfanın verileri kötü okundu (sembollerinin %1'i ya da daha fazlası
  düzeltilemeyecek durumda). Böyle bir taramada veriler okunamazken etiket
  yine de okunabilir olabilir.

Verileri iyi okunan bir sayfa, başlığı olmayan eski bir sayfadır ve ona
dokunulmaz. Yavaş yöntem bir şey bulamazsa etiketten okunan sonuç korunur.

## Nasıl çalışır { #how-it-works }

Yavaş yöntem taramayı büyütür. Normal yöntemin emin olduğu noktalardan,
sayfanın her kısmında komşu noktaların birbirine nasıl karıştığını öğrenir.
Sonra bu bilgiyle her noktayı okur ve her sembolü bir bütün olarak seçer.

## Uygulamada { #in-the-application }

![Yavaş yöntemle okunan iki sayfa; düzeltilen noktalar işaretli](img/slow-pages.png)

*Üretilmiş, küçük ve çok düşük çözünürlükte taranmış bir test sayfası.
Düzeltilen noktalar önizlemede işaretlenmiştir.*

- Yavaş yöntem çalışırken taramanın satırı yavaş yöntemin adımını ve
  ilerlemesini gösterir. Satır seçildiğinde bunun yaklaşık bir dakika
  sürdüğü söylenir.
- Ardından satır, sayfanın yavaş yöntemle okunduğunu ve kaç noktanın
  düzeltildiğini söyler; örneğin “Sayfa 3 · Yavaş yöntemle okundu · 265.112
  nokta düzeltildi”. Düzeltilen nokta, tek başına okunan değeri sembolün
  bütün olarak seçilmesinde geçersiz kalan noktadır.
- Düzeltilen noktalar tarama önizlemesinde işaretlenir; her işaret bir nokta
  genişliğindedir. Düşük çözünürlüklü taramalarda bu çoğu zaman noktaların
  yüzde birkaçıdır; bu yüzden sayfaya bütün olarak bakıldığında düzeltmeler
  kadar yoğun bir renk tonu görünür. Yakınlaştırınca tek tek noktalar
  görünür.
- Belge doğrulandıktan sonra satıra, sayfanın kaç baytının belgenin
  korumasıyla onarıldığı eklenir (“· 6.912 bayt belgenin korumasıyla
  onarıldı”). Sayfa seçildiğinde iki sayı da gösterilir.

Böyle bir sayfaya hiçbir zaman “Sağlam” denmez ve alttaki çubukta ayrı
sayılır. Yavaş yöntem her sembol için en iyi tahminini verir; bu yüzden
sayfada neyin onarılamayacak durumda olduğunu söyleyemez.

## Komut satırında { #on-the-command-line }

`optar decode` da onu kendiliğinden çalıştırır ve denendiği her tarama için
bunu standart hata çıkışına (stderr) yazar. `--no-slow-reader` onu kapatır.

## Ne kadar sürer { #how-long-it-takes }

Geliştirme bilgisayarında bir A4 sayfa toplam 40 ila 70 saniye sürdü: normal
yöntemin vazgeçmesi için 20 ila 35 saniye, ardından yavaş yöntem için 20 ila
35 saniye.

Hiç optar sayfası olmayan, ama içinde bir sayfa dış hattı bulunan bir
görüntü, yavaş yöntem yokken sürdüğünden yaklaşık 20 ila 35 saniye daha
uzun sürer.

## Sınırlar { #limits }

- Bir sayfayı yalnızca verilerindeki başlıktan tanır. Etiketlerindeki
  künyeyle tanınan eski 0.2 tarzı sayfalar kapsanmaz.
- Künyesini normal yöntemin kabul ettiği bir sayfa yavaş yönteme asla
  verilmez.
- Yaklaşık 290 dpi ile taranmış standart noktalı bir sayfa için standart
  korumanın yetmeyeceği beklenir. Bu yolla kurtarılan tek gerçek belgede
  yüksek koruma vardı ve standart korumanın sağlayabileceğinden fazla onarım
  gerekti.
- Yanlış bir dosyayı doğruymuş gibi göstermez: her zaman olduğu gibi bir
  dosyayı doğrulanmış yapan yalnızca parmak izidir.
