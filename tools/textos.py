#!/usr/bin/env python3
"""Lee las listas de tiles del cartucho y saca el texto y su sitio en pantalla.

Yie Ar Kung-Fu no guarda cadenas: guarda LISTAS DE TILES para el interprete de
0x44a6, y el texto esta escrito con los numeros de tile de su propia fuente. El
alfabeto se deduce de las tres palabras que se leen solas -KONAMI, PERFECT y
GAME OVER-: la 'A' es el tile 0x21 y de ahi seguidas hasta la 'Z' en 0x3a, con
el 0x00 de espacio.

La lista se recorre con su propio formato: 0xFF acaba, 0xFE toma los dos bytes
siguientes como una direccion de VRAM nueva -byte bajo primero- y sigue ahi, y
cualquier otro byte es un tile que se escribe y avanza una posicion.

Y TODA lista empieza por su direccion, porque 0x449e -la puerta normal- solo
pone la mascara y CAE dentro de 0x44a0, que es el cuerpo del comando 0xFE: lo
primero que hace es leerse dos bytes. La unica entrada que se salta eso es
0x449a. Leer una lista sin contar con esos dos bytes saca dos letras de mas al
principio y coloca el texto donde no va.

Como la tabla de nombres esta en la VRAM 0x3800 y mide 32x24, de la direccion
salen la fila y la columna, que es lo que hace falta para poder decir donde se
lee cada cosa en la pantalla de verdad.

Uso: textos.py <rom> <ini> [<ini> ...]
     textos.py <rom> --todas      (barre la ROM buscando tramos legibles)
"""
import sys

ORG = 0x4000
NOMBRES = 0x3800


def glifo(v):
    if v in (0x00, 0x20):
        return " "                       # 0x00 es el tile vacio y 0x20 el espacio
    if 0x21 <= v <= 0x3A:
        return chr(v - 0x21 + ord("A"))
    if 0x10 <= v <= 0x19:
        return chr(v - 0x10 + ord("0"))
    if v == 0x1A:
        return "@"                       # el circulo del copyright
    return f"[{v:02X}]"


def lee(rom, pos, con_direccion=True):
    """Recorre una lista de tiles y devuelve (fin, [(vram, texto), ...])."""
    tramos, vram, act = [], None, []
    if con_direccion:
        vram = rom[pos - ORG] | (rom[pos + 1 - ORG] << 8)
        pos += 2
    while True:
        if not ORG <= pos < ORG + len(rom):
            return None, []
        v = rom[pos - ORG]
        pos += 1
        if v == 0xFF:
            if act:
                tramos.append((vram, "".join(act)))
            return pos, tramos
        if v == 0xFE:
            if act:
                tramos.append((vram, "".join(act)))
                act = []
            vram = rom[pos - ORG] | (rom[pos + 1 - ORG] << 8)
            pos += 2
            continue
        act.append(glifo(v))


def sitio(vram):
    if vram is None:
        return "(la trae el codigo en HL)"
    p = (vram & 0x3FFF) - NOMBRES
    if 0 <= p < 768:
        return f"VRAM 0x{vram:04X} = fila {p // 32}, columna {p % 32}"
    return f"VRAM 0x{vram:04X} (fuera de la tabla de nombres)"


def main():
    rom = open(sys.argv[1], "rb").read()
    for a in sys.argv[2:]:
        ini = int(a, 0)
        fin, tramos = lee(rom, ini)
        if fin is None:
            print(f"0x{ini:04X}: no es una lista de tiles")
            continue
        print(f"\n0x{ini:04X}..0x{fin:04X}  ({fin - ini} bytes)")
        for vram, texto in tramos:
            print(f"    {sitio(vram):48}  |{texto}|")


if __name__ == "__main__":
    main()
