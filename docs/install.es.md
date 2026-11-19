---
source_hash: e2c7112db6c41d20df8b36d2d29c2ab43a5ecb4a
---

# Instalación { #install }

## Descarga { #download }

Descargue el archivo para su sistema desde la
[página Releases](https://github.com/mezinster/optar/releases/latest). Abajo,
`<tag>` es la versión, por ejemplo `v0.5.0`.

| Sistema | Aplicación de escritorio | Línea de comandos |
|---|---|---|
| Linux | `optar-gui-<tag>-linux-x86_64` | `optar-<tag>-linux-x86_64` |
| macOS (Apple silicon) | `optar-gui-<tag>-macos-arm64.zip` | `optar-<tag>-macos-arm64` |
| Windows | `optar-gui-<tag>-windows-x86_64.exe` | `optar-<tag>-windows-x86_64.exe` |

Cada uno es un único archivo y no necesita nada más instalado.

- **Linux:** ejecute primero `chmod +x` sobre el archivo.
- **macOS:** ejecute `chmod +x` sobre el archivo de línea de comandos.
  Descomprima la aplicación e intente abrirla. Los programas no están
  firmados, así que macOS puede negarse: abra «Ajustes del Sistema»,
  «Privacidad y seguridad», y elija «Abrir igualmente» (en versiones
  anteriores de macOS, haga clic derecho en la aplicación y elija «Abrir»).
- **Windows:** los programas no están firmados, así que Windows puede mostrar
  una advertencia la primera vez que se ejecutan.

## Desde el código fuente { #from-source }

Necesita Python 3.12 o posterior y una copia del repositorio.

El programa de línea de comandos (instala numpy y Pillow):

    pip install .

También la aplicación de escritorio:

    pip install '.[gui]'
    optar-gui

## Comprobar que funciona { #check-that-it-works }

`optar --version` y `optar-gui --version` muestran la versión.

`optar-gui --self-test` inicia la aplicación sin pantalla y comprueba que
puede codificar y leer páginas.
