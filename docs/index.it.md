---
source_hash: e97cf214a68552056382e38b7773d047576c8f46
---

# optar { #optar }

optar conserva un file su carta. Stampa il file con una stampante laser a
600 dpi come pagine di piccoli punti bianchi e neri, e rilegge il file dalle
scansioni di quelle pagine.

![L'applicazione dopo aver letto due pagine: entrambe buone, il file verificato](img/verified.png)

- **Una pagina A4 contiene circa 200.000 byte** con la dimensione dei punti
  standard.
- **Si possono scegliere punti più grandi**, in modo che basti uno scanner a
  200 dpi; una pagina allora contiene meno dati.
- **La protezione** è un insieme di dati aggiuntivi distribuiti su tutte le
  pagine. Con la protezione il programma ripara macchie e angoli strappati e,
  in un documento abbastanza lungo, ricostruisce una pagina persa.
- **Un'impronta** del file viene stampata insieme al file. Il file recuperato
  si dice verificato solo quando corrisponde a quell'impronta.

I programmi sono due e usano lo stesso codice:

- `optar-gui`, un'applicazione desktop per Linux, macOS e Windows;
- `optar`, un programma a riga di comando.

## Da dove cominciare { #where-to-start }

| Vuoi | Leggi |
|---|---|
| Ottenere i programmi | [Installazione](install.md) |
| Stampare un file | [Scrivere un file su carta](put-on-paper.md) |
| Recuperare un file da una stampa | [Rileggere il file](read-from-paper.md) |
| Leggere scansioni fatte a una risoluzione troppo bassa | [Scansioni a risoluzione troppo bassa](slower-reader.md) |
| Usarlo dagli script | [Riga di comando](command-line.md) |
| Sapere quanto fidarti | [Che cosa è stato mostrato e che cosa no](evidence.md) |
| Scrivere un tuo programma di lettura o un tuo codificatore | [Specifica del formato](format.md) |

## In breve { #in-short }

1. Nell'applicazione apri «Scrivi su carta», scegli il file e crea il PDF.
2. Stampa il PDF a dimensione reale (100%), non con «Adatta alla pagina», su
   una stampante laser a 600 dpi.
3. Per recuperare il file, scansiona le pagine in scala di grigi come PNG o
   TIFF, alla risoluzione adatta alla dimensione dei punti (600 dpi per i
   punti standard).
4. Apri «Leggi da carta», aggiungi le scansioni in qualsiasi ordine e salva il
   file quando la barra in basso dice che è verificato.

## Da dove viene { #where-it-comes-from }

optar è stato scritto in C da Karel 'Clock' Kulhavy di Twibright Labs nel
2007. Questo progetto è una versione in Python che legge e scrive le stesse
pagine e aggiunge l'applicazione desktop, i punti più grandi, la protezione e
l'impronta. Vedi la sezione [Storia](history.md).
