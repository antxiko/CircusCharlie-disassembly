#!/usr/bin/env python3
"""Mide donde acaba cada guion de rotulos EJECUTANDO el interprete que lo lee.

El presupuesto exige que todo byte del cartucho este explicado, y adivinar
donde acaba un bloque produce rangos convincentes que no son nada. Aqui no se
adivina: el cartucho trae su propio interprete y se ejecuta.

El interprete de Circus Charlie son tres puertas a la misma rutina, y el guion
le llega en HL (al reves que en Ping Pong, donde llegaba en DE):

    L_4062  ld c,000h / jr L_4068     la mascara 0x00: escribe CEROS, o sea
                                      BORRA el rotulo reutilizando su guion
    L_4066  ld c,0ffh                 la mascara 0xFF: lo pinta tal cual
    L_4068  ld e,(hl) / inc hl / ld d,(hl) / inc hl
                                      DE = destino en VRAM, HL = el guion + 2
    L_406C  ld a,(hl) / inc hl
            ld b,a / inc b / ret z    byte 0xFF -> FIN del guion
            inc b / jr z,L_4068       byte 0xFE -> otro destino de VRAM
            and c                     la mascara
            call L_4010               escribe A en la VRAM que apunta DE
            inc de
            jr L_406C

O sea que el formato es: [destino VRAM, word] [bytes...] con dos codigos de
control, 0xFE para saltar a otro destino y 0xFF para terminar. Ejecutando eso
desde cada arranque salen los bytes consumidos EXACTOS.

Los arranques no se eligen a ojo: se sacan del listado, buscando las
constantes que el codigo carga en HL justo antes de llamar al interprete.

Uso: guiones.py <rom> <org> <listado.asm> [--textos]
"""
import re
import sys

ORG_POR_DEFECTO = 0x4000
INTERPRETES = (0x4062, 0x4066, 0x4068)

# Los bytes que el guion escribe en la VRAM son indices de patron. Si la fuente
# del cartucho esta ordenada como el ASCII a partir del espacio, el indice 0 es
# el espacio (0x20). Con --textos se aplica ese desplazamiento para LEER el
# rotulo; es una lectura tentativa hasta que el dibujo de la fuente lo
# confirme, y por eso no va en el modo normal.
DESPLAZAMIENTO_FUENTE = 0x20


def lee_listado(path):
    """Los arranques ciertos: la constante cargada en HL antes de llamar."""
    carga = re.compile(r"\bld\s+hl,\s*0([0-9a-f]{4})h\b", re.I)
    llama = re.compile(r"\b(?:call|jp)\s+(?:[a-z]{1,2},\s*)?(?:L_)?0?([0-9A-Fa-f]{4})h?\b")
    arranques = []
    ultimo_hl = None
    ultima_dir = None
    for ln in open(path, encoding="utf-8"):
        m = carga.search(ln)
        if m:
            ultimo_hl = int(m.group(1), 16)
            d = re.search(r";([0-9a-f]{4})\s*$", ln.split(";")[1] if ";" in ln else "")
            ultima_dir = re.search(r";([0-9a-f]{4})", ln)
            ultima_dir = int(ultima_dir.group(1), 16) if ultima_dir else None
            continue
        m = llama.search(ln)
        if m and ultimo_hl is not None:
            destino = int(m.group(1), 16)
            if destino in INTERPRETES:
                arranques.append((ultimo_hl, ultima_dir, destino))
            ultimo_hl = None
    return arranques


def ejecuta(rom, org, ini):
    """Recorre un guion como lo recorre el cartucho. Devuelve (fin, tramos).

    tramos es la lista de (destino_vram, bytes) que el guion escribe.
    """
    p = ini - org
    tramos = []
    esperando_destino = True
    destino = None
    cuerpo = bytearray()
    while 0 <= p < len(rom):
        if esperando_destino:
            if p + 1 >= len(rom):
                return None, tramos
            destino = rom[p] | (rom[p + 1] << 8)
            p += 2
            esperando_destino = False
            cuerpo = bytearray()
            continue
        b = rom[p]
        p += 1
        if b == 0xFF:                      # fin del guion
            if cuerpo:
                tramos.append((destino, bytes(cuerpo)))
            return org + p, tramos
        if b == 0xFE:                      # otro destino de VRAM
            if cuerpo:
                tramos.append((destino, bytes(cuerpo)))
            esperando_destino = True
            continue
        cuerpo.append(b)
    return None, tramos


def main():
    rom = open(sys.argv[1], "rb").read()
    org = int(sys.argv[2], 0) if len(sys.argv) > 2 else ORG_POR_DEFECTO
    listado = sys.argv[3]
    textos = "--textos" in sys.argv

    vistos = {}
    for ini, desde, puerta in lee_listado(listado):
        if not (org <= ini < org + len(rom)):
            continue
        vistos.setdefault(ini, []).append((desde, puerta))

    print(f"# {len(vistos)} arranques de guion sacados del listado")
    for ini in sorted(vistos):
        fin, tramos = ejecuta(rom, org, ini)
        if fin is None:
            print(f"# 0x{ini:04X}: NO CIERRA (se sale del cartucho)")
            continue
        quien = ", ".join(f"0x{d:04X}" for d, _ in vistos[ini] if d)
        total = sum(len(c) for _, c in tramos)
        print(f"D 0x{ini:04x} 0x{fin:04x} guion_0x{ini:04X}  "
              f"{fin - ini} bytes, {len(tramos)} tramos, {total} bytes a la VRAM; "
              f"lo pinta {quien}")
        if textos:
            for destino, cuerpo in tramos:
                txt = "".join(
                    chr(b + DESPLAZAMIENTO_FUENTE) if 0 <= b + DESPLAZAMIENTO_FUENTE < 127 else "."
                    for b in cuerpo)
                print(f"#     VRAM 0x{destino:04X}  {len(cuerpo):3d}  |{txt}|")


if __name__ == "__main__":
    main()
