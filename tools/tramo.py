#!/usr/bin/env python3
"""Saca del listado el tramo entre dos direcciones, para leerlo y comentarlo.

Un `awk` entre etiquetas deja de funcionar en cuanto una tanda las renombra.
Esto va por la direccion que mkasm escribe al final de cada linea, que no
cambia nunca.

Uso: tramo.py <listado.asm> <ini> <fin> [--solo-sin-comentar]
"""
import re
import sys

DIR = re.compile(r";([0-9a-f]{4})\s*$")
DIR_CON_COMENTARIO = re.compile(r";([0-9a-f]{4})\s+;\s*(.+)$")


def main():
    asm, ini, fin = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
    solo = "--solo-sin-comentar" in sys.argv
    for ln in open(asm, encoding="utf-8"):
        ln = ln.rstrip("\n")
        m = DIR.search(ln) or DIR_CON_COMENTARIO.search(ln)
        if not m:
            continue
        d = int(m.group(1), 16)
        if not (ini <= d <= fin):
            continue
        if solo and DIR_CON_COMENTARIO.search(ln):
            continue
        print(ln)


if __name__ == "__main__":
    main()
