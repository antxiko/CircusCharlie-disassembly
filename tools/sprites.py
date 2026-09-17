#!/usr/bin/env python3
"""Dibuja los sprites del cartucho, montandolos como los monta el juego.

Aqui no hay capturas. Los patrones de sprite de Twin Bee no estan enteros en
la ROM: solo esta la MITAD IZQUIERDA de cada uno, y 0x4743 calcula la derecha
invirtiendo cada byte bit a bit. Por eso todo lo que vuela en este juego es
simetrico respecto a su eje vertical. Aqui se hace lo mismo.

De cada fase salen sus enemigos, porque 0x9177 sube un bloque distinto segun
(0xE076); las naves, los disparos y las campanas son comunes a las cinco.

Lo que sale:

    naves.png           los sprites comunes: naves, brazos, disparos, campanas
    enemigos_faseN.png  los de cada fase
    jefe_faseN.png      los del jefe de cada fase

Uso: sprites.py <rom> <org> <directorio de salida>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from descomprime import descomprime, filtro                     # noqa: E402
from vdp import PALETA, R7, SPR_PAT, guarda                     # noqa: E402

COMUNES = 0x8E8F              # -> 0x1800, BC = 0x1100
COMUNES2 = 0x8F9F             # -> 0x1A20, BC = 0x0501
COMUNES3 = 0x903F             # bloque suelto, con su destino dentro
DEL_JEFE = 0x9671             # -> 0x1D80, BC = 0x0401
TABLA_ENEMIGOS = 0x9191       # cinco punteros
TABLA_JEFE = 0x96F1           # otros cinco
FASES = 5


def expande(rom, org, origen, destino, bc, v):
    """0x4743: media pareja de 16 bytes y la otra media invertida.

    B y C entran al reves -`ld h,c` y `ld l,b`-, asi que C es el filtro y B
    las vueltas. Con el bit 0 de C puesto salen DOS parejas por vuelta y el
    origen avanza 32 bytes; sin el, una sola y avanza 16.
    """
    b, c = bc >> 8, bc & 0xFF
    p = origen - org
    d = destino & 0x3FFF
    for _ in range(b):
        base = p
        for k in range(16):
            v[d] = rom[base + k]
            d += 1
        if c & 1:
            for k in range(16):
                v[d] = rom[base + 16 + k]
                d += 1
            for k in range(16):
                v[d] = filtro(rom[base + 16 + k], 1)
                d += 1
        for k in range(16):
            v[d] = filtro(rom[base + k], 1)
            d += 1
        p += 32 if c & 1 else 16
    return v


def palabra(rom, org, a):
    return rom[a - org] | rom[a - org + 1] << 8


def vram_de_sprites(rom, org, fase):
    """Lo que dejan 0x5E12, 0x9648 y 0x9177 en la tabla de patrones."""
    v = bytearray(0x4000)
    expande(rom, org, COMUNES, 0x1800, 0x1100, v)
    expande(rom, org, COMUNES2, 0x1A20, 0x0501, v)
    descomprime(rom, org, COMUNES3, vram=v)
    descomprime(rom, org, 0x4AA9, 0x1D40, 0, v)
    # y los enemigos de la fase, que van a 0x1D80. El primer byte del bloque
    # dice cuantas parejas trae (0x9183), y detras de ellas viene un bloque
    # comprimido normal con su destino dentro.
    de = palabra(rom, org, TABLA_ENEMIGOS + 2 * (fase - 1))
    n = rom[de - org]
    expande(rom, org, de + 1, 0x1D80, n << 8, v)
    descomprime(rom, org, de + 1 + 16 * n, vram=v)
    return v


def vram_del_jefe(rom, org, fase):
    """Lo que sube 0x9648 cuando aparece el jefe: PISA a los enemigos en
    0x1D80, que para entonces ya no hacen falta."""
    v = vram_de_sprites(rom, org, fase)
    expande(rom, org, DEL_JEFE, 0x1D80, 0x0401, v)
    de = palabra(rom, org, TABLA_JEFE + 2 * (fase - 1))
    expande(rom, org, de, 0x1E80, 0x0201, v)
    descomprime(rom, org, de + 32, 0x1F00, 0, v)
    return v


def hoja(v, pat0, pat1, color=15, cols=8, base=SPR_PAT):
    """Una hoja con los sprites del `pat0` al `pat1`, de cuatro en cuatro."""
    n = (pat1 - pat0) // 4
    filas = (n + cols - 1) // cols
    fondo = PALETA[R7 & 0x0F]
    px = [[fondo] * (cols * 16) for _ in range(filas * 16)]
    tinta = PALETA[color]
    for i in range(n):
        a = base + (pat0 + 4 * i) * 8
        oy, ox = (i // cols) * 16, (i % cols) * 16
        for f in range(16):
            izq, der = v[a + f], v[a + 16 + f]
            for b in range(8):
                if izq & (0x80 >> b):
                    px[oy + f][ox + b] = tinta
                if der & (0x80 >> b):
                    px[oy + f][ox + 8 + b] = tinta
    return px


def main():
    rom = open(sys.argv[1], "rb").read()
    org = int(sys.argv[2], 0)
    sal = sys.argv[3]
    os.makedirs(sal, exist_ok=True)
    # 0x1800 es el patron 0, asi que los comunes ocupan del 0 al 0xB0 y lo
    # que sube la fase empieza justo en el 0xB0 (0x1D80).
    v = vram_de_sprites(rom, org, 1)
    guarda(hoja(v, 0, 0xB0), os.path.join(sal, "naves.png"), 3)
    for fase in range(1, FASES + 1):
        vf = vram_de_sprites(rom, org, fase)
        guarda(hoja(vf, 0xB0, 0x100),
               os.path.join(sal, "enemigos_fase%d.png" % fase), 3)
        guarda(hoja(vram_del_jefe(rom, org, fase), 0xB0, 0x100),
               os.path.join(sal, "jefe_fase%d.png" % fase), 3)


if __name__ == "__main__":
    main()
