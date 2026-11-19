---
source_hash: bceb221e5e7d1915ae0d3656ce9713f5c5f1cdeb
---

# Scrivere un file su carta { #put-a-file-on-paper }

## Nell'applicazione { #in-the-application }

Apri la scheda «Scrivi su carta».

![La scheda «Scrivi su carta» con un file scelto](img/put-on-paper.png)

1. Scegli un file, oppure trascinalo sulla scheda.
2. Scegli A4 o US Letter.
3. Scegli la [dimensione dei punti](#dot-size) e la [protezione](#protection).
   La finestra parte con punti standard e protezione standard.
4. Dai un nome al file. La riga «Stampato come:» mostra il testo che verrà
   stampato su ogni pagina.
5. Leggi la riga sotto: indica quante pagine servono per il file e, con la
   protezione, quante di quelle pagine si possono perdere.
6. «Crea PDF…» salva il PDF.

Se spunti «Compatibile con optar 0.2 e con l'optar originale», ottieni una
stampa che quei programmi più vecchi sanno leggere. Ha punti standard e
nessuna protezione.

Dalla riga di comando, vedi [`optar encode`](command-line.md#encode).

## Stampa { #printing }

Stampa il PDF a dimensione reale (100%), non con «Adatta alla pagina», su una
stampante laser a 600 dpi. Le stampanti a getto d'inchiostro non sono state
provate.

Una stampa che esce più piccola della dimensione reale ha punti più piccoli,
che sono più difficili da leggere. Una stampa reale misurava circa il 95%
della dimensione reale.

## Dimensione dei punti { #dot-size }

La dimensione dei punti è la grandezza con cui viene stampato ogni punto di
dati. I punti più grandi resistono a una scansione a risoluzione più bassa, ma
una pagina ne contiene meno, quindi contiene meno dati. Un punto di dati è
formato da 3, 4, 5, 6 o 9 punti di una stampante a 600 dpi.

La tabella indica la risoluzione di scansione da usare (tre pixel della
scansione per ogni punto di dati) e i byte che una pagina contiene prima di
aggiungere la protezione:

| Dimensione dei punti | Opzione | Punti della stampante per punto di dati | Scansiona a | Pagina A4 | Pagina Letter |
|---|---|---|---|---|---|
| Standard | `standard` | 3 | 600 dpi | 199.773 | 192.591 |
| Medi | `medium` | 4 | 450 dpi | 114.904 | 110.463 |
| Grandi | `big` | 5 | 360 dpi | 73.027 | 69.463 |
| Grossi | `large` | 6 | 300 dpi | 49.119 | 48.403 |
| Molto grossi | `xlarge` | 9 | 200 dpi | 21.606 | 21.127 |

Scegli la dimensione dei punti in base allo scanner che leggerà le pagine,
magari tra molti anni. Se non lo sai, i punti più grandi sono la scelta più
sicura.

## Protezione { #protection }

La protezione è un insieme di dati aggiuntivi, distribuiti su tutte le pagine
del documento, con cui il programma ripara le zone danneggiate e ricostruisce
le pagine perse. Le scelte sono Nessuna, Standard e Alta.

- Costa carta: la protezione standard aggiunge circa il 14% di pagine in più e
  quella alta circa il 34%.
- I dati aggiuntivi sono distribuiti in modo che una macchia, un angolo
  strappato o una pagina mancante costino a ogni parte del file all'incirca la
  stessa piccola quantità. È questa piccola quantità che la protezione ripara.
- Con la protezione, una parte delle pagine porta i dati della protezione, e
  ogni pagina ripete un breve record che dice a quale documento appartiene e
  che pagina è. Per questo al file resta meno spazio di quanto mostra la
  tabella qui sopra.

### Perdere una pagina intera { #losing-a-whole-page }

La finestra e `optar encode` promettono che una pagina persa si può recuperare
solo per i documenti abbastanza lunghi, e in quel caso dicono «si può perdere
N pagina su T» o «si possono perdere N pagine su T».

| Protezione | Si può perdere 1 pagina a partire da | Si possono perdere 2 pagine a partire da |
|---|---|---|
| Standard | 12 pagine | 24 pagine |
| Alta | 6 pagine | 12 pagine |

Al di sotto, i danni all'interno delle pagine vengono riparati, ma perdere una
pagina intera significa perdere il file. La promessa è volutamente prudente, e
un documento può recuperare più di quanto promette.

### Il file più grande { #the-largest-file }

Un file la cui stampa con protezione occuperebbe su carta più di 256 MiB viene
rifiutato. La finestra dice allora se il file entrerebbe senza protezione o
con punti più piccoli.

## Quali programmi sanno leggere la stampa { #which-programs-can-read-the-printout }

| Stampa | Letta da |
|---|---|
| Qualsiasi dimensione dei punti tranne quella standard, o qualsiasi protezione | optar 0.3 o successivo. In lettura non c'è niente da impostare. |
| Punti standard, nessuna protezione, «Compatibile» spuntato | ogni versione, e il programma in C originale |

L'applicazione 0.2.0 non sa leggere affatto le pagine con punti più grandi.
Per i punti standard con protezione, la 0.2.0 e il programma in C restituiscono
i dati avvolti nelle informazioni aggiuntive e nella protezione, non il file.

Le ragioni sono nella sezione
[Come si identifica una pagina](identification.md).

!!! note "I file di una stampa compatibile sono completati con zeri"
    Una stampa fatta per la 0.2 e i programmi più vecchi non conserva nei
    suoi dati la lunghezza del file; ce l'ha solo il contrassegno
    nell'etichetta. `optar decode` a riga di comando e il programma in C
    restituiscono un file del genere completato con zeri fino a una pagina
    intera. Se i tuoi dati ne risentono, impacchettali con tar.
