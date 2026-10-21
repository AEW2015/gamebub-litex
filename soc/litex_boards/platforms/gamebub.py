# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Rev4 diagnostic subset; pin assignments derived from GameBub rev_4.xdc.

This is not yet an upstream litex-boards platform. Unimplemented interfaces
are disabled electrically, not presented as working peripherals. PMOD UART
is opt-in: never connect this image with an incompatible PMOD accessory.
Upstream: https://github.com/elipsitz/gamebub
"""
from litex.build.generic_platform import Pins, IOStandard, Subsignal
from litex.build.xilinx import XilinxPlatform

# (resource, package pins, constant inactive value). No fabricated delays/cuts.
SAFE_IO = [
    ("vibrate_in1", "F5", 0), ("vibrate_in2", "G6", 0),
    ("dac_mclk", "T15", 0), ("dac_wclk", "R15", 0),
    ("dac_bclk", "R16", 0), ("dac_din", "P15", 0),
    # Rev4 nFET gate: zero is idle despite the historical active-low name.
    ("mcu_irq_n", "N15", 0), ("cart_oe_n", "A5", 1),
    ("cart_bank0_dir", "D15", 0), ("cart_bank1_dir", "A11", 0),
    ("cart_bank2_dir", "F6", 0), ("cart_bank3_dir", "B4", 0),
    ("cart_pin30_dir", "C16", 0), ("cart_pin31_dir", "F15", 0),
    ("link_so_dir", "K16", 0), ("link_si_dir", "J14", 0),
    ("link_sd_dir", "H14", 0), ("link_sc_dir", "G14", 0),
    ("sram_ce_n", "V4", 1), ("sram_we_n", "V9", 1),
    ("sram_oe_n", "T11", 1), ("sram_ub_n", "R10", 1),
    ("sram_lb_n", "T10", 1), ("sdram_cke", "J4 H4", 0),
    ("sdram_cs_n", "J3 G4", 3), ("sdram_clk", "J5", 0),
    ("sdram_we_n", "K2", 1), ("sdram_ras_n", "J2", 1),
    ("sdram_cas_n", "K1", 1), ("sdram_ldqm", "L1", 1),
    ("sdram_udqm", "K3", 1), ("lcd_dotclk", "T18", 0),
    ("lcd_hsync", "U18", 1), ("lcd_vsync", "T16", 1),
    ("lcd_data_en", "R18", 0),
    ("lcd_data_r", "E18 E16 D18 D17 C17 B18 B17 A18", 0),
    ("lcd_data_g", "J17 J18 H16 H17 G18 G17 F18 E17", 0),
    ("lcd_data_b", "R17 P18 N17 M17 M18 L16 L18 K17", 0),
]


class Platform(XilinxPlatform):
    default_clk_name = "clk50"
    default_clk_period = 20.0

    def __init__(self, console_pmod=False):
        io = [("clk50", 0, Pins("P17"), IOStandard("LVCMOS33"))]
        io += [(name, 0, Pins(pins), IOStandard("LVCMOS33"))
               for name, pins, _ in SAFE_IO]
        if console_pmod:
            io += [("serial", 0,
                    Subsignal("tx", Pins("V14")),
                    Subsignal("rx", Pins("U14")), IOStandard("LVCMOS33"))]
        # Used only for RTL conversion; the explicit modern openXC7 adapter
        # runs synthesis/P&R. No vendor executable or legacy backend is run.
        super().__init__("xc7a100tcsg324-1", io, toolchain="openxc7")
