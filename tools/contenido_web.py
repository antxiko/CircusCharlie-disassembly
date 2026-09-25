#!/usr/bin/env python3
"""El CONTENIDO de la portada: los hallazgos y los pies de la galeria.

Va aparte de make_web.py a proposito. make_web.py es el generador -la
plantilla, la maquetacion, el HTML- y no cambia de un juego al siguiente; esto
es lo unico que hay que reescribir entero en cada cartucho. Teniendolo separado
no hay que ir buscando los textos del juego anterior dentro del generador, que
es justo como se han colado los nombres equivocados otras veces.

Cada hallazgo es (titulo, html) y cada entrada de galeria
(fichero, pie en castellano, pie en ingles).

Todas las cifras de aqui estan medidas sobre este cartucho, con las
herramientas de tools/, y no copiadas de ningun otro proyecto.
"""

HALLAZGOS = {
    "es": [
        ("El juego entero vive en la interrupcion",
         "<p>INIT (<code>0x407B</code>) engancha H.KEYI con un "
         "<code>jp 0x402C</code>, pone a cero el kilobyte de RAM y se queda "
         "para siempre en el <code>jr $</code> de <code>0x40A9</code>. Todo "
         "lo demas pasa en el gancho, una vez por cuadro: el sonido, los "
         "mandos y la escena. El cerrojo de <code>0xE005</code> cuenta las "
         "interrupciones solapadas y atiende la que entro mientras tanto sin "
         "volver a la pila.</p>"),

        ("La pista, desde las tablas",
         "<p>Los personajes y los obstaculos no los pone el montaje: los pone "
         "el juego cuadro a cuadro. <code>tools/pista.py</code> reescribe ese "
         "cuadro desde las tablas del cartucho -moviles <code>0x549B</code>, "
         "poses <code>0x5116</code>, arranques <code>0x6161</code>- y contra "
         "43 volcados de openMSX da <b>0 bytes distintos</b>.</p>"),

        ("Cinco numeros, un byte",
         "<p><code>(0xE052)</code> dice que atraccion es, de 0 a 4, y el "
         "cartucho reparte por el cuatro tablas pegadas detras de sus "
         "<code>call</code>: el montaje (<code>0x5FEF</code>), el arranque "
         "(<code>0x60B6</code>), el cuadro (<code>0x4C93</code>) y la tabla "
         "de moviles (<code>0x549B</code>). Tres de ellas estaban rotuladas "
         "corridas uno en el listado; lo destapo la RAM medida al arrancar "
         "cada numero.</p>"),

        ("Un decorado que se repite cada 240 bytes",
         "<p><code>0x458F</code> lee por DE y escribe por HL, al reves de lo "
         "que parece. Por eso <code>0x7477</code> copia <code>0x2AC0</code> "
         "<b>sobre</b> <code>0x2BB0</code>, solapado, y el decorado del "
         "caballo se repite solo.</p>"),

        ("El parpadeo de 1P mira el reloj",
         "<p>El <code>ld hl,(0xE002)</code> trae las banderas en L y el "
         "<b>contador de cuadros en H</b>. El <code>bit 5,h</code> no mira el "
         "numero de jugadores: alterna la mascara entre pintar y borrar cada "
         "32 cuadros.</p>"),

        ("Cuatro sprites por linea",
         "<p>El VDP no pinta el quinto sprite que cruza una linea. En el "
         "trapecio son seis los que cruzan las lineas 48 a 52, y se come dos. "
         "Con ese tope el dibujo casa con la foto del emulador en 49.152 "
         "puntos de 49.152.</p>"),
    ],
    "en": [
        ("The whole game lives inside the interrupt",
         "<p>INIT (<code>0x407B</code>) hooks H.KEYI with a "
         "<code>jp 0x402C</code>, clears the one kilobyte of RAM and then sits "
         "forever on the <code>jr $</code> at <code>0x40A9</code>. Everything "
         "else happens in the hook, once per frame: sound, controls and the "
         "current scene. The lock at <code>0xE005</code> counts overlapping "
         "interrupts and serves the one that came in meanwhile without going "
         "back through the stack.</p>"),

        ("The ring, from the tables",
         "<p>The characters and obstacles are not placed by the scenery "
         "set-up: the game places them frame by frame. "
         "<code>tools/pista.py</code> rewrites that frame from the "
         "cartridge's tables -moving objects <code>0x549B</code>, poses "
         "<code>0x5116</code>, start-ups <code>0x6161</code>- and against 43 "
         "openMSX dumps it gives <b>0 bytes different</b>.</p>"),

        ("Five acts, one byte",
         "<p><code>(0xE052)</code> says which act it is, 0 to 4, and the "
         "cartridge dispatches on it through four tables stuck right behind "
         "their <code>call</code>s: set-up (<code>0x5FEF</code>), start "
         "(<code>0x60B6</code>), frame (<code>0x4C93</code>) and the moving "
         "objects table (<code>0x549B</code>). Three of them were labelled "
         "off by one in the listing; the RAM measured at the start of each "
         "act gave it away.</p>"),

        ("Scenery that repeats every 240 bytes",
         "<p><code>0x458F</code> reads through DE and writes through HL, the "
         "other way round from what it looks like. That is why "
         "<code>0x7477</code> copies <code>0x2AC0</code> <b>over</b> "
         "<code>0x2BB0</code>, overlapping, and the horse act's scenery "
         "repeats by itself.</p>"),

        ("The 1P blink watches the clock",
         "<p>The <code>ld hl,(0xE002)</code> brings the flags in L and the "
         "<b>frame counter in H</b>. The <code>bit 5,h</code> is not the "
         "number of players: it flips the mask between drawing and erasing "
         "every 32 frames.</p>"),

        ("Four sprites per line",
         "<p>The VDP does not draw the fifth sprite crossing a line. On the "
         "trapeze six of them cross lines 48 to 52, and two are dropped. With "
         "that limit the drawing matches the emulator's picture in 49,152 "
         "dots out of 49,152.</p>"),
    ],
}

GALERIA = [
    ("en-pista-0-trapecio.png",
     "El trapecio, con la cama elastica abajo. Dibujado desde las tablas, "
     "no una captura.",
     "The trapeze, with the trampoline below. Drawn from the tables, not a "
     "capture."),
    ("en-pista-1-leon.png",
     "El leon y el aro de fuego, que esta pintado con tiles del fondo.",
     "The lion and the ring of fire, which is drawn with background tiles."),
    ("en-pista-2-cuerda-floja.png",
     "La cuerda floja y los monos.",
     "The tightrope and the monkeys."),
    ("en-pista-3-bolas.png",
     "Las bolas.",
     "The balls."),
    ("en-pista-4-caballo.png",
     "El caballo.",
     "The horse."),
    ("pantalla-titulo.png",
     "La pantalla de titulo, montada desde la ROM y cotejada a cero bytes.",
     "The title screen, built from the ROM and checked down to zero bytes."),
    ("pantalla-presentacion.png",
     "La pantalla de la casa. Comparte decorado con la de titulo byte a "
     "byte; solo cambia la tabla de nombres.",
     "The company screen. It shares its scenery with the title screen byte "
     "for byte; only the name table changes."),
    ("sprites.png",
     "Los patrones de sprite, de 0x61BA y 0x5FCF. En la pantalla de titulo "
     "estan a cero: el cartucho no los sube hasta que empieza una fase.",
     "The sprite patterns, from 0x61BA and 0x5FCF. On the title screen they "
     "are all zero: the cartridge only uploads them when an act begins."),
]
