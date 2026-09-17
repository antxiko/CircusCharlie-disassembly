#!/usr/bin/env python3
"""Quita del .notes las directivas C repetidas, dejando la primera.

Al comentar por tandas es facil volver a comentar una direccion ya comentada;
tools/valida_c.py las caza, y esto las limpia. Se queda la PRIMERA, que es la
que ya estaba y suele ser la mas pensada.

Uso: quita_repetidos.py <fichero.notes>
"""
import re
import sys

p = sys.argv[1]
vistos, fuera, out = set(), 0, []
for ln in open(p, encoding="utf-8"):
    m = re.match(r"^C (0x[0-9A-Fa-f]+)", ln)
    if m:
        a = int(m.group(1), 16)
        if a in vistos:
            fuera += 1
            continue
        vistos.add(a)
    out.append(ln)
open(p, "w", encoding="utf-8").writelines(out)
print("%s: %d comentarios repetidos fuera, quedan %d" % (p, fuera, len(vistos)))
