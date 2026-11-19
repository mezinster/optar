---
source_hash: e2c7112db6c41d20df8b36d2d29c2ab43a5ecb4a
---

# Installazione { #install }

## Download { #download }

Scarica il file per il tuo sistema dalla
[sezione Releases su GitHub](https://github.com/mezinster/optar/releases/latest).
Qui sotto `<tag>` è la versione, per esempio `v0.5.0`.

| Sistema | Applicazione desktop | Riga di comando |
|---|---|---|
| Linux | `optar-gui-<tag>-linux-x86_64` | `optar-<tag>-linux-x86_64` |
| macOS (Apple silicon) | `optar-gui-<tag>-macos-arm64.zip` | `optar-<tag>-macos-arm64` |
| Windows | `optar-gui-<tag>-windows-x86_64.exe` | `optar-<tag>-windows-x86_64.exe` |

Ognuno è un unico file e non richiede di installare nient'altro.

- **Linux:** prima esegui `chmod +x` sul file.
- **macOS:** esegui `chmod +x` sul file a riga di comando. Decomprimi
  l'applicazione e prova ad aprirla. I programmi non sono firmati, quindi
  macOS potrebbe rifiutarsi di aprirli: apri Impostazioni di Sistema, Privacy e
  sicurezza, e scegli «Apri comunque» (nelle versioni meno recenti di macOS,
  fai clic destro sull'applicazione e scegli Apri).
- **Windows:** i programmi non sono firmati, quindi Windows potrebbe mostrare
  un avviso al primo avvio.

## Dai sorgenti { #from-source }

Ti servono Python 3.12 o una versione successiva e una copia locale del repository.

Il programma a riga di comando (installa numpy e Pillow):

    pip install .

Anche l'applicazione desktop:

    pip install '.[gui]'
    optar-gui

## Controllare che funzioni { #check-that-it-works }

`optar --version` e `optar-gui --version` stampano la versione.

`optar-gui --self-test` avvia l'applicazione senza schermo e controlla che
sappia codificare e leggere pagine.
