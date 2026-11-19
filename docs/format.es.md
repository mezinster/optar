---
source_hash: 90182c569913da957ad8b2b3c51203f66726cc36
---

# El formato optar { #the-optar-format }

El texto normativo de esta especificación es el inglés, [The optar format](https://mezinster.github.io/optar/format/): el formato lo definen ese texto y los vectores de prueba de `tests/vectors`. Esta traducción es informativa; si difiere del texto inglés, prevalece el texto inglés.

optar guarda un archivo en papel como páginas de puntos negros y blancos. Este
texto define qué es una página y qué es un documento (un conjunto de páginas
que lleva un archivo), de modo que se pueda escribir un codificador cuyas
páginas lea este proyecto y un decodificador que lea las páginas de este
proyecto.

El texto tiene ocho partes:

1. Términos y convenciones
2. La página (versión 0)
3. La etiqueta del documento (impresiones 0.2.0)
4. Documentos autoidentificables (versión 1)
5. Impresión
6. Lo que debe hacer un lector
7. Decodificador de referencia (informativo)
8. Historia

Las partes 1 a 6 son normativas. «Debe» (must) se usa solo para lo que es una
página o un documento y, en la parte 6, para lo que un lector hace con lo que
ha leído. Cómo encuentra un lector una página en un escaneo y cómo la muestrea
no forma parte del formato; la parte 7 describe cómo lo hace este proyecto.

El formato queda fijado por los vectores de prueba de `tests/vectors`. Cada
sección normativa termina con una línea «Vectores:» que nombra los archivos que
la fijan; `tests/vectors/README.md` explica cómo se lee cada archivo. Las
tablas precedidas por un comentario `spec-table` y los bloques delimitados
marcados `example` se comparan con el código mediante `tests/unit/test_spec.py`.

## 1. Términos y convenciones { #1-terms-and-conventions }

### 1.1 Números, bits y bytes { #11-numbers-bits-and-bytes }

- Todos los enteros se escriben en decimal, salvo que lleven el prefijo `0x`.
- `a // b` es la división redondeada hacia abajo, `a mod b` su resto, y
  `ceil(a / b)` la división redondeada hacia arriba. Las tres se usan solo con
  enteros no negativos.
- Los recuentos y los índices empiezan en 0, salvo los números de página y las
  caras del dodecaedro de la sección 2.5, que empiezan en 1.
- Una **cadena de bits** se lee empezando por el bit más significativo: el bit
  `n` de una cadena de bytes es el bit `7 - (n mod 8)` del byte `n // 8`, donde
  el bit 7 de un byte es su bit más significativo. Una palabra de `w` bits
  tomada de una cadena de bits tiene como bit más significativo el primer bit
  de la cadena.
- Los enteros de varios bytes de la cabecera (sección 4.2) son big-endian: el
  byte más significativo primero.
- SHA-256 y CRC-32 son las funciones habituales. CRC-32 es el de zlib, PNG y
  Ethernet: polinomio reflejado `0xEDB88320`, valor inicial y XOR final
  `0xFFFFFFFF`.

### 1.2 Píxeles y colores { #12-pixels-and-colours }

- Una **página** es una imagen rectangular de **píxeles de página**. Cada píxel
  de página es negro o blanco.
- Un píxel de datos negro es el bit 1; un píxel de datos blanco es el bit 0.
- En los archivos de imagen en gris de 8 bits, un píxel negro tiene el valor 0
  y un píxel blanco el valor 255. Esta especificación no usa ninguna otra
  codificación de imagen.
- Las coordenadas de página son `(x, y)`: `x` cuenta columnas desde el lado
  izquierdo, `y` cuenta filas desde el lado superior, ambas desde 0. La página
  se imprime y se lee derecha, con la banda del rótulo (sección 2.8) abajo.
- Las **coordenadas del área de datos** `(u, v)` dejan fuera el borde (sección
  2.2): `u = x - border`, `v = y - border`.

### 1.3 Unidades { #13-units }

- Un **punto tipográfico** (pt) es 1/72 de pulgada.
- Un **punto de impresora** es 1/600 de pulgada: un punto físico de la
  impresora de 600 dpi para la que están hechos los diseños.
- Un **punto de datos** es un píxel de página tal como se imprime. Es un
  cuadrado de un número entero de puntos de impresora (sección 5.1). El punto
  de datos **estándar** mide 3 puntos de impresora de ancho, 1/200 de pulgada.

### 1.4 Tipos de documento { #14-kinds-of-document }

Un **flujo** es la cadena de bytes que las páginas de un documento llevan en
sus píxeles de datos. Existen tres tipos de documento; los tres están hechos de
las mismas páginas de versión 0 (parte 2).

| Tipo | Lo escribe | El flujo es | El rótulo lleva |
|---|---|---|---|
| simple | el programa en C, optar 0.1.0, `--no-tag` | el archivo | solo texto libre |
| con etiqueta | optar 0.2.0 y posteriores («compatible») | el archivo | la etiqueta (parte 3) |
| autoidentificable | optar 0.3.0 y posteriores | el contenedor (parte 4) | solo texto libre |

### 1.5 Constantes { #15-constants }

Los nombres de esta tabla se usan en todo el texto.

<!-- spec-table: constants -->
| Nombre | Valor | Significado |
|---|---|---|
| `PageFormat.version` | 0 | versión del formato de página |
| `PageFormat.cpitch` | 24 | distancia entre los orígenes de las cruces, en píxeles de página |
| `PageFormat.chalf` | 3 | la mitad del lado de una cruz, en píxeles de página |
| `PageFormat.fec_order` | 1 | código de página: 1 es Golay, de 2 a 5 son códigos de Hamming |
| `PageFormat.border` | 2 | grosor del borde, en píxeles de página |
| `PageFormat.text_height` | 24 | filas de la banda del rótulo |
| `LABEL_HEIGHT` | 24 | la única altura de la banda del rótulo que se puede dibujar |
| `TEXT_WIDTH` | 13 | ancho de una celda de carácter del rótulo, en píxeles del rótulo |
| `FIRST_CHAR` | 32 | código de carácter de la primera celda de la tira de la fuente |
| `GLYPH_CELLS` | 95 | celdas de carácter de la tira de la fuente |
| `MAX_PAGES` | 9999 | máximo de páginas de un documento |
| `FINGERPRINT_DIGITS` | 8 | dígitos hexadecimales de la huella en una etiqueta |
| `CHECK_DIGITS` | 2 | dígitos hexadecimales del control en una etiqueta |
| `MAX_SIZE_DIGITS` | 12 | máximo de dígitos decimales del tamaño en una etiqueta |
| `HEADER_MAGIC` | "oPt1" | primeros cuatro bytes de una cabecera, en ASCII |
| `CONTAINER_VERSION` | 1 | byte de versión de una cabecera |
| `HEADER_SIZE` | 38 | bytes de una copia de la cabecera |
| `HEADER_COPIES` | 5 | copias de la cabecera en cada página |
| `FINGERPRINT_SIZE` | 16 | bytes de la huella en una cabecera |
| `CODEWORD` | 255 | bytes de una palabra de código Reed-Solomon |
| `SPREAD_STEP` | 7919 | salto de la dispersión (sección 4.6) |
| `NAME_MAX_BYTES` | 255 | máximo de bytes del nombre de archivo guardado |
| `PADDING_KEY` | "optar padding" | clave del flujo de relleno, en ASCII |
| `PADDING_BLOCK` | 32 | bytes de un bloque del flujo de relleno |
| `PROTECTED_MAX_BYTES` | 268435456 | máximo de bytes de página de un documento con paridad |
| `PROMISE_NUM` | 3 | numerador de la fracción de la paridad sobre la que prometen las herramientas (4.9) |
| `PROMISE_DEN` | 4 | denominador de esa fracción |
| `PRINTER_DPI` | 600 | puntos de impresora por pulgada |
| `PIXELS_PER_INCH` | 200 | puntos de datos estándar por pulgada |
| `STANDARD_PRINTER_DOTS` | 3 | puntos de impresora a lo ancho de un punto de datos estándar |
| `POINTS_PER_INCH` | 72 | puntos tipográficos por pulgada |
| `SCAN_PIXELS_PER_DOT` | 3 | píxeles de escaneo por punto de datos a la resolución de escaneo recomendada |
| `MIN_MARGIN_PT` | 12 | margen mínimo alrededor de una página impresa, en puntos tipográficos |

## 2. La página (versión 0) { #2-the-page-version-0 }

### 2.1 El formato de página y la cadena de formato { #21-the-page-format-and-the-format-string }

Un **formato de página** son ocho enteros no negativos:

| Campo | Nombre | Significado | Debe ser |
|---|---|---|---|
| 1 | `version` | versión del formato de página | 0 |
| 2 | `xcrosses` | cruces en una fila | al menos 2 |
| 3 | `ycrosses` | cruces en una columna | al menos 2 |
| 4 | `cpitch` | distancia entre los orígenes de las cruces | más de `2 * chalf` |
| 5 | `chalf` | la mitad del lado de una cruz | al menos 1 |
| 6 | `fec_order` | código de página | de 1 a 5 |
| 7 | `border` | grosor del borde | al menos 1 |
| 8 | `text_height` | filas de la banda del rótulo | `LABEL_HEIGHT` |

La **cadena de formato** son los ocho campos en este orden, en decimal sin
ceros a la izquierda, unidos por `-`. Cada página imprime su cadena de formato
en su rótulo (sección 2.8). Las páginas que imprime este proyecto solo
difieren en `xcrosses` y `ycrosses`; los demás campos tienen los valores de la
sección 1.5. Los diez formatos de página que imprime se enumeran en la sección
5.2. Otros valores son páginas válidas y se leen cuando se le da al lector la
cadena de formato.

Todos los tamaños siguientes están en píxeles de página.

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

Los nombres con el prefijo `a4_` son del formato `0-65-93-24-3-1-2-24`, la
página A4 estándar.

Vectores: `tests/vectors/c/encoder_pages.json`.

### 2.2 Las partes de una página { #22-the-parts-of-a-page }

Una página tiene `width` columnas por `height` filas. De arriba abajo:

| Filas `y` | Contenido |
|---|---|
| de `0` a `border - 1` | borde: negro |
| de `border` a `border + data_height - 1` | columnas de `0` a `border - 1` y las últimas `border` columnas: negro. Entre ellas: el **área de datos**, `data_width` columnas |
| de `border + data_height` a `border + data_height + text_height - 1` | la **banda del rótulo**: negra en todo el ancho, con el rótulo dibujado en blanco en las columnas de `border` a `border + data_width - 1` (sección 2.8) |
| las últimas `border` filas | borde: negro |

```example
a4_label_top_row = 2216
```

Cada píxel del área de datos forma parte de una cruz (sección 2.3) o es un
píxel de datos (sección 2.4).

Vectores: `tests/vectors/c/encoder_pages.json`.

### 2.3 Cruces { #23-crosses }

El área de datos contiene `xcrosses * ycrosses` **cruces**, que un lector usa
para encontrar los píxeles de datos. La cruz `(i, j)`, `0 <= i < xcrosses`,
`0 <= j < ycrosses`, es el cuadrado de `2 * chalf` por `2 * chalf` píxeles
cuyo píxel superior izquierdo, su **origen**, está en las coordenadas del área
de datos `(i * cpitch, j * cpitch)`. Sus cuatro cuartos de `chalf` por `chalf`
píxeles son:

| Cuarto | Color |
|---|---|
| superior izquierdo | negro |
| superior derecho | blanco |
| inferior izquierdo | blanco |
| inferior derecho | negro |

La primera cruz toca la esquina superior izquierda del área de datos y la
última, su esquina inferior derecha. Un píxel `(u, v)` del área de datos forma
parte de una cruz exactamente cuando `u mod cpitch < 2 * chalf` y
`v mod cpitch < 2 * chalf`.

```example
a4_last_cross_x = 1538
a4_last_cross_y = 2210
```

Estas son las coordenadas de página `(x, y)` del origen de la última cruz.

Vectores: `tests/vectors/c/encoder_pages.json`.

### 2.4 Los píxeles de datos y su orden { #24-data-pixels-and-their-order }

Los **píxeles de datos** son los píxeles del área de datos que no forman parte
de una cruz. Se numeran desde 0 en orden de lectura: fila por fila desde arriba
y, dentro de una fila, de izquierda a derecha. El número de un píxel de datos
es su **posición de canal**; `total_bits` es el número de píxeles de datos.

Las filas del área de datos se repiten con periodo `cpitch`:

- una **franja estrecha** de `2 * chalf` filas que pasan por cruces. Cada fila
  contiene `narrow_width` píxeles de datos, en `xcrosses - 1` huecos de
  `gap_width` píxeles entre las cruces;
- una **franja ancha** de `gap_width` filas sin cruces. Cada fila contiene
  `data_width` píxeles de datos.

El último periodo solo tiene franja estrecha.

    gap_width     = cpitch - 2 * chalf
    narrow_width  = gap_width * (xcrosses - 1)
    narrow_pixels = 2 * chalf * narrow_width
    wide_pixels   = gap_width * data_width
    rep_pixels    = narrow_pixels + wide_pixels
    total_bits    = rep_pixels * (ycrosses - 1) + narrow_pixels

Las coordenadas del área de datos `(u, v)` de la posición de canal `n` son:

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

Las coordenadas de página son `(u + border, v + border)`.

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

`a4_xy_of_N` es `u, v` de la posición de canal `N`.

Vectores: `tests/vectors/c/bit_placement.json`.

### 2.5 El código de página { #25-the-page-code }

Los datos de una página se cortan en **palabras** de `small` bits. Cada
palabra se codifica en un **símbolo** de `large` bits, que se puede corregir
cuando algunos de sus bits se leen mal. `fec_order` selecciona el código:

| `fec_order` | Código | `large` | `small` |
|---|---|---|---|
| 1 | Golay (24, 12) | 24 | 12 |
| de 2 a 5 | Hamming extendido | `2 ^ fec_order` | `large - 1 - fec_order` |

```example
code_bits_of_order_1 = 24, 12
code_bits_of_order_2 = 4, 1
code_bits_of_order_3 = 8, 4
code_bits_of_order_4 = 16, 11
code_bits_of_order_5 = 32, 26
```

Aquí un símbolo se escribe como un entero de `large` bits; su **bit `b`**, en
el orden en que los bits se colocan en la página, se cuenta desde el bit más
significativo: el bit 0 es el bit de valor `2 ^ (large - 1)`.

#### Código de Golay (24, 12) { #golay-24-12 }

El símbolo de la palabra de 12 bits `d` es `d * 4096 + p(d)`: la palabra en los
12 bits superiores y 12 bits de paridad debajo de ella. Los bits de paridad
salen de un dodecaedro cuyas caras se numeran de 1 a 12. La cara `f`
representa el bit de valor `2 ^ (f - 1)` de `d`. Cada cara tiene cinco
vecinas:

<!-- spec-table: golay -->
| Cara | Vecinas | Máscara |
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

La máscara de la cara `r` tiene un 1 por cada cara que no es vecina de `r`
(incluida la propia cara `r`). El bit de paridad de la cara `r` es 1 cuando
`d AND mask` tiene un número impar de bits a 1. Es el bit de valor
`2 ^ (12 - r)` de `p(d)`: la cara 1 da el bit de paridad más significativo; la
cara 12, el menos significativo.

```example
golay_0x001 = 0x00183f
golay_0x800 = 0x800fc1
golay_0xabc = 0xabca13
golay_0xfff = 0xffffff
```

El código es lineal, la palabra 0 tiene el símbolo 0 y dos símbolos
cualesquiera difieren en al menos 8 bits. Por eso, un símbolo leído con hasta 3
bits erróneos tiene exactamente un símbolo a 3 bits o menos de él: el que se
imprimió. El archivo de vectores fija los 4096 símbolos.

#### Hamming extendido (`fec_order` de 2 a 5) { #extended-hamming-fec_order-2-to-5 }

Se numeran los bits del símbolo por su valor: la posición `q` es el bit de
valor `2 ^ q`, `0 <= q < large`.

1. Los bits de la palabra, empezando por el más significativo, van a las
   posiciones que no son ni 0 ni una potencia de dos, desde la posición
   `large - 1` hacia abajo.
2. Para `i` de 0 a `fec_order - 1`, la posición `2 ^ i` se elige de modo que
   las posiciones cuyo número tiene el bit `i` a 1 contengan un número par de
   bits a 1.
3. La posición 0 se elige de modo que todo el símbolo contenga un número par de
   bits a 1.

Un símbolo así se puede corregir cuando un bit es erróneo, y dos bits erróneos
se detectan. Con `fec_order` 2, el símbolo es el único bit de la palabra
repetido cuatro veces.

```example
hamming_2_of_1 = 1111
hamming_3_of_1011 = 10101010
hamming_4_of_10000000001 = 1000000100011000
hamming_5_of_1 = 00000000000000000000000000001111
```

Cada línea da una palabra en binario después de `of_` y su símbolo en binario,
empezando por el bit más significativo.

Vectores: `tests/vectors/c/golay.json`, `tests/vectors/c/encoder_pages.json`.

### 2.6 Los símbolos en la página { #26-symbols-on-the-page }

Una página contiene

    symbols   = total_bits // large
    used_bits = symbols * large
    net_bits  = symbols * small

`net_bits` es el número de bits de datos que lleva una página. Los símbolos se
entrelazan de modo que los píxeles vecinos pertenezcan a símbolos distintos:

    bit b of symbol s is at channel position  s + b * symbols

para `0 <= s < symbols` y `0 <= b < large`. Así, con el código de Golay los
píxeles de datos forman 24 grupos consecutivos de `symbols` píxeles, y cada
símbolo tiene un píxel en cada grupo, en el mismo lugar en cada uno.

Los píxeles de datos de las posiciones de canal `used_bits` y superiores no
pertenecen a ningún símbolo y son blancos.

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

Los nombres con `a4_medium_` son del formato `0-50-70-24-3-1-2-24`; los
`hamming_N_net_bits` son de la cuadrícula A4 con `fec_order` N.

Vectores: `tests/vectors/c/bit_placement.json`, `tests/vectors/c/encoder_pages.json`.

### 2.7 Del flujo a las páginas { #27-from-a-stream-to-pages }

Sea el flujo de `nbytes` bytes, leído como una cadena de bits (sección 1.1).

    pages = ceil(8 * nbytes / net_bits)

La página `p` (desde 1) lleva los bits `(p - 1) * net_bits` a
`p * net_bits - 1` del flujo. La palabra `s` de la página son los `small` bits
que empiezan en el bit `s * small` de los bits de la página, y el símbolo `s`
es su código (sección 2.5).

- Los bits posteriores al final del flujo son 0. Así, la última palabra que
  contiene bits del flujo se completa con bits 0 en su extremo bajo, y cada
  palabra posterior de la última página es 0. El símbolo de la palabra 0 es 0,
  de modo que esas palabras se imprimen como píxeles blancos.
- Un documento tiene como máximo `MAX_PAGES` páginas; un flujo más largo no se
  puede codificar.
- Un flujo vacío (`nbytes = 0`) da `pages = 0`. Se imprime como una página
  cuyos píxeles de datos son todos blancos y cuyo rótulo da el número de página
  1 y el total de páginas 0 (`1/0`).

Leer las páginas en orden y unir sus `net_bits` bits da el flujo seguido de
bits 0. Una página no registra dónde termina el flujo: un documento simple
devuelve su archivo rellenado con bytes cero hasta el final de su última
página (menos los bits que no llenan un byte, cuando `net_bits` no es múltiplo
de 8). La etiqueta (parte 3) y el contenedor (parte 4) registran ambos el
tamaño del archivo.

```example
a4_pages_for_0_bytes = 0
a4_pages_for_1_byte = 1
a4_pages_for_199773_bytes = 1
a4_pages_for_199774_bytes = 2
a4_words_for_1000_bytes = 667
```

Un flujo de 1000 bytes llena 667 palabras de la primera página; la última de
ellas contiene 8 bits del flujo y cuatro bits 0.

Vectores: `tests/vectors/c/encoder_pages.json`.

### 2.8 El rótulo { #28-the-label }

La banda del rótulo contiene una línea de texto, para las personas y, en un
documento con etiqueta, para el lector. Se dibuja con una fuente fija.

**La tira de la fuente** es una imagen de `LABEL_HEIGHT` filas y 1500
columnas, con cada píxel negro o blanco. Las columnas de `0` a
`TEXT_WIDTH * GLYPH_CELLS - 1` contienen `GLYPH_CELLS` celdas de carácter de
`TEXT_WIDTH` columnas: la celda del carácter de código `c`, `32 <= c <= 126`,
empieza en la columna `TEXT_WIDTH * (c - FIRST_CHAR)`. Las columnas restantes
contienen un logotipo. Los glifos y el logotipo son blancos sobre negro. La
tira es el archivo `src/optar/data/font.png` de este proyecto (un píxel suyo es
blanco cuando su valor de gris es 128 o más); su resumen, más abajo, es el
SHA-256 de sus píxeles como bytes 0 (negro) y 255 (blanco), fila por fila.

```example
strip_width = 1500
logo_width = 265
glyph_column_of_capital_a = 429
font_strip_sha256 = 481c0abd7884afb5ab6d958fbb95c0d6be97b0e2a7124f57e1abcd118d7d4bc4
```

**La línea del rótulo** de la página `page` de `total` con el texto libre
`text` es

    two spaces, the format string, a space, page, "/", total, a space, text

con `page` y `total` en decimal sin ceros a la izquierda. El espacio después de
`total` está ahí incluso cuando `text` está vacío. Después, la línea se recorta
a sus primeros `data_width // TEXT_WIDTH - 1` caracteres (puntos de código
Unicode).

**Dibujo.** La banda tiene `data_width` columnas de ancho, numeradas desde 0 en
la columna de página `border`; todo lo que no se dibuja en ella es negro.

1. Si `logo_width <= data_width`, el logotipo se copia en las columnas de la
   banda de `0` a `logo_width - 1`.
2. Un cursor empieza en la columna de la banda `logo_width`, se haya dibujado o
   no el logotipo.
3. Para cada carácter de la línea recortada, en orden: un carácter cuyo código
   esté por debajo de 32 o por encima de 127 se omite. Si no, cuando el cursor
   más `TEXT_WIDTH` es como máximo `data_width`, las `TEXT_WIDTH` columnas de
   la tira que empiezan en `TEXT_WIDTH * (code - FIRST_CHAR)` se copian en la
   banda en el cursor; en cualquiera de los dos casos, el cursor avanza
   `TEXT_WIDTH`.

Tres consecuencias que un codificador debe reproducir para imprimir las mismas
páginas:

- Una página muestra como máximo `(data_width - logo_width) // TEXT_WIDTH`
  caracteres, que son menos de aquellos a los que se recorta la línea; el resto
  no se dibuja.
- Los caracteres fuera de los códigos 32 a 127 no ocupan celda, pero cuentan
  para la longitud a la que se recorta la línea.
- El código 127 ocupa una celda y dibuja las primeras `TEXT_WIDTH` columnas
  del logotipo. Un rótulo así no se puede volver a leer.

```example
a4_label_line = "  0-65-93-24-3-1-2-24 3/7 backup.tar"
a4_label_characters = 117
a4_label_cells = 98
a4_xlarge_label_cells = 18
```

`a4_label_characters` es la longitud a la que se recorta la línea y
`a4_label_cells`, el número de caracteres que muestra una página. Una página
del formato `0-22-31-24-3-1-2-24` muestra 18 caracteres, menos de los que
tiene su cadena de formato; la sección 5.4 explica cómo se rotulan esas
páginas al imprimirlas.

Vectores: `tests/vectors/c/label.json`, `tests/vectors/c/encoder_pages.json`.

## 3. La etiqueta del documento (impresiones 0.2.0) { #3-the-document-tag-020-printouts }

Un documento simple no dice cuánto mide su archivo, qué páginas van juntas ni
si el archivo se leyó correctamente. Un **documento con etiqueta** lo dice en
el texto libre de cada rótulo. Su flujo es el propio archivo, de modo que sus
páginas también las leen programas que no saben nada de la etiqueta.

### 3.1 La etiqueta { #31-the-tag }

Para un archivo de `size` bytes:

- `SIZE` es `size` en decimal sin ceros a la izquierda (`0` para un archivo
  vacío), con `MAX_SIZE_DIGITS` dígitos como máximo;
- `FINGERPRINT` son los primeros `FINGERPRINT_DIGITS` caracteres del SHA-256
  del archivo, escrito en hexadecimal en minúsculas;
- `CHECK`, para la página `page` de `total`, son los primeros `CHECK_DIGITS`
  caracteres del SHA-256 en hexadecimal en minúsculas del texto ASCII
  `SIZE:FINGERPRINT:page/total`, con `page` y `total` escritos como en la línea
  del rótulo.

La etiqueta de una página es el texto `[SIZE:FINGERPRINT:CHECK]`. El texto
libre del rótulo de la página es la etiqueta, o bien la etiqueta, un espacio y
un nombre. `SIZE` y `FINGERPRINT` son iguales en todas las páginas de un
documento; `CHECK` cambia de una página a otra.

Un archivo vacío es una página rotulada `1/0` (sección 2.7); su control se
calcula con `page` 1 y `total` 0.

```example
tag_fingerprint_of_x = 2d711642
tag_check_input = "1:2d711642:1/1"
tag_check_of_x_page_1_of_1 = ca
tag_free_text = "[1:2d711642:ca] name.tar"
tag_of_empty_file = "[0:e3b0c442:e0]"
```

Las cuatro primeras líneas son del archivo de un byte `x` impreso con el nombre
`name.tar`.

Vectores: `tests/vectors/py/tag.json`.

### 3.2 Cuándo es válida una etiqueta { #32-when-a-tag-is-valid }

El texto libre de un rótulo **empieza con una etiqueta** cuando empieza con
`[`, un tamaño como el descrito arriba, `:`, exactamente 8 caracteres de
`0-9a-f`, `:`, exactamente 2 caracteres de `0-9a-f` y `]`, y a la etiqueta le
sigue un espacio o el final del texto.

Una etiqueta leída de la página `page` de `total` en el formato de página `F`
es **válida** cuando se cumplen las dos condiciones:

- su control es igual al control calculado a partir del tamaño, la huella,
  `page` y `total` tal como se leyeron;
- el tamaño encaja con el total de páginas: `size = 0` y `total = 0`, o bien
  `size > 0`, `total > 0` y `(total - 1) * capacity < size <= total * capacity`
  con `capacity = net_bits // 8` de `F`.

En los dos diseños `standard` (sección 5.2), `net_bits` es múltiplo de 8, de
modo que un tamaño encaja exactamente con el total de páginas que le asigna la
sección 2.7. El lector de este proyecto identifica las páginas por su etiqueta
solo en esos dos diseños.

Vectores: `tests/vectors/py/tag.json`.

## 4. Documentos autoidentificables (versión 1) { #4-self-identifying-documents-version-1 }

Un **documento autoidentificable** lleva, en los datos de cada página, una
cabecera que dice a qué documento pertenece la página y qué página es, y puede
llevar paridad con la que se reparan las páginas dañadas y ausentes. El
archivo, su nombre y la paridad se empaquetan en un flujo, el **contenedor**, y
ese flujo se imprime como páginas ordinarias de versión 0 (parte 2). La versión
1 es la versión del contenedor; el formato de página conserva la versión 0.

### 4.1 Tamaños { #41-sizes }

Para un formato de página `F`, un nivel de paridad `parity` (sección 4.4) y un
total de páginas `T`:

    page_bytes = net_bits // 8                         payload of one page
    page_body  = page_bytes - HEADER_COPIES * HEADER_SIZE
    k          = CODEWORD - parity                     data bytes of a codeword
    m(T)       = T * page_body // CODEWORD             codewords
    D(T)       = m(T) * k                              bytes of the data region

La **carga útil** de una página son sus primeros `page_bytes * 8` bits de
datos tomados como bytes. El **cuerpo** de una página es su carga útil sin las
copias de la cabecera (sección 4.3), `page_body` bytes. El **cuerpo del
documento** son los cuerpos de las páginas 1 a `T` unidos, `T * page_body`
bytes.

Un formato de página solo puede llevar un contenedor si
`page_bytes // HEADER_COPIES >= HEADER_SIZE`.

```example
a4_page_bytes = 199773
a4_page_body = 199583
```

Vectores: `tests/vectors/py/container.json`.

### 4.2 La cabecera { #42-the-header }

Una cabecera tiene `HEADER_SIZE` bytes:

<!-- spec-table: header-fields -->
| Desplazamiento | Tamaño | Campo | Tipo | Contenido |
|---|---|---|---|---|
| 0 | 4 | `magic` | bytes | `HEADER_MAGIC` |
| 4 | 1 | `version` | entero | `CONTAINER_VERSION` |
| 5 | 1 | `parity` | entero | bytes de paridad por palabra de código: 0, 32 o 64 |
| 6 | 2 | `page` | entero | número de esta página, desde 1 |
| 8 | 2 | `total` | entero | páginas del documento |
| 10 | 8 | `size` | entero | tamaño del archivo en bytes |
| 18 | 16 | `fingerprint` | bytes | primeros `FINGERPRINT_SIZE` bytes del SHA-256 del archivo |
| 34 | 4 | `crc` | entero | CRC-32 de los bytes 0 a 33 |

Los enteros son big-endian. Todos los campos salvo `page` (y, con él, `crc`)
son iguales en todas las páginas de un documento.

```example
header_bytes = 6f5074310140000300070000000000086e3c000102030405060708090a0b0c0d0e0f1ef0ca9d
header_crc = 0x1ef0ca9d
```

Esta es la cabecera de la página 3 de 7 de un archivo de 552508 bytes con
paridad 64 cuya huella son los bytes de `00` a `0f`.

Vectores: `tests/vectors/py/container.json`.

### 4.3 La carga útil de una página { #43-the-payload-of-a-page }

La copia `c` de la cabecera de la página, `0 <= c < HEADER_COPIES`, está en los
bytes de la carga útil

    c * (page_bytes // HEADER_COPIES)   to   c * (page_bytes // HEADER_COPIES) + HEADER_SIZE - 1

Los demás bytes de la carga útil, en orden, son el cuerpo de la página.

```example
a4_header_offsets = 0, 39954, 79908, 119862, 159816
```

Vectores: `tests/vectors/py/container.json`.

### 4.4 Niveles de paridad { #44-parity-levels }

<!-- spec-table: parity -->
| Nombre | Bytes de paridad | Bytes de datos |
|---|---|---|
| none | 0 | 255 |
| standard | 32 | 223 |
| high | 64 | 191 |

«Bytes de paridad» es el campo de cabecera `parity`; «Bytes de datos» es `k`.
Un documento con paridad 0 tiene cabeceras y un nombre, pero no se repara nada.

Vectores: `tests/vectors/py/container.json`.

### 4.5 El código Reed-Solomon { #45-the-reed-solomon-code }

Una **palabra de código** son `CODEWORD` bytes: `k` bytes de datos seguidos de
`parity` bytes de paridad.

- Los bytes son elementos de GF(256) con el polinomio del cuerpo
  `x^8 + x^4 + x^3 + x^2 + 1` (`0x11D`): un byte es un polinomio sobre GF(2)
  cuyo coeficiente de `x^7` es su bit más significativo, la suma es XOR y la
  multiplicación es la multiplicación de polinomios módulo el polinomio del
  cuerpo.
- `alpha` es el elemento `0x02`.
- El polinomio generador es
  `g(x) = (x - alpha^0)(x - alpha^1) ... (x - alpha^(parity - 1))`.
- El byte `i` de una palabra de código, `0 <= i <= 254`, es el coeficiente de
  `x^(254 - i)` del polinomio de la palabra de código `c(x)`.
- Los bytes de datos son los coeficientes de `x^254` hasta `x^parity`. Los
  bytes de paridad se eligen de modo que `g(x)` divida a `c(x)`: son el resto
  de la división del polinomio de datos (con coeficientes cero por debajo de
  `x^parity`) entre `g(x)`, empezando por el coeficiente de `x^(parity - 1)`.

Una palabra de código se puede reparar cuando `2 * e + f <= parity`, donde `f`
es el número de sus bytes de los que se sabe que son ilegibles (borrados) y
`e`, el número de los demás bytes que son erróneos.

```example
gf_alpha_8 = 0x1d
gf_alpha_254 = 0x8e
rs_32_parity_of_one = 744034ae367e10c2a221219db0c5e10c3b37fde4942fb3b9188afd148e37ac58
rs_32_parity_of_counting = 41841183b11fdb537421939696cda70e1db5c86684af222564b89cc6069f172e
```

`rs_32_parity_of_one` es la paridad, para la paridad 32, de los 223 bytes de
datos que son todos cero salvo un último byte de 1; estos son los coeficientes
de `g(x)` desde `x^31` hasta `x^0`. `rs_32_parity_of_counting` es la paridad
de los bytes de datos 0, 1, 2, ..., 222.

Vectores: `tests/vectors/py/reed_solomon.json`.

### 4.6 La región de datos y la dispersión { #46-the-data-region-and-the-spread }

La **región de datos** son `D(T)` bytes:

| Bytes | Contenido |
|---|---|
| `size` | el archivo |
| 1 | `L`, la longitud del nombre en bytes, de 0 a `NAME_MAX_BYTES` |
| `L` | el nombre del archivo en UTF-8 |
| el resto | relleno (sección 4.7) |

Un nombre de más de `NAME_MAX_BYTES` bytes en UTF-8 se recorta al mayor número
entero de caracteres que cabe. La huella no cubre el nombre. Un carácter del
nombre que UTF-8 no puede codificar (un punto de código suplente aislado, de
U+D800 a U+DFFF) se guarda como `?`.

La palabra de código `j`, `0 <= j < m`, tiene como bytes de datos los bytes
`j * k` a `j * k + k - 1` de la región de datos. Con paridad 0, una palabra de
código son sus 255 bytes de datos.

**La dispersión.** El byte `i` de la palabra de código `j` es el byte del
cuerpo del documento en la posición

    i * m + (j + i * SPREAD_STEP) mod m

Así, el byte `i` de cada palabra de código está en el tramo de `i * m` a
`(i + 1) * m - 1` del cuerpo, y los 255 bytes de una palabra de código están
en 255 tramos distintos, dispersos por todo el documento: un daño en un lugar
le cuesta a cada palabra de código unos pocos bytes, en lugar de costarles todo
a unas pocas palabras de código.

Los últimos `T * page_body - CODEWORD * m` bytes del cuerpo (menos de
`CODEWORD`) no pertenecen a ninguna palabra de código y son relleno.

Vectores: `tests/vectors/py/container.json`.

### 4.7 Relleno { #47-padding }

El relleno no lleva nada. Existen dos contenidos, y los dos son válidos:

- optar 0.3.0 escribía bytes cero;
- optar 0.3.1 y posteriores escriben el **flujo de relleno**: su bloque `n`,
  `n = 0, 1, 2, ...`, son los `PADDING_BLOCK` bytes del SHA-256 de
  `PADDING_KEY` seguido de `n` como 8 bytes, big-endian; el flujo son los
  bloques unidos. El relleno de la región de datos es el flujo desde su byte 0;
  el relleno del final del cuerpo continúa el flujo donde se detuvo el relleno
  de la región de datos. (Los bytes cero se imprimen como líneas blancas que
  atraviesan cada página; el flujo se imprime como si fueran datos.)

Un documento cuyo relleno sea cualquier otra cosa sigue siendo un documento
válido para un lector (sección 6.4), pero solo el flujo de relleno da las
páginas que imprime este proyecto.

```example
padding_block_0 = d518824e181c15b2f69e390066efbfa00d73eb8f0c3d932313396940eedd1286
padding_bytes_30_to_33 = 12863e00
```

Vectores: `tests/vectors/py/container.json`.

### 4.8 El total de páginas y los límites { #48-the-page-count-and-the-limits }

Un documento tiene el menor número de páginas que contienen el archivo, el
byte de longitud y el nombre:

    need = size + 1 + L
    T    = the smallest T >= 1 with D(T) >= need

Los límites son:

- `T <= MAX_PAGES`;
- con `parity > 0`: `T * page_bytes <= PROTECTED_MAX_BYTES`;
- `size < 2^64`, `L <= NAME_MAX_BYTES`.

Un archivo que necesite más no se puede poner en un documento.

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

El ejemplo es un archivo de 1000000 bytes llamado `vector.bin` en páginas A4
estándar con paridad 32. Necesita 4485 palabras de código; cinco páginas
contienen menos y seis contienen `m = 4696`. El documento tiene las 4696
palabras de código; las que el archivo no necesita contienen relleno.
`plan_spare_bytes` es el relleno del final del cuerpo y
`plan_padding_in_region`, el relleno de la región de datos. Las posiciones son
posiciones en el cuerpo del documento (sección 4.6).

Vectores: `tests/vectors/py/container.json`.

### 4.9 Lo que soporta el documento (informativo) { #49-what-the-document-withstands-informative }

Una página perdida le cuesta a una palabra de código como máximo
`ceil(page_body / m) + 1` bytes. Este proyecto le dice a su usuario que se
pueden perder `n` páginas cualesquiera cuando
`n * (ceil(page_body / m) + 1) <= PROMISE_NUM * parity // PROMISE_DEN`, lo que
deja una cuarta parte de la paridad para los daños en las páginas que quedan.
Es una promesa de las herramientas, no una propiedad en la que un lector pueda
confiar ni que deba comprobar.

### 4.10 Del contenedor a las páginas { #410-from-the-container-to-pages }

El flujo tiene `T * net_bits // 8` bytes. Leído como cadena de bits, la carga
útil de la página `p` (desde 1) empieza en el bit `(p - 1) * net_bits`; todos
los demás bits son 0. Cuando `net_bits` es múltiplo de 8, el flujo son
simplemente las cargas útiles unidas. Cuando no lo es, cada página tiene
`net_bits mod 8` bits sin usar después de su carga útil, y las cargas útiles
de algunas páginas no empiezan al principio de un byte del flujo.

El flujo se imprime como dice la sección 2.7, lo que da exactamente `T`
páginas. El rótulo de una página es una línea de rótulo ordinaria cuyo texto
libre es para las personas: es el nombre del archivo (el rótulo que dio el
usuario, o el nombre del archivo), el mismo en todas las páginas, y no lleva
etiqueta. (Una etiqueta válida haría que un lector tomara la página por una
página de un documento con etiqueta, sección 6.1.)

Con el código de Golay, `net_bits mod 8` es 0 o 4 y la última carga útil
siempre termina dentro del flujo. Este proyecto imprime documentos
autoidentificables solo en los diez formatos de página de la sección 5.2, y su
lector busca cabeceras solo en esos formatos.

```example
a4_medium_stream_bytes_for_3_pages = 344713
a4_medium_page_2_starts_at = 114904, 4
a4_medium_page_3_starts_at = 229809, 0
```

Una página del formato `0-50-70-24-3-1-2-24` tiene `net_bits = 919236`, lo que
deja 4 bits después de sus 114904 bytes de carga útil. Los dos valores son el
byte del flujo en el que empieza la carga útil de la página y el bit dentro de
ese byte (0 es el más significativo).

Vectores: `tests/vectors/py/container.json`, `tests/vectors/c/container_pages.json`.

## 5. Impresión { #5-printing }

### 5.1 Tamaños de punto { #51-dot-sizes }

Una página se imprime con uno de cinco tamaños de punto. Un punto de datos es
un cuadrado de un número entero de puntos de impresora, de modo que cada píxel
de página se imprime como el mismo cuadro de puntos de impresora.

<!-- spec-table: dot-sizes -->
| Nombre | Puntos de impresora por punto de datos | Puntos de datos por pulgada | Tamaño de punto (pt) | Escaneo recomendado (dpi) |
|---|---|---|---|---|
| standard | 3 | 200 | 0.36 | 600 |
| medium | 4 | 150 | 0.48 | 450 |
| big | 5 | 120 | 0.6 | 360 |
| large | 6 | 100 | 0.72 | 300 |
| xlarge | 9 | 200/3 | 1.08 | 200 |

La resolución de escaneo recomendada da `SCAN_PIXELS_PER_DOT` píxeles de
escaneo por punto de datos. Es una recomendación; una página es la misma página
a cualquier resolución de escaneo.

### 5.2 Diseños { #52-layouts }

Un **diseño** es un papel, un tamaño de punto y el formato de página impreso en
él. Hay diez. Los papeles se llaman `a4` y `letter`.

<!-- spec-table: layouts -->
| Papel | Puntos | Cruces a lo ancho | Cruces a lo alto | Cadena de formato | Ancho (px) | Alto (px) | Bits netos | Bytes de página | Bytes de cuerpo |
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

«Bytes de página» y «Bytes de cuerpo» son `page_bytes` y `page_body` de la
sección 4.1. Este proyecto imprime un documento simple o con etiqueta en un
diseño `standard` (o, cuando se le da a mano una cadena de formato, en ese
formato de página con el tamaño de punto estándar y los desplazamientos del
diseño `standard` del papel, siempre que cada margen sea de al menos
`MIN_MARGIN_PT`), y un documento autoidentificable en cualquiera de los diez
diseños.

Vectores: `tests/vectors/c/bit_placement.json`, `tests/vectors/py/container.json`.

La imagen de la página se coloca en el papel con su esquina inferior izquierda
en los desplazamientos siguientes, medidos desde la esquina inferior izquierda
del papel. Los márgenes son lo que queda a cada lado.

<!-- spec-table: layouts -->
| Papel | Puntos | Ancho del papel (pt) | Alto del papel (pt) | Desplazamiento x (pt) | Desplazamiento y (pt) | Izquierdo (mm) | Inferior (mm) | Derecho (mm) | Superior (mm) |
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

Cada desplazamiento es un número entero de puntos de impresora, de modo que los
lados de la imagen caen sobre puntos de impresora. Las cuadrículas y los
desplazamientos de los dos diseños `standard` son heredados (parte 8). Los
otros ocho son derivados: la cuadrícula es el mayor `xcrosses` y `ycrosses`
para el que la página, con su tamaño de punto, deja al menos `MIN_MARGIN_PT` en
cada lado, y cada desplazamiento es la mitad de la longitud libre, redondeada
hacia abajo a un punto de impresora entero. Son las tablas, no esta regla, las
que definen los diseños.

La identidad de una página no depende de dónde esté en el papel: un lector
encuentra la página por su borde. La colocación solo importa para la
impresión: una página impresa a otra escala tiene puntos de otro tamaño, y una
impresa más cerca del lado del papel puede quedar recortada.

### 5.3 El PDF que escribe este proyecto { #53-the-pdf-this-project-writes }

Cada página del documento es una página PDF cuya caja de medios (media box) es
el papel, `[0 0 width height]` en puntos tipográficos. La imagen de la página
es una sola imagen de 1 bit por píxel (1 es blanco), de `width` por `height`
píxeles de página, sin interpolación, dibujada con su esquina inferior
izquierda en los desplazamientos del diseño y escalada de modo que un píxel de
página sea un punto de datos:

    image width in points  = width  * dot size in points
    image height in points = height * dot size in points

```example
a4_large_image_width_pt = 560.16
a4_large_image_height_pt = 802.08
```

El PDF está pensado para imprimirse a tamaño real (100%). Ningún vector fija el
PDF; lo hace `tests/unit/test_pdf.py`.

Las imágenes de página también se escriben como archivos PNG o PGM con un
píxel de imagen por píxel de página; los vectores identifican una página por
el SHA-256 de su archivo PGM binario (`P5`), cuyos bytes exactos da
`tests/vectors/README.md`: la cabecera `P5\n<width> <height>\n255\n` en ASCII
y, después, los bytes de los píxeles fila por fila.

### 5.4 La tira del rótulo { #54-the-label-strip }

Un rótulo se dibuja en píxeles de página (sección 2.8), de modo que en una
página con puntos más grandes caben menos caracteres: con los más grandes,
demasiado pocos para su propia cadena de formato. Por eso, en un PDF, el
rótulo de una página de un diseño cuyo tamaño de punto no es `standard` se
sustituye por una **tira del rótulo**, una segunda imagen dibujada en puntos de
datos estándar:

- la tira tiene `LABEL_HEIGHT` filas y
  `floor(data_width * printer dots per data dot / STANDARD_PRINTER_DOTS)`
  columnas de píxeles de la tira;
- contiene la línea del rótulo de la página, recortada y dibujada como en la
  sección 2.8, con el ancho de la tira en lugar de `data_width`;
- en la imagen de la página, la banda del rótulo se vuelve negra en las
  columnas de `border` a `border + data_width - 1`;
- la tira se dibuja sobre la banda a 0.36 pt por píxel de la tira, con su lado
  izquierdo en el lado izquierdo de las columnas de datos de la banda y
  centrada en la altura de la banda.

Solo la banda del rótulo difiere de la página de la parte 2; el área de datos y
el borde no se tocan. Una página PNG o PGM de un diseño así conserva el rótulo
de la sección 2.8. El rótulo de una página autoidentificable no se usa para
identificarla (sección 6.2), de modo que un lector no necesita leer la tira.

```example
a4_large_strip_width = 1548
a4_large_strip_characters = 118
a4_large_strip_width_pt = 557.28
```

Vectores: `tests/vectors/c/container_pages.json` fija las páginas de dos
diseños con puntos más grandes como páginas ordinarias; la tira la fijan
`tests/unit/test_font.py` y `tests/unit/test_pdf.py`.

## 6. Lo que debe hacer un lector { #6-what-a-reader-must-do }

Un lector tiene páginas escaneadas y ha leído de cada una, por cualquier
método, sus bits de datos y, cuando ha podido, su rótulo. Esta parte dice qué
debe concluir de ellos. Los escaneos no son fiables: una página la puede
imprimir cualquiera y puede afirmar cualquier cosa.

### 6.1 Una etiqueta válida prevalece sobre una cabecera { #61-a-valid-tag-wins-over-a-header }

Para una página de un diseño `standard`, el lector debe mirar primero el
rótulo. Si el rótulo tiene la forma de la sección 2.8, lleva la cadena de
formato del diseño, un total de páginas de `MAX_PAGES` como máximo, un número
de página de 1 al total de páginas (o 1 con el total de páginas 0), y su texto
libre empieza con una etiqueta que es válida para ese número de página y ese
total (sección 3.2), la página es una página de un documento con etiqueta.
Debe tratarse como tal aunque sus datos contengan una cabecera válida.

El motivo: el flujo de un documento autoidentificable, tal como lo devuelve un
programa antiguo, se puede volver a imprimir como documento con etiqueta. Esas
páginas contienen cabeceras antiguas en sus datos, y son páginas del documento
con etiqueta, cuyo archivo es ese flujo.

### 6.2 La cabecera no es fiable { #62-a-header-is-untrusted }

Una copia de la cabecera está **bien formada** cuando su CRC es correcto, su
firma mágica es `HEADER_MAGIC`, su versión es `CONTAINER_VERSION`, su paridad
es 0, 32 o 64 y `1 <= page <= total`.

La **cabecera de una página** existe cuando al menos una de sus
`HEADER_COPIES` copias está bien formada y todas las copias bien formadas son
iguales. Una página cuyas copias bien formadas difieren no tiene cabecera.

Una cabecera leída de una página del formato `F` es **aceptable** cuando
describe un documento que la sección 4.8 permite, es decir, cuando se cumplen
todas estas condiciones (`m`, `D` y `page_bytes` como en la sección 4.1, para
`F` y la paridad de la cabecera):

1. `total <= MAX_PAGES`;
2. `page_bytes // HEADER_COPIES >= HEADER_SIZE`;
3. si `parity > 0`: `total * page_bytes <= PROTECTED_MAX_BYTES`;
4. `size + 1 <= D(total)`: las páginas contienen el archivo y el byte de
   longitud;
5. si `total > 1`: `size + 1 + NAME_MAX_BYTES > D(total - 1)`: ningún nombre
   habría permitido que el archivo cupiera en menos páginas.

Un lector no debe usar una cabecera que no sea aceptable. Las reglas 4 y 5
ligan el total de páginas al tamaño, de modo que una cabecera no pueda afirmar
muchas páginas para un archivo pequeño ni pocas para un archivo grande.

Un lector debe mantener su memoria y su tiempo en proporción a las páginas que
se le dieron, no a lo que afirma una cabecera: una página que afirma un
documento de 9999 páginas no debe hacer que el lector reserve memoria para
9999 páginas ni las procese.

Las páginas pertenecen a un mismo documento cuando sus cabeceras coinciden en
`fingerprint`, `size`, `total` y `parity` y las páginas tienen el mismo formato
de página. No se deben usar páginas de otro documento.

### 6.3 Solo la huella verifica un archivo { #63-only-the-fingerprint-verifies-a-file }

- **Documento autoidentificable.** Un byte de la carga útil es un borrado
  cuando uno de sus bits está en un símbolo que el código de página no pudo
  corregir; cada byte de una página que no se proporcionó es un borrado. El
  archivo son los primeros `size` bytes de la región de datos, y solo se
  recupera si cada palabra de código que contiene uno de esos bytes se leyó o
  se reparó (con paridad 0: no tiene ningún borrado). El archivo está
  **verificado** cuando se ha recuperado y los primeros `FINGERPRINT_SIZE`
  bytes de su SHA-256 son iguales a la huella de la cabecera.
- **Documento con etiqueta.** El archivo son los primeros `SIZE` bytes del
  flujo. Está **verificado** cuando tiene `SIZE` bytes y los primeros
  `FINGERPRINT_DIGITS` caracteres hexadecimales de su SHA-256 son iguales a la
  huella de la etiqueta.
- **Documento simple.** Nada lo verifica, y no se conoce su longitud (sección
  2.7).

Un lector no debe dar un archivo por verificado por ninguna otra razón. En
particular, una reparación que no informa de ningún fallo no verifica el
archivo: una palabra de código con más bytes erróneos de los que su paridad
puede reparar puede convertirse en otra palabra de código válida, y con
paridad 0 no se comprueba nada en absoluto.

El nombre del archivo (sección 4.6) queda fuera de la huella. Es texto no
fiable incluso cuando el archivo está verificado, como lo es todo rótulo.

### 6.4 El relleno nunca se lee { #64-padding-is-never-read }

Un lector no debe leer ni comprobar el relleno de la sección 4.7, ni depender
de él. Los bytes cero (0.3.0) y el flujo de relleno (0.3.1) son válidos los
dos, y un documento con cualquiera de ellos es el mismo documento para un
lector.

Los bytes de la región de datos posteriores al nombre son relleno. Un registro
de nombre cuyo byte de longitud apunte más allá del final de la región de
datos, o cuyos bytes no sean UTF-8, o que esté en una palabra de código que no
se reparó, no da ningún nombre; no invalida el archivo.

Vectores: `tests/vectors/py/container.json`, `tests/vectors/py/tag.json`.

## 7. Decodificador de referencia (informativo) { #7-reference-decoder-informative }

Esta parte describe cómo lee este proyecto un escaneo. Nada de ella es
obligatorio: un lector puede encontrar y muestrear una página de cualquier
manera. Los pasos y sus constantes son los del programa en C `unoptar` (parte
8); los resultados de este decodificador sobre escaneos concretos quedan
fijados por los vectores nombrados al final, de modo que no cambien por
accidente.

### 7.1 El escaneo { #71-the-scan }

Un escaneo se lee como una imagen en gris de 8 bits en luz lineal. Una muestra
`v` del archivo se convierte en `floor(255 * (v / 255) ^ (1 / gamma) + 0.5)`,
donde `gamma` es la gamma del archivo (PNG `gAMA`), o 0.454545 cuando el
archivo no da ninguna. Una imagen en color se convierte canal por canal y
después se pondera con 0.212671 para el rojo, 0.715160 para el verde y
0.072169 para el azul, con redondeo al entero más próximo. Una muestra de 16
bits conserva sus 8 bits superiores.

```example
linear_light_of_128 = 56
linear_light_of_200 = 149
```

### 7.2 Búsqueda de la página { #72-finding-the-page }

Al decodificador se le da el formato de página. Trabaja con la imagen derecha.

1. **Niveles de gris.** El nivel de corte empieza en el valor de gris medio.
   Hasta 32 veces: `black` es el corte menos la media cuadrática (RMS) de las
   distancias al corte de los píxeles que están por debajo de él, y `white` el
   corte más la de los píxeles que están por encima; el nuevo corte es
   `sync_white_cut * white + (1 - sync_white_cut) * black`, redondeado; el
   proceso se detiene cuando el corte ya no cambia. Un segundo nivel, el corte
   de llenado, está a medio camino entre `black` y `white`.
2. **Aislamiento de la página.** El blanco alrededor de la página es cada
   píxel igual o superior al corte de llenado que está conectado (por los
   lados, no por las esquinas) con una de las cuatro esquinas o con uno de los
   cuatro centros de los lados del escaneo. La página es todo lo demás que está
   conectado con el centro del escaneo. Todos los demás píxeles (suciedad entre
   la página y el lado del escaneo) se vuelven blancos.
3. **Un hueco en el marco.** Si una impresora recortó un lado de la página, el
   borde tiene un hueco, el blanco alrededor de la página se cuela entre los
   puntos y el paso 2 encuentra solo un trozo de la página. Cuando el área
   encontrada es menor que la mitad de lo que no es blanco alrededor de la
   página, se toma en su lugar como blanco alrededor de la página lo que se puede alcanzar a
   través de pasajes de al menos `2 * r + 1` píxeles de ancho, con
   `r = max(5, longest side // 250) // 2`; el blanco entre los puntos es más
   estrecho que eso. Este resultado solo se usa si da una página entera. Es una
   tolerancia de este decodificador, no una propiedad del formato: una página
   tiene un borde entero.
4. **Esquinas.** Desde cada esquina del escaneo, el decodificador recorre las
   diagonales hacia dentro y toma el primer píxel por debajo del corte. Esto
   requiere que la página esté derecha y sea más alta que ancha; un escaneo más
   ancho que alto se gira primero (7.5).
5. **Tamaño del píxel.** Los píxeles de escaneo por píxel de página, en
   horizontal y en vertical, salen de las distancias entre las esquinas
   divididas por `width` y `height`; las direcciones de las filas y las
   columnas de la página salen de las medias de los lados opuestos. (El tamaño
   horizontal usa la esquina superior izquierda dos veces y la esquina inferior
   izquierda ninguna. Es un comportamiento heredado del decodificador y no
   forma parte del formato.)

### 7.3 Cruces { #73-crosses }

La primera cruz se espera `border + chalf` píxeles de página hacia dentro desde
la esquina superior izquierda. Cada una de las demás cruces se espera un paso a
la derecha de su vecina izquierda, y la primera de una fila, un paso por debajo
de la que tiene encima, de modo que cada búsqueda parte de una cruz ya
encontrada. Para cada cruz:

1. una búsqueda gruesa sobre píxeles de escaneo enteros, hasta la mitad de
   media cruz en cada dirección, del lugar donde la imagen mejor se
   correlaciona con el patrón de la cruz (oscuro, claro, claro, oscuro);
2. una búsqueda fina dentro de medio píxel de escaneo, en incrementos de un
   cuarto de píxel, sobre una cruz reducida en `cross_trim` píxeles de página
   por cada lado;
3. un nivel de corte propio: a partir de los píxeles de la cruz, `white` y
   `black` como en 7.2, combinados como
   `white_cut * white + (1 - white_cut) * black`.

### 7.4 Muestreo y decodificación { #74-sampling-and-decoding }

1. **Filtros.** Se eliminan las motas oscuras más estrechas que
   `minmax_filter` veces el tamaño de un píxel de página (pasadas de un filtro
   de máximo y después otras tantas de un filtro de mínimo); a continuación, la
   imagen se difumina con un núcleo de 3 por 3 (1 2 1 / 2 4 2 / 1 2 1),
   `round(pixel area * pixel_blur ^ 2)` veces.
2. **Muestreo.** La posición en el escaneo de cada píxel de datos se interpola
   entre las cuatro cruces que lo rodean, y lo mismo su nivel de corte. La
   muestra se realza: `value + unsharp_mask * (value - mean of the four
   neighbours at unsharp_dist page pixels)`. El bit es 1 cuando el resultado
   está por debajo del nivel de corte.
3. **Decodificación.** Los bits se vuelven a reunir en símbolos (sección 2.6).
   Un símbolo de Golay se sustituye por el símbolo más cercano si este difiere
   en 3 bits como máximo; si no, el símbolo es no corregible y sus 12 bits
   superiores se toman tal como se leyeron. En un símbolo de Hamming se corrige
   un bit erróneo; dos bits erróneos lo hacen no corregible.
4. Las palabras de una página se unen en sus `net_bits` bits de datos. Para un
   documento simple o con etiqueta, los bits de las páginas se unen en orden de
   página y se cortan en bytes; los bits que no llenan un último byte se
   descartan.

```example
decoder_unsharp_mask = 7
decoder_unsharp_dist = 1
decoder_sync_white_cut = 0.1
decoder_white_cut = 0.06
decoder_minmax_filter = 0.5
decoder_pixel_blur = 0.25
decoder_cross_trim = 0.75
```

### 7.5 Identificación de un escaneo { #75-identifying-a-scan }

Cuando no se le dice el formato de página, este proyecto lo deduce:

1. El contorno de la página (7.2, pasos 1 a 4) da su forma. Los dos papeles se
   prueban por orden de lo cerca que está la forma de su página `standard`;
   cada uno se prueba derecho y girado media vuelta (o un cuarto de vuelta en
   cualquiera de los dos sentidos, para un escaneo más ancho que alto).
2. Para cada papel, primero su página `standard`: se localiza la página y se lee
   su rótulo comparando cada celda de carácter con la fuente. Una etiqueta
   válida decide de inmediato (sección 6.1). Un rótulo sin etiqueta solo se
   acepta cuando se leyó con claridad, y aun entonces se examinan los datos en
   busca de una cabecera, porque una página autoidentificable con puntos
   estándar tiene un rótulo así.
3. Después, los diseños del papel, empezando por la forma más cercana: se
   localiza la página, se decodifica, y decide una cabecera aceptable (sección
   6.2).

Una etiqueta mal leída supera su control aproximadamente una vez de cada 256; un rótulo sin etiqueta no tiene ningún control, y por eso debe leerse
con claridad y por eso se rechaza el texto libre que está a un carácter mal
leído de una etiqueta válida. Estos umbrales de aceptación pertenecen a este
lector, no al formato.

### 7.6 El lector lento { #76-the-slower-reader }

Cuando los pasos de 7.5 no identifican nada pero se encontró el contorno de
una página, o aceptan una página solo por un rótulo sin etiqueta en un escaneo
con menos de 2.5 píxeles de escaneo por píxel de datos mientras el 1% o más de
los símbolos de la página son no corregibles, este proyecto prueba un segundo
lector, más lento (`src/optar/decoder/soft.py`), pensado para un escaneo de
resolución demasiado baja para su tamaño de punto. Para cada diseño y cada
rotación candidatos, en el orden de 7.5:

1. amplía el escaneo de modo que un píxel de datos mida unos cuatro píxeles de
   escaneo de ancho, y localiza la página como en 7.2 y 7.3;
2. lee la página como en 7.4 y toma como conocidos los símbolos decodificados
   con un bit corregido como máximo;
3. muestrea una cuadrícula de 7 por 7 posiciones separadas medio píxel de datos
   alrededor de cada píxel de datos y ajusta, por mínimos cuadrados, un filtro
   que lleva de esas muestras a los bits conocidos, un filtro para cada una de
   las 16 por 22 regiones de la página;
4. aplica los filtros a cada píxel de datos, lo que da una confianza con signo
   para cada bit, y elige para cada símbolo de Golay la palabra de código que
   mejor se ajusta a sus 24 confianzas;
5. toma como conocido el 60% de los símbolos con más confianza y repite desde el
   paso 3, cinco ajustes en total.

Una página solo se acepta por una cabecera aceptable (sección 6.2). No se lee
ningún rótulo, de modo que una página sin cabecera (un documento simple o con
etiqueta, parte 3) no se identifica de esta manera. Una página cuya etiqueta se
aceptó nunca se lee de esta manera, de modo que la sección 6.1 se cumple. El
resultado va al contenedor exactamente igual que el del lector normal, y solo
la huella verifica el archivo (sección 6.3). Nada de este lector forma parte
del formato, y no cambia los resultados del decodificador de 7.1 a 7.5.

Vectores: `tests/vectors/c/decoder.json`, `tests/vectors/c/decoder_internals.json`
(fijan los resultados de este decodificador sobre escaneos concretos, no el
formato).

## 8. Historia { #8-history }

La página de la parte 2 es el formato de Twibright Optar, un programa en C
escrito por Karel Kulhavy en 2007 y mantenido desde 2012 en `colindean/optar`.
Su código fuente se conserva sin cambios en la carpeta `lega-c` de este
proyecto, tal como estaba en el commit `9c8379c25466bf142459a26b0f34521bdde2af12` de ese
repositorio. Los vectores de `tests/vectors/c` se registraron con ese programa;
los de `tests/vectors/py`, con este proyecto.

| Versión | Lo que añadió |
|---|---|
| programa en C | la página (parte 2); A4 o Letter, elegido al compilar |
| 0.1.0 | las mismas páginas, escritas y leídas por este proyecto |
| 0.2.0 | la etiqueta (parte 3) |
| 0.3.0 | el contenedor, los tamaños de punto y los diseños (partes 4 y 5), con relleno de ceros |
| 0.3.1 | el flujo de relleno (sección 4.7) |

Lo que el formato conserva del programa en C:

- el borde, las cruces, el orden de los píxeles de datos y el entrelazado;
- la tabla de Golay, construida a partir del dodecaedro, y los códigos de
  Hamming;
- la tira de la fuente, la línea del rótulo y sus tres peculiaridades (sección
  2.8);
- el límite de 9999 páginas, y el archivo vacío impreso como una página `1/0`;
- que una página no registra la longitud de su flujo;
- las cuadrículas de los dos diseños `standard` y los desplazamientos del de
  Letter. Las herramientas en C colocaban la página A4 en 19.22 y 17.44 pt, que
  no caen en puntos de impresora enteros; este proyecto la coloca en los
  desplazamientos de la sección 5.2.

El programa en C tiene un único formato de página compilado. Su decodificador
toma la cadena de formato como argumento, pero solo usa el último campo.

Queda una diferencia con el programa en C en el rótulo: el programa en C
recortaba la línea del rótulo por bytes, y este formato la recorta por
caracteres. Las dos formas dan la misma página salvo que la línea se recorte y
contenga caracteres fuera de ASCII antes del corte.

Comportamiento del decodificador heredado del programa en C que no forma parte
del formato (parte 7): las siete constantes de la sección 7.4, el doble uso de
una esquina en el tamaño del píxel, la búsqueda de esquinas que necesita una
página derecha más alta que ancha, y la aritmética de coma flotante de 32 bits
que fijan los vectores del decodificador.
