---
source_hash: 116c27601de6c43ed57c443b775aafdc63d50d6c
---

# Format optar { #the-optar-format }

Normatywny jest angielski tekst tej specyfikacji, [The optar format](https://mezinster.github.io/optar/format/): format definiuje on wraz z wektorami testowymi w `tests/vectors`. To tłumaczenie ma charakter informacyjny; jeśli różni się od tekstu angielskiego, obowiązuje tekst angielski.

optar przechowuje plik na papierze w postaci stron z czarnych i białych kropek.
Niniejsza specyfikacja definiuje, czym jest strona i czym jest dokument (zbiór
stron, który niesie jeden plik), tak aby można było napisać koder, którego
strony ten projekt odczytuje, oraz dekoder, który odczytuje strony tego
projektu.

Specyfikacja składa się z ośmiu części:

1. Terminy i konwencje
2. Strona (wersja 0)
3. Znacznik dokumentu (wydruki 0.2.0)
4. Dokumenty samoidentyfikujące (wersja 1)
5. Drukowanie
6. Co musi robić program odczytujący
7. Dekoder referencyjny (informacyjnie)
8. Historia

Części od 1 do 6 są normatywne. Słowa „musi” (ang. *must*) używa się tylko
w odniesieniu do tego, czym jest strona lub dokument, a w części 6 – do tego,
co program odczytujący robi z tym, co odczytał. To, jak program odczytujący
znajduje stronę na skanie i ją próbkuje, nie należy do formatu; część 7
opisuje, jak robi to ten projekt.

Format jest ustalony przez wektory testowe w `tests/vectors`. Każda sekcja
normatywna kończy się wierszem „Wektory:”, który wymienia pliki ustalające tę
sekcję; to, jak odczytywać każdy z tych plików, opisuje
`tests/vectors/README.md`. Tabele poprzedzone komentarzem `spec-table` oraz
bloki kodu oznaczone `example` są porównywane z kodem przez
`tests/unit/test_spec.py`.

## 1. Terminy i konwencje { #1-terms-and-conventions }

### 1.1 Liczby, bity i bajty { #11-numbers-bits-and-bytes }

- Wszystkie liczby całkowite są zapisane dziesiętnie, chyba że mają przedrostek
  `0x`.
- `a // b` to dzielenie z zaokrągleniem w dół, `a mod b` – jego reszta,
  `ceil(a / b)` – dzielenie z zaokrągleniem w górę. Wszystkich trzech używa się
  tylko dla nieujemnych liczb całkowitych.
- Liczenie i indeksowanie zaczyna się od 0, z wyjątkiem numerów stron i ścian
  dwunastościanu z sekcji 2.5, które zaczynają się od 1.
- **Ciąg bitów** czyta się od najstarszego bitu: bit `n` ciągu bajtów to bit
  `7 - (n mod 8)` bajtu `n // 8`, przy czym bit 7 bajtu jest jego najstarszym
  bitem. Słowo o długości `w` bitów pobrane z ciągu bitów ma pierwszy bit tego
  ciągu jako swój najstarszy bit.
- Wielobajtowe liczby całkowite w nagłówku (sekcja 4.2) są zapisane
  w kolejności big-endian: najstarszy bajt pierwszy.
- SHA-256 i CRC-32 to standardowe funkcje. CRC-32 to funkcja z zlib, PNG
  i Ethernetu: odwrócony wielomian `0xEDB88320`, wartość początkowa i końcowy
  XOR `0xFFFFFFFF`.

### 1.2 Piksele i kolory { #12-pixels-and-colours }

- **Strona** to prostokątny obraz złożony z **pikseli strony**. Każdy piksel
  strony jest albo czarny, albo biały.
- Czarny piksel danych to bit 1; biały piksel danych to bit 0.
- W 8-bitowych plikach obrazów w skali szarości czarny piksel ma wartość 0,
  a biały – wartość 255. Ta specyfikacja nie używa żadnego innego kodowania
  obrazu.
- Współrzędne strony to `(x, y)`: `x` liczy kolumny od lewej krawędzi, `y`
  liczy wiersze od górnej krawędzi, oba od 0. Stronę drukuje się i odczytuje
  we właściwym położeniu, z pasem napisu (sekcja 2.8) u dołu.
- **Współrzędne obszaru danych** `(u, v)` pomijają ramkę (sekcja 2.2):
  `u = x - border`, `v = y - border`.

### 1.3 Jednostki { #13-units }

- **Punkt** (pt) to 1/72 cala.
- **Kropka drukarki** to 1/600 cala: jedna kropka drukarki 600 dpi, dla której
  zaprojektowano układy.
- **Kropka danych** to jeden piksel strony w postaci wydrukowanej. Jest
  kwadratem z całkowitej liczby kropek drukarki (sekcja 5.1). **Standardowa**
  kropka danych ma szerokość 3 kropek drukarki, 1/200 cala.

### 1.4 Rodzaje dokumentów { #14-kinds-of-document }

**Strumień** to ciąg bajtów, który strony dokumentu niosą w swoich pikselach
danych. Istnieją trzy rodzaje dokumentów; wszystkie trzy składają się z takich
samych stron w wersji 0 (część 2).

| Rodzaj | Zapisywany przez | Strumień to | Napis niesie |
|---|---|---|---|
| prosty | program w C, optar 0.1.0, `--no-tag` | plik | tylko tekst dowolny |
| ze znacznikiem | optar 0.2.0, a nowsze wersje jako swój wydruk „zgodny” | plik | znacznik (część 3) |
| samoidentyfikujący | optar 0.3.0 i nowsze | kontener (część 4) | tylko tekst dowolny |

### 1.5 Stałe { #15-constants }

Nazwy z tej tabeli są używane w całej specyfikacji.

<!-- spec-table: constants -->
| Nazwa | Wartość | Znaczenie |
|---|---|---|
| `PageFormat.version` | 0 | wersja formatu strony |
| `PageFormat.cpitch` | 24 | odległość między początkami krzyżyków, w pikselach strony |
| `PageFormat.chalf` | 3 | połowa boku krzyżyka, w pikselach strony |
| `PageFormat.fec_order` | 1 | kod strony: 1 to kod Golaya, od 2 do 5 – kody Hamminga |
| `PageFormat.border` | 2 | grubość ramki, w pikselach strony |
| `PageFormat.text_height` | 24 | liczba wierszy pasa napisu |
| `LABEL_HEIGHT` | 24 | jedyna wysokość pasa napisu, jaką można narysować |
| `TEXT_WIDTH` | 13 | szerokość jednej komórki znaku napisu, w pikselach napisu |
| `FIRST_CHAR` | 32 | kod znaku pierwszej komórki paska czcionki |
| `GLYPH_CELLS` | 95 | liczba komórek znaków w pasku czcionki |
| `MAX_PAGES` | 9999 | największa liczba stron jednego dokumentu |
| `FINGERPRINT_DIGITS` | 8 | liczba cyfr szesnastkowych odcisku w znaczniku |
| `CHECK_DIGITS` | 2 | liczba cyfr szesnastkowych wartości kontrolnej w znaczniku |
| `MAX_SIZE_DIGITS` | 12 | największa liczba cyfr dziesiętnych rozmiaru w znaczniku |
| `HEADER_MAGIC` | "oPt1" | pierwsze cztery bajty nagłówka, w ASCII |
| `CONTAINER_VERSION` | 1 | bajt wersji nagłówka |
| `HEADER_SIZE` | 38 | liczba bajtów jednej kopii nagłówka |
| `HEADER_COPIES` | 5 | liczba kopii nagłówka na każdej stronie |
| `FINGERPRINT_SIZE` | 16 | liczba bajtów odcisku w nagłówku |
| `CODEWORD` | 255 | liczba bajtów jednego słowa kodowego Reeda-Solomona |
| `SPREAD_STEP` | 7919 | krok rozproszenia (sekcja 4.6) |
| `NAME_MAX_BYTES` | 255 | największa liczba bajtów zapisanej nazwy pliku |
| `PADDING_KEY` | "optar padding" | klucz strumienia dopełnienia, w ASCII |
| `PADDING_BLOCK` | 32 | liczba bajtów jednego bloku strumienia dopełnienia |
| `PROTECTED_MAX_BYTES` | 268435456 | największa liczba bajtów stron dokumentu z parzystością |
| `PROMISE_NUM` | 3 | licznik udziału parzystości, na którym opiera się obietnica narzędzi (4.9) |
| `PROMISE_DEN` | 4 | mianownik tego udziału |
| `PRINTER_DPI` | 600 | kropki drukarki na cal |
| `PIXELS_PER_INCH` | 200 | standardowe kropki danych na cal |
| `STANDARD_PRINTER_DOTS` | 3 | kropki drukarki na szerokość standardowej kropki danych |
| `POINTS_PER_INCH` | 72 | punkty na cal |
| `SCAN_PIXELS_PER_DOT` | 3 | piksele skanu na kropkę danych przy zalecanej rozdzielczości skanowania |
| `MIN_MARGIN_PT` | 12 | najmniejszy margines wokół wydrukowanej strony, w punktach |

## 2. Strona (wersja 0) { #2-the-page-version-0 }

### 2.1 Format strony i ciąg formatu { #21-the-page-format-and-the-format-string }

**Format strony** to osiem nieujemnych liczb całkowitych:

| Pole | Nazwa | Znaczenie | Musi wynosić |
|---|---|---|---|
| 1 | `version` | wersja formatu strony | 0 |
| 2 | `xcrosses` | liczba krzyżyków w wierszu | co najmniej 2 |
| 3 | `ycrosses` | liczba krzyżyków w kolumnie | co najmniej 2 |
| 4 | `cpitch` | odległość między początkami krzyżyków | więcej niż `2 * chalf` |
| 5 | `chalf` | połowa boku krzyżyka | co najmniej 1 |
| 6 | `fec_order` | kod strony | od 1 do 5 |
| 7 | `border` | grubość ramki | co najmniej 1 |
| 8 | `text_height` | liczba wierszy pasa napisu | `LABEL_HEIGHT` |

**Ciąg formatu** to osiem pól w tej kolejności, zapisanych dziesiętnie bez zer
wiodących i połączonych znakiem `-`. Każda strona drukuje swój ciąg formatu
w swoim napisie (sekcja 2.8). Strony drukowane przez ten projekt różnią się
tylko polami `xcrosses` i `ycrosses`; pozostałe pola mają wartości z sekcji
1.5. Dziesięć formatów stron, które drukuje, wymieniono w sekcji 5.2. Inne
wartości dają ważne strony, które są odczytywane, gdy program odczytujący
otrzyma ciąg formatu.

Wszystkie poniższe rozmiary są podane w pikselach strony.

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

Nazwy z przedrostkiem `a4_` dotyczą formatu `0-65-93-24-3-1-2-24`,
standardowej strony A4.

Wektory: `tests/vectors/c/encoder_pages.json`.

### 2.2 Części strony { #22-the-parts-of-a-page }

Strona ma `width` kolumn i `height` wierszy. Od góry do dołu:

| Wiersze `y` | Zawartość |
|---|---|
| od `0` do `border - 1` | ramka: czarna |
| od `border` do `border + data_height - 1` | kolumny od `0` do `border - 1` i ostatnie `border` kolumn: czarne. Między nimi: **obszar danych**, `data_width` kolumn |
| od `border + data_height` do `border + data_height + text_height - 1` | **pas napisu**: czarny na całej szerokości, z napisem narysowanym na biało w kolumnach od `border` do `border + data_width - 1` (sekcja 2.8) |
| ostatnie `border` wierszy | ramka: czarna |

```example
a4_label_top_row = 2216
```

Każdy piksel obszaru danych jest albo częścią krzyżyka (sekcja 2.3), albo
pikselem danych (sekcja 2.4).

Wektory: `tests/vectors/c/encoder_pages.json`.

### 2.3 Krzyżyki { #23-crosses }

Obszar danych zawiera `xcrosses * ycrosses` **krzyżyków**, z których program
odczytujący korzysta, aby znaleźć piksele danych. Krzyżyk `(i, j)`,
`0 <= i < xcrosses`, `0 <= j < ycrosses`, to kwadrat `2 * chalf` na
`2 * chalf` pikseli, którego lewy górny piksel, jego **początek**, leży we
współrzędnych obszaru danych `(i * cpitch, j * cpitch)`. Jego cztery ćwiartki
o rozmiarze `chalf` na `chalf` pikseli to:

| Ćwiartka | Kolor |
|---|---|
| lewa górna | czarna |
| prawa górna | biała |
| lewa dolna | biała |
| prawa dolna | czarna |

Pierwszy krzyżyk dotyka lewego górnego rogu obszaru danych, a ostatni – jego
prawego dolnego rogu. Piksel `(u, v)` obszaru danych jest częścią krzyżyka
dokładnie wtedy, gdy `u mod cpitch < 2 * chalf` i `v mod cpitch < 2 * chalf`.

```example
a4_last_cross_x = 1538
a4_last_cross_y = 2210
```

Są to współrzędne strony `(x, y)` początku ostatniego krzyżyka.

Wektory: `tests/vectors/c/encoder_pages.json`.

### 2.4 Piksele danych i ich kolejność { #24-data-pixels-and-their-order }

**Piksele danych** to piksele obszaru danych, które nie są częścią krzyżyka.
Numeruje się je od 0 w kolejności czytania: wiersz po wierszu od góry,
a w obrębie wiersza od lewej do prawej. Numer piksela danych to jego
**pozycja w kanale**; `total_bits` to liczba pikseli danych.

Wiersze obszaru danych powtarzają się z okresem `cpitch`:

- **wąski pas** z `2 * chalf` wierszy, które przechodzą przez krzyżyki. Każdy
  wiersz zawiera `narrow_width` pikseli danych w `xcrosses - 1` przerwach
  szerokości `gap_width` pikseli między krzyżykami;
- **szeroki pas** z `gap_width` wierszy bez krzyżyków. Każdy wiersz zawiera
  `data_width` pikseli danych.

Ostatni okres ma tylko wąski pas.

    gap_width     = cpitch - 2 * chalf
    narrow_width  = gap_width * (xcrosses - 1)
    narrow_pixels = 2 * chalf * narrow_width
    wide_pixels   = gap_width * data_width
    rep_pixels    = narrow_pixels + wide_pixels
    total_bits    = rep_pixels * (ycrosses - 1) + narrow_pixels

Współrzędne obszaru danych `(u, v)` pozycji w kanale `n` to:

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

Współrzędne strony to `(u + border, v + border)`.

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

`a4_xy_of_N` to `u, v` pozycji w kanale `N`.

Wektory: `tests/vectors/c/bit_placement.json`.

### 2.5 Kod strony { #25-the-page-code }

Dane strony dzieli się na **słowa** po `small` bitów. Każde słowo koduje się
w **symbol** o długości `large` bitów, który można skorygować, gdy kilka jego
bitów zostanie odczytanych błędnie. `fec_order` wybiera kod:

| `fec_order` | Kod | `large` | `small` |
|---|---|---|---|
| 1 | kod Golaya (24, 12) | 24 | 12 |
| od 2 do 5 | rozszerzony kod Hamminga | `2 ^ fec_order` | `large - 1 - fec_order` |

```example
code_bits_of_order_1 = 24, 12
code_bits_of_order_2 = 4, 1
code_bits_of_order_3 = 8, 4
code_bits_of_order_4 = 16, 11
code_bits_of_order_5 = 32, 26
```

Symbol zapisuje się tutaj jako liczbę całkowitą o długości `large` bitów; jego
**bit `b`**, w kolejności, w jakiej bity są umieszczane na stronie, liczy się
od najstarszego bitu: bit 0 to bit o wartości `2 ^ (large - 1)`.

#### Kod Golaya (24, 12) { #golay-24-12 }

Symbol 12-bitowego słowa `d` to `d * 4096 + p(d)`: słowo w górnych 12 bitach,
pod nim 12 bitów parzystości. Bity parzystości pochodzą z dwunastościanu,
którego ściany są ponumerowane od 1 do 12. Ściana `f` odpowiada bitowi
o wartości `2 ^ (f - 1)` słowa `d`. Każda ściana ma pięć sąsiednich ścian:

<!-- spec-table: golay -->
| Ściana | Sąsiednie ściany | Maska |
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

Maska ściany `r` ma 1 dla każdej ściany, która nie sąsiaduje z `r` (łącznie
z samą ścianą `r`). Bit parzystości ściany `r` ma wartość 1, gdy `d AND mask`
ma nieparzystą liczbę bitów 1. Jest to bit o wartości `2 ^ (12 - r)`
w `p(d)`: ściana 1 daje najstarszy bit parzystości, ściana 12 – najmłodszy.

```example
golay_0x001 = 0x00183f
golay_0x800 = 0x800fc1
golay_0xabc = 0xabca13
golay_0xfff = 0xffffff
```

Kod jest liniowy, słowo 0 ma symbol 0, a każde dwa symbole różnią się co
najmniej 8 bitami. Dlatego dla symbolu odczytanego z co najwyżej 3 błędnymi
bitami istnieje dokładnie jeden symbol odległy od niego o nie więcej niż
3 bity – ten, który został wydrukowany. Plik wektorów ustala wszystkie 4096
symboli.

#### Rozszerzony kod Hamminga (`fec_order` od 2 do 5) { #extended-hamming-fec_order-2-to-5 }

Bity symbolu numeruje się według ich wartości: pozycja `q` to bit o wartości
`2 ^ q`, `0 <= q < large`.

1. Bity słowa, od najstarszego, trafiają na pozycje, które nie są ani 0, ani
   potęgą dwójki, od pozycji `large - 1` w dół.
2. Dla `i` od 0 do `fec_order - 1` pozycję `2 ^ i` ustawia się tak, aby
   pozycje, których numer ma ustawiony bit `i`, zawierały parzystą liczbę
   bitów 1.
3. Pozycję 0 ustawia się tak, aby cały symbol zawierał parzystą liczbę
   bitów 1.

Taki symbol można skorygować, gdy jeden bit jest błędny, a dwa błędne bity
zostają wykryte. Przy `fec_order` 2 symbol to jedyny bit słowa powtórzony
cztery razy.

```example
hamming_2_of_1 = 1111
hamming_3_of_1011 = 10101010
hamming_4_of_10000000001 = 1000000100011000
hamming_5_of_1 = 00000000000000000000000000001111
```

Każdy wiersz podaje słowo w zapisie binarnym po `of_` i jego symbol w zapisie
binarnym, od najstarszego bitu.

Wektory: `tests/vectors/c/golay.json`, `tests/vectors/c/encoder_pages.json`.

### 2.6 Symbole na stronie { #26-symbols-on-the-page }

Strona zawiera

    symbols   = total_bits // large
    used_bits = symbols * large
    net_bits  = symbols * small

`net_bits` to liczba bitów danych, które niesie strona. Symbole są przeplatane
tak, aby sąsiednie piksele należały do różnych symboli:

    bit b of symbol s is at channel position  s + b * symbols

dla `0 <= s < symbols` i `0 <= b < large`. Przy kodzie Golaya piksele danych
tworzą więc 24 kolejne grupy po `symbols` pikseli, a każdy symbol ma po jednym
pikselu w każdej grupie, w tym samym miejscu każdej z nich.

Piksele danych na pozycjach w kanale `used_bits` i wyższych nie należą do
żadnego symbolu i są białe.

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

Nazwy z `a4_medium_` dotyczą formatu `0-50-70-24-3-1-2-24`;
`hamming_N_net_bits` dotyczą siatki A4 z `fec_order` N.

Wektory: `tests/vectors/c/bit_placement.json`, `tests/vectors/c/encoder_pages.json`.

### 2.7 Od strumienia do stron { #27-from-a-stream-to-pages }

Niech strumień ma `nbytes` bajtów i będzie czytany jako ciąg bitów (sekcja
1.1).

    pages = ceil(8 * nbytes / net_bits)

Strona `p` (od 1) niesie bity strumienia od `(p - 1) * net_bits` do
`p * net_bits - 1`. Słowo `s` strony to `small` bitów zaczynających się od
bitu `s * small` bitów strony, a symbol `s` to jego kod (sekcja 2.5).

- Bity za końcem strumienia mają wartość 0. Ostatnie słowo, które zawiera bity
  strumienia, jest więc uzupełnione bitami 0 na najmłodszych pozycjach, a każde
  dalsze słowo ostatniej strony to 0. Symbol słowa 0 to 0, więc te słowa
  drukują się jako białe piksele.
- Dokument ma co najwyżej `MAX_PAGES` stron; dłuższego strumienia nie można
  zakodować.
- Pusty strumień (`nbytes = 0`) daje `pages = 0`. Drukuje się go jako jedną
  stronę, której wszystkie piksele danych są białe i której napis podaje numer
  strony 1 i liczbę stron 0 (`1/0`).

Odczytanie stron po kolei i połączenie ich `net_bits` bitów daje strumień, po
którym następują bity 0. Strona nie zapisuje, gdzie kończy się strumień:
dokument prosty zwraca swój plik dopełniony bajtami zerowymi do końca swojej
ostatniej strony (bez bitów, które nie wypełniają bajtu, gdy `net_bits` nie
jest wielokrotnością 8). Znacznik (część 3) i kontener (część 4) zapisują
rozmiar pliku.

```example
a4_pages_for_0_bytes = 0
a4_pages_for_1_byte = 1
a4_pages_for_199773_bytes = 1
a4_pages_for_199774_bytes = 2
a4_words_for_1000_bytes = 667
```

Strumień o długości 1000 bajtów wypełnia 667 słów pierwszej strony; ostatnie
z nich zawiera 8 bitów strumienia i cztery bity 0.

Wektory: `tests/vectors/c/encoder_pages.json`.

### 2.8 Napis { #28-the-label }

Pas napisu zawiera jeden wiersz tekstu, dla ludzi oraz, w dokumencie ze
znacznikiem, dla programu odczytującego. Zawsze rysuje się go tą samą
czcionką, którą definiuje opisany niżej pasek czcionki.

**Pasek czcionki** to obraz o `LABEL_HEIGHT` wierszach i 1500 kolumnach,
w którym każdy piksel jest czarny lub biały. Kolumny od `0` do
`TEXT_WIDTH * GLYPH_CELLS - 1` zawierają `GLYPH_CELLS` komórek znaków po
`TEXT_WIDTH` kolumn: komórka znaku o kodzie `c`, `32 <= c <= 126`, zaczyna się
w kolumnie `TEXT_WIDTH * (c - FIRST_CHAR)`. Pozostałe kolumny zawierają logo.
Glify i logo są białe na czarnym tle. Pasek to plik `src/optar/data/font.png`
tego projektu (jego piksel jest biały, gdy jego wartość szarości wynosi 128
lub więcej); jego skrót podany niżej to SHA-256 jego pikseli zapisanych jako
bajty 0 (czarny) i 255 (biały), wiersz po wierszu.

```example
strip_width = 1500
logo_width = 265
glyph_column_of_capital_a = 429
font_strip_sha256 = 481c0abd7884afb5ab6d958fbb95c0d6be97b0e2a7124f57e1abcd118d7d4bc4
```

**Wiersz napisu** strony `page` z `total` z tekstem dowolnym `text` to

    two spaces, the format string, a space, page, "/", total, a space, text

przy czym `page` i `total` są zapisane dziesiętnie bez zer wiodących. Spacja
po `total` występuje nawet wtedy, gdy `text` jest pusty. Następnie wiersz
obcina się do jego pierwszych `data_width // TEXT_WIDTH - 1` znaków (punktów
kodowych Unicode).

**Rysowanie.** Pas ma szerokość `data_width` kolumn, numerowanych od 0 od
kolumny strony `border`; wszystko, co nie zostało w nim narysowane, jest
czarne.

1. Jeśli `logo_width <= data_width`, logo kopiuje się do kolumn pasa od `0`
   do `logo_width - 1`.
2. Kursor zaczyna w kolumnie pasa `logo_width`, niezależnie od tego, czy logo
   zostało narysowane.
3. Dla każdego znaku obciętego wiersza, po kolei: znak o kodzie poniżej 32
   lub powyżej 127 jest pomijany. W przeciwnym razie, jeśli kursor plus
   `TEXT_WIDTH` wynosi co najwyżej `data_width`, `TEXT_WIDTH` kolumn paska
   zaczynających się od `TEXT_WIDTH * (code - FIRST_CHAR)` kopiuje się do pasa
   w miejscu kursora; w obu przypadkach kursor przesuwa się o `TEXT_WIDTH`.

Trzy konsekwencje, które koder musi odtworzyć, aby drukować takie same strony:

- Strona pokazuje co najwyżej `(data_width - logo_width) // TEXT_WIDTH`
  znaków, czyli mniej, niż wynosi długość, do której obcina się wiersz; reszta
  nie jest rysowana.
- Znaki spoza kodów od 32 do 127 nie zajmują komórki, ale wliczają się do
  długości, przy której obcina się wiersz.
- Kod 127 zajmuje komórkę i rysuje pierwsze `TEXT_WIDTH` kolumn logo. Takiego
  napisu nie można odczytać z powrotem.

```example
a4_label_line = "  0-65-93-24-3-1-2-24 3/7 backup.tar"
a4_label_characters = 117
a4_label_cells = 98
a4_xlarge_label_cells = 18
```

`a4_label_characters` to długość, do której obcina się wiersz,
a `a4_label_cells` – liczba znaków, które pokazuje strona. Strona formatu
`0-22-31-24-3-1-2-24` pokazuje 18 znaków, mniej, niż liczy jej ciąg formatu;
sekcja 5.4 opisuje, jak takie strony otrzymują napis na wydruku.

Wektory: `tests/vectors/c/label.json`, `tests/vectors/c/encoder_pages.json`.

## 3. Znacznik dokumentu (wydruki 0.2.0) { #3-the-document-tag-020-printouts }

Dokument prosty nie mówi, jak długi jest jego plik, które strony tworzą jedną
całość ani czy plik został odczytany poprawnie. **Dokument ze znacznikiem**
mówi to w tekście dowolnym każdego napisu. Jego strumieniem jest sam plik,
więc jego strony odczytują także programy, które nic nie wiedzą o znaczniku.

### 3.1 Znacznik { #31-the-tag }

Dla pliku o rozmiarze `size` bajtów:

- `SIZE` to `size` zapisany dziesiętnie bez zer wiodących (`0` dla pustego
  pliku), najwyżej `MAX_SIZE_DIGITS` cyfr;
- `FINGERPRINT` to pierwsze `FINGERPRINT_DIGITS` znaków skrótu SHA-256 pliku
  w zapisie szesnastkowym małymi literami;
- `CHECK` dla strony `page` z `total` to pierwsze `CHECK_DIGITS` znaków skrótu
  SHA-256 tekstu ASCII `SIZE:FINGERPRINT:page/total` w zapisie szesnastkowym
  małymi literami, przy czym `page` i `total` są zapisane tak jak w wierszu
  napisu.

Znacznik strony to tekst `[SIZE:FINGERPRINT:CHECK]`. Tekst dowolny napisu
strony to znacznik albo znacznik, jedna spacja i nazwa. `SIZE`
i `FINGERPRINT` są takie same na każdej stronie dokumentu; `CHECK` jest różny
na różnych stronach.

Pusty plik to jedna strona z napisem `1/0` (sekcja 2.7); jego wartość
kontrolną oblicza się dla `page` 1 i `total` 0.

```example
tag_fingerprint_of_x = 2d711642
tag_check_input = "1:2d711642:1/1"
tag_check_of_x_page_1_of_1 = ca
tag_free_text = "[1:2d711642:ca] name.tar"
tag_of_empty_file = "[0:e3b0c442:e0]"
```

Pierwsze cztery wiersze dotyczą jednobajtowego pliku `x` wydrukowanego
z nazwą `name.tar`.

Wektory: `tests/vectors/py/tag.json`.

### 3.2 Kiedy znacznik jest ważny { #32-when-a-tag-is-valid }

Tekst dowolny napisu **zaczyna się od znacznika**, gdy zaczyna się od `[`,
rozmiaru jak wyżej, `:`, dokładnie 8 znaków z `0-9a-f`, `:`, dokładnie
2 znaków z `0-9a-f` i `]`, a po znaczniku następuje spacja albo koniec
tekstu.

Znacznik odczytany ze strony `page` z `total` w formacie strony `F` jest
**ważny**, gdy spełnione są oba warunki:

- jego wartość kontrolna jest równa wartości kontrolnej obliczonej z
  odczytanych rozmiaru, odcisku, `page` i `total`;
- rozmiar pasuje do liczby stron: `size = 0` i `total = 0` albo `size > 0`,
  `total > 0` i `(total - 1) * capacity < size <= total * capacity`, gdzie
  `capacity = net_bits // 8` formatu `F`.

W dwóch układach `standard` (sekcja 5.2) `net_bits` jest wielokrotnością 8,
więc rozmiar pasuje dokładnie do tej liczby stron, którą przypisuje mu sekcja
2.7. Program odczytujący tego projektu identyfikuje strony po znaczniku tylko
w tych dwóch układach.

Wektory: `tests/vectors/py/tag.json`.

## 4. Dokumenty samoidentyfikujące (wersja 1) { #4-self-identifying-documents-version-1 }

**Dokument samoidentyfikujący** niesie w danych każdej strony nagłówek, który
mówi, do jakiego dokumentu należy strona i którą jest stroną, i może nieść
parzystość, dzięki której naprawia się uszkodzone strony i odtwarza
brakujące. Plik, jego nazwę i parzystość pakuje się w strumień, **kontener**,
a ten strumień drukuje się jako zwykłe strony w wersji 0 (część 2). Wersja 1
to wersja kontenera; format strony zachowuje wersję 0.

### 4.1 Rozmiary { #41-sizes }

Dla formatu strony `F`, poziomu parzystości `parity` (sekcja 4.4) i liczby
stron `T`:

    page_bytes = net_bits // 8                         payload of one page
    page_body  = page_bytes - HEADER_COPIES * HEADER_SIZE
    k          = CODEWORD - parity                     data bytes of a codeword
    m(T)       = T * page_body // CODEWORD             codewords
    D(T)       = m(T) * k                              bytes of the data region

**Ładunek** strony to jej pierwsze `page_bytes * 8` bitów danych w postaci
bajtów. **Treść** strony to jej ładunek bez kopii nagłówka (sekcja 4.3),
`page_body` bajtów. **Treść dokumentu** to połączone treści stron od 1 do `T`,
`T * page_body` bajtów.

Format strony może nieść kontener tylko wtedy, gdy
`page_bytes // HEADER_COPIES >= HEADER_SIZE`.

```example
a4_page_bytes = 199773
a4_page_body = 199583
```

Wektory: `tests/vectors/py/container.json`.

### 4.2 Nagłówek { #42-the-header }

Nagłówek ma `HEADER_SIZE` bajtów:

<!-- spec-table: header-fields -->
| Przesunięcie | Rozmiar | Pole | Typ | Zawartość |
|---|---|---|---|---|
| 0 | 4 | `magic` | bajty | `HEADER_MAGIC` |
| 4 | 1 | `version` | liczba całkowita | `CONTAINER_VERSION` |
| 5 | 1 | `parity` | liczba całkowita | liczba bajtów parzystości na słowo kodowe: 0, 32 lub 64 |
| 6 | 2 | `page` | liczba całkowita | numer tej strony, od 1 |
| 8 | 2 | `total` | liczba całkowita | liczba stron dokumentu |
| 10 | 8 | `size` | liczba całkowita | rozmiar pliku w bajtach |
| 18 | 16 | `fingerprint` | bajty | pierwsze `FINGERPRINT_SIZE` bajtów skrótu SHA-256 pliku |
| 34 | 4 | `crc` | liczba całkowita | CRC-32 bajtów od 0 do 33 |

Liczby całkowite są zapisane w kolejności big-endian. Wszystkie pola oprócz
`page` (a wraz z nim `crc`) są takie same na każdej stronie dokumentu.

```example
header_bytes = 6f5074310140000300070000000000086e3c000102030405060708090a0b0c0d0e0f1ef0ca9d
header_crc = 0x1ef0ca9d
```

To jest nagłówek strony 3 z 7 pliku o rozmiarze 552508 bajtów z parzystością
64, którego odcisk to bajty od `00` do `0f`.

Wektory: `tests/vectors/py/container.json`.

### 4.3 Ładunek strony { #43-the-payload-of-a-page }

Kopia `c` nagłówka strony, `0 <= c < HEADER_COPIES`, zajmuje bajty ładunku

    c * (page_bytes // HEADER_COPIES)   to   c * (page_bytes // HEADER_COPIES) + HEADER_SIZE - 1

Pozostałe bajty ładunku, po kolei, tworzą treść strony.

```example
a4_header_offsets = 0, 39954, 79908, 119862, 159816
```

Wektory: `tests/vectors/py/container.json`.

### 4.4 Poziomy parzystości { #44-parity-levels }

<!-- spec-table: parity -->
| Nazwa | Bajty parzystości | Bajty danych |
|---|---|---|
| none | 0 | 255 |
| standard | 32 | 223 |
| high | 64 | 191 |

„Bajty parzystości” to pole nagłówka `parity`; „Bajty danych” to `k`. Dokument
z parzystością 0 ma nagłówki i nazwę, ale nic nie jest naprawiane.

Wektory: `tests/vectors/py/container.json`.

### 4.5 Kod Reeda-Solomona { #45-the-reed-solomon-code }

**Słowo kodowe** ma `CODEWORD` bajtów: `k` bajtów danych, po których następuje
`parity` bajtów parzystości.

- Bajty są elementami GF(256) z wielomianem ciała
  `x^8 + x^4 + x^3 + x^2 + 1` (`0x11D`): bajt to wielomian nad GF(2), którego
  współczynnik przy `x^7` jest jego najstarszym bitem, dodawanie to XOR,
  a mnożenie to mnożenie wielomianów modulo wielomian ciała.
- `alpha` to element `0x02`.
- Wielomian generujący to
  `g(x) = (x - alpha^0)(x - alpha^1) ... (x - alpha^(parity - 1))`.
- Bajt `i` słowa kodowego, `0 <= i <= 254`, to współczynnik przy
  `x^(254 - i)` wielomianu słowa kodowego `c(x)`.
- Bajty danych to współczynniki od `x^254` w dół do `x^parity`. Bajty
  parzystości dobiera się tak, aby `g(x)` dzielił `c(x)`: są one resztą
  z dzielenia wielomianu danych (z zerowymi współczynnikami poniżej
  `x^parity`) przez `g(x)`, począwszy od współczynnika przy `x^(parity - 1)`.

Słowo kodowe można naprawić, gdy `2 * e + f <= parity`, gdzie `f` to liczba
jego bajtów, o których wiadomo, że są nieczytelne (wymazania), a `e` – liczba
pozostałych bajtów, które są błędne.

```example
gf_alpha_8 = 0x1d
gf_alpha_254 = 0x8e
rs_32_parity_of_one = 744034ae367e10c2a221219db0c5e10c3b37fde4942fb3b9188afd148e37ac58
rs_32_parity_of_counting = 41841183b11fdb537421939696cda70e1db5c86684af222564b89cc6069f172e
```

`rs_32_parity_of_one` to, dla parzystości 32, bajty parzystości 223 bajtów
danych, które wszystkie są zerowe z wyjątkiem ostatniego bajtu równego 1; są
to współczynniki `g(x)` od `x^31` w dół do `x^0`. `rs_32_parity_of_counting`
to, dla parzystości 32, bajty parzystości bajtów danych 0, 1, 2, ..., 222.

Wektory: `tests/vectors/py/reed_solomon.json`.

### 4.6 Strefa danych i rozproszenie { #46-the-data-region-and-the-spread }

**Strefa danych** ma `D(T)` bajtów:

| Bajty | Zawartość |
|---|---|
| `size` | plik |
| 1 | `L`, długość nazwy w bajtach, od 0 do `NAME_MAX_BYTES` |
| `L` | nazwa pliku w UTF-8 |
| reszta | dopełnienie (sekcja 4.7) |

Nazwę dłuższą niż `NAME_MAX_BYTES` bajtów w UTF-8 obcina się do największej
całkowitej liczby znaków, która się mieści. Nazwa nie jest objęta odciskiem.
Znak nazwy, którego UTF-8 nie potrafi zakodować (samotny punkt kodowy
surogatu, od U+D800 do U+DFFF), zapisuje się jako `?`.

Słowo kodowe `j`, `0 <= j < m`, ma jako bajty danych bajty strefy danych od
`j * k` do `j * k + k - 1`. Przy parzystości 0 słowo kodowe to jego 255 bajtów
danych.

**Rozproszenie.** Bajt `i` słowa kodowego `j` to bajt treści dokumentu na
pozycji

    i * m + (j + i * SPREAD_STEP) mod m

Bajt `i` każdego słowa kodowego leży więc w wycinku treści od `i * m` do
`(i + 1) * m - 1`, a 255 bajtów jednego słowa kodowego leży w 255 różnych
wycinkach, rozproszonych po całym dokumencie: uszkodzenie w jednym miejscu
kosztuje każde słowo kodowe kilka bajtów, zamiast kosztować kilka słów
kodowych wszystko.

Ostatnie `T * page_body - CODEWORD * m` bajtów treści (mniej niż `CODEWORD`)
nie należy do żadnego słowa kodowego i stanowi dopełnienie.

Wektory: `tests/vectors/py/container.json`.

### 4.7 Dopełnienie { #47-padding }

Dopełnienie nic nie niesie. Istnieją dwa warianty jego zawartości i oba są
ważne:

- optar 0.3.0 zapisywał bajty zerowe;
- optar 0.3.1 i nowsze zapisują **strumień dopełnienia**: jego blok `n`,
  `n = 0, 1, 2, ...`, to `PADDING_BLOCK` bajtów skrótu SHA-256 ciągu
  złożonego z `PADDING_KEY` i następującego po nim `n` zapisanego jako
  8 bajtów w kolejności big-endian; strumień to połączone bloki. Dopełnienie
  strefy danych to strumień od jego bajtu 0; dopełnienie na końcu treści
  kontynuuje strumień tam, gdzie zatrzymało się dopełnienie strefy danych.
  (Bajty zerowe drukują się jako białe linie w poprzek każdej strony;
  strumień drukuje się jak dane).

Dokument, którego dopełnienie jest czymkolwiek innym, nadal jest dla programu
odczytującego ważnym dokumentem (sekcja 6.4), ale tylko strumień dopełnienia
daje strony, które drukuje ten projekt.

```example
padding_block_0 = d518824e181c15b2f69e390066efbfa00d73eb8f0c3d932313396940eedd1286
padding_bytes_30_to_33 = 12863e00
```

Wektory: `tests/vectors/py/container.json`.

### 4.8 Liczba stron i ograniczenia { #48-the-page-count-and-the-limits }

Dokument ma najmniejszą liczbę stron, która mieści plik, bajt długości
i nazwę:

    need = size + 1 + L
    T    = the smallest T >= 1 with D(T) >= need

Ograniczenia są następujące:

- `T <= MAX_PAGES`;
- przy `parity > 0`: `T * page_bytes <= PROTECTED_MAX_BYTES`;
- `size < 2^64`, `L <= NAME_MAX_BYTES`.

Pliku, który wymaga więcej, nie można umieścić w dokumencie.

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

Przykład dotyczy pliku o rozmiarze 1000000 bajtów o nazwie `vector.bin` na
standardowych stronach A4 z parzystością 32. Wymaga on 4485 słów kodowych;
pięć stron mieści ich mniej, a sześć mieści `m = 4696`. Dokument ma wszystkie
4696 słów kodowych; te, których plik nie potrzebuje, zawierają dopełnienie.
`plan_spare_bytes` to dopełnienie na końcu treści,
a `plan_padding_in_region` – dopełnienie strefy danych. Pozycje to pozycje
w treści dokumentu (sekcja 4.6).

Wektory: `tests/vectors/py/container.json`.

### 4.9 Co wytrzymuje dokument (informacyjnie) { #49-what-the-document-withstands-informative }

Utracona strona kosztuje słowo kodowe co najwyżej `ceil(page_body / m) + 1`
bajtów. Ten projekt mówi swojemu użytkownikowi, że można utracić dowolne `n`
stron, gdy
`n * (ceil(page_body / m) + 1) <= PROMISE_NUM * parity // PROMISE_DEN`, co
pozostawia ćwierć parzystości na uszkodzenia na stronach, które pozostały.
Jest to obietnica narzędzi: nie jest to ani właściwość, na której program
odczytujący może polegać, ani taka, którą program odczytujący musi sprawdzać.

### 4.10 Od kontenera do stron { #410-from-the-container-to-pages }

Strumień ma `T * net_bits // 8` bajtów. Gdy czyta się go jako ciąg bitów,
ładunek strony `p` (od 1) zaczyna się od bitu `(p - 1) * net_bits`; każdy bit
strumienia, który nie leży w żadnym ładunku, ma wartość 0. Gdy `net_bits` jest wielokrotnością 8, strumień
to po prostu połączone ładunki. Gdy nie jest, każda strona ma `net_bits mod 8`
niewykorzystanych bitów po swoim ładunku, a ładunki niektórych stron nie
zaczynają się na początku bajtu strumienia.

Strumień drukuje się tak, jak opisuje sekcja 2.7, co daje dokładnie `T` stron.
Napis strony to zwykły wiersz napisu, którego tekst dowolny jest przeznaczony
dla ludzi: jest to napis podany przez użytkownika albo, gdy go nie podano,
nazwa, którą wybiera narzędzie (okno używa nazwy pliku, wiersz poleceń – nazwy
podanej w `-o`, która może być pusta). Tekst ten jest taki sam na każdej
stronie i nie zawiera znacznika. (Ważny
znacznik sprawiłby, że program odczytujący uznałby stronę za stronę dokumentu
ze znacznikiem, sekcja 6.1).

Przy kodzie Golaya `net_bits mod 8` wynosi 0 lub 4, a ostatni ładunek zawsze
kończy się w obrębie strumienia. Ten projekt drukuje dokumenty
samoidentyfikujące tylko w dziesięciu formatach stron z sekcji 5.2, a jego
program odczytujący szuka nagłówków tylko w tych formatach.

```example
a4_medium_stream_bytes_for_3_pages = 344713
a4_medium_page_2_starts_at = 114904, 4
a4_medium_page_3_starts_at = 229809, 0
```

Strona formatu `0-50-70-24-3-1-2-24` ma `net_bits = 919236`, co pozostawia
4 bity po jej 114904 bajtach ładunku. Te dwie wartości to bajt strumienia,
w którym zaczyna się ładunek strony, i bit w tym bajcie (0 to najstarszy).

Wektory: `tests/vectors/py/container.json`, `tests/vectors/c/container_pages.json`.

## 5. Drukowanie { #5-printing }

### 5.1 Rozmiary kropek { #51-dot-sizes }

Stronę drukuje się z jednym z pięciu rozmiarów kropek. Kropka danych jest
kwadratem z całkowitej liczby kropek drukarki, tak aby każdy piksel strony
drukował się jako ten sam kwadrat kropek drukarki.

<!-- spec-table: dot-sizes -->
| Nazwa | Kropki drukarki na kropkę danych | Kropki danych na cal | Rozmiar kropki (pt) | Zalecany skan (dpi) |
|---|---|---|---|---|
| standard | 3 | 200 | 0.36 | 600 |
| medium | 4 | 150 | 0.48 | 450 |
| big | 5 | 120 | 0.6 | 360 |
| large | 6 | 100 | 0.72 | 300 |
| xlarge | 9 | 200/3 | 1.08 | 200 |

Zalecana rozdzielczość skanowania daje `SCAN_PIXELS_PER_DOT` pikseli skanu na
kropkę danych. Jest to zalecenie; strona jest tą samą stroną przy każdej
rozdzielczości skanowania.

### 5.2 Układy { #52-layouts }

**Układ** to papier, rozmiar kropek i format strony drukowany na nim. Jest ich
dziesięć. Papiery mają nazwy `a4` i `letter`.

<!-- spec-table: layouts -->
| Papier | Kropki | Krzyżyki w poziomie | Krzyżyki w pionie | Ciąg formatu | Szerokość (px) | Wysokość (px) | Bity netto | Bajty strony | Bajty treści |
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

„Bajty strony” i „Bajty treści” to `page_bytes` i `page_body` z sekcji 4.1.
Ten projekt drukuje dokument prosty lub ze znacznikiem w układzie `standard`
(albo, gdy ręcznie podano ciąg formatu, w tym formacie strony ze standardowym
rozmiarem kropek i z przesunięciami układu `standard` danego papieru; taki
ciąg formatu ten projekt odrzuca, chyba że każdy margines wynosi wtedy co
najmniej `MIN_MARGIN_PT`), a dokument
samoidentyfikujący – w dowolnym z dziesięciu układów.

Wektory: `tests/vectors/c/bit_placement.json`, `tests/vectors/py/container.json`.

Obraz strony umieszcza się na papierze tak, aby jego lewy dolny róg leżał
w miejscu określonym przez poniższe przesunięcia, mierzone od lewego dolnego
rogu papieru. Marginesy to to, co pozostaje z każdego boku.

<!-- spec-table: layouts -->
| Papier | Kropki | Szerokość papieru (pt) | Wysokość papieru (pt) | Przesunięcie x (pt) | Przesunięcie y (pt) | Lewy (mm) | Dolny (mm) | Prawy (mm) | Górny (mm) |
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

Każde przesunięcie to całkowita liczba kropek drukarki, więc krawędzie obrazu
wypadają na kropkach drukarki. Siatki i przesunięcia dwóch układów `standard`
są odziedziczone (część 8). Pozostałe osiem jest wyprowadzonych: siatka to
największe `xcrosses` i `ycrosses`, przy których strona, przy swoim rozmiarze
kropek, pozostawia co najmniej `MIN_MARGIN_PT` z każdego boku, a każde
przesunięcie to połowa wolnej długości, zaokrąglona w dół do całkowitej
liczby kropek drukarki. Układy definiują tabele, a nie ta reguła.

Strona jest tą samą stroną niezależnie od tego, gdzie leży na papierze: program
odczytujący znajduje stronę po jej ramce. Umieszczenie ma znaczenie tylko dla
drukowania: strona wydrukowana w innej skali ma kropki innego rozmiaru,
a strona wydrukowana bliżej krawędzi może zostać przycięta.

### 5.3 PDF zapisywany przez ten projekt { #53-the-pdf-this-project-writes }

Każda strona dokumentu to jedna strona PDF, której pole nośnika (media box)
to papier: `[0 0 width height]`, gdzie szerokość i wysokość papieru podano
w punktach. Obraz strony to jeden obraz
o 1 bicie na piksel (1 to biały), `width` na `height` pikseli strony, bez
interpolacji, narysowany tak, aby jego lewy dolny róg leżał w miejscu
przesunięć układu, i przeskalowany tak, aby jeden piksel strony był jedną
kropką danych:

    image width in points  = width  * dot size in points
    image height in points = height * dot size in points

```example
a4_large_image_width_pt = 560.16
a4_large_image_height_pt = 802.08
```

PDF jest przeznaczony do drukowania w rozmiarze rzeczywistym (100%). Żaden
wektor nie ustala PDF; robi to `tests/unit/test_pdf.py`.

Obrazy stron zapisuje się też jako pliki PNG lub PGM z jednym pikselem obrazu
na piksel strony; wektory identyfikują stronę po skrócie SHA-256 jej
binarnego pliku PGM (`P5`), którego dokładne bajty podaje
`tests/vectors/README.md`: nagłówek `P5\n<width> <height>\n255\n`
w ASCII, a następnie bajty pikseli wiersz po wierszu.

### 5.4 Pasek napisu { #54-the-label-strip }

Napis rysuje się w pikselach strony (sekcja 2.8), więc na stronie z większymi
kropkami mieści on mniej znaków: przy największych za mało nawet na własny
ciąg formatu. Dlatego w PDF napis strony z układu, którego rozmiar kropek nie
jest `standard`, zastępuje się **paskiem napisu**, drugim obrazem rysowanym
standardowymi kropkami danych:

- pasek ma `LABEL_HEIGHT` wierszy i
  `floor(data_width * printer dots per data dot / STANDARD_PRINTER_DOTS)`
  kolumn pikseli paska;
- zawiera wiersz napisu strony, obcięty i narysowany jak w sekcji 2.8,
  z szerokością paska zamiast `data_width`;
- w obrazie strony pas napisu staje się czarny w kolumnach od `border` do
  `border + data_width - 1`;
- pasek rysuje się na pasie w skali 0.36 pt na piksel paska, z lewą krawędzią
  przy lewej krawędzi kolumn danych pasa i wyśrodkowany względem wysokości
  pasa.

Od strony z części 2 różni się tylko pas napisu; obszar danych i ramka
pozostają nietknięte. Strona PNG lub PGM takiego układu zachowuje napis
z sekcji 2.8. Napis strony samoidentyfikującej nie służy do jej identyfikacji
(sekcja 6.2), więc program odczytujący nie musi odczytywać paska.

```example
a4_large_strip_width = 1548
a4_large_strip_characters = 118
a4_large_strip_width_pt = 557.28
```

Wektory: `tests/vectors/c/container_pages.json` ustala strony dwóch układów
z większymi kropkami jako zwykłe strony; pasek ustalają
`tests/unit/test_font.py` i `tests/unit/test_pdf.py`.

## 6. Co musi robić program odczytujący { #6-what-a-reader-must-do }

Program odczytujący ma zeskanowane strony i dowolną metodą odczytał z każdej
z nich jej bity danych oraz, tam gdzie mógł, jej napis. Ta część mówi, jakie
wnioski musi z nich wyciągnąć. Skanom nie można ufać: jedną stronę może
wydrukować każdy i może ona deklarować cokolwiek.

### 6.1 Ważny znacznik ma pierwszeństwo przed nagłówkiem { #61-a-valid-tag-wins-over-a-header }

W przypadku strony w układzie `standard` program odczytujący musi najpierw
sprawdzić napis. Jeśli napis ma postać z sekcji 2.8, zawiera ciąg formatu tego
układu, liczbę stron wynoszącą co najwyżej `MAX_PAGES`, numer strony od 1 do
liczby stron (albo 1 przy liczbie stron 0), a jego tekst dowolny zaczyna się
od znacznika, który jest ważny dla tego numeru i tej liczby stron (sekcja
3.2), to strona jest stroną dokumentu ze znacznikiem. Musi być traktowana jako
taka strona nawet wtedy, gdy jej dane zawierają dopuszczalny nagłówek
(sekcja 6.2).

Powód: strumień dokumentu samoidentyfikującego, w postaci, w jakiej zwraca go
stary program, można wydrukować ponownie jako dokument ze znacznikiem. Te
strony zawierają w swoich danych stare nagłówki, a są stronami dokumentu ze
znacznikiem, którego plikiem jest ten strumień.

### 6.2 Nagłówkowi nie można ufać { #62-a-header-is-untrusted }

Kopia nagłówka jest **poprawna składniowo**, gdy jej CRC się zgadza, jej
sygnatura (magic) to `HEADER_MAGIC`, jej wersja to `CONTAINER_VERSION`, jej
parzystość wynosi 0, 32 lub 64 oraz `1 <= page <= total`.

**Nagłówek strony** istnieje, gdy co najmniej jedna z jej `HEADER_COPIES`
kopii jest poprawna składniowo, a wszystkie kopie poprawne składniowo są
równe. Strona, której kopie poprawne składniowo się różnią, nie ma nagłówka.

Nagłówek odczytany ze strony formatu `F` jest **dopuszczalny**, gdy opisuje
dokument, na który pozwala sekcja 4.8, czyli gdy spełnione są wszystkie
poniższe warunki (`m`, `D` i `page_bytes` jak w sekcji 4.1, dla `F`
i parzystości z nagłówka):

1. `total <= MAX_PAGES`;
2. `page_bytes // HEADER_COPIES >= HEADER_SIZE`;
3. jeśli `parity > 0`: `total * page_bytes <= PROTECTED_MAX_BYTES`;
4. `size + 1 <= D(total)`: strony mieszczą plik i bajt długości;
5. jeśli `total > 1`: `size + 1 + NAME_MAX_BYTES > D(total - 1)`: żadna nazwa
   nie pozwoliłaby zmieścić pliku na mniejszej liczbie stron.

Programowi odczytującemu nie wolno używać nagłówka, który nie jest
dopuszczalny. Reguły 4 i 5 wiążą liczbę stron z rozmiarem, tak aby nagłówek
nie mógł deklarować wielu stron dla małego pliku ani niewielu dla dużego.

Program odczytujący musi utrzymywać zużycie pamięci i czasu w proporcji do
liczby stron, które otrzymał, a nie do tego, co deklaruje nagłówek: z powodu
jednej strony, która deklaruje dokument z 9999 stron, programowi
odczytującemu nie wolno przydzielać pamięci dla 9999 stron ani ich
przetwarzać.

Strony należą do jednego dokumentu, gdy ich nagłówki zgadzają się w polach
`fingerprint`, `size`, `total` i `parity`, a strony mają ten sam format
strony. Stron innego dokumentu nie wolno używać.

### 6.3 Tylko odcisk weryfikuje plik { #63-only-the-fingerprint-verifies-a-file }

- **Dokument samoidentyfikujący.** Bajt ładunku jest wymazaniem, gdy jeden
  z jego bitów leży w symbolu, którego kod strony nie zdołał skorygować; każdy
  bajt strony, która nie została dostarczona, jest wymazaniem. Plik to
  pierwsze `size` bajtów strefy danych i jest on odzyskany wtedy i tylko
  wtedy, gdy każde słowo kodowe, które zawiera jeden z tych bajtów, zostało
  odczytane lub naprawione (przy parzystości 0, gdy nic nie jest naprawiane:
  gdy żadne takie słowo kodowe nie ma wymazania). Plik jest
  **zweryfikowany**, gdy jest odzyskany, a pierwsze `FINGERPRINT_SIZE` bajtów
  jego skrótu SHA-256 jest równe odciskowi z nagłówka.
- **Dokument ze znacznikiem.** Plik to pierwsze `SIZE` bajtów strumienia. Jest
  **zweryfikowany**, gdy ma `SIZE` bajtów, a pierwsze `FINGERPRINT_DIGITS`
  znaków szesnastkowych jego skrótu SHA-256 jest równe odciskowi ze znacznika.
- **Dokument prosty.** Nic go nie weryfikuje, a jego długość nie jest znana
  (sekcja 2.7).

Programowi odczytującemu nie wolno nazwać pliku zweryfikowanym z żadnego
innego powodu. W szczególności naprawa, która nie zgłasza niepowodzenia, nie
weryfikuje pliku: słowo kodowe z większą liczbą błędnych bajtów, niż jego
parzystość potrafi naprawić, może zostać zamienione w inne ważne słowo
kodowe, a przy parzystości 0 nic w ogóle nie jest sprawdzane.

Nazwa pliku (sekcja 4.6) nie jest objęta odciskiem. Jest tekstem niezaufanym nawet
wtedy, gdy plik jest zweryfikowany, podobnie jak każdy napis.

### 6.4 Dopełnienia nigdy się nie odczytuje { #64-padding-is-never-read }

Programowi odczytującemu nie wolno odczytywać ani sprawdzać dopełnienia
z sekcji 4.7 ani od niego zależeć. Bajty zerowe (0.3.0) i strumień dopełnienia
(0.3.1) są oba ważne, a dokument z jednym lub drugim jest dla programu
odczytującego tym samym dokumentem.

Bajty strefy danych po nazwie są dopełnieniem. Rekord nazwy, którego bajt
długości wskazuje poza koniec strefy danych albo którego bajty nie są zapisem
UTF-8, albo który leży w słowie kodowym, które nie zostało naprawione, nie
daje nazwy; nie czyni to pliku nieważnym.

Wektory: `tests/vectors/py/container.json`, `tests/vectors/py/tag.json`.

## 7. Dekoder referencyjny (informacyjnie) { #7-reference-decoder-informative }

Ta część opisuje, jak ten projekt odczytuje skan. Nic z niej nie jest
wymagane: program odczytujący może znajdować i próbkować stronę w dowolny
sposób. Kroki i ich stałe pochodzą z programu w C `unoptar` (część 8); wyniki
tego dekodera dla stałego zestawu skanów są ustalone przez wektory wymienione
na końcu, aby dekoder nie zmienił się przypadkiem.

### 7.1 Skan { #71-the-scan }

Skan wczytuje się jako 8-bitowy obraz w skali szarości w świetle liniowym.
Próbka `v` pliku staje się wartością
`floor(255 * (v / 255) ^ (1 / gamma) + 0.5)`, gdzie `gamma` to gamma pliku
(PNG `gAMA`) albo 0.454545, gdy plik jej nie podaje. Obraz kolorowy
przekształca się kanał po kanale, a następnie oblicza się średnią ważoną z wagami 0.212671 dla
czerwonego, 0.715160 dla zielonego i 0.072169 dla niebieskiego oraz zaokrągla
do najbliższej liczby całkowitej. Próbka 16-bitowa zachowuje swoje górne
8 bitów.

```example
linear_light_of_128 = 56
linear_light_of_200 = 149
```

### 7.2 Znajdowanie strony { #72-finding-the-page }

Dekoder otrzymuje format strony. Pracuje na obrazie we właściwym położeniu.

1. **Poziomy szarości.** Próg ma początkowo wartość średniej szarości.
   Co najwyżej 32 razy: `black` to próg minus średnia kwadratowa
   (pierwiastek kwadratowy ze średniej kwadratów) odległości od progu pikseli
   leżących poniżej niego, `white` – próg plus ta sama wielkość dla pikseli
   leżących powyżej niego; nowy próg to
   `sync_white_cut * white + (1 - sync_white_cut) * black`, zaokrąglony;
   procedura kończy się, gdy próg przestaje się zmieniać. Drugi poziom, próg
   wypełnienia, leży w połowie między `black` i `white`.
2. **Wyodrębnianie strony.** Biel wokół strony to każdy piksel na poziomie
   progu wypełnienia lub powyżej, który jest połączony (krawędziami, nie
   narożnikami) z jednym z czterech rogów lub czterech środków krawędzi
   skanu. Strona to wszystko inne, co jest połączone ze środkiem skanu.
   Wszystkie pozostałe piksele (brud między stroną a krawędzią skanu) stają
   się białe.
3. **Przerwa w ramce.** Jeśli drukarka przycięła krawędź strony, ramka ma
   przerwę, biel wokół strony wnika między kropki, a krok 2 znajduje tylko
   kawałek strony. Gdy znaleziony obszar jest mniejszy niż połowa tego, co nie
   jest bielą wokół strony w postaci, w jakiej znalazł ją krok 2, za biel wokół strony przyjmuje się zamiast tego to,
   do czego można dotrzeć przejściami o szerokości co najmniej `2 * r + 1`
   pikseli, gdzie `r = max(5, longest side // 250) // 2`; biel między
   kropkami jest węższa. Ten wynik jest używany tylko wtedy, gdy daje całą
   stronę. Jest to tolerancja tego dekodera, a nie właściwość formatu: strona
   ma całą ramkę.
4. **Rogi.** Z każdego rogu skanu dekoder idzie po przekątnych do wewnątrz
   i bierze pierwszy piksel poniżej progu. Wymaga to strony we właściwym
   położeniu, wyższej niż szerszej; skan szerszy niż wyższy jest najpierw
   obracany (7.5).
5. **Rozmiar piksela.** Liczba pikseli skanu na piksel strony, w poziomie
   i w pionie, wynika z odległości między rogami podzielonych przez `width`
   i `height`; kierunki wierszy i kolumn strony wynikają ze średnich
   przeciwległych boków. (Rozmiar w poziomie wykorzystuje lewy górny róg
   dwukrotnie, a lewego dolnego wcale. Jest to odziedziczone zachowanie
   dekodera, a nie część formatu).

### 7.3 Krzyżyki { #73-crosses }

Pierwszy krzyżyk jest oczekiwany `border + chalf` pikseli strony w głąb od
lewego górnego rogu. Każdy kolejny krzyżyk jest oczekiwany o jeden odstęp
krzyżyków na prawo od swojego lewego sąsiada, a pierwszy w wierszu – o jeden
odstęp krzyżyków poniżej krzyżyka nad nim, więc każde wyszukiwanie zaczyna się
od już znalezionego krzyżyka. Dla każdego krzyżyka:

1. wyszukiwanie zgrubne po całych pikselach skanu, w każdym kierunku do
   połowy `chalf` (połowy połowy boku krzyżyka), miejsca, w którym obraz najlepiej koreluje ze
   wzorem krzyżyka (ciemny, jasny, jasny, ciemny);
2. wyszukiwanie dokładne w obrębie pół piksela skanu krokami co ćwierć
   piksela, na krzyżyku pomniejszonym o `cross_trim` pikseli strony z każdego
   boku;
3. własny próg: z pikseli krzyżyka `white` i `black` jak w 7.2, połączone
   jako `white_cut * white + (1 - white_cut) * black`.

### 7.4 Próbkowanie i dekodowanie { #74-sampling-and-decoding }

1. **Filtry.** Ciemne plamki węższe niż `minmax_filter` razy rozmiar piksela
   strony są usuwane (przebiegi filtra maksimum, a następnie tyle samo
   przebiegów filtra minimum); następnie obraz rozmywa się jądrem 3 na 3
   (1 2 1 / 2 4 2 / 1 2 1) `round(pixel area * pixel_blur ^ 2)` razy.
2. **Próbkowanie.** Położenie każdego piksela danych na skanie interpoluje się
   między czterema otaczającymi go krzyżykami; tak samo jego próg. Próbka jest
   wyostrzana: `value + unsharp_mask * (value - mean of the four
   neighbours at unsharp_dist page pixels)`. Bit ma wartość 1, gdy wynik jest
   poniżej progu.
3. **Dekodowanie.** Bity składa się z powrotem w symbole (sekcja 2.6). Symbol
   Golaya zastępuje się najbliższym symbolem, jeśli różni się on co najwyżej
   3 bitami; w przeciwnym razie symbol jest nie do skorygowania, a jego górne
   12 bitów przyjmuje się tak, jak zostały odczytane. W symbolu Hamminga
   koryguje się jeden błędny bit; dwa błędne bity czynią go nie do
   skorygowania.
4. Słowa strony łączy się w jej `net_bits` bitów danych. W dokumencie prostym
   lub ze znacznikiem bity stron łączy się w kolejności stron i dzieli na
   bajty; bity, które nie wypełniają ostatniego bajtu, są odrzucane.

```example
decoder_unsharp_mask = 7
decoder_unsharp_dist = 1
decoder_sync_white_cut = 0.1
decoder_white_cut = 0.06
decoder_minmax_filter = 0.5
decoder_pixel_blur = 0.25
decoder_cross_trim = 0.75
```

### 7.5 Identyfikacja skanu { #75-identifying-a-scan }

Gdy nie podano mu formatu strony, ten projekt sam go ustala:

1. Obrys strony (7.2, kroki od 1 do 4) daje jej kształt. Oba papiery próbuje
   się w kolejności tego, jak bliski jest ten kształt ich stronie `standard`;
   każdy próbuje się we właściwym położeniu i po obróceniu o pół obrotu (albo
   o ćwierć obrotu w lewo lub w prawo dla skanu szerszego niż wyższy).
2. Dla każdego papieru najpierw jego strona `standard`: stronę się lokalizuje,
   a jej napis odczytuje, dopasowując każdą komórkę znaku do czcionki. Ważny
   znacznik rozstrzyga od razu (sekcja 6.1). Napis bez znacznika jest
   przyjmowany tylko wtedy, gdy został odczytany wyraźnie, i nawet wtedy dane
   są nadal sprawdzane pod kątem nagłówka, ponieważ strona samoidentyfikująca
   ze standardowymi kropkami ma taki napis.
3. Następnie układy tego papieru, od najbliższego kształtu: stronę się
   lokalizuje i dekoduje, a rozstrzyga dopuszczalny nagłówek (sekcja 6.2).

Błędnie odczytany znacznik przechodzi sprawdzenie wartości kontrolnej mniej
więcej raz na 256 przypadków; napis bez znacznika nie ma żadnej wartości
kontrolnej, dlatego musi zostać odczytany wyraźnie i dlatego tekst dowolny, który od ważnego znacznika dzieli jeden
błędnie odczytany znak, jest odrzucany. Te progi przyjęcia należą do tego
programu odczytującego, a nie do formatu.

### 7.6 Wolniejsza metoda odczytu { #76-the-slower-reader }

Ten projekt próbuje drugiej, wolniejszej metody odczytu
(`src/optar/decoder/soft.py`), przeznaczonej dla skanu o zbyt niskiej
rozdzielczości dla jego rozmiaru kropek, w dwóch przypadkach. Pierwszy: kroki
z 7.5 niczego nie identyfikują, choć obrys strony został znaleziony. Drugi:
spełnione są wszystkie trzy następujące warunki: kroki z 7.5 przyjmują stronę
wyłącznie na podstawie napisu bez znacznika; piksel danych tego skanu ma
szerokość mniejszą niż 2.5 piksela skanu; 1% lub więcej symboli strony jest
nie do skorygowania. Dla każdego rozważanego układu i obrotu, w kolejności z 7.5,
metoda ta:

1. powiększa skan tak, aby piksel danych miał szerokość około czterech
   pikseli skanu, i lokalizuje stronę jak w 7.2 i 7.3;
2. odczytuje stronę jak w 7.4 i przyjmuje za znane symbole zdekodowane
   z co najwyżej jednym skorygowanym bitem;
3. próbkuje siatkę 7 na 7 punktów oddalonych od siebie o pół piksela danych
   wokół każdego piksela danych i dopasowuje metodą najmniejszych kwadratów
   filtr przekształcający te próbki w znane bity, osobny filtr dla każdego
   z 16 na 22 obszarów strony;
4. stosuje filtry do każdego piksela danych, co daje dla każdego bitu pewność
   ze znakiem, i wybiera dla każdego symbolu strony ten symbol kodu Golaya
   (sekcja 2.5), który najlepiej pasuje do jego 24 wartości pewności;
5. przyjmuje za znane 60% symboli o największej pewności i powtarza od kroku
   3, łącznie pięć dopasowań.

Strona jest przyjmowana tylko na podstawie dopuszczalnego nagłówka (sekcja
6.2). Napis nie jest odczytywany, więc strona bez nagłówka (dokument prosty
lub ze znacznikiem, część 3) nie jest w ten sposób identyfikowana. Strona,
której znacznik został przyjęty, nigdy nie jest odczytywana w ten sposób,
więc sekcja 6.1 pozostaje w mocy. Wynik trafia
do kontenera dokładnie tak samo jak wynik zwykłej metody odczytu i tylko
odcisk weryfikuje plik (sekcja 6.3). Nic w tej metodzie odczytu nie jest
częścią formatu i nie zmienia ona wyników dekodera z sekcji od 7.1 do
7.5.

Wektory: `tests/vectors/c/decoder.json`, `tests/vectors/c/decoder_internals.json`
(ustalają wyniki tego dekodera dla stałego zestawu skanów, a nie format).

## 8. Historia { #8-history }

Strona z części 2 to format Twibright Optar, programu w C, który w 2007 roku
napisał Karel Kulhavy; później, od 2012 roku, był on utrzymywany w
`colindean/optar`. Jego źródła są przechowywane bez zmian w folderze `lega-c`
tego projektu, w stanie z commita `9c8379c25466bf142459a26b0f34521bdde2af12`
tamtego repozytorium. Wektory w `tests/vectors/c` zostały zarejestrowane za pomocą
tego programu; te w `tests/vectors/py` – za pomocą tego projektu.

| Wersja | Co dodała |
|---|---|
| program w C | strona (część 2); A4 lub Letter wybierane przy kompilacji |
| 0.1.0 | te same strony, zapisywane i odczytywane przez ten projekt |
| 0.2.0 | znacznik (część 3) |
| 0.3.0 | kontener, rozmiary kropek i układy (części 4 i 5), z dopełnieniem zerami |
| 0.3.1 | strumień dopełnienia (sekcja 4.7) |

Co format zachowuje z programu w C:

- ramkę, krzyżyki, kolejność pikseli danych i przeplot;
- tabelę Golaya, zbudowaną z dwunastościanu, i kody Hamminga;
- pasek czcionki, wiersz napisu i jego trzy osobliwości (sekcja 2.8);
- limit 9999 stron oraz pusty plik drukowany jako jedna strona `1/0`;
- to, że strona nie zapisuje długości swojego strumienia;
- siatki dwóch układów `standard` i przesunięcia układu Letter.
  Narzędzia w C umieszczały stronę A4 z przesunięciami 19.22 i 17.44 pt, które
  nie wypadają na całych kropkach drukarki; ten projekt umieszcza ją
  z przesunięciami z sekcji 5.2.

Program w C ma wkompilowany jeden format strony. Jego dekoder przyjmuje ciąg
formatu jako argument, ale używa tylko ostatniego pola.

W napisie pozostaje jedna różnica względem programu w C: program w C obcinał
wiersz napisu według bajtów, ten format obcina go według znaków. Oba sposoby
dają tę samą stronę, chyba że wiersz zostaje obcięty i przed miejscem
obcięcia zawiera znaki spoza ASCII.

Zachowanie dekodera odziedziczone z programu w C, które nie jest częścią
formatu (część 7): siedem stałych z sekcji 7.4, podwójne użycie jednego rogu
przy rozmiarze piksela, wyszukiwanie rogów wymagające strony we właściwym
położeniu, wyższej niż szerszej, oraz 32-bitowa arytmetyka
zmiennoprzecinkowa, którą ustalają wektory dekodera.
