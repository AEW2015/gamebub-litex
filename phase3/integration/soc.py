# SPDX-License-Identifier: 0BSD
"""Combined simulation target: real CPU, serial endpoint and external memories.

Clock inputs are supplied by the testbench at the intended domain rates. This
is a functional simulation target, not a physical MMCM/timing qualification.
"""
from migen import ClockDomain, Signal, If, Cat
from migen.genlib.cdc import MultiReg
from litex.gen import LiteXModule
from litex.build.generic_platform import GenericPlatform, Pins, Subsignal
from litex.soc.integration.soc_core import SoCCore
from litex.soc.integration.soc import SoCRegion
from litex.soc.interconnect.csr import CSRStatus, CSRStorage


class Platform(GenericPlatform):
    def __init__(self):
        io = [("clk50", 0, Pins(1)), ("clk200", 0, Pins(1)),
              ("clk_video", 0, Pins(1)), ("sim_reset", 0, Pins(1)),
              ("buttons_n", 0, Pins(12)), ("test_status", 0, Pins(32)),
              ("serial", 0, Subsignal("tx", Pins(1)), Subsignal("rx", Pins(1))),
              ("sram", 0, Subsignal("a", Pins(18)), Subsignal("dq", Pins(16)),
               Subsignal("ce_n", Pins(1)), Subsignal("we_n", Pins(1)),
               Subsignal("oe_n", Pins(1)), Subsignal("lb_n", Pins(1)), Subsignal("ub_n", Pins(1))),
              ("sdram", 0, Subsignal("a", Pins(13)), Subsignal("ba", Pins(2)),
               Subsignal("dq", Pins(16)), Subsignal("dm", Pins(2)),
               Subsignal("cs_n", Pins(2)), Subsignal("cke", Pins(2)),
               Subsignal("ras_n", Pins(1)), Subsignal("cas_n", Pins(1)),
               Subsignal("we_n", Pins(1)), Subsignal("clk", Pins(1))),
              ("lcd", 0, Subsignal("dotclk", Pins(1)), Subsignal("de", Pins(1)),
               Subsignal("hsync", Pins(1)), Subsignal("vsync", Pins(1)),
               Subsignal("r", Pins(8)), Subsignal("g", Pins(8)), Subsignal("b", Pins(8))),
              ("qspi", 0, Subsignal("sck", Pins(1)), Subsignal("cs_n", Pins(1)),
               Subsignal("dq_i", Pins(4)), Subsignal("dq_o", Pins(4)), Subsignal("dq_oe", Pins(4))),
              ("esp_irq_gate", 0, Pins(1))]
        super().__init__("SIM", io, name="gamebub_phase3")


class CRG(LiteXModule):
    def __init__(self, platform):
        self.cd_sys = ClockDomain("sys")
        self.cd_service = ClockDomain("service")
        self.cd_video = ClockDomain("video")
        self.startup = Signal(6, reset_less=True)
        self.comb += [self.cd_sys.clk.eq(platform.request("clk50")),
                      self.cd_service.clk.eq(platform.request("clk200")),
                      self.cd_video.clk.eq(platform.request("clk_video"))]
        self.sync += If(self.startup != 63, self.startup.eq(self.startup + 1))
        reset = Signal()
        self.comb += reset.eq((self.startup != 63) | platform.request("sim_reset"))
        # Functional reset model. Physical asynchronous-assert/synchronous-
        # release reset synchronizers must be included before a hardware build.
        self.comb += [self.cd_sys.rst.eq(reset), self.cd_service.rst.eq(reset),
                      self.cd_video.rst.eq(reset)]


class Diagnostic(LiteXModule):
    def __init__(self):
        self.result = CSRStorage(32, name="result")
        self.sdram_ready = CSRStatus(1, name="sdram_ready")
        self.video_frames = CSRStatus(32, name="video_frames")
        self.buttons = CSRStatus(12, name="buttons")
        self.esp_irq = CSRStatus(1, name="esp_irq")


class BaseSoC(SoCCore):
    def __init__(self, rom_init=None):
        # Imported lazily: each component can be generated/tested independently.
        from video.video import Video
        from memory.controllers import GameBubSRAM, GameBubSDRAM
        from esp32.service import ESP32Service
        platform = Platform()
        self.crg = CRG(platform)
        super().__init__(platform, 50_000_000, cpu_type="vexriscv", cpu_variant="minimal",
            integrated_rom_size=16384, integrated_rom_init=rom_init or [],
            integrated_sram_size=16384, integrated_sram_init=[0] * 4096,
            integrated_main_ram_size=0, csr_data_width=32,
            with_uart=True, uart_name="serial", uart_baudrate=115200,
            with_timer=True, ident="GameBub Phase3 board-interface simulation", ident_version=False)
        self.diagnostic = Diagnostic()
        self.add_csr("diagnostic")
        self.comb += platform.request("test_status").eq(self.diagnostic.result.storage)

        self.ext_sram = GameBubSRAM(platform.request("sram"))
        self.ext_sdram = GameBubSDRAM(platform.request("sdram"), sys_clk_freq=50e6)
        self.bus.add_slave("ext_sram", self.ext_sram.bus,
            SoCRegion(origin=0x30000000, size=0x80000, cached=True))
        self.bus.add_slave("ext_sdram", self.ext_sdram.bus,
            SoCRegion(origin=0x40000000, size=0x2000000, cached=True))
        self.comb += self.diagnostic.sdram_ready.status.eq(self.ext_sdram.initialized)
        self.video = Video(platform.request("lcd"), timing_profile=1)
        vsync = Signal()
        vsync_last = Signal()
        frames = Signal(32)
        self.specials += MultiReg(self.video.vsync, vsync)
        self.sync += [vsync_last.eq(vsync), If(vsync & ~vsync_last, frames.eq(frames + 1))]
        self.comb += self.diagnostic.video_frames.status.eq(frames)
        self.buttons_n = platform.request("buttons_n")
        self.qspi_pads = platform.request("qspi")
        self.irq_pad = platform.request("esp_irq_gate")
        self.comb += self.diagnostic.buttons.status.eq(~self.buttons_n)
        self.esp32 = ESP32Service(platform, pads=self.qspi_pads,
            service_domain="service", sys_domain="sys", with_overlay=True)
        self.bus.add_slave("esp32", self.esp32.bus,
            SoCRegion(origin=0xb0000000, size=0x1000, cached=False))
        self.comb += [self.esp32.buttons_native.eq(~self.buttons_n),
                      self.irq_pad.eq(self.esp32.irq_gate),
                      self.esp32.vblank.eq(self.video.vsync),
                      self.diagnostic.esp_irq.status.eq(self.esp32.cpu_irq)]
        self.esp32.overlay.connect_video(self.video)
