---
source_hash: e97cf214a68552056382e38b7773d047576c8f46
---

# optar { #optar }

optar, bir dosyayı kâğıtta saklar. Dosyayı 600 dpi çözünürlüklü bir lazer
yazıcıda küçük siyah ve beyaz noktalardan oluşan sayfalar hâlinde yazdırır ve
dosyayı bu sayfaların taramalarından geri okur.

![İki sayfayı okuduktan sonra uygulama: ikisi de sağlam, dosya doğrulandı](img/verified.png)

- **Standart nokta boyutuyla bir A4 sayfaya yaklaşık 200.000 bayt sığar.**
- **Daha büyük noktalar** seçilebilir; böylece 200 dpi çözünürlüklü bir
  tarayıcı yeterli olur. Bu durumda bir sayfaya daha az veri sığar.
- **Koruma**, tüm sayfalara yayılmış ek veridir. Program bu veriyle lekeleri
  ve yırtık köşeleri onarır, yeterince uzun bir belgede de kaybolan bir
  sayfayı yeniden oluşturur.
- Dosyanın **parmak izi** dosyayla birlikte yazdırılır. Kurtarılan dosyaya
  yalnızca bu parmak iziyle eşleştiğinde doğrulanmış denir.

Aynı kodu kullanan iki program vardır:

- `optar-gui`: Linux, macOS ve Windows için bir masaüstü uygulaması;
- `optar`: bir komut satırı programı.

## Nereden başlamalı { #where-to-start }

| Ne yapmak istiyorsunuz | Okuyun |
|---|---|
| Programları edinmek | [Kurulum](install.md) |
| Bir dosyayı yazdırmak | [Dosyayı kâğıda yazma](put-on-paper.md) |
| Bir dosyayı çıktıdan geri almak | [Dosyayı geri okuma](read-from-paper.md) |
| Çok düşük çözünürlükte yapılmış taramaları okumak | [Çözünürlüğü çok düşük taramalar](slower-reader.md) |
| Programı betiklerden kullanmak | [Komut satırı](command-line.md) |
| Programa ne kadar güvenebileceğinizi bilmek | [Neler gösterildi, neler gösterilmedi](evidence.md) |
| Kendi okuyucu programınızı ya da kodlayıcınızı yazmak | [Biçim belirtimi](format.md) |

## Kısaca { #in-short }

1. Uygulamada “Kâğıda yaz” sekmesini açın, dosyayı seçin ve PDF'yi
   oluşturun.
2. PDF'yi 600 dpi çözünürlüklü bir lazer yazıcıda gerçek boyutunda (%100)
   yazdırın, “Sayfaya sığdır” ile değil.
3. Dosyayı geri almak için sayfaları gri tonlamalı olarak, nokta boyutunun
   gerektirdiği çözünürlükte (standart noktalar için 600 dpi) PNG ya da TIFF
   biçiminde tarayın.
4. “Kâğıttan oku” sekmesini açın, taramaları herhangi bir sırayla ekleyin ve
   alttaki çubuk dosyanın doğrulandığını söylediğinde dosyayı kaydedin.

## Nereden geliyor { #where-it-comes-from }

optar, 2007'de Twibright Labs'ten Karel 'Clock' Kulhavy tarafından C ile
yazıldı. Bu proje, aynı sayfaları okuyup yazan bir Python sürümüdür; buna
masaüstü uygulamasını, daha büyük noktaları, korumayı ve parmak izini ekler.
Ayrıntılar için [Tarihçe](history.md) bölümüne bakın.
