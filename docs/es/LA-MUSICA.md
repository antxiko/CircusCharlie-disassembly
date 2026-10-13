# La música

Todo lo que suena aquí sale de ejecutar el motor de sonido del cartucho (`suena_un_cuadro`, 0x7A3D, y `pide_un_sonido`, 0x7BA2, que le reparte las voces; lo llama la interrupción en 0x4030) en un Z80 emulado, cuadro a cuadro y a 60 por segundo, igual que lo llama el juego. Lo que el motor escribe en el PSG pasa a sonido con un AY-3-8910 (`tools/musica.py`). Cada MP3 es la pieza entera hasta donde vuelve a empezar, más 8 segundos de la vuelta apagándose; las que no se repiten acaban donde acaba el motor.

## Cotejado con openMSX

Las escrituras al PSG se han comparado cuadro a cuadro con las de openMSX (C-BIOS MSX1 japonés). En todos los cuadros el PSG queda igual:

- el sonido del final (0x8F) entero, 170 cuadros, pedida a la fuerza y en la partida tal como el juego la pide;
- la 0x89 entera, 1154 cuadros, y la 0x8B entera, 1538, con el paso 6 que les da el juego;
- los primeros 384 cuadros de la 0x8D, con el paso 4 (la pieza dura 3106 y vuelve al cuadro 33; el juego la vuelve a pedir a los 384).

El timbre no está cotejado: es el de un AY-3-8910 de manual, no una grabación del emulador. Las sondas están en `tools/omsx_psg.tcl` y `tools/coteja_psg.py`.

## El paso que llega en A'

Estas pistas no fijan la duración de sus notas: la duración sale de un «paso» que `pide_un_sonido` copia del registro A' (el `ex af,af'` que el juego hace justo antes de llamar). El juego pone 6 en las músicas 0x89 y 0x8B de arranque de fase, 4 en la 0x8D, y 3 o 5 en los avisos de que se acaba el tiempo (la misma partitura, a otra velocidad). Con el A' a cero la primera nota duraba 256 cuadros en vez de 232 y las pistas no cuadraban con openMSX; con el A' del juego, sí. Aquí sólo están las versiones de arranque de fase; los avisos de tiempo (paso 3 o 5) no se publican. Las pistas 0x88, 0x8A, 0x8C, 0x8E y 0x90 de la tabla no las pide ninguna rutina con un `ld a` y no se publican.

## Las músicas

**La música de arranque de la fase** (0x89)

Lo pide `L_60D8` (con el paso 6 en A') y, con el paso 3 o 5, `avisa_de_que_queda_poco`; dura 19,2 s y vuelve a empezar en el segundo 0,0.

<audio controls preload="none" src="../audio/musica_89.mp3?v=8050c4c4"></audio>

**La música de la fase** (0x8B)

Lo pide `pon_al_jugador_en_su_sitio` (con el paso 6 en A') y, con el paso 5, `avisa_de_que_queda_poco`; dura 25,6 s y vuelve a empezar en el segundo 0,0.

<audio controls preload="none" src="../audio/musica_8B.mp3?v=8acc900b"></audio>

**La música de otra fase** (0x8D)

Lo pide `L_6161` (con el paso 4 en A') y, con el paso 3, `avisa_de_que_queda_poco`; dura 51,8 s y vuelve a empezar en el segundo 0,6.

<audio controls preload="none" src="../audio/musica_8D.mp3?v=9bccf081"></audio>

**El sonido del final** (0x8F)

Lo pide `estado_por_la_tabla_5000`; dura 2,8 s.

<audio controls preload="none" src="../audio/musica_8F.mp3?v=30fd0f94"></audio>
