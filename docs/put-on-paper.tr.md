---
source_hash: bceb221e5e7d1915ae0d3656ce9713f5c5f1cdeb
---

# Dosyayı kâğıda yazma { #put-a-file-on-paper }

## Uygulamada { #in-the-application }

“Kâğıda yaz” sekmesini açın.

![Bir dosya seçilmiş “Kâğıda yaz” sekmesi](img/put-on-paper.png)

1. Bir dosya seçin ya da dosyayı sekmenin üzerine bırakın.
2. A4 ya da US Letter seçin.
3. [Nokta boyutunu](#dot-size) ve [korumayı](#protection) seçin. Pencere
   standart noktalar ve standart korumayla açılır.
4. Dosyaya bir ad verin. “Yazdırılacak ad:” satırı, her sayfaya yazdırılacak
   metni gösterir.
5. Altındaki satırı okuyun: dosyanın kaç sayfa gerektirdiğini ve koruma
   varsa bu sayfalardan kaçının kaybolabileceğini gösterir.
6. “PDF oluştur…” PDF'yi kaydeder.

“optar 0.2 ve özgün optar ile uyumlu” kutusu işaretlenirse bu eski
programların okuyabildiği bir çıktı oluşturulur. Bu çıktının noktaları
standart boyuttadır ve koruması yoktur.

Komut satırı için [`optar encode`](command-line.md#encode) bölümüne bakın.

## Yazdırma { #printing }

PDF'yi 600 dpi çözünürlüklü bir lazer yazıcıda gerçek boyutunda (%100)
yazdırın, “Sayfaya sığdır” ile değil. Mürekkep püskürtmeli yazıcılar test
edilmedi.

Gerçek boyutundan küçük çıkan bir çıktının noktaları da küçüktür ve daha zor
okunur. Gerçek bir çıktı, gerçek boyutun yaklaşık %95'i olarak ölçüldü.

## Nokta boyutu { #dot-size }

Nokta boyutu, her veri noktasının ne kadar büyük yazdırıldığıdır. Daha büyük
noktalar daha düşük çözünürlüklü bir taramaya da dayanır, ama bir sayfaya
bunlardan daha az sığar; bu yüzden sayfa daha az veri taşır. Bir veri
noktası, 600 dpi çözünürlüklü bir yazıcının 3, 4, 5, 6 ya da 9 noktasıdır.

Tablo, kullanılacak tarama çözünürlüğünü (veri noktası başına üç tarama
pikseli) ve koruma eklenmeden önce bir sayfanın taşıdığı bayt sayısını verir:

| Nokta boyutu | Seçenek | Veri noktası başına yazıcı noktası | Tarama çözünürlüğü | A4 sayfa | Letter sayfa |
|---|---|---|---|---|---|
| Standart | `standard` | 3 | 600 dpi | 199.773 | 192.591 |
| Orta | `medium` | 4 | 450 dpi | 114.904 | 110.463 |
| Büyük | `big` | 5 | 360 dpi | 73.027 | 69.463 |
| İri | `large` | 6 | 300 dpi | 49.119 | 48.403 |
| Çok iri | `xlarge` | 9 | 200 dpi | 21.606 | 21.127 |

Nokta boyutunu sayfaları okuyacak tarayıcıya göre seçin; bu okuma yıllar
sonra yapılabilir. Bilmiyorsanız daha büyük noktalar daha güvenli seçimdir.

## Koruma { #protection }

Koruma, belgenin tüm sayfalarına yayılmış ek veridir; program bu veriyle
hasarlı yerleri onarır ve kaybolan sayfaları yeniden oluşturur. Seçenekler
şunlardır: Yok, Standart ve Yüksek.

- Kâğıt ister: standart koruma yaklaşık %14, yüksek koruma yaklaşık %34 daha
  fazla sayfa ekler.
- Ek veri öyle yayılır ki bir leke, yırtık bir köşe ya da eksik bir sayfa,
  dosyanın her kısmından aşağı yukarı aynı küçük miktarı götürür. Korumanın
  onardığı da bu küçük miktardır.
- Koruma varsa sayfaların bir kısmı koruma verisini taşır ve her sayfa,
  hangi belgenin hangi sayfası olduğunu söyleyen kısa bir kaydı tekrarlar.
  Bu yüzden dosyaya yukarıdaki tabloda gösterilenden daha az yer kalır.

### Bütün bir sayfanın kaybolması { #losing-a-whole-page }

Pencere ve `optar encode`, kaybolan bir sayfanın kurtarılabileceğine yalnızca
yeterince uzun belgeler için söz verir ve bu durumda “T sayfadan N sayfa
kaybolsa da kurtarılabilir” der.

| Koruma | 1 sayfanın kaybolabileceği en kısa belge | 2 sayfanın kaybolabileceği en kısa belge |
|---|---|---|
| Standart | 12 sayfa | 24 sayfa |
| Yüksek | 6 sayfa | 12 sayfa |

Daha kısa belgelerde sayfa içindeki hasar onarılır, ama bütün bir sayfa
kaybolursa dosya da kaybolur. Bu söz bilerek temkinli tutulmuştur; bir
belgede söz verilenden fazlası kurtarılabilir.

### En büyük dosya { #the-largest-file }

Koruma eklenmiş çıktısı kâğıt üzerinde 256 MiB sınırını aşacak bir dosya
reddedilir. Pencere bu durumda dosyanın korumasız ya da daha küçük noktalarla
sığıp sığmayacağını söyler.

## Çıktıyı hangi programlar okuyabilir { #which-programs-can-read-the-printout }

| Çıktı | Okuyabilen |
|---|---|
| Standart dışında herhangi bir nokta boyutu ya da herhangi bir koruma | optar 0.3 ya da daha yeni bir sürüm. Okurken hiçbir şeyi ayarlamak gerekmez. |
| Standart noktalar, koruma yok, “uyumlu” kutusu işaretli | tüm sürümler ve C ile yazılmış özgün program |

0.2.0 uygulaması daha büyük noktalı sayfaları hiç okuyamaz. Standart
noktalarla ve koruma eklenerek yapılmış sayfalarda 0.2.0 ve C aracı dosyayı
değil, ek bilgilerle ve korumayla sarılmış veriyi döndürür.

Nedenleri
“[Sayfa kendini nasıl tanıtır](identification.md)” bölümünde açıklanmıştır.

!!! note "Uyumlu çıktıdaki dosyalar sıfırlarla tamamlanır"
    0.2 ve daha eski programlar için yapılmış bir çıktı, dosyanın uzunluğunu
    verilerinde saklamaz; uzunluk yalnızca etiketteki künyede bulunur. Komut
    satırındaki `optar decode` ve C aracı böyle bir dosyayı sıfırlarla tam
    bir sayfaya tamamlanmış olarak döndürür. Verileriniz buna duyarlıysa
    onları tar ile paketleyin.
