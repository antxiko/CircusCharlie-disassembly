# Getting started

This repository holds the commented disassembly of Konami's **Circus Charlie**
for the MSX (RC-712, 1984). It does not hold the cartridge: the ROM image is
not distributed.

## What you need

- `pasmo` — the assembler that rebuilds the ROM
- `z80dasm` — the disassembler that generates the listing
- `python3` — the tools in `tools/`
- `make`
- Your own copy of the cartridge, in the root, named `circus.rom`

It is **exactly 16,384 bytes** and its fingerprint is:

    sha256  89e1badac10e65886590d55e735ed794e5ca3c41142e6637b3e7ac6b25d042c0

To check it:

    make comprueba

## Rebuilding all of it

| command | what it does | what it proves |
|---|---|---|
| `make listado` | traces the flow and generates `src/circus.asm` with the notes | that the listing comes from the cartridge and `src/circus.notes`, not hand edits |
| `make verify` | reassembles with `pasmo` and compares | that the listing IS the ROM, byte for byte |
| `make sanity` | splits the 16,384 bytes into code and data | that not one byte is left unassigned |
| `make test` | 49 tests | that the numbers on this site are the listing's |
| `make imagenes` | draws everything in `docs/imagenes/` from the ROM | that the formats are read right |
| `make coteja_montaje` / `make coteja_arranque` / `make coteja_pista` | compare against openMSX dumps | zero bytes different |

All three comparisons need the emulator dumps first: `tools/omsx_montaje.tcl`
and `tools/omsx_arranque.tcl` (the ring one uses the same dumps as the start),
each with its usage line in the header. See
[In the emulator](IN-THE-EMULATOR.html).
