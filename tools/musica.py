#!/usr/bin/env python3
"""La musica del cartucho, ejecutando su motor de sonido (ver motor_musica.py).

Pide el sonido con `pide_un_sonido` (0x7BA2, A = numero) y corre
`suena_un_cuadro` (0x7A3D), que la interrupcion llama cada cuadro (0x4030). Tres
voces de 11 bytes desde 0xE010; la copia del registro 7 del PSG, en 0xE031.
Uso:  musica.py registros 0x8F [cuadros] | mp3 0x8F f.mp3 | todas docs/audio
      musica.py barrido 0x80 0xFF | emu
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motor_musica  # noqa: E402
from motor_musica import P  # noqa: E402

PIEZAS = [
    P(0x8F, "El sonido del final", "The ending sound",
      "`estado_por_la_tabla_5000`"),
]

PAGINA = motor_musica.pagina_basica(
    "`suena_un_cuadro`, 0x7A3D, y `pide_un_sonido`, 0x7BA2, que le reparte "
    "las voces; lo llama la interrupción en 0x4030",
    "`suena_un_cuadro`, 0x7A3D, and `pide_un_sonido`, 0x7BA2, which hands it "
    "the voices; the interrupt calls it at 0x4030",
    "C-BIOS MSX1 japonés",
    [("el sonido del final (0x8F) entera, 170 cuadros, "
      "pedida a la fuerza y en la partida tal como el juego la pide",
      "the ending sound (0x8F), whole, 170 frames, both forced and in "
      "the game as the game asks for it")],
    [("Lo que no se publica",
      "Es la única música que el listado pide con un `ld a` y que suena de "
      "verdad (el 0x94 del arranque es silencio y el 0x11 es un efecto). La "
      "tabla guarda además las pistas 0x88 a 0x90, y aquí no se publican "
      "porque el cotejo no cuadra: con la 0x8B pedida a la fuerza, openMSX "
      "y este motor dan lo mismo durante 229 cuadros y luego la duración de "
      "la primera nota es 232 cuadros en el emulador y 256 aquí. La causa no "
      "está resuelta. Lo más probable es que el juego deje en la RAM de las "
      "voces un valor, el paso de las notas (+10), que estas pistas no "
      "fijan y que aquí parte de cero, pero no se ha comprobado.",
      "What is not published",
      "It is the only music the listing asks for with an `ld a` that really "
      "sounds (0x94 at start-up is silence and 0x11 is an effect). The table "
      "also holds tracks 0x88 to 0x90, which are not published here because "
      "the check does not match: with 0x8B forced, openMSX and this engine "
      "agree for 229 frames and then the first note lasts 232 frames in the "
      "emulator and 256 here. The cause is unresolved. The likeliest is that "
      "the game leaves in the voices' RAM a value, the note step (+10), that "
      "these tracks do not set and that here starts at zero, but this has "
      "not been checked.")])

CFG = dict(rom="circus.rom", org=0x4000, frame=0x7A3D, pide=0x7BA2,
           ram=(0xE010, 0xE034), excluye=[0xE019, 0xE024, 0xE02F],
           ram0=[(0xE031, 0xB8)], hz=60, psg0={7: 0xB8}, piezas=PIEZAS,
           pagina=PAGINA, cotejado=[(0x8F, 170, None)])

if __name__ == "__main__":
    sys.exit(motor_musica.main(CFG, sys.argv[1:]))
