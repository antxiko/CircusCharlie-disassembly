"""COTEJO DE LAS ATRACCIONES EN PISTA contra openMSX.

tools/pista.py dibuja cada atraccion cuadro a cuadro desde las tablas del
cartucho. Aqui se compara, en cada cuadro que volco tools/omsx_arranque.tcl
(work/arranque/tipo_N_cK.{ram,vram}, en el vuelco de sprites de 0x4CA9 y sin
tocar el mando):

  - la RAM de estado: la posicion en la pista y el bonus (0xE055-0xE05A), y
    todo lo que va de 0xE0B0 a 0xE27F -bufer de sprites, jugador, moviles,
    recogibles, el suelto, las figuras del trapecio, la cola del caballo-;
  - la VRAM hasta 0x3B00: patrones, colores y tabla de nombres;
  - la tabla de sprites (0x3B00), que en ese instante es la del cuadro
    ANTERIOR: el vuelco de 0x4CA9 aun no se ha hecho. Por eso en el cuadro 1
    no se mira: ahi todavia esta la del menu.

Un ajuste, el mismo que en tools/coteja_arranque.py: el reloj de cuadros
(0xE003) se toma del volcado del montaje, porque lo pone el tiempo que se
pasara en el menu y no la ROM.

Cada tipo se mira hasta el ultimo cuadro volcado ANTES de que Charlie se
estrelle: pista.py dibuja la atraccion sin tocar el mando, y lo que pasa
despues del choque no esta pasado a Python.

    python3 tools/coteja_pista.py circus.rom [work/arranque]
Sale con 0 si todo da cero bytes de diferencia.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pista as P               # noqa: E402

CUADROS = (1, 2, 3, 5, 10, 25, 50, 100, 200)

# El primer cuadro en que el jugador ya no esta en su estado de partida, por
# el Z80 de cotejo (tools/corre_circus.py): el trapecio no se cae sin mando,
# el leon choca con un aro en el 398, la cuerda floja en el 200, las bolas en
# el 352 y el caballo en el 114.
CHOQUE = (10000, 398, 200, 352, 114)

ZONAS = ((0xE055, 0xE05B), (0xE0B0, 0xE280))


def coteja(rom, dir_, tipo):
    ram0 = open(os.path.join(dir_, "tipo_%d_c000.ram" % tipo), "rb").read()
    p = P.Pista(rom, tipo, reloj=ram0[3])
    anterior = p.sprites()
    fallos = 0
    hechos = 0
    for k in range(1, max(CUADROS) + 1):
        if k >= CHOQUE[tipo]:
            break
        if k > 1:
            p.tras_el_vuelco()
        sat = anterior
        p.cuadro()
        anterior = p.sprites()
        if k not in CUADROS:
            continue
        base = os.path.join(dir_, "tipo_%d_c%03d" % (tipo, k))
        ram = open(base + ".ram", "rb").read()
        vram = open(base + ".vram", "rb").read()
        dr = [a for lo, hi in ZONAS for a in range(lo, hi)
              if p[a] != ram[a - 0xE000]]
        dv = [a for a in range(0x3B00) if p.vram[a] != vram[a]]
        # en el cuadro 1 la tabla de sprites aun es la del menu
        ds = [i for i in range(0x80) if k > 1 and sat[i] != vram[0x3B00 + i]]
        hechos += 1
        if dr or dv or ds:
            fallos += 1
            print("  tipo %d cuadro %d: RAM %d, VRAM %d, sprites %d"
                  % (tipo, k, len(dr), len(dv), len(ds)))
            for a in dr[:8]:
                print("     RAM  %04X: %02X, openMSX %02X"
                      % (a, p[a], ram[a - 0xE000]))
            for a in dv[:8]:
                print("     VRAM %04X: %02X, openMSX %02X"
                      % (a, p.vram[a], vram[a]))
    return hechos, fallos


def main():
    rom = open(sys.argv[1], "rb").read()
    dir_ = sys.argv[2] if len(sys.argv) > 2 else "work/arranque"
    total = 0
    for tipo in range(5):
        hechos, fallos = coteja(rom, dir_, tipo)
        total += fallos
        print("tipo %d (%s): %d cuadros, %s"
              % (tipo, P.G.ATRACCIONES[tipo], hechos,
                 "CERO bytes de diferencia" if not fallos
                 else "%d con diferencias" % fallos))
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
