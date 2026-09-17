#!/usr/bin/env python3
"""Ejecuta el descompresor del cartucho para medir donde acaba cada bloque.

Los bloques graficos no llevan escrito su tamano en ninguna parte: acaban
cuando el descompresor decide parar. Asi que no se estima: se ejecuta el mismo
algoritmo que ejecuta el Z80, y el byte en el que se para ES el final.

El descompresor son tres puertas (0x45C9, 0x45CD, 0x45D1):

    L_45C9  ld e,(hl) / inc hl / ld d,(hl) / inc hl   DE = destino en VRAM
    L_45CD  di / call L_45EC                          SETWRT DE
    L_45D1  ld a,(hl) / and 07fh / ld c,a             C = la cuenta, 7 bits
            ld a,(hl) / inc hl
            jr nz,L_45DE                              cuenta != 0 -> un tramo
            cp c                                      cuenta == 0:
            jr nz,L_45C9                                 0x80 -> otro destino
            ei / ret                                     0x00 -> FIN
    L_45DE  ld b,000h / cp c / push af
            call nz,L_457B                            bit 7 PUESTO -> literal
            pop af / call z,L_4573                    bit 7 a CERO  -> repetir
            di / jr L_45D1

O sea, y esto es al reves de lo que parece a primera vista:

    0nnnnnnn  b     REPITE el byte b, n veces   (L_4573: un `out` en bucle)
    1nnnnnnn  b*n   COPIA n bytes tal cual      (L_457B: `djnz` leyendo)
    0x80            fin del tramo; detras viene otro destino de VRAM
    0x00            fin del bloque entero

Las dos puertas de entrada se distinguen en el listado: quien llama a 0x45C9
trae HL apuntando al destino (el bloque lo lleva pegado delante); quien llama a
0x45CD trae el destino ya puesto en DE y HL en los datos.

Uso: rle.py <rom> <org> <listado.asm>          (lee los arranques del listado)
     rle.py <rom> <org> --desde 0x61BA [0x45C9|0x45CD]
"""
import re
import sys

ORG_POR_DEFECTO = 0x4000
CON_CABECERA = 0x45C9      # el bloque trae el destino de VRAM delante
SIN_CABECERA = 0x45CD      # el destino llega en DE


def descomprime(rom, org, ini, con_cabecera=True):
    """Recorre el bloque como lo recorre el cartucho.

    Devuelve (fin, tramos) con tramos = [(destino_vram, bytes_escritos)], o
    (None, ...) si el bloque no cierra dentro del cartucho.
    """
    p = ini - org
    tramos = []
    destino = None
    salida = bytearray()
    leer_destino = con_cabecera
    while 0 <= p < len(rom):
        if leer_destino:
            if p + 1 >= len(rom):
                return None, tramos
            if salida:
                tramos.append((destino, bytes(salida)))
                salida = bytearray()
            destino = rom[p] | (rom[p + 1] << 8)
            p += 2
            leer_destino = False
            continue
        ctrl = rom[p]
        p += 1
        cuenta = ctrl & 0x7F
        if cuenta == 0:
            if ctrl == 0x00:                     # fin del bloque entero
                if salida:
                    tramos.append((destino, bytes(salida)))
                return org + p, tramos
            leer_destino = True                  # 0x80: otro destino de VRAM
            continue
        if ctrl & 0x80:                          # copia literal
            salida += rom[p:p + cuenta]
            p += cuenta
        else:                                    # repeticion
            if p >= len(rom):
                return None, tramos
            salida += bytes([rom[p]]) * cuenta
            p += 1
    return None, tramos


def arranques_del_listado(path):
    """Las constantes cargadas en HL (o en DE) antes de llamar al descompresor.

    No se eligen a ojo: las dice el codigo. Para 0x45CD el destino de VRAM
    viene en DE, asi que se apunta tambien el ultimo `ld de,`.
    """
    carga_hl = re.compile(r"\bld\s+hl,\s*0([0-9a-f]{4})h\b", re.I)
    carga_de = re.compile(r"\bld\s+de,\s*0([0-9a-f]{4})h\b", re.I)
    llama = re.compile(r"\b(?:call|jp)\s+(?:[a-z]{1,2},\s*)?L_([0-9A-F]{4})\b")
    dir_de_linea = re.compile(r";([0-9a-f]{4})")
    out, hl, de, dir_hl = [], None, None, None
    for ln in open(path, encoding="utf-8"):
        m = carga_hl.search(ln)
        if m:
            hl = int(m.group(1), 16)
            d = dir_de_linea.search(ln)
            dir_hl = int(d.group(1), 16) if d else None
            continue
        m = carga_de.search(ln)
        if m:
            de = int(m.group(1), 16)
            continue
        m = llama.search(ln)
        if m:
            destino = int(m.group(1), 16)
            if destino in (CON_CABECERA, SIN_CABECERA) and hl is not None:
                out.append((hl, dir_hl, destino, de))
            if destino not in (CON_CABECERA, SIN_CABECERA):
                pass
            hl = None
    return out


