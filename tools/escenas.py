#!/usr/bin/env python3
"""Ejecuta la maquina de escenas del cartucho para medir donde acaba cada una.

Una "escena" -la pantalla de un nivel, el titulo, el menu- no es un bloque
comprimido y ya: es un guion que el cartucho recorre con tres rutinas
encadenadas, y solo ejecutandolo sale el numero de bytes exacto.

El bucle (0x6A42, y su gemelo 0x6A33) es:

    L_6A42  call L_6A51      descomprime un trozo al bufer de 0xE280
            call L_69D5      lee DOS bytes (B y C) y llama a L_467B, que
                             revuelve el bufer: B*8 es el desplazamiento
            call L_69DF      pinta el bufer en la VRAM (0x69FB en 0x6A33)
            ld a,(hl) / or a / jr nz,L_6A42     otro trozo si no es cero
            inc hl / ret                        y si lo es, se acabo

Y la parte que no es obvia, 0x69DF -> 0x6A1A:

    L_69DF  ld d,(hl) / inc hl               D: la pagina del destino
    L_69E1  ld a,(hl) / inc hl / or a / ret z   E: la fila; 0 -> fin
            destino = (D,E) * 8, con el bit 14 puesto
    L_6A1A  ld c,(hl) / inc hl / ld b,008h   C: UNA MASCARA DE OCHO BITS
    L_6A1F  rl c / ld bc,00008h
            call c,L_457B                    bit a 1: vuelca 8 bytes del bufer
            add hl,bc                        bit a 0: se los salta
            djnz L_6A1F
            ld a,(hl) / or a / jr nz,L_6A1A  otra mascara si no es cero
            inc hl / ret

O sea que cada byte de mascara dice CUALES de los ocho patrones siguientes del
bufer se escriben de verdad. Es lo que permite repintar media pantalla sin
tocar la otra media.

0x69FB es la misma idea con la pagina fija (D=5) y un byte mas por fila, que
suma al destino con L_4027.

Uso: escenas.py <rom> <org> --desde 0x6BE3 [42|33]
     escenas.py <rom> <org> <listado.asm>
"""
import re
import sys

from rle import descomprime_ram


def pinta_69df(rom, org, p):
    """0x69DF: consume el guion de pintado. Devuelve el puntero detras."""
    if p - org >= len(rom):
        return None
    p += 1                                  # ld d,(hl): la pagina
    while True:
        if p - org >= len(rom):
            return None
        fila = rom[p - org]
        p += 1
        if fila == 0x00:                    # or a / ret z
            return p
        p = mascaras(rom, org, p)
        if p is None:
            return None


def pinta_69fb(rom, org, p):
    """0x69FB: igual, pero con pagina fija y un byte de ajuste por fila."""
    while True:
        if p - org >= len(rom):
            return None
        fila = rom[p - org]
        p += 1
        if fila == 0x00:
            return p
        if p - org >= len(rom):
            return None
        p += 1                              # ld a,(hl) / call L_4027
        p = mascaras(rom, org, p)
        if p is None:
            return None


def mascaras(rom, org, p):
    """0x6A1A: mascaras de ocho bits hasta el 0x00 que corta el bucle."""
    while True:
        if p - org >= len(rom):
            return None
        p += 1                              # ld c,(hl): la mascara
        if p - org >= len(rom):
            return None
        if rom[p - org] == 0x00:            # ld a,(hl) / or a / jr nz
            return p + 1                    # inc hl / ret
    # inalcanzable


def escena(rom, org, ini, variante=0x42):
    """El bucle entero. Devuelve (fin, trozos) o (None, trozos)."""
    p, trozos = ini, []
    while len(trozos) < 64:
        f, datos = descomprime_ram(rom, org, p)
        if f is None:
            return None, trozos
        trozos.append(len(datos))
        p = f + 2                           # los dos bytes de 0x69D5
        p = (pinta_69df if variante == 0x42 else pinta_69fb)(rom, org, p)
        if p is None:
            return None, trozos
        if p - org >= len(rom):
            return None, trozos
        if rom[p - org] == 0x00:            # el `or a / jr nz` del final
            return p + 1, trozos
    return None, trozos


def main():
    rom = open(sys.argv[1], "rb").read()
    org = int(sys.argv[2], 0)
    if sys.argv[3] == "--desde":
        ini = int(sys.argv[4], 0)
        var = int(sys.argv[5], 16) if len(sys.argv) > 5 else 0x42
        fin, trozos = escena(rom, org, ini, var)
        print(f"0x{ini:04X} -> " +
              (f"0x{fin:04X}  ({fin - ini} bytes, {len(trozos)} trozos "
               f"de {trozos} descomprimidos)" if fin else f"NO CIERRA ({trozos})"))
        return

    # Los arranques ciertos: la constante en HL antes de llamar a 0x6A42/0x6A33.
    carga = re.compile(r"\bld\s+hl,\s*0([0-9a-f]{4})h\b", re.I)
    llama = re.compile(r"\bcall\s+L_(6A42|6A33)\b", re.I)
    dirl = re.compile(r";([0-9a-f]{4})")
    hl, desde, vistos = None, None, {}
    for ln in open(sys.argv[3], encoding="utf-8"):
        m = carga.search(ln)
        if m:
            hl = int(m.group(1), 16)
            d = dirl.search(ln)
            desde = int(d.group(1), 16) if d else None
            continue
        m = llama.search(ln)
        if m and hl is not None:
            var = 0x42 if m.group(1).upper() == "6A42" else 0x33
            vistos.setdefault((hl, var), []).append(desde)
            hl = None

    print(f"# {len(vistos)} escenas sacadas del listado")
    for (ini, var) in sorted(vistos):
        fin, trozos = escena(rom, org, ini, var)
        quien = ", ".join(f"0x{d:04X}" for d in vistos[(ini, var)] if d)
        if fin is None:
            print(f"# 0x{ini:04X} (por 0x6A{var:02X}, desde {quien}): NO CIERRA")
            continue
        print(f"D 0x{ini:04x} 0x{fin:04x} escena_0x{ini:04X}  "
              f"{fin - ini} bytes, {len(trozos)} trozos de {sum(trozos)} "
              f"descomprimidos; la monta {quien}")


if __name__ == "__main__":
    main()
