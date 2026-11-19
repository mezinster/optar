---
source_hash: 116c27601de6c43ed57c443b775aafdc63d50d6c
---

# Il formato optar { #the-optar-format }

Il testo normativo di questa specifica è quello inglese, [The optar format](https://mezinster.github.io/optar/format/): il formato è definito da esso e dai vettori di test in `tests/vectors`. Questa traduzione è informativa; se differisce dal testo inglese, vale il testo inglese.

optar conserva un file su carta sotto forma di pagine di punti neri e bianchi.
Questa specifica definisce che cos'è una pagina e che cos'è un documento (un
insieme di pagine che porta un file), in modo che si possa scrivere un
codificatore le cui pagine questo progetto legge, e un decodificatore che legge
le pagine di questo progetto.

La specifica si compone di otto parti:

1. Termini e convenzioni
2. La pagina (versione 0)
3. Il contrassegno del documento (stampe 0.2.0)
4. Documenti autoidentificanti (versione 1)
5. Stampa
6. Che cosa deve fare un programma di lettura
7. Decodificatore di riferimento (informativo)
8. Storia

Le parti da 1 a 6 sono normative. Il verbo «dovere» (*must*) si usa solo per
ciò che una pagina o un documento è e, nella parte 6, per ciò che un programma
di lettura fa con quanto ha letto. Il modo in cui un programma di lettura trova
una pagina in una scansione e la campiona non fa parte del formato; la parte 7
descrive come lo fa questo progetto.

Il formato è fissato dai vettori di test in `tests/vectors`. Ogni sezione
normativa termina con una riga «Vettori:» che nomina i file che la fissano;
`tests/vectors/README.md` spiega come si legge ciascun file. Le tabelle
precedute da un commento `spec-table` e i blocchi delimitati marcati `example`
sono confrontati con il codice da `tests/unit/test_spec.py`.

## 1. Termini e convenzioni { #1-terms-and-conventions }

### 1.1 Numeri, bit e byte { #11-numbers-bits-and-bytes }

- Tutti gli interi sono scritti in decimale, salvo quelli con il prefisso `0x`.
- `a // b` è la divisione arrotondata per difetto, `a mod b` il suo resto,
  `ceil(a / b)` la divisione arrotondata per eccesso. Tutte e tre si usano solo
  su interi non negativi.
- I conteggi e gli indici partono da 0, tranne i numeri di pagina e le facce
  del dodecaedro della sezione 2.5, che partono da 1.
- Una **stringa di bit** si legge a partire dal bit più significativo: il bit
  `n` di una stringa di byte è il bit `7 - (n mod 8)` del byte `n // 8`, dove
  il bit 7 di un byte è il suo bit più significativo. Una parola di `w` bit
  presa da una stringa di bit ha come bit più significativo il primo bit della
  stringa.
- Gli interi di più byte nell'intestazione (sezione 4.2) sono big-endian:
  prima il byte più significativo.
- SHA-256 e CRC-32 sono le funzioni consuete. Il CRC-32 è quello di zlib, PNG
  ed Ethernet: polinomio riflesso `0xEDB88320`, valore iniziale e XOR finale
  `0xFFFFFFFF`.

### 1.2 Pixel e colori { #12-pixels-and-colours }

- Una **pagina** è un'immagine rettangolare di **pixel della pagina**. Ogni
  pixel della pagina è nero oppure bianco.
- Un pixel di dati nero è il bit 1; un pixel di dati bianco è il bit 0.
- Nei file di immagine in scala di grigi a 8 bit un pixel nero ha il valore 0
  e un pixel bianco il valore 255. Questa specifica non usa nessun'altra
  codifica delle immagini.
- Le coordinate della pagina sono `(x, y)`: `x` conta le colonne dal lato
  sinistro, `y` conta le righe dal lato superiore, entrambe da 0. La pagina si
  stampa e si legge diritta, con la banda dell'etichetta (sezione 2.8) in
  basso.
- Le **coordinate dell'area dei dati** `(u, v)` escludono il bordo (sezione
  2.2): `u = x - border`, `v = y - border`.

### 1.3 Unità { #13-units }

- Un **punto tipografico** (pt) è 1/72 di pollice.
- Un **punto della stampante** è 1/600 di pollice: un punto del dispositivo
  della stampante a 600 dpi per cui sono fatti i layout.
- Un **punto di dati** è un pixel della pagina così come viene stampato. È un
  quadrato di un numero intero di punti della stampante (sezione 5.1). Il punto
  di dati **standard** è largo 3 punti della stampante, 1/200 di pollice.

### 1.4 Tipi di documento { #14-kinds-of-document }

Un **flusso** è la stringa di byte che le pagine di un documento portano nei
loro pixel di dati. Esistono tre tipi di documento; tutti e tre sono fatti
delle stesse pagine di versione 0 (parte 2).

| Tipo | Scritto da | Il flusso è | L'etichetta porta |
|---|---|---|---|
| semplice | il programma in C, optar 0.1.0, `--no-tag` | il file | solo testo libero |
| con contrassegno | optar 0.2.0, e le versioni successive nella loro stampa «compatibile» | il file | il contrassegno (parte 3) |
| autoidentificante | optar 0.3.0 e successivi | il contenitore (parte 4) | solo testo libero |

### 1.5 Costanti { #15-constants }

I nomi di questa tabella sono usati in tutta la specifica.

<!-- spec-table: constants -->
| Nome | Valore | Significato |
|---|---|---|
| `PageFormat.version` | 0 | versione del formato di pagina |
| `PageFormat.cpitch` | 24 | distanza tra le origini delle croci, in pixel della pagina |
| `PageFormat.chalf` | 3 | metà del lato di una croce, in pixel della pagina |
| `PageFormat.fec_order` | 1 | codice di pagina: 1 è il codice di Golay, da 2 a 5 sono codici di Hamming |
| `PageFormat.border` | 2 | spessore del bordo, in pixel della pagina |
| `PageFormat.text_height` | 24 | righe della banda dell'etichetta |
| `LABEL_HEIGHT` | 24 | l'unica altezza della banda dell'etichetta che si può disegnare |
| `TEXT_WIDTH` | 13 | larghezza di una cella del carattere dell'etichetta, in pixel dell'etichetta |
| `FIRST_CHAR` | 32 | codice del carattere della prima cella della striscia del font |
| `GLYPH_CELLS` | 95 | celle dei caratteri nella striscia del font |
| `MAX_PAGES` | 9999 | numero massimo di pagine di un documento |
| `FINGERPRINT_DIGITS` | 8 | cifre esadecimali dell'impronta in un contrassegno |
| `CHECK_DIGITS` | 2 | cifre esadecimali del controllo in un contrassegno |
| `MAX_SIZE_DIGITS` | 12 | numero massimo di cifre decimali della dimensione in un contrassegno |
| `HEADER_MAGIC` | "oPt1" | primi quattro byte di un'intestazione, in ASCII |
| `CONTAINER_VERSION` | 1 | byte di versione di un'intestazione |
| `HEADER_SIZE` | 38 | byte di una copia dell'intestazione |
| `HEADER_COPIES` | 5 | copie dell'intestazione in ogni pagina |
| `FINGERPRINT_SIZE` | 16 | byte dell'impronta in un'intestazione |
| `CODEWORD` | 255 | byte di una parola di codice Reed-Solomon |
| `SPREAD_STEP` | 7919 | incremento della distribuzione (sezione 4.6) |
| `NAME_MAX_BYTES` | 255 | numero massimo di byte del nome del file memorizzato |
| `PADDING_KEY` | "optar padding" | chiave del flusso di riempimento, in ASCII |
| `PADDING_BLOCK` | 32 | byte di un blocco del flusso di riempimento |
| `PROTECTED_MAX_BYTES` | 268435456 | numero massimo di byte di pagina di un documento con parità |
| `PROMISE_NUM` | 3 | numeratore della quota di parità su cui si basa la promessa degli strumenti (4.9) |
| `PROMISE_DEN` | 4 | denominatore di quella quota |
| `PRINTER_DPI` | 600 | punti della stampante per pollice |
| `PIXELS_PER_INCH` | 200 | punti di dati standard per pollice |
| `STANDARD_PRINTER_DOTS` | 3 | punti della stampante sulla larghezza di un punto di dati standard |
| `POINTS_PER_INCH` | 72 | punti tipografici per pollice |
| `SCAN_PIXELS_PER_DOT` | 3 | pixel della scansione per punto di dati alla risoluzione di scansione consigliata |
| `MIN_MARGIN_PT` | 12 | margine minimo attorno a una pagina stampata, in pt |

## 2. La pagina (versione 0) { #2-the-page-version-0 }

### 2.1 Il formato di pagina e la stringa di formato { #21-the-page-format-and-the-format-string }

Un **formato di pagina** è composto da otto interi non negativi:

| Campo | Nome | Significato | Deve essere |
|---|---|---|---|
| 1 | `version` | versione del formato di pagina | 0 |
| 2 | `xcrosses` | croci in una riga | almeno 2 |
| 3 | `ycrosses` | croci in una colonna | almeno 2 |
| 4 | `cpitch` | distanza tra le origini delle croci | maggiore di `2 * chalf` |
| 5 | `chalf` | metà del lato di una croce | almeno 1 |
| 6 | `fec_order` | codice di pagina | da 1 a 5 |
| 7 | `border` | spessore del bordo | almeno 1 |
| 8 | `text_height` | righe della banda dell'etichetta | `LABEL_HEIGHT` |

