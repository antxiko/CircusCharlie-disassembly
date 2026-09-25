# Circus Charlie (Konami, MSX) — desensamblado comentado

*(Also available [in English](README.md).)*

Cartucho **RC-712** de 16 KB, 1984. El listado de `src/circus.asm` reensambla
la ROM **byte a byte** con `pasmo`, y cada uno de sus 16.384 bytes está
asignado: **7.894 de código y 8.490 de datos**. Son **576 rutinas, ninguna por
debajo del 10 % comentado**, y una densidad del **47,1 %**.

Las cinco atracciones están dibujadas desde la ROM: el decorado con la cadena
de montaje del propio cartucho, y los personajes y obstáculos **ejecutando el
cartucho** en un Z80 escrito en Python. Las dos cosas están cotejadas contra la
VRAM de openMSX a **cero bytes**.

La ROM no se distribuye.

- Web: https://antxiko.github.io/CircusCharlie-disassembly/es/
- Para empezar: [docs/es/EMPEZAR.md](docs/es/EMPEZAR.md)
- Aviso legal: [AVISO-LEGAL.md](AVISO-LEGAL.md)
