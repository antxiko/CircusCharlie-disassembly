#!/usr/bin/env python3
"""El descompresor del cartucho, rehecho en Python a partir de 0x4716.

Todo lo que este cartucho mete en la VRAM -patrones, colores, tablas de
nombres y textos- pasa por la misma rutina, asi que sin ella no hay ni una
lamina. El formato, leido instruccion a instruccion en 0x471F:

    n = 0x00           fin del bloque
    n < 0x80           REPETICION: el byte siguiente, n veces
    n = 0x80           cambio de destino: los dos bytes siguientes son la
                       nueva direccion de VRAM, y ademas APAGA el filtro
                       (0x4711 hace `ld c,0` antes de volver al bucle)
    n > 0x80           LITERALES: los n & 0x7F bytes siguientes, tal cual

Y cada byte que sale pasa por el filtro de 0x4786, que mira el registro C:

    bit 0 de C     el byte se INVIERTE bit a bit (0x4793: ocho `rr l / rla`).
                   Es el espejo horizontal: media nave guardada, la otra
                   mitad calculada.
    bit 7 de C     PERMUTA DE COLOR (0x47B5), nibble a nibble:
                   0x0C -> 6 siempre; y si ademas el bit 0 esta puesto,
                   0x0A se queda, 6 -> 0x0C y 5 -> 9.

0x4695 entra con C=1 (espejo) y 0x4699 con C=0; los dos repiten el mismo
bloque TRES veces subiendo 0x0800 en la VRAM, que son los tres bancos de
SCREEN 2.

Uso como modulo:  from descomprime import descomprime, DEST_EN_EL_BLOQUE
"""


def _permuta_nibble(v, c):
    """La permuta de color de 0x47B5. v es un nibble."""
    if v == 0x0C:
        return 6
    if c & 1:
        if v == 0x0A:
            return v
        if v == 6:
            return 0x0C
        if v == 5:
            return 9
    return v


def filtro(b, c):
    """El byte que sale de 0x4786 para el byte b leido y el registro C."""
    if c & 0x80:
        alto = _permuta_nibble((b >> 4) & 0x0F, c)
        bajo = _permuta_nibble(b & 0x0F, c)
        return (alto << 4) | bajo
    if c & 1:
        r = 0
        for _ in range(8):
            r = (r << 1) | (b & 1)
            b >>= 1
        return r
    return b


DEST_EN_EL_BLOQUE = -1


def descomprime(rom, org, origen, destino=DEST_EN_EL_BLOQUE, c=0, vram=None):
    """Descomprime el bloque de `origen` sobre una VRAM de 16 KB.

    destino: la direccion de VRAM donde empieza; con DEST_EN_EL_BLOQUE se
    leen los dos primeros bytes del bloque, que es lo que hace 0x4711.
    Devuelve (vram, siguiente_origen).
    """
    if vram is None:
        vram = bytearray(0x4000)
    p = origen - org
    if destino == DEST_EN_EL_BLOQUE:
        destino = rom[p] | rom[p + 1] << 8
        p += 2
        c = 0
    d = destino & 0x3FFF
    while True:
        n = rom[p]
        p += 1
        if n == 0:
            return vram, org + p
        if n == 0x80:                       # nuevo destino, y filtro fuera
            d = (rom[p] | rom[p + 1] << 8) & 0x3FFF
            p += 2
            c = 0
            continue
        if n < 0x80:                        # repeticion
            b = filtro(rom[p], c)
            p += 1
            for _ in range(n):
                vram[d] = b
                d = (d + 1) & 0x3FFF
        else:                               # literales
            for _ in range(n & 0x7F):
                vram[d] = filtro(rom[p], c)
                p += 1
                d = (d + 1) & 0x3FFF


def tres_bancos(rom, org, origen, destino, c=0, vram=None):
    """Lo que hacen 0x4695 (c=1) y 0x4699 (c=0): el mismo bloque en los tres
    bancos de SCREEN 2, subiendo 0x0800 cada vez."""
    if vram is None:
        vram = bytearray(0x4000)
    for k in range(3):
        descomprime(rom, org, origen, (destino + 0x800 * k) & 0x3FFF, c, vram)
    return vram
