# SPDX-License-Identifier: 0BSD
"""Fixed native GameBub LCD timing with LiteX video stream boundaries."""
from migen import Signal, If, Case, ClockSignal
from litex.gen import LiteXModule
from litex.soc.interconnect import stream

PROFILES = {
    0: dict(hstart=14, vstart=24, htotal=541, vtotal=834),
    1: dict(hstart=123, vstart=6, htotal=605, vtotal=809),
}
COLORS = (0xffffff, 0xffff00, 0x00ffff, 0x00ff00,
          0xff00ff, 0xff0000, 0x0000ff, 0x000000)


class Video(LiteXModule):
    """Video-domain 480x800 fixed raster; no backpressure on panel timing.

    overlay_x/y/de issue a pixel request before the rising edge. An external
    synchronous reader supplies overlay_valid/rgb during the following cycle;
    those are sampled at the next rising edge alongside the registered base.
    Overlay coordinates are native panel coordinates, no rotation or scaling.
    """
    def __init__(self, pads=None, timing_profile=1):
        p = PROFILES[timing_profile]
        self.dotclk = Signal(name="dotclk")
        self.de = Signal(name="de")
        self.hsync = Signal(name="hsync")
        self.vsync = Signal(name="vsync")
        self.r = Signal(8, name="r")
        self.g = Signal(8, name="g")
        self.b = Signal(8, name="b")
        self.x = Signal(10, name="x")
        self.y = Signal(10, name="y")
        self.overlay_valid = Signal(name="overlay_valid")
        self.overlay_rgb = Signal(24, name="overlay_rgb")
        self.overlay_x = Signal(10, name="overlay_x")
        self.overlay_y = Signal(10, name="overlay_y")
        self.overlay_de = Signal(name="overlay_de")
        self.frame_start = Signal(name="frame_start")
        self.source = source = stream.Endpoint([
            ("de", 1), ("hsync", 1), ("vsync", 1),
            ("x", 10), ("y", 10), ("rgb", 24)])
        sx, sy = Signal(10), Signal(10)
        active, px, py, rgb = Signal(), Signal(10), Signal(10), Signal(24)
        self.comb += [active.eq((sx >= p["hstart"]) & (sx < p["hstart"] + 480) &
                               (sy >= p["vstart"]) & (sy < p["vstart"] + 800)),
                      px.eq(0), py.eq(0),
                      If(active, px.eq(sx-p["hstart"]), py.eq(sy-p["vstart"])),
                      self.overlay_x.eq(px), self.overlay_y.eq(py), self.overlay_de.eq(active),
                      self.frame_start.eq((sx == 0) & (sy == 0)), rgb.eq(0)]
        # Constant thresholds avoid a hardware divider and preserve exact bars.
        for index, color in reversed(list(enumerate(COLORS[:-1]))):
            self.comb += If(px < (index+1)*60, rgb.eq(color))
        self.sync.video += [
            If(sx == p["htotal"]-1, sx.eq(0),
               If(sy == p["vtotal"]-1, sy.eq(0)).Else(sy.eq(sy+1))).Else(sx.eq(sx+1)),
            source.valid.eq(1), source.de.eq(active),
            source.hsync.eq(sx < 4), source.vsync.eq(sy < 4),
            source.x.eq(px), source.y.eq(py), source.rgb.eq(0),
            If(active, source.rgb.eq(rgb)),
            self.de.eq(source.de), self.hsync.eq(source.hsync), self.vsync.eq(source.vsync),
            self.x.eq(source.x), self.y.eq(source.y),
            self.r.eq(source.rgb[16:24]), self.g.eq(source.rgb[8:16]), self.b.eq(source.rgb[:8]),
            If(source.de & self.overlay_valid,
               self.r.eq(self.overlay_rgb[16:24]), self.g.eq(self.overlay_rgb[8:16]), self.b.eq(self.overlay_rgb[:8])),
        ]
        self.comb += [self.dotclk.eq(ClockSignal("video")), source.ready.eq(1)]
        if pads is not None:
            for name in ("dotclk", "de", "hsync", "vsync", "r", "g", "b"):
                self.comb += getattr(pads, name).eq(getattr(self, name))
