#!/usr/bin/env python3
"""Rehace la VRAM de Circus Charlie y la DIBUJA. Aqui no hay ni una captura.

Cada imagen sale de correr en Python los MISMOS pasos que da el Z80, citando la
direccion de cada paso. Si un dibujo sale mal, lo que esta mal es la lectura del
cartucho: por eso vale como comprobacion y no como adorno.

EL REPARTO DE LA VRAM, QUE HAY QUE LEER EN LOS REGISTROS
--------------------------------------------------------
Los ocho registros los baja 0x4708 desde 0x4722, que vale
`02 E2 0E 7F 07 76 03 E1` -los mismos ocho, byte a byte, que Magical Tree
(RC-713) y Comic Bakery (RC-714)-. En SCREEN 2 el R3 y el R4 no son direcciones
sino BASE y MASCARA:

    R2 = 0x0E   tabla de NOMBRES en 0x3800
    R3 = 0x7F   COLOR: bit 7 a CERO, base 0x0000
    R4 = 0x07   PATRONES: bit 2 puesto, base 0x2000
    R5 = 0x76   atributos de sprite en 0x3B00
    R6 = 0x03   patrones de SPRITE en 0x1800

Lo confirma el propio cartucho: 0x434A manda "los patrones del titulo" a
0x3600 y 0x4350 su color a 0x1600, que son la misma celda de tercios
distintos, uno en cada tabla.

Y OJO CON LAS DIRECCIONES DE 16 BITS: el cartucho escribe `ld de,07600h` para
la VRAM 0x3600 y `ld de,05600h` para la 0x1600. El VDP solo mira catorce bits,
asi que los dos de arriba sobran; aqui se enmascaran igual que alli.

LO QUE SALE
-----------
Las dos primeras son PANTALLAS ENTERAS, y las dos estan cotejadas contra un
volcado de la VRAM del emulador a CERO bytes de diferencia
(tools/coteja_vram.py). Las demas son hojas de material, para mirar el
contenido de las tablas:

    pantalla-presentacion.png  la pantalla de LA CASA: el logotipo de KONAMI y
                   el rotulo "- VIDEO CARTRIDGE -"
    pantalla-titulo.png  la pantalla de TITULO: "Circus Charlie", el
                   "(c) Konami 1984", el "PLAY SELECT" y las cuatro opciones
                   con su cursor
    logotipo-konami.png  los 26 dibujos del logotipo de la casa, patrones
                   0x41..0x5A. OJO: es el logotipo de KONAMI, no el titulo del
                   juego -son dos cosas distintas y confundirlas ya costo una
                   tanda de imagenes malas-
    fuente-titulo.png  los 48 dibujos que 0x4347 sube para la pantalla de
                   titulo: la fuente entera, recolocada en el patron 0xC0 del
                   tercer tercio y pintada de 0x70
    tiles.png      la hoja de patrones del fondo, tal como queda en la VRAM
    tiles-tercio3.png  la del tercer tercio
    sprites.png    los patrones de sprite de 0x1800

Uso: graficos.py <rom> <org> <salida>
"""
import os
import struct
import sys
import zlib

ORG = 0x4000

PALETA = [
    (0, 0, 0), (0, 0, 0), (33, 200, 66), (94, 220, 120),
    (84, 85, 237), (125, 118, 252), (212, 82, 77), (66, 235, 245),
    (252, 85, 84), (255, 121, 120), (212, 193, 84), (230, 206, 128),
    (33, 176, 59), (201, 91, 186), (204, 204, 204), (255, 255, 255),
]

VDP = [0x02, 0xE2, 0x0E, 0x7F, 0x07, 0x76, 0x03, 0xE1]
NOMBRES = VDP[2] * 0x400
COLOR = (VDP[3] & 0x80) << 6
PATRONES = (VDP[4] & 0x04) << 11
SPRITES = VDP[6] * 0x800


