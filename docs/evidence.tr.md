---
source_hash: 34c3bf2795da00caec5ecf72aeb5391c9d6f4e57
---

# Neler gösterildi, neler gösterilmedi { #what-has-and-has-not-been-shown }

Bu bölüm, projenin iddialarının neye dayandığını anlatır. Bunların çoğu
kâğıttan değil, simüle edilmiş taramalardan gelir.

## Simüle edilmiş taramalar { #simulated-scans }

Otomatik testler bulanıklık, gürültü ve döndürme eklenmiş, üretilmiş
görüntüleri okur. Simüle edilen bulanıklık, yazdırılmış tek bir sayfanın tek
bir yazıcı ve tek bir sayfa beslemeli tarayıcıyla yapılmış üç gerçek 300 dpi
taramasına göre ayarlandı.

- Bu bulanıklıkta, 300 dpi ile taranan standart noktaların kodu normal okuma
  yöntemiyle çözülemedi.
- Orta noktalar standart korumayla 300 dpi ve 200 dpi ile doğrulandı.
- Büyük, iri ve çok iri noktalar 200 dpi ile hatasız doğrulandı.
- 12 sayfalık bir belge, bir sayfası dışarıda bırakılarak doğrulandı.

## Yavaş okuma yöntemi { #the-slower-reader }

[Yavaş okuma yöntemi](slower-reader.md) bir gerçek ve bir simüle edilmiş
belge üzerinde gösterildi.

**Gerçek.** Proje sahibinin altı A4 sayfalık belgesi: standart noktalar,
yüksek koruma; 600 dpi önerilirken yaklaşık 290 dpi ile taranmış. Normal
okuma yöntemi sayfaların hiçbirini tanımadı. Yavaş yöntemle dosya kurtarıldı
ve parmak iziyle doğrulandı: 759.879 bayt; bunun 41.495 baytı belgenin
korumasıyla onarıldı, en kötü blok 64'lük bütçesinin 40'ını kullandı. Bu,
tek bir belge, tek bir yazıcı, tek bir tarayıcı ve tek bir çözünürlüktür.
Taramalar deponun parçası değildir.

**Simüle edilmiş** (`tests/unit/test_coarse_claim.py`). Aynı türden iki
sayfalık bir belge, 1,8 yazıcı noktası bulanıklıkla 290 ve 300 dpi ile
taranmış. 290 dpi ile normal yöntem iki sayfayı da tanımıyor; 300 dpi ile her
sayfanın etiketini okuyor ama başlığını okuyamıyor. İki durumda da dosya
yavaş yöntemle doğrulanıyor. Simülatörün varsayılan bulanıklığında (1,0)
normal yöntem böyle bir sayfayı 300 dpi ile kendi başına okur.

Simülatör proje sahibinin tarayıcısından daha yumuşaktır: simülasyonda
290 dpi ile yavaş yöntem hiçbir şey onarmadı; gerçek belgede ise 41.495
baytın onarılması gerekti.

Standart korumanın bütçesi 32'dir; bu, gerçek belgenin en kötü bloğunun
ihtiyaç duyduğu 40'ın altındadır. Bu yüzden bu şekilde taranmış, standart
koruma eklenmiş bir belgenin başarısız olması beklenir. Eski 0.2 tarzı
sayfalar yavaş yöntemin kapsamında değildir.

## Neler gösterilmedi { #what-is-not-shown }

- Daha büyük noktalı bir sayfanın hiçbir gerçek taraması henüz okunmadı.
- Etiketlerin okunması ve kod çözme için otomatik testler yalnızca sentetik
  taramalarda var; gerçekten yazdırılıp taranmış sayfalarda yok. Daha büyük
  noktalı ya da koruma eklenmiş her çıktı buna dâhildir.
- Sayfa beslemeli tarayıcılar, programın üç gerçek taramada nokta ızgarasını
  bulmasının ötesinde test edilmedi.
- Bir çıktının üç gerçek 300 dpi taraması yaklaşık 286 dpi olarak ölçüldü;
  bu, o çıktının gerçek boyutun yaklaşık %95'i olarak basıldığı anlamına
  gelir. Küçük noktalar daha zor okunur; bu yüzden gerçek boyutunda (%100)
  yazdırın.
- Mürekkep püskürtmeli yazıcılar test edilmedi.

## C programıyla aynı sayfalar { #the-same-pages-as-the-c-program }

Python kodlayıcısının sayfaları, A4, Letter ve beş hata düzeltme modunun
tamamı için C ile yazılmış özgün `optar` programının çıktısıyla bayt bayt
aynıdır. Python kod çözücüsünün artı işareti konumları ve örneklenen bitleri,
sentetik test görüntülerinde C `unoptar` programınınkilerle bit bit aynıdır.
İkisi de C araçlarının bir kez kaydedilip `tests/vectors` içinde saklanan
çıktılarıyla karşılaştırılır.

Kendini tanıtan bir çıktının her sayfası yine sıradan bir optar sayfasıdır:
aynı ızgara boyutuyla derlenmiş bir C `unoptar` noktalarını tam olarak okur
(A4 kâğıtta iri noktalar ve Letter kâğıtta orta noktalar için kaydedildi). Döndürdüğü
şey dosya değil, dosyanın çevresine ek bilgiler ve koruma sarılmış veridir.
