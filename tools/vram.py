#!/usr/bin/env python3
"""Dibuja una pantalla a partir de un VOLCADO DE VRAM de verdad.

Esto NO es un dibujo hecho desde la ROM: es lo que el VDP tenia puesto en el
instante en que `tools/omsx_vram.tcl` lo vuelco. Sirve para dos cosas, y las
dos importan:

  1. VER que hay de verdad en cada pantalla, sin adivinar. Reimplementar en
     Python el montador de escenas del cartucho y mirar si el dibujo "parece"
     bueno es justo la manera de publicar un error: el volcado no opina.
  2. COTEJAR contra lo que monta tools/graficos.py, byte a byte.

Cada volcado viene con su `info_NN.txt`, que trae los ocho registros del VDP y
las variables de trabajo -entre ellas el TIPO DE FASE-, asi que que atraccion
sale en cada imagen lo dice el cartucho y no el ojo.

SCREEN 2, con el reparto leido de los registros y no supuesto:

    nombres   R2 * 0x400
    patrones  base (R4 & 0x04) << 11,  mascara ((R4 & 3) << 8) | 0xFF
    color     base (R3 & 0x80) << 6,   mascara ((R3 & 0x7F) << 3) | 0x07
    sprites   atributos R5 * 0x80, patrones R6 * 0x800

Uso: vram.py <vram.bin> <info.txt> <salida.png> [escala]
"""
import struct
import sys
import zlib

PALETA = [
    (0, 0, 0), (0, 0, 0), (33, 200, 66), (94, 220, 120),
    (84, 85, 237), (125, 118, 252), (212, 82, 77), (66, 235, 245),
    (252, 85, 84), (255, 121, 120), (212, 193, 84), (230, 206, 128),
    (33, 176, 59), (201, 91, 186), (204, 204, 204), (255, 255, 255),
]


def png(w, h, px, fn):
    raw = b"".join(b"\0" + bytes(px[y * w * 3:(y + 1) * w * 3]) for y in range(h))

    def chunk(t, d):
        return (struct.pack(">I", len(d)) + t + d
                + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF))
    open(fn, "wb").write(b"\x89PNG\r\n\x1a\n"
                         + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                         + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def lee_info(path):
    d = {}
    for ln in open(path, encoding="utf-8", errors="replace"):
        p = ln.split()
        if not p:
            continue
        if p[0] == "regs":
            d["regs"] = [int(x, 16) for x in p[1:]]
        elif len(p) >= 2:
            d[p[0]] = p[1]
    return d


def pantalla(vram, regs, con_sprites=True):
    """Los 256x192 puntos, como los saca el VDP."""
    nombres = regs[2] * 0x400
    pat_base = (regs[4] & 0x04) << 11
    pat_masc = ((regs[4] & 0x03) << 8) | 0xFF
    col_base = (regs[3] & 0x80) << 6
    col_masc = ((regs[3] & 0x7F) << 3) | 0x07
    fondo = regs[7] & 0x0F

    tela = [[fondo] * 256 for _ in range(192)]
    for fila in range(24):
        tercio = fila // 8
        for col in range(32):
            n = vram[nombres + fila * 32 + col]
            idx = (tercio << 8) | n
            pa = pat_base + (idx & pat_masc) * 8
            co = col_base + (idx & col_masc) * 8
            for f in range(8):
                p, c = vram[pa + f], vram[co + f]
                tinta, tras = c >> 4, c & 0x0F
                for b in range(8):
                    v = tinta if p & (0x80 >> b) else tras
                    tela[fila * 8 + f][col * 8 + b] = v if v else fondo

    if con_sprites:
        pinta_sprites(vram, regs, tela, fondo)

    px = bytearray(256 * 192 * 3)
    for y in range(192):
        for x in range(256):
            c = PALETA[tela[y][x]]
            i = (y * 256 + x) * 3
            px[i], px[i + 1], px[i + 2] = c
    return px


def pinta_sprites(vram, regs, tela, fondo):
    """Los 32 sprites, con SU COLOR, que sale del cuarto byte del atributo.

    En el MSX1 cada sprite es de un solo color, asi que las figuras de dos o
    mas colores se hacen SOLAPANDO sprites en la misma posicion: por eso hay
    que pintarlos todos y en orden, del 31 al 0, para que el de menor numero
    quede encima.
    """
    attr = regs[5] * 0x80
    base = regs[6] * 0x800
    grande = bool(regs[1] & 0x02)          # bit 1 del R1: sprites de 16x16
    lado = 16 if grande else 8
    for s in range(31, -1, -1):
        y = vram[attr + s * 4]
        if y == 0xD0:                      # 0xD0 corta la lista
            continue
        x = vram[attr + s * 4 + 1]
        pat = vram[attr + s * 4 + 2]
        col = vram[attr + s * 4 + 3]
        tinta = col & 0x0F
        if col & 0x80:                     # early clock: 32 puntos a la izquierda
            x -= 32
        y = (y + 1) & 0xFF
        if y > 192:
            y -= 256
        if grande:
            pat &= 0xFC
        d = base + pat * 8
        for cuarto in range(4 if grande else 1):
            ox = (cuarto // 2) * 8
            oy = (cuarto % 2) * 8
            for f in range(8):
                b8 = vram[d + cuarto * 8 + f]
                for b in range(8):
                    if not (b8 & (0x80 >> b)):
                        continue
                    px_, py = x + ox + b, y + oy + f
                    if 0 <= px_ < 256 and 0 <= py < 192 and tinta:
                        tela[py][px_] = tinta


def main():
    vram = open(sys.argv[1], "rb").read()
    info = lee_info(sys.argv[2])
    salida = sys.argv[3]
    esc = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    px = pantalla(vram, info["regs"])
    if esc > 1:
        w, h = 256 * esc, 192 * esc
        g = bytearray(w * h * 3)
        for y in range(h):
            fy = y // esc
            for x in range(w):
                fx = x // esc
                i, j = (y * w + x) * 3, (fy * 256 + fx) * 3
                g[i:i + 3] = px[j:j + 3]
        png(w, h, g, salida)
    else:
        png(256, 192, px, salida)
    print(f"{salida}  etiqueta={info.get('etiqueta')} "
          f"tipo_de_fase={info.get('tipo_de_fase')} "
          f"fase={info.get('numero_de_fase')} regs={info['regs']}")


if __name__ == "__main__":
    main()
