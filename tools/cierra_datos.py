#!/usr/bin/env python3
"""Mide donde acaba cada bloque de datos EJECUTANDO el interprete que lo lee.

El presupuesto exige que todo byte del cartucho este explicado. Los bloques
grandes de Yie Ar Kung-Fu no son volcados: son GUIONES (el interprete de
0x442c) y LISTAS DE TILES (el de 0x44a6), y los dos tienen su propio byte de
fin. Asi que no hay que adivinar donde acaban: se ejecutan.

Lo que hace:

  1. Recorre el listado buscando las llamadas a los dibujadores, y se queda con
     la constante que el codigo acababa de cargar en DE. Esos son los arranques
     CIERTOS, los que el propio cartucho usa.
  2. Ejecuta el interprete que toque desde cada arranque y anota los bytes que
     consume. Los guiones encadenan con 0x80 y las listas con 0xFE: el rango
     que sale es el de verdad, no una estimacion.
  3. Junta lo consumido y lo compara con los huecos del presupuesto.

Uso: cierra_datos.py <listado.asm> <rom> [--notes]
     con --notes escribe directivas D listas para pegar en el .notes.
"""
import re
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])
import guiones

ORG = 0x4000

# Los dibujadores del cartucho y por que registro entra el dato. Las
# direcciones salen del listado; los nombres, de las notas.
DIBUJADORES = {
    0x4423: ("guion", "encadena_el_guion"),
    0x4429: ("guion", "dibuja_el_guion"),
    0x4452: ("guion", "dibuja_el_guion_en_el_puerto_cero"),
    0x44CA: ("guion", "dibuja_en_dos_tercios"),
    0x44CE: ("guion", "dibuja_en_los_tres_tercios"),
    0x449A: ("lista", "dibuja_la_lista_sin_encadenar"),
    0x449E: ("lista", "dibuja_la_lista"),
    0x44A0: ("lista", "encadena_la_lista"),
    0x44B5: ("lista", "borra_la_lista"),
}

CARGA_DE = re.compile(r"^\s*ld\s+de,0([0-9a-f]{4})h\s*;([0-9a-f]{4})", re.I)
CARGA_HL = re.compile(r"^\s*ld\s+hl,0([0-9a-f]{4})h\s*;([0-9a-f]{4})", re.I)
LLAMADA = re.compile(r"^\s*(?:call|jp|jr)\s+(?:[a-z]{1,2},\s*)?"
                     r"(?:L_([0-9A-F]{4})|0([0-9a-f]{4})h|([a-z_][a-z_0-9]*))"
                     r"\s*;([0-9a-f]{4})", re.I)

# `add a,a / call suma_a_hl / ld e,(hl) / inc hl / ld d,(hl) / ret`: DE sale de
# la tabla de punteros que traiga HL, indexada por A. O sea que el arranque no
# es una constante sino TODAS las entradas de esa tabla.
INDEXA = 0x4CE8

# Lo que rompe el rastro de DE: se lo cargan de otro sitio.
PIERDE_DE = re.compile(r"^\s*(pop\s+de|ex\s+de,hl|ld\s+de,\(|ld\s+[de],[^,]*\(|"
                       r"ld\s+[de],[a-l]\b|inc\s+de|dec\s+de|add\s+hl,de)", re.I)


def lista(rom, pos):
    """El cuerpo de 0x44a6. Devuelve la posicion tras el ultimo byte.

    Un byte por vuelta: 0xFF acaba, 0xFE encadena -y los dos siguientes son
    una direccion de VRAM, byte bajo primero-, y cualquier otro es un tile.
    """
    vistos = set()
    while True:
        if pos < ORG or pos > ORG + len(rom) - 1:
            return None
        if pos in vistos:
            return None
        vistos.add(pos)
        b = rom[pos - ORG]
        pos += 1
        if b == 0xFF:
            return pos
        if b == 0xFE:
            pos += 2


def guion(rom, pos):
    """El cuerpo de 0x442c, con red por si el arranque no era un guion."""
    try:
        fin = guiones.cuerpo(rom, pos)
    except IndexError:
        return None
    return fin if ORG <= fin <= ORG + len(rom) else None


def etiquetas(texto):
    """Las etiquetas del listado y su direccion, para resolver los `call nombre`."""
    m = {}
    pendiente = None
    for linea in texto.splitlines():
        e = re.match(r"^([a-zA-Z_][a-zA-Z_0-9]*):", linea)
        if e:
            pendiente = e.group(1)
            continue
        d = re.search(r";([0-9a-f]{4})\s*(?:;|$|\|)", linea)
        d = re.search(r";([0-9a-f]{4})", linea)
        if d and pendiente:
            m[pendiente] = int(d.group(1), 16)
            pendiente = None
    return m


