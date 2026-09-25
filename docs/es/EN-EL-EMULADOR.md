# En el emulador

Con openMSX y la máquina `Philips_VG_8020`:

    openmsx -machine Philips_VG_8020 -cart circus.rom -script tools/omsx_montaje.tcl

Hay tres guiones:

- `omsx_montaje.tcl` vuelca la VRAM en `0x4C3C`, con el decorado recién
  montado. Fuerza el tipo en `0x4C39` antes del **primer** montaje, porque
  forzarlo después deja restos del número anterior.
- `omsx_arranque.tcl` sigue adelante y vuelca VRAM y RAM en los cuadros 1 a
  200, con un punto de ruptura en `0x4CA9`, el vuelco de sprites.
- `omsx_cuadro.tcl`, la ráfaga de cuadros alrededor de una foto, porque
  `screenshot` no da el cuadro del instante en que se leyó la VRAM.

Todo el juego pasa en el gancho de `0x402C`: un punto de ruptura ahí para una
vez por cuadro.
