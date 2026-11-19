---
source_hash: bceb221e5e7d1915ae0d3656ce9713f5c5f1cdeb
---

# Pasar un archivo al papel { #put-a-file-on-paper }

## En la aplicación { #in-the-application }

Abra la pestaña «Pasar al papel».

![La pestaña «Pasar al papel» con un archivo elegido](img/put-on-paper.png)

1. Elija un archivo o suéltelo sobre la pestaña.
2. Elija A4 o US Letter.
3. Elija el [tamaño de punto](#dot-size) y la [protección](#protection). La
   ventana empieza con puntos estándar y protección estándar.
4. Dé un nombre al archivo. La línea «Se imprime como:» muestra el texto que
   se imprimirá en cada página.
5. Lea la línea que hay debajo: muestra cuántas páginas necesita el archivo y,
   con protección, cuántas de esas páginas se pueden perder.
6. «Crear PDF…» guarda el PDF.

Si marca «Compatible con optar 0.2 y el optar original», se crea una impresión
que esos programas más antiguos pueden leer. Tiene puntos estándar y no tiene
protección.

Para la línea de comandos, véase [`optar encode`](command-line.md#encode).

## Impresión { #printing }

Imprima el PDF a tamaño real (100 %), no con «Ajustar a la página», en una
impresora láser de 600 dpi. Las impresoras de inyección de tinta no se han
probado.

Una impresión que sale más pequeña que el tamaño real tiene puntos más
pequeños, que son más difíciles de leer. Una impresión real midió alrededor del 95 %
del tamaño real.

## Tamaño de punto { #dot-size }

El tamaño de punto es lo grande que se imprime cada punto de datos. Los puntos
más grandes resisten un escaneo de resolución más baja, pero en una página
caben menos, así que contiene menos datos. Un punto de datos ocupa 3, 4, 5, 6
o 9 puntos de una impresora de 600 dpi.

La tabla da la resolución de escaneo que hay que usar (tres píxeles de escaneo
por punto de datos) y los bytes que contiene una página antes de añadir la
protección:

| Tamaño de punto | Opción | Puntos de impresora por punto de datos | Escanear a | Página A4 | Página Letter |
|---|---|---|---|---|---|
| Estándar | `standard` | 3 | 600 dpi | 199.773 | 192.591 |
| Mediano | `medium` | 4 | 450 dpi | 114.904 | 110.463 |
| Grande | `big` | 5 | 360 dpi | 73.027 | 69.463 |
| Muy grande | `large` | 6 | 300 dpi | 49.119 | 48.403 |
| Extragrande | `xlarge` | 9 | 200 dpi | 21.606 | 21.127 |

Elija el tamaño de punto según el escáner que leerá las páginas, quizá dentro
de muchos años. Si no lo sabe, los puntos más grandes son la opción más
segura.

## Protección { #protection }

La protección son datos adicionales, repartidos por todas las páginas del
documento, con los que el programa repara las zonas dañadas y reconstruye las
páginas perdidas. Las opciones son Ninguna, Estándar y Alta.

- Ocupa papel: la protección estándar añade alrededor de un 14 % más de
  páginas, y la alta, alrededor de un 34 %.
- Los datos adicionales se reparten de modo que una mancha, una esquina rota o
  una página ausente le cuesten a cada parte del archivo más o menos la misma
  pequeña cantidad. Esa pequeña cantidad es lo que repara la protección.
- Con protección, una parte de las páginas lleva los datos de protección, y
  cada página repite un breve registro que dice de qué documento y de qué
  página se trata. Por eso el archivo dispone de menos espacio del que muestra
  la tabla anterior.

### Perder una página entera { #losing-a-whole-page }

La ventana y `optar encode` prometen que se puede recuperar una página perdida
solo en documentos lo bastante largos, y entonces dicen «puede perder N
página(s) de T».

| Protección | Puede perder 1 página a partir de | Puede perder 2 páginas a partir de |
|---|---|---|
| Estándar | 12 páginas | 24 páginas |
| Alta | 6 páginas | 12 páginas |

Por debajo de eso, los daños dentro de las páginas se reparan, pero si se
pierde una página entera se pierde el archivo. La promesa es prudente a
propósito, y un documento puede recuperar más de lo que promete.

### El archivo más grande { #the-largest-file }

Se rechaza un archivo cuya impresión con protección ocuparía más de 256 MiB en
papel. La ventana dice entonces si el archivo cabría sin protección o con
puntos más pequeños.

## Qué programas pueden leer la impresión { #which-programs-can-read-the-printout }

| Impresión | La leen |
|---|---|
| Cualquier tamaño de punto salvo el estándar, o cualquier protección | optar 0.3 o posterior. No hay que configurar nada al leer. |
| Puntos estándar, sin protección, «Compatible» marcado | todas las versiones, y el programa original en C |

La aplicación 0.2.0 no puede leer en absoluto las páginas de puntos más
grandes. Con puntos estándar y protección, 0.2.0 y la herramienta en C
devuelven los datos envueltos en los detalles adicionales y la protección, no
el archivo.

Las razones están en la sección
[Cómo se identifica una página](identification.md).

!!! note "Los archivos de una impresión compatible se rellenan"
    Una impresión hecha para 0.2 y programas más antiguos no guarda la longitud
    del archivo en sus datos; solo la tiene la etiqueta del rótulo. El
    `optar decode` de la línea de comandos y la herramienta en C devuelven un
    archivo así rellenado con ceros hasta completar una página entera.
    Empaquete sus datos con tar si esto les afecta.
