---
source_hash: 2249212b8920c7b2d504e467f61c20e86e4b2d9d
---

# Cómo se identifica una página { #how-a-page-identifies-itself }

El programa tiene que saber, para cada escaneo, a qué documento pertenece y qué
página es. Una página puede decirlo de dos maneras, según cómo se hizo la
impresión.

| Impresión | Se identifica por |
|---|---|
| Hecha con protección, o con cualquier tamaño de punto salvo el estándar | una cabecera en los datos de la página («páginas autoidentificables») |
| Impresión compatible de 0.2.0 o posterior | la etiqueta del rótulo de la parte inferior |
| De 0.1.0 o de la herramienta en C | solo el rótulo, que no tiene nada con qué contrastarlo |

Una etiqueta válida en el rótulo siempre prevalece: una página cuyo rótulo
tiene una etiqueta válida se lee como página de 0.2.0, contengan lo que
contengan sus datos.

## Páginas autoidentificables { #self-identifying-pages }

Las páginas de una impresión hecha con protección, o con cualquier tamaño de
punto salvo el estándar, llevan en sus datos los detalles del documento: a qué
impresión pertenecen, su número, el número de páginas, el tamaño del archivo y
su huella.

El rótulo impreso en la parte inferior es para las personas y no se usa para
identificar las páginas. En un PDF se imprime a un mismo tamaño sea cual sea el tamaño
de punto (el tamaño del rótulo de una página estándar), para que quepa la
línea entera. Entonces es demasiado pequeño para leerse en un escaneo de baja
resolución, y la ventana muestra «(sin nombre)» hasta que el archivo se
recupera y se conoce su propio nombre. Las páginas PNG y PGM tienen un píxel
por punto, así que su rótulo se dibuja con los puntos de la página y crece con
ellos.

El espacio que un documento así no usa se rellena con un patrón fijo que
parece datos, para que todas las páginas se impriman de forma uniforme. La
versión 0.3.0 lo rellenaba con ceros, que se imprimían como líneas blancas que
cruzaban las páginas. Ambos se leen, también con 0.3.0: ningún lector mira
el relleno.

La cabecera de una página no es fiable por sí sola: una sola página escaneada
podría afirmar que pertenece a cualquier documento. Solo la huella del archivo
recuperado hace que quede verificado.

## El rótulo { #the-label }

Cada página tiene un rótulo en la parte inferior: el formato de página, el
número de página y el número de páginas y, después, texto libre. En las
impresiones de 0.2.0 y anteriores, la aplicación lee este rótulo en el
escaneo.

- Un rótulo con etiqueta se acepta cuando se lee de forma verosímil, el
  control de la etiqueta coincide con el número de página y el número de
  páginas, y el tamaño de archivo de la etiqueta es compatible con ese número
  de páginas.
- Un rótulo sin etiqueta (impresiones hechas con 0.1.0 o con la herramienta
  en C) no tiene nada con qué contrastarlo, así que solo se acepta cuando se
  lee con claridad.
- Se rechaza un rótulo que parece una etiqueta con un carácter dañado.

Un escaneo rechazado aparece como «Ilegible» junto con el motivo, y puede
asignarlo a mano a una página.

## La etiqueta { #the-tag }

Desde la versión 0.2.0, `optar encode` y la aplicación imprimen una etiqueta
al principio del texto libre de cada página de una impresión compatible, con
la forma `[SIZE:FINGERPRINT:CC]`.

| Parte | Significado |
|---|---|
| `SIZE` | el tamaño del archivo en bytes |
| `FINGERPRINT` | los 8 primeros dígitos hexadecimales del SHA-256 del archivo |
| `CC` | un control de dos dígitos hexadecimales que depende del número de página y del número de páginas |

La etiqueta permite a la aplicación:

- mantener separadas las páginas de impresiones distintas;
- rechazar un rótulo con etiqueta cuyo tamaño no es compatible con el número
  de páginas;
- rechazar un escaneo cuyo rótulo se leyó mal, en lugar de colocarlo en una
  página equivocada (alrededor de 1 lectura errónea de cada 256 puede pasar
  aun así el control);
- recortar el archivo recuperado a su tamaño real, para que no tenga relleno
  de ceros;
- comparar el archivo recuperado con la huella, que es la verificación final
  de que el archivo es el original.

Para imprimir sin etiqueta, use `optar encode --no-tag`. Las páginas que se
identifican por sus datos no imprimen etiqueta.

Las definiciones exactas están en la
[especificación del formato](format.md): la parte 3 para la etiqueta y la
parte 4 para los documentos autoidentificables.
