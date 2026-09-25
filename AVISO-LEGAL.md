# Aviso legal y atribucion

*(Also available [in English](LEGAL-NOTICE.md).)*

## De quien es cada cosa

**El juego no es nuestro.** *Circus Charlie* lo publico **Konami** para MSX en 1984; su
numero de catalogo es **RC-712** y son 16 KB. Todos los derechos sobre el juego
siguen siendo de sus titulares.

**Lo que si es nuestro** son las herramientas de este repositorio, los
comentarios del listado, el analisis y la documentacion. Eso se publica con la
licencia de `LICENSE`.

## Que hay en este repositorio

El fichero `src/circus.asm` es el desensamblado comentado del cartucho. Se publica
para la **preservacion, el estudio y la documentacion** de un titulo que es
parte de la historia del software del MSX.

La imagen del cartucho (`.rom`) **no** se distribuye aqui. Quien quiera volver a
montar el listado tiene que poner la suya, y el `Makefile` comprueba su sha256
antes de hacer nada.

Las imagenes que produce `tools/graficos.py` no son ilustraciones traidas de
fuera: se dibujan leyendo los propios bloques del cartucho, en las direcciones
que dice el listado. Son parte de la prueba de que la lectura del binario es
correcta: si estuviera mal, saldria ruido.

## En que se apoya

En nada de nadie. Todo lo que se afirma aqui sale de leer este binario o de
medirlo corriendo, y cada afirmacion lleva su evidencia al lado: la instruccion
que lee un dato, la tabla que cierra exactamente donde tiene que cerrar, o la
medida hecha en el emulador. Lo que no esta cerrado se dice que no lo esta.

Este cartucho no lleva la marca oculta de Konami: `tools/busca_marca_konami.py`
la rastrea en los 16.384 bytes y no la encuentra. El formato de esa marca lo
descubrio Manuel Pazos, y a el se le dan las gracias.

## Si eres uno de los autores

Si trabajaste en *Circus Charlie* o tienes derechos sobre el juego, y preferirias que este
material no estuviera publicado, **dilo y se retira, sin discusion**. La
intencion de este trabajo es justo la contraria de perjudicarte: es dejar
constancia de como se hizo.
