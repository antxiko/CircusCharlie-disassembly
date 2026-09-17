#!/usr/bin/env python3
"""La densidad que HABRA cuando se apliquen las tandas de work/coment.

densidad.py mide sobre el .asm ya generado. Mientras las tandas de comentarios
se estan escribiendo aparte, esto dice como va a quedar sin tener que regenerar
el listado -que ademas no se puede regenerar mientras alguien lo esta leyendo-.

Uso: densidad_prevista.py <asm> <notes> <work/coment> [minimo] [--tramo A B]
"""
import glob
import os
import re
import sys


def comentadas(notes, carpeta):
    d = set()
    for fn in [notes] + sorted(glob.glob(os.path.join(carpeta, "*.notes"))):
        for ln in open(fn, encoding="utf-8"):
            m = re.match(r"^C (0x[0-9a-fA-F]{4}) ", ln)
            if m:
                d.add(int(m.group(1), 16))
    return d


def main():
    asm, notes, carpeta = sys.argv[1:4]
    resto = [a for a in sys.argv[4:] if not a.startswith("--")]
    minimo = int(resto[0]) if resto else 6
    tramo = None
    if "--tramo" in sys.argv:
        i = sys.argv.index("--tramo")
        tramo = (int(sys.argv[i + 1], 0), int(sys.argv[i + 2], 0))

    marcadas = comentadas(notes, carpeta)
    bloques, nombre, ini, instr = [], "(cabecera)", 0, []
    for ln in open(asm, encoding="utf-8").read().splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z_0-9]*):\s*(;.*)?$", ln)
        if m:
            if instr:
                bloques.append((nombre, ini, instr))
            nombre, ini, instr = m.group(1), 0, []
            continue
        m = re.match(r"^\t.*;([0-9a-f]{4})", ln)
        if not m:
            continue
        a = int(m.group(1), 16)
        if not ini:
            ini = a
        instr.append(a)
    if instr:
        bloques.append((nombre, ini, instr))
    bloques = [b for b in bloques if b[1]]
    if tramo:
        bloques = [b for b in bloques if tramo[0] <= b[1] <= tramo[1]]

    flojos = []
    tn = tc = 0
    for nom, a, ins in bloques:
        c = sum(1 for x in ins if x in marcadas)
        tn += len(ins)
        tc += c
        if len(ins) >= minimo and c * 100 // len(ins) < 10:
            flojos.append((nom, a, len(ins), c))
    for nom, a, n, c in sorted(flojos, key=lambda b: -b[2]):
        print("  %-34s 0x%04X  %3d instr  %2d comentarios  %2d %%"
              % (nom, a, n, c, c * 100 // n))
    print("  ---- %d rutinas por debajo del 10 %%, de %d"
          % (len(flojos), len(bloques)))
    print("  ---- en total: %d instrucciones, %d comentarios, %.1f %%"
          % (tn, tc, 100.0 * tc / tn if tn else 0))


main()
