#!/usr/bin/env python3
"""EL CARTUCHO EN PYTHON CONTRA openMSX, cuadro a cuadro.

tools/corre_circus.py ejecuta el cartucho; tools/omsx_arranque.tcl vuelca la
VRAM y la RAM de openMSX en 0x4C3C (el montaje) y en los vuelcos de sprites
(0x4CA9) de los cuadros 1, 2, 3, 5, 10, 25, 50, 100 y 200. Aqui se toman las
dos fotos EN EL MISMO INSTANTE -al entrar en esas direcciones- y se exige
CERO bytes de diferencia en los 16 KB de VRAM, en las cinco atracciones.

Un ajuste, y solo uno: el contador de cuadros (0xE003) se iguala al de openMSX
al acabar el montaje. openMSX pasa por la BIOS y por el menu un numero de
cuadros distinto, y de ese contador cuelgan la cuenta atras del BONUS y el
paso del caballo. La RAM que sigue distinta es la musica (0xE01A-0xE030) y la
cortinilla del menu (0xE00E/F), que no tocan la pantalla.

    python3 tools/coteja_arranque.py circus.rom work/arranque
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from corre_circus import Circus, MONTADA, VUELCA_LOS_SPRITES  # noqa: E402

CUADROS = [1, 2, 3, 5, 10, 25, 50, 100, 200]


def main():
    rom = open(sys.argv[1], "rb").read()
    carpeta = sys.argv[2]
    malos = 0
    for tipo in range(5):
        ram0 = open(os.path.join(carpeta, "tipo_%d_c000.ram" % tipo), "rb").read()
        m = Circus(rom)
        m.tipo = tipo
        m.arranca()
        est = {"n": -1, "fotos": {}}

        def montada(z):
            z.mem[0xE003] = ram0[3]
            est["n"] = 0
            est["fotos"][0] = bytes(z.vdp.vram)

        def vuelca(z):
            if est["n"] < 0:
                return
            est["n"] += 1
            if est["n"] in CUADROS:
                est["fotos"][est["n"]] = bytes(z.vdp.vram)

        m.paradas[MONTADA] = montada
        m.paradas[VUELCA_LOS_SPRITES] = vuelca
        f = 0
        while est["n"] < CUADROS[-1]:
            m.espacio = (f % 100) < 20 and est["n"] < 0
            m.cuadro()
            f += 1
        linea = []
        for k, v in sorted(est["fotos"].items()):
            ref = open(os.path.join(carpeta, "tipo_%d_c%03d.vram" % (tipo, k)), "rb").read()
            d = sum(1 for i in range(0x4000) if v[i] != ref[i])
            malos += d
            linea.append("c%d:%d" % (k, d))
        print("tipo %d  %s" % (tipo, "  ".join(linea)))
    print("TOTAL %d bytes distintos" % malos)
    sys.exit(1 if malos else 0)


if __name__ == "__main__":
    main()
