#!/usr/bin/env python3
"""Rutinas ordenadas por INSTRUCCIONES SIN COMENTAR (el margen que queda).

densidad.py mide el porcentaje; para decidir DONDE atacar hace falta el valor
absoluto: una rutina de 120 instrucciones al 30 % deja 84 sin comentar y una
de 8 al 0 % deja 8.

Uso: margen.py <asm> [cuantas]
"""
import re
import sys


def main():
    lineas = open(sys.argv[1], encoding="utf-8").read().splitlines()
    cuantas = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    bloques, nombre, ini, n, c = [], "(cabecera)", 0, 0, 0
    for ln in lineas:
        m = re.match(r"^([A-Za-z_][A-Za-z_0-9]*):\s*(;.*)?$", ln)
        if m:
            if n:
                bloques.append((nombre, ini, n, c))
            nombre, ini, n, c = m.group(1), 0, 0, 0
            continue
        m = re.match(r"^\t.*;([0-9a-f]{4})(.*)$", ln)
        if not m:
            continue
        if not ini:
            ini = int(m.group(1), 16)
        n += 1
        if ";" in m.group(2):
            c += 1
    if n:
        bloques.append((nombre, ini, n, c))
    bloques.sort(key=lambda b: -(b[2] - b[3]))
    for nom, a, n, c in bloques[:cuantas]:
        print("  %-38s 0x%04X  %3d instr  %3d sin  %3d %%"
              % (nom, a, n, n - c, c * 100 // n))
    tot_n = sum(b[2] for b in bloques)
    tot_c = sum(b[3] for b in bloques)
    print("  ---- %d instrucciones, %d comentarios, %.1f %%, %d sin comentar"
          % (tot_n, tot_c, 100.0 * tot_c / tot_n, tot_n - tot_c))


main()
