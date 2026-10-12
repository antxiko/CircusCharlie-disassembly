# The music

Everything you hear here comes from running the cartridge's own sound engine (`suena_un_cuadro`, 0x7A3D, and `pide_un_sonido`, 0x7BA2, which hands it the voices; the interrupt calls it at 0x4030) on an emulated Z80, frame by frame at 60 per second, just as the game calls it. What the engine writes to the PSG is turned into sound with an AY-3-8910 (`tools/musica.py`). Each MP3 is the whole piece up to where it starts again, plus 8 seconds of the repeat fading out; those that do not repeat end where the engine ends.

## Checked against openMSX

The PSG writes have been compared frame by frame with those of openMSX (C-BIOS MSX1 japonés). In every frame the PSG ends up the same:

- the ending sound (0x8F), whole, 170 frames, both forced and in the game as the game asks for it.

The timbre is not checked: it is a textbook AY-3-8910, not a recording of the emulator. The probes are `tools/omsx_psg.tcl` and `tools/coteja_psg.py`.

## What is not published

It is the only music the listing asks for with an `ld a` that really sounds (0x94 at start-up is silence and 0x11 is an effect). The table also holds tracks 0x88 to 0x90, which are not published here because the check does not match: with 0x8B forced, openMSX and this engine agree for 229 frames and then the first note lasts 232 frames in the emulator and 256 here. The cause is unresolved. The likeliest is that the game leaves in the voices' RAM a value, the note step (+10), that these tracks do not set and that here starts at zero, but this has not been checked.

## The tunes

**The ending sound** (0x8F)

Asked for by `estado_por_la_tabla_5000`; lasts 2.8 s.

<audio controls preload="none" src="audio/musica_8F.mp3?v=30fd0f94"></audio>
