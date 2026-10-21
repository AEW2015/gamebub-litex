# SPDX-License-Identifier: 0BSD
"""Physical LiteX target; earlier hash-bound simulation sources stay unchanged."""
from types import SimpleNamespace
from migen import ClockSignal, Signal, Instance, If, Mux
from migen.genlib.cdc import MultiReg
from migen.fhdl.specials import Tristate
from litex.gen import LiteXModule
from litex.soc.integration.soc_core import SoCCore
from litex.soc.integration.soc import SoCRegion
from litex.soc.interconnect.csr import CSRStorage, CSRStatus
from board import Platform
from clocking import CRG
from apps import AppOverlay, AppOutputs


class Diagnostic(LiteXModule):
    def __init__(self):
        self.result = CSRStorage(32, name="result")
        self.memory_pass = CSRStorage(2, name="memory_pass")
        self.sdram_ready = CSRStatus(1, name="sdram_ready")
        self.video_frames = CSRStatus(32, name="video_frames")
        self.buttons = CSRStatus(12, name="buttons")


class BaseSoC(SoCCore):
    def __init__(self, rom_init=None):
        from raster import Video
        from memory.controllers import GameBubSRAM, GameBubSDRAM
        from esp32_service import ESP32Service
        platform = Platform()
        self.crg = CRG(platform)
        super().__init__(platform, 50_000_000, cpu_type="vexriscv", cpu_variant="minimal",
            integrated_rom_size=16384, integrated_rom_init=rom_init or [],
            integrated_sram_size=16384, integrated_main_ram_size=0,
            csr_data_width=32, with_uart=True, uart_name="jtag_uart", uart_fifo_depth=16,
            with_timer=True, ident="GameBub open-source physical interface demo", ident_version=False)
        self.diagnostic = Diagnostic()
        self.add_csr("diagnostic")
        for name, value in platform.safe.items():
            if not name.startswith(("vibrate_", "dac_")):
                self.comb += platform.request(name).eq(value)
        buttons = platform.request("buttons_n")
        buttons_sync = Signal(12)
        self.specials += MultiReg(~buttons, buttons_sync)
        self.comb += self.diagnostic.buttons.status.eq(buttons_sync)
        self.outputs = AppOutputs(platform, buttons_sync)
        self.add_csr("outputs")
        self.app_overlay = AppOverlay()
        self.bus.add_slave("app_overlay", self.app_overlay.bus,
                           SoCRegion(origin=0xc0000000, size=0x8000, cached=False))
        self.ext_sram = GameBubSRAM(platform.request("sram"))
        dram = platform.request("sdram")
        # The controller's inverted clock is replaced only at the physical
        # pad by an ODDR with identical phase (D1=0,D2=1). No fabric clock mux.
        dram_internal = SimpleNamespace(**{name: getattr(dram, name) for name in
            ("a", "ba", "dq", "dm", "cs_n", "cke", "ras_n", "cas_n", "we_n")})
        dram_internal.clk = Signal()
        self.ext_sdram = GameBubSDRAM(dram_internal, sys_clk_freq=50e6)
        self.specials += Instance("ODDR", p_DDR_CLK_EDGE="SAME_EDGE", p_INIT=0, p_SRTYPE="SYNC",
            i_C=ClockSignal("sys"), i_CE=1, i_D1=0, i_D2=1, i_R=0, i_S=0, o_Q=dram.clk)
        self.bus.add_slave("ext_sram", self.ext_sram.bus, SoCRegion(origin=0x30000000, size=0x80000, cached=True))
        self.bus.add_slave("ext_sdram", self.ext_sdram.bus, SoCRegion(origin=0x40000000, size=0x2000000, cached=True))
        self.comb += self.diagnostic.sdram_ready.status.eq(self.ext_sdram.initialized)
        self.video = Video(timing_profile=1)
        self.specials += MultiReg(self.outputs.color.storage, self.video.pattern, odomain="video")
        lcd = platform.request("lcd")
        self.specials += Instance("ODDR", p_DDR_CLK_EDGE="SAME_EDGE", p_INIT=0, p_SRTYPE="SYNC",
            i_C=ClockSignal("video"), i_CE=1, i_D1=1, i_D2=0, i_R=0, i_S=0, o_Q=lcd.dotclk)
        for name in ("de", "hsync", "vsync"):
            self.comb += getattr(lcd, name).eq(getattr(self.video, name))
        qspi = platform.request("qspi")
        logical_qspi = SimpleNamespace(sck=qspi.sck, cs_n=qspi.cs_n,
            dq_i=Signal(4), dq_o=Signal(4), dq_oe=Signal(4))
        self.qspi_oe = logical_qspi.dq_oe
        for lane in range(4):
            self.specials += Tristate(qspi.dq[lane], logical_qspi.dq_o[lane],
                                     logical_qspi.dq_oe[lane], logical_qspi.dq_i[lane])
        self.esp32 = ESP32Service(platform, pads=logical_qspi, service_domain="service", sys_domain="sys", with_overlay=True)
        self.bus.add_slave("esp32", self.esp32.bus, SoCRegion(origin=0xb0000000, size=0x1000, cached=False))
        self.comb += [self.esp32.buttons_native.eq(~buttons),
                      platform.request("esp_irq_gate").eq(self.esp32.irq_gate),
                      self.esp32.vblank.eq(self.video.vsync)]
        for reader in (self.esp32.overlay, self.app_overlay):
            self.comb += [reader.x.eq(self.video.overlay_x), reader.y.eq(self.video.overlay_y),
                          reader.de.eq(self.video.overlay_de)]
        self.comb += [self.video.overlay_valid.eq(self.esp32.overlay.valid | self.app_overlay.valid),
                      self.video.overlay_rgb.eq(Mux(self.esp32.overlay.valid,
                          self.esp32.overlay.rgb, self.app_overlay.rgb))]
        vs, old_vs = Signal(), Signal()
        frames = Signal(32)
        self.specials += MultiReg(self.video.vsync, vs)
        self.sync += [old_vs.eq(vs), If(vs & ~old_vs, frames.eq(frames + 1))]
        self.comb += self.diagnostic.video_frames.status.eq(frames)
        self.comb += [lcd.r.eq(self.video.r), lcd.g.eq(self.video.g), lcd.b.eq(self.video.b)]
