---
source_hash: e2c7112db6c41d20df8b36d2d29c2ab43a5ecb4a
---

# Instalacja { #install }

## Pobieranie { #download }

Pobierz plik dla swojego systemu ze strony
[Releases](https://github.com/mezinster/optar/releases/latest). `<tag>`
w nazwach poniżej oznacza wersję, na przykład `v0.5.0`.

| System | Aplikacja okienkowa | Wiersz poleceń |
|---|---|---|
| Linux | `optar-gui-<tag>-linux-x86_64` | `optar-<tag>-linux-x86_64` |
| macOS (Apple silicon) | `optar-gui-<tag>-macos-arm64.zip` | `optar-<tag>-macos-arm64` |
| Windows | `optar-gui-<tag>-windows-x86_64.exe` | `optar-<tag>-windows-x86_64.exe` |

Każdy z nich to pojedynczy plik, który nie wymaga instalowania niczego innego.

- **Linux:** najpierw wykonaj na pliku `chmod +x`.
- **macOS:** wykonaj `chmod +x` na pliku programu wiersza poleceń. Rozpakuj
  aplikację i spróbuj ją otworzyć. Programy nie są podpisane, więc macOS może
  odmówić: otwórz Ustawienia systemowe, Prywatność i ochrona, i wybierz
  „Otwórz mimo to” (w starszych wersjach macOS kliknij aplikację prawym
  przyciskiem myszy i wybierz Otwórz).
- **Windows:** programy nie są podpisane, więc przy pierwszym uruchomieniu
  Windows może wyświetlić ostrzeżenie.

## Z kodu źródłowego { #from-source }

Potrzebujesz Pythona 3.12 lub nowszego i kopii repozytorium.

Program wiersza poleceń (instaluje numpy i Pillow):

    pip install .

Do tego aplikacja okienkowa:

    pip install '.[gui]'
    optar-gui

## Sprawdzenie, czy działa { #check-that-it-works }

`optar --version` i `optar-gui --version` wyświetlają numer wersji.

`optar-gui --self-test` uruchamia aplikację bez ekranu i sprawdza, czy potrafi
zakodować i odczytać strony.
