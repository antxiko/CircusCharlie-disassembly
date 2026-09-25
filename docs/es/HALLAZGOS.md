# Hallazgos

1. **Los encabezados de tres tablas iban corridos uno.** Los de `0x5FEF`,
   `0x60B6` y `0x4C93` estaban numerados como si el índice empezara en 1. Lo
   destapó la RAM medida al arrancar cada atracción: el guion `0x5C8E` sale en
   el caballo y no en las bolas, y el cuadro de `0x4CC2` es el del trapecio.
2. **El tipo 0 es el trapecio**, no un trampolín: la cama elástica es solo el
   suelo.
3. **Dos erratas que repetían el decorado.** `0x458F` lee por DE y escribe por
   HL, al revés de lo que parecía. Por eso `0x7477` copia `0x2AC0` **sobre**
   `0x2BB0`, solapado, y el decorado del caballo se repite cada 240 bytes.
4. **El parpadeo de "1P" no mira el número de jugadores.** El
   `ld hl,(0xE002)` trae las banderas en L y el **contador de cuadros en H**;
   el `bit 5,h` alterna la máscara cada 32 cuadros.
5. **La tabla de `0x4CEA` tiene diez entradas, no cinco.** Dos son `0x0000`, y
   otras dos apuntan a los únicos trozos de código que ninguna instrucción
   alcanzaba.
6. **`0x462F` repite un patrón hacia atrás**: `[N][ocho bytes]` escribe ese
   patrón N veces, porque el bucle retrocede ocho antes de repetir. Quien lo
   llama no carga su dirección, sigue desde el HL que dejó la escena anterior.
7. **La VRAM de cada atracción se hereda del menú**: solo se borra la tabla de
   nombres. Montarla desde cero no da cero bytes; partir del menú, sí.
8. **Cuatro sprites por línea, y el quinto no se pinta.** En el trapecio son
   seis los que cruzan las líneas 48 a 52, y el VDP se come dos. Sin ese tope,
   el cotejo contra la foto no llega a cero; con él, 49.152 puntos de 49.152.
9. **Siete bytes huérfanos**: se desensamblan como instrucciones coherentes,
   pero nada los alcanza.
10. **Es el mismo código que Magical Tree, desplazado.** La firma de catorce
    bytes del bucle del descompresor (`0x45D1` aquí) aparece igual en el
    RC-713, y con ella el intérprete de rótulos y el despachador de escenas.
