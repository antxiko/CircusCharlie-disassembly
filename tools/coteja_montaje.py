#!/usr/bin/env python3
"""Coteja las cinco atracciones montadas desde la ROM contra la VRAM real.

La VRAM real es la que tools/omsx_montaje.tcl vuelca en 0x4C3C, la instruccion
que sigue al `call monta_el_decorado_de_la_fase` de 0x4C39: el decorado
entero, el marcador ya pintado y el juego todavia sin mover nada. Contra ese
estado, lo que monta tools/graficos.py tiene que dar CERO en la tabla de
color, en la de patrones, en los patrones de sprite y en la tabla de nombres.
Los atributos de sprite (0x3B00..0x3B80) no se cotejan: a esa altura llevan
lo que dejo el menu, y el montaje no los toca.

Los valores del marcador -vidas, fase, bonificacion- se leen del
info_tipo_N.txt de cada volcado, no se suponen.

Uso: coteja_montaje.py <rom> [carpeta de los volcados]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graficos as G                                       # noqa: E402

REGIONES = (("color", 0x0000, 0x1800), ("sprites", 0x1800, 0x2000),
            ("patrones", 0x2000, 0x3800), ("nombres", 0x3800, 0x3B00))


def info(ruta):
    d = {}
    for linea in open(ruta, encoding="utf-8"):
        partes = linea.split()
        if len(partes) == 2 and partes[1].lstrip("-").isdigit():
            d[partes[0]] = int(partes[1])
    return d


def coteja(rom, carpeta, tipo):
    """(distintos por region, detalle) para un tipo; None si no hay volcado."""
    vol = os.path.join(carpeta, "vram_tipo_%d.bin" % tipo)
    if not os.path.exists(vol):
        return None, None
    d = open(vol, "rb").read()
    i = info(os.path.join(carpeta, "info_tipo_%d.txt" % tipo))
    v = G.vram_de_la_atraccion(rom, tipo)
    G.pinta_el_marcador(v, rom, vidas=i.get("vidas", 2),
                        fase_bcd=i.get("fase_bcd", 1),
                        bonificacion=(i.get("bonificacion_alto", 0x80),
                                      i.get("bonificacion_bajo", 0x00)))
    dif = {n: sum(1 for k in range(a, b) if v.b[k] != d[k])
           for n, a, b in REGIONES}
    detalle = []
    for n, a, b in REGIONES:
        malos = sorted(set((k - a) // 8 for k in range(a, b) if v.b[k] != d[k]))
        if malos:
            detalle.append("%s: %s" % (n, ", ".join("%04X" % (a + m * 8)
                                                   for m in malos[:10])))
    return dif, detalle


def main():
    rom = open(sys.argv[1], "rb").read()
    carpeta = sys.argv[2] if len(sys.argv) > 2 else "work/montaje"
    total, vistos = 0, 0
    for tipo, nombre in enumerate(G.ATRACCIONES):
        dif, detalle = coteja(rom, carpeta, tipo)
        if dif is None:
            print("  tipo %d %-13s sin volcado (make montaje)" % (tipo, nombre))
            continue
        vistos += 1
        n = sum(dif.values())
        total += n
        print("  tipo %d %-13s %5d bytes distintos  %s" % (tipo, nombre, n, dif))
        for linea in detalle:
            print("       ", linea)
    if not vistos:
        print("  no hay volcados en %s" % carpeta)
        return 2
    print("  %d atracciones cotejadas, %d bytes distintos en total" % (vistos, total))
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
