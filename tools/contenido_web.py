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
        ("La mitad derecha de la mesa no esta guardada",
         "<p>La pista se dibuja una sola vez, y la otra mitad sale de "
         "<b>reflejarla</b>. La rutina de <code>0x7060</code> copia 768 bytes "
         "de VRAM a VRAM pasando cada uno por <code>0x47A6</code>, que le da "
         "la vuelta a sus ocho bits con ocho <code>rr c / rla</code>. El "
         "bucle que la llama recupera el origen con un <code>pop</code> en "
         "cada vuelta y solo sube el destino, asi que el mismo trozo se "
         "refleja en los tres tercios de la pantalla.</p>"
         "<p>Se ve en la hoja de patrones: donde el primer tercio pone "
         "<b>KONAMI</b>, el reflejo pone <b>IMANOK</b>.</p>"),

        ("Cuarenta fotogramas que llevan detras el puntero a sus patrones",
         "<p>Los munecos no tienen una tabla de graficos. Cada fotograma es "
         "<code>[dy, dx, patron]</code> por sprite, un <code>0x81</code> si "
         "lleva menos de los que pide el bucle, y <b>pegado detras, el "
         "puntero a su propio bloque comprimido</b>. El descompresor de "
         "<code>0x5E9B</code> no recibe el bloque: lo saca de ahi.</p>"
         "<p>De ese puntero salen los 3.135 bytes de "
         "<code>0x73A7..0x7D25</code>, y encaja por dos caminos "
         "independientes: encadenando bloques desde <code>0x73A7</code> la "
         "cadena cae <b>exactamente</b> en <code>0x7D26</code> en cuarenta "
         "saltos, y los cuarenta punteros de los fotogramas son uno por uno "
         "esos cuarenta arranques. Veinte para el jugador de cerca y veinte "
         "para el del fondo.</p>"),

        ("El reglamento del tenis de mesa, en BCD",
         "<p>El tanteo se lleva en decimal codificado: <code>0x6760</code> "
         "suma con <code>add a,001h / daa</code>. Leyendolo asi, las reglas "
         "salen enteras y son las de verdad:</p>"
         "<ul><li>el set se gana a <b>21</b> (<code>cp 021h</code>)</li>"
         "<li>hay que <b>ganar por dos</b>, y si los dos llegan a 21 el "
         "marcador vuelve a cero</li>"
         "<li><b>deuce</b> al empate a 20 (<code>cp 020h</code>)</li>"
         "<li>el <b>saque cambia cada cinco puntos</b>: <code>0x683D</code> "
         "suma los dos tanteos, hace <code>daa</code> y mira si el digito de "
         "las unidades es 0 o 5</li>"
         "<li>y en el set decisivo se <b>cambia de campo a los 10</b></li></ul>"
         "<p>La comprobacion de los dos puntos de diferencia acepta "
         "<code>0x02</code> <b>y tambien 0x08</b>, y no es un error: la resta "
         "es binaria sobre BCD, asi que 21 menos 19 da <code>0x08</code> y "
         "son dos puntos igual.</p>"),

        ("Una tabla de seno para la pelota",
         "<p><code>0x6EAD</code> son 92 bytes que suben de 12 a 255, bajan, "
         "pasan por cero y vuelven a subir. Que es un seno esta medido: los "
         "31 valores del primer cuarto contra "
         "<code>255&middot;sin(i&middot;90/31)</code> se desvian <b>4,7 como "
         "mucho</b>, sobre un recorrido de 255.</p>"
         "<p>Y los dos sitios que la leen, <code>0x6E99</code> y "
         "<code>0x6EA3</code>, estan separados <b>31 posiciones</b>: un cuarto "
         "de onda. De una sola tabla salen el seno y el coseno.</p>"),

        ("El despacho va en dos niveles, y el segundo no gasta tabla",
         "<p>La escena la reparte el despachador de <code>0x4062</code> con "
         "una tabla <b>pegada detras del <code>call</code></b>: el "
         "<code>pop hl</code> recupera su propia direccion de retorno, que es "
         "donde empieza la tabla.</p>"
         "<p>Pero la SUBescena no gasta tabla: se elige bajando por una "
         "<b>cadena de <code>djnz</code></b>, cada uno de dos bytes, y el "
         "trozo que corre es aquel en que B llega a cero. Veinticinco "
         "escalones en cincuenta bytes.</p>"),

        ("Un interprete de rotulos con cuatro puertas",
         "<p>El mismo bucle sirve para las cuatro combinaciones de lo que "
         "puede variar: si lee del guion la direccion de destino o le llega "
         "ya puesta, y si la mascara deja pasar los bytes o escribe ceros.</p>"
         "<ul><li><code>0x4764</code> cabecera si, pinta</li>"
         "<li><code>0x476C</code> cabecera no, con todo puesto</li>"
         "<li><code>0x475C</code> cabecera no, pinta</li>"
         "<li><code>0x4760</code> cabecera si, <b>BORRA</b></li></ul>"
         "<p>La cuarta es la buena: con la mascara a cero, el mismo guion que "
         "escribio el rotulo lo borra dejando su geometria.</p>"),

        ("La perspectiva, con multiplicaciones y una division a mano",
         "<p>El Z80 no multiplica ni divide. <code>0x6BA1</code> convierte las "
         "tres coordenadas de la mesa en fila y columna de pantalla con dos "
         "rutinas propias -<code>0x6F65</code> multiplica sumando y "
         "desplazando ocho veces, <code>0x6F88</code> divide restando y "
         "desplazando dieciseis- y tres factores fijos: <code>0xD4</code> para "
         "la profundidad, <code>0xBF</code> para la anchura y <code>0x8E</code> "
         "para la fila.</p>"
         "<p>Y el tamano de la pelota no se calcula: sale de dos tablas de "
         "cinco patrones, elegidas por la altura contra cuatro escalones.</p>"),

        ("La marca oculta de Konami",
         "<p>Los ultimos quince bytes del cartucho son el titulo en katakana "
         "-<b>&#12467;&#12490;&#12511;&#12398;&#12500;&#12531;&#12509;&#12531;"
         "</b>, Konami no Ping Pong-, su longitud <code>0x0C</code> y el "
         "<code>0x31</code> de <b>RC-731</b>. Delante van 70 bytes de "
         "<code>0xFF</code>: lo que sobro del cartucho.</p>"
         "<p>Esa marca la descubrio <b>Manuel Pazos</b>, y de el es el "
         "hallazgo.</p>"),

        ("El mismo armazon que Road Fighter",
         "<p>No es parecido: es el mismo, pieza por pieza. El despachador con "
         "la tabla pegada detras, las dos sumas de 8 sobre 16 bits, el "
         "interprete de rotulos, el descompresor y su bucle de tercios.</p>"
         "<p>Y los <b>ocho bytes de los registros del VDP son identicos</b>, "
         "uno por uno: <code>02 E2 0E 7F 07 76 03 E4</code>. Dejan la VRAM al "
         "reves de lo acostumbrado -el COLOR abajo, en <code>0x0000</code>, y "
         "los PATRONES arriba, en <code>0x2000</code>- porque R3 y R4 no son "
         "direcciones sino base y mascara.</p>"),

        ("Dos escrituras que no llegan a ninguna parte",
         "<p><code>0x4013</code> escribe en <code>0x40EE</code> y "
         "<code>0x4052</code> en <code>0x40F8</code>. Las dos direcciones "
         "caen <b>dentro de la propia ROM</b>, que no admite escritura: los "
         "dos <code>ld</code> se ejecutan en cada partida y no cambian "
         "nada.</p>"),
    ],
    "en": [
        ("The right half of the table is not stored anywhere",
         "<p>The court is drawn once, and the other half comes from "
         "<b>mirroring it</b>. The routine at <code>0x7060</code> copies 768 "
         "bytes from VRAM to VRAM, passing each one through "
         "<code>0x47A6</code>, which reverses its eight bits with eight "
         "<code>rr c / rla</code> pairs. The loop that calls it restores the "
         "source with a <code>pop</code> on every pass and only advances the "
         "destination, so the same chunk is mirrored into all three thirds of "
         "the screen.</p>"
         "<p>You can see it in the pattern sheet: where the first third reads "
         "<b>KONAMI</b>, the mirror reads <b>IMANOK</b>.</p>"),

        ("Forty frames, each carrying the pointer to its own patterns",
         "<p>The players have no graphics table. Each frame is "
         "<code>[dy, dx, pattern]</code> per sprite, an <code>0x81</code> if "
         "it uses fewer than the loop asks for, and <b>right behind it, the "
         "pointer to its own compressed block</b>. The decompressor at "
         "<code>0x5E9B</code> is not handed the block: it fetches it from "
         "there.</p>"
         "<p>That pointer accounts for the 3,135 bytes of "
         "<code>0x73A7..0x7D25</code>, and it checks out two independent "
         "ways: chaining blocks from <code>0x73A7</code> lands "
         "<b>exactly</b> on <code>0x7D26</code> in forty steps, and the forty "
         "pointers held by the frames are, one by one, those forty starts. "
         "Twenty for the near player and twenty for the far one.</p>"),

        ("The whole of table tennis scoring, in BCD",
         "<p>The score is kept in binary-coded decimal: <code>0x6760</code> "
         "adds with <code>add a,001h / daa</code>. Read that way, the rules "
         "come out complete, and they are the real ones:</p>"
         "<ul><li>a game is won at <b>21</b> (<code>cp 021h</code>)</li>"
         "<li>you must <b>win by two</b>, and if both reach 21 the score "
         "resets</li>"
         "<li><b>deuce</b> at 20-all (<code>cp 020h</code>)</li>"
         "<li>the <b>service changes every five points</b>: "
         "<code>0x683D</code> adds both scores, runs <code>daa</code> and "
         "checks whether the units digit is 0 or 5</li>"
         "<li>and in the deciding game the players <b>change ends at "
         "10</b></li></ul>"
         "<p>The two-point-lead check accepts <code>0x02</code> <b>and also "
         "0x08</b>, and that is not a bug: the subtraction is binary over "
         "BCD, so 21 minus 19 gives <code>0x08</code> and is still two "
         "points.</p>"),

        ("A sine table for the ball",
         "<p><code>0x6EAD</code> holds 92 bytes that climb from 12 to 255, "
         "come back down, pass through zero and climb again. That it is a "
         "sine is measured, not assumed: the 31 values of the first quarter "
         "against <code>255&middot;sin(i&middot;90/31)</code> are off by "
         "<b>4.7 at most</b>, over a range of 255.</p>"
         "<p>And the two places that read it, <code>0x6E99</code> and "
         "<code>0x6EA3</code>, sit <b>31 entries apart</b>: a quarter of a "
         "wave. One table gives both sine and cosine.</p>"),

        ("Dispatch happens on two levels, and the second uses no table",
         "<p>The scene is dispatched by <code>0x4062</code> through a table "
         "<b>glued right behind the <code>call</code></b>: the "
         "<code>pop hl</code> retrieves its own return address, which is "
         "where the table starts.</p>"
         "<p>But the SUBscene uses no table at all: it is picked by walking "
         "down a <b>chain of <code>djnz</code></b>, two bytes each, and the "
         "block that runs is the one where B hits zero. Twenty-five steps in "
         "fifty bytes.</p>"),

        ("A label interpreter with four doors",
         "<p>One loop covers all four combinations of what can vary: whether "
         "it reads the destination address from the script or gets it "
         "ready-made, and whether the mask lets the bytes through or writes "
         "zeros.</p>"
         "<ul><li><code>0x4764</code> header yes, paints</li>"
         "<li><code>0x476C</code> header no, everything ready</li>"
         "<li><code>0x475C</code> header no, paints</li>"
         "<li><code>0x4760</code> header yes, <b>ERASES</b></li></ul>"
         "<p>The fourth is the clever one: with the mask at zero, the very "
         "script that wrote the label erases it, keeping its shape.</p>"),

        ("Perspective, with multiplication and a division done by hand",
         "<p>The Z80 can neither multiply nor divide. <code>0x6BA1</code> "
         "turns the three table coordinates into a screen row and column "
         "using two routines of its own -<code>0x6F65</code> multiplies by "
         "adding and shifting eight times, <code>0x6F88</code> divides by "
         "subtracting and shifting sixteen- and three fixed factors: "
         "<code>0xD4</code> for depth, <code>0xBF</code> for width and "
         "<code>0x8E</code> for the row.</p>"
         "<p>The ball's size is not computed: it comes from two tables of "
         "five patterns, picked by testing its height against four "
         "thresholds.</p>"),

        ("Konami's hidden mark",
         "<p>The last fifteen bytes of the cartridge are the title in katakana "
         "-<b>&#12467;&#12490;&#12511;&#12398;&#12500;&#12531;&#12509;&#12531;"
         "</b>, Konami no Ping Pong-, its length <code>0x0C</code> and the "
         "<code>0x31</code> of <b>RC-731</b>. Before them sit 70 bytes of "
         "<code>0xFF</code>: whatever was left over of the cartridge.</p>"
         "<p>That mark was discovered by <b>Manuel Pazos</b>, and the finding "
         "is his.</p>"),

        ("The same skeleton as Road Fighter",
         "<p>Not similar: the same, piece by piece. The dispatcher with the "
         "table glued behind it, the two 8-over-16-bit adds, the label "
         "interpreter, the decompressor and its thirds loop.</p>"
         "<p>And the <b>eight VDP register bytes are identical</b>, one by "
         "one: <code>02 E2 0E 7F 07 76 03 E4</code>. They lay out VRAM the "
         "other way round from the usual -COLOUR low, at <code>0x0000</code>, "
         "and PATTERNS high, at <code>0x2000</code>- because R3 and R4 are "
         "not addresses but a base and a mask.</p>"),

        ("Two writes that go nowhere",
         "<p><code>0x4013</code> writes to <code>0x40EE</code> and "
         "<code>0x4052</code> to <code>0x40F8</code>. Both addresses fall "
         "<b>inside the ROM itself</b>, which cannot be written: the two "
         "<code>ld</code>s run on every game and change nothing.</p>"),
    ],
}

