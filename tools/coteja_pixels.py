#!/usr/bin/env python3
"""Coteja el dibujo de tools/vram.py contra la foto del propio openMSX.

QUE ANADE ESTO A tools/coteja_vram.py. Aquel compara las cuatro tablas de la
VRAM byte a byte, o sea que comprueba los DATOS. Este comprueba el
RENDERIZADOR: coge la misma VRAM, la dibuja y la pone al lado de lo que ensena
el emulador en la pantalla. Son dos preguntas distintas, y las dos hay que
contestarlas: se puede tener la VRAM clavada y pintarla mal.

SE COMPARA POR NUMERO DE COLOR DEL MSX, NUNCA POR RGB. Cada dibujante trae su
tabla de RGB para los mismos quince colores, y comparando por RGB sale el 100 %
distinto sin que nada este mal. Ademas el 0 y el 1 se unifican, que en el MSX
los dos son negro.

Y LA FOTO VA UN CUADRO POR DETRAS de la lectura de la VRAM: eso esta MEDIDO en
las cinco atracciones (ver tools/omsx_cuadro.tcl, que vuelca la VRAM en una
rafaga de cuadros alrededor de la foto). Por eso el modo --serie no compara
contra un volcado sino contra todos los de la rafaga, y dice CUAL casa.

Uso:
    coteja_pixels.py <vram.bin> <info.txt> <pant.png>
    coteja_pixels.py --serie <carpeta de omsx_cuadro.tcl>
"""
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vram as V

# El cuadro con el que casa la foto, medido en las cinco atracciones y en dos
# instantes distintos: el ANTERIOR al de la lectura de la VRAM.
CUADRO_QUE_CASA = -1


