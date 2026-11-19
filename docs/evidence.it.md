---
source_hash: 34c3bf2795da00caec5ecf72aeb5391c9d6f4e57
---

# Che cosa è stato mostrato e che cosa no { #what-has-and-has-not-been-shown }

Questa sezione dice su che cosa si basano le affermazioni del progetto. Per
lo più vengono da scansioni simulate, non dalla carta.

## Scansioni simulate { #simulated-scans }

I test automatici leggono immagini generate con sfocatura, rumore e
rotazione. La sfocatura simulata è stata adattata a tre scansioni reali a
300 dpi di una pagina stampata, fatte con una stampante e uno scanner con
alimentatore di fogli.

- Con quella sfocatura i punti standard non sono stati decodificati a 300 dpi
  con il metodo normale.
- I punti medi con protezione standard hanno superato la verifica a 300 dpi e
  a 200 dpi.
- I punti grandi, grossi e molto grossi hanno superato la verifica a 200 dpi
  senza errori.
- Un documento di 12 pagine ha superato la verifica con una pagina tolta.

## Il metodo lento { #the-slower-reader }

Il [metodo lento](slower-reader.md) è stato mostrato su un documento reale e
su uno simulato.

**Reale.** Il documento del proprietario del progetto: sei pagine A4, punti
standard, protezione alta, scansionate a circa 290 dpi dove sono consigliati
600 dpi. Il metodo normale non ha identificato nessuna delle pagine. Con il
metodo lento il file è stato recuperato e verificato dalla sua impronta:
759.879 byte, di cui 41.495 byte riparati dalla protezione del documento; il
blocco peggiore ha usato 40 della sua capacità di riparazione di 64. Si
tratta di un documento, una stampante, uno scanner e una risoluzione. Le
scansioni non fanno parte del repository.

**Simulato** (`tests/unit/test_coarse_claim.py`). Un documento di due pagine
dello stesso tipo, scansionato a 290 e a 300 dpi con una sfocatura di 1,8
punti della stampante. A 290 dpi il metodo normale non identifica nessuna
delle due pagine; a 300 dpi legge l'etichetta di ogni pagina ma nessuna
intestazione. In entrambi i casi il file supera la verifica con il metodo
lento. Con la sfocatura predefinita del simulatore (1,0) il metodo normale
legge da solo una pagina del genere a 300 dpi.

Il simulatore è più indulgente dello scanner del proprietario: a 290 dpi
nella simulazione il metodo lento non ha riparato niente, mentre il documento
reale ha richiesto la riparazione di 41.495 byte.

La protezione standard ha una capacità di riparazione di 32, sotto i 40 di
cui aveva bisogno il blocco peggiore del documento reale. Quindi un documento
con protezione standard scansionato in questo modo dovrebbe fallire. Le
vecchie pagine nello stile della 0.2 non sono coperte dal metodo lento.

## Che cosa non è stato mostrato { #what-is-not-shown }

- Finora non è stata letta nessuna scansione reale di una pagina con punti
  più grandi.
- La lettura delle etichette e la decodifica hanno test automatici solo su
  scansioni sintetiche, non su pagine reali stampate e scansionate. Questo
  vale per ogni stampa con punti più grandi o con protezione.
- Gli scanner con alimentatore di fogli non sono stati provati, salvo il fatto
  che il programma trova la griglia di punti su tre scansioni reali.
- Tre scansioni reali a 300 dpi di una stampa misuravano circa 286 dpi, il che
  significa che quella stampa è uscita a circa il 95% della dimensione reale.
  I punti più piccoli sono più difficili da leggere, quindi stampa a
  dimensione reale (100%).
- Le stampanti a getto d'inchiostro non sono state provate.

## Le stesse pagine del programma in C { #the-same-pages-as-the-c-program }

Le pagine del codificatore Python sono identiche byte per byte all'output
dell'`optar` originale in C per A4, Letter e tutte e cinque le modalità di
correzione degli errori. Le posizioni delle croci e i bit campionati del
decodificatore Python sono identici bit per bit a quelli di `unoptar` in C
sulle immagini di prova sintetiche. Entrambe le cose sono controllate rispetto
a output dei programmi in C registrati una volta sola e conservati in
`tests/vectors`.

Ogni pagina di una stampa autoidentificante è comunque una normale pagina di
optar: un `unoptar` in C compilato con la stessa dimensione della griglia ne
legge esattamente i punti (registrato per i punti grossi su A4 e per i punti
medi su Letter). Quello che restituisce sono i dati con le informazioni
aggiuntive e la protezione avvolte attorno al file, non il file.
