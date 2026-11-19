---
source_hash: 3205775811b328fd30b9d40d49b0c5b503e8cced
---

# Historia { #history }

Program optar napisał w języku C Karel „Clock” Kulhavy z Twibright Labs
w 2007 roku, jako programy `optar`, `unoptar` i `pgm2ps`. Jego witryna to
[ronja.twibright.com/optar](http://ronja.twibright.com/optar/). Colin Dean
utrzymywał dostępność kodu źródłowego i ulepszał go w latach 2012–2018 w
[github.com/colindean/optar](https://github.com/colindean/optar).

Ten projekt wyszedł od tego kodu. Oryginalne programy w C są przechowywane
bez zmian w folderze `lega-c` repozytorium. Są historią: nic w tym projekcie
ich już nie buduje ani nie uruchamia. Plik
[README](https://github.com/mezinster/optar#history-the-original-c-program)
zachowuje ich oryginalne instrukcje.

## Wersje tego projektu { #versions-of-this-project }

| Wersja | Co dodała |
|---|---|
| 0.1.0 | Polecenie `optar` w Pythonie, które odczytuje i zapisuje te same strony co programy w C. |
| 0.2.0 | Aplikację okienkową oraz znacznik w napisie z rozmiarem i odciskiem pliku. |
| 0.3.0 | Większe kropki, ochronę i strony, które identyfikują się na podstawie swoich danych. |
| 0.4.0 | Wolniejszą metodę odczytu dla skanów o zbyt niskiej rozdzielczości. |
| 0.5.0 | Paski postępu dla skanów w trakcie odczytu oraz liczby tego, co skorygowała wolniejsza metoda. |

Sam format, łącznie z tym, co pochodzi z programu w C, opisuje część 8
[specyfikacji formatu](format.md).

## Licencja { #licence }

GPL. © 2007 Karel „Clock” Kulhavy z Twibright Labs; ulepszenia © 2012–2018
Colin Dean. Zob. plik `COPYING` w repozytorium.
