# Findings

1. **The headings of three tables were off by one.** Those at `0x5FEF`,
   `0x60B6` and `0x4C93` were numbered as if the index started at 1. The RAM
   measured at the start of each act gave it away: the `0x5C8E` script shows
   up in the horse act, not the balls, and the frame at `0x4CC2` is the
   trapeze's.
2. **Type 0 is the trapeze**, not a trampoline: the trampoline is just the
   floor.
3. **Two errata that made the scenery repeat.** `0x458F` reads through DE and
   writes through HL, the other way round from what it looked like. That is
   why `0x7477` copies `0x2AC0` **over** `0x2BB0`, overlapping, and the horse
   act's scenery repeats every 240 bytes.
4. **The "1P" blink does not look at the number of players.** The
   `ld hl,(0xE002)` brings the flags in L and the **frame counter in H**; the
   `bit 5,h` flips the mask every 32 frames.
5. **The table at `0x4CEA` has ten entries, not five.** Two are `0x0000`, and
   two others point at the only pieces of code no instruction reached.
6. **`0x462F` repeats a pattern by stepping back**: `[N][eight bytes]` writes
   that pattern N times, because the loop goes back eight before repeating.
   Its caller does not load its address; it carries on from the HL the
   previous scene left behind.
7. **Each act's VRAM is inherited from the menu**: only the name table is
   cleared. Building it from scratch does not give zero bytes; starting from
   the menu does.
8. **Four sprites per line, and the fifth is not drawn.** On the trapeze six
   of them cross lines 48 to 52, and the VDP drops two. Without that limit the
   comparison against the picture does not reach zero; with it, 49,152 dots
   out of 49,152.
9. **Seven orphan bytes**: they disassemble into sensible instructions, but
   nothing reaches them.
10. **It is the same code as Magical Tree, shifted.** The fourteen-byte
    signature of the decompressor loop (`0x45D1` here) shows up unchanged in
    RC-713, and with it the text-script interpreter and the scene
    dispatcher.