def png(w, h, px, fn):
    raw = b"".join(b"\0" + bytes(px[y * w * 3:(y + 1) * w * 3]) for y in range(h))

    def chunk(t, d):
        return (struct.pack(">I", len(d)) + t + d
                + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF))
    open(fn, "wb").write(b"\x89PNG\r\n\x1a\n"
                         + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                         + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def lienzo(w, h, c=(24, 24, 24)):
    return bytearray(bytes(c) * (w * h))


def punto(px, w, x, y, c):
    i = (y * w + x) * 3
    px[i], px[i + 1], px[i + 2] = c


class Vram:
    """La VRAM y su puntero de escritura, como el VDP de verdad.

    Hace falta el puntero porque 0x45C6 encadena DOS bloques: el segundo se
    descomprime con el HL que dejo el primero y sin volver a situar el destino.
    """

    def __init__(self):
        self.b = bytearray(0x4000)
        self.pt = 0

    def situa(self, de):
        self.pt = de & 0x3FFF

    def escribe(self, v):
        self.b[self.pt] = v
        self.pt = (self.pt + 1) & 0x3FFF


def descomprime(v, rom, ini, destino=None, cabecera=True):
    """El descompresor de 0x45C9, con sus puertas.

    El lenguaje va al reves de lo que parece: bit 7 a CERO repite un byte y
    bit 7 PUESTO copia n bytes tal cual. 0x80 cambia de destino y 0x00 cierra.
    Devuelve donde acaba, que es lo que permite encadenar el bloque siguiente.
    """
    p = ini - ORG
    if destino is not None:
        v.situa(destino)
    elif cabecera:
        v.situa(rom[p] | (rom[p + 1] << 8))
        p += 2
    while True:
        ctrl = rom[p]
        p += 1
        cuenta = ctrl & 0x7F
        if cuenta == 0:
            if ctrl == 0x00:
                return ORG + p
            v.situa(rom[p] | (rom[p + 1] << 8))
            p += 2
            continue
        if ctrl & 0x80:
            for i in range(cuenta):
                v.escribe(rom[p + i])
            p += cuenta
        else:
            for _ in range(cuenta):
                v.escribe(rom[p])
            p += 1


def rellena(v, destino, n, valor):
    v.situa(destino)
    for _ in range(n):
        v.escribe(valor)


def duplica_las_dos_tablas(v):
    """0x45B0: el primer tercio de patrones y el de color, a los otros dos."""
    for base in (PATRONES, COLOR):
        v.b[base + 0x800:base + 0x1000] = v.b[base:base + 0x800]
        v.b[base + 0x1000:base + 0x1800] = v.b[base:base + 0x800]


def vram_del_titulo(rom):
    """0x4341: la cortinilla, el fondo y los patrones del titulo."""
    v = Vram()
    # 0x4B49 prepara_la_cortinilla: los 26 dibujos del logotipo
    descomprime(v, rom, 0x4BA6, destino=0x6208)          # 0x4B54
    rellena(v, 0x0208, 0xD0, 0xF0)                       # 0x4B5D
    duplica_las_dos_tablas(v)                            # 0x4B68
    # 0x45BB carga_la_pantalla_de_fondo: dos bloques ENCADENADOS
    fin = descomprime(v, rom, 0x47DE)                    # 0x45C0
    descomprime(v, rom, fin)                             # 0x45C6, pegado detras
    duplica_las_dos_tablas(v)                            # 0x45BE
    # 0x4347 los patrones del titulo y su color
    descomprime(v, rom, 0x47F1, destino=0x7600)          # 0x4347
    rellena(v, 0x5600, 0x180, 0x70)                      # 0x4350
    descomprime(v, rom, 0x4A69)                          # 0x435B
    de = 0x4600                                          # 0x4361: diecisiete veces
    for _ in range(0x11):
        descomprime(v, rom, 0x4378, destino=de)
        de += 0x10
    return v


def pinta_rotulo(v, rom, ini, mascara=0xFF):
    """El interprete de rotulos de 0x4066, que es el mismo de tools/guiones.py.

    Con la mascara a 0xFF pinta y con 0x00 BORRA, escribiendo ceros sobre la
    misma geometria: por eso el cartucho no guarda una segunda copia para
    quitar un rotulo.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from guiones import ejecuta
    fin, tramos = ejecuta(rom, ORG, ini)
    for destino, cuerpo in tramos:
        v.situa(destino)
        for b in cuerpo:
            v.escribe(b & mascara)
    return fin


def baja_la_cortinilla(v, pasos=0x11):
    """0x4B6B, y NO es una cortinilla: es el logotipo de KONAMI subiendo.

    Cada pasada escribe tres franjas de patrones CORRELATIVOS -3, 11 y 12
    celdas desde el 0x41 hasta el 0x5A, que son los veintiseis dibujos del
    logotipo- y detras borra doce celdas de la fila de abajo, que es el rastro
    de la pasada anterior. Por eso no hace falta limpiar nada mas.

    Lo llamativo es a donde escribe: al REFLEJO de la cuenta respecto de
    0x3AAA (`ld hl,03aaah / sbc hl,de`), asi que el logotipo SUBE mientras la
    cuenta baja. Con los diecisiete pasos de 0x4B49 acaba en 0x388A, que es la
    fila 4, columna 10. Magical Tree y Comic Bakery hacen lo mismo, celda por
    celda, y solo cambian el patron por el que empiezan.
    """
    for paso in range(1, pasos + 1):
        de = (0x3AAA - paso * 0x20) & 0x3FFF
        a = 0x41
        for n in (3, 11, 12):
            v.situa(de)
            for _ in range(n):
                v.escribe(a)
                a = (a + 1) & 0xFF
            de = (de + 0x20) & 0x3FFF
        v.situa(de)                        # 0x4B8E: el rastro de la anterior
        for _ in range(12):
            v.escribe(0x00)


def vram_de_la_presentacion(rom):
    """LA PANTALLA DE LA CASA, entera: la escena 2 del cartucho.

    OJO CON EL NOMBRE, que ya costo una tanda de imagenes malas: esta NO es la
    pantalla de titulo del juego. Es la de la casa -el logotipo de KONAMI y el
    rotulo "- VIDEO CARTRIDGE -"-, y la de titulo es otra, con su propio
    decorado. Lo dice el cartucho: la escena 2 pinta esto y la 4 pinta "PLAY
    SELECT" y el "(c) 1984".

    Sale de encadenar lo que encadena la escena 0 (0x40E9):
        0x40EC  monta_la_pantalla_del_titulo  el decorado
        0x40F9  baja_la_cortinilla            el logotipo, diecisiete pasos
        0x4100  pinta_rotulo 0x4A53           "- VIDEO CARTRIDGE -"
    """
    v = vram_del_titulo(rom)
    baja_la_cortinilla(v)
    pinta_rotulo(v, rom, 0x4A53)
    return v


def barre_la_pantalla(v, pasos=0x11):
    """0x44F7: la cortina que tapa el logotipo, columna a columna.

    La nota del listado dice "tres filas por llamada" y en realidad es una
    COLUMNA de tres celdas: DE arranca en 0x3888 -fila 4, columna 8- y le suma
    el numero de pasada, que es la columna; luego baja de fila en fila (`ld
    a,020h / suma_a_a_de`). La de arriba se deja vacia y las dos de abajo
    llevan los patrones 0xC0+2n y 0xC1+2n, o sea una pareja distinta por
    columna. Con diecisiete pasadas cubre las columnas 8 a 24, que es
    exactamente donde estaba el logotipo.
    """
    for paso in range(pasos):
        de = 0x3888 + paso
        for valor in (0x00, 0xC0 + paso * 2, 0xC1 + paso * 2):
            v.situa(de)
            v.escribe(valor & 0xFF)
            de += 0x20


def donde_va_el_cursor(opcion):
    """0x453E, y hay que hacerlo con ROTACIONES, no con divisiones.

        ld a,(0e042h) / add a,014h / rrca / rrca / ld e,a / ld d,07ah

    `rrca` ROTA: el bit 0 no se pierde, sube al bit 7. Con la opcion 0 los dos
    giros de 0x14 dan 0x05 y coincide con dividir por cuatro, pero con la 1
    -0x15- dan 0x45 y no 0x05: el bit que se sale es el que separa una opcion
    de la siguiente. De ahi salen 0x3A05, 0x3A45, 0x3A85 y 0x3AC5, o sea la
    columna 5 de las filas 16, 18, 20 y 22.
    """
    a = (0x14 + opcion) & 0xFF
    for _ in range(2):
        a = ((a >> 1) | ((a & 1) << 7)) & 0xFF
    return (0x7A00 | a) & 0x3FFF


def vram_de_la_seleccion(rom, cursor=True, opcion=0):
    """LA PANTALLA DE TITULO DE VERDAD: la del menu, con "PLAY SELECT".

    Es la que el jugador reconoce como titulo, y se llega a ella desde la de
    la casa sin recargar el decorado: los patrones y el color son los MISMOS
    -medido: cero bytes de diferencia-, y lo unico que cambia es la tabla de
    nombres. Tres pasos, en el orden en que los da el cartucho:

        0x410D  borra_rotulo 0x4A53   quita el "VIDEO CARTRIDGE" con su mismo
                                      guion y la mascara a 0x00
        0x44F7  barre_la_pantalla     la cortina, diecisiete columnas
        0x451D  pinta_rotulo 0x49C3   "PLAY SELECT", las cuatro filas del menu
                                      y el "(c) 1984"

    El cursor (0x4527) es lo unico que no es fijo: son dos celdas, los patrones
    0x3E y 0x3F, y PARPADEA con el bit 3 del plazo, asi que en la mitad de los
    cuadros no esta. Donde va lo dice 0x453E: la opcion elegida mas 0x14, dos
    `rrca` y la pagina 0x7A fija, que para la primera opcion da 0x3A05 -fila
    16, columna 5-. Cotejado contra dos volcados: con el cursor encendido, 0
    diferencias; con el apagado, esas dos celdas.
    """
    v = vram_de_la_presentacion(rom)
    pinta_rotulo(v, rom, 0x4A53, mascara=0x00)
    barre_la_pantalla(v)
    pinta_rotulo(v, rom, 0x49C3)
    if cursor:
        v.situa(donde_va_el_cursor(opcion))
        v.escribe(0x3E)
        v.escribe(0x3F)
    return v


def vuelca_patrones_repetidos(v, rom, ini):
    """0x462F: `[N][ocho bytes]` escribe ese patron N veces.

    El bucle RETROCEDE ocho (`ld bc,0fff8h / add hl,bc`) despues de cada copia,
    y solo al acabar las N avanza al patron siguiente. Un cero cierra la lista.
    Devuelve donde acaba, que es lo que permite encadenar lo que venga detras
    sin recargar el puntero.
    """
    p = ini - ORG
    while True:
        n = rom[p]
        p += 1
        if n == 0:
            return ORG + p
        for _ in range(n):
            for i in range(8):
                v.escribe(rom[p + i])
        p += 8


def copia_a_los_tres_tercios(v, de, n):
    """0x4608: el tercio 0 al 1 y al 2, en COLOR y en PATRONES a la vez.

    `copia_dos_tercios` copia n bytes de DE a DE+0x800 y repite 0x2000 mas
    arriba, que es donde esta la otra tabla; y 0x4608 lo hace dos veces, de
    modo que el primer tercio acaba en los tres.
    """
    for _ in range(2):
        for base in (0x0000, 0x2000):
            orig = (de + base) & 0x3FFF
            dest = (de + base + 0x800) & 0x3FFF
            v.b[dest:dest + n] = v.b[orig:orig + n]
        de += 0x800


def que_dibujo_toca(tipo):
    """0x57A8: devuelve si toca el dibujo A (tipos 0 y 2) o el B."""
    return tipo in (0, 2)


def vuelca_la_tanda_cuatro_veces(v, rom, ini):
    """0x6DB5: la MISMA lista de patrones repetidos, cuatro veces seguidas.

    Guarda el puntero antes de cada pasada (`push hl`), asi que las cuatro
    leen lo mismo y lo que avanza es el destino en la VRAM.
    """
    for _ in range(4):
        vuelca_patrones_repetidos(v, rom, ini)


def copia_dos_tercios(v, de, n):
    """0x4612: el tercio DE al siguiente, en COLOR y en PATRONES."""
    for base in (0x0000, 0x2000):
        orig = (de + base) & 0x3FFF
        dest = (de + base + 0x800) & 0x3FFF
        v.b[dest:dest + n] = v.b[orig:orig + n]


def decorado_del_leon(v, rom):
    """0x6D97, el del LEON (tipo 1). Y 0x7149 detras, que lo apila el
    despachador."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import escenas as E
    E.monta(rom, ORG, 0x6DC1, v.b, 0x33)                 # 0x6D9A, por la otra puerta
    v.situa(0x4B00)                                      # 0x6DA0
    vuelca_la_tanda_cuatro_veces(v, rom, 0x6FA5)         # 0x6DA3
    vuelca_la_tanda_cuatro_veces(v, rom, 0x6FC1)         # 0x6DA9
    copia_dos_tercios(v, 0x0B00, 0x0280)                 # 0x6DB2
    E.monta(rom, ORG, 0x7155, v.b, 0x42)                 # 0x714C
    v.situa(0x1200)                                      # 0x714F
    vuelca_patrones_repetidos(v, rom, 0x719E)            # 0x7152


def descomprime_en_de(v, rom, ini, de):
    """0x45CD: el destino viene en DE y el bloque no lleva cabecera."""
    v.situa(de)
    return descomprime(v, rom, ini, cabecera=False)


def copia_vram_a_vram(v, de, hl, n):
    """0x458F: de DE a HL dentro de la VRAM, byte a byte y en orden.

    Las dos rutinas de 0x4010 trabajan con DE: lee_de_vram lee (DE), y el
    `ex de,hl` de antes de escribe_en_vram pone en DE lo que venia en HL. O
    sea que se LEE por DE y se ESCRIBE por HL. Con HL por delante de DE y la
    copia hacia delante, lo copiado se vuelve a leer: el decorado se repite
    cada (HL - DE) bytes, que es lo que 0x7477 quiere.
    """
    for i in range(n):
        v.b[(hl + i) & 0x3FFF] = v.b[(de + i) & 0x3FFF]


def del_reves(b):
    """Los ocho bits de un byte dados la vuelta: 0x758B, ocho `rl d / rra`."""
    return int("{:08b}".format(b)[::-1], 2)


def vuelca_con_espera(v, rom, ini, de):
    """0x7567: el lenguaje del descompresor, pero cada byte sale con los BITS
    DEL REVES. Control con el bit 7 a cero: UN byte, repetido N veces; con el
    bit 7 puesto: N bytes, uno a uno. Un cero cierra. Los `push hl / pop hl`
    del bucle solo dan tiempo al VDP."""
    v.situa(de)
    p = ini - ORG
    while True:
        ctrl = rom[p]
        p += 1
        if ctrl == 0:
            return ORG + p
        n = ctrl & 0x7F
        if ctrl & 0x80:
            for i in range(n):
                v.escribe(del_reves(rom[p + i]))
            p += n
        else:
            b = del_reves(rom[p])
            p += 1
            for _ in range(n):
                v.escribe(b)


def celda_de_la_posicion(d, e):
    """0x53F3 posicion_a_celda: (D, E) en pixeles -> celda de la tabla de
    nombres. Los giros dejan 0x38 + (D >> 6) en D y ((D >> 3) & 7) * 32 +
    (E >> 3) en E, o sea 0x3800 + (D >> 3) * 32 + (E >> 3)."""
    return 0x3800 + ((d >> 3) << 5) + (e >> 3)


def pinta_bloque_en_su_sitio(v, rom, de, bc, z):
    """0x6A6D: un rectangulo de la tabla de nombres con UN patron por fila.

    B celdas de ancho -recortadas a lo que quede hasta el borde derecho- y C
    filas, desde la celda de (D, E). El patron de cada fila sale de una tira
    entrando por D >> 3: la de 0x6A9E si toca el dibujo A (tipos 0 y 2) o la
    de 0x6AA9 si no. Las dos tiras caen sobre bytes que tambien son codigo.
    Y el `inc hl` esta FUERA del `djnz`: cada fila es un solo patron.
    """
    d, e = de >> 8, de & 0xFF
    celda = celda_de_la_posicion(d, e)
    tabla = 0x6A9E if z else 0x6AA9
    p = tabla + ((d >> 3) & 0x1F)
    b, c = bc >> 8, bc & 0xFF
    resto = (-((celda & 0xFF) | 0xE0)) & 0xFF
    if resto < b:
        b = resto
    for _ in range(c):
        patron = rom[p - ORG]
        for i in range(b):
            v.b[(celda + i) & 0x3FFF] = patron
        p += 1
        celda += 0x20


def vuelca_la_figura(v, rom, hl, de, bufer, z):
    """0x5711: el dibujo grande del decorado, por franjas y CON REFERENCIAS.

    El puntero de VRAM se mueve con 0x57B3 -la columna avanza y da la vuelta
    DENTRO de la fila, y la fila solo cambia con la parte alta del salto- y
    al pasar de la columna 31 se vuelve al principio de la MISMA fila
    (0x57B0: `dec d` y +0xE0). En el dibujo, un cero no es un patron: es una
    referencia, y el byte siguiente dice cuanto RETROCEDER; a partir de ahi
    se sigue leyendo desde ese sitio (el `inc hl` de 0x5799 avanza el puntero
    ya movido). Es una compresion por diccionario dentro del propio dibujo.

    Primero 32 celdas desde la columna 0x15; luego seis filas de 5 celdas con
    referencias, 6 tal cual y 6 con referencias; luego dos franjas de 15; y
    al final un patron (ocho bytes) del bufer de 0xE280 -el ultimo trozo de
    la escena de 0x6D0A- que se elige con el ultimo indice leido y va al
    patron 0x51: en los tercios 1 y 2 con el dibujo A, en el 0 con el B.
    """
    st = {"hl": hl, "de": de}

    def avanza(a):                      # 0x57B3 avanza_sin_salir_de_la_fila
        e, d = st["de"] & 0xFF, (st["de"] >> 8) & 0xFF
        col, fila = a & 0x1F, a & 0xE0
        s = fila + e
        if s > 0xFF:
            d = (d + 1) & 0xFF
        st["de"] = (d << 8) | (s & 0xE0) | ((e + col) & 0x1F)

    def baja_una_fila():                # 0x57B0: dec d, y 0xE0 por 0x57B3
        st["de"] = (st["de"] - 0x100) & 0xFFFF
        avanza(0xE0)

    def escribe(a):
        v.b[st["de"] & 0x3FFF] = a
        st["de"] = (st["de"] + 1) & 0xFFFF
        if (st["de"] & 0x1F) == 0:
            baja_una_fila()

    def lee():
        a = rom[st["hl"] - ORG]
        return a

    def franja_con_referencias(b):      # 0x578E
        for _ in range(b):
            a = lee()
            if a == 0:
                st["hl"] += 1
                st["hl"] = st["hl"] + rom[st["hl"] - ORG] - 0x100
                a = lee()
            st["hl"] += 1
            escribe(a)

    def con_referencias(a, b):          # 0x578B
        avanza(a)
        franja_con_referencias(b)

    con_referencias(0x15, 0x20)                       # 0x5714
    st["hl"] += 2                                     # 0x571B
    a = 0x20
    for _ in range(6):                                # 0x571D, seis grupos
        g = st["hl"]
        st["hl"] = g + 6                              # 0x5723
        con_referencias(a, 5)                         # 0x5729
        st["hl"] = g                                  # pop hl
        for _ in range(6):                            # 0x5731, tal cual
            escribe(lee())
            st["hl"] += 1
        franja_con_referencias(6)                     # 0x5742
        st["hl"] += 2                                 # 0x5745
        a = 0x2F                                      # 0x5747
    st["hl"] = st["hl"] + 0xEA - 0x100                # 0x574C: 22 atras
    st["de"] = (st["de"] - 0x100) & 0xFFFF            # 0x5754 dec d
    con_referencias(0xC0, 15)                         # 0x5752
    st["hl"] += 8                                     # 0x575A
    con_referencias(0x31, 15)                         # 0x575F
    st["hl"] -= 1                                     # 0x5766
    ultimo = lee()
    desde = ((ultimo - 0xB8) & 0x0C) * 2              # 0x5768: 0, 8, 16 o 24
    patron = bytes(bufer[desde:desde + 8])
    assert len(patron) == 8, "el bufer de 0xE280 se queda corto"
    for destino in ((0x2A88, 0x3288) if z else (0x2288,)):   # 0x5772-0x5788
        v.situa(destino)
        for x in patron:
            v.escribe(x)


def remata_el_montaje(v, rom, tipo):
    """0x699D, lo que el despachador de 0x5FD6 apila para despues del decorado
    de cada tipo: el fondo alterno (solo con el dibujo A), el bloque de un
    patron por fila, la escena de 0x6D0A y la figura grande. Los tres
    parametros son constantes del propio remate: 0x1000/0x1800/0x2013 con el
    dibujo B y 0x6800/0x7000/0x200A con el A."""
    import escenas as E
    z = que_dibujo_toca(tipo)
    if z:
        descomprime(v, rom, 0x6AC1 if tipo == 2 else 0x6AC6)   # 0x69C8
        hl, de, bc = 0x6800, 0x7000, 0x200A
    else:
        hl, de, bc = 0x1000, 0x1800, 0x2013
    pinta_bloque_en_su_sitio(v, rom, de, bc, z)               # 0x69B9
    E.monta(rom, ORG, 0x6D0A, v.b, 0x42)                      # 0x69BF
    variante = (hl & 0xFF) & 0x06                             # 0x56D5
    dibujo = rom[0x6ACB + variante - ORG] | (rom[0x6ACB + variante + 1 - ORG] << 8)
    celda = celda_de_la_posicion(hl >> 8, hl & 0xFF)          # 0x56E5
    vuelca_la_figura(v, rom, dibujo, celda, E.BUFER, z)


def carga_los_sprites_667D(v, rom):
    """0x603D: el bloque de 0x667D sobre 0x1BA0, los patrones de sprite."""
    descomprime_en_de(v, rom, 0x667D, 0x1BA0)


def decorado_del_trampolin(v, rom):
    """0x753B, el del TRAMPOLIN (tipo 0). Dos bloques encadenados, los mismos
    bytes volcados otra vez con los bits del reves -la primera mitad a 0x2680
    y la segunda a 0x25C0-, 1.152 celdas de 0xF0 y el tercio 0 copiado al 1."""
    fin = descomprime(v, rom, 0x7596)                    # 0x753E
    descomprime(v, rom, fin, cabecera=False)             # 0x7541
    # la tira empieza en 0x7598, detras de la cabecera del bloque, y la
    # SEGUNDA llamada sigue por donde dejo la primera: 0x7658, la otra mitad
    fin = vuelca_con_espera(v, rom, 0x7598, 0x2680)      # 0x7547
    vuelca_con_espera(v, rom, fin, 0x25C0)               # 0x754D
    rellena(v, 0x0380, 0x0480, 0xF0)                     # 0x7553
    copia_dos_tercios(v, 0x0500, 0x0180)                 # 0x755E


def decorado_de_las_bolas(v, rom):
    """0x71D9, el de LAS BOLAS (tipo 3): la escena de 0x71EB, sus patrones en 0x1400 y el
    bloque de 0x728F."""
    import escenas as E
    fin = E.monta(rom, ORG, 0x71EB, v.b, 0x42)           # 0x71DC
    v.situa(0x1400)                                      # 0x71DF
    vuelca_patrones_repetidos(v, rom, fin)               # 0x71E2
    descomprime(v, rom, 0x728F)                          # 0x71E8


def decorado_del_caballo(v, rom):
    """0x7477, el del CABALLO (tipo 4): la escena de 0x7498, sus patrones en 0x0AC0, 720
    bytes de 0x2AC0 copiados sobre 0x2BB0 -solapados, asi que el decorado se
    repite cada 240- y el tercio 1 al 2."""
    import escenas as E
    fin = E.monta(rom, ORG, 0x7498, v.b, 0x42)           # 0x747A
    v.situa(0x0AC0)                                      # 0x747D
    vuelca_patrones_repetidos(v, rom, fin)               # 0x7480
    copia_vram_a_vram(v, 0x2AC0, 0x2BB0, 0x02D0)         # 0x748C
    copia_dos_tercios(v, 0x0AC0, 0x03C0)                 # 0x7495


def decorado_del_tipo(v, rom, tipo):
    """La tabla de cinco de 0x5FEF, una entrada por tipo de fase."""
    if tipo == 0:                                        # 0x6034
        decorado_del_trampolin(v, rom)
        descomprime(v, rom, 0x67A1)                      # 0x603A
        carga_los_sprites_667D(v, rom)              # 0x603D
    elif tipo == 1:                                      # 0x5FF9
        decorado_del_leon(v, rom)                    # y 0x7149 detras
    elif tipo == 2:                                      # 0x5FFF
        descomprime(v, rom, 0x6547)                      # 0x6019
        descomprime_en_de(v, rom, 0x7056, 0x2D00)        # 0x6008
        rellena(v, 0x0D00, 0x0100, 0x60)                 # 0x6013
    elif tipo == 3:                                      # 0x6016
        decorado_de_las_bolas(v, rom)
        descomprime(v, rom, 0x6547)                      # 0x6019
    elif tipo == 4:                                      # 0x601F
        decorado_del_caballo(v, rom)
        descomprime_en_de(v, rom, 0x6323, 0x1B20)        # 0x6028
        carga_los_sprites_667D(v, rom)              # 0x602B
        descomprime(v, rom, 0x68BD)                      # 0x6031


def vram_de_la_atraccion(rom, tipo=0):
    """LA VRAM DE UNA ATRACCION, como la deja 0x5FD6 al empezar la fase.

    Es la cadena entera: los sprites y el marco, lo comun a las cinco
    (0x6968), el decorado de SU tipo (la tabla de cinco de 0x5FEF) y el
    remate de 0x699D, que el despachador apila antes de saltar. Nada aqui
    depende del estado del juego: los parametros del remate son constantes
    y posicion_a_celda no lee la RAM.

        0x696B  monta_escena 0x6BE3          la escena del nivel
        0x6978  vuelca_patrones_repetidos    desde 0x6D1A, a la VRAM 0x4200
        0x697B  descomprime_donde_quedo      con el MISMO puntero
        0x697E  vuelca_lista_de_patrones     idem
        0x6987  copia_a_los_tres_tercios     648 bytes
        0x698A  monta_la_franja_de_abajo     0x72ED + sus patrones en 0x1680
        0x6997  y, solo con el dibujo A (tipos 0 y 2), otros 1.016 bytes a
                los tres tercios y la escena de 0x73C2 con sus patrones
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import escenas as E
    # LA VRAM SE HEREDA: la fase no parte de cero sino de lo que dejo la
    # pantalla de seleccion -la fuente, los colores-, con la tabla de nombres
    # borrada (0x4558). Sin esto, todo lo que la fase no reescribe sale mal.
    v = vram_de_la_seleccion(rom, cursor=False)
    v.b[NOMBRES:NOMBRES + 0x300] = bytes(0x300)
    descomprime(v, rom, 0x61BA)                          # 0x5FD9
    descomprime(v, rom, 0x5FCF)                          # 0x5FDF
    E.monta(rom, ORG, 0x6BE3, v.b, 0x42)                 # 0x696B
    v.situa(0x4200)                                      # 0x6971
    fin = vuelca_patrones_repetidos(v, rom, 0x6D1A)      # 0x6978
    fin = descomprime(v, rom, fin, cabecera=False)       # 0x697B
    vuelca_patrones_repetidos(v, rom, fin)               # 0x697E
    copia_a_los_tres_tercios(v, 0x0000, 0x0288)          # 0x6987
    fin = E.monta(rom, ORG, 0x72ED, v.b, 0x42)           # 0x72E4
    v.situa(0x1680)                                      # 0x72E7
    vuelca_patrones_repetidos(v, rom, fin)               # 0x72EA
    if que_dibujo_toca(tipo):                            # 0x698D
        copia_a_los_tres_tercios(v, 0x0288, 0x03F8)      # 0x6997
        fin = E.monta(rom, ORG, 0x73C2, v.b, 0x42)       # 0x73B9
        v.situa(0x0E80)                                  # 0x73BC
        vuelca_patrones_repetidos(v, rom, fin)           # 0x73BF
    decorado_del_tipo(v, rom, tipo)                      # 0x5FEC
    remata_el_montaje(v, rom, tipo)                      # 0x699D
    return v


def imprime_bcd(v, de, valores):
    """0x449D: cada byte BCD son dos digitos, el alto primero, y el "0" es la
    casilla 0x10 de la fuente. `valores` va como lo recorre la rutina: del
    byte alto al bajo (el puntero de la variable retrocede)."""
    v.situa(de)
    for b in valores:
        v.escribe(0x10 | (b >> 4))
        v.escribe(0x10 | (b & 0x0F))


def pinta_el_marcador(v, rom, vidas=2, fase_bcd=0x01, bonificacion=(0x80, 0x00),
                      tanteo=(0, 0, 0), record=(0, 0, 0)):
    """0x4450, EL MARCADOR ENTERO, como queda al empezar la primera fase.

    Los rotulos fijos salen del guion de 0x499F -"1P-", "HI-", "STAGE-",
    "BONUS-"-; los numeros, del impresor de BCD: el tanteo en 0x3805 (tres
    bytes, 0xE04B hacia atras), el record en 0x380F (0xE045), el numero de
    fase en 0x381C (0xE051, un byte) y la bonificacion en 0x3832 (dos bytes,
    0xE058 y 0xE057). Las vidas, 0x44D4: una marca 0x0B por vida desde la
    celda 0x383D hacia la izquierda, cinco como mucho.

    Los valores por defecto son los MEDIDOS en 0x4C3C con
    tools/omsx_montaje.tcl al arrancar una partida: dos vidas -tres menos la
    que se va a jugar, el `dec (hl)` de 0x416B-, fase 01 y bonificacion 8000.
    """
    pinta_rotulo(v, rom, 0x499F)                         # 0x4453
    imprime_bcd(v, 0x3805, tanteo)                       # 0x4483
    imprime_bcd(v, 0x380F, record)                       # 0x447A
    imprime_bcd(v, 0x381C, (fase_bcd,))                  # 0x4495
    imprime_bcd(v, 0x3832, bonificacion)                 # 0x52A0
    de = 0x383D                                          # 0x44D4
    for k in range(1, 6):
        v.b[de] = 0x0B if vidas - k >= 0 else 0x00
        de -= 1


def marco_del_rotulo(v, desde=0xC0, hasta=0xE1):
    """Donde cae el rotulo grande en la tabla de nombres: las celdas con los
    patrones del rotulo (0xC0..0xE1, los sesenta que colorea el FILVRM de
    0x4351), medidas y no puestas a ojo. Devuelve (fila, col, alto, ancho) en
    celdas con una celda de margen."""
    # solo cuentan las filas donde el rotulo DOMINA (ocho celdas o mas en su
    # rango): una celda suelta del menu con un patron de ese rango no es el
    # rotulo, y llevarse la pantalla entera por ella es justo lo que se evita
    # y solo en el TERCIO del rotulo: los numeros de patron se repiten en los
    # tres tercios de SCREEN 2, y el menu de abajo usa 0xC0-0xE1 del tercio 2
    # para otra cosa
    filas, cols = [], []
    for f in range(24):
        en_fila = [c for c in range(32) if desde <= v.b[NOMBRES + f * 32 + c] <= hasta]
        if len(en_fila) >= 8 and (not filas or f // 8 == filas[0] // 8):
            filas.append(f)
            cols.extend(en_fila)
    f0, f1, c0, c1 = min(filas), max(filas), min(cols), max(cols)
    return f0 - 1, c0 - 1, f1 - f0 + 3, c1 - c0 + 3


def rotulo_del_juego(v, fn, esc=4):
    """El logotipo del juego -"Circus Charlie", en rojo y blanco- recortado
    de la pantalla de titulo montada desde la ROM, para la cabecera de la
    web. Ley de la serie: el rotulo se dibuja, no se captura."""
    f0, c0, alto, ancho = marco_del_rotulo(v)
    w, h = ancho * 8, alto * 8
    px = lienzo(w * esc, h * esc, (0, 0, 0))
    for f in range(alto):
        for c in range(ancho):
            t = v.b[NOMBRES + (f0 + f) * 32 + c0 + c]
            tercio = (f0 + f) // 8
            pinta_celda(px, w * esc, c * 8 * esc, f * 8 * esc,
                        v.b[PATRONES + tercio * 0x800 + t * 8:
                            PATRONES + tercio * 0x800 + t * 8 + 8],
                        v.b[COLOR + tercio * 0x800 + t * 8:
                            COLOR + tercio * 0x800 + t * 8 + 8], esc)
    png(w * esc, h * esc, px, fn)


ATRACCIONES = ("trapecio", "leon", "cuerda-floja", "bolas", "caballo")


def pinta_celda(px, w, x0, y0, patron, color, esc=1):
    for f in range(8):
        p, c = patron[f], color[f]
        tinta, fondo = PALETA[c >> 4], PALETA[c & 0x0F]
        for b in range(8):
            col = tinta if p & (0x80 >> b) else fondo
            for dy in range(esc):
                for dx in range(esc):
                    punto(px, w, x0 + b * esc + dx, y0 + f * esc + dy, col)


def celda(v, t, tercio=0):
    p = PATRONES + tercio * 0x800 + t * 8
    c = COLOR + tercio * 0x800 + t * 8
    return v.b[p:p + 8], v.b[c:c + 8]


def hoja(v, tercio, fn, cols=16, esc=2):
    w, h = cols * 8 * esc, (256 // cols) * 8 * esc
    px = lienzo(w, h)
    for t in range(256):
        pa, co = celda(v, t, tercio)
        pinta_celda(px, w, (t % cols) * 8 * esc, (t // cols) * 8 * esc, pa, co, esc)
    png(w, h, px, fn)


def rango(v, t0, n, fn, tercio=0, cols=10, esc=4):
    filas = (n + cols - 1) // cols
    w, h = cols * 8 * esc, filas * 8 * esc
    px = lienzo(w, h)
    for i in range(n):
        pa, co = celda(v, t0 + i, tercio)
        pinta_celda(px, w, (i % cols) * 8 * esc, (i // cols) * 8 * esc, pa, co, esc)
    png(w, h, px, fn)


def logotipo(v, fn, esc=6):
    """El logotipo de KONAMI, montado como lo monta 0x4B7D.

    Empieza en el patron 0x41 y los pinta CORRELATIVOS (`inc a` de 0x4B9C) en
    tres filas seguidas de 3, 11 y 12 celdas: veintiseis, del 0x41 al 0x5A. Es
    el mismo reparto, celda por celda, que usan Magical Tree (desde el 0x60) y
    Comic Bakery (desde el 0x40) para el mismo logotipo.
    """
    filas = [(0x41, 3), (0x44, 11), (0x4F, 12)]
    w, h = 12 * 8 * esc, 3 * 8 * esc
    px = lienzo(w, h)
    for r, (t0, n) in enumerate(filas):
        for i in range(n):
            pa, co = celda(v, t0 + i, 0)
            pinta_celda(px, w, i * 8 * esc, r * 8 * esc, pa, co, esc)
    png(w, h, px, fn)


def vram_con_los_sprites(rom):
    """0x5FD6: los patrones de sprite, que en las pantallas de menu NO estan.

    Esto arreglaba una imagen que se publicaba ENTERA NEGRA. La hoja de
    sprites se dibujaba de la VRAM de la pantalla de titulo, y ahi los 2048
    bytes de 0x1800 estan a cero -medido, y el volcado del emulador dice lo
    mismo-: el cartucho no los sube hasta que empieza una fase.

    Son dos bloques encadenados, los dos con el destino en la cabecera:

        0x61BA  909 bytes -> 1376 en 0x1800, los dibujos de las figuras
        0x5FCF  los del marco

    Cotejado contra el volcado de la atraccion del trampolin: 0 de 2048. Las
    otras cuatro atracciones AÑADEN los suyos encima (por ejemplo 0x6025
    descomprime 0x6323 sobre 0x1B20), asi que esta hoja es la base comun, no
    todo lo que llega a haber.
    """
    v = Vram()
    descomprime(v, rom, 0x61BA)                          # 0x5FD9
    descomprime(v, rom, 0x5FCF)                          # 0x5FDF
    return v


def pantalla_entera(v, fn, esc=2, con_sprites=False):
    """Los 256x192 puntos, con EL MISMO renderizador que se coteja.

    No se dibuja aqui a mano: se llama a tools/vram.py, que es el que esta
    medido contra la pantalla de openMSX punto por punto (las cinco
    atracciones, 49.152 de 49.152). Si el dibujante y el cotejador fueran dos
    trozos de codigo distintos, el verde del segundo no diria nada del primero.

    Las dos pantallas de menu no llevan NI UN sprite visible -comprobado en los
    volcados: la lista de 0x3B00 no tiene ninguno con color-, asi que lo
    dibujado es todo lo que hay.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import vram as V
    px = V.pantalla(v.b, VDP, con_sprites=con_sprites)
    if esc == 1:
        png(256, 192, px, fn)
        return
    w, h = 256 * esc, 192 * esc
    g = bytearray(w * h * 3)
    for y in range(h):
        fy = y // esc
        for x in range(w):
            i, j = (y * w + x) * 3, (fy * 256 + x // esc) * 3
            g[i:i + 3] = px[j:j + 3]
    png(w, h, g, fn)


def sprites(v, base, fn, n=16, cols=8, esc=3):
    filas = (n + cols - 1) // cols
    w, h = cols * 16 * esc, filas * 16 * esc
    px = lienzo(w, h)
    for i in range(n):
        d = base + i * 32
        x0, y0 = (i % cols) * 16 * esc, (i // cols) * 16 * esc
        for cuarto in range(4):
            cx, cy = (cuarto // 2) * 8 * esc, (cuarto % 2) * 8 * esc
            pinta_celda(px, w, x0 + cx, y0 + cy,
                        v.b[d + cuarto * 8: d + cuarto * 8 + 8], b"\xf0" * 8, esc)
    png(w, h, px, fn)


# El cuadro de cada foto en pista, contado desde el montaje (0x4C3C) en los
# vuelcos de sprites de 0x4CA9, con la flecha derecha pulsada: el instante en
# que se ve mejor el obstaculo de cada numero.
EN_PISTA = (100, 100, 150, 350, 50)


def en_pista(rom, tipo, cuadros, teclas=0x80):
    """La VRAM del cartucho EN MARCHA, `cuadros` despues del montaje."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from corre_circus import Circus, MONTADA, VUELCA_LOS_SPRITES
    m = Circus(rom)
    m.tipo = tipo
    m.arranca()
    cuenta = [-1]

    def montada(z):
        cuenta[0] = 0

    def vuelca(z):
        if cuenta[0] >= 0:
            cuenta[0] += 1

    m.paradas[MONTADA] = montada
    m.paradas[VUELCA_LOS_SPRITES] = vuelca
    f = 0
    while cuenta[0] < 0:                  # el menu: espacio a golpes
        m.espacio = (f % 100) < 20
        m.cuadro()
        f += 1
    m.espacio = False
    m.teclas = {8: teclas}
    while cuenta[0] < cuadros:
        m.cuadro()
    return bytes(m.vdp.vram), list(m.vdp.regs)


def main():
    global ORG
    rom = open(sys.argv[1], "rb").read()
    ORG = int(sys.argv[2], 0)
    sal = sys.argv[3]
    os.makedirs(sal, exist_ok=True)

    # LAS DOS PANTALLAS ENTERAS, que son las unicas imagenes de las que se
    # puede decir que son lo que el jugador ve: las dos estan cotejadas contra
    # el volcado de VRAM del emulador a CERO bytes de diferencia
    # (tools/coteja_vram.py).
    pantalla_entera(vram_de_la_presentacion(rom),
                    os.path.join(sal, "pantalla-presentacion.png"))
    pantalla_entera(vram_de_la_seleccion(rom),
                    os.path.join(sal, "pantalla-titulo.png"))

    v = vram_del_titulo(rom)
    logotipo(v, os.path.join(sal, "logotipo-konami.png"))
    hoja(v, 0, os.path.join(sal, "tiles.png"))
    hoja(v, 2, os.path.join(sal, "tiles-tercio3.png"))
    rango(v, 0xC0, 48, os.path.join(sal, "fuente-titulo.png"), tercio=2, cols=16, esc=4)
    # LOS SPRITES van en su propia VRAM: en la pantalla de titulo la tabla de
    # 0x1800 esta a cero, y dibujarla desde ahi daba una lamina entera NEGRA.
    sprites(vram_con_los_sprites(rom), SPRITES,
            os.path.join(sal, "sprites.png"), n=32, cols=8)

    # EL ROTULO DEL JUEGO, para la cabecera: recortado de la pantalla de
    # titulo con el marco medido sobre la tabla de nombres
    rotulo_del_juego(vram_de_la_seleccion(rom, cursor=False),
                     os.path.join(sal, "rotulo.png"))

    # LAS CINCO ATRACCIONES, montadas desde la ROM con la cadena entera de
    # 0x5FD6 y con el marcador tal como queda al empezar la partida. Cada una
    # esta cotejada a CERO bytes contra la VRAM que openMSX tiene en 0x4C3C
    # (tools/omsx_montaje.tcl + tools/coteja_montaje.py). Sin sprites: el
    # jugador y los bichos los pinta el juego cuadro a cuadro, no el montaje.
    for tipo, nombre in enumerate(ATRACCIONES):
        v = vram_de_la_atraccion(rom, tipo)
        pinta_el_marcador(v, rom)
        pantalla_entera(v, os.path.join(sal, "atraccion-%d-%s.png" % (tipo, nombre)))

    # Y LAS CINCO EN PISTA, con Charlie, su animal y los obstaculos. Esos no
    # los pone el montaje sino el juego cuadro a cuadro, asi que se EJECUTA el
    # cartucho (tools/corre_circus.py) y se fotografia su VRAM en el cuadro
    # elegido. Cotejado contra openMSX en tools/coteja_arranque.py: 0 bytes.
    for tipo, nombre in enumerate(ATRACCIONES):
        v, regs = en_pista(rom, tipo, EN_PISTA[tipo])
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import vram as V
        px = V.pantalla(v, regs, con_sprites=True)
        png(256, 192, px, os.path.join(sal, "en-pista-%d-%s.png" % (tipo, nombre)))

    for f in sorted(os.listdir(sal)):
        print("  ", os.path.join(sal, f))


if __name__ == "__main__":
    main()
