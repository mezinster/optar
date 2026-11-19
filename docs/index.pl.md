---
source_hash: e97cf214a68552056382e38b7773d047576c8f46
---

# optar { #optar }

optar przechowuje plik na papierze. Drukuje go na drukarce laserowej 600 dpi
jako strony z drobnych czarnych i białych kropek, a potem odczytuje plik
z powrotem ze skanów tych stron.

![Aplikacja po odczytaniu dwóch stron: obie w porządku, plik zweryfikowany](img/verified.png)

- **Jedna strona A4 mieści około 200 000 bajtów** przy standardowym rozmiarze
  kropek.
- **Większe kropki** można wybrać tak, by wystarczył skaner 200 dpi; strona
  mieści wtedy mniej.
- **Ochrona przed uszkodzeniami** to dodatkowe dane rozłożone na wszystkie
  strony. Dzięki niej program naprawia plamy i oderwane rogi, a w dostatecznie
  długim dokumencie odtwarza utraconą stronę.
- **Odcisk** pliku jest drukowany razem z nim. Odzyskany plik nazywa się
  zweryfikowanym tylko wtedy, gdy zgadza się z tym odciskiem.

Są dwa programy, które korzystają z tego samego kodu:

- `optar-gui` – aplikacja okienkowa dla systemów Linux, macOS i Windows;
- `optar` – program wiersza poleceń.

## Od czego zacząć { #where-to-start }

| Chcesz | Przeczytaj |
|---|---|
| Pobrać programy | [Instalacja](install.md) |
| Wydrukować plik | [Zapisywanie pliku na papierze](put-on-paper.md) |
| Odzyskać plik z wydruku | [Odczytywanie pliku](read-from-paper.md) |
| Odczytać skany wykonane w zbyt niskiej rozdzielczości | [Skany o zbyt niskiej rozdzielczości](slower-reader.md) |
| Używać programu w skryptach | [Wiersz poleceń](command-line.md) |
| Wiedzieć, na ile można mu ufać | [Co wykazano, a czego nie](evidence.md) |
| Napisać własny program odczytujący lub koder | [Specyfikacja formatu](format.md) |

## W skrócie { #in-short }

1. W aplikacji otwórz kartę „Zapisz na papierze”, wybierz plik i utwórz PDF.
2. Wydrukuj PDF w rozmiarze rzeczywistym (100%), a nie z opcją „Dopasuj do
   strony”, na drukarce laserowej 600 dpi.
3. Aby odzyskać plik, zeskanuj strony w skali szarości do formatu PNG lub
   TIFF, w rozdzielczości odpowiedniej dla rozmiaru kropek (600 dpi dla
   standardowych kropek).
4. Otwórz kartę „Odczytaj z papieru”, dodaj skany w dowolnej kolejności
   i zapisz plik, gdy pasek u dołu poda, że jest zweryfikowany.

## Skąd się wziął { #where-it-comes-from }

Program optar napisał w języku C Karel „Clock” Kulhavy z Twibright Labs
w 2007 roku. Ten projekt to wersja w Pythonie, która odczytuje i zapisuje te
same strony, a do tego dodaje aplikację okienkową, większe kropki, ochronę
i odcisk. Zob. rozdział [„Historia”](history.md).
