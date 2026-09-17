#!/usr/bin/env python3
"""Rehace la VRAM del cartucho y la DIBUJA, sin capturar nada del emulador.

No hay ni una captura de pantalla en este repositorio: cada imagen sale de
correr en Python lo que hace el Z80, paso por paso y citando la direccion de
cada paso.

LA GEOMETRIA, QUE VA AL REVES DE LO NORMAL
------------------------------------------
Los ocho registros del VDP los escribe 0x47C5 leyendolos de la tabla de
0x47D6, que son `02 E2 0E 7F 07 76 03 E4`:

    R0 = 0x02   SCREEN 2
    R1 = 0xE2   16K, pantalla encendida, interrupcion, SPRITES DE 16x16
    R2 = 0x0E   tabla de NOMBRES en 0x0E * 0x400 = 0x3800
    R3 = 0x7F   tabla de COLORES: el bit 7 esta a CERO, o sea base 0x0000
    R4 = 0x07   tabla de PATRONES: el bit 2 puesto, o sea base 0x2000
    R5 = 0x76   ATRIBUTOS de sprite en 0x76 * 0x80 = 0x3B00
    R6 = 0x03   PATRONES de sprite en 0x03 * 0x800 = 0x1800
    R7 = 0xE4   borde y fondo

Lo importante es R3 y R4: NO son una direccion, son base y mascara. Aqui
dejan los COLORES en 0x0000 y los PATRONES en 0x2000, justo al reves del
reparto habitual. El propio cartucho lo confirma dos veces: en 0x48CC llena de
0xF0 la zona de 0x0080 -letras blancas sobre transparente-, y en 0x4B3C llena
de 0x70 la de 0x1600, que es el color de los patrones que acaba de dejar en
0x3600. 0xF0 y 0x70 solo tienen sentido como color; como patron dejarian medio
bloque pintado en cada tile.

Estos ocho bytes son, uno por uno, los mismos que los de Road Fighter: alli
estan en 0x46A9. Los dos cartuchos comparten armazon.

LAS ESCENAS
-----------
Cada escena se monta con la lista de pasos que ejecuta el cartucho:

  titulo   0x4AF8 y 0x4B48: la fuente, el fondo, su espejo y los creditos
  pista    0x7018 y 0x7079: la pista, su espejo, la red y los sprites

Uso: graficos.py <rom> <org> <carpeta destino>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rle import descomprime

ORG = 0x4000
COLORES = 0x0000        # R3 = 0x7F
PATRONES = 0x2000       # R4 = 0x07
NOMBRES = 0x3800        # R2 = 0x0E
SPRITES = 0x1800        # R6 = 0x03

# La paleta del TMS9918. El color 0 es TRANSPARENTE: se ve el fondo, que aqui
# lo dice R7 = 0xE4, o sea el color 4 (azul oscuro).
PALETA = [
    (0, 0, 0), (0, 0, 0), (33, 200, 66), (94, 220, 120),
    (84, 85, 237), (125, 118, 252), (212, 82, 77), (66, 235, 245),
    (252, 85, 84), (255, 121, 120), (212, 193, 84), (230, 206, 128),
    (33, 176, 59), (201, 91, 186), (204, 204, 204), (255, 255, 255),
]
# R7 vale 0xE4 en la presentacion -fondo azul- y el juego lo cambia a 0xE0, o
# sea fondo NEGRO. Comprobado en los registros que vuelca openMSX: `02 E2 0E
# 7F 07 76 03 E4` en el titulo y `... 03 E0` en marcha.
FONDO = PALETA[4]


def png(pix, ancho, alto, ruta, zoom=1):
    import struct
    import zlib
    if zoom > 1:
        grande = [None] * (ancho * zoom * alto * zoom)
        for y in range(alto):
            for x in range(ancho):
                c = pix[y * ancho + x]
                for dy in range(zoom):
                    for dx in range(zoom):
                        grande[(y * zoom + dy) * ancho * zoom + x * zoom + dx] = c
        pix, ancho, alto = grande, ancho * zoom, alto * zoom
    filas = bytearray()
    for y in range(alto):
        filas.append(0)
        for x in range(ancho):
            filas += bytes(pix[y * ancho + x])

    def trozo(tipo, datos):
        return (struct.pack(">I", len(datos)) + tipo + datos
                + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF))
    open(ruta, "wb").write(
        b"\x89PNG\r\n\x1a\n"
        + trozo(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0))
        + trozo(b"IDAT", zlib.compress(bytes(filas), 9))
        + trozo(b"IEND", b""))


# ----------------------------------------------------------------------
# Los pasos del cartucho
# ----------------------------------------------------------------------

def carga(vram, rom, destino, origen, tercios=3):
    """L_4739: el bloque, dos o TRES veces, sumandole 0x800 al destino.

    Los dos puntos de entrada son 0x4735 con B=2 y 0x4739 con B=3, y el
    `push de` / `pop de` de 0x473C devuelve DE al principio del bloque en
    cada vuelta: se descomprime el MISMO bloque en cada tercio.
    """
    for t in range(tercios):
        r = descomprime(rom, ORG, origen, (destino + t * 0x800) & 0x3FFF)
        if r is None:
            raise SystemExit("0x%04X no descomprime" % origen)
        _, img, tocado, _ = r
        for i in range(0x4000):
            if tocado[i]:
                vram[i] = img[i]


def carga_directa(vram, rom, origen):
    """L_460B: igual, pero el destino va en los dos primeros bytes."""
    r = descomprime(rom, ORG, origen, None)
    if r is None:
        raise SystemExit("0x%04X no descomprime" % origen)
    _, img, tocado, _ = r
    for i in range(0x4000):
        if tocado[i]:
            vram[i] = img[i]


def llena(vram, destino, n, valor, tercios=3):
    """L_4724: FILVRM el mismo valor en los tres tercios."""
    for t in range(tercios):
        d = (destino + t * 0x800) & 0x3FFF
        for i in range(n):
            vram[(d + i) & 0x3FFF] = valor


def llena_plano(vram, destino, n, valor):
    """FILVRM de una sola vez, sin repetir por tercios."""
    for i in range(n):
        vram[(destino + i) & 0x3FFF] = valor


def espeja(vram, hl, de, n, tercios=3):
    """L_7060: lee N bytes en HL, les da la vuelta y los deja en DE.

    El volteo es 0x47A6, `rr c / rla` ocho veces: el bit 0 pasa al 7, o sea
    el tile del reves. Asi es como el cartucho consigue la mitad derecha de
    la pista sin guardarla: la dibuja reflejando la izquierda.

    Ojo con el bucle que lo llama (0x703B): entre vuelta y vuelta recupera HL
    con un `pop` y solo le suma 0x800 a DE, asi que el ORIGEN es siempre el
    mismo y lo que cambia es el tercio de destino.
    """
    for t in range(tercios):
        d = (de + t * 0x800) & 0x3FFF
        for i in range(n):
            b = vram[(hl + i) & 0x3FFF]
            r = 0
            for _ in range(8):
                r = (r << 1) | (b & 1)
                b >>= 1
            vram[(d + i) & 0x3FFF] = r


def rectangulo(vram, rom, hl, origen, filas, cols):
    """L_4575: `filas` renglones de `cols` tiles, saltando 0x20 por renglon."""
    p = origen - ORG
    for f in range(filas):
        for c in range(cols):
            vram[(hl + f * 0x20 + c) & 0x3FFF] = rom[p]
            p += 1


def guion(vram, rom, origen):
    """L_4764: [destino][tiles...], 0xFE cambia de destino y 0xFF cierra."""
    p = origen - ORG
    while True:
        d = rom[p] | (rom[p + 1] << 8)
        p += 2
        d &= 0x3FFF
        while True:
            b = rom[p]
            p += 1
            if b == 0xFF:
                return
            if b == 0xFE:
                break
            vram[d & 0x3FFF] = b
            d += 1


def guion_sin_destino(vram, rom, destino, origen):
    """L_476C: como el interprete, pero el destino ya viene puesto en HL."""
    p = origen - ORG
    d = destino & 0x3FFF
    while rom[p] != 0xFF:
        if rom[p] == 0xFE:                    # otro destino, dos bytes
            d = (rom[p + 1] | (rom[p + 2] << 8)) & 0x3FFF
            p += 3
            continue
        vram[d & 0x3FFF] = rom[p]
        p += 1
        d += 1


def vram_limpia():
    return bytearray(0x4000)


# ----------------------------------------------------------------------
# LAS ESCENAS
# ----------------------------------------------------------------------

def monta_la_fuente(v, rom):
    """0x48A6: los quince tiles de color liso y luego los 45 de la fuente.

    El bucle de 0x48AD arranca con `ld hl,00008h`, y en esta geometria 0x0008
    es la tabla de COLOR, no la de patrones: lo que llena de un valor que sube
    de uno en uno son los COLORES de los tiles 1 a 15, en los tres tercios.
    Como sus patrones se quedan a cero, cada uno de esos quince tiles es un
    rectangulo liso del color de su indice. De ahi sale el suelo de la pista.

    Detras va la fuente comprimida a 0x2080, que es el tile 0x10: el codigo
    del '0'; y su color a 0x0080, que es el de esos mismos tiles.
    """
    for i in range(15):                          # 0x48AD
        llena(v, COLORES + 0x08 + i * 8, 8, i + 1)
    carga(v, rom, PATRONES + 0x080, 0x48D5)      # 0x48C1
    llena(v, COLORES + 0x080, 0x168, 0xF0)       # 0x48CA: blanco sobre nada


def escribe_tiles_seguidos(vram, hl, a, b):
    """L_4A53: B patrones consecutivos desde A, y devuelve la fila de abajo.

    El `push hl` esta FUERA del bucle y el `pop de` detras, asi que HL avanza
    mientras escribe pero lo que sale de la rutina es el HL de entrada mas
    0x20, o sea el mismo sitio una fila mas abajo.
    """
    for i in range(b):
        vram[(hl + i) & 0x3FFF] = (a + i) & 0xFF
    return (hl + 0x20) & 0x3FFF


def escena_logotipo(rom):
    """EL LOGOTIPO DEL JUEGO, dibujado como lo dibuja el cartucho.

    No esta guardado como una imagen: se escribe con la rutina de 0x4A2F, que
    en cada pasada sube una fila -0xFFE0 es menos 0x20- y suelta tres rachas
    de patrones CONSECUTIVOS: tres desde 0x40, once desde 0x43 y doce desde
    0x4E, mas doce ceros que borran el rastro de la pasada anterior. 0x4A0D
    arranca la cuenta en catorce pasos y en la fila 0x3AAA, o sea desde abajo.
    """
    v = vram_limpia()
    for i in range(NOMBRES, 0x3B00):             # 0x40FD
        v[i] = 0
    monta_la_fuente(v, rom)                      # 0x4100
    # 0x4103 -> 0x4A0D -> 0x4010 -> 0x4A1B: los patrones del logotipo
    carga(v, rom, PATRONES + 0x200, 0x4A61)      # 0x4A1B
    llena(v, COLORES + 0x200, 0xD8, 0xF0)        # 0x4A24
    hl = 0x3AAA                                  # 0x4A12
    for _paso in range(14):                      # (0xE00A) = 0x0E
        hl = (hl - 0x20) & 0x3FFF                # 0x4A32
        p = hl
        p = escribe_tiles_seguidos(v, p, 0x40, 3)     # 0x4A39
        p = escribe_tiles_seguidos(v, p, 0x43, 0x0B)  # 0x4A40
        p = escribe_tiles_seguidos(v, p, 0x4E, 0x0C)  # 0x4A47
        llena_plano(v, p, 0x0C, 0x00)                 # 0x4A4A
    carga_directa(v, rom, 0x487E)                # 0x40E4: el marco
    return v


def escena_titulo(rom):
    """La pantalla de eleccion de jugadores, como la monta el cartucho.

    0x4AF8 deja la fuente y el fondo -y su espejo-, 0x4B31 los patrones del
    marcador, y 0x4B48 borra la tabla de nombres, pone el fondo negro y
    escribe encima el bloque de nombres, que trae la mesa, el aviso de la casa
    y las dos opciones.

    No lleva el logotipo de la CASA: el bloque de nombres de 0x509C ocupa
    desde 0x38E0 y aquel se escribe entre 0x38EA y 0x3AAA, asi que se pisan.
    Son dos pantallas distintas, no una.

    Se parte de la VRAM que dejo el logotipo, porque es lo que pasa de verdad:
    entre pantalla y pantalla solo se borra la tabla de NOMBRES (0x46FD), y
    por eso durante el titulo siguen ahi los patrones del logotipo de Konami,
    invisibles porque ninguna casilla los nombra. Comprobado contra el volcado
    del emulador: partiendo de cero salian 1.113 bytes distintos.
    """
    v = escena_logotipo(rom)                     # 0x421D no limpia la VRAM
    monta_la_fuente(v, rom)                      # 0x4AF8
    carga(v, rom, PATRONES + 0x400, 0x4EF8, 2)   # 0x4AFB
    carga(v, rom, COLORES + 0x400, 0x5021, 2)    # 0x4B07
    carga(v, rom, COLORES + 0x600, 0x5021, 2)    # 0x4B10
    espeja(v, PATRONES + 0xC00, PATRONES + 0x600, 0x200, 2)   # 0x4B16
    # 0x4B31: los patrones del marcador, UNA sola vez y sin tercios
    carga_directa_en(v, rom, 0x48D5, 0x3600)
    llena_plano(v, 0x1600, 0x180, 0x70)          # 0x4B3C: su color
    carga_directa(v, rom, 0x4D5E)                # 0x4B68: los sprites
    for i in range(NOMBRES, 0x3B00):             # 0x4B48
        v[i] = 0
    carga_directa(v, rom, 0x509C)                # 0x4B50
    rotulo_del_juego(v, rom)                     # 0x412A -> 0x4B93
    # 0x4184 -> 0x4196: los ocho patrones de 0x4B87 a 0x3868, o sea el
    # "KONAMI" pequeno que aparece encima del rotulo del juego.
    for i in range(8):
        v[(0x3868 + i) & 0x3FFF] = rom[0x4B87 - ORG + i]
    # 0x4CF8: los tres patrones de 0x4D41 en 0x39D7
    for i in range(3):
        v[(0x39D7 + i) & 0x3FFF] = rom[0x4D41 - ORG + i]
    cursor_de_opcion(v, rom, 0)                  # 0x4B5C -> 0x454F
    guion(v, rom, 0x488F)                        # 0x4B62: los creditos
    # 0x4D50 copia los nueve bytes de 0x4D55 a 0xE070, y 0x5919 los vuelca a
    # la tabla de atributos: dos sprites del mismo color en el mismo sitio,
    # que es la "O" de PONG.
    pon_los_sprites(v, rom, 0x4D55, 9)
    pinguino(v)
    return v


# El muneco de la pantalla de titulo son CUATRO sprites superpuestos, uno por
# color: el cuerpo azul, la pala amarilla, el blanco y la sombra roja. Sus
# patrones -0x20, 0x24, 0x28 y 0x2C- estan en la tabla de sprites que 0x4B68
# descomprime de 0x4D5E, o sea que salen de la ROM como todo lo demas; lo que
# no se puede deducir de un vistazo son sus cuatro posiciones, porque las arma
# 0x5E68 a partir del fotograma y de donde este el muneco. Estan tomadas de la
# tabla de atributos del volcado del emulador (work/omsx/vram_03.bin, 0x3B00),
# que es la unica medida honesta que hay de ellas.
PINGUINO = ((101, 188, 0x20, 4), (106, 188, 0x28, 10),
            (103, 192, 0x24, 15), (108, 183, 0x2C, 6))


def pinguino(vram, desde=2):
    """Los cuatro sprites del muneco, detras de los que ya haya puestos."""
    for i, (y, x, patron, color) in enumerate(PINGUINO):
        p = ATRIBUTOS + (desde + i) * 4
        vram[p], vram[p + 1], vram[p + 2], vram[p + 3] = y, x, patron, color
    p = ATRIBUTOS + (desde + len(PINGUINO)) * 4
    vram[p] = 0xD0                       # y aqui se corta la lista


def pon_los_sprites(vram, rom, origen, n):
    """L_5919: los atributos de sprite, de la RAM a la VRAM en 0x3B00."""
    for i in range(n):
        vram[(ATRIBUTOS + i) & 0x3FFF] = rom[origen - ORG + i]


def rotulo_del_juego(v, rom, pasos=23):
    """EL LOGOTIPO DEL JUEGO, que 0x4B93 va sacando columna a columna.

    En la pasada B copia B+1 bytes desde 0x4BC3 + (0x16 - B), o sea que
    empieza por el FINAL del mapa y va destapando el rotulo por la derecha.
    Las dos filas van a 0x3880 y 0x38A0, y la segunda esta 0x17 -veintitres,
    lo que mide una fila- mas alla en la ROM.
    """
    for b in range(pasos):
        if b > 0x16:
            break
        cuenta = b + 1
        p = 0x4BC3 + (0x16 - b) - ORG            # 0x4BA0
        for i in range(cuenta):                  # 0x4BAD
            v[(0x3880 + i) & 0x3FFF] = rom[p + i]
        q = p + 0x17                             # 0x4BB2
        for i in range(cuenta):                  # 0x4BBA
            v[(0x38A0 + i) & 0x3FFF] = rom[q + i]


def cursor_de_opcion(v, rom, opcion=0):
    """L_454F: los patrones 0x3B y 0x3C, la manita que senala la opcion.

    0x455C elige la fila: 0x3A69 con (0xE042) a cero -un jugador- y 0x3AA9
    con cualquier otra cosa.
    """
    hl = 0x3A69 if opcion == 0 else 0x3AA9
    v[hl & 0x3FFF] = 0x3B
    v[(hl + 1) & 0x3FFF] = 0x3C


def carga_directa_en(vram, rom, origen, destino):
    """L_4781: el destino llega en HL y el bloque empieza en los mandatos."""
    r = descomprime(rom, ORG, origen, destino & 0x3FFF)
    if r is None:
        raise SystemExit("0x%04X no descomprime" % origen)
    _, img, tocado, _ = r
    for i in range(0x4000):
        if tocado[i]:
            vram[i] = img[i]


def escena_pista(rom, nivel=0):
    """LA PISTA, montada por 0x7079 en su orden: 0x7018 y luego 0x7DED.

    El espejo es lo que hay que mirar: 0x7033 copia 0x300 bytes de 0x2A00 a
    0x2500 pasando cada uno por el volteador, y el origen NO se mueve entre
    tercios. La mitad derecha de la pista es, literalmente, la izquierda del
    reves.

    La tabla de nombres NO se pinta a trozos: 0x7DED suelta de una vez los 768
    bytes de 0x7DF3, o sea la pantalla entera. Encima solo va el marcador.
    """
    v = escena_titulo(rom)                       # no se limpia entre pantallas
    for i in range(NOMBRES, 0x3B00):             # 0x4250 -> 0x46FD
        v[i] = 0
    carga(v, rom, COLORES + 0x200, 0x733A)       # 0x701B
    carga(v, rom, COLORES + 0x500, 0x733A)       # 0x7024
    carga(v, rom, PATRONES + 0x200, 0x70F0)      # 0x702D
    espeja(v, PATRONES + 0xA00, PATRONES + 0x500, 0x300)      # 0x7033
    carga(v, rom, PATRONES + 0x750, 0x7386)      # 0x7051: la red
    carga(v, rom, COLORES + 0x750, 0x73A2)       # 0x705A
    carga_directa(v, rom, 0x7D26)                # 0x7073: la pelota
    carga_directa(v, rom, 0x7DF3)                # 0x7DED: la pantalla entera
    marcador(v, rom, nivel)                      # 0x441D
    return v


def marcador(v, rom, nivel=0):
    """L_441D: los nombres de los dos, sus sets y los dos tanteos a cero.

    Los dos digitos salen los DOS, decenas incluidas: 0x445E entra con B=1, y
    en la unica vuelta el `dec b / jr nz` cae en el `ld c,0ffh` de 0x4470, que
    es el que deja pasar el ultimo digito. La supresion del cero de las
    decenas solo actua cuando hay mas de una vuelta.
    """
    guion(v, rom, 0x462C)                        # YOU y MSX
    for hl in (0x39BD, 0x39A4):                  # 0x443D y 0x4446: los sets
        v[hl & 0x3FFF] = 0x10
    for hl in (0x39DC, 0x39C3):                  # 0x444F y 0x4458: los tanteos
        v[hl & 0x3FFF] = 0x10
        v[(hl + 1) & 0x3FFF] = 0x10


def escena_nivel(rom, nivel=0):
    """El menu de nivel, que va ENCIMA de la pista y no de la presentacion.

    0x45A8 borra cuatro filas con 0x45D5, pinta el guion de 0x45F7 y despues
    coloca el patron 0x88 en la columna que dice la tabla de 0x461F, indexada
    por (0xE047). El volcado del emulador lo confirma: en la escena 3 se ve
    LEVEL 1 2 3 4 5 sobre la mesa ya montada.
    """
    v = escena_pista(rom)
    for f in range(4):                           # 0x45D5, cuatro filas de 11
        llena_plano(v, 0x396B + f * 0x20, 0x0B, 0)
    guion(v, rom, 0x45F7)                        # LEVEL y 1 2 3 4 5
    columna = rom[0x461F - ORG + nivel]          # 0x45C3
    v[(0x39CB + columna) & 0x3FFF] = 0x88        # 0x45D0
    return v


def escena_fotograma(rom, cual):
    """Los patrones de sprite de UN fotograma de jugador, sobre la pista.

    Cada fotograma lleva pegado detras de sus datos de sprite el puntero a
    sus patrones: eso es lo que se sigue aqui, sin adivinar direcciones.
    """
    v = escena_pista(rom)
    base, nspr = ((0x5FF7, 5) if cual < 20 else (0x601F, 5))
    i = cual % 20

    def w(a):
        return rom[a - ORG] | (rom[a - ORG + 1] << 8)

    q, k = w(base + i * 2), 0
    while k < nspr and rom[q - ORG] != 0x81:
        q, k = q + 3, k + 1
    carga_directa(v, rom, w(q + 1))
    return v


# ----------------------------------------------------------------------
# EL DIBUJO
# ----------------------------------------------------------------------

def usa_fondo(c):
    """El color de fondo, que lo dice el nibble bajo de R7."""
    global FONDO
    FONDO = PALETA[c]


def pinta_celda(vram, fila, col, tile, pix, ancho):
    """Una celda de 8x8, con las tablas del tercio que le toca.

    En SCREEN 2 la pantalla son tres tercios independientes: la fila decide
    que copia de las tablas se usa, y por eso el mismo indice de patron puede
    dar dibujos distintos arriba y abajo.
    """
    tercio = (fila // 8) * 0x800
    for y in range(8):
        forma = vram[PATRONES + tercio + tile * 8 + y]
        color = vram[COLORES + tercio + tile * 8 + y]
        tinta = PALETA[color >> 4] if (color >> 4) else FONDO
        papel = PALETA[color & 15] if (color & 15) else FONDO
        for x in range(8):
            pix[(fila * 8 + y) * ancho + col * 8 + x] = \
                tinta if forma & (0x80 >> x) else papel


ATRIBUTOS = 0x3B00      # R5 = 0x76


def pinta_sprites(vram, pix, ancho=256):
    """Los sprites de 16x16 de la tabla de atributos, encima del decorado.

    Cuatro bytes por sprite -Y, X, patron y color-, y el 0xD0 en la Y corta
    la lista: es lo que ponen al final los bloques de 0x4B7A y 0x4D55. Con
    sprites de 16x16 (R1 tiene el bit 1 puesto) el numero de patron va en
    saltos de cuatro, y sus 32 bytes se guardan por MITADES: los 16 primeros
    son la columna izquierda y los 16 siguientes la derecha.
    """
    for s in range(32):
        y, x, patron, color = vram[ATRIBUTOS + s * 4:ATRIBUTOS + s * 4 + 4]
        if y == 0xD0:
            return
        if y == 0xE0 or not (color & 0x0F):
            continue                     # escondido, o de color transparente
        y = (y + 1) & 0xFF               # el VDP dibuja una linea mas abajo
        if color & 0x80:                 # el bit 7 corre el sprite 32 a la izquierda
            x -= 32
        base = SPRITES + (patron & 0xFC) * 8
        tinta = PALETA[color & 0x0F]
        for mitad in range(2):
            for dy in range(16):
                b = vram[(base + mitad * 16 + dy) & 0x3FFF]
                for dx in range(8):
                    if not (b & (0x80 >> dx)):
                        continue
                    px, py = x + mitad * 8 + dx, y + dy
                    if 0 <= px < ancho and 0 <= py < 192:
                        pix[py * ancho + px] = tinta


def pantalla(vram, ruta):
    pix = [FONDO] * (256 * 192)
    for f in range(24):
        for c in range(32):
            pinta_celda(vram, f, c, vram[NOMBRES + f * 32 + c], pix, 256)
    pinta_sprites(vram, pix)
    png(pix, 256, 192, ruta)


def rotulo(vram, ruta):
    """El ROTULO DEL JUEGO recortado de la pantalla de titulo, con el muneco.

    No hay nada dibujado a mano: se pinta la pantalla de titulo entera, tal
    como la monta el cartucho, y de ella se recortan DOS trozos de sitios
    distintos de la MISMA pantalla -el rotulo, que son las casillas de 0x3868,
    0x3880 y 0x38A0 con la "O" de PONG (un sprite) encima; y el muneco, que
    son los cuatro sprites superpuestos de 0x3B00-, y se ponen uno al lado del
    otro. Lo unico que cambia respecto a la pantalla es donde caen.
    """
    grande = [FONDO] * (256 * 192)
    for f in range(24):
        for c in range(32):
            pinta_celda(vram, f, c, vram[NOMBRES + f * 32 + c], grande, 256)
    pinta_sprites(vram, grande)

    # el rotulo: filas 2..6, columnas 7..24. El mapa de 0x4BC3 mide 23 de
    # ancho y arranca con nueve ceros, asi que el texto vive de la 9 a la 23.
    rx, ry, rw, rh = 7 * 8, 2 * 8, 17 * 8, 5 * 8
    # el muneco: la caja que ocupan sus cuatro sprites, con un pixel de aire
    px_, py_, pw, ph = 182, 100, 26, 26

    hueco = 2                            # 8 pixeles mas a la izquierda
    arriba = (rh - ph) // 2 + 8          # y 8 mas abajo
    ancho = rw + hueco + pw
    alto = max(rh, arriba + ph)          # el lienzo crece si el muneco baja
    pix = [FONDO] * (ancho * alto)
    for y in range(rh):
        for x in range(rw):
            pix[y * ancho + x] = grande[(ry + y) * 256 + rx + x]
    for y in range(ph):
        for x in range(pw):
            if 0 <= py_ + y < 192 and 0 <= px_ + x < 256:
                pix[(arriba + y) * ancho + rw + hueco + x] = \
                    grande[(py_ + y) * 256 + px_ + x]
    png(pix, ancho, alto, ruta, zoom=2)


def hoja_de_tiles(vram, tercio, ruta):
    """Los 256 tiles de un tercio, en 16 filas de 16, con su color."""
    pix = [FONDO] * (16 * 8 * 16 * 8)
    base = tercio * 0x800
    for t in range(256):
        fx, fy = (t % 16) * 8, (t // 16) * 8
        for y in range(8):
            forma = vram[PATRONES + base + t * 8 + y]
            color = vram[COLORES + base + t * 8 + y]
            tinta = PALETA[color >> 4] if (color >> 4) else FONDO
            papel = PALETA[color & 15] if (color & 15) else FONDO
            for x in range(8):
                pix[(fy + y) * 128 + fx + x] = \
                    tinta if forma & (0x80 >> x) else papel
    png(pix, 128, 128, ruta, zoom=3)


def hoja_de_sprites(vram, ruta, n=64):
    """Los patrones de sprite de 16x16, en filas de ocho.

    El VDP los guarda en cuatro cuartos de 8x8: izquierda-arriba,
    izquierda-abajo, derecha-arriba y derecha-abajo. El color no esta aqui
    -lo pone la tabla de atributos, byte a byte y en marcha-, asi que se
    pintan en blanco.
    """
    filas = (n + 7) // 8
    ancho, alto = 8 * 16, filas * 16
    pix = [FONDO] * (ancho * alto)
    for s in range(n):
        ox, oy = (s % 8) * 16, (s // 8) * 16
        for cuarto in range(4):
            dx = 8 if cuarto >= 2 else 0
            dy = 8 if cuarto % 2 else 0
            for y in range(8):
                b = vram[SPRITES + s * 32 + cuarto * 8 + y]
                for x in range(8):
                    if b & (0x80 >> x):
                        pix[(oy + dy + y) * ancho + ox + dx + x] = PALETA[15]
    png(pix, ancho, alto, ruta, zoom=3)


def main():
    rom = open(sys.argv[1], "rb").read()
    org = int(sys.argv[2], 0)
    if org != ORG:
        raise SystemExit("este cartucho va en 0x4000")
    salida = sys.argv[3]
    os.makedirs(salida, exist_ok=True)

    # La tabla de 0x47D6 deja R7 en 0xE4 -fondo AZUL- y asi se queda mientras
    # esta el logotipo de la casa; 0x4B4B lo cambia a 0xE0 -negro- antes de
    # pintar la eleccion de jugadores, y ya no vuelve. Medido en los volcados
    # del emulador: info_00 e info_01 dan E4, y de info_02 en adelante, E0.
    usa_fondo(4)
    pantalla(escena_logotipo(rom), os.path.join(salida, "logotipo.png"))

    usa_fondo(0)
    v = escena_titulo(rom)
    pantalla(v, os.path.join(salida, "titulo.png"))
    rotulo(v, os.path.join(salida, "rotulo.png"))
    for t in range(3):
        hoja_de_tiles(v, t, os.path.join(salida, "tiles_titulo_%d.png" % t))

    pantalla(escena_nivel(rom), os.path.join(salida, "nivel.png"))

    v = escena_pista(rom)
    pantalla(v, os.path.join(salida, "pista.png"))
    for t in range(3):
        hoja_de_tiles(v, t, os.path.join(salida, "tiles_pista_%d.png" % t))
    hoja_de_sprites(v, os.path.join(salida, "sprites.png"))

    # Un fotograma de cada jugador, con sus patrones de sprite puestos.
    for cual, nombre in ((0, "fotograma_cercano"), (20, "fotograma_lejano")):
        v = escena_fotograma(rom, cual)
        hoja_de_sprites(v, os.path.join(salida, "%s.png" % nombre), n=32)
    print("escrito en %s" % salida)


if __name__ == "__main__":
    main()