La **stringa di formato** è composta dagli otto campi in quest'ordine, in
decimale senza zeri iniziali, uniti da `-`. Ogni pagina stampa la propria
stringa di formato nell'etichetta (sezione 2.8). Le pagine che questo progetto
stampa differiscono solo in `xcrosses` e `ycrosses`; gli altri campi hanno i
valori della sezione 1.5. I dieci formati di pagina che stampa sono elencati
nella sezione 5.2. Altri valori danno pagine valide, che vengono lette quando
al programma di lettura si fornisce la stringa di formato.

Tutte le dimensioni che seguono sono in pixel della pagina.

    data_width  = cpitch * (xcrosses - 1) + 2 * chalf
    data_height = cpitch * (ycrosses - 1) + 2 * chalf
    width       = 2 * border + data_width
    height      = 2 * border + data_height + text_height

```example
a4_data_width = 1542
a4_data_height = 2214
a4_width = 1546
a4_height = 2242
```

I nomi con il prefisso `a4_` si riferiscono al formato `0-65-93-24-3-1-2-24`,
la pagina A4 standard.

Vettori: `tests/vectors/c/encoder_pages.json`.

### 2.2 Le parti di una pagina { #22-the-parts-of-a-page }

Una pagina è larga `width` colonne e alta `height` righe. Dall'alto in basso:

| Righe `y` | Contenuto |
|---|---|
| da `0` a `border - 1` | bordo: nero |
| da `border` a `border + data_height - 1` | colonne da `0` a `border - 1` e le ultime `border` colonne: nere. Tra di esse: l'**area dei dati**, `data_width` colonne |
| da `border + data_height` a `border + data_height + text_height - 1` | la **banda dell'etichetta**: nera su tutta la larghezza, con l'etichetta disegnata in bianco nelle colonne da `border` a `border + data_width - 1` (sezione 2.8) |
| le ultime `border` righe | bordo: nero |

```example
a4_label_top_row = 2216
```

Ogni pixel dell'area dei dati fa parte di una croce (sezione 2.3) oppure è un
pixel di dati (sezione 2.4).

Vettori: `tests/vectors/c/encoder_pages.json`.

### 2.3 Croci { #23-crosses }

L'area dei dati contiene `xcrosses * ycrosses` **croci**, che un programma di
lettura usa per trovare i pixel di dati. La croce `(i, j)`, `0 <= i < xcrosses`,
`0 <= j < ycrosses`, è il quadrato di `2 * chalf` per `2 * chalf` pixel il cui
pixel in alto a sinistra, la sua **origine**, si trova alle coordinate dell'area
dei dati `(i * cpitch, j * cpitch)`. I suoi quattro quarti di `chalf` per
`chalf` pixel sono:

| Quarto | Colore |
|---|---|
| in alto a sinistra | nero |
| in alto a destra | bianco |
| in basso a sinistra | bianco |
| in basso a destra | nero |

La prima croce tocca l'angolo in alto a sinistra dell'area dei dati e l'ultima
l'angolo in basso a destra. Un pixel `(u, v)` dell'area dei dati fa parte di una
croce esattamente quando `u mod cpitch < 2 * chalf` e `v mod cpitch < 2 * chalf`.

```example
a4_last_cross_x = 1538
a4_last_cross_y = 2210
```

Queste sono le coordinate della pagina `(x, y)` dell'origine dell'ultima croce.

Vettori: `tests/vectors/c/encoder_pages.json`.

### 2.4 I pixel di dati e il loro ordine { #24-data-pixels-and-their-order }

I **pixel di dati** sono i pixel dell'area dei dati che non fanno parte di una
croce. Sono numerati da 0 in ordine di lettura: riga per riga dall'alto e,
all'interno di una riga, da sinistra a destra. Il numero di un pixel di dati è
la sua **posizione nel canale**; `total_bits` è il numero dei pixel di dati.

Le righe dell'area dei dati si ripetono con periodo `cpitch`:

- una **striscia stretta** di `2 * chalf` righe che attraversano le croci. Ogni
  riga contiene `narrow_width` pixel di dati, in `xcrosses - 1` intervalli di
  `gap_width` pixel tra le croci;
- una **striscia larga** di `gap_width` righe senza croci. Ogni riga contiene
  `data_width` pixel di dati.

L'ultimo periodo ha solo una striscia stretta.

    gap_width     = cpitch - 2 * chalf
    narrow_width  = gap_width * (xcrosses - 1)
    narrow_pixels = 2 * chalf * narrow_width
    wide_pixels   = gap_width * data_width
    rep_pixels    = narrow_pixels + wide_pixels
    total_bits    = rep_pixels * (ycrosses - 1) + narrow_pixels