def _desfiltra(datos, alto, ancho_linea, bpp):
    fuera, prev, pos = [], bytearray(ancho_linea), 0
    for _ in range(alto):
        f = datos[pos]
        linea = bytearray(datos[pos + 1:pos + 1 + ancho_linea])
        pos += 1 + ancho_linea
        for i in range(ancho_linea):
            a = linea[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if f == 1:
                linea[i] = (linea[i] + a) & 0xFF
            elif f == 2:
                linea[i] = (linea[i] + b) & 0xFF
            elif f == 3:
                linea[i] = (linea[i] + (a + b) // 2) & 0xFF
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                linea[i] = (linea[i] + pr) & 0xFF
        fuera.append(linea)
        prev = linea
    return fuera


def lee_png(ruta):
    """(ancho, alto, filas[y][x] = (r,g,b)). Lo justo para leer una captura."""
    d = open(ruta, "rb").read()
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("%s no es un PNG" % ruta)
    pos, idat, paleta, ihdr = 8, [], None, None
    while pos + 8 <= len(d):
        largo = struct.unpack(">I", d[pos:pos + 4])[0]
        tipo = d[pos + 4:pos + 8]
        cuerpo = d[pos + 8:pos + 8 + largo]
        pos += 12 + largo
        if tipo == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", cuerpo)
        elif tipo == b"PLTE":
            paleta = [tuple(cuerpo[i:i + 3]) for i in range(0, len(cuerpo), 3)]
        elif tipo == b"IDAT":
            idat.append(cuerpo)
        elif tipo == b"IEND":
            break
    ancho, alto, prof, color, _c, _f, entre = ihdr
    if entre or prof != 8:
        raise ValueError("PNG entrelazado o de %d bits: no se lee" % prof)
    canales = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
    lineas = _desfiltra(zlib.decompress(b"".join(idat)), alto,
                        ancho * canales, canales)
    pix = []
    for y in range(alto):
        fila = []
        for x in range(ancho):
            i = x * canales
            if color == 3:
                fila.append(paleta[lineas[y][i]])
            elif color in (0, 4):
                g = lineas[y][i]
                fila.append((g, g, g))
            else:
                fila.append(tuple(lineas[y][i:i + 3]))
        pix.append(fila)
    return ancho, alto, pix


_CACHE = {}


def color_msx(rgb):
    """RGB -> numero de color del MSX, con el 0 y el 1 unificados (los dos negro).

    Devuelve (numero, distancia). La distancia importa: si es grande, ese punto
    NO es un color del MSX sino una mezcla, y eso avisa de que el emulador
    lleva encendido algun efecto de televisor (ver omsx_cuadro.tcl).
    """
    if rgb not in _CACHE:
        mejor, dist = 0, None
        for n, c in enumerate(V.PALETA):
            d = sum((a - b) ** 2 for a, b in zip(rgb, c))
            if dist is None or d < dist:
                mejor, dist = n, d
        _CACHE[rgb] = (0 if mejor == 1 else mejor, dist)
    return _CACHE[rgb]


def tela_de_la_foto(png):
    """Los 256x192 de la zona activa, en numeros de color. La captura viene de
    320x240 con el borde alrededor, asi que se recorta centrada."""
    w, h, pix = lee_png(png)
    ox, oy = (w - 256) // 2, (h - 192) // 2
    tela, mezclas = [], 0
    for y in range(192):
        fila = []
        for x in range(256):
            n, d = color_msx(pix[oy + y][ox + x])
            if d > 900:
                mezclas += 1
            fila.append(n)
        tela.append(fila)
    return tela, mezclas


def tela_del_volcado(vram, regs):
    px = V.pantalla(vram, regs)
    return [[color_msx(tuple(px[(y * 256 + x) * 3:(y * 256 + x) * 3 + 3]))[0]
             for x in range(256)] for y in range(192)]


def diferencias(a, b):
    return [(y, x) for y in range(192) for x in range(256) if a[y][x] != b[y][x]]


def informa(dif):
    if not dif:
        return
    filas = {}
    for y, _ in dif:
        filas[y] = filas.get(y, 0) + 1
    peores = sorted(filas.items(), key=lambda t: -t[1])[:6]
    print("       franja y %d..%d  x %d..%d" % (
        min(y for y, _ in dif), max(y for y, _ in dif),
        min(x for _, x in dif), max(x for _, x in dif)))
    print("       peores filas: %s" % ", ".join(
        "y=%d (%d)" % (y, n) for y, n in peores))
    celdas = sorted(set((y // 8, x // 8) for y, x in dif))[:10]
    print("       celdas (fila,col): %s" % celdas)


def un_par(binario, info, png):
    regs = V.lee_info(info)["regs"]
    suyo, mezclas = tela_de_la_foto(png)
    mio = tela_del_volcado(open(binario, "rb").read(), regs)
    dif = diferencias(mio, suyo)
    print("  %s contra %s: %d puntos de 49152 (%.2f %% iguales)" % (
        os.path.basename(binario), os.path.basename(png), len(dif),
        100.0 * (49152 - len(dif)) / 49152))
    if mezclas:
        print("       OJO: %d puntos de la foto no son colores del MSX; el"
              " emulador tiene encendido el blur o el glow" % mezclas)
    informa(dif)
    return 0 if not dif else 1


def una_serie(carpeta):
    """Cada foto contra toda su rafaga de cuadros: cual casa, y con cuantos."""
    actos = sorted(f[5:-4] for f in os.listdir(carpeta)
                   if f.startswith("info_") and f.endswith(".txt"))
    if not actos:
        print("  no hay volcados en %s" % carpeta)
        return 2
    mal = 0
    for acto in actos:
        regs = V.lee_info(os.path.join(carpeta, "info_%s.txt" % acto))["regs"]
        suyo, mezclas = tela_de_la_foto(
            os.path.join(carpeta, "pant_%s.png" % acto))
        linea, suyos = [], {}
        for k in range(-9, 10):
            nom = os.path.join(carpeta, "vram_%s_%s%02d.bin" % (
                acto, "m" if k < 0 else "p", abs(k)))
            if not os.path.exists(nom):
                continue
            n = len(diferencias(
                tela_del_volcado(open(nom, "rb").read(), regs), suyo))
            linea.append((k, n))
            suyos[k] = n
        # Lo que se exige es que case el cuadro medido. Que ademas casen otros
        # no es una pega: quiere decir que en ese instante no se movia nada.
        n = suyos.get(CUADRO_QUE_CASA)
        marca = "OK" if n == 0 else "%s PUNTOS" % n
        print("  %-8s contra el cuadro %+d: %s"
              % (acto, CUADRO_QUE_CASA, marca))
        if n:
            mal += 1
            print("       %s" % "  ".join("%+d:%d" % t for t in linea))
            if mezclas:
                print("       OJO: %d puntos de la foto no son colores del"
                      " MSX (blur o glow encendidos)" % mezclas)
    print("  %d de %d atracciones cotejadas punto por punto"
          % (len(actos) - mal, len(actos)))
    return 0 if not mal else 1


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--serie":
        return una_serie(sys.argv[2])
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    return un_par(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    sys.exit(main())
