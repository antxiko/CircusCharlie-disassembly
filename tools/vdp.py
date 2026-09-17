#!/usr/bin/env python3
"""La VRAM de este cartucho y como se pinta. Sin capturas: todo se calcula.

El reparto no esta supuesto: sale de la tabla de OCHO bytes de 0x47F1, que
0x47E1 escribe del registro 7 al 0 (`ld c,8`, `dec c`, WRTVDP), o sea al reves
de como esta escrita:

    R7 = 0xE4   tinta 14 sobre fondo 4, el azul del cielo
    R6 = 0x03   patrones de SPRITE en 0x1800
    R5 = 0x76   atributos de sprite en 0x3B00
    R4 = 0x07   en SCREEN 2 solo cuenta el bit 2: patrones en 0x2000
    R3 = 0x7F   y aqui solo el bit 7: color en 0x0000, y el resto es MASCARA
    R2 = 0x0E   tabla de nombres en 0x3800
    R1 = 0xE2   16 KB, pantalla y interrupcion activas, sprites de 16x16
    R0 = 0x02   SCREEN 2

R3 y R4 no son direcciones sino base y mascara, que es la trampa de siempre en
SCREEN 2: leerlos como direcciones deja las formas bien y los COLORES a
franjas. Aqui salen del reves de lo corriente -patrones ARRIBA, color ABAJO-,
igual que en Knightmare.
"""
import struct
import zlib

NOMBRES = 0x3800
PATRONES = 0x2000
COLOR = 0x0000
SPR_PAT = 0x1800
SPR_ATR = 0x3B00
R7 = 0xE4

# La paleta del TMS9918, en el orden de los codigos del VDP.
PALETA = [(0, 0, 0), (0, 0, 0), (33, 200, 66), (94, 220, 120),
          (84, 85, 237), (125, 118, 252), (212, 82, 77), (66, 235, 245),
          (252, 85, 84), (255, 121, 120), (212, 193, 84), (230, 206, 128),
          (33, 176, 59), (201, 91, 186), (204, 204, 204), (255, 255, 255)]


def png(w, h, px, fn):
    """PNG de 24 bits sin dependencias. px son los bytes RGB en crudo."""
    nul = bytes([0])
    raw = b"".join(nul + bytes(px[y * w * 3:(y + 1) * w * 3]) for y in range(h))

    def chunk(t, d):
        return (struct.pack(">I", len(d)) + t + d
                + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF))
    firma = bytes([137, 80, 78, 71, 13, 10, 26, 10])
    open(fn, "wb").write(firma
                         + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                         + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def escala(lienzo, esc):
    """Un lienzo -lista de filas de (r,g,b)- a los bytes que espera png()."""
    px = bytearray()
    for fila in lienzo:
        tira = bytearray()
        for r, g, b in fila:
            tira += bytes((r, g, b)) * esc
        px += tira * esc
    return px


def guarda(lienzo, fn, esc=2):
    png(len(lienzo[0]) * esc, len(lienzo) * esc, escala(lienzo, esc), fn)
    print("  %s  %d x %d" % (fn, len(lienzo[0]) * esc, len(lienzo) * esc))


def casilla(v, n, banda):
    """Los 8x8 pixeles de la casilla n en el tercio de pantalla que se pida."""
    p = PATRONES + banda * 0x800 + n * 8
    c = COLOR + banda * 0x800 + n * 8
    out = []
    for f in range(8):
        forma, col = v[p + f], v[c + f]
        tinta = PALETA[col >> 4] if col >> 4 else PALETA[R7 & 0x0F]
        papel = PALETA[col & 0x0F] if col & 0x0F else PALETA[R7 & 0x0F]
        out.append([tinta if forma & (0x80 >> b) else papel for b in range(8)])
    return out


def pinta(v, nombres=None):
    """Los 256x192 pixeles del fondo: 24 filas de 32 casillas, cada tercio con
    su banco. Sin `nombres`, se usa la tabla que hay en la VRAM."""
    if nombres is None:
        nombres = v[NOMBRES:NOMBRES + 768]
    fondo = PALETA[R7 & 0x0F]
    px = [[fondo] * 256 for _ in range(192)]
    for f in range(24):
        for c in range(32):
            d = casilla(v, nombres[f * 32 + c], f // 8)
            for y in range(8):
                px[f * 8 + y][c * 8:c * 8 + 8] = d[y]
    return px


def sprite(v, patron, color, base=SPR_PAT):
    """Los 16x16 (transparente = None) del patron de sprite numero `patron`.

    En el VDP los 32 bytes van por cuartos de 8x8: los 16 primeros son la
    mitad IZQUIERDA de arriba abajo, y los 16 siguientes la DERECHA.
    """
    a = base + (patron & 0xFC) * 8
    tinta = PALETA[color & 0x0F]
    px = [[None] * 16 for _ in range(16)]
    for f in range(16):
        izq, der = v[a + f], v[a + 16 + f]
        for b in range(8):
            if izq & (0x80 >> b):
                px[f][b] = tinta
            if der & (0x80 >> b):
                px[f][8 + b] = tinta
    return px


def pega_sprites(px, v, atributos=None, base=SPR_PAT):
    """Superpone los 32 sprites de la tabla de atributos sobre un lienzo ya
    pintado. Y = 0xD0 corta la lista, como manda el VDP."""
    if atributos is None:
        atributos = v[SPR_ATR:SPR_ATR + 128]
    for i in range(32):
        y, x, p, c = atributos[i * 4:i * 4 + 4]
        if y == 0xD0:
            break
        if y == 0xE0:
            continue
        y = (y + 1) & 0xFF
        if y > 0xE0:
            y -= 0x100
        if c & 0x80:                       # el bit de "arrastre a la izquierda"
            x -= 32
        d = sprite(v, p, c, base)
        for f in range(16):
            for cc in range(16):
                if d[f][cc] is None:
                    continue
                yy, xx = y + f, x + cc
                if 0 <= yy < len(px) and 0 <= xx < len(px[0]):
                    px[yy][xx] = d[f][cc]
    return px
