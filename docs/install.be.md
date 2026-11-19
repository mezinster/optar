---
source_hash: e2c7112db6c41d20df8b36d2d29c2ab43a5ecb4a
---

# Усталяванне { #install }

## Спампоўка { #download }

Спампуйце файл для сваёй сістэмы з
[раздзела Releases на GitHub](https://github.com/mezinster/optar/releases/latest).
`<tag>` ніжэй — гэта нумар версіі, напрыклад `v0.5.0`.

| Сістэма | Праграма з акном | Камандны радок |
|---|---|---|
| Linux | `optar-gui-<tag>-linux-x86_64` | `optar-<tag>-linux-x86_64` |
| macOS (Apple silicon) | `optar-gui-<tag>-macos-arm64.zip` | `optar-<tag>-macos-arm64` |
| Windows | `optar-gui-<tag>-windows-x86_64.exe` | `optar-<tag>-windows-x86_64.exe` |

Кожная праграма — гэта адзін файл, і больш нічога ўсталёўваць не трэба.

- **Linux:** спачатку выканайце для файла `chmod +x`.
- **macOS:** выканайце `chmod +x` для праграмы каманднага радка. Распакуйце
  праграму з акном і паспрабуйце яе адкрыць. Праграмы не падпісаныя, таму
  macOS можа адмовіцца іх адкрываць: адкрыйце System Settings («Сістэмныя
  налады»), раздзел Privacy & Security («Прыватнасць і бяспека») і выберыце
  Open Anyway («Усё роўна адкрыць»). У старэйшых версіях macOS пстрыкніце па
  праграме правай кнопкай мышы і выберыце Open («Адкрыць»).
- **Windows:** праграмы не падпісаныя, таму пры першым запуску Windows можа
  паказаць папярэджанне.

## З зыходнага кода { #from-source }

Патрэбны Python 3.12 або навейшы і копія рэпазіторыя.

Праграма каманднага радка (усталёўвае numpy і Pillow):

    pip install .

Разам з праграмай з акном:

    pip install '.[gui]'
    optar-gui

## Пераканацца, што ўсё працуе { #check-that-it-works }

`optar --version` і `optar-gui --version` выводзяць нумар версіі.

`optar-gui --self-test` запускае праграму без экрана і пераконваецца, што яна
ўмее кадаваць і чытаць старонкі.