def main():
    rom = open(sys.argv[1], "rb").read()
    org = int(sys.argv[2], 0)
    if sys.argv[3] == "--desde":
        ini = int(sys.argv[4], 0)
        puerta = int(sys.argv[5], 0) if len(sys.argv) > 5 else CON_CABECERA
        fin, tramos = descomprime(rom, org, ini, puerta == CON_CABECERA)
        print(f"0x{ini:04X} -> {'0x%04X' % fin if fin else 'NO CIERRA'}")
        for d, c in tramos:
            print(f"   VRAM 0x{d:04X}  {len(c)} bytes")
        return

    vistos = {}
    for ini, desde, puerta, de in arranques_del_listado(sys.argv[3]):
        if not (org <= ini < org + len(rom)):
            continue
        vistos.setdefault((ini, puerta), []).append((desde, de))

    print(f"# {len(vistos)} arranques de bloque comprimido sacados del listado")
    for (ini, puerta) in sorted(vistos):
        fin, tramos = descomprime(rom, org, ini, puerta == CON_CABECERA)
        quien = ", ".join(f"0x{d:04X}" for d, _ in vistos[(ini, puerta)] if d)
        if fin is None:
            print(f"# 0x{ini:04X} (por 0x{puerta:04X}, desde {quien}): NO CIERRA")
            continue
        total = sum(len(c) for _, c in tramos)
        destinos = " ".join(f"0x{d:04X}" % () if d is not None else "?"
                            for d, _ in tramos)
        print(f"D 0x{ini:04x} 0x{fin:04x} bloque_0x{ini:04X}  "
              f"{fin - ini} bytes comprimidos -> {total} en VRAM "
              f"({len(tramos)} tramos: {destinos}); lo carga {quien}")


if __name__ == "__main__":
    main()


# ----------------------------------------------------------------------
# EL SEGUNDO DESCOMPRESOR: el que descarga a RAM (0x6A51)
# ----------------------------------------------------------------------
# Mismo lenguaje que el de VRAM pero sin cabecera de destino -el destino es
# fijo, 0xE280- y con el fin marcado por un 0x00:
#
#     L_6A51  ld de,0e280h
#     L_6A54  ld a,(hl) / inc hl / or a / ret z        0x00 -> FIN
#             jp m,L_6A64                              bit 7 -> copia literal
#             ld b,a / ld a,(hl) / inc hl
#     L_6A5E  ld (de),a / inc de / djnz L_6A5E         repetir
#             jr L_6A54
#     L_6A64  and 07fh / ld c,a / ld b,000h / ldir     copiar n bytes
#             jr L_6A54
#
# Y sus dos envoltorios, 0x6A33 y 0x6A42, lo llaman EN BUCLE: descomprimen un
# trozo, lo pintan, y si el byte siguiente no es cero vuelven a empezar. Por
# eso una cadena termina en un 0x00 de mas, el que corta el bucle.

def descomprime_ram(rom, org, ini):
    """Un solo trozo. Devuelve (fin, bytes_producidos) o (None, ...)."""
    p = ini - org
    salida = bytearray()
    while 0 <= p < len(rom):
        ctrl = rom[p]
        p += 1
        if ctrl == 0x00:
            return org + p, bytes(salida)
        if ctrl & 0x80:
            n = ctrl & 0x7F
            salida += rom[p:p + n]
            p += n
        else:
            if p >= len(rom):
                return None, bytes(salida)
            salida += bytes([rom[p]]) * ctrl
            p += 1
    return None, bytes(salida)


def cadena_ram(rom, org, ini, tope=64):
    """El bucle de 0x6A33 / 0x6A42: trozos hasta que el byte siguiente es 0.

    Devuelve (fin, [bytes de cada trozo]).
    """
    p, trozos = ini, []
    while len(trozos) < tope:
        f, datos = descomprime_ram(rom, org, p)
        if f is None:
            return None, trozos
        trozos.append(datos)
        p = f
        if p - org >= len(rom):
            return None, trozos
        if rom[p - org] == 0x00:      # `ld a,(hl) / or a / jr nz` -> se acaba
            return p + 1, trozos
    return None, trozos
