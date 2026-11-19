---
source_hash: fc438b9b7896988d42b22d54829293c774aa20c2
---

# Línea de comandos { #command-line }

El comando `optar` codifica un archivo en páginas y decodifica los escaneos para
obtenerlo de nuevo. No necesita compilador de C, ni libpng, ni ImageMagick.

    optar encode INPUT [-o BASE] [--paper a4|letter] [--to pdf|png|pgm] [--label TEXT] [--no-tag]
                 [--dots standard|medium|big|large|xlarge] [--protect none|standard|high]
                 [--compatible] [--format STRING]
    optar decode BASE [-o OUTPUT] [--paper a4|letter] [--format STRING] [--debug-images] [--force]
                 [--no-slow-reader]
    optar --version

## encode { #encode }

`encode` escribe `BASE.pdf` de forma predeterminada (`BASE` es `optar_out` si
no se indica otro), o las páginas `BASE_0001.png` (o `.pgm`),
`BASE_0002.png`, ... con `--to`.

| Si indica | Obtiene |
|---|---|
| ni `--dots` ni `--protect`, o `--compatible` | una impresión que leen 0.2.0 y la herramienta en C: puntos estándar, sin protección |
| solo `--dots X` | ese tamaño de punto con protección estándar |
| solo `--protect LEVEL` | puntos estándar con esa protección |
| `--protect none` | sin protección |

Cualquiera de las tres últimas crea páginas autoidentificables (páginas que
dicen por sí mismas a qué documento pertenecen y qué número tienen), que
necesitan optar 0.3 o posterior para leerse. Por ejemplo:

    optar encode photo.jpg -o photo --dots large --protect high

Los tamaños de punto y los niveles de protección se describen en
[Pasar un archivo al papel](put-on-paper.md#dot-size).

Una impresión compatible lleva una [etiqueta](identification.md#the-tag) en
cada página; añada `--no-tag` para omitirla.

`--paper` es A4 de forma predeterminada.

## decode { #decode }

`decode` lee `BASE_0001.png`, `BASE_0002.png`, ... y escribe los datos en
`-o OUTPUT`, o en stdout. Solo lee archivos con esos nombres.

Lo que hace depende de la impresión. Lo decide a partir de los tres primeros
escaneos: si ninguno de ellos se puede identificar como página
autoidentificable, trata el conjunto como una impresión de 0.2.0 o anterior.

### Páginas autoidentificables { #self-identifying-pages }

`decode` averigua a partir de los propios escaneos qué son.

- Acepta los escaneos en cualquier orden y en cualquier orientación.
- Un escaneo que no puede leer cuenta como página ausente.
- Un escaneo que el lector normal no puede identificar pasa primero al
  [lector lento](slower-reader.md), salvo que indique `--no-slow-reader`.
- Repara los datos, los recorta a su tamaño real y comprueba la huella.
- Escribe el archivo solo si la huella coincide, salvo que indique `--force`,
  que guarda lo que se recuperó aunque no haya superado la verificación.
  Incluso con `--force` no se guarda nada si se leyó menos de la mitad de las
  páginas.

### Impresiones de 0.2.0 o anteriores { #printouts-from-020-or-earlier }

- `--paper` debe ser el mismo que al codificar.
- La página debe estar derecha (vertical, con el rótulo abajo). Los escaneos
  apaisados no se admiten aquí, algo heredado del decodificador en C. La
  aplicación de escritorio acepta cualquier orientación en todas las
  impresiones.
- `decode` no recorta la salida al tamaño de la etiqueta ni comprueba la
  huella: la salida siempre se rellena con ceros hasta completar una página
  entera. La aplicación de escritorio hace ambas cosas. Empaquete sus datos con
  tar si esto les afecta.
- `--force` no cambia nada, y `decode` lo indica.

## Código de salida { #exit-status }

| Código | Significado |
|---|---|
| 0 | Éxito. Con páginas autoidentificables: el archivo quedó verificado. |
| 1 | Los datos se decodificaron pero no son corregibles, o la numeración de las páginas tiene un hueco, o (con páginas autoidentificables) el archivo no superó la verificación. |
| 2 | Un error de uso o de entrada. |

## El código corrector de errores { #the-error-correcting-code }

El predeterminado es el código de Golay 24/12. También se admiten códigos de
Hamming de orden 2 a 5, que se eligen con `--format` (el sexto campo de la
cadena de formato). La [especificación del formato](format.md) define la
cadena de formato.
