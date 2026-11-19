---
source_hash: 2249212b8920c7b2d504e467f61c20e86e4b2d9d
---

# Come si identifica una pagina { #how-a-page-identifies-itself }

Per ogni scansione il programma deve sapere a quale documento appartiene e
che pagina è. Una pagina può dirlo in due modi, a seconda di come è stata
fatta la stampa.

| Stampa | Identificata da |
|---|---|
| Fatta con protezione, o con qualsiasi dimensione dei punti tranne quella standard | un'intestazione nei dati della pagina («pagine autoidentificanti»: pagine che dicono da sole a quale documento appartengono e che numero hanno) |
| Stampa compatibile della 0.2.0 o successiva | il contrassegno nell'etichetta in fondo |
| Della 0.1.0 o del programma in C | la sola etichetta, che non ha niente con cui essere controllata |

Un contrassegno valido nell'etichetta vince sempre: una pagina la cui
etichetta ha un contrassegno valido viene letta come pagina della 0.2.0,
qualunque cosa contengano i suoi dati.

## Pagine autoidentificanti { #self-identifying-pages }

Le pagine di una stampa fatta con protezione, o con qualsiasi dimensione dei
punti tranne quella standard, portano nei loro dati le informazioni sul
documento: a quale stampa appartengono, il loro numero, il numero di pagine,
la dimensione del file e la sua impronta.

L'etichetta stampata in fondo è per le persone e non serve a identificarle.
In un PDF viene stampata a una sola grandezza, qualunque sia la dimensione dei
punti (la grandezza dell'etichetta di una pagina standard), così che l'intera
riga ci stia. È però troppo piccola per essere letta da una scansione a bassa
risoluzione, e la finestra mostra «(senza nome)» finché il file non viene
recuperato e non se ne conosce il vero nome. Le pagine PNG e PGM hanno un
pixel per punto, quindi la loro etichetta è disegnata con i punti della pagina
e cresce insieme a loro.

Lo spazio che un documento del genere non usa viene riempito con un motivo
fisso che sembra fatto di dati, così che ogni pagina venga stampata in modo
uniforme. La versione 0.3.0 lo riempiva di zeri, che venivano stampati come
righe bianche attraverso le pagine. Entrambi si leggono, anche con la 0.3.0:
nessun programma di lettura guarda il riempimento.

L'intestazione di una pagina, da sola, non è affidabile: una singola pagina
scansionata potrebbe dichiarare di appartenere a qualsiasi documento. Solo
l'impronta del file recuperato lo rende verificato.

## L'etichetta { #the-label }

Ogni pagina ha un'etichetta in fondo: il formato di pagina, il numero della
pagina e il numero di pagine, poi un testo libero. Per le stampe della 0.2.0
e precedenti l'applicazione legge questa etichetta dalla scansione.

- Un'etichetta con contrassegno viene accettata quando la lettura è
  plausibile, il controllo del contrassegno corrisponde al numero della
  pagina e al numero di pagine, e la dimensione del file indicata nel
  contrassegno è compatibile con quel numero di pagine.
- Un'etichetta senza contrassegno (stampe fatte dalla 0.1.0 o dal programma
  in C) non ha niente con cui essere controllata, quindi viene accettata solo
  quando si legge con chiarezza.
- Un'etichetta che sembra un contrassegno con un carattere danneggiato viene
  rifiutata.

Una scansione rifiutata compare come «Illeggibile» con il motivo, e puoi
assegnarla a mano a una pagina.

## Il contrassegno { #the-tag }

Dalla 0.2.0, `optar encode` e l'applicazione stampano un contrassegno
all'inizio del testo libero di ogni pagina di una stampa compatibile, nella
forma `[SIZE:FINGERPRINT:CC]`.

| Parte | Significato |
|---|---|
| `SIZE` | la dimensione del file in byte |
| `FINGERPRINT` | le prime 8 cifre esadecimali dello SHA-256 del file |
| `CC` | un controllo di due cifre esadecimali che dipende dal numero della pagina e dal numero di pagine |

Il contrassegno permette all'applicazione di:

- tenere separate le pagine di stampe diverse;
- rifiutare un'etichetta con contrassegno la cui dimensione non è compatibile
  con il numero di pagine;
- rifiutare una scansione la cui etichetta è stata letta male, invece di
  assegnarla alla pagina sbagliata (circa 1 lettura errata su 256 può
  comunque superare il controllo);
- tagliare il file recuperato alla sua vera dimensione, così che non abbia
  zeri di riempimento;
- confrontare il file recuperato con l'impronta, che è il controllo finale
  che il file sia l'originale.

Per stampare senza contrassegno, usa `optar encode --no-tag`. Le pagine che
si identificano dai propri dati non stampano nessun contrassegno.

Le definizioni esatte sono nella [specifica del formato](format.md): la parte
3 per il contrassegno e la parte 4 per i documenti autoidentificanti.
