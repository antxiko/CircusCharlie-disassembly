# Empezar

Este repositorio contiene el desensamblado comentado de **Circus Charlie** de
Konami para MSX (RC-712, 1984). No contiene el cartucho: la imagen de la ROM no
se distribuye.

## Lo que hace falta

- `pasmo` — el ensamblador que reproduce la ROM
- `z80dasm` — el desensamblador con el que se genera el listado
- `python3` — las herramientas de `tools/`
- `make`
- Tu propia copia del cartucho, en la raíz y con el nombre `circus.rom`

Son **16.384 bytes exactos** y su huella es:

    sha256  89e1badac10e65886590d55e735ed794e5ca3c41142e6637b3e7ac6b25d042c0

Para comprobarla:

    make comprueba

## Reproducirlo entero

| orden | qué hace | qué demuestra |
|---|---|---|
| `make listado` | traza el flujo y genera `src/circus.asm` con las notas | que el listado sale del cartucho y de `src/circus.notes`, no se edita a mano |
| `make verify` | reensambla con `pasmo` y compara | que el listado ES la ROM, byte a byte |
| `make sanity` | reparte los 16.384 bytes entre código y datos | que no queda ni un byte sin asignar |
| `make test` | 47 tests | que las cifras de esta web son las del listado |
| `make imagenes` | dibuja todo lo de `docs/imagenes/` desde la ROM | que los formatos están bien leídos |
| `make coteja_montaje` / `make coteja_arranque` | comparan con volcados de openMSX | cero bytes de diferencia |

Los dos cotejos necesitan antes los volcados del emulador:
`tools/omsx_montaje.tcl` y `tools/omsx_arranque.tcl`, cada uno con su línea de
uso en la cabecera. Ver [En el emulador](EN-EL-EMULADOR.html).
