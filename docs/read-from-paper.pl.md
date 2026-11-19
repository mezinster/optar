---
source_hash: e79216aee6b95b8e8e6f807f3e335aa738ff2181
---

# Odczytywanie pliku { #read-it-back }

## Skanowanie { #scanning }

- Skanuj w skali szarości (256 poziomów) albo w kolorze. Nie skanuj w trybie
  czarno-białym.
- Wyłącz każdy tryb „dokument” i każde oczyszczanie tekstu. Zamieniają one
  kropki na czarne lub białe, zanim program je zobaczy.
- Dobierz rozdzielczość do rozmiaru kropek: 600 dpi dla standardowych kropek,
  przy czym 1200 dpi jest nieco lepsze. Pozostałe wartości podaje
  [tabela rozmiarów kropek](put-on-paper.md#dot-size).
- Zapisuj w formacie PNG lub TIFF. Aplikacja przyjmuje też BMP, PGM/PPM
  i JPEG. JPEG kompresuje stratnie i jest złym wyborem. Nie zapisuj stron
  jako jednego pliku PDF.
- Wyczyść szybę skanera i dociśnij stronę płasko: pokrywa, która nie dociska
  papieru, zostawia rozmyte miejsca.

Skan wykonany w zbyt niskiej rozdzielczości dostaje uwagę, która podaje
właściwą rozdzielczość. To tylko rada: skan o niskiej rozdzielczości, który
da się odczytać, i tak zostaje użyty, a taki, którego zwykła metoda odczytu
nie potrafi odczytać, trafia do
[drugiej, wolniejszej metody odczytu](slower-reader.md).

## W aplikacji { #in-the-application }

Otwórz kartę „Odczytaj z papieru” i dodaj skany stron („+ Dodaj skany…” albo
przeciągnij pliki lub foldery na kartę).

Program sam ustala, którą stroną jest każdy skan, jaki to papier i jak skan
jest obrócony. Dlatego skany można dodawać w dowolnej kolejności, do góry
nogami albo obrócone na bok. Sam ustala też rozmiar kropek i ochronę; nie
trzeba niczego ustawiać.

![Skany w trakcie odczytu, każdy z paskiem postępu i swoim etapem](img/being-read.png)

Lista pokazuje jeden wiersz na stronę wraz z jej stanem. Wybranie wiersza
pokazuje skan z zaznaczonymi uszkodzonymi miejscami: kółko myszy przybliża
i oddala, przeciąganie przesuwa obraz, dwukrotne kliknięcie dopasowuje widok
do całej strony.

Gdy pasek u dołu poda, że plik jest zweryfikowany, „Zapisz plik…” zapisuje go.

Z listy możesz:

- usunąć skan z listy;
- zastąpić skan strony albo użyć zamiast bieżącego zapasowego skanu tej
  strony;
- przełączyć się na inny dokument, jeśli dodane skany należą do więcej niż
  jednego wydruku;
- ręcznie przypisać do strony skan, którego nie udało się zidentyfikować;
- złożyć dokument ręcznie, gdy nie da się zidentyfikować żadnego skanu:
  podajesz papier i liczbę stron, a potem przypisujesz każdy skan do jego
  strony.

## W trakcie odczytu skanu { #while-a-scan-is-being-read }

Każdy dodany skan jest widoczny w sekcji „W trakcie odczytu”, dopóki nie
zostanie odczytany, razem z paskiem postępu i etapem, na którym jest:

| Etap | Co się dzieje |
|---|---|
| W kolejce | Skan czeka na swoją kolej. |
| Otwieranie pliku | Obraz jest wczytywany. |
| Szukanie strony | Program szuka zarysu strony. |
| Identyfikacja strony | Program próbuje kolejnych papierów, rozmiarów kropek i orientacji, aż któraś kombinacja pasuje. |
| Odczyt danych | Kropki są odczytywane i korygowane. |
| Wolniejsza metoda: próbkowanie, potem „Wolniejsza metoda: przebieg 4 z 5” | Tylko dla skanu, którym zajmuje się [wolniejsza metoda](slower-reader.md). |

Pasek liczy etapy, a nie sekundy: może zatrzymać się na jednym etapie, a potem
skoczyć, ale nigdy nie cofa się. „Usuń z listy” przerywa odczyt skanu.
Odczytany skan zostaje przypisany do swojej strony albo trafia do sekcji „Nieczytelne”.

## Stany stron { #page-states }

| Stan | Znaczenie | Co zrobić |
|---|---|---|
| W porządku | Strona została odczytana bez żadnego błędu do skorygowania. | Nic. |
| Naprawiona · N | N bloków było uszkodzonych, a korekcja błędów je naprawiła. Dane są nienaruszone. | Nic. |
| Uszkodzona · N utraconych | N bloków nie dało się naprawić, więc zapisany plik ma w tych miejscach błędne dane. | Zeskanuj ponownie stronę w skali szarości w rozdzielczości dla jej rozmiaru kropek i zastąp skan. |
| Odczytana wolniejszą metodą | Rozdzielczość skanu była za niska dla zwykłej metody. Zob. [Skany o zbyt niskiej rozdzielczości](slower-reader.md). | Sprawdź, czy dokument przechodzi weryfikację. |
| Nieczytelna | Nie udało się zidentyfikować skanu: na przykład na obrazie nie ma strony optar albo nie udało się odczytać napisu. | Zeskanuj go ponownie albo ręcznie przypisz do strony. |
| Brak | Nie dodano skanu tej strony. | Dodaj go. W dokumencie z ochroną pozostałe strony mogą jeszcze wystarczyć i wtedy pasek o tym informuje. |

Skan wykonany w rozdzielczości poniżej 400 dpi, którego nie da się odczytać,
mówi o tym wprost, na przykład „Zeskanowano w rozdzielczości około 200 dpi,
zbyt niskiej do odczytu”, i podaje rozdzielczość potrzebną dla każdego
rozmiaru kropek.

## Pasek u dołu { #the-bar-at-the-bottom }

Pasek pokazuje stan całego dokumentu.

| Pasek podaje | Znaczenie |
|---|---|
| Plik odzyskany i zweryfikowany · N bajtów | Wszystkie strony zostały odczytane, a odzyskany plik zgadza się z odciskiem na papierze. |
| Nie zgadza się z odciskiem na papierze | Wszystkie strony zostały odczytane, ale plik nie jest oryginałem, bo część danych zdekodowano błędnie. Zeskanuj strony ponownie, zaczynając od oznaczonych jako „Naprawiona”. |
| Do odzyskania: brak strony 3, można ją odtworzyć z pozostałych | Dokument z ochroną: brakuje stron, ale odczytane strony powinny wystarczyć, by je odtworzyć. |
| Do odzyskania: brak strony 3, odtworzona z pozostałych · zgadza się z odciskiem | Odtworzenie zostało wykonane i sprawdzone. Dalej podany jest rozmiar i to, co zrobiła naprawa. |
| Przetwarzanie… Odczytano 3 z 6 skanów | Skany są jeszcze odczytywane. Jeśli dokument ma już stan do pokazania, licznik pojawia się po nim: „Plik odzyskany i zweryfikowany · N bajtów · odczytano 3 z 6 skanów”. |
| Sprawdzanie odcisku… | Sprawdzanie trwa w tle. |
| Odczytano wszystkie strony: N · nie można zweryfikować (brak znacznika) | Strony pochodzą ze starego programu i nie mają odcisku. |
| 4 z 6 stron w porządku · 1 uszkodzona · 1 brakująca | W pozostałych przypadkach – zestawienie liczbowe. |

Dla dokumentu z ochroną okno pokazuje też, ile bajtów naprawiła ochrona i jaką
część swojej zdolności naprawczej wykorzystało najgorsze miejsce, na przykład
„najgorsze miejsce wykorzystało 57% zdolności naprawczej (18 z 32):
umiarkowany zapas”.
Jeśli naprawa się nie powiedzie, okno
podaje strony, które trzeba dodać lub zeskanować ponownie.

!!! info "Co znaczy „zweryfikowany”"
    „Zweryfikowany” zawsze oznacza, że odcisk odzyskanego pliku był zgodny
    z odciskiem na papierze. Nigdy nie oznacza tylko tego, że naprawa nie
    zgłosiła niepowodzenia.

## Zapisywanie { #saving }

Gdy plik nie jest zweryfikowany, „Zapisz plik…” prosi o potwierdzenie i podaje,
co jest z nim nie tak.

Dokument z ochroną, którego nie udało się naprawić, można mimo to zapisać
w takim stanie, w jakim udało się go odzyskać, po ostrzeżeniu, że plik może
zawierać błędne fragmenty. Jest to możliwe tylko wtedy, gdy odczytano co
najmniej połowę jego stron: przy mniejszej liczbie nic nie zostaje zapisane.

## Wydruki ze starych programów { #printouts-from-old-programs }

Wydruki z optar 0.1.0 lub z programu w C nie mają znacznika w napisie.
Aplikacja je odczytuje, ale:

- nie potrafi stwierdzić, czy strony należą do jednego wydruku ani czy plik
  jest kompletny;
- nie może zweryfikować pliku;
- zapisany plik jest dopełniany zerami do pełnej strony.

Zapisz taki plik dopiero po przeczytaniu ostrzeżenia, które pokazuje
aplikacja.
