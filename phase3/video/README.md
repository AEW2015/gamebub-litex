# Migen/LiteX native LCD scanout

`video.py` provides `Video(pads=None, timing_profile=1)` in the `video` clock
domain. It uses a LiteX `stream.Endpoint` for the internal registered video
boundary. Fixed Migen counters retain the panel's phase relationship exactly;
LiteX `VideoTimingGenerator` starts active video at counter zero and advances
its vertical counter at horizontal sync, so using that core directly would
change the independently verified legacy pin alignment.

The default profile is **official-derived fixed**: 480x800 native portrait,
605 clocks/line, 809 lines/frame, active start (123,6), HSYNC/VSYNC active high
for 4 clocks/4 lines. At 29.3619791667 MHz it runs approximately 59.99 Hz.
This is the fixed timing documented in the legacy LCD comparison, rather than
the upstream adaptive framebuffer scheduler. Profile 0 retains the earlier
541x834 totals and active start (14,24). Output RGB is conventional RGB888.
Eight 60-pixel bars are white/yellow/cyan/green/magenta/red/blue/black.

Pads are a record with `dotclk,de,hsync,vsync,r,g,b`. The same output signals
are available on the module, together with display-aligned `x,y` coordinates.
`dotclk` follows the supplied video clock directly. Physical clock generation,
forwarded-clock implementation/constraints and output timing are integration
responsibilities; this module introduces no PLL, vendor simulation primitive,
external framebuffer or physical clock frequency claim.

## Overlay reader contract

Before each rising video clock, `overlay_x`, `overlay_y`, `overlay_de` issue a
native panel pixel request. A synchronous RAM reader samples that request and
returns `overlay_rgb` (24-bit RGB) and `overlay_valid` during the next cycle.
Video samples that response at the following rising edge alongside its aligned
base pixel. A true valid flag selects an opaque overlay pixel; false preserves
the base. Blanking stays black. Coordinate rotation, ESP32 framebuffer format,
alpha decoding and CDC remain with the ESP32 reader. `frame_start` pulses at
raw raster (0,0), before the two-cycle output pipeline. Timing cannot stall.

## Independent full-frame test

In the isolated LiteX Python environment, with OSS CAD Suite `iverilog`/`vvp`
on PATH:

```sh
python phase3/video/run.py --output /path/to/new/evidence \
  --reference /path/to/gamebub-vivado-public/fpga/ip_repo/gamebub_lcd_axis_v1_5/src/gamebub_axis_raster.v
```

For both profiles this generates new Migen RTL, instantiates the unmodified
public raster reference with explicit profile parameters, and compares every
pin/coordinate/RGB value after the legacy output register. A separate arithmetic
oracle checks sync widths, periods, blanking, active bounds, every pixel color,
480 pixels per active line and 800 active lines per frame. The second full frame
adds a synchronous opaque 20x20 overlay with a deliberately asymmetric RGB color,
checking reader latency and channel ordering. Each profile must observe exactly
768,000 active pixels over two frames and no reference stream faults.

Executed 2026-10-21 with Icarus 14: both profiles PASS. Profile 0 compared
902,388 pixel clocks, profile 1 compared 978,890. Evidence with commands and
source/capture SHA-256:
`D:/xup_2026/bub/gamebub-phase3-video-test1/evidence.json`.
Each profile directory contains native 480x800 `colorbars.ppm` and `overlay.ppm`
captures. `preview.py input.ppm new-output.png` losslessly converts a capture
to a convenient PNG without rotating or modifying its pixels.

Timing provenance: the packaged `hdl/gamebub_lcd_axis.v` sets profile 1 to
(123,6,605,809); the raster source's own defaults are profile 0. The historical
`gamebub-source/fpga/vivado/gamebub_lcd_compare/LCD_V14_OFFICIAL_TIMING_PLAN.md`
documents both profiles, their official-source relationship, clock and limits.
This test does not claim physical display acceptance, ESP32 protocol testing,
or external SRAM/SDRAM verification.
