---
source_hash: 2249212b8920c7b2d504e467f61c20e86e4b2d9d
---

# Jak strona się identyfikuje { #how-a-page-identifies-itself }

Program musi wiedzieć o każdym skanie, do jakiego dokumentu należy i którą
jest stroną. Strona może to przekazać na dwa sposoby, zależnie od tego, jak
wykonano wydruk.

| Wydruk | Identyfikowany po |
|---|---|
| Wykonany z ochroną albo z dowolnym rozmiarem kropek innym niż standardowy | nagłówku w danych strony („strony samoidentyfikujące”: strony, które same podają, do jakiego dokumentu należą i jaki mają numer) |
| Wydruk zgodny wykonany w wersji 0.2.0 lub nowszej | znaczniku w napisie u dołu strony |
| Z wersji 0.1.0 lub z programu w C | samym napisie, którego nie ma z czym porównać |

Ważny znacznik w napisie zawsze wygrywa: strona, której napis ma ważny
znacznik, jest odczytywana jak strona z wersji 0.2.0, bez względu na to, co
zawierają jej dane.

## Strony samoidentyfikujące { #self-identifying-pages }

Strony wydruku wykonanego z ochroną albo z dowolnym rozmiarem kropek innym niż
standardowy niosą w swoich danych informacje o dokumencie: do jakiego wydruku
należą, swój numer, liczbę stron, rozmiar pliku i jego odcisk.

Napis drukowany u dołu jest dla ludzi i nie służy do identyfikacji stron.
W pliku PDF jest drukowany w jednym rozmiarze bez względu na rozmiar kropek
(w rozmiarze napisu strony ze standardowymi kropkami), więc mieści się cały
wiersz. Jest wtedy za mały, by odczytać go ze skanu o niskiej rozdzielczości,
i okno pokazuje „(bez nazwy)”, dopóki plik nie zostanie odzyskany i nie
będzie znana jego własna nazwa. Strony PNG i PGM mają jeden piksel na kropkę,
więc ich napis jest rysowany kropkami strony i rośnie razem z nimi.

Miejsce, którego taki dokument nie wykorzystuje, jest wypełniane stałym
wzorem wyglądającym jak dane, dzięki czemu każda strona drukuje się
równomiernie. Wersja 0.3.0 wypełniała je zerami, które drukowały się jako
białe pasy w poprzek stron. Odczytywane są oba warianty, także przez wersję
0.3.0: żaden program odczytujący nie zagląda do wypełnienia.

Sam nagłówek strony nie jest wiarygodny: jedna zeskanowana strona
mogłaby twierdzić, że należy do dowolnego dokumentu. Tylko odcisk odzyskanego
pliku sprawia, że plik jest zweryfikowany.

## Napis { #the-label }

Każda strona ma u dołu napis: format strony, numer strony i liczbę stron,
a potem tekst dowolny. W wydrukach z wersji 0.2.0 i wcześniejszych aplikacja
odczytuje ten napis ze skanu.

- Napis ze znacznikiem jest przyjmowany, gdy odczytuje się wiarygodnie,
  wartość kontrolna znacznika zgadza się z numerem strony i liczbą stron,
  a rozmiar pliku w znaczniku pasuje do tej liczby stron.
- Napisu bez znacznika (wydruki z wersji 0.1.0 lub z programu w C) nie ma
  z czym porównać, więc jest przyjmowany tylko wtedy, gdy odczytuje się
  wyraźnie.
- Napis, który wygląda jak znacznik z jednym uszkodzonym znakiem, jest
  odrzucany.

Odrzucony skan trafia do sekcji „Nieczytelne” wraz z przyczyną i możesz go
ręcznie przypisać do strony.

## Znacznik { #the-tag }

Od wersji 0.2.0 `optar encode` i aplikacja drukują znacznik na początku
tekstu dowolnego każdej strony wydruku zgodnego, w postaci
`[SIZE:FINGERPRINT:CC]`.

| Część | Znaczenie |
|---|---|
| `SIZE` | rozmiar pliku w bajtach |
| `FINGERPRINT` | pierwsze 8 cyfr szesnastkowych skrótu SHA-256 pliku |
| `CC` | wartość kontrolna z dwóch cyfr szesnastkowych, zależna od numeru strony i liczby stron |

Znacznik pozwala aplikacji:

- rozdzielać strony różnych wydruków;
- odrzucić napis ze znacznikiem, w którym rozmiar nie pasuje do liczby stron;
- odrzucić skan, którego napis został błędnie odczytany, zamiast umieścić go
  na niewłaściwej stronie (mniej więcej 1 błędny odczyt na 256 może mimo to
  przejść kontrolę);
- przyciąć odzyskany plik do prawdziwego rozmiaru, tak by nie miał dopełnienia
  zerami;
- porównać odzyskany plik z odciskiem, co jest ostatecznym sprawdzeniem, że
  plik jest oryginałem.

Aby drukować bez znacznika, użyj `optar encode --no-tag`. Strony, które
identyfikują się na podstawie swoich danych, nie mają drukowanego znacznika.

Dokładne definicje zawiera [specyfikacja formatu](format.md): część 3
dla znacznika i część 4 dla dokumentów samoidentyfikujących.
