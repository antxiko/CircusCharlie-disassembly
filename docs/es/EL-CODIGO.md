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

## Y la pista, desde las tablas

`tools/pista.py` es el cuadro de partida rutina a rutina: parte del estado que
dejan `0x604C` y el arranque de cada número (`0x60B6`), y en cada cuadro mueve
y pinta lo que mueve y pinta el juego. Contra 43 volcados de openMSX: **0 bytes
distintos** (`make coteja_pista`). `tools/corre_circus.py`, que ejecuta el
cartucho en el Z80 de `tools/z80run.py`, queda como segunda vara (`make
coteja_arranque`), no como fuente de las imágenes.
