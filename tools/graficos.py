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


def decorado_de_la_fase_1(v, rom):
    """0x6D97, el de la cuerda floja. Y 0x7149 detras, que lo apila el
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


def vram_de_la_atraccion(rom, tipo=0):
    """LO COMUN A LAS CINCO ATRACCIONES: la cadena de 0x6968.

    ESTADO: INCOMPLETO, y aqui esta dicho para que nadie lo publique creyendo
    que es la pantalla. Monta la cadena comun y, del reparto por tipo de fase
    (la tabla de cinco de 0x5FEF), solo el decorado de la fase 1. Falta el
    remate de 0x699D, que el despachador apila antes de saltar:

        0x69A1  elige_el_decorado_alterno   0x6AC1 o 0x6AC6
        0x69B9  pinta_bloque_en_su_sitio    el fondo, fila a fila
        0x69BF  monta_escena 0x6D0A
        0x69C5  pinta_la_figura_grande

    NO depende del estado del juego -eso se comprobo y es que no-: los tres
    parametros son CONSTANTES del propio remate (0x1000/0x1800/0x2013, o
    0x6800/0x7000/0x200A segun `que_dibujo_toca`), y `posicion_a_celda`
    (0x53F3) trabaja solo con D y E, sin leer una sola direccion de RAM. O sea
    que se PUEDE montar desde la ROM; lo que falta es implementar esas dos
    rutinas, que es trabajo pendiente y no un imposible.

    Y una cosa que hay que leer con cuidado al hacerlo: en el bucle de
    0x6A91 el `inc hl` esta FUERA del `djnz`, asi que cada fila del bloque se
    pinta con UN solo patron repetido B veces, y solo al cambiar de fila se
    coge el siguiente.

    Lo que SI esta cerrado es el motor: tools/escenas.py ejecuta ahora la
    maquina de escenas, y lo que la escena del nivel escribe coincide al
    100 % con el volcado de la atraccion del monociclo -167 bytes de 167- y al
    96 % con otras tres.

    Esto es el decorado que comparten las cinco; encima, cada tipo de fase
    monta el suyo (la tabla de cinco de 0x5FEF).

        0x696B  monta_escena 0x6BE3          la escena del nivel
        0x6978  vuelca_patrones_repetidos    desde 0x6D1A, a la VRAM 0x4200
        0x697B  descomprime_donde_quedo      con el MISMO puntero
        0x697E  vuelca_lista_de_patrones     idem
        0x6987  copia_a_los_tres_tercios     648 bytes
        0x698A  monta_la_franja_de_abajo     0x72ED + sus patrones en 0x1680
        0x6997  y, solo en los tipos 0 y 2, otros 1.016 bytes a los tres
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import escenas as E
    v = vram_con_los_sprites(rom)                        # 0x5FD6
    E.monta(rom, ORG, 0x6BE3, v.b, 0x42)                 # 0x696B
    v.situa(0x4200)                                      # 0x6971
    fin = vuelca_patrones_repetidos(v, rom, 0x6D1A)      # 0x6978
    fin = descomprime(v, rom, fin, cabecera=False)       # 0x697B
    vuelca_patrones_repetidos(v, rom, fin)               # 0x697E
    copia_a_los_tres_tercios(v, 0x0000, 0x0288)          # 0x6987
    E.monta(rom, ORG, 0x72ED, v.b, 0x42)                 # 0x72E4
    v.situa(0x1680)                                      # 0x72E7
    vuelca_patrones_repetidos(v, rom, 0x7335)            # 0x72EA
    if que_dibujo_toca(tipo):                            # 0x698D
        copia_a_los_tres_tercios(v, 0x0288, 0x03F8)      # 0x6997
    # y encima, el decorado de SU tipo: la tabla de cinco de 0x5FEF
    if tipo == 1:
        decorado_de_la_fase_1(v, rom)                    # 0x5FF9
    return v


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

    for f in sorted(os.listdir(sal)):
        print("  ", os.path.join(sal, f))


if __name__ == "__main__":
    main()
