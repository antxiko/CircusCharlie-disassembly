#!/usr/bin/env python3
"""Deduce el tamano de cada tabla de punteros que sigue a un CALL despachador.

El armazon de este cartucho despacha asi (0x406C):

    pop hl          ; la direccion de retorno ES la tabla
    add a,a
    call 0x405B     ; HL += A
    ld e,(hl) / inc hl / ld d,(hl) / ex de,hl / jp (hl)

O sea que detras de cada `call 0x406C` hay una tabla de palabras. Cuantas, no
lo dice nadie: se deduce con la regla de siempre —**la entrada mas
baja es el final de la tabla**—, porque el codigo al que apunta viene justo
despues.

Con dos matices que este cartucho obligo a anadir, porque hay tablas que saltan
HACIA ATRAS, a codigo compartido muy anterior:

  1. Solo cierran la tabla los destinos que caen POR DELANTE de ella. Si a la
     entrada 0x8000 de la tabla de 0x8937 se le deja fijar el tope, la tabla se
     corta en la primera palabra y el trazado se queda sin media ROM.
  2. Una entrada hacia atras solo se acepta si esa direccion aparece ademas como
     destino de un call/jp en algun sitio del cartucho. Es lo que separa la
     0x8000 de la tabla de 0x8937 -llamada desde 0x4D4B con `call nz`- de la
     falsa 0x5421 que aparecia al final de la de 0x8041, que no es una entrada
     sino los bytes 21 54 de un `ld hl,0xE154`.

Verificado a mano en las tres que la regla cruda fallaba: 0x7E90 (8, ya estaba
bien), 0x8041 (6, no 7) y 0x8937 (7, no 1). Ver el .notes.

Uso: tablas_despacho.py <rom> <org> <dir_despachador>
"""
import sys


# Los opcodes que llevan una direccion de 16 bits detras: call/jp, con y sin
# condicion. Sirven para saber si una direccion es codigo al que ya salta
# alguien, que es lo que valida las entradas hacia atras de una tabla.
SALTOS = ({0xCD, 0xC3}
          | {0xC4, 0xCC, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC}
          | {0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA})


def destinos_de_saltos(rom, org):
    """Toda direccion que aparece detras de un call/jp en el cartucho."""
    d = set()
    for i in range(len(rom) - 2):
        if rom[i] in SALTOS:
            d.add(rom[i + 1] | (rom[i + 2] << 8))
    return d


def main():
    rom = open(sys.argv[1], "rb").read()
    org = int(sys.argv[2], 0)
    desp = int(sys.argv[3], 0)
    fin = org + len(rom)
    pat = bytes([0xCD, desp & 0xFF, desp >> 8])
    saltados = destinos_de_saltos(rom, org)

    llamadas = [i + org for i in range(len(rom) - 2) if rom[i:i + 3] == pat]
    print("# %d llamadas a %04X" % (len(llamadas), desp))
    for c in llamadas:
        t = c + 3                      # la tabla empieza tras el CALL
        n, tope = 0, fin
        while True:
            p = t + n * 2
            if p + 1 >= tope:
                break
            w = rom[p - org] | (rom[p + 1 - org] << 8)
            if not (org <= w < fin):   # deja de parecer un puntero
                break
            if w > t:                  # solo los destinos POR DELANTE cierran:
                tope = min(tope, w)    # los saltos hacia atras no dicen nada
            elif w not in saltados:    # y hacia atras solo vale si es codigo
                break                  # al que ya salta alguien
            n += 1
            if t + n * 2 >= tope:      # ya hemos llegado al codigo apuntado
                break
        dest = [rom[t + i * 2 - org] | (rom[t + i * 2 + 1 - org] << 8)
                for i in range(n)]
        print("!tabla 0x%04x %3d   # tras el `call %04Xh` de 0x%04X; "
              "sigue en 0x%04X" % (t, n, desp, c, min(dest) if dest else 0))


if __name__ == "__main__":
    main()
