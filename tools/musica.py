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
    P(0x89, "La música de arranque de la fase", "The stage start tune",
      "`L_60D8` (con el paso 6 en A') y, con el paso 3 o 5, "
      "`avisa_de_que_queda_poco`"),
    P(0x8B, "La música de la fase", "The stage tune",
      "`pon_al_jugador_en_su_sitio` (con el paso 6 en A') y, con el paso 5, "
      "`avisa_de_que_queda_poco`"),
    P(0x8D, "La música de otra fase", "The tune of another stage",
      "`L_6161` (con el paso 4 en A') y, con el paso 3, "
      "`avisa_de_que_queda_poco`"),
    P(0x8F, "El sonido del final", "The ending sound",
      "`estado_por_la_tabla_5000`"),
]

PAGINA = motor_musica.pagina_basica(
    "`suena_un_cuadro`, 0x7A3D, y `pide_un_sonido`, 0x7BA2, que le reparte "
    "las voces; lo llama la interrupción en 0x4030",
    "`suena_un_cuadro`, 0x7A3D, and `pide_un_sonido`, 0x7BA2, which hands it "
    "the voices; the interrupt calls it at 0x4030",
    "C-BIOS MSX1 japonés",
    [("el sonido del final (0x8F) entero, 170 cuadros, "
      "pedida a la fuerza y en la partida tal como el juego la pide",
      "the ending sound (0x8F), whole, 170 frames, both forced and in "
      "the game as the game asks for it"),
     ("la 0x89 entera, 1154 cuadros, y la 0x8B entera, 1538, con el paso 6 "
      "que les da el juego",
      "0x89, whole, 1154 frames, and 0x8B, whole, 1538, with the step 6 "
      "that the game gives them"),
     ("los primeros 384 cuadros de la 0x8D, con el paso 4 (la pieza dura "
      "3106 y vuelve al cuadro 33; el juego la vuelve a pedir a los 384)",
      "the first 384 frames of 0x8D, with step 4 (the piece lasts 3106 and "
      "goes back to frame 33; the game asks for it again at 384)")],
    [("El paso que llega en A'",
      "Estas pistas no fijan la duración de sus notas: la duración sale de un "
      "«paso» que `pide_un_sonido` copia del registro A' (el `ex af,af'` que "
      "el juego hace justo antes de llamar). El juego pone 6 en las músicas "
      "0x89 y 0x8B de arranque de fase, 4 en la 0x8D, y 3 o 5 en los avisos "
      "de que se acaba el tiempo (la misma partitura, a otra velocidad). Con "
      "el A' a cero la primera nota duraba 256 cuadros en vez de 232 y las "
      "pistas no cuadraban con openMSX; con el A' del juego, sí. Aquí sólo "
      "están las versiones de arranque de fase; los avisos de tiempo (paso 3 "
      "o 5) no se publican. Las pistas 0x88, 0x8A, 0x8C, 0x8E y 0x90 de la "
      "tabla no las pide ninguna rutina con un `ld a` y no se publican.",
      "The step that arrives in A'",
      "These tracks do not set the length of their notes: it comes from a "
      "«step» that `pide_un_sonido` copies from register A' (the "
      "`ex af,af'` the game does just before calling). The game puts 6 in "
      "the stage-start tunes 0x89 and 0x8B, 4 in 0x8D, and 3 or 5 in the "
      "running-out-of-time warnings (the same score at another speed). With "
      "A' at zero the first note lasted 256 frames instead of 232 and the "
      "tracks did not match openMSX; with the game's A' they do. Only the "
      "stage-start versions are here; the time warnings (step 3 or 5) are "
      "not published. Tracks 0x88, 0x8A, 0x8C, 0x8E and 0x90 of the table "
      "are not asked for by any routine with an `ld a` and are not "
      "published.")])

CFG = dict(rom="circus.rom", org=0x4000, frame=0x7A3D, pide=0x7BA2,
           ram=(0xE010, 0xE034), excluye=[0xE019, 0xE024, 0xE02F],
           ram0=[(0xE031, 0xB8)], regs_pide_de={0x89: {"af_": 0x0600},
                         0x8B: {"af_": 0x0600}, 0x8D: {"af_": 0x0400}},
           hz=60, max_s=60, psg0={7: 0xB8}, piezas=PIEZAS,
           pagina=PAGINA, cotejado=[(0x8F, 170, None), (0x89, 1154, 1), (0x8B, 1538, 1)])

if __name__ == "__main__":
    sys.exit(motor_musica.main(CFG, sys.argv[1:]))
