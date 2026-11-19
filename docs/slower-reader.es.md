---
source_hash: e1aa7bf9091169288d65ca97a824f48d1c05c64e
---

# Escaneos de resolución demasiado baja: el lector lento { #scans-that-are-too-coarse-the-slower-reader }

Desde la versión 0.4.0, el programa tiene un segundo lector, más lento, para
escaneos hechos con una resolución demasiado baja para su tamaño de punto, por
ejemplo una página de puntos estándar escaneada a 300 dpi en lugar de 600.

Escanee a la resolución recomendada siempre que pueda. El lector lento
recupera algunos escaneos de baja resolución, no todos (véase
[Qué muestran las pruebas y qué no](evidence.md#the-slower-reader)).

## Cuándo actúa { #when-it-runs }

Actúa por sí solo, en dos casos:

- El lector normal no puede identificar un escaneo, pero encuentra en él el
  contorno de una página.
- Un escaneo de baja resolución (menos de 2,5 píxeles de escaneo por punto)
  solo le dio al lector normal un rótulo sin etiqueta y ninguna cabecera, y los
  datos de la página se leyeron mal (el 1 % o más de sus símbolos no se pudo
  corregir). En un escaneo así, el rótulo puede seguir siendo legible aunque
  los datos no lo sean.

Una página cuyos datos se leen bien es una página antigua sin cabecera, y se
deja como está. Si el lector lento no encuentra nada, se conserva la lectura
del rótulo.

## Cómo funciona { #how-it-works }

El lector lento amplía el escaneo. A partir de los puntos de los que el lector
normal está seguro, aprende cómo se difuminan los puntos vecinos unos sobre
otros en cada parte de la página. Después lee cada punto con ese conocimiento
y elige cada símbolo en conjunto.

## En la aplicación { #in-the-application }

![Dos páginas leídas por el lector lento, con los puntos corregidos marcados](img/slow-pages.png)

*Una página de prueba generada, pequeña y escaneada con una resolución muy
baja. Los puntos corregidos están marcados en la vista previa.*

- Mientras trabaja, la fila del escaneo muestra el paso y el progreso del
  lector lento. Al seleccionar la fila se indica que esto tarda alrededor de un
  minuto.
- Después, la fila dice que la página la leyó el lector lento y cuántos puntos
  corrigió, por ejemplo «Página 3 · Leída por el lector lento · 265.112 puntos
  corregidos». Un punto corregido es aquel cuya propia impresión no prevaleció
  al decidirse su símbolo.
- Los puntos corregidos están marcados en la vista previa del escaneo, y cada
  marca tiene el ancho de un punto. En los escaneos de baja resolución, a
  menudo son varios de cada cien puntos, así que, vista entera, la página
  muestra un tono tan denso como las correcciones. Al ampliar se ven los puntos
  sueltos.
- Una vez verificado el documento, la fila añade cuántos bytes de la página
  reparó la protección del documento («· 6.912 bytes reparados por la
  protección del documento»). Al seleccionar la página se muestran ambas
  cifras.

Una página así nunca se llama «Correcta» y se cuenta aparte en la barra
inferior. El lector lento da a cada símbolo su mejor estimación, así que no
puede decir qué no tiene reparación en la página.

## En la línea de comandos { #on-the-command-line }

`optar decode` también lo ejecuta por sí solo y lo indica en stderr para cada
escaneo con el que lo prueba. `--no-slow-reader` lo desactiva.

## Cuánto tarda { #how-long-it-takes }

Una página A4 tardó en total de 40 a 70 segundos en la máquina de desarrollo:
de 20 a 35 segundos hasta que el lector normal se rindió y, después, de 20 a
35 segundos para el lector lento.

Una imagen que no es en absoluto una página de optar, pero en la que se
encuentra el contorno de una página, tarda entre 20 y 35 segundos más de lo
que tardaba sin el lector lento.

## Límites { #limits }

- Identifica una página solo por la cabecera de sus datos. Las páginas
  antiguas al estilo de 0.2, que se identifican por la etiqueta de su rótulo,
  no están cubiertas.
- Una página cuya etiqueta aceptó el lector normal nunca pasa al lector lento.
- Se espera que la protección estándar no baste para una página de puntos
  estándar escaneada a unos 290 dpi. El único documento real que se recuperó
  así tenía protección alta y necesitó más reparación de la que puede dar la
  protección estándar.
- No hace que un archivo erróneo parezca correcto: como siempre, solo la
  huella hace que un archivo quede verificado.