GALERIA = [
    ("titulo.png",
     "La pantalla de titulo, montada paso a paso como la monta el cartucho. "
     "El rotulo lo escribe 0x4B93 columna a columna desde la derecha, y la "
     "\"O\" de PONG no es un tile: son dos sprites del mismo color en el "
     "mismo sitio. Cotejada contra la VRAM del emulador.",
     "The title screen, assembled step by step the way the cartridge does it. "
     "The logo is written by 0x4B93 one column at a time from the right, and "
     "the \"O\" in PONG is not a tile: it is two same-coloured sprites in the "
     "same place. Checked against the emulator's VRAM."),

    ("pista.png",
     "La mesa. Su mitad derecha no esta guardada en el cartucho: se dibuja "
     "reflejando la izquierda byte a byte. Cero bytes de diferencia contra la "
     "VRAM del emulador.",
     "The table. Its right half is not stored in the cartridge: it is drawn "
     "by mirroring the left one byte by byte. Zero bytes different from the "
     "emulator's VRAM."),

    ("nivel.png",
     "El menu de nivel, que va encima de la mesa ya montada. Los cinco "
     "valores -1, 3, 5, 7 y 9- salen de la tabla de 0x461F, y el cursor es el "
     "patron 0x88 puesto en la columna que ella dice.",
     "The level menu, drawn on top of the table once it is up. The five "
     "values -1, 3, 5, 7 and 9- come from the table at 0x461F, and the cursor "
     "is pattern 0x88 placed at the column it names."),

    ("tiles_pista_1.png",
     "La hoja de patrones del segundo tercio. Arriba, la fuente: 45 tiles "
     "desde el 0x10, que es el codigo del '0'. Abajo, la mesa y su reflejo: "
     "donde uno pone KONAMI, el otro pone IMANOK.",
     "The pattern sheet of the middle third. On top, the font: 45 tiles from "
     "0x10, which is the code for '0'. Below, the table and its mirror: where "
     "one reads KONAMI, the other reads IMANOK."),

    ("logotipo.png",
     "El logotipo de la casa, que 0x4A2F dibuja subiendo una fila por pasada. "
     "No es una imagen guardada: son tres rachas de patrones CONSECUTIVOS "
     "-tres desde 0x40, once desde 0x43 y doce desde 0x4E- mas doce ceros que "
     "borran el rastro de la pasada anterior. Cero bytes de diferencia contra "
     "la VRAM del emulador.",
     "The company logo, which 0x4A2F draws one row higher on each pass. It is "
     "not a stored image: it is three runs of CONSECUTIVE patterns -three "
     "from 0x40, eleven from 0x43 and twelve from 0x4E- plus twelve zeros "
     "that wipe the previous pass. Zero bytes different from the emulator's "
     "VRAM."),

    ("sprites.png",
     "La tabla de patrones de sprite tal como queda en la pantalla de titulo: "
     "las pelotas en sus cinco tamanos, la red y las palas. Los munecos no "
     "estan aqui: sus cuarenta fotogramas se descomprimen uno a uno, segun "
     "hacen falta.",
     "The sprite pattern table as it stands on the title screen: the balls at "
     "their five sizes, the net and the bats. The players are not here: their "
     "forty frames are decompressed one at a time, as needed."),
]
