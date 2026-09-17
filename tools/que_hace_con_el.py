#!/usr/bin/env python3
"""Para cada hueco, el codigo que lo carga y QUE HACE justo despues.

Saber quien carga un bloque no basta para identificarlo: lo que lo identifica
es lo que viene detras de la carga. Un `call` al descompresor dice que esta
comprimido; un `ldir` dice que se copia tal cual; un bucle que lee de (hl) con
un contador dice que es una lista.

Asi que esto junta las dos cosas en una linea por hueco: quien lo carga y las
instrucciones siguientes, que es lo que hay que leer.

Uso: que_hace_con_el.py <listado.asm> <huecos.txt> [cuantas]
"""
import re
import sys

CARGA = re.compile(r"\bld\s+(hl|de|bc|ix|iy),\s*0([0-9a-f]{4})h\b", re.I)
DIR = re.compile(r";([0-9a-f]{4})")


def main():
    lineas = []
    with open(sys.argv[1], encoding="utf-8") as f:
        for ln in f:
            m = DIR.search(ln)
            if m and not ln.lstrip().startswith(("defb", "defw", ";")):
                lineas.append((int(m.group(1), 16), ln.split(";")[0].strip()))

    cuantas = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    huecos = []
    for ln in open(sys.argv[2], encoding="utf-8"):
        a, b = ln.split()
        huecos.append((int(a, 16), int(b, 16)))

    # indice de la linea que carga cada constante
    cargas = []
    for i, (dirr, txt) in enumerate(lineas):
        m = CARGA.search(txt)
        if m:
            cargas.append((int(m.group(2), 16), i, m.group(1)))

    for ini, fin in huecos:
        print(f"\n0x{ini:04X}..0x{fin:04X}  ({fin - ini + 1} bytes)")
        dentro = [(v, i, r) for v, i, r in cargas if ini <= v <= fin]
        if not dentro:
            print("   nadie lo carga con una constante")
            continue
        for v, i, r in dentro[:4]:
            desde = lineas[i][0]
            sigue = " / ".join(t for _, t in lineas[i + 1:i + 1 + cuantas])
            print(f"   0x{desde:04X}  ld {r},0x{v:04X}  ->  {sigue}")


if __name__ == "__main__":
    main()
