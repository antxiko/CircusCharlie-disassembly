#!/usr/bin/env python3
"""Monta las pantallas fijas del cartucho ejecutando sus propios pasos.

No hay capturas: cada imagen sale de correr en Python lo que hace el Z80.

  - La PANTALLA DE TITULO la monta L_4489. El rotulo grande no es un dibujo
    suelto: son tres filas de veinte celdas con patrones CONSECUTIVOS desde el
    0xC0, escritas una tras otra (`ld d,0c0h / ld c,003h / ld hl,03887h`, y un
    `inc d` por celda). Debajo, dos filas rellenas con los patrones 0xBE y
    0xBF, y encima el guion de texto de 0x5ca4, que trae el PUSH SPACE KEY.
    El color del rotulo lo pone un FILVRM de 480 bytes en 0x0600 -que son los
    sesenta patrones del rotulo- y alterna entre 0xD0 y 0xC0 segun el bit 0
    del contador de 0xE043: por eso el rotulo cambia de color.

  - El MARCO DE ZONA lo monta L_4A61: dos filas de veinticuatro celdas arriba
    y abajo y cuatro columnas de veintidos celdas a los lados, mas el guion de
    0x71f7 con el resto del decorado.

Uso: pantallas.py <rom> <org> <carpeta destino>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapas import monta_vram, celda, guarda_png, FONDO      # noqa: E402
from guiones import ejecuta                                  # noqa: E402

NOMBRES = 0x3800


def pantalla_vacia():
    return [[0] * 32 for _ in range(24)], [FONDO] * (256 * 192)


def pinta(vram, nombres, pix):
    for f in range(24):
        for c in range(32):
            if nombres[f][c]:
                celda(vram, f, c, nombres[f][c], pix)


def pon_guion(rom, org, nombres, inicio):
    """Escribe en la tabla de nombres lo que deja un guion del rotulador."""
    r = ejecuta(rom, org, inicio)
    if r is None:
        raise SystemExit("el guion de 0x%04X no cierra" % inicio)
    p = inicio - org
    destino = None
    while True:
        if destino is None:
            destino = rom[p] | (rom[p + 1] << 8)
            p += 2
        b = rom[p]
        p += 1
        if b == 0xFF:
            return
        if b == 0xFE:
            destino = None
            continue
        o = destino - NOMBRES
        if 0 <= o < 768:
            nombres[o // 32][o % 32] = b
        destino += 1


def titulo(rom, org, vram, color_alto=True):
    """La pantalla de titulo, tal como la deja L_4489."""
    nombres, pix = pantalla_vacia()

    # El FILVRM de 0x4495: 480 bytes de color desde 0x0600, o sea los sesenta
    # patrones del rotulo (0x600/8 = 0xC0). Alterna 0xD0 y 0xC0.
    v = bytearray(vram)
    tinta = 0xD0 if color_alto else 0xC0
    for base in (0x0000, 0x0800, 0x1000):
        v[base + 0x600:base + 0x600 + 0x1E0] = bytes([tinta]) * 0x1E0

    # Tres filas de veinte celdas con patrones consecutivos desde 0xC0
    patron = 0xC0
    origen = 0x3887 - NOMBRES
    for fila in range(3):
        for col in range(20):
            o = origen + fila * 32 + col
            nombres[o // 32][o % 32] = patron
            patron = (patron + 1) & 0xFF

    # Las dos filas de abajo, rellenas con 0xBE y 0xBF
    for o, p in ((0x3AC0 - NOMBRES, 0xBE), (0x3AE0 - NOMBRES, 0xBF)):
        for c in range(32):
            nombres[(o + c) // 32][(o + c) % 32] = p

    pon_guion(rom, org, nombres, 0x5CA4)      # PUSH SPACE KEY y lo demas
    pinta(v, nombres, pix)
    return pix


def marco(rom, org, vram):
    """El marco del area de juego, tal como lo deja L_4A61."""
    nombres, pix = pantalla_vacia()
    for o, p, n in ((0x3844 - NOMBRES, 0xA3, 24), (0x3AE4 - NOMBRES, 0xA2, 24)):
        for c in range(n):
            nombres[(o + c) // 32][(o + c) % 32] = p
    for o, p, n in ((0x3842 - NOMBRES, 0x97, 22), (0x3863 - NOMBRES, 0xA5, 20),
                    (0x387C - NOMBRES, 0xA1, 20), (0x385D - NOMBRES, 0x97, 22)):
        for f in range(n):
            q = o + f * 32
            if 0 <= q < 768:
                nombres[q // 32][q % 32] = p
    pon_guion(rom, org, nombres, 0x71F7)
    pinta(vram, nombres, pix)
    return pix


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    rom = open(sys.argv[1], "rb").read()
    org = int(sys.argv[2], 0)
    destino = sys.argv[3]
    os.makedirs(destino, exist_ok=True)
    vram = monta_vram(rom, org)

    for nombre, pix in (("titulo.png", titulo(rom, org, vram, True)),
                        ("titulo_otro_color.png", titulo(rom, org, vram, False)),
                        ("marco_de_zona.png", marco(rom, org, vram))):
        ruta = os.path.join(destino, nombre)
        guarda_png(pix, 256, 192, ruta)
        print("  %s" % ruta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
