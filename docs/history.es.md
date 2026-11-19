---
source_hash: 3205775811b328fd30b9d40d49b0c5b503e8cced
---

# Historia { #history }

optar lo escribió en C Karel 'Clock' Kulhavy, de Twibright Labs, en 2007, como
los programas `optar`, `unoptar` y `pgm2ps`. Su página de inicio es
[ronja.twibright.com/optar](http://ronja.twibright.com/optar/). Colin Dean
mantuvo disponible el código fuente y lo mejoró de 2012 a 2018 en
[github.com/colindean/optar](https://github.com/colindean/optar).

Este proyecto partió de ese código fuente. Los programas originales en C se
conservan sin cambios en la carpeta `lega-c` del repositorio. Son historia:
nada en este proyecto los compila ni los ejecuta ya. El
[README](https://github.com/mezinster/optar#history-the-original-c-program)
conserva sus instrucciones originales.

## Versiones de este proyecto { #versions-of-this-project }

| Versión | Qué añadió |
|---|---|
| 0.1.0 | La orden `optar` en Python, que lee y escribe las mismas páginas que los programas en C. |
| 0.2.0 | La aplicación de escritorio, y la etiqueta del rótulo con el tamaño y la huella del archivo. |
| 0.3.0 | Puntos más grandes, protección y páginas que se identifican por sus datos. |
| 0.4.0 | El lector lento para escaneos de resolución demasiado baja. |
| 0.5.0 | Barras de progreso para los escaneos en lectura, y recuentos de lo que corrigió el lector lento. |

El propio formato, incluido lo que procede del programa en C, se describe en
la parte 8 de la [especificación del formato](format.md).

## Licencia { #licence }

GPL. © 2007 Karel 'Clock' Kulhavy, de Twibright Labs; mejoras © 2012-2018
Colin Dean. Véase `COPYING` en el repositorio.
