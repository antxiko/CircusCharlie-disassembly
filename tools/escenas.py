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
se suma al puntero del BUFER (`ld de,0e280h` y luego L_4027): la fila se pinta
desde ese byte del trozo, no desde el principio.

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


# ---------------------------------------------------------------- MONTAR
# EL BUFER DE 0xE280 ES RAM, Y SE QUEDA CON LO QUE HABIA. Cada trozo se
# descomprime encima desde el principio, pero lo que el trozo no cubre sigue
# ahi; y prepara_la_figura (0x467B) escribe DENTRO del bufer antes de que se
# pinte: el espejo del dibujo si C lleva alguno de sus dos bits altos, y
# siempre tres copias desplazadas dos, cuatro y seis pixeles, una altura mas
# arriba cada una. Como pinta_el_bufer lee el bufer DESPUES, esas copias son
# lo que se ve. Y 0x5770 saca de aqui, ya acabada la escena de 0x6D0A, el
# patron 0x51 con el desplazamiento que toque.
BUFER = bytearray(0x400)
PAREJAS = []


def rota_el_bufer_un_bit(hueco, b):
    """0x46E1: los B bytes del hueco, de atras hacia delante, un bit a la
    izquierda con el acarreo encadenado; lo que sale por la izquierda del
    primero entra por la derecha del ultimo (`dec hl / inc (hl)`)."""
    acarreo = 0
    for i in range(b - 1, -1, -1):
        viejo = hueco[i]
        hueco[i] = ((viejo << 1) | acarreo) & 0xFF
        acarreo = viejo >> 7
    if acarreo:
        hueco[b - 1] = (hueco[b - 1] + 1) & 0xFF


def espeja_patrones(buf, c):
    """0x4647 (bautizado transpone_patrones, pero lo que hace es un ESPEJO):
    de cada byte saca los ocho bits del reves (`rlc (hl) / rra` ocho veces),
    o sea que da la vuelta a cada fila; los patrones salen de
    0xE280 + (C & 7) * 8 y van a 0xE288 + (C & 0x38), y cada uno siguiente
    16 bytes mas ABAJO (+0xF0 y `dec d`), tantos como digan los dos bits de
    arriba de C."""
    cuantos = c >> 6                              # A = C & 0xC0, rlca / rlca
    de = 8 + (c & 0x38)
    hl = (c & 0x07) * 8
    for _ in range(cuantos):
        for k in range(8):
            if de + k >= 0:                       # por debajo de 0xE280 no es el bufer
                buf[de + k] = int("{:08b}".format(buf[hl + k])[::-1], 2)
        hl += 8
        de -= 8                                   # +8 escritos, -16


def prepara_la_figura(buf, b, c):
    """0x467B: B es la altura en patrones y C trae el espejo (bits 7-6) y la
    variante. Se saca cada COLUMNA del dibujo -el byte j de cada uno de los B
    patrones- al hueco de paso, se desplaza dos bits tres veces y cada pasada
    se deja una altura mas arriba: copias del dibujo movido 2, 4 y 6 pixeles.
    """
    altura = (b * 8) & 0xFF
    if c & 0xC0:
        espeja_patrones(buf, c)
    hueco = bytearray(0x40)
    for j in range(8):                            # ocho patrones (columnas)
        for k in range(b):
            hueco[k] = buf[j + 8 * k]
        iy = altura + j
        for _ in range(3):                        # gira_tres_veces
            rota_el_bufer_un_bit(hueco, b)        # desplaza_el_bufer: dos
            rota_el_bufer_un_bit(hueco, b)
            for k in range(b):
                buf[iy + 8 * k] = hueco[k]
            iy += altura


