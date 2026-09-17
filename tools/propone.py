#!/usr/bin/env python3
"""Propone que es cada hueco del presupuesto PROBANDO a ejecutarlo.

Un hueco que empieza donde empieza un bloque comprimido y acaba justo donde
empieza el siguiente trozo conocido no es una coincidencia: el descompresor
del cartucho consume exactamente esos bytes y se para en el borde. Lo mismo
con el interprete de guiones.

Asi que esto coge cada rango que el presupuesto deja sin asignar y prueba las
dos maquinas del cartucho desde su primer byte. Solo propone lo que CIERRA en
el borde del hueco; lo que no cierre se queda sin proponer, que es la
respuesta honesta.

Uso: propone.py <rom> <org> <huecos.txt>
"""
import sys

from rle import descomprime, CON_CABECERA
from guiones import ejecuta as ejecuta_guion


def main():
    rom = open(sys.argv[1], "rb").read()
    org = int(sys.argv[2], 0)
    huecos = []
    for ln in open(sys.argv[3], encoding="utf-8"):
        a, b = ln.split()
        huecos.append((int(a, 16), int(b, 16) + 1))

    for ini, fin in huecos:
        largo = fin - ini
        propuestas = []

        for con_cab, nombre in ((True, "comprimido"), (False, "comprimido sin cabecera")):
            f, tramos = descomprime(rom, org, ini, con_cab)
            if f == fin:
                total = sum(len(c) for _, c in tramos)
                d = " ".join(f"0x{x:04X}" for x, _ in tramos if x is not None)
                propuestas.append(f"{nombre}: cierra CLAVADO, {total} bytes a VRAM ({d})")

        f, tramos = ejecuta_guion(rom, org, ini)
        if f == fin:
            total = sum(len(c) for _, c in tramos)
            d = " ".join(f"0x{x:04X}" for x, _ in tramos)
            propuestas.append(f"guion: cierra CLAVADO, {len(tramos)} tramos, {total} a VRAM ({d})")

        # Encadenado: varios guiones o bloques seguidos que llenan el hueco.
        for maquina, nombre in ((lambda p: descomprime(rom, org, p, True), "comprimidos"),
                                (lambda p: ejecuta_guion(rom, org, p), "guiones")):
            p, n, cortes = ini, 0, []
            while p is not None and p < fin and n < 40:
                cortes.append(p)
                p, _ = maquina(p)
                n += 1
            if p == fin and n > 1:
                propuestas.append(f"{n} {nombre} seguidos: " +
                                  " ".join(f"0x{c:04X}" for c in cortes))

        print(f"0x{ini:04X}..0x{fin - 1:04X} ({largo} bytes)")
        for p in propuestas:
            print(f"    {p}")
        if not propuestas:
            print("    -")


if __name__ == "__main__":
    main()
