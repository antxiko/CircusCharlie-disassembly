# The music

Everything you hear here comes from running the cartridge's own sound engine (`suena_un_cuadro`, 0x7A3D, and `pide_un_sonido`, 0x7BA2, which hands it the voices; the interrupt calls it at 0x4030) on an emulated Z80, frame by frame at 60 per second, just as the game calls it. What the engine writes to the PSG is turned into sound with an AY-3-8910 (`tools/musica.py`). Each MP3 is the whole piece up to where it starts again, plus 8 seconds of the repeat fading out; those that do not repeat end where the engine ends.

## Checked against openMSX

The PSG writes have been compared frame by frame with those of openMSX (C-BIOS MSX1 japonés). In every frame the PSG ends up the same:

- the ending sound (0x8F), whole, 170 frames, both forced and in the game as the game asks for it;
- 0x89, whole, 1154 frames, and 0x8B, whole, 1538, with the step 6 that the game gives them;
- the first 384 frames of 0x8D, with step 4 (the piece lasts 3106 and goes back to frame 33; the game asks for it again at 384).

The timbre is not checked: it is a textbook AY-3-8910, not a recording of the emulator. The probes are `tools/omsx_psg.tcl` and `tools/coteja_psg.py`.

## The step that arrives in A'

These tracks do not set the length of their notes: it comes from a «step» that `pide_un_sonido` copies from register A' (the `ex af,af'` the game does just before calling). The game puts 6 in the stage-start tunes 0x89 and 0x8B, 4 in 0x8D, and 3 or 5 in the running-out-of-time warnings (the same score at another speed). With A' at zero the first note lasted 256 frames instead of 232 and the tracks did not match openMSX; with the game's A' they do. Only the stage-start versions are here; the time warnings (step 3 or 5) are not published. Tracks 0x88, 0x8A, 0x8C, 0x8E and 0x90 of the table are not asked for by any routine with an `ld a` and are not published.

## The tunes

**The stage start tune** (0x89)

Asked for by `L_60D8` (con el paso 6 en A') y, con el paso 3 o 5, `avisa_de_que_queda_poco`; lasts 19.2 s and starts again at second 0.0.

<audio controls preload="none" src="audio/musica_89.mp3?v=8050c4c4"></audio>

**The stage tune** (0x8B)

Asked for by `pon_al_jugador_en_su_sitio` (con el paso 6 en A') y, con el paso 5, `avisa_de_que_queda_poco`; lasts 25.6 s and starts again at second 0.0.

<audio controls preload="none" src="audio/musica_8B.mp3?v=8acc900b"></audio>

**The tune of another stage** (0x8D)

Asked for by `L_6161` (con el paso 4 en A') y, con el paso 3, `avisa_de_que_queda_poco`; lasts 51.8 s and starts again at second 0.6.

<audio controls preload="none" src="audio/musica_8D.mp3?v=9bccf081"></audio>

**The ending sound** (0x8F)

Asked for by `estado_por_la_tabla_5000`; lasts 2.8 s.

<audio controls preload="none" src="audio/musica_8F.mp3?v=30fd0f94"></audio>
