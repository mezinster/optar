---
source_hash: fc438b9b7896988d42b22d54829293c774aa20c2
---

# Riga di comando { #command-line }

Il comando `optar` codifica un file in pagine e decodifica le scansioni per
riottenerlo. Non richiede un compilatore C, né libpng, né ImageMagick.

    optar encode INPUT [-o BASE] [--paper a4|letter] [--to pdf|png|pgm] [--label TEXT] [--no-tag]
                 [--dots standard|medium|big|large|xlarge] [--protect none|standard|high]
                 [--compatible] [--format STRING]
    optar decode BASE [-o OUTPUT] [--paper a4|letter] [--format STRING] [--debug-images] [--force]
                 [--no-slow-reader]
    optar --version

## encode { #encode }

`encode` scrive per impostazione predefinita `BASE.pdf` (`BASE` vale
`optar_out` se non indicato), oppure, con `--to`, le pagine `BASE_0001.png`
(o `.pgm`), `BASE_0002.png`, ...

| Indichi | Ottieni |
|---|---|
| né `--dots` né `--protect`, oppure `--compatible` | una stampa che la 0.2.0 e il programma in C sanno leggere: punti standard, nessuna protezione |
| solo `--dots X` | quella dimensione dei punti con la protezione standard |
| solo `--protect LEVEL` | punti standard con quella protezione |
| `--protect none` | nessuna protezione |

Ciascuno degli ultimi tre casi produce pagine autoidentificanti (pagine che
dicono da sole a quale documento appartengono e che numero hanno), che per
essere lette richiedono optar 0.3 o successivo. Per esempio:

    optar encode photo.jpg -o photo --dots large --protect high

Le dimensioni dei punti e i livelli di protezione sono descritti nella sezione
[Scrivere un file su carta](put-on-paper.md#dot-size).

Una stampa compatibile porta un [contrassegno](identification.md#the-tag) su
ogni pagina; aggiungi `--no-tag` per ometterlo.

`--paper` è A4 se non indicato.

## decode { #decode }

`decode` legge `BASE_0001.png`, `BASE_0002.png`, ... e scrive i dati in
`-o OUTPUT`, oppure su stdout. Legge solo file con quei nomi.

Che cosa fa dipende dalla stampa. Lo decide dalle prime tre scansioni: se
nessuna di esse si può identificare come pagina autoidentificante, tratta
l'insieme come una stampa della 0.2.0 o precedente.

### Pagine autoidentificanti { #self-identifying-pages }

`decode` ricava dalle scansioni stesse che cosa sono.

- Accetta le scansioni in qualsiasi ordine e con qualsiasi orientamento.
- Una scansione che non riesce a leggere conta come pagina mancante.
- Una scansione che il metodo normale non riesce a identificare viene prima
  passata al [metodo lento](slower-reader.md), a meno che tu non indichi
  `--no-slow-reader`.
- Ripara i dati, li taglia alla loro vera dimensione e controlla l'impronta.
- Scrive il file solo se l'impronta corrisponde, a meno che tu non indichi
  `--force`, che salva quanto è stato recuperato anche se non ha superato la
  verifica. Anche con `--force` non viene salvato nulla se è stata letta meno
  della metà delle pagine.

### Stampe della 0.2.0 o precedenti { #printouts-from-020-or-earlier }

- `--paper` deve essere lo stesso usato per la codifica.
- La pagina deve essere dritta (verticale, etichetta in basso). Le scansioni
  orizzontali qui non sono supportate, cosa ereditata dal decodificatore in C.
  L'applicazione desktop accetta qualsiasi orientamento per ogni stampa.
- `decode` non taglia i dati in uscita alla dimensione indicata nel
  contrassegno e non controlla l'impronta: i dati in uscita sono sempre
  completati con zeri fino a una pagina intera. L'applicazione desktop fa entrambe le cose. Se i tuoi dati ne
  risentono, impacchettali con tar.
- `--force` non cambia nulla, e `decode` lo dice.

## Codice di uscita { #exit-status }

| Codice | Significato |
|---|---|
| 0 | Successo. Per le pagine autoidentificanti: il file ha superato la verifica. |
| 1 | I dati sono stati decodificati ma non sono correggibili, oppure c'è un buco nella numerazione delle pagine, oppure (pagine autoidentificanti) il file non ha superato la verifica. |
| 2 | Un errore d'uso o di input. |

## Il codice a correzione d'errore { #the-error-correcting-code }

Il codice predefinito è il codice di Golay 24/12. Sono supportati anche i
codici di Hamming di ordine da 2 a 5, scelti con `--format` (il sesto campo
della stringa di formato). La [specifica del formato](format.md) definisce la
stringa di formato.
