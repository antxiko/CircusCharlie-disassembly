#!/usr/bin/env python3
"""Compara la VRAM que monta graficos.py con la que vuelca el emulador.

Mirar el dibujo no basta: dos imagenes pueden parecerse y tener las tablas
distintas. Esto compara BYTE A BYTE las cuatro tablas -patrones, color,
nombres y patrones de sprite- contra los volcados de tools/omsx_vram.tcl, y
dice en cual y en cuantos bytes se diferencian.

Los sprites en movimiento y el marcador cambian cada cuadro, asi que la tabla
de ATRIBUTOS de sprite (0x3B00) no se compara: lo que se compara es el
decorado, que es lo que graficos.py dice reproducir.

LAS DOS PANTALLAS, Y NO SON LA MISMA. Costo una tanda de imagenes malas
confundirlas:

    presentacion  la pantalla de LA CASA: el logotipo de KONAMI subiendo y el
                  rotulo "- VIDEO CARTRIDGE -". Es la escena 2.
    seleccion     la pantalla de TITULO de verdad, la del menu: "PLAY SELECT",
                  las cuatro opciones, el "(c) 1984" y el cursor. Es la que
                  sale despues de que la cortina tape el logotipo.

Las dos comparten decorado -mismos patrones y mismo color, cero bytes de
diferencia-: lo unico que cambia entre ellas es la tabla de nombres.

Uso: coteja_vram.py <rom> <vram.bin> <escena>
     escena: presentacion | seleccion | seleccion-sin-cursor
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graficos

TABLAS = (
    ("COLOR    ", 0x0000, 0x1800),
    ("SPR PATR ", 0x1800, 0x2000),
    ("PATRONES ", 0x2000, 0x3800),
    ("NOMBRES  ", 0x3800, 0x3B00),
)


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    rom = open(sys.argv[1], "rb").read()
    real = open(sys.argv[2], "rb").read()
    escena = sys.argv[3]
    monta = {
        "presentacion": graficos.vram_de_la_presentacion,
        "seleccion": graficos.vram_de_la_seleccion,
        "seleccion-sin-cursor":
            lambda r: graficos.vram_de_la_seleccion(r, cursor=False),
    }
    if escena not in monta:
        print("  escena desconocida: %s (hay %s)"
              % (escena, ", ".join(sorted(monta))))
        return 2
    mio = monta[escena](rom).b

    print("  %s contra %s" % (escena, os.path.basename(sys.argv[2])))
    print("  " + "-" * 58)
    total = 0
    for nombre, ini, fin in TABLAS:
        d = [a for a in range(ini, fin) if mio[a] != real[a]]
        total += len(d)
        n = fin - ini
        marca = "OK" if not d else "%d de %d (%.1f %%)" % (
            len(d), n, 100.0 * len(d) / n)
        print("  %s 0x%04X..0x%04X  %s" % (nombre, ini, fin - 1, marca))
        if d:
            print("       primeros: %s" % " ".join("0x%04X" % a for a in d[:8]))
    print("  " + "-" * 58)
    print("  %d bytes distintos" % total)
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
