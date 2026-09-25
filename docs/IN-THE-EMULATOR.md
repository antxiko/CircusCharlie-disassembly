# In the emulator

With openMSX and the `Philips_VG_8020` machine:

    openmsx -machine Philips_VG_8020 -cart circus.rom -script tools/omsx_montaje.tcl

There are three scripts:

- `omsx_montaje.tcl` dumps the VRAM at `0x4C3C`, with the scenery just built.
  It forces the type at `0x4C39` before the **first** set-up, because forcing
  it later leaves remains of the previous act behind.
- `omsx_arranque.tcl` carries on and dumps VRAM and RAM at frames 1 to 200,
  with a breakpoint at `0x4CA9`, the sprite copy.
- `omsx_cuadro.tcl`, the burst of frames around a picture, because
  `screenshot` does not give the frame at the instant the VRAM was read.

The whole game happens in the hook at `0x402C`: a breakpoint there stops once
per frame.
