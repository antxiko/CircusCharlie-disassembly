#!/usr/bin/env python3
"""Anade al final de un fichero de texto, en UTF-8 y sin sorpresas.

Existe porque en esta maquina el `cat fichero >> destino` de Git Bash escribe
POR EL PRINCIPIO del destino en vez de por el final, y eso ya se ha comido dos
veces la cabecera del .notes. Con esto no pasa.

Uso: anexa.py <destino> <fichero a anadir> [<otro> ...]
"""
import sys

destino = sys.argv[1]
trozos = [open(f, encoding="utf-8").read() for f in sys.argv[2:]]
with open(destino, encoding="utf-8") as f:
    s = f.read()
with open(destino, "w", encoding="utf-8") as f:
    f.write(s + "\n" + "\n".join(trozos))
print("%s: %d bytes anadidos" % (destino, sum(len(t) for t in trozos)))
