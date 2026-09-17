#!/usr/bin/env python3
"""Rehace la VRAM de Circus Charlie y la DIBUJA. Aqui no hay ni una captura.

Cada imagen sale de correr en Python los MISMOS pasos que da el Z80, citando la
direccion de cada paso. Si un dibujo sale mal, lo que esta mal es la lectura del
cartucho: por eso vale como comprobacion y no como adorno.

EL REPARTO DE LA VRAM, QUE HAY QUE LEER EN LOS REGISTROS
--------------------------------------------------------
Los ocho registros los baja 0x4708 desde 0x4722, que vale
`02 E2 0E 7F 07 76 03 E1` -los mismos ocho, byte a byte, que Magical Tree
(RC-713) y Comic Bakery (RC-714)-. En SCREEN 2 el R3 y el R4 no son direcciones
sino BASE y MASCARA:

    R2 = 0x0E   tabla de NOMBRES en 0x3800
    R3 = 0x7F   COLOR: bit 7 a CERO, base 0x0000
    R4 = 0x07   PATRONES: bit 2 puesto, base 0x2000
    R5 = 0x76   atributos de sprite en 0x3B00
    R6 = 0x03   patrones de SPRITE en 0x1800

Lo confirma el propio cartucho: 0x434A manda "los patrones del titulo" a
0x3600 y 0x4350 su color a 0x1600, que son la misma celda de tercios
distintos, uno en cada tabla.

Y OJO CON LAS DIRECCIONES DE 16 BITS: el cartucho escribe `ld de,07600h` para
la VRAM 0x3600 y `ld de,05600h` para la 0x1600. El VDP solo mira catorce bits,
asi que los dos de arriba sobran; aqui se enmascaran igual que alli.

LO QUE SALE
-----------
    logotipo.png   el KONAMI que baja por la pantalla, patrones 0x41..0x5A
    fuente-titulo.png  los 48 dibujos que 0x4347 sube para la pantalla de
                   titulo: la fuente entera, recolocada en el patron 0xC0 del
                   tercer tercio y pintada de 0x70
    tiles.png      la hoja de patrones del fondo, tal como queda en la VRAM
    fuente.png     los dibujos de texto
    sprites.png    los patrones de sprite de 0x1800

Uso: graficos.py <rom> <org> <salida>
"""
import os
import struct
import sys
import zlib

ORG = 0x4000

PALETA = [
    (0, 0, 0), (0, 0, 0), (33, 200, 66), (94, 220, 120),
    (84, 85, 237), (125, 118, 252), (212, 82, 77), (66, 235, 245),
    (252, 85, 84), (255, 121, 120), (212, 193, 84), (230, 206, 128),
    (33, 176, 59), (201, 91, 186), (204, 204, 204), (255, 255, 255),
]

VDP = [0x02, 0xE2, 0x0E, 0x7F, 0x07, 0x76, 0x03, 0xE1]
NOMBRES = VDP[2] * 0x400
COLOR = (VDP[3] & 0x80) << 6
PATRONES = (VDP[4] & 0x04) << 11
SPRITES = VDP[6] * 0x800


