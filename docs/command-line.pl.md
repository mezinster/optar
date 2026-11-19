---
source_hash: fc438b9b7896988d42b22d54829293c774aa20c2
---

# Wiersz poleceń { #command-line }

Polecenie `optar` koduje plik na strony i dekoduje skany z powrotem do pliku.
Nie potrzebuje kompilatora C, biblioteki libpng ani programu ImageMagick.

    optar encode INPUT [-o BASE] [--paper a4|letter] [--to pdf|png|pgm] [--label TEXT] [--no-tag]
                 [--dots standard|medium|big|large|xlarge] [--protect none|standard|high]
                 [--compatible] [--format STRING]
    optar decode BASE [-o OUTPUT] [--paper a4|letter] [--format STRING] [--debug-images] [--force]
                 [--no-slow-reader]
    optar --version

## encode { #encode }

`encode` domyślnie zapisuje `BASE.pdf` (domyślne `BASE` to `optar_out`), a z
opcją `--to` – strony `BASE_0001.png` (lub `.pgm`), `BASE_0002.png`, ...

| Podajesz | Dostajesz |
|---|---|
| ani `--dots`, ani `--protect`, albo `--compatible` | wydruk, który odczytają wersja 0.2.0 i program w C: standardowe kropki, bez ochrony |
| samo `--dots X` | ten rozmiar kropek ze standardową ochroną |
| samo `--protect LEVEL` | standardowe kropki z tą ochroną |
| `--protect none` | bez ochrony |

Każdy z trzech ostatnich wariantów daje strony samoidentyfikujące (strony,
które same podają, do jakiego dokumentu należą i jaki mają numer); do ich
odczytu potrzebny jest optar 0.3 lub nowszy. Na przykład:

    optar encode photo.jpg -o photo --dots large --protect high

Rozmiary kropek i poziomy ochrony opisuje rozdział
[Zapisywanie pliku na papierze](put-on-paper.md#dot-size).

Wydruk zgodny ma na każdej stronie [znacznik](identification.md#the-tag);
dodaj `--no-tag`, by go pominąć.

Domyślna wartość `--paper` to A4.

## decode { #decode }

`decode` odczytuje `BASE_0001.png`, `BASE_0002.png`, ... i zapisuje dane do
`-o OUTPUT` albo na stdout. Odczytuje tylko pliki o takich nazwach.

To, co robi, zależy od wydruku. Rozstrzyga na podstawie pierwszych trzech
skanów: jeśli żadnego z nich nie da się zidentyfikować jako strony
samoidentyfikującej, traktuje zestaw jako wydruk z wersji 0.2.0 lub
wcześniejszej.

### Strony samoidentyfikujące { #self-identifying-pages }

`decode` ustala na podstawie samych skanów, czym one są.

- Przyjmuje skany w dowolnej kolejności i dowolnej orientacji.
- Skan, którego nie potrafi odczytać, liczy się jako brakująca strona.
- Skan, którego zwykła metoda odczytu nie potrafi zidentyfikować, najpierw
  trafia do [wolniejszej metody odczytu](slower-reader.md), chyba że podasz
  `--no-slow-reader`.
- Naprawia dane, przycina je do prawdziwego rozmiaru i sprawdza odcisk.
- Zapisuje plik tylko wtedy, gdy odcisk się zgadza, chyba że podasz
  opcję `--force`, która zapisuje to, co udało się odzyskać, nawet jeśli plik nie
  przeszedł weryfikacji. Nawet z `--force` nic nie zostaje zapisane, jeśli
  odczytano mniej niż połowę stron.

### Wydruki z wersji 0.2.0 lub wcześniejszych { #printouts-from-020-or-earlier }

- Wartość `--paper` musi być taka sama jak przy kodowaniu.
- Strona musi być we właściwym położeniu (pionowo, napis u dołu). Skany
  w poziomie nie są tu obsługiwane – to odziedziczone po dekoderze w C.
  Aplikacja okienkowa przyjmuje dowolną orientację dla każdego wydruku.
- `decode` nie przycina wyniku do rozmiaru ze znacznika i nie sprawdza
  odcisku: wynik jest zawsze dopełniony zerami do pełnej strony. Aplikacja
  okienkowa robi jedno i drugie. Jeśli twoje dane są na to wrażliwe, spakuj je
  programem tar.
- `--force` niczego nie zmienia i `decode` o tym informuje.

## Kod wyjścia { #exit-status }

| Kod | Znaczenie |
|---|---|
| 0 | Powodzenie. Dla stron samoidentyfikujących: plik przeszedł weryfikację. |
| 1 | Dane zdekodowano, ale są nie do skorygowania, albo w numeracji stron jest luka, albo (strony samoidentyfikujące) plik nie przeszedł weryfikacji. |
| 2 | Błąd użycia lub danych wejściowych. |

## Kod korekcyjny { #the-error-correcting-code }

Domyślny jest kod Golaya 24/12. Obsługiwane są też kody Hamminga rzędu od 2
do 5, wybierane opcją `--format` (szóste pole ciągu formatu).
[Specyfikacja formatu](format.md) definiuje ciąg formatu.