def monta(rom, org, ini, vram, variante=0x42):
    """Ejecuta la escena DE VERDAD, escribiendo en la VRAM.

    Lo de arriba solo MIDE -recorre el guion para saber donde acaba-. Esto
    ademas pinta, que es lo que hace falta para dibujar un nivel desde la ROM.

    El bucle es el de 0x6A42:

        0x6A51  descomprime un trozo al bufer de 0xE280
        0x69D5  lee B y C y llama a prepara_la_figura (0x467B)
        0x69DF  vuelca el bufer a la VRAM por MASCARAS DE OCHO BITS

    Y LA CLAVE, que estaba mal leida en el comentario de arriba: los ocho
    bytes que se escriben salen del BUFER, no del guion. En 0x6A1E hay un
    `ex de,hl` que pone HL en el bufer y DE en el guion, asi que el guion solo
    lleva las mascaras; cada bit a uno vuelca un patron -ocho bytes- y el
    bufer avanza ocho EN LOS DOS CASOS (`add hl,bc` esta fuera del `call c`).
    O sea que la mascara elige CUALES de los ocho patrones se escriben, y los
    elegidos van seguidos desde el destino.

    Cada fila reinicia el bufer (`ld de,0e280h` en 0x69F2), asi que todas las
    filas eligen del mismo trozo descomprimido.

    prepara_la_figura NO se reimplementa, y es correcto: sus tres pasadas de
    giro escriben copias del dibujo MAS ARRIBA en el bufer (0xE280 + altura*8,
    +2 y +3), para poder pintar la figura desplazada un bit, dos y tres. El
    trozo original no lo toca. Lo unico que si lo tocaria es
    `transpone_patrones` (0x468E), y solo se llama cuando los dos bits de
    arriba de C estan puestos.
    """
    global PAREJAS
    p = ini
    PAREJAS = []
    for _ in range(64):
        f, datos = descomprime_ram(rom, org, p)
        if f is None:
            return None
        BUFER[0:len(datos)] = datos         # 0x6A51: encima de lo que habia
        b, c = rom[f - org], rom[f - org + 1]
        PAREJAS.append((b, c))
        prepara_la_figura(BUFER, b, c)      # 0x69D5 -> 0x467B
        bufer = BUFER
        p = f + 2                           # los dos bytes de 0x69D5
        p = _vuelca(rom, org, p, vram, bufer, variante)
        if p is None or p - org >= len(rom):
            return None
        if rom[p - org] == 0x00:
            return p + 1
    return None


def _vuelca(rom, org, p, vram, bufer, variante):
    """0x69DF (o 0x69FB): las filas, y por cada fila sus mascaras."""
    pagina = 0
    if variante == 0x42:
        pagina = rom[p - org]               # ld d,(hl)
        p += 1
    while True:
        fila = rom[p - org]
        p += 1
        if fila == 0x00:                    # or a / ret z
            return p
        d = pagina if variante == 0x42 else 0x05
        destino = ((d << 8) | fila) * 8
        destino = (destino | 0x4000) & 0x3FFF      # set 6,d, y el VDP ve 14 bits
        desde = 0
        if variante != 0x42:
            # 0x6A10: el byte de ajuste se suma a DE DESPUES del `ld de,0e280h`
            # de 0x6A0D, o sea al puntero del BUFER, no al destino: elige desde
            # que byte del trozo se empieza a pintar esta fila
            desde = rom[p - org]
            p += 1
        p, destino = _mascaras(rom, org, p, vram, bufer, destino, desde)
        if p is None:
            return None


def _mascaras(rom, org, p, vram, bufer, destino, desde=0):
    """0x6A1A: mascaras de ocho bits, un bit por patron."""
    pos = desde                             # ld de,0e280h (+ el ajuste, por 0x69FB)
    while True:
        mascara = rom[p - org]
        p += 1
        for _ in range(8):                  # ld b,008h
            bit = (mascara >> 7) & 1        # rl c
            mascara = (mascara << 1) & 0xFF
            if bit:
                for i in range(8):          # copia_literal, ocho bytes
                    if pos + i < len(bufer):
                        vram[destino & 0x3FFF] = bufer[pos + i]
                        destino += 1
            pos += 8                        # add hl,bc, se escriba o no
        if rom[p - org] == 0x00:            # ld a,(hl) / or a / jr nz
            return p + 1, destino
