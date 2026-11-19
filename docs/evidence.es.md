---
source_hash: 34c3bf2795da00caec5ecf72aeb5391c9d6f4e57
---

# Qué se ha mostrado y qué no { #what-has-and-has-not-been-shown }

Esta sección dice en qué se basan las afirmaciones del proyecto. La mayor parte
procede de escaneos simulados, no de papel.

## Escaneos simulados { #simulated-scans }

Las pruebas automáticas leen imágenes generadas con desenfoque, ruido y
rotación. El desenfoque simulado se ajustó a tres escaneos reales a 300 dpi de
una página impresa, hechos con una impresora y un escáner con alimentador de
hojas.

- Con ese desenfoque, los puntos estándar no se decodificaron a 300 dpi con el
  lector normal.
- Los puntos medianos con protección estándar quedaron verificados a 300 dpi y
  a 200 dpi.
- Los puntos grandes, muy grandes y extragrandes quedaron verificados a
  200 dpi sin errores.
- Un documento de 12 páginas quedó verificado con una página retenida.

## El lector lento { #the-slower-reader }

El [lector lento](slower-reader.md) se ha mostrado con un documento real y uno
simulado.

**Real.** El documento del propietario, de seis páginas A4, puntos estándar,
protección alta, escaneado a unos 290 dpi cuando se recomiendan 600 dpi. El
lector normal no identificó ninguna de las páginas. Con el lector lento, el
archivo se recuperó y quedó verificado por su huella: 759.879 bytes, de los
cuales 41.495 bytes los reparó la protección del documento; el peor bloque usó
40 de su capacidad de reparación de 64. Es un documento, una impresora, un
escáner y una resolución. Los escaneos no forman parte del repositorio.

**Simulado** (`tests/unit/test_coarse_claim.py`). Un documento de dos páginas
del mismo tipo, escaneado a 290 y a 300 dpi con un desenfoque de 1,8 puntos de
impresora. A 290 dpi, el lector normal no identifica ninguna de las dos
páginas; a 300 dpi lee el rótulo de cada página, pero ninguna cabecera. En
ambos casos el archivo queda verificado con el lector lento. Con el
desenfoque predeterminado del simulador (1,0), el lector normal lee una página
así a 300 dpi por sí solo.

El simulador es más benévolo que el escáner del propietario: a 290 dpi, en la
simulación, el lector lento no reparó nada, mientras que el documento real
necesitó que se repararan 41.495 bytes.

La protección estándar tiene una capacidad de reparación de 32, por debajo de
los 40 que necesitó el peor bloque del documento real. Por eso se espera que un
documento con protección estándar escaneado así falle. Las páginas antiguas al
estilo de 0.2 no están cubiertas por el lector lento.

## Qué no se ha mostrado { #what-is-not-shown }

- Todavía no se ha leído ningún escaneo real de una página de puntos más
  grandes.
- La lectura de rótulos y la decodificación tienen pruebas automáticas solo
  con escaneos sintéticos, no con páginas reales impresas y escaneadas. Eso
  incluye todas las impresiones con puntos más grandes o con protección.
- Los escáneres con alimentador de hojas no se han probado, más allá de que el
  programa encontró la cuadrícula de puntos en tres escaneos reales.
- Tres escaneos reales a 300 dpi de una impresión midieron unos 286 dpi, lo que
  significa que esa impresión salió a alrededor del 95 % del tamaño real. Los
  puntos más pequeños cuestan más de leer, así que imprima a tamaño real
  (100 %).
- Las impresoras de inyección de tinta no se han probado.

## Las mismas páginas que el programa en C { #the-same-pages-as-the-c-program }

Las páginas del codificador en Python son idénticas byte a byte a la salida
del `optar` original en C para A4, Letter y los cinco modos de corrección de
errores. Las posiciones de las cruces y los bits muestreados del decodificador
en Python son idénticos bit a bit a los del `unoptar` en C con las imágenes de
prueba sintéticas. Ambas cosas se comprueban con salidas de las herramientas
en C que se registraron una vez y se conservan en `tests/vectors`.

Cada página de una impresión autoidentificable sigue siendo una página de
optar ordinaria: un `unoptar` en C compilado con el mismo tamaño de cuadrícula
lee sus puntos exactamente (registrado para puntos muy grandes en A4 y puntos
medianos en Letter). Lo que devuelve son los datos con los detalles
adicionales y la protección envolviendo el archivo, no el archivo.
