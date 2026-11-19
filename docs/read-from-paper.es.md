---
source_hash: e79216aee6b95b8e8e6f807f3e335aa738ff2181
---

# Recuperar el archivo { #read-it-back }

## Escaneo { #scanning }

- Escanee en escala de grises (256 niveles) o en color. No escanee en blanco y
  negro.
- Desactive cualquier limpieza de «documento» o de texto. Convierte los puntos
  en negros o blancos antes de que el programa los vea.
- Use la resolución que corresponde al tamaño de punto: 600 dpi para puntos
  estándar, donde 1200 dpi es algo mejor. Las demás están en la
  [tabla de tamaños de punto](put-on-paper.md#dot-size).
- Guarde en PNG o TIFF. La aplicación también acepta BMP, PGM/PPM y JPEG. JPEG
  pierde calidad y es una mala elección. No guarde las páginas como un único
  PDF.
- Limpie el cristal del escáner y apriete bien la página: una tapa que no
  aprieta el papel deja zonas borrosas.

Un escaneo hecho con una resolución demasiado baja recibe una nota que indica
la resolución que hay que usar. Es solo un consejo: un escaneo de baja
resolución que se puede leer se usa igualmente, y uno que el lector normal no
puede leer pasa a un [segundo lector, más lento](slower-reader.md).

## En la aplicación { #in-the-application }

Abra la pestaña «Leer del papel» y añada los escaneos de las páginas
(«+ Añadir escaneos…», o suelte archivos o carpetas sobre la pestaña).

El programa averigua por sí mismo qué página es cada escaneo, de qué papel es
y en qué orientación está. Así que los escaneos se pueden añadir en cualquier
orden, al revés o girados de lado. También deduce el tamaño de punto y la
protección; no hay nada que configurar.

![Escaneos en lectura, cada uno con una barra de progreso y su paso](img/being-read.png)

La lista muestra una fila por página con su estado. Al seleccionar una fila se
muestra el escaneo con las zonas dañadas marcadas: con la rueda se acerca o se
aleja la vista, arrastrando se desplaza y con un doble clic la página se ajusta a la vista.

Cuando la barra inferior dice que el archivo está verificado, «Guardar
archivo…» lo escribe.

Desde la lista puede:

- quitar un escaneo;
- reemplazar el escaneo de una página, o usar un escaneo de repuesto de esa
  página en lugar del que está en uso;
- cambiar a otro documento, si los escaneos que añadió pertenecen a más de una
  impresión;
- asignar a mano a una página un escaneo que no se pudo identificar;
- componer un documento a mano, cuando no se puede identificar ningún escaneo:
  usted indica el papel y el número de páginas y, después, asigna cada escaneo
  a su página.

## Mientras se lee un escaneo { #while-a-scan-is-being-read }

Cada escaneo que añade aparece en «En lectura» hasta que se ha leído, con una
barra de progreso y el paso en el que está:

| Paso | Qué ocurre |
|---|---|
| En espera | El escaneo espera su turno. |
| Abriendo el archivo | Se carga la imagen. |
| Buscando la página | El programa busca el contorno de una página. |
| Identificando la página | Prueba cada papel, tamaño de punto y orientación hasta que uno encaja. |
| Leyendo los datos | Los puntos se leen y se corrigen. |
| Lector lento: muestreo y, después, «pasada 4 de 5» | Solo para un escaneo del que se encarga el [lector lento](slower-reader.md). |

La barra cuenta pasos, no segundos: puede detenerse en un paso y luego saltar,
pero nunca retrocede. «Quitar» detiene la lectura del escaneo. Una vez leído,
el escaneo pasa a ser su página, o aparece como ilegible.

## Estados de las páginas { #page-states }

| Estado | Significado | Qué hacer |
|---|---|---|
| Correcta | La página se leyó sin ningún error que corregir. | Nada. |
| Reparada · N | N bloques estaban dañados y la corrección de errores los reparó. Los datos están intactos. | Nada. |
| Dañada · N perdidos | N bloques no se pudieron reparar, así que el archivo guardado tiene datos erróneos en esa parte. | Vuelva a escanear la página en escala de grises con la resolución que corresponde a su tamaño de punto y reemplace el escaneo. |
| Leída por el lector lento | El escaneo tenía una resolución demasiado baja para el lector normal. Véase [Escaneos de resolución demasiado baja](slower-reader.md). | Compruebe que el documento queda verificado. |
| Ilegible | No se pudo identificar el escaneo: por ejemplo, no hay ninguna página de optar en la imagen o no se pudo leer el rótulo. | Vuelva a escanear la página o asigne el escaneo a mano a una página. |
| Ausente | No se ha añadido ningún escaneo de esta página. | Añada uno. En un documento con protección, las demás páginas pueden bastar todavía, y entonces la barra lo dice. |

Un escaneo hecho a menos de 400 dpi que no se puede leer lo dice, por ejemplo
«Escaneado a unos 200 dpi, una resolución demasiado baja para leerlo», junto
con la resolución que necesita cada tamaño de punto.

## La barra inferior { #the-bar-at-the-bottom }

La barra muestra el estado de todo el documento.

| La barra dice | Significado |
|---|---|
| Archivo recuperado y verificado · N bytes | Se leyeron todas las páginas y el archivo recuperado coincide con la huella del papel. |
| No coincide con la huella del papel | Se leyeron todas las páginas, pero el archivo no es el original, porque algunos datos se decodificaron mal. Vuelva a escanear las páginas, empezando por las marcadas como «Reparada». |
| Recuperable: falta la página 3, se puede reconstruir a partir de las demás | Un documento con protección: faltan páginas, pero las páginas leídas deberían bastar para reconstruirlas. |
| Recuperable: falta la página 3, reconstruida a partir de las demás · coincide con la huella | Esa reparación se ha hecho y comprobado. A continuación aparecen el tamaño y lo que hizo la reparación. |
| Procesando… 3 de 6 escaneos leídos | Todavía se están leyendo escaneos. Cuando el documento ya tiene un estado que mostrar, el recuento va detrás: «Archivo recuperado y verificado · N bytes · 3 de 6 escaneos leídos». |
| Comprobando la huella… | La comprobación se está haciendo en segundo plano. |
| Leídas las N páginas · no se puede verificar (sin etiqueta) | Las páginas proceden de un programa antiguo y no llevan huella. |
| 4 de 6 páginas correctas · 1 dañada · 1 ausente | En los demás casos, un recuento. |

En un documento con protección, la ventana muestra también cuántos bytes
reparó la protección y qué parte de su capacidad de reparación usó la peor
zona, por ejemplo «la peor zona usó el 57 % de su capacidad de reparación
(18 de 32): un margen moderado».
Si la reparación falla,
indica qué páginas hay que añadir o volver a escanear.

!!! info "Qué significa «verificado»"
    «Verificado» siempre significa que la huella del archivo recuperado
    coincidió con la del papel. Nunca significa solo que la reparación no
    informó de ningún fallo.

## Guardar { #saving }

«Guardar archivo…» pide confirmación cuando el archivo no está verificado, y
dice qué le pasa.

Un documento con protección que no se pudo reparar se puede guardar de todos
modos hasta donde se recuperó, tras una advertencia de que el archivo puede
contener partes erróneas. Esto solo es posible cuando se leyó al menos la
mitad de sus páginas: con menos, no se guarda nada.

## Impresiones de programas antiguos { #printouts-from-old-programs }

Las impresiones de optar 0.1.0 o de la herramienta en C no tienen etiqueta en
su rótulo. La aplicación las lee, pero:

- no puede saber si las páginas van juntas ni si el archivo está completo;
- no puede verificar el archivo;
- el archivo guardado se rellena con ceros hasta completar una página entera.

Guarde un archivo así solo después de leer la advertencia que muestra la
aplicación.