Le coordinate dell'area dei dati `(u, v)` della posizione nel canale `n` sono:

    rep = n // rep_pixels
    s   = n mod rep_pixels
    if s < narrow_pixels:                      (narrow strip)
        row = s // narrow_width
        r   = s mod narrow_width
        u   = 2 * chalf + (r // gap_width) * cpitch + r mod gap_width
        v   = rep * cpitch + row
    else:                                      (wide strip)
        s   = s - narrow_pixels
        u   = s mod data_width
        v   = rep * cpitch + 2 * chalf + s // data_width

Le coordinate della pagina sono `(u + border, v + border)`.

```example
a4_narrow_width = 1152
a4_narrow_pixels = 6912
a4_wide_pixels = 27756
a4_rep_pixels = 34668
a4_total_bits = 3196368
a4_xy_of_0 = 6, 0
a4_xy_of_17 = 23, 0
a4_xy_of_18 = 30, 0
a4_xy_of_1152 = 6, 1
a4_xy_of_6912 = 0, 6
a4_xy_of_8454 = 0, 7
a4_xy_of_34668 = 6, 24
a4_xy_of_3196367 = 1535, 2213
```

`a4_xy_of_N` è `u, v` della posizione nel canale `N`.

Vettori: `tests/vectors/c/bit_placement.json`.

### 2.5 Il codice di pagina { #25-the-page-code }

I dati di una pagina sono tagliati in **parole** di `small` bit. Ogni parola è
codificata in un **simbolo** di `large` bit, che si può correggere quando pochi
dei suoi bit sono letti in modo errato. `fec_order` sceglie il codice:

| `fec_order` | Codice | `large` | `small` |
|---|---|---|---|
| 1 | Golay (24, 12) | 24 | 12 |
| da 2 a 5 | Hamming esteso | `2 ^ fec_order` | `large - 1 - fec_order` |

```example
code_bits_of_order_1 = 24, 12
code_bits_of_order_2 = 4, 1
code_bits_of_order_3 = 8, 4
code_bits_of_order_4 = 16, 11
code_bits_of_order_5 = 32, 26
```

Qui un simbolo si scrive come un intero di `large` bit; il suo **bit `b`**,
nell'ordine in cui i bit sono posti sulla pagina, si conta a partire dal bit più
significativo: il bit 0 è il bit di valore `2 ^ (large - 1)`.

#### Golay (24, 12) { #golay-24-12 }

Il simbolo della parola di 12 bit `d` è `d * 4096 + p(d)`: la parola nei 12 bit
alti, 12 bit di parità sotto di essa. I bit di parità derivano da un dodecaedro
le cui facce sono numerate da 1 a 12. La faccia `f` rappresenta il bit di valore
`2 ^ (f - 1)` di `d`. Ogni faccia ha cinque facce vicine:

<!-- spec-table: golay -->
| Faccia | Vicine | Maschera |
|---|---|---|
| 1 | 2, 3, 4, 5, 6 | `0xfc1` |
| 2 | 1, 3, 6, 7, 8 | `0xf1a` |
| 3 | 1, 2, 4, 8, 9 | `0xe74` |
| 4 | 1, 3, 5, 9, 10 | `0xcea` |
| 5 | 1, 4, 6, 10, 11 | `0x9d6` |
| 6 | 1, 2, 5, 7, 11 | `0xbac` |
| 7 | 2, 6, 8, 11, 12 | `0x35d` |
| 8 | 2, 3, 7, 9, 12 | `0x6b9` |
| 9 | 3, 4, 8, 10, 12 | `0x573` |
| 10 | 4, 5, 9, 11, 12 | `0x2e7` |
| 11 | 5, 6, 7, 10, 12 | `0x58f` |
| 12 | 7, 8, 9, 10, 11 | `0x83f` |

La maschera della faccia `r` ha un 1 per ogni faccia che non è vicina di `r`
(compresa la faccia `r` stessa). Il bit di parità della faccia `r` è 1 quando
`d AND mask` ha un numero dispari di bit a 1. È il bit di valore `2 ^ (12 - r)`
di `p(d)`: la faccia 1 dà il bit di parità più significativo, la faccia 12 il
meno significativo.

```example
golay_0x001 = 0x00183f
golay_0x800 = 0x800fc1
golay_0xabc = 0xabca13
golay_0xfff = 0xffffff
```

Il codice è lineare, la parola 0 ha il simbolo 0 e due simboli qualsiasi
differiscono in almeno 8 bit. Un simbolo letto con al massimo 3 bit errati ha
quindi esattamente un simbolo entro 3 bit da sé, quello che è stato stampato.
Il file dei vettori fissa tutti i 4096 simboli.

#### Hamming esteso (`fec_order` da 2 a 5) { #extended-hamming-fec_order-2-to-5 }

Si numerano i bit del simbolo secondo il loro valore: la posizione `q` è il bit
di valore `2 ^ q`, `0 <= q < large`.

1. I bit della parola, dal più significativo, vanno nelle posizioni che non
   sono né 0 né una potenza di due, dalla posizione `large - 1` verso il basso.
2. Per `i` da 0 a `fec_order - 1`, la posizione `2 ^ i` è impostata in modo che
   le posizioni il cui numero ha il bit `i` impostato contengano un numero pari di
   bit a 1.
3. La posizione 0 è impostata in modo che l'intero simbolo contenga un numero
   pari di bit a 1.

Un simbolo di questo tipo si può correggere quando un bit è errato, e due bit
errati vengono rilevati. Con `fec_order` 2 il simbolo è l'unico bit della parola
ripetuto quattro volte.

```example
hamming_2_of_1 = 1111
hamming_3_of_1011 = 10101010
hamming_4_of_10000000001 = 1000000100011000
hamming_5_of_1 = 00000000000000000000000000001111
```

Ogni riga dà una parola in binario dopo `of_` e il suo simbolo in binario, dal
bit più significativo.

Vettori: `tests/vectors/c/golay.json`, `tests/vectors/c/encoder_pages.json`.

### 2.6 I simboli sulla pagina { #26-symbols-on-the-page }

Una pagina contiene

    symbols   = total_bits // large
    used_bits = symbols * large
    net_bits  = symbols * small

`net_bits` è il numero di bit di dati che una pagina porta. I simboli sono
interlacciati in modo che pixel vicini appartengano a simboli diversi:

    bit b of symbol s is at channel position  s + b * symbols

per `0 <= s < symbols` e `0 <= b < large`. Con il codice di Golay i pixel di dati
formano quindi 24 gruppi consecutivi di `symbols` pixel, e ogni simbolo ha un
pixel in ciascun gruppo, nella stessa posizione in ciascuno.

I pixel di dati nelle posizioni nel canale `used_bits` e successive non
appartengono a nessun simbolo e sono bianchi.

```example
a4_symbols = 133182
a4_used_bits = 3196368
a4_net_bits = 1598184
a4_position_of_symbol_1000_bit_5 = 666910
a4_xy_of_666910 = 1306, 462
a4_medium_total_bits = 1838484
a4_medium_symbols = 76603
a4_medium_unused_bits = 12
a4_medium_net_bits = 919236
hamming_2_net_bits = 799092
hamming_3_net_bits = 1598184
hamming_4_net_bits = 2197503
hamming_5_net_bits = 2597036
```

I nomi con `a4_medium_` si riferiscono al formato `0-50-70-24-3-1-2-24`; i
`hamming_N_net_bits` alla griglia A4 con `fec_order` N.

Vettori: `tests/vectors/c/bit_placement.json`, `tests/vectors/c/encoder_pages.json`.

### 2.7 Da un flusso alle pagine { #27-from-a-stream-to-pages }

Sia il flusso lungo `nbytes` byte, letto come stringa di bit (sezione 1.1).

    pages = ceil(8 * nbytes / net_bits)

La pagina `p` (da 1) porta i bit da `(p - 1) * net_bits` a `p * net_bits - 1`
del flusso. La parola `s` della pagina è composta dai `small` bit che iniziano
al bit `s * small` dei bit della pagina, e il simbolo `s` è il suo codice
(sezione 2.5).

- I bit oltre la fine del flusso sono 0. L'ultima parola che contiene bit del
  flusso è quindi completata con bit 0 nella sua parte bassa, e ogni parola
  successiva dell'ultima pagina è 0. Il simbolo della parola 0 è 0, per cui
  quelle parole si stampano come pixel bianchi.
- Un documento ha al massimo `MAX_PAGES` pagine; un flusso più lungo non si può
  codificare.
- Un flusso vuoto (`nbytes = 0`) dà `pages = 0`. Si stampa come una pagina i cui
  pixel di dati sono tutti bianchi e la cui etichetta indica il numero di
  pagina 1 e il numero di pagine 0 (`1/0`).

Leggendo le pagine in ordine e unendo i loro `net_bits` bit si ottiene il flusso
seguito da bit 0. Una pagina non registra dove finisce il flusso: un documento
semplice restituisce il proprio file completato con byte zero fino alla fine
della sua ultima pagina (esclusi i bit che non riempiono un byte, quando
`net_bits` non è multiplo di 8). Il contrassegno (parte 3) e il contenitore
(parte 4) registrano entrambi la dimensione del file.

```example
a4_pages_for_0_bytes = 0
a4_pages_for_1_byte = 1
a4_pages_for_199773_bytes = 1
a4_pages_for_199774_bytes = 2
a4_words_for_1000_bytes = 667
```

Un flusso di 1000 byte riempie 667 parole della prima pagina; l'ultima di esse
contiene 8 bit del flusso e quattro bit 0.

Vettori: `tests/vectors/c/encoder_pages.json`.

### 2.8 L'etichetta { #28-the-label }

La banda dell'etichetta contiene una riga di testo, per le persone e, in un
documento con contrassegno, per il programma di lettura. È sempre disegnata con lo
stesso font, quello definito dalla striscia del font descritta qui sotto.

**La striscia del font** è un'immagine di `LABEL_HEIGHT` righe e 1500 colonne,
con ogni pixel nero o bianco. Le colonne da `0` a `TEXT_WIDTH * GLYPH_CELLS - 1`
contengono `GLYPH_CELLS` celle dei caratteri di `TEXT_WIDTH` colonne: la cella
del carattere con codice `c`, `32 <= c <= 126`, inizia alla colonna
`TEXT_WIDTH * (c - FIRST_CHAR)`. Le colonne restanti contengono un logo. Glifi
e logo sono bianchi su nero. La striscia è il file `src/optar/data/font.png`
di questo progetto (un suo pixel è bianco quando il suo valore di grigio è 128 o
più); il digest riportato qui sotto è lo SHA-256 dei suoi pixel come byte 0
(nero) e 255 (bianco), riga per riga.

```example
strip_width = 1500
logo_width = 265
glyph_column_of_capital_a = 429
font_strip_sha256 = 481c0abd7884afb5ab6d958fbb95c0d6be97b0e2a7124f57e1abcd118d7d4bc4
```

**La riga dell'etichetta** della pagina `page` di `total` con il testo libero
`text` è

    two spaces, the format string, a space, page, "/", total, a space, text

con `page` e `total` in decimale senza zeri iniziali. Lo spazio dopo `total` c'è
anche quando `text` è vuoto. La riga viene poi tagliata ai suoi primi
`data_width // TEXT_WIDTH - 1` caratteri (code point Unicode).

**Disegno.** La banda è larga `data_width` colonne, numerate da 0 a partire
dalla colonna `border` della pagina; tutto ciò che in essa non viene disegnato
è nero.

1. Se `logo_width <= data_width`, il logo viene copiato nelle colonne della
   banda da `0` a `logo_width - 1`.
2. Un cursore parte dalla colonna della banda `logo_width`, che il logo sia
   stato disegnato o no.
3. Per ogni carattere della riga tagliata, in ordine: un carattere il cui
   codice è inferiore a 32 o superiore a 127 viene saltato. Altrimenti, se il
   cursore più `TEXT_WIDTH` è al massimo `data_width`, le `TEXT_WIDTH` colonne
   della striscia che iniziano a `TEXT_WIDTH * (code - FIRST_CHAR)` vengono
   copiate nella banda alla posizione del cursore; in entrambi i casi il
   cursore avanza di `TEXT_WIDTH`.

Tre conseguenze che un codificatore deve riprodurre per stampare le stesse
pagine:

- Una pagina mostra al massimo `(data_width - logo_width) // TEXT_WIDTH`
  caratteri, meno di quelli a cui la riga viene tagliata; il resto non viene
  disegnato.
- I caratteri al di fuori dei codici da 32 a 127 non occupano una cella, ma
  contano per la lunghezza a cui la riga viene tagliata.
- Il codice 127 occupa una cella e disegna le prime `TEXT_WIDTH` colonne del
  logo. Un'etichetta di questo tipo non si può rileggere.

```example
a4_label_line = "  0-65-93-24-3-1-2-24 3/7 backup.tar"
a4_label_characters = 117
a4_label_cells = 98
a4_xlarge_label_cells = 18
```

`a4_label_characters` è la lunghezza a cui la riga viene tagliata e
`a4_label_cells` il numero di caratteri che una pagina mostra. Una pagina del
formato `0-22-31-24-3-1-2-24` mostra 18 caratteri, meno di quanti ne abbia la
sua stringa di formato; la sezione 5.4 spiega come si etichettano in stampa
queste pagine.

Vettori: `tests/vectors/c/label.json`, `tests/vectors/c/encoder_pages.json`.

## 3. Il contrassegno del documento (stampe 0.2.0) { #3-the-document-tag-020-printouts }

Un documento semplice non dice quanto è lungo il suo file, quali pagine vanno
insieme né se il file è stato letto correttamente. Un **documento con
contrassegno** lo dice nel testo libero di ogni etichetta. Il suo flusso è il
file stesso, per cui le sue pagine vengono lette anche da programmi che non
sanno nulla del contrassegno.

### 3.1 Il contrassegno { #31-the-tag }

Per un file di `size` byte:

- `SIZE` è `size` in decimale senza zeri iniziali (`0` per un file vuoto), al
  massimo `MAX_SIZE_DIGITS` cifre;
- `FINGERPRINT` è composto dai primi `FINGERPRINT_DIGITS` caratteri dello
  SHA-256 del file, scritto in esadecimale minuscolo;
- `CHECK`, per la pagina `page` di `total`, è composto dai primi `CHECK_DIGITS`
  caratteri dello SHA-256 esadecimale minuscolo del testo ASCII
  `SIZE:FINGERPRINT:page/total`, con `page` e `total` scritti come li scrive la
  riga dell'etichetta.

Il contrassegno di una pagina è il testo `[SIZE:FINGERPRINT:CHECK]`. Il testo
libero dell'etichetta della pagina è il contrassegno, oppure il contrassegno, uno
spazio e un nome. `SIZE` e `FINGERPRINT` sono uguali su ogni pagina di un
documento; `CHECK` cambia da una pagina all'altra.

Un file vuoto è una pagina con l'etichetta `1/0` (sezione 2.7); il suo
controllo si calcola con `page` 1 e `total` 0.

```example
tag_fingerprint_of_x = 2d711642
tag_check_input = "1:2d711642:1/1"
tag_check_of_x_page_1_of_1 = ca
tag_free_text = "[1:2d711642:ca] name.tar"
tag_of_empty_file = "[0:e3b0c442:e0]"
```

Le prime quattro righe si riferiscono al file di un byte `x` stampato con il
nome `name.tar`.

Vettori: `tests/vectors/py/tag.json`.

### 3.2 Quando un contrassegno è valido { #32-when-a-tag-is-valid }

Il testo libero di un'etichetta **inizia con un contrassegno** quando comincia
con `[`, una dimensione come sopra, `:`, esattamente 8 caratteri tra `0-9a-f`,
`:`, esattamente 2 caratteri tra `0-9a-f` e `]`, e il contrassegno è seguito da
uno spazio o dalla fine del testo.

Un contrassegno letto dalla pagina `page` di `total` nel formato di pagina `F` è
**valido** quando valgono entrambe le condizioni:

- il suo controllo è uguale al controllo calcolato dalla dimensione,
  dall'impronta, da `page` e da `total` così come sono stati letti;
- la dimensione è coerente con il numero di pagine: `size = 0` e `total = 0`,
  oppure `size > 0`, `total > 0` e
  `(total - 1) * capacity < size <= total * capacity` con
  `capacity = net_bits // 8` di `F`.

Nei due layout `standard` (sezione 5.2) `net_bits` è multiplo di 8, per cui una
dimensione è coerente esattamente con il numero di pagine che le assegna la
sezione 2.7. Il programma di lettura di questo progetto identifica le pagine dal
loro contrassegno solo in quei due layout.

Vettori: `tests/vectors/py/tag.json`.

## 4. Documenti autoidentificanti (versione 1) { #4-self-identifying-documents-version-1 }

Un **documento autoidentificante** porta, nei dati di ogni pagina,
un'intestazione che dice a quale documento appartiene la pagina e quale pagina
è, e può portare una parità con cui si riparano le pagine danneggiate e si
ricostruiscono quelle mancanti. Il file, il suo nome e la parità sono
impacchettati in un flusso, il **contenitore**, e quel flusso viene stampato come
normali pagine di versione 0 (parte 2). La versione 1 è la versione del
contenitore; il formato di pagina mantiene la versione 0.

### 4.1 Dimensioni { #41-sizes }

Per un formato di pagina `F`, un livello di parità `parity` (sezione 4.4) e un
numero di pagine `T`:

    page_bytes = net_bits // 8                         payload of one page
    page_body  = page_bytes - HEADER_COPIES * HEADER_SIZE
    k          = CODEWORD - parity                     data bytes of a codeword
    m(T)       = T * page_body // CODEWORD             codewords
    D(T)       = m(T) * k                              bytes of the data region

Il **carico utile** di una pagina è composto dai suoi primi `page_bytes * 8` bit
di dati, presi come byte. Il **corpo** di una pagina è il suo carico utile senza
le copie dell'intestazione (sezione 4.3), `page_body` byte. Il **corpo del
documento** è composto dai corpi delle pagine da 1 a `T` concatenati,
`T * page_body` byte.

Un formato di pagina può portare un contenitore solo se
`page_bytes // HEADER_COPIES >= HEADER_SIZE`.

```example
a4_page_bytes = 199773
a4_page_body = 199583
```

Vettori: `tests/vectors/py/container.json`.

### 4.2 L'intestazione { #42-the-header }

Un'intestazione è composta da `HEADER_SIZE` byte:

<!-- spec-table: header-fields -->
| Offset | Dimensione | Campo | Tipo | Contenuto |
|---|---|---|---|---|
| 0 | 4 | `magic` | byte | `HEADER_MAGIC` |
| 4 | 1 | `version` | intero | `CONTAINER_VERSION` |
| 5 | 1 | `parity` | intero | byte di parità per parola di codice: 0, 32 o 64 |
| 6 | 2 | `page` | intero | numero di questa pagina, da 1 |
| 8 | 2 | `total` | intero | pagine nel documento |
| 10 | 8 | `size` | intero | dimensione del file in byte |
| 18 | 16 | `fingerprint` | byte | primi `FINGERPRINT_SIZE` byte dello SHA-256 del file |
| 34 | 4 | `crc` | intero | CRC-32 dei byte da 0 a 33 |

Gli interi sono big-endian. Tutti i campi tranne `page` (e con esso `crc`) sono
uguali su ogni pagina di un documento.

```example
header_bytes = 6f5074310140000300070000000000086e3c000102030405060708090a0b0c0d0e0f1ef0ca9d
header_crc = 0x1ef0ca9d
```

Questa è l'intestazione della pagina 3 di 7 di un file di 552508 byte con parità
64, la cui impronta è composta dai byte da `00` a `0f`.

Vettori: `tests/vectors/py/container.json`.

### 4.3 Il carico utile di una pagina { #43-the-payload-of-a-page }

La copia `c` dell'intestazione della pagina, `0 <= c < HEADER_COPIES`, occupa i
byte del carico utile

    c * (page_bytes // HEADER_COPIES)   to   c * (page_bytes // HEADER_COPIES) + HEADER_SIZE - 1

Gli altri byte del carico utile, in ordine, sono il corpo della pagina.

```example
a4_header_offsets = 0, 39954, 79908, 119862, 159816
```

Vettori: `tests/vectors/py/container.json`.

### 4.4 Livelli di parità { #44-parity-levels }

<!-- spec-table: parity -->
| Nome | Byte di parità | Byte di dati |
|---|---|---|
| none | 0 | 255 |
| standard | 32 | 223 |
| high | 64 | 191 |

«Byte di parità» è il campo `parity` dell'intestazione; «Byte di dati» è `k`.
Un documento con parità 0 ha intestazioni e un nome, ma non viene riparato
nulla.

Vettori: `tests/vectors/py/container.json`.

### 4.5 Il codice di Reed-Solomon { #45-the-reed-solomon-code }

Una **parola di codice** è composta da `CODEWORD` byte: `k` byte di dati seguiti
da `parity` byte di parità.

- I byte sono elementi di GF(256) con il polinomio del campo
  `x^8 + x^4 + x^3 + x^2 + 1` (`0x11D`): un byte è un polinomio su GF(2) il cui
  coefficiente di `x^7` è il suo bit più significativo, l'addizione è lo XOR e
  la moltiplicazione è la moltiplicazione di polinomi modulo il polinomio del
  campo.
- `alpha` è l'elemento `0x02`.
- Il polinomio generatore è
  `g(x) = (x - alpha^0)(x - alpha^1) ... (x - alpha^(parity - 1))`.
- Il byte `i` di una parola di codice, `0 <= i <= 254`, è il coefficiente di
  `x^(254 - i)` del polinomio della parola di codice `c(x)`.
- I byte di dati sono i coefficienti da `x^254` a `x^parity`. I byte di parità
  sono scelti in modo che `g(x)` divida `c(x)`: sono il resto della divisione
  del polinomio dei dati (con coefficienti nulli sotto `x^parity`) per `g(x)`,
  a partire dal coefficiente di `x^(parity - 1)`.

Una parola di codice si può riparare quando `2 * e + f <= parity`, dove `f` è il
numero dei suoi byte che si sa essere illeggibili (cancellazioni) ed `e` il
numero degli altri byte errati.

```example
gf_alpha_8 = 0x1d
gf_alpha_254 = 0x8e
rs_32_parity_of_one = 744034ae367e10c2a221219db0c5e10c3b37fde4942fb3b9188afd148e37ac58
rs_32_parity_of_counting = 41841183b11fdb537421939696cda70e1db5c86684af222564b89cc6069f172e
```

`rs_32_parity_of_one` sono, per parità 32, i byte di parità dei 223 byte di dati
che sono tutti zero tranne l'ultimo, che vale 1; questi sono i coefficienti di
`g(x)` da `x^31` a `x^0`. `rs_32_parity_of_counting` sono, per parità 32, i byte
di parità dei byte di dati 0, 1, 2, ..., 222.

Vettori: `tests/vectors/py/reed_solomon.json`.

### 4.6 La regione dei dati e la distribuzione { #46-the-data-region-and-the-spread }

La **regione dei dati** è composta da `D(T)` byte:

| Byte | Contenuto |
|---|---|
| `size` | il file |
| 1 | `L`, la lunghezza del nome in byte, da 0 a `NAME_MAX_BYTES` |
| `L` | il nome del file in UTF-8 |
| il resto | riempimento (sezione 4.7) |

Un nome più lungo di `NAME_MAX_BYTES` byte in UTF-8 viene tagliato al maggior
numero di caratteri interi che vi entra. Il nome non è coperto
dall'impronta. Un carattere del nome che UTF-8 non può codificare (un code point
surrogato isolato, da U+D800 a U+DFFF) viene memorizzato come `?`.

La parola di codice `j`, `0 <= j < m`, ha come byte di dati i byte da `j * k` a
`j * k + k - 1` della regione dei dati. Con parità 0 una parola di codice è
composta dai suoi 255 byte di dati.

**La distribuzione.** Il byte `i` della parola di codice `j` è il byte del corpo
del documento alla posizione

    i * m + (j + i * SPREAD_STEP) mod m

Così il byte `i` di ogni parola di codice si trova nella porzione da `i * m` a
`(i + 1) * m - 1` del corpo, e i 255 byte di una parola di codice si trovano in
255 porzioni diverse, distribuite su tutto il documento: un danno in una zona
costa a ogni parola di codice pochi byte, invece di costare tutto a poche parole
di codice.

Gli ultimi `T * page_body - CODEWORD * m` byte del corpo (meno di `CODEWORD`)
non appartengono a nessuna parola di codice e sono riempimento.

Vettori: `tests/vectors/py/container.json`.

### 4.7 Riempimento { #47-padding }

Il riempimento non porta nulla. Esistono due contenuti, ed entrambi sono validi:

- optar 0.3.0 scriveva byte zero;
- optar 0.3.1 e successivi scrivono il **flusso di riempimento**: il suo blocco
  `n`, `n = 0, 1, 2, ...`, è composto dai `PADDING_BLOCK` byte dello SHA-256 di
  un'unica stringa di byte: `PADDING_KEY` con in coda `n` come intero di 8 byte,
  big-endian; il flusso è composto dai
  blocchi concatenati. Il riempimento della regione dei dati è il flusso a
  partire dal suo byte 0; il riempimento alla fine del corpo prosegue il flusso
  dove si era fermato il riempimento della regione dei dati. (I byte zero si
  stampano come righe bianche che attraversano ogni pagina; il flusso si stampa
  come i dati.)

Un documento il cui riempimento è qualsiasi altra cosa è comunque un documento
valido per un programma di lettura (sezione 6.4), ma solo il flusso di
riempimento dà le pagine che questo progetto stampa.

```example
padding_block_0 = d518824e181c15b2f69e390066efbfa00d73eb8f0c3d932313396940eedd1286
padding_bytes_30_to_33 = 12863e00
```

Vettori: `tests/vectors/py/container.json`.

### 4.8 Il numero di pagine e i limiti { #48-the-page-count-and-the-limits }

Un documento ha il minor numero di pagine che contengono il file, il byte di
lunghezza e il nome:

    need = size + 1 + L
    T    = the smallest T >= 1 with D(T) >= need

I limiti sono:

- `T <= MAX_PAGES`;
- con `parity > 0`: `T * page_bytes <= PROTECTED_MAX_BYTES`;
- `size < 2^64`, `L <= NAME_MAX_BYTES`.

Un file che richiede di più non si può mettere in un documento.

```example
plan_need = 1000011
plan_codewords_needed = 4485
plan_pages = 6
plan_codewords = 4696
plan_data_bytes = 1047208
plan_body_bytes = 1197498
plan_spare_bytes = 18
plan_padding_in_region = 47197
plan_position_of_codeword_0_byte_0 = 0
plan_position_of_codeword_5_byte_0 = 5
plan_position_of_codeword_5_byte_1 = 7924
plan_position_of_codeword_5_byte_254 = 1194327
plan_page_of_codeword_5_byte_254 = 6
```

L'esempio è un file di 1000000 byte di nome `vector.bin` su pagine A4 standard
con parità 32. Richiede 4485 parole di codice; cinque pagine ne contengono meno,
sei ne contengono `m = 4696`. Il documento ha tutte le 4696 parole di codice;
quelle di cui il file non ha bisogno contengono riempimento. `plan_spare_bytes`
è il riempimento alla fine del corpo e `plan_padding_in_region` il riempimento
della regione dei dati. Le posizioni sono posizioni nel corpo del documento
(sezione 4.6).

Vettori: `tests/vectors/py/container.json`.

### 4.9 Che cosa sopporta il documento (informativo) { #49-what-the-document-withstands-informative }

Una pagina persa costa a una parola di codice al massimo
`ceil(page_body / m) + 1` byte. Questo progetto dice al proprio utente che si
possono perdere `n` pagine qualsiasi quando
`n * (ceil(page_body / m) + 1) <= PROMISE_NUM * parity // PROMISE_DEN`, il che
lascia un quarto della parità per i danni sulle pagine rimaste. Questa è una
promessa degli strumenti: non è una proprietà su cui un programma di lettura può
fare affidamento, né una proprietà che un programma di lettura deve controllare.

### 4.10 Dal contenitore alle pagine { #410-from-the-container-to-pages }

Il flusso è composto da `T * net_bits // 8` byte. Letto come stringa di bit, il
carico utile della pagina `p` (da 1) inizia al bit `(p - 1) * net_bits`; ogni bit
del flusso che non si trova in alcun carico utile è 0. Quando `net_bits` è multiplo di 8 il flusso è
semplicemente composto dai carichi utili concatenati. Quando non lo è, ogni
pagina ha `net_bits mod 8` bit inutilizzati dopo il proprio carico utile, e i
carichi utili di alcune pagine non iniziano al confine di un byte del flusso.

Il flusso viene stampato come dice la sezione 2.7, il che dà esattamente `T`
pagine. L'etichetta di una pagina è una normale riga dell'etichetta il cui testo
libero è per le persone: è l'etichetta data dall'utente o, in sua assenza, un nome scelto
dallo strumento (la finestra usa il nome del file, la riga di comando il nome
dato con `-o`, che può essere vuoto), uguale su ogni pagina, e non porta alcun contrassegno. (Un
contrassegno valido farebbe prendere la pagina a un programma di lettura per una
pagina di un documento con contrassegno, sezione 6.1.)

Con il codice di Golay `net_bits mod 8` vale 0 o 4 e l'ultimo carico utile
termina sempre all'interno del flusso. Questo progetto stampa documenti
autoidentificanti solo nei dieci formati di pagina della sezione 5.2, e il suo
programma di lettura cerca intestazioni solo in quei formati.

```example
a4_medium_stream_bytes_for_3_pages = 344713
a4_medium_page_2_starts_at = 114904, 4
a4_medium_page_3_starts_at = 229809, 0
```

Una pagina del formato `0-50-70-24-3-1-2-24` ha `net_bits = 919236`, il che
lascia 4 bit dopo i suoi 114904 byte di carico utile. I due valori sono il byte
del flusso in cui inizia il carico utile della pagina e il bit all'interno di
quel byte (0 è il più significativo).

Vettori: `tests/vectors/py/container.json`, `tests/vectors/c/container_pages.json`.

## 5. Stampa { #5-printing }

### 5.1 Dimensioni dei punti { #51-dot-sizes }

Una pagina si stampa con una di cinque dimensioni dei punti. Un punto di dati è
un quadrato di un numero intero di punti della stampante, in modo che ogni pixel
della pagina si stampi come lo stesso gruppo di punti del dispositivo.

<!-- spec-table: dot-sizes -->
| Nome | Punti della stampante per punto di dati | Punti di dati per pollice | Dimensione del punto (pt) | Scansione consigliata (dpi) |
|---|---|---|---|---|
| standard | 3 | 200 | 0.36 | 600 |
| medium | 4 | 150 | 0.48 | 450 |
| big | 5 | 120 | 0.6 | 360 |
| large | 6 | 100 | 0.72 | 300 |
| xlarge | 9 | 200/3 | 1.08 | 200 |

La risoluzione di scansione consigliata dà `SCAN_PIXELS_PER_DOT` pixel della
scansione per punto di dati. È un consiglio; una pagina è la stessa pagina a
qualsiasi risoluzione di scansione.

### 5.2 Layout { #52-layouts }

Un **layout** è composto da una carta, una dimensione dei punti e il formato di
pagina stampato su di essa. Ce ne sono dieci. Le carte si chiamano `a4` e
`letter`.

<!-- spec-table: layouts -->
| Carta | Punti | Croci in orizzontale | Croci in verticale | Stringa di formato | Larghezza (px) | Altezza (px) | Bit netti | Byte di pagina | Byte del corpo |
|---|---|---|---|---|---|---|---|---|---|
| a4 | standard | 65 | 93 | `0-65-93-24-3-1-2-24` | 1546 | 2242 | 1598184 | 199773 | 199583 |
| a4 | medium | 50 | 70 | `0-50-70-24-3-1-2-24` | 1186 | 1690 | 919236 | 114904 | 114714 |
| a4 | big | 40 | 56 | `0-40-56-24-3-1-2-24` | 946 | 1354 | 584220 | 73027 | 72837 |
| a4 | large | 33 | 46 | `0-33-46-24-3-1-2-24` | 778 | 1114 | 392952 | 49119 | 48929 |
| a4 | xlarge | 22 | 31 | `0-22-31-24-3-1-2-24` | 514 | 754 | 172848 | 21606 | 21416 |
| letter | standard | 67 | 87 | `0-67-87-24-3-1-2-24` | 1594 | 2098 | 1540728 | 192591 | 192401 |
| letter | medium | 51 | 66 | `0-51-66-24-3-1-2-24` | 1210 | 1594 | 883704 | 110463 | 110273 |
| letter | big | 41 | 52 | `0-41-52-24-3-1-2-24` | 970 | 1258 | 555708 | 69463 | 69273 |
| letter | large | 34 | 44 | `0-34-44-24-3-1-2-24` | 802 | 1066 | 387228 | 48403 | 48213 |
| letter | xlarge | 23 | 29 | `0-23-29-24-3-1-2-24` | 538 | 706 | 169020 | 21127 | 20937 |

«Byte di pagina» e «Byte del corpo» sono `page_bytes` e `page_body` della
sezione 4.1. Questo progetto stampa un documento semplice o con contrassegno in
un layout `standard` (oppure, quando gli si dà a mano una stringa di formato, in
quel formato di pagina con la dimensione dei punti standard e gli offset del
layout `standard` della carta; rifiuta una stringa di formato di questo tipo a
meno che ogni margine non risulti allora di almeno `MIN_MARGIN_PT`), e un documento autoidentificante in uno qualsiasi dei dieci
layout.

Vettori: `tests/vectors/c/bit_placement.json`, `tests/vectors/py/container.json`.

L'immagine della pagina viene posta sulla carta con l'angolo in basso a sinistra
agli offset qui sotto, misurati dall'angolo in basso a sinistra della carta. I
margini sono ciò che resta su ciascun lato.

<!-- spec-table: layouts -->
| Carta | Punti | Larghezza della carta (pt) | Altezza della carta (pt) | Offset x (pt) | Offset y (pt) | Sinistro (mm) | Inferiore (mm) | Destro (mm) | Superiore (mm) |
|---|---|---|---|---|---|---|---|---|---|
| a4 | standard | 595.28 | 841.89 | 19.20 | 17.40 | 6.77 | 6.14 | 6.89 | 6.13 |
| a4 | medium | 595.28 | 841.89 | 12.96 | 15.24 | 4.57 | 5.38 | 4.60 | 5.45 |
| a4 | big | 595.28 | 841.89 | 13.80 | 14.64 | 4.87 | 5.16 | 4.90 | 5.24 |
| a4 | large | 595.28 | 841.89 | 17.52 | 19.80 | 6.18 | 6.99 | 6.21 | 7.06 |
| a4 | xlarge | 595.28 | 841.89 | 20.04 | 13.68 | 7.07 | 4.83 | 7.10 | 4.90 |
| letter | standard | 612 | 792 | 19.08 | 18.36 | 6.73 | 6.48 | 6.73 | 6.48 |
| letter | medium | 612 | 792 | 15.60 | 13.44 | 5.50 | 4.74 | 5.50 | 4.74 |
| letter | big | 612 | 792 | 15.00 | 18.60 | 5.29 | 6.56 | 5.29 | 6.56 |
| letter | large | 612 | 792 | 17.28 | 12.24 | 6.10 | 4.32 | 6.10 | 4.32 |
| letter | xlarge | 612 | 792 | 15.48 | 14.76 | 5.46 | 5.21 | 5.46 | 5.21 |

Ogni offset è un numero intero di punti della stampante, per cui i lati
dell'immagine cadono su punti del dispositivo. Le griglie e gli offset dei due
layout `standard` sono ereditati (parte 8). Gli altri otto sono derivati: la
griglia è quella con i valori di `xcrosses` e `ycrosses` più grandi per cui la
pagina, alla sua dimensione dei punti, lascia almeno `MIN_MARGIN_PT` su ogni
lato, e ogni offset è la metà della lunghezza libera, arrotondata per difetto a
un numero intero di punti della stampante. Sono le tabelle, non questa regola, a
definire i layout.

Una pagina è la stessa pagina ovunque si trovi sulla carta: un programma di
lettura trova la pagina dal suo bordo. La posizione conta solo per la stampa:
una pagina stampata in un'altra scala ha punti di un'altra dimensione, e una
pagina stampata più vicino all'orlo della carta può venire tagliata.

### 5.3 Il PDF che scrive questo progetto { #53-the-pdf-this-project-writes }

Ogni pagina del documento è una pagina PDF la cui media box è la carta:
`[0 0 width height]`, con la larghezza e l'altezza della carta in pt. L'immagine della pagina è un'unica immagine a 1 bit
per pixel (1 è bianco), di `width` per `height` pixel della pagina, senza
interpolazione, disegnata con l'angolo in basso a sinistra agli offset del
layout e scalata in modo che un pixel della pagina sia un punto di dati:

    image width in points  = width  * dot size in points
    image height in points = height * dot size in points

```example
a4_large_image_width_pt = 560.16
a4_large_image_height_pt = 802.08
```

Il PDF è pensato per essere stampato a dimensione reale (100%). Nessun vettore fissa il PDF; lo fa
`tests/unit/test_pdf.py`.

Le immagini delle pagine si scrivono anche come file PNG o PGM con un pixel
dell'immagine per pixel della pagina; i vettori identificano una pagina dallo
SHA-256 del suo file PGM binario (`P5`), i cui byte esatti sono indicati in
`tests/vectors/README.md`: l'intestazione `P5\n<width> <height>\n255\n` in
ASCII, poi i byte dei pixel riga per riga.

### 5.4 La striscia dell'etichetta { #54-the-label-strip }

Un'etichetta si disegna in pixel della pagina (sezione 2.8), per cui su una
pagina con punti più grandi contiene meno caratteri: con i punti più
grandi, troppo pochi per la sua stessa stringa di formato. In un PDF, una pagina
di un layout la cui dimensione dei punti non è `standard` ha quindi la propria
etichetta sostituita da una **striscia dell'etichetta**, una seconda immagine
disegnata in punti di dati standard:

- la striscia è di `LABEL_HEIGHT` righe e
  `floor(data_width * printer dots per data dot / STANDARD_PRINTER_DOTS)`
  colonne di pixel della striscia;
- contiene la riga dell'etichetta della pagina, tagliata e disegnata come nella
  sezione 2.8 con la larghezza della striscia al posto di `data_width`;
- nell'immagine della pagina, la banda dell'etichetta viene resa nera nelle
  colonne da `border` a `border + data_width - 1`;
- la striscia viene disegnata sopra la banda a 0.36 pt per pixel della
  striscia, con il lato sinistro sul lato sinistro delle colonne di dati della
  banda e centrata nell'altezza della banda.

Solo la banda dell'etichetta differisce dalla pagina della parte 2; l'area dei
dati e il bordo restano intatti. Una pagina PNG o PGM di un layout di questo
tipo mantiene l'etichetta della sezione 2.8. L'etichetta di una pagina
autoidentificante non viene usata per identificarla (sezione 6.2), per cui un
programma di lettura non è tenuto a leggere la striscia.

```example
a4_large_strip_width = 1548
a4_large_strip_characters = 118
a4_large_strip_width_pt = 557.28
```

Vettori: `tests/vectors/c/container_pages.json` fissa come pagine normali le
pagine di due layout con punti più grandi; la striscia è fissata da
`tests/unit/test_font.py` e `tests/unit/test_pdf.py`.

## 6. Che cosa deve fare un programma di lettura { #6-what-a-reader-must-do }

Un programma di lettura ha pagine scansionate e, con un metodo qualsiasi, ha
letto da ciascuna i suoi bit di dati e, dove ha potuto, la sua etichetta. Questa
parte dice che cosa deve concluderne. Le scansioni non sono affidabili: una
pagina può essere stampata da chiunque e può dichiarare qualsiasi cosa.

### 6.1 Un contrassegno valido prevale su un'intestazione { #61-a-valid-tag-wins-over-a-header }

Per una pagina in un layout `standard`, il programma di lettura deve guardare
prima l'etichetta. Se l'etichetta ha la forma della sezione 2.8, porta la
stringa di formato del layout, un numero di pagine non superiore a `MAX_PAGES`,
un numero di pagina da 1 al numero di pagine (oppure 1 con il numero di pagine
0), e il suo testo libero inizia con un contrassegno valido per quel numero di
pagina e quel numero di pagine (sezione 3.2), la pagina è una pagina di un
documento con contrassegno. Deve essere trattata come tale anche se i suoi dati
contengono un'intestazione accettabile (sezione 6.2).

Il motivo: il flusso di un documento autoidentificante, così come lo restituisce
un vecchio programma, può essere stampato di nuovo come documento con
contrassegno. Quelle pagine contengono nei loro dati vecchie intestazioni, e
sono pagine del documento con contrassegno, il cui file è quel flusso.

### 6.2 Un'intestazione non è affidabile { #62-a-header-is-untrusted }

Una copia dell'intestazione è **ben formata** quando il suo CRC è giusto, il suo
numero magico è `HEADER_MAGIC`, la sua versione è `CONTAINER_VERSION`, la sua
parità è 0, 32 o 64 e `1 <= page <= total`.

L'**intestazione di una pagina** esiste quando almeno una delle sue
`HEADER_COPIES` copie è ben formata e tutte le copie ben formate sono uguali.
Una pagina le cui copie ben formate differiscono non ha intestazione.

Un'intestazione letta da una pagina del formato `F` è **accettabile** quando
descrive un documento che la sezione 4.8 consente, cioè quando valgono tutte
queste condizioni (`m`, `D` e `page_bytes` come nella sezione 4.1, per `F` e la
parità dell'intestazione):

1. `total <= MAX_PAGES`;
2. `page_bytes // HEADER_COPIES >= HEADER_SIZE`;
3. se `parity > 0`: `total * page_bytes <= PROTECTED_MAX_BYTES`;
4. `size + 1 <= D(total)`: le pagine contengono il file e il byte di lunghezza;
5. se `total > 1`: `size + 1 + NAME_MAX_BYTES > D(total - 1)`: nessun nome
   avrebbe permesso al file di stare in meno pagine.

Un programma di lettura non deve usare un'intestazione che non è accettabile.
Le regole 4 e 5 legano il numero di pagine alla dimensione, in modo che
un'intestazione non possa dichiarare molte pagine per un file piccolo o poche
per un file grande.

Un programma di lettura deve mantenere la propria memoria e il proprio tempo
proporzionati alle pagine che ha ricevuto, non a ciò che un'intestazione
dichiara: una pagina che dichiara un documento di 9999 pagine non deve indurre
il programma di lettura ad allocare o elaborare 9999 pagine.

Le pagine appartengono a un unico documento quando le loro intestazioni
concordano in `fingerprint`, `size`, `total` e `parity` e le pagine hanno lo
stesso formato di pagina. Le pagine di un altro documento non devono essere
usate.

### 6.3 Solo l'impronta verifica un file { #63-only-the-fingerprint-verifies-a-file }

- **Documento autoidentificante.** Un byte del carico utile è una cancellazione
  quando uno dei suoi bit si trova in un simbolo che il codice di pagina non ha
  potuto correggere; ogni byte di una pagina che non è stata fornita è una
  cancellazione. Il file è composto dai primi `size` byte della regione dei
  dati, ed è recuperato quando, e solo quando, ogni parola di codice che
  contiene uno di quei byte è stata letta o riparata (con parità 0, dove non si
  ripara nulla: quando ogni parola di codice di questo tipo non ha
  cancellazioni). Il file è
  **verificato** quando è recuperato e i primi `FINGERPRINT_SIZE` byte del suo
  SHA-256 sono uguali all'impronta dell'intestazione.
- **Documento con contrassegno.** Il file è composto dai primi `SIZE` byte del
  flusso. È **verificato** quando ha `SIZE` byte e i primi `FINGERPRINT_DIGITS`
  caratteri esadecimali del suo SHA-256 sono uguali all'impronta del
  contrassegno.
- **Documento semplice.** Nulla lo verifica, e la sua lunghezza non è nota
  (sezione 2.7).

Un programma di lettura non deve dichiarare verificato un file per nessun altro
motivo. In particolare una riparazione che non segnala alcun fallimento non
verifica il file: una parola di codice con più byte errati di quanti la sua
parità ne possa riparare può essere trasformata in un'altra parola di codice
valida, e con parità 0 non si controlla proprio nulla.

Il nome del file (sezione 4.6) è al di fuori dell'impronta. È testo non
affidabile anche quando il file è verificato, come ogni etichetta.

### 6.4 Il riempimento non si legge mai { #64-padding-is-never-read }

Un programma di lettura non deve leggere né controllare il riempimento della
sezione 4.7, né dipendere da esso. I byte zero (0.3.0) e il flusso di
riempimento (0.3.1) sono entrambi validi, e un documento con l'uno o con l'altro
è, per un programma di lettura, lo stesso documento.

I byte della regione dei dati dopo il nome sono riempimento. Un record del nome
il cui byte di lunghezza punta oltre la fine della regione dei dati, o i cui
byte non sono UTF-8, o che si trova in una parola di codice che non è stata
riparata, non dà alcun nome; non rende il file non valido.

Vettori: `tests/vectors/py/container.json`, `tests/vectors/py/tag.json`.

## 7. Decodificatore di riferimento (informativo) { #7-reference-decoder-informative }

Questa parte descrive come questo progetto legge una scansione. Nulla di essa è
obbligatorio: un programma di lettura può trovare e campionare una pagina in
qualsiasi modo. Le fasi e le loro costanti sono quelle del programma in C
`unoptar` (parte 8); i risultati di questo decodificatore su scansioni
prestabilite sono fissati dai vettori indicati alla fine, in modo che non cambi
per caso.

### 7.1 La scansione { #71-the-scan }

Una scansione si legge come immagine in scala di grigi a 8 bit in luce lineare.
Un campione `v` del file diventa `floor(255 * (v / 255) ^ (1 / gamma) + 0.5)`,
dove `gamma` è il valore gamma del file (PNG `gAMA`) o 0.454545 quando il file
non ne indica alcuno. Un'immagine a colori si converte canale per canale e poi
si pesa con 0.212671 per il rosso, 0.715160 per il verde e 0.072169 per il blu,
arrotondando all'intero più vicino. Un campione a 16 bit conserva i suoi 8 bit
alti.

```example
linear_light_of_128 = 56
linear_light_of_200 = 149
```

### 7.2 Trovare la pagina { #72-finding-the-page }

Al decodificatore viene fornito il formato di pagina. Lavora sull'immagine
diritta.

1. **Livelli di grigio.** Il livello di soglia parte dal valore di grigio medio.
   Per al massimo 32 volte: `black` è la soglia meno la radice quadrata della
   media dei quadrati delle distanze dalla soglia dei pixel che stanno sotto di
   essa, `white` la soglia più la stessa grandezza calcolata per i pixel che
   stanno sopra; la nuova soglia è
   `sync_white_cut * white + (1 - sync_white_cut) * black`, arrotondata; il
   procedimento si ferma quando la soglia non cambia più. Un secondo livello, la
   soglia di propagazione (*fill cut*), sta a metà tra `black` e `white`.
2. **Isolamento della pagina.** Il bianco attorno alla pagina è ogni pixel pari
   o superiore alla soglia di propagazione che sia connesso (attraverso i lati
   dei pixel, non i vertici) a uno dei quattro angoli della scansione o al
   centro di uno dei suoi quattro lati. La pagina è tutto il resto che è connesso al centro della
   scansione. Tutti gli altri pixel (lo sporco tra la pagina e il lato della
   scansione) vengono resi bianchi.
3. **Un'interruzione nella cornice.** Se una stampante ha tagliato un lato della
   pagina, il bordo ha un'interruzione, il bianco attorno alla pagina penetra
   tra i punti e la fase 2 trova solo un pezzo della pagina. Quando l'area
   trovata è meno della metà di ciò che non è il bianco attorno alla pagina così
   come l'ha trovato la fase 2, il
   bianco attorno alla pagina viene invece preso come ciò che si può
   raggiungere attraverso passaggi larghi almeno `2 * r + 1` pixel, con
   `r = max(5, longest side // 250) // 2`; il bianco tra i punti è più stretto
   di così. Questo risultato si usa solo se dà una pagina intera. È una
   tolleranza di questo decodificatore, non una proprietà del formato: una
   pagina ha un bordo intero.
4. **Angoli.** Da ciascun angolo della scansione il decodificatore percorre le
   diagonali verso l'interno e prende il primo pixel sotto la soglia. Questo
   richiede che la pagina sia diritta e più alta che larga; una scansione più
   larga che alta viene prima ruotata (7.5).
5. **Dimensione dei pixel.** I pixel della scansione per pixel della pagina, in
   orizzontale e in verticale, derivano dalle distanze tra gli angoli divise per
   `width` e `height`; le direzioni delle righe e delle colonne della pagina
   derivano dalle medie dei lati opposti. (La dimensione orizzontale usa due
   volte l'angolo in alto a sinistra e mai quello in basso a sinistra. È un
   comportamento ereditato del decodificatore e non fa parte del formato.)

### 7.3 Croci { #73-crosses }

La prima croce è attesa `border + chalf` pixel della pagina verso l'interno
dall'angolo in alto a sinistra. Ogni altra croce è attesa un passo a destra
della sua vicina di sinistra, e la prima di una riga un passo sotto quella che
le sta sopra, per cui ogni ricerca parte da una croce già trovata. Per ciascuna
croce:

1. una ricerca approssimativa su pixel interi della scansione, fino a metà di
   `chalf` (un quarto del lato della croce) in ogni direzione, della posizione in cui l'immagine ha la
   correlazione migliore con il motivo della croce (scuro, chiaro, chiaro,
   scuro);
2. una ricerca fine entro mezzo pixel della scansione a incrementi di un quarto
   di pixel, su una croce rimpicciolita di `cross_trim` pixel della pagina su
   ogni lato;
3. un proprio livello di soglia: dai pixel della croce, `white` e `black` come
   in 7.2, combinati come `white_cut * white + (1 - white_cut) * black`.

### 7.4 Campionamento e decodifica { #74-sampling-and-decoding }

1. **Filtri.** Le macchie scure più strette di `minmax_filter` volte la
   dimensione di un pixel della pagina vengono rimosse (passate di un filtro di
   massimo, poi altrettante di un filtro di minimo); l'immagine viene poi
   sfocata con un kernel 3 per 3 (1 2 1 / 2 4 2 / 1 2 1),
   `round(pixel area * pixel_blur ^ 2)` volte.
2. **Campionamento.** La posizione nella scansione di ogni pixel di dati viene
   interpolata tra le quattro croci che lo circondano, e così anche il suo
   livello di soglia. Il campione viene reso più nitido:
   `value + unsharp_mask * (value - mean of the four neighbours at unsharp_dist page pixels)`.
   Il bit è 1 quando il risultato è sotto il livello di soglia.
3. **Decodifica.** I bit vengono rimessi nei simboli (sezione 2.6). Un simbolo
   di Golay viene sostituito dal simbolo più vicino se questo differisce in al
   massimo 3 bit; altrimenti il simbolo non è correggibile e i suoi 12 bit alti
   vengono presi così come sono stati letti. In un simbolo di Hamming si
   corregge un bit errato; due bit errati lo rendono non correggibile.
4. Le parole di una pagina vengono unite nei suoi `net_bits` bit di dati. Per un
   documento semplice o con contrassegno i bit delle pagine vengono uniti in
   ordine di pagina e tagliati in byte; i bit che non riempiono un ultimo byte
   vengono scartati.

```example
decoder_unsharp_mask = 7
decoder_unsharp_dist = 1
decoder_sync_white_cut = 0.1
decoder_white_cut = 0.06
decoder_minmax_filter = 0.5
decoder_pixel_blur = 0.25
decoder_cross_trim = 0.75
```

### 7.5 Identificare una scansione { #75-identifying-a-scan }

Quando non gli viene indicato il formato di pagina, questo progetto lo ricava:

1. Il contorno della pagina (7.2, fasi da 1 a 4) ne dà la forma. Le due carte
   vengono provate in ordine di quanto la forma è vicina alla loro pagina
   `standard`; ciascuna viene provata diritta e ruotata di mezzo giro (o di un
   quarto di giro in un senso o nell'altro per una scansione più larga che
   alta).
2. Per ciascuna carta, prima la sua pagina `standard`: la pagina viene
   localizzata e la sua etichetta letta confrontando ogni cella del carattere
   con il font. Un contrassegno valido decide subito (sezione 6.1).
   Un'etichetta senza contrassegno è accettata solo se è stata letta in modo
   chiaro, e anche allora nei dati si cerca comunque un'intestazione, perché una
   pagina autoidentificante con punti standard ha un'etichetta di questo tipo.
3. Poi i layout della carta, a partire dalla forma più vicina: la pagina viene
   localizzata e decodificata, e decide un'intestazione accettabile (sezione
   6.2).

Un contrassegno letto male supera il controllo circa una volta su 256;
un'etichetta senza contrassegno non ha alcun controllo, ed è per questo che deve
essere letta in modo chiaro e che viene rifiutato un testo libero che dista un
solo carattere letto male da un contrassegno valido. Questi criteri di
accettazione appartengono a questo programma di lettura, non al formato.

### 7.6 Il metodo di lettura lento { #76-the-slower-reader }

Questo progetto prova un secondo metodo di lettura, più lento
(`src/optar/decoder/soft.py`), pensato per una scansione a risoluzione troppo
bassa per la sua dimensione dei punti, in due casi. Primo: le fasi di 7.5 non
identificano nulla, benché il contorno di una pagina sia stato trovato. Secondo:
valgono tutte e tre queste condizioni: le fasi di 7.5 accettano una pagina in
base alla sola etichetta senza contrassegno; un pixel di dati di quella scansione
è largo meno di 2.5 pixel della scansione; e l'1% o più dei simboli della pagina
non è correggibile. Per ciascun layout e ciascuna rotazione
candidati, nell'ordine di 7.5, il metodo:

1. ingrandisce la scansione in modo che un pixel di dati sia largo circa quattro
   pixel della scansione, e localizza la pagina come in 7.2 e 7.3;
2. legge la pagina come in 7.4 e prende come noti i simboli decodificati con al
   massimo un bit corretto;
3. campiona una griglia di 7 per 7 posizioni distanti mezzo pixel di dati
   attorno a ogni pixel di dati e adatta, con i minimi quadrati, un filtro da
   quei campioni ai bit noti, un filtro per ciascuna di 16 per 22 zone della
   pagina;
4. applica i filtri a ogni pixel di dati, il che dà una confidenza con segno per
   ciascun bit, e sceglie, per ogni simbolo della pagina, il simbolo di Golay
   (sezione 2.5) che meglio si adatta alle sue 24 confidenze;
5. prende come noti il 60% dei simboli con la confidenza più alta e ripete dalla
   fase 3, per cinque adattamenti in tutto.

Una pagina viene accettata solo in base a un'intestazione accettabile (sezione
6.2). L'etichetta non viene letta, per cui una pagina senza intestazione (un
documento semplice o con contrassegno, parte 3) non viene identificata in questo
modo. Una pagina il cui contrassegno è stato accettato non viene mai letta in
questo modo, per cui la sezione 6.1 resta valida. Il risultato va
al contenitore esattamente come quello del metodo di lettura normale, e solo
l'impronta verifica il file (sezione 6.3). Nulla di questo metodo di lettura fa
parte del formato, ed esso non cambia i risultati del decodificatore da 7.1 a
7.5.

