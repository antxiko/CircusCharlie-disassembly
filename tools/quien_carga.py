#!/usr/bin/env python3
"""Quien CARGA cada hueco, leyendo el listado y no la ROM cruda.

apunta_a.py busca la palabra de 16 bits en todo el binario, y en un cartucho de
32 KB eso devuelve decenas de coincidencias por hueco: cualquier pareja de
bytes vale. Aqui solo cuentan las instrucciones que el trazado dio por codigo y
que de verdad cargan una direccion —`ld hl,`, `ld de,`, `ld bc,`, `ld ix,`,
`ld iy,`, `ld (nn),`, `ld a,(nn)`, `call` y `jp`—, asi que lo que sale es quien
usa el bloque, no quien se le parece.

De cada hueco se dice cuantas cargas lo apuntan y desde donde. Un hueco con
CERO cargas es la senal de que lo lee una tabla de punteros, no el codigo: ahi
hay que tirar de apunta_a.py.

Uso: quien_carga.py <listado.asm> <ini> <fin> [<ini> <fin> ...]
     quien_carga.py <listado.asm> --presupuesto   (lee los rangos por la entrada)
"""
import re
import sys

CARGA = re.compile(
    r"^\s+(ld (?:hl|de|bc|ix|iy),|ld a,\(|ld \(|call (?:\w+,)?|jp (?:\w+,)?)"
    r"0?([0-9a-f]{4})h")
PC = re.compile(r";([0-9a-f]{4})")


def cargas(listado):
    """[(valor, direccion_de_la_instruccion, mnemonico)] de todo el listado."""
    out = []
    for ln in open(listado, encoding="utf-8", errors="replace"):
        m = CARGA.match(ln)
        if not m:
            continue
        pc = PC.search(ln)
        out.append((int(m.group(2), 16), int(pc.group(1), 16) if pc else 0,
                    m.group(1).strip().rstrip(",")))
    return out


def rangos_por_la_entrada():
    """Los rangos que imprime presupuesto.py: '0xAAAA..0xBBBB  (n bytes)'."""
    out = []
    for ln in sys.stdin:
        m = re.search(r"0x([0-9A-Fa-f]{4})\.\.0x([0-9A-Fa-f]{4})", ln)
        if m:
            out.append((int(m.group(1), 16), int(m.group(2), 16) + 1))
    return out


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    todas = cargas(sys.argv[1])
    if sys.argv[2] == "--presupuesto":
        rangos = rangos_por_la_entrada()
    else:
        v = [int(x, 0) for x in sys.argv[2:]]
        rangos = list(zip(v[::2], v[1::2]))
    for a, b in rangos:
        hits = sorted(t for t in todas if a <= t[0] < b)
        print("0x%04X..0x%04X  (%5d B)  %d cargas" % (a, b - 1, b - a, len(hits)))
        for val, pc, mn in hits[:12]:
            print("      0x%04X  <-  0x%04X  %s" % (val, pc, mn))
        if len(hits) > 12:
            print("      ... y %d mas" % (len(hits) - 12))


if __name__ == "__main__":
    main()
