#!/usr/bin/env python3
"""Mete en el .notes los comentarios que las tandas dejaron en work/coment/.

Cada tanda es un fichero de lineas `C 0xADDR texto` (y `B 0xADDR texto`) que se
escribio APARTE, contra un tramo de direcciones, para poder repartir el trabajo
sin que dos manos se pisen el mismo fichero. Esto los junta, los valida contra
el listado y los deja en el .notes, que es de donde se genera el .asm.

Admite las tres directivas que una tanda puede traer: C (comentario de linea),
B (cabecera de bloque) y L (bautizar una rutina).

Lo que se rechaza, y por que:
  - direccion que no es el principio de una instruccion del .asm: un comentario
    de linea colgado de un `defb` no sale por ninguna parte
  - direccion que ya tiene comentario en el .notes: lo escrito a mano manda
  - direcciones repetidas entre tandas: se queda la primera
  - cabecera de bloque identica -misma direccion y mismo texto- a una que ya
    esta: el aplicador se corre varias veces por proyecto y sin esto vuelve a
    meter las mismas cada pasada. En Mopi Ranger habia 1.589 lineas de sobra
  - cabecera de bloque cuya direccion ya tiene cabecera: si no se filtran, cada
    pasada del aplicador vuelve a meter las mismas y el listado acaba con la
    misma cabecera repetida diez veces (paso de verdad en este cartucho)
  - lineas con caracteres no ASCII: el .notes es ASCII a proposito
  - etiqueta con un nombre que ya usa otra rutina: dos etiquetas iguales no
    ensamblan, y eso rompe la prueba de que el listado reproduce la ROM

Uso: aplica_comentarios.py <asm> <notes> <work/coment> [--escribe]
Sin --escribe solo dice lo que haria.
"""
import glob
import os
import re
import sys


# Una linea de cabecera que solo lleva guiones, iguales o almohadillas es un
# marco, no un texto: la misma raya se repite arriba y abajo a proposito, asi
# que esas no se filtran nunca.
DECORATIVA = re.compile(r"^[-=#*_~+.:\s]*$")


def direcciones_del_asm(asm):
    """Las direcciones que son principio de instruccion, con su texto."""
    d = {}
    for ln in open(asm, encoding="utf-8").read().splitlines():
        m = re.match(r"^\t(.*?);([0-9a-f]{4})(.*)$", ln)
        if m:
            d[int(m.group(2), 16)] = m.group(1).strip()
    return d


def main(argv):
    if len(argv) < 4:
        return print(__doc__) or 2
    asm, notes, carpeta = argv[1:4]
    escribe = "--escribe" in argv

    instr = direcciones_del_asm(asm)
    texto = open(notes, encoding="utf-8").read()
    ya = set()
    ya_etiq = set()
    ya_bloque = set()
    nombres = set()
    for ln in texto.splitlines():
        m = re.match(r"^C (0x[0-9a-fA-F]{4}) ", ln)
        if m:
            ya.add(int(m.group(1), 16))
        m = re.match(r"^B (0x[0-9a-fA-F]{4}) +(.*)$", ln)
        if m:
            ya_bloque.add((int(m.group(1), 16), m.group(2).rstrip()))
        m = re.match(r"^L (0x[0-9a-fA-F]{4}) +(\S+)", ln)
        if m:
            ya_etiq.add(int(m.group(1), 16))
            nombres.add(m.group(2))

    nuevas, visto, vistos_nombres = [], set(), set()
    n_fuera = n_ya = n_dup = n_mal = n_nom = 0
    for fn in sorted(glob.glob(os.path.join(carpeta, "*.notes"))):
        cuenta = 0
        for ln in open(fn, encoding="utf-8").read().splitlines():
            ln = ln.rstrip()
            m = re.match(r"^([CBL]) (0x[0-9a-fA-F]{4}) +(.+)$", ln)
            if not m:
                continue
            try:
                ln.encode("ascii")
            except UnicodeEncodeError:
                n_mal += 1
                continue
            dire, cuerpo = int(m.group(2), 16), m.group(3)
            if m.group(1) == "C":
                if dire not in instr:
                    n_fuera += 1
                    continue
                if dire in ya:
                    n_ya += 1
                    continue
                if dire in visto:
                    n_dup += 1
                    continue
                visto.add(dire)
            elif m.group(1) == "B":
                clave = (dire, cuerpo.rstrip())
                if clave in ya_bloque and not DECORATIVA.match(cuerpo):
                    n_ya += 1
                    continue
                ya_bloque.add(clave)
            elif m.group(1) == "L":
                nombre = cuerpo.split()[0]
                if dire not in instr:
                    n_fuera += 1
                    continue
                if dire in ya_etiq or dire in vistos_nombres:
                    n_ya += 1
                    continue
                if nombre in nombres:
                    n_nom += 1
                    continue
                nombres.add(nombre)
                vistos_nombres.add(dire)
            nuevas.append("%s 0x%04x %s" % (m.group(1), dire, cuerpo))
            cuenta += 1
        print("  %-28s %4d" % (os.path.basename(fn), cuenta))

    print("  ---- %d lineas nuevas" % len(nuevas))
    for n, q in (("no son instruccion", n_fuera), ("ya comentadas", n_ya),
                 ("repetidas entre tandas", n_dup), ("con acentos", n_mal),
                 ("con un nombre de etiqueta ya usado", n_nom)):
        if q:
            print("  ---- %d descartadas: %s" % (q, n))

    if not escribe:
        print("  (en seco: pasa --escribe para dejarlo en el .notes)")
        return 0

    cabecera = ("\n\n# ======================================================"
                "================\n# COMENTARIOS DE LINEA\n"
                "# ======================================================"
                "================\n")
    with open(notes, "a", encoding="utf-8", newline="\n") as f:
        f.write(cabecera + "\n".join(nuevas) + "\n")
    print("  escritas en %s" % notes)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