def entradas_de_la_tabla(rom, dir_):
    """Los punteros de una tabla que acaba donde empieza su primer destino.

    Es la regla que ya usan las nueve tablas de despacho declaradas en el
    .entries: se leen palabras mientras caigan dentro del cartucho, y la tabla
    no puede seguir mas alla del mas bajo de los destinos que ya ha dado.
    """
    fuera, pos, tope = [], dir_, 0x8000
    while pos + 1 < 0x8000 and pos < tope:
        p = rom[pos - ORG] | (rom[pos + 1 - ORG] << 8)
        if not 0x4000 <= p < 0x8000:
            break
        fuera.append(p)
        tope = min(tope, p)
        pos += 2
    return fuera


def arranques(texto, rom):
    """(direccion_del_dato, clase, quien_lo_llama) de cada dibujado del listado.

    Dos vias: la constante que el codigo carga en DE, y -cuando DE sale de
    0x4CE8- todas las entradas de la tabla de punteros que traia HL.
    """
    etiq = etiquetas(texto)
    fuera = []
    de = hl = None
    tablas = []
    for linea in texto.splitlines():
        c = CARGA_DE.match(linea)
        if c:
            de = int(c.group(1), 16)
            continue
        h = CARGA_HL.match(linea)
        if h:
            hl = int(h.group(1), 16)
            continue
        if PIERDE_DE.match(linea):
            # DE deja de valer, pero la tabla que lo lleno sigue siendo la
            # candidata: el cartucho apila DE, indexa otra tabla para la VRAM y
            # lo desapila justo antes de dibujar.
            de = None
            continue
        l = LLAMADA.match(linea)
        if not l:
            continue
        if l.group(1):
            destino = int(l.group(1), 16)
        elif l.group(2):
            destino = int(l.group(2), 16)
        else:
            destino = etiq.get(l.group(3))
        if destino == INDEXA:
            de = None
            if hl is not None and hl not in tablas:
                tablas.append(hl)
            continue
        if destino in DIBUJADORES:
            clase, nombre = DIBUJADORES[destino]
            desde = int(l.group(4), 16)
            if de is not None:
                fuera.append((de, clase, desde, nombre))
            else:
                # Las tablas que no apuntan al cartucho -las de direcciones de
                # VRAM- se caen solas: entradas_de_la_tabla no les da ninguna.
                for t in tablas:
                    for p in entradas_de_la_tabla(rom, t):
                        fuera.append((p, clase, desde, f"{nombre}, tabla 0x{t:04X}"))
            continue
        # cualquier otra llamada puede tocar DE; el rastro se corta
        de = None
        tablas = []
    return fuera


def main():
    asm, rom_f = sys.argv[1], sys.argv[2]
    con_notas = "--notes" in sys.argv
    texto = open(asm, encoding="utf-8").read()
    rom = open(rom_f, "rb").read()

    consumido = bytearray(len(rom))
    rangos = []
    for dir_, clase, desde, nombre in arranques(texto, rom):
        fin = guion(rom, dir_) if clase == "guion" else lista(rom, dir_)
        if fin is None:
            print(f"  0x{dir_:04X}  {clase:6}  NO SE PUEDE LEER  (desde 0x{desde:04X})")
            continue
        for a in range(dir_, fin):
            consumido[a - ORG] = 1
        rangos.append((dir_, fin, clase, desde, nombre))

    rangos.sort()
    visto = set()
    for dir_, fin, clase, desde, nombre in rangos:
        if (dir_, fin) in visto:
            continue
        visto.add((dir_, fin))
        print(f"  0x{dir_:04X}..0x{fin:04X}  ({fin - dir_:5} bytes)  {clase:6}"
              f"  leido desde 0x{desde:04X} ({nombre})")

    total = sum(consumido)
    print(f"\n  {total} bytes consumidos por los interpretes "
          f"({100.0 * total / len(rom):.2f} % del cartucho)")

    if con_notas:
        print("\n--- para el .notes ---")
        for dir_, fin, clase, desde, nombre in rangos:
            if (dir_, fin) not in visto:
                continue
            print(f"D 0x{dir_:04x} 0x{fin:04x} {clase}_{dir_:04x}  "
                  f"Lo dibuja {nombre} desde 0x{desde:04X}")


if __name__ == "__main__":
    main()
