# El código

## El juego entero vive en la interrupción

INIT pone el modo 1, engancha H.KEYI (`0xFD9A`) con un `jp 0x402C`, pone la
RAM a cero y se queda para siempre en el `jr $` de `0x40A9`. Todo lo demás
pasa en el gancho, una vez por cuadro: el sonido primero, después los mandos y
después la escena. El cerrojo de `0xE005` cuenta las interrupciones
solapadas: si un cuadro tarda más de la cuenta, la siguiente se atiende al
salir, sin volver a la pila.

## Las tablas van pegadas detrás del `call`

`despacha_por_tabla` (`0x404E`) saca con `pop hl` su propia dirección de
retorno, que es donde empieza la tabla. Así se reparten las escenas, los cinco
montajes (`0x5FEF`), los cinco arranques (`0x60B6`) y los cinco cuadros
(`0x4C93`).

## Tres máquinas de datos

Reescritas en Python en `tools/`:

- `rle.py`, el descompresor de `0x45C9`: `0nnnnnnn b` repite y
  `1nnnnnnn b…` copia; `0x80` cambia de destino y `0x00` termina. Un segundo
  descompresor con el mismo lenguaje escribe en RAM (`0x6A51` → `0xE280`), y
  un tercero (`0x7567`) lee los bits del revés.
- `guiones.py`, el intérprete de rótulos de `0x4062`: `[destino][índices…]`,
  `0xFE` salta y `0xFF` termina. Con la máscara a `0x00`, **el mismo guion
  borra** lo que pintó.
- `escenas.py`: descomprime al búfer y vuelca por máscaras de ocho bits, un
  bit por patrón, de modo que repinta media pantalla sin tocar la otra.
  `0x4647` espeja los patrones y `0x467B` hace tres copias desplazadas 2, 4 y
  6 píxeles.

## Y el cartucho, ejecutado

`tools/corre_circus.py` corre INIT hasta el `jr $` y después el gancho una vez
por cuadro, sobre el Z80 pequeño de `tools/z80run.py`, que revienta ante
cualquier opcode que no conozca. Las siete rutinas de la BIOS se imitan en
Python. Contra openMSX, en cinco atracciones por diez instantes: **0 bytes de
VRAM distintos** (`make coteja_arranque`). La RAM solo difiere en la música y
en la cortinilla del menú.
