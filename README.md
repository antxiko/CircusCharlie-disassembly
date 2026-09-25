# Circus Charlie (Konami, MSX) — a commented disassembly

*(También [en castellano](README.es.md).)*

An **RC-712** 16 KB cartridge, 1984. The listing in `src/circus.asm`
reassembles the ROM **byte for byte** with `pasmo`, and every one of its
16,384 bytes is accounted for: **7,894 of code and 8,490 of data**. There are
**576 routines, none below 10% commented**, and the density is **47.1%**.

The five acts are drawn from the ROM: the scenery with the cartridge's own
set-up chain, and the characters and obstacles by **running the cartridge** on
a Z80 written in Python. Both are checked against openMSX's VRAM down to
**zero bytes**.

The ROM is not distributed.

- Website: https://antxiko.github.io/CircusCharlie-disassembly/
- Getting started: [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md)
- Legal notice: [LEGAL-NOTICE.md](LEGAL-NOTICE.md)