Vettori: `tests/vectors/c/decoder.json`, `tests/vectors/c/decoder_internals.json`
(fissano i risultati di questo decodificatore su scansioni prestabilite, non il
formato).

## 8. Storia { #8-history }

La pagina della parte 2 è il formato di Twibright Optar, un programma in C
scritto da Karel Kulhavy nel 2007; in seguito è stato mantenuto, a partire dal
2012, in `colindean/optar`. I
suoi sorgenti sono conservati senza modifiche nella cartella `lega-c` di questo
progetto, così come erano al commit `9c8379c25466bf142459a26b0f34521bdde2af12`
di quel repository. I vettori in `tests/vectors/c` sono stati registrati da quel
programma; quelli in `tests/vectors/py` da questo progetto.

| Versione | Che cosa ha aggiunto |
|---|---|
| Programma in C | la pagina (parte 2); A4 o Letter scelti in fase di compilazione |
| 0.1.0 | le stesse pagine, scritte e lette da questo progetto |
| 0.2.0 | il contrassegno (parte 3) |
| 0.3.0 | il contenitore, le dimensioni dei punti e i layout (parti 4 e 5), con riempimento a zeri |
| 0.3.1 | il flusso di riempimento (sezione 4.7) |

Che cosa il formato conserva del programma in C:

