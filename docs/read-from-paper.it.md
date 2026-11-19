---
source_hash: e79216aee6b95b8e8e6f807f3e335aa738ff2181
---

# Rileggere il file { #read-it-back }

## Scansione { #scanning }

- Scansiona in scala di grigi (256 livelli) o a colori. Non scansionare in
  bianco e nero.
- Disattiva qualsiasi modalità «documento» o di pulizia del testo. Rende i
  punti neri o bianchi prima che il programma li veda.
- Usa la risoluzione adatta alla dimensione dei punti: 600 dpi per i punti
  standard, dove 1200 dpi è leggermente meglio. Le altre sono nella
  [tabella delle dimensioni dei punti](put-on-paper.md#dot-size).
- Salva in PNG o TIFF. L'applicazione accetta anche BMP, PGM/PPM e JPEG. Il
  JPEG comprime con perdita ed è una scelta scadente. Non salvare le pagine in
  un unico PDF.
- Pulisci il vetro dello scanner e tieni la pagina ben piatta: un coperchio
  che non preme la carta lascia zone sfocate.

Una scansione fatta a una risoluzione troppo bassa riceve una nota che indica
la risoluzione da usare. È solo un consiglio: una scansione a bassa
risoluzione che si riesce a leggere viene usata comunque, e una che il metodo
di lettura normale non riesce a leggere viene passata a un
[secondo metodo di lettura, più lento](slower-reader.md).

## Nell'applicazione { #in-the-application }

Apri la scheda «Leggi da carta» e aggiungi le scansioni delle pagine
(«+ Aggiungi scansioni…», oppure trascina file o cartelle sulla scheda).

Il programma capisce da solo quale pagina è ogni scansione, su quale carta è
stata stampata e in che verso è. Quindi le scansioni si possono aggiungere in
qualsiasi ordine, capovolte o ruotate di lato. Ricava anche la dimensione dei
punti e la protezione; non c'è niente da impostare.

![Scansioni in lettura, ognuna con la sua barra di avanzamento e la sua fase](img/being-read.png)

L'elenco mostra una riga per pagina con il suo stato. Selezionando una riga
si vede la scansione con le zone danneggiate evidenziate: la rotellina
regola lo zoom, il trascinamento sposta, il doppio clic adatta la pagina alla
finestra.

Quando la barra in basso dice che il file è verificato, «Salva file…» lo
scrive.

Dall'elenco puoi:

- rimuovere una scansione;
- sostituire la scansione di una pagina, oppure usare una scansione di
  riserva di quella pagina al posto di quella in uso;
- passare a un altro documento, se le scansioni che hai aggiunto appartengono
  a più di una stampa;
- assegnare a mano a una pagina una scansione che non è stato possibile
  identificare;
- comporre un documento a mano, quando nessuna scansione si può identificare:
  indichi la carta e il numero di pagine, poi assegni ogni scansione alla sua
  pagina.

## Mentre una scansione è in lettura { #while-a-scan-is-being-read }

Ogni scansione che aggiungi compare sotto «In lettura» finché non è stata
letta, con una barra di avanzamento e la fase in cui si trova:

| Fase | Che cosa succede |
|---|---|
| In attesa | La scansione aspetta il suo turno. |
| Apertura del file | L'immagine viene caricata. |
| Ricerca della pagina | Il programma cerca il contorno di una pagina. |
| Identificazione della pagina | Prova ogni carta, dimensione dei punti e orientamento finché uno non corrisponde. |
| Lettura dei dati | I punti vengono letti e corretti. |
| Metodo lento: campionamento, poi «Metodo lento: passata 4 di 5» | Solo per una scansione di cui si occupa il [metodo lento](slower-reader.md). |

La barra conta le fasi, non i secondi: può fermarsi su una fase e poi fare un
salto, ma non torna mai indietro. «Rimuovi» interrompe la lettura della
scansione. Una volta letta, la scansione diventa la sua pagina, oppure
compare come illeggibile.

## Stati delle pagine { #page-states }

| Stato | Significato | Che cosa fare |
|---|---|---|
| Buona | La pagina è stata letta senza alcun errore da correggere. | Niente. |
| Riparata · N | N blocchi erano danneggiati e la correzione degli errori li ha riparati. I dati sono integri. | Niente. |
| Danneggiata · N persi | Non è stato possibile riparare N blocchi, quindi lì il file salvato contiene dati errati. | Scansiona di nuovo la pagina in scala di grigi alla risoluzione adatta alla sua dimensione dei punti e sostituisci la scansione. |
| Letta con il metodo lento | La risoluzione della scansione era troppo bassa per il metodo normale. Vedi [Scansioni a risoluzione troppo bassa](slower-reader.md). | Controlla che il documento superi la verifica. |
| Illeggibile | Non è stato possibile identificare la scansione: per esempio nell'immagine non c'è nessuna pagina di optar, oppure non è stato possibile leggere l'etichetta. | Scansionala di nuovo, oppure assegnala a mano a una pagina. |
| Mancante | Non è stata aggiunta nessuna scansione di questa pagina. | Aggiungine una. In un documento con protezione le altre pagine potrebbero bastare comunque, e in quel caso la barra lo dice. |

Una scansione fatta sotto i 400 dpi che non si riesce a leggere lo dice, per
esempio «Scansione fatta a circa 200 dpi, risoluzione troppo bassa per
leggerla», con la risoluzione che serve per ogni dimensione dei punti.

## La barra in basso { #the-bar-at-the-bottom }

La barra mostra lo stato dell'intero documento.

| La barra dice | Significato |
|---|---|
| File recuperato e verificato · N byte | Tutte le pagine sono state lette e il file recuperato corrisponde all'impronta sulla carta. |
| Non corrisponde all'impronta sulla carta | Tutte le pagine sono state lette, ma il file non è l'originale, perché alcuni dati sono stati decodificati in modo errato. Scansiona di nuovo le pagine, a cominciare da quelle indicate come «Riparata». |
| Recuperabile: manca la pagina 3, si può ricostruire dalle altre | Un documento con protezione: mancano delle pagine, ma quelle lette dovrebbero bastare a ricostruirle. |
| Recuperabile: manca la pagina 3, ricostruita dalle altre · corrisponde all'impronta | Questa riparazione è stata eseguita e controllata. Seguono la dimensione e che cosa ha fatto la riparazione. |
| Elaborazione… Scansioni lette: 3 su 6 | Ci sono ancora scansioni in lettura. Quando il documento ha già uno stato da mostrare, il conteggio lo segue: «File recuperato e verificato · N byte · Scansioni lette: 3 su 6». |
| Controllo dell'impronta… | Il controllo è in corso in background. |
| Lette tutte le pagine (N) · non verificabile (nessun contrassegno) | Le pagine vengono da un vecchio programma e non portano nessuna impronta. |
| Pagine buone: 4 su 6 · 1 danneggiata · 1 mancante | Negli altri casi, un conteggio. |

Per un documento con protezione la finestra mostra anche quanti byte ha
riparato la protezione e quanta della sua capacità di riparazione ha usato la
zona peggiore, per esempio «capacità di riparazione usata nella zona
peggiore: 57% (18 su 32), margine moderato».
Se la riparazione non riesce, la finestra
indica le pagine da aggiungere o da scansionare di nuovo.

!!! info "Che cosa significa «verificato»"
    «Verificato» significa sempre che l'impronta del file recuperato
    corrispondeva a quella sulla carta. Non significa mai soltanto che la
    riparazione non ha segnalato errori.

## Salvataggio { #saving }

«Salva file…» chiede una conferma quando il file non è verificato, e dice che
cosa non va.

Un documento con protezione che non è stato possibile riparare si può
comunque salvare per la parte recuperata, dopo un avviso che il file potrebbe
contenere parti errate. Questo è possibile solo quando è stata letta almeno
metà delle sue pagine: con meno pagine non viene salvato nulla.

## Stampe di vecchi programmi { #printouts-from-old-programs }

Le stampe di optar 0.1.0 o del programma in C non hanno nessun contrassegno
nell'etichetta. L'applicazione le legge, ma:

- non può sapere se le pagine vanno insieme né se il file è completo;
- non può verificare il file;
- il file salvato è completato con zeri fino a una pagina intera.

Salva un file del genere solo dopo aver letto l'avvertenza che l'applicazione
mostra.
