#!/usr/bin/env python3
"""Dibuja las 25 zonas de Konami's Ping Pong DESCOMPRIMIENDOLAS de la ROM.

No hay ni una captura del emulador aqui dentro: cada imagen se monta
ejecutando en Python lo que hace el cartucho, y por eso el dibujo es una
comprobacion de que se ha entendido, no una ilustracion.

La cadena, tal como la hace el propio juego:

  1. L_45D4 carga los OCHO registros del VDP desde la tabla de 0x45f7, que
     vale 02 E2 0E 7F 07 76 03 E0. Y ahi esta la sorpresa de este cartucho:

         R2 = 0x0E  ->  tabla de NOMBRES en 0x3800
         R3 = 0x7F  ->  tabla de COLORES en 0x0000
         R4 = 0x07  ->  tabla de PATRONES en 0x2000
         R6 = 0x03  ->  patrones de SPRITE en 0x1800

     O sea que este juego pone los colores DEBAJO y los patrones ENCIMA, al
     reves de lo habitual. Leerlo al reves da formas correctas y colores a
     franjas, que es el sintoma clasico.

  2. L_5DB8 llama tres veces a L_5DD5, con HL = 0x0000, 0x0800 y 0x1000: los
     tres tercios de SCREEN 2, cada uno con su juego de tablas. Dentro,
     L_5DD5 reparte cuatro cosas por tercio:

         base+0x0000  ocho ceros: el color del patron 0
         base+0x0080  0xF0 repetido 600 veces: tinta 15 sobre fondo 0
         base+0x03C0  el bloque 0x753d descomprimido (colores, tiles 0x78+)
         base+0x2000  el bloque 0x5e0e descomprimido (patrones, tiles 0x00+)
         base+0x23C0  el bloque 0x722b descomprimido (patrones, tiles 0x78+)

  3. Cada zona es un bloque RLE de 120 bytes (tools/rle.py), y cada byte es un
     METATILE: un cuadro de 2x2 celdas cuyos cuatro indices estan en la tabla
     de 0x6ef3, de cuatro bytes por entrada. 120 metatiles en 12 columnas por
     10 filas ocupan 24x20 celdas de las 32x24 de la pantalla.

Uso: mapas.py <rom> <org> <carpeta destino>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rle import descomprime, descomprime_vram          # noqa: E402

TABLA_DE_MAPAS = 0x6522
METATILES = 0x6EF3
N_ZONAS = 25

# Ancho y alto en metatiles, y de donde salen: NO del aspecto del dibujo, sino
# de las dos constantes con las que L_64CD cuenta. Pinta metatiles llevando la
# cuenta en (0xE2A0) hasta `cp 00ch` -doce por fila-, y filas en (0xE2A1)
# hasta `cp 00ah` -diez-. Y entre fila y fila suma 0x40 al puntero de la tabla
# de nombres, que son dos filas de 32 celdas: lo que ocupa un metatile.
ANCHO = 12
ALTO = 10

# El origen en la tabla de nombres, tambien del codigo: L_64B5 arranca con
# `ld hl,03864h`. Con la tabla de nombres en 0x3800, el desplazamiento es 0x64,
# o sea 100 celdas: fila 3, columna 4.
ORIGEN_FILA = 3
ORIGEN_COL = 4

# La paleta del TMS9918. El color 0 es TRANSPARENTE, no negro: se ve el
# fondo, que aqui es el que dice R7 (0xE0 -> borde 14, fondo 0).
PALETA = [
    (0, 0, 0), (0, 0, 0), (33, 200, 66), (94, 220, 120),
    (84, 85, 237), (125, 118, 252), (212, 82, 77), (66, 235, 245),
    (252, 85, 84), (255, 121, 120), (212, 193, 84), (230, 206, 128),
    (33, 176, 59), (201, 91, 186), (204, 204, 204), (255, 255, 255),
]
FONDO = PALETA[1]           # R7 = 0xE0: el fondo es el color 0, aqui negro


def monta_vram(rom, org):
    """Rehace los 16 KB de VRAM como los deja L_5DB8, tercio a tercio."""
    vram = bytearray(0x4000)
    for base in (0x0000, 0x0800, 0x1000):
        vram[base:base + 8] = b"\x00" * 8                    # color del tile 0
        vram[base + 0x80:base + 0x80 + 0x258] = b"\xF0" * 0x258
        for destino, origen in ((base + 0x03C0, 0x753D),     # colores
                                (base + 0x2000, 0x5E0E),     # patrones
                                (base + 0x23C0, 0x722B)):    # patrones altos
            r = descomprime_vram(rom, org, origen)
            if r is None:
                raise SystemExit("0x%04X no descomprime" % origen)
            datos = b"".join(t[1] for t in r[1])
            vram[destino:destino + len(datos)] = datos
    return vram


def celda(vram, fila, col, tile, pix):
    """Pinta una celda de 8x8 en `pix`, con el juego de tablas de su tercio.

    En SCREEN 2 la pantalla son tres tercios independientes: la fila decide
    que copia de las tablas se usa, y por eso el mismo indice de patron puede
    dar dibujos distintos arriba y abajo.
    """
    tercio = (fila // 8) * 0x800
    for y in range(8):
        forma = vram[0x2000 + tercio + tile * 8 + y]
        color = vram[0x0000 + tercio + tile * 8 + y]
        tinta = PALETA[color >> 4] if (color >> 4) else FONDO
        papel = PALETA[color & 15] if (color & 15) else FONDO
        for x in range(8):
            pix[(fila * 8 + y) * 256 + col * 8 + x] = \
                tinta if forma & (0x80 >> x) else papel


def dibuja_zona(rom, org, vram, indice):
    """Descomprime la zona `indice` y la devuelve como imagen de 256x192."""
    p = TABLA_DE_MAPAS - org + indice * 2
    destino = rom[p] | (rom[p + 1] << 8)
    r = descomprime(rom, org, destino)
    if r is None or len(r[1]) != 120:
        raise SystemExit("la zona %d no da 120 bytes" % indice)
    mapa = r[1]

    pix = [FONDO] * (256 * 192)
    for i, meta in enumerate(mapa):
        mf, mc = divmod(i, ANCHO)
        o = METATILES - org + meta * 4
        cuatro = rom[o:o + 4]
        for k, tile in enumerate(cuatro):
            df, dc = divmod(k, 2)
            fila = mf * 2 + df + ORIGEN_FILA
            col = mc * 2 + dc + ORIGEN_COL
            if fila < 24 and col < 32:
                celda(vram, fila, col, tile, pix)
    return pix


def guarda_png(pix, ancho, alto, ruta):
    """PNG sin comprimir de verdad (deflate con bloques crudos), sin PIL."""
    import struct
    import zlib
    filas = bytearray()
    for y in range(alto):
        filas.append(0)
        for x in range(ancho):
            filas += bytes(pix[y * ancho + x])
    def trozo(tipo, datos):
        return (struct.pack(">I", len(datos)) + tipo + datos
                + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF))
    png = (b"\x89PNG\r\n\x1a\n"
           + trozo(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0))
           + trozo(b"IDAT", zlib.compress(bytes(filas), 9))
           + trozo(b"IEND", b""))
    open(ruta, "wb").write(png)


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    rom = open(sys.argv[1], "rb").read()
    org = int(sys.argv[2], 0)
    destino = sys.argv[3]
    os.makedirs(destino, exist_ok=True)

    vram = monta_vram(rom, org)
    # Los mapas repetidos no se dibujan dos veces: se anota cual comparte con
    # cual, que es parte de lo que se ha aprendido del cartucho.
    vistos = {}
    for i in range(N_ZONAS):
        p = TABLA_DE_MAPAS - org + i * 2
        d = rom[p] | (rom[p + 1] << 8)
        if d in vistos:
            print("  zona %2d: el mismo mapa que la %d (0x%04X)"
                  % (i, vistos[d], d))
            continue
        vistos[d] = i
        pix = dibuja_zona(rom, org, vram, i)
        ruta = os.path.join(destino, "zona_%02d.png" % i)
        guarda_png(pix, 256, 192, ruta)
        print("  zona %2d: 0x%04X -> %s" % (i, d, ruta))
    print("  %d mapas distintos de %d zonas" % (len(vistos), N_ZONAS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