def png(w, h, px, fn):
    raw = b"".join(b"\0" + bytes(px[y * w * 3:(y + 1) * w * 3]) for y in range(h))

    def chunk(t, d):
        return (struct.pack(">I", len(d)) + t + d
                + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF))
    open(fn, "wb").write(b"\x89PNG\r\n\x1a\n"
                         + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                         + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def lienzo(w, h, c=(24, 24, 24)):
    return bytearray(bytes(c) * (w * h))


def punto(px, w, x, y, c):
    i = (y * w + x) * 3
    px[i], px[i + 1], px[i + 2] = c


class Vram:
    """La VRAM y su puntero de escritura, como el VDP de verdad.

    Hace falta el puntero porque 0x45C6 encadena DOS bloques: el segundo se
    descomprime con el HL que dejo el primero y sin volver a situar el destino.
    """

    def __init__(self):
        self.b = bytearray(0x4000)
        self.pt = 0

    def situa(self, de):
        self.pt = de & 0x3FFF

    def escribe(self, v):
        self.b[self.pt] = v
        self.pt = (self.pt + 1) & 0x3FFF


def descomprime(v, rom, ini, destino=None, cabecera=True):
    """El descompresor de 0x45C9, con sus puertas.

    El lenguaje va al reves de lo que parece: bit 7 a CERO repite un byte y
    bit 7 PUESTO copia n bytes tal cual. 0x80 cambia de destino y 0x00 cierra.
    Devuelve donde acaba, que es lo que permite encadenar el bloque siguiente.
    """
    p = ini - ORG
    if destino is not None:
        v.situa(destino)
    elif cabecera:
        v.situa(rom[p] | (rom[p + 1] << 8))
        p += 2
    while True:
        ctrl = rom[p]
        p += 1
        cuenta = ctrl & 0x7F
        if cuenta == 0:
            if ctrl == 0x00:
                return ORG + p
            v.situa(rom[p] | (rom[p + 1] << 8))
            p += 2
            continue
        if ctrl & 0x80:
            for i in range(cuenta):
                v.escribe(rom[p + i])
            p += cuenta
        else:
            for _ in range(cuenta):
                v.escribe(rom[p])
            p += 1


def rellena(v, destino, n, valor):
    v.situa(destino)
    for _ in range(n):
        v.escribe(valor)


def duplica_las_dos_tablas(v):
    """0x45B0: el primer tercio de patrones y el de color, a los otros dos."""
    for base in (PATRONES, COLOR):
        v.b[base + 0x800:base + 0x1000] = v.b[base:base + 0x800]
        v.b[base + 0x1000:base + 0x1800] = v.b[base:base + 0x800]


def vram_del_titulo(rom):
    """0x4341: la cortinilla, el fondo y los patrones del titulo."""
    v = Vram()
    # 0x4B49 prepara_la_cortinilla: los 26 dibujos del logotipo
    descomprime(v, rom, 0x4BA6, destino=0x6208)          # 0x4B54
    rellena(v, 0x0208, 0xD0, 0xF0)                       # 0x4B5D
    duplica_las_dos_tablas(v)                            # 0x4B68
    # 0x45BB carga_la_pantalla_de_fondo: dos bloques ENCADENADOS
    fin = descomprime(v, rom, 0x47DE)                    # 0x45C0
    descomprime(v, rom, fin)                             # 0x45C6, pegado detras
    duplica_las_dos_tablas(v)                            # 0x45BE
    # 0x4347 los patrones del titulo y su color
    descomprime(v, rom, 0x47F1, destino=0x7600)          # 0x4347
    rellena(v, 0x5600, 0x180, 0x70)                      # 0x4350
    descomprime(v, rom, 0x4A69)                          # 0x435B
    de = 0x4600                                          # 0x4361: diecisiete veces
    for _ in range(0x11):
        descomprime(v, rom, 0x4378, destino=de)
        de += 0x10
    return v


def pinta_celda(px, w, x0, y0, patron, color, esc=1):
    for f in range(8):
        p, c = patron[f], color[f]
        tinta, fondo = PALETA[c >> 4], PALETA[c & 0x0F]
        for b in range(8):
            col = tinta if p & (0x80 >> b) else fondo
            for dy in range(esc):
                for dx in range(esc):
                    punto(px, w, x0 + b * esc + dx, y0 + f * esc + dy, col)


def celda(v, t, tercio=0):
    p = PATRONES + tercio * 0x800 + t * 8
    c = COLOR + tercio * 0x800 + t * 8
    return v.b[p:p + 8], v.b[c:c + 8]


def hoja(v, tercio, fn, cols=16, esc=2):
    w, h = cols * 8 * esc, (256 // cols) * 8 * esc
    px = lienzo(w, h)
    for t in range(256):
        pa, co = celda(v, t, tercio)
        pinta_celda(px, w, (t % cols) * 8 * esc, (t // cols) * 8 * esc, pa, co, esc)
    png(w, h, px, fn)


def rango(v, t0, n, fn, tercio=0, cols=10, esc=4):
    filas = (n + cols - 1) // cols
    w, h = cols * 8 * esc, filas * 8 * esc
    px = lienzo(w, h)
    for i in range(n):
        pa, co = celda(v, t0 + i, tercio)
        pinta_celda(px, w, (i % cols) * 8 * esc, (i // cols) * 8 * esc, pa, co, esc)
    png(w, h, px, fn)


def logotipo(v, fn, esc=6):
    """El logotipo de KONAMI, montado como lo monta 0x4B7D.

    Empieza en el patron 0x41 y los pinta CORRELATIVOS (`inc a` de 0x4B9C) en
    tres filas seguidas de 3, 11 y 12 celdas: veintiseis, del 0x41 al 0x5A. Es
    el mismo reparto, celda por celda, que usan Magical Tree (desde el 0x60) y
    Comic Bakery (desde el 0x40) para el mismo logotipo.
    """
    filas = [(0x41, 3), (0x44, 11), (0x4F, 12)]
    w, h = 12 * 8 * esc, 3 * 8 * esc
    px = lienzo(w, h)
    for r, (t0, n) in enumerate(filas):
        for i in range(n):
            pa, co = celda(v, t0 + i, 0)
            pinta_celda(px, w, i * 8 * esc, r * 8 * esc, pa, co, esc)
    png(w, h, px, fn)


def sprites(v, base, fn, n=16, cols=8, esc=3):
    filas = (n + cols - 1) // cols
    w, h = cols * 16 * esc, filas * 16 * esc
    px = lienzo(w, h)
    for i in range(n):
        d = base + i * 32
        x0, y0 = (i % cols) * 16 * esc, (i // cols) * 16 * esc
        for cuarto in range(4):
            cx, cy = (cuarto // 2) * 8 * esc, (cuarto % 2) * 8 * esc
            pinta_celda(px, w, x0 + cx, y0 + cy,
                        v.b[d + cuarto * 8: d + cuarto * 8 + 8], b"\xf0" * 8, esc)
    png(w, h, px, fn)


def main():
    global ORG
    rom = open(sys.argv[1], "rb").read()
    ORG = int(sys.argv[2], 0)
    sal = sys.argv[3]
    os.makedirs(sal, exist_ok=True)

    v = vram_del_titulo(rom)
    logotipo(v, os.path.join(sal, "logotipo.png"))
    hoja(v, 0, os.path.join(sal, "tiles.png"))
    hoja(v, 2, os.path.join(sal, "tiles-tercio3.png"))
    rango(v, 0xC0, 48, os.path.join(sal, "fuente-titulo.png"), tercio=2, cols=16, esc=4)
    sprites(v, SPRITES, os.path.join(sal, "sprites.png"))

    for f in sorted(os.listdir(sal)):
        print("  ", os.path.join(sal, f))


if __name__ == "__main__":
    main()