- il bordo, le croci, l'ordine dei pixel di dati e l'interlacciamento;
- la tabella di Golay, costruita dal dodecaedro, e i codici di Hamming;
- la striscia del font, la riga dell'etichetta e le sue tre particolarità
  (sezione 2.8);
- il limite di 9999 pagine, e il file vuoto stampato come una pagina `1/0`;
- il fatto che una pagina non registri la lunghezza del proprio flusso;
- le griglie dei due layout `standard` e gli offset di quello Letter.
  Gli strumenti in C ponevano la pagina A4 a 19.22 e 17.44 pt, valori che non
  cadono su un numero intero di punti della stampante; questo progetto la pone
  agli offset della sezione 5.2.

Il programma in C ha un solo formato di pagina compilato al suo interno. Il suo
decodificatore accetta la stringa di formato come argomento, ma ne usa solo
l'ultimo campo.

Nell'etichetta rimane una differenza rispetto al programma in C: il programma in
C tagliava la riga dell'etichetta per byte, questo formato la taglia per
caratteri. I due danno la stessa pagina, a meno che la riga venga tagliata e
contenga caratteri non ASCII prima del taglio.

Comportamento del decodificatore ereditato dal programma in C che non fa parte
del formato (parte 7): le sette costanti della sezione 7.4, il doppio uso di un
angolo nella dimensione dei pixel, la ricerca degli angoli che richiede una
pagina diritta più alta che larga, e l'aritmetica in virgola mobile a 32 bit che
i vettori del decodificatore fissano.
