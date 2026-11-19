---
source_hash: 34c3bf2795da00caec5ecf72aeb5391c9d6f4e57
---

# Co wykazano, a czego nie { #what-has-and-has-not-been-shown }

Ten rozdział mówi, na czym opierają się twierdzenia projektu. Większość z nich
pochodzi z symulowanych skanów, a nie z papieru.

## Symulowane skany { #simulated-scans }

Testy automatyczne odczytują wygenerowane obrazy z rozmyciem, szumem
i obrotem. Symulowane rozmycie dopasowano do trzech prawdziwych skanów 300 dpi
jednej wydrukowanej strony, wykonanych na jednej drukarce i jednym skanerze
z podajnikiem arkuszy.

- Przy tym rozmyciu standardowe kropki nie dały się zdekodować w 300 dpi
  zwykłą metodą odczytu.
- Średnie kropki ze standardową ochroną przeszły weryfikację w 300 dpi
  i w 200 dpi.
- Duże, bardzo duże i ogromne kropki przeszły weryfikację w 200 dpi bez
  błędów.
- Dokument z 12 stron przeszedł weryfikację z jedną stroną pominiętą.

## Wolniejsza metoda odczytu { #the-slower-reader }

Działanie [wolniejszej metody odczytu](slower-reader.md) wykazano na jednym
prawdziwym dokumencie i jednym symulowanym.

**Prawdziwy.** Dokument właściciela projektu: sześć stron A4, standardowe
kropki, wysoka ochrona, zeskanowany w około 290 dpi tam, gdzie zalecane jest
600 dpi. Zwykła metoda nie zidentyfikowała żadnej ze stron. Z wolniejszą
metodą plik został odzyskany i zweryfikowany odciskiem: 759 879 bajtów,
z czego 41 495 bajtów naprawiła ochrona dokumentu, a najgorszy blok
wykorzystał 40 ze swojego budżetu 64. To jeden dokument, jedna drukarka, jeden
skaner i jedna rozdzielczość. Skany nie są częścią repozytorium.

**Symulowany** (`tests/unit/test_coarse_claim.py`). Dwustronicowy dokument
tego samego rodzaju, zeskanowany w 290 i w 300 dpi przy rozmyciu 1,8 kropki
drukarki. W 290 dpi zwykła metoda nie identyfikuje żadnej strony; w 300 dpi
odczytuje napis każdej strony, ale żadnego nagłówka. W obu przypadkach plik
przechodzi weryfikację z wolniejszą metodą. Przy domyślnym rozmyciu symulatora
(1,0) zwykła metoda sama odczytuje taką stronę w 300 dpi.

Symulator jest łagodniejszy niż skaner właściciela: w symulacji przy 290 dpi
wolniejsza metoda niczego nie naprawiła, podczas gdy prawdziwy dokument
wymagał naprawienia 41 495 bajtów.

Standardowa ochrona ma budżet 32, mniej niż 40, których potrzebował najgorszy
blok prawdziwego dokumentu. Oczekuje się więc, że dokument ze standardową
ochroną zeskanowany w ten sposób nie zostanie odzyskany. Wolniejsza metoda nie
obsługuje starych stron w stylu 0.2.

## Czego nie wykazano { #what-is-not-shown }

- Nie odczytano jeszcze żadnego prawdziwego skanu strony z większymi
  kropkami.
- Odczyt napisów i dekodowanie mają testy automatyczne tylko na syntetycznych
  skanach, a nie na prawdziwych wydrukowanych i zeskanowanych stronach.
  Dotyczy to każdego wydruku z większymi kropkami lub z ochroną.
- Skanerów z podajnikiem arkuszy nie testowano poza tym, że program znalazł
  siatkę kropek na trzech prawdziwych skanach.
- Trzy prawdziwe skany 300 dpi jednego wydruku dały pomiar około 286 dpi, co
  oznacza, że ten wydruk wyszedł w około 95% rozmiaru rzeczywistego. Mniejsze
  kropki trudniej odczytać, więc drukuj w rozmiarze rzeczywistym (100%).
- Drukarek atramentowych nie testowano.

## Te same strony co w programie w C { #the-same-pages-as-the-c-program }

Strony z kodera w Pythonie są identyczne co do bajtu z wynikiem oryginalnego
programu `optar` w C dla A4, Letter i wszystkich pięciu trybów korekcji
błędów. Położenia krzyżyków i próbkowane bity dekodera w Pythonie są
identyczne co do bitu z programem `unoptar` w C na syntetycznych obrazach
testowych. Jedno i drugie jest sprawdzane z wynikami programów w C, które
zarejestrowano jeden raz i przechowuje się w `tests/vectors`.

Każda strona wydruku samoidentyfikującego jest nadal zwykłą stroną optar:
program `unoptar` w C zbudowany z tym samym rozmiarem siatki odczytuje jej
kropki dokładnie (zarejestrowano to dla bardzo dużych kropek na A4 i średnich kropek
na Letter). Zwraca przy tym dane z dodatkowymi informacjami i ochroną
opakowanymi wokół pliku, a nie sam plik.
