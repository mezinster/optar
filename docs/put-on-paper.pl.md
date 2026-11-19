---
source_hash: bceb221e5e7d1915ae0d3656ce9713f5c5f1cdeb
---

# Zapisywanie pliku na papierze { #put-a-file-on-paper }

## W aplikacji { #in-the-application }

Otwórz kartę „Zapisz na papierze”.

![Karta „Zapisz na papierze” z wybranym plikiem](img/put-on-paper.png)

1. Wybierz plik albo przeciągnij go na kartę.
2. Wybierz A4 lub US Letter.
3. Wybierz [rozmiar kropek](#dot-size) i [ochronę](#protection). Okno
   otwiera się ze standardowymi kropkami i standardową ochroną.
4. Nadaj plikowi nazwę. Wiersz „Na wydruku:” pokazuje tekst, który zostanie
   wydrukowany na każdej stronie.
5. Przeczytaj wiersz pod nim: pokazuje, ilu stron potrzebuje plik, a przy
   ochronie także, ile z tych stron można utracić.
6. „Utwórz PDF…” zapisuje plik PDF.

Zaznaczenie pola „Zgodność z optar 0.2 i oryginalnym programem optar” daje
wydruk, który te starsze programy potrafią odczytać. Ma on standardowe kropki
i nie ma ochrony.

Jak to zrobić w wierszu poleceń, opisuje [`optar encode`](command-line.md#encode).

## Drukowanie { #printing }

Wydrukuj PDF w rozmiarze rzeczywistym (100%), a nie z opcją „Dopasuj do
strony”, na drukarce laserowej 600 dpi. Drukarek atramentowych nie
testowano.

Wydruk mniejszy niż rozmiar rzeczywisty ma mniejsze kropki, które trudniej
odczytać. Jeden prawdziwy wydruk miał około 95% rozmiaru rzeczywistego.

## Rozmiar kropek { #dot-size }

Rozmiar kropek to wielkość, z jaką drukowana jest każda kropka danych. Większe
kropki przetrwają skan w niższej rozdzielczości, ale strona mieści ich mniej,
więc mieści mniej danych. Kropka danych to 3, 4, 5, 6 lub 9 kropek drukarki
600 dpi.

Tabela podaje rozdzielczość skanowania (trzy piksele skanu na kropkę
danych) oraz liczbę bajtów, które mieści jedna strona przed dodaniem
ochrony:

| Rozmiar kropek | Opcja | Kropki drukarki na kropkę danych | Skanuj w | Strona A4 | Strona Letter |
|---|---|---|---|---|---|
| Standardowe | `standard` | 3 | 600 dpi | 199 773 | 192 591 |
| Średnie | `medium` | 4 | 450 dpi | 114 904 | 110 463 |
| Duże | `big` | 5 | 360 dpi | 73 027 | 69 463 |
| Bardzo duże | `large` | 6 | 300 dpi | 49 119 | 48 403 |
| Ogromne | `xlarge` | 9 | 200 dpi | 21 606 | 21 127 |

Wybierz rozmiar kropek pod skaner, który będzie odczytywał strony – być może
za wiele lat. Jeśli nie wiesz, bezpieczniejszym wyborem są większe kropki.

## Ochrona { #protection }

Ochrona przed uszkodzeniami to dodatkowe dane, rozłożone na wszystkie strony
dokumentu, dzięki którym program naprawia uszkodzone miejsca i odtwarza
utracone strony. Do wyboru są: Brak, Standardowa i Wysoka.

- Zajmuje papier: standardowa ochrona dodaje około 14% stron, a wysoka
  około 34%.
- Dodatkowe dane są rozłożone tak, że plama, oderwany róg czy brakująca
  strona odbierają każdej części pliku mniej więcej tyle samo – niewiele.
  Właśnie tę niewielką część naprawia ochrona.
- Przy ochronie część stron niesie dane ochrony, a każda strona powtarza
  krótki zapis, który podaje, z jakiego dokumentu pochodzi i którą jest
  stroną. Dlatego na sam plik zostaje mniej miejsca, niż pokazuje tabela
  powyżej.

### Utrata całej strony { #losing-a-whole-page }

Okno i `optar encode` obiecują odzyskanie utraconej strony tylko
w dokumentach dostatecznie długich i wtedy podają „można utracić N stronę
z T” (albo „N strony”, „N stron” – zależnie od liczby).

| Ochrona | 1 stronę można utracić od | 2 strony można utracić od |
|---|---|---|
| Standardowa | 12 stron | 24 stron |
| Wysoka | 6 stron | 12 stron |

W krótszych dokumentach uszkodzenia wewnątrz stron są naprawiane, ale utrata
całej strony oznacza utratę pliku. Ta obietnica jest celowo ostrożna
i z dokumentu może dać się odzyskać więcej, niż obiecuje.

### Największy plik { #the-largest-file }

Plik, którego wydruk z ochroną zająłby na papierze więcej niż 256 MiB, jest
odrzucany. Okno podaje wtedy, czy plik zmieściłby się bez ochrony albo
z mniejszymi kropkami.

## Jakie programy odczytają wydruk { #which-programs-can-read-the-printout }

| Wydruk | Odczytuje go |
|---|---|
| Dowolny rozmiar kropek inny niż standardowy albo dowolna ochrona | optar 0.3 lub nowszy. Przy odczycie nie trzeba niczego ustawiać. |
| Standardowe kropki, bez ochrony, zaznaczone pole „Zgodność” | każda wersja oraz oryginalny program w C |

Aplikacja w wersji 0.2.0 w ogóle nie potrafi odczytać stron z większymi
kropkami. Przy standardowych kropkach z ochroną wersja 0.2.0 i program w C
zwracają dane opakowane w dodatkowe informacje i ochronę, a nie sam plik.

Przyczyny opisuje rozdział
[„Jak strona się identyfikuje”](identification.md).

!!! note "Pliki z wydruku zgodnego są dopełniane zerami"
    Wydruk przeznaczony dla wersji 0.2 i starszych programów nie przechowuje
    w danych długości pliku; ma ją tylko znacznik w napisie. Program wiersza
    poleceń `optar decode` i program w C zwracają taki plik dopełniony zerami
    do pełnej strony. Jeśli twoje dane są na to wrażliwe, spakuj je programem
    tar.
