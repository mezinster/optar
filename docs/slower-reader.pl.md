---
source_hash: e1aa7bf9091169288d65ca97a824f48d1c05c64e
---

# Skany o zbyt niskiej rozdzielczości: wolniejsza metoda odczytu { #scans-that-are-too-coarse-the-slower-reader }

Od wersji 0.4.0 program ma drugą, wolniejszą metodę odczytu dla skanów
wykonanych w rozdzielczości zbyt niskiej dla ich rozmiaru kropek, na przykład
strony ze standardowymi kropkami zeskanowanej w 300 dpi zamiast w 600.

Jeśli możesz, skanuj w zalecanej rozdzielczości. Wolniejsza metoda odzyskuje
niektóre skany o niskiej rozdzielczości, nie wszystkie (zob.
[Co wykazano, a czego nie](evidence.md#the-slower-reader)).

## Kiedy działa { #when-it-runs }

Uruchamia się sama, w dwóch przypadkach:

- Zwykła metoda odczytu nie potrafi zidentyfikować skanu, ale znajduje na nim
  zarys strony.
- Skan o niskiej rozdzielczości (mniej niż 2,5 piksela skanu na kropkę) dał
  zwykłej metodzie tylko napis bez znacznika i żadnego nagłówka, a dane strony
  odczytały się źle (co najmniej 1% symboli nie do skorygowania). Na takim
  skanie napis może być jeszcze czytelny tam, gdzie dane już nie są.

Strona, której dane odczytują się dobrze, to stara strona bez nagłówka i nie
jest ruszana. Jeśli wolniejsza metoda niczego nie znajdzie, zostaje odczyt
z napisu.

## Jak działa { #how-it-works }

Wolniejsza metoda powiększa skan. Na podstawie kropek, których zwykła metoda
jest pewna, uczy się, jak sąsiednie kropki rozmywają się w siebie nawzajem
w każdej części strony. Następnie z tą wiedzą odczytuje każdą kropkę i wybiera
każdy symbol jako całość.

## W aplikacji { #in-the-application }

![Dwie strony odczytane wolniejszą metodą, z zaznaczonymi skorygowanymi kropkami](img/slow-pages.png)

*Wygenerowana strona testowa, mała i zeskanowana w bardzo niskiej
rozdzielczości. Skorygowane kropki są zaznaczone na podglądzie.*

- Podczas pracy wolniejszej metody wiersz skanu pokazuje jej etap i postęp.
  Wybranie wiersza informuje, że trwa to około minuty.
- Potem wiersz podaje, że strona została odczytana wolniejszą metodą, i ile
  kropek ta metoda skorygowała, na przykład „Strona 3 · Odczytana wolniejszą
  metodą · 265 112 kropek skorygowanych”. Skorygowana kropka to taka, której
  własny wygląd został przegłosowany przy wyborze jej symbolu.
- Skorygowane kropki są zaznaczone na podglądzie skanu, każde zaznaczenie ma
  szerokość jednej kropki. Na skanach o niskiej rozdzielczości to często
  kilka procent kropek, więc w widoku całej strony widać zabarwienie tak
  gęste, jak gęste są korekty. Powiększenie pokazuje pojedyncze kropki.
- Po weryfikacji dokumentu wiersz dodaje, ile bajtów strony naprawiła ochrona
  dokumentu („· 6 912 bajtów naprawionych przez ochronę dokumentu”).
  Wybranie strony pokazuje obie liczby.

Taka strona nigdy nie jest oznaczana jako „W porządku” i w pasku u dołu jest
liczona osobno. Wolniejsza metoda daje każdemu symbolowi swoje najlepsze
przypuszczenie, więc nie potrafi powiedzieć, co na stronie jest nie do
naprawienia.

## W wierszu poleceń { #on-the-command-line }

`optar decode` też uruchamia ją sam i informuje o tym na stderr dla każdego
skanu, na którym jej próbuje. `--no-slow-reader` ją wyłącza.

## Ile to trwa { #how-long-it-takes }

Strona A4 zajęła na komputerze, na którym rozwijano program, łącznie od 40 do
70 sekund: 20–35 sekund, zanim zwykła metoda się poddała, a potem 20–35 sekund
pracy wolniejszej metody.

Obraz, który w ogóle nie jest stroną optar, ale na którym znaleziono zarys
strony, kosztuje około 20–35 sekund więcej niż bez wolniejszej metody.

## Ograniczenia { #limits }

- Identyfikuje stronę tylko po nagłówku w jej danych. Stare strony w stylu
  0.2, identyfikowane po znaczniku w napisie, nie są objęte.
- Strona, której znacznik zwykła metoda zaakceptowała, nigdy nie trafia do
  wolniejszej metody.
- Oczekuje się, że standardowa ochrona nie wystarczy dla strony ze
  standardowymi kropkami zeskanowanej w około 290 dpi. Jedyny prawdziwy
  dokument, który odzyskano w ten sposób, miał wysoką ochronę i wymagał
  więcej naprawy, niż może dać standardowa ochrona.
- Nie sprawia, że błędny plik wygląda na poprawny: jak zawsze, tylko odcisk
  sprawia, że plik jest zweryfikowany.
