# SPDX-License-Identifier: 0BSD
"""BRAM-only bring-up SoC; no ESP32 service or functional external interfaces."""
from migen import ClockDomain, Signal, If
from litex.gen import LiteXModule
from litex.soc.integration.soc_core import SoCCore
from litex.soc.interconnect.csr import CSRStatus, CSRStorage
from litex_boards.platforms.gamebub import Platform, SAFE_IO


class CRG(LiteXModule):
    def __init__(self, platform):
        self.cd_sys = ClockDomain("sys")
        # Reset-less counter progresses while the system reset is asserted.
        # Yosys inserts the physical BUFG; there is no PLL/MMCM or CDC here.
        self.startup = Signal(6, reset_less=True, name="startup")
        self.comb += self.cd_sys.clk.eq(platform.request("clk50"))
        self.sync += If(self.startup != 63, self.startup.eq(self.startup + 1))
        self.comb += self.cd_sys.rst.eq(self.startup != 63)


class Diagnostic(LiteXModule):
    def __init__(self):
        self.identifier = CSRStatus(32, name="identifier", reset=0x47424c32)
        self.result = CSRStorage(32, name="result", reset=0)


class BaseSoC(SoCCore):
    def __init__(self, rom_init=None, *, console_pmod=False):
        if not console_pmod:
            raise ValueError("Phase2 serial diagnostic requires explicit --console-pmod")
        platform = Platform(console_pmod=console_pmod)
        self.crg = CRG(platform)
        super().__init__(platform, 50_000_000,
            cpu_type="vexriscv", cpu_variant="minimal",
            integrated_rom_size=0x4000, integrated_rom_init=rom_init or [],
            integrated_sram_size=0x4000, integrated_sram_init=[0] * 4096,
            integrated_main_ram_size=0,
            csr_data_width=32, with_uart=True, uart_name="serial",
            uart_baudrate=115200, uart_fifo_depth=16,
            with_timer=True, with_ctrl=True,
            ident="GameBub open-source Phase2 BRAM diagnostic", ident_version=False)
        self.diagnostic = Diagnostic()
        self.add_csr("diagnostic")
        for name, _, inactive in SAFE_IO:
            self.comb += platform.request(name).eq(inactive)
