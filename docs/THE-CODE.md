# The code

## The whole game lives inside the interrupt

INIT sets mode 1, hooks H.KEYI (`0xFD9A`) with a `jp 0x402C`, clears the RAM
and then sits forever on the `jr $` at `0x40A9`. Everything else happens in the
hook, once per frame: sound first, then the controls, then the scene. The lock
at `0xE005` counts overlapping interrupts: if a frame runs long, the next one
is served on the way out, without going back through the stack.

## Tables sit right behind the `call`

`despacha_por_tabla` (`0x404E`) takes its own return address with `pop hl`,
and that is where the table starts. That is how the scenes are dispatched, and
the five set-ups (`0x5FEF`), the five starts (`0x60B6`) and the five frames
(`0x4C93`).

## Three data machines

Rewritten in Python in `tools/`:

- `rle.py`, the decompressor at `0x45C9`: `0nnnnnnn b` repeats and
  `1nnnnnnn b…` copies; `0x80` changes the destination and `0x00` ends. A
  second decompressor with the same language writes to RAM (`0x6A51` →
  `0xE280`), and a third one (`0x7567`) reads the bits backwards.
- `guiones.py`, the text-script interpreter at `0x4062`: `[destination]
  [indices…]`, `0xFE` jumps and `0xFF` ends. With the mask at `0x00`, **the
  same script erases** what it drew.
- `escenas.py`: decompresses into the buffer and copies it out through
  eight-bit masks, one bit per pattern, so it can repaint half the screen
  without touching the other half. `0x4647` mirrors the patterns and `0x467B`
  makes three copies shifted by 2, 4 and 6 pixels.

## And the cartridge, running

`tools/corre_circus.py` runs INIT up to the `jr $` and then the hook once per
frame, on the small Z80 in `tools/z80run.py`, which stops dead on any opcode
it does not know. The seven BIOS routines are imitated in Python. Against
openMSX, five acts at ten instants each: **0 VRAM bytes different** (`make
coteja_arranque`). The RAM only differs in the music and in the menu's
curtain.
