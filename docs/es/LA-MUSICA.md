# La música

Todo lo que suena aquí sale de ejecutar el motor de sonido del cartucho (`suena_un_cuadro`, 0x7A3D, y `pide_un_sonido`, 0x7BA2, que le reparte las voces; lo llama la interrupción en 0x4030) en un Z80 emulado, cuadro a cuadro y a 60 por segundo, igual que lo llama el juego. Lo que el motor escribe en el PSG pasa a sonido con un AY-3-8910 (`tools/musica.py`). Cada MP3 es la pieza entera hasta donde vuelve a empezar, más 8 segundos de la vuelta apagándose; las que no se repiten acaban donde acaba el motor.

## Cotejado con openMSX

Las escrituras al PSG se han comparado cuadro a cuadro con las de openMSX (C-BIOS MSX1 japonés). En todos los cuadros el PSG queda igual:

- el sonido del final (0x8F) entera, 170 cuadros, pedida a la fuerza y en la partida tal como el juego la pide.

El timbre no está cotejado: es el de un AY-3-8910 de manual, no una grabación del emulador. Las sondas están en `tools/omsx_psg.tcl` y `tools/coteja_psg.py`.

## Lo que no se publica

Es la única música que el listado pide con un `ld a` y que suena de verdad (el 0x94 del arranque es silencio y el 0x11 es un efecto). La tabla guarda además las pistas 0x88 a 0x90, y aquí no se publican porque el cotejo no cuadra: con la 0x8B pedida a la fuerza, openMSX y este motor dan lo mismo durante 229 cuadros y luego la duración de la primera nota es 232 cuadros en el emulador y 256 aquí. La causa no está resuelta. Lo más probable es que el juego deje en la RAM de las voces un valor, el paso de las notas (+10), que estas pistas no fijan y que aquí parte de cero, pero no se ha comprobado.

## Las músicas

**El sonido del final** (0x8F)

Lo pide `estado_por_la_tabla_5000`; dura 2,8 s.

<audio controls preload="none" src="../audio/musica_8F.mp3?v=30fd0f94"></audio>
