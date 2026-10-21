# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Physical Rev4 pin binding derived from the frozen official rev_4.xdc."""
import hashlib
from pathlib import Path
import re
from litex.build.generic_platform import Pins, IOStandard, Subsignal, Misc
from litex.build.xilinx import XilinxPlatform

REFERENCE_SHA = "af2d5b6e9a157ed9636330cc1105180bd4bc7384e8c67d622119944b923953b8"


def pin_map():
    source = Path(__file__).parent / "reference/rev_4.xdc"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == REFERENCE_SHA
    pairs = re.findall(r"PACKAGE_PIN\s+(\S+)\s+IOSTANDARD\s+(\S+)\s*\}\s*\[get_ports\s*\{\s*([^}]+?)\s*\}", source.read_text())
    mapping = {name.strip(): (pin, standard) for pin, standard, name in pairs}
    assert len(mapping) == len(pairs)
    return mapping


class Platform(XilinxPlatform):
    default_clk_name = "clk50"
    default_clk_period = 20.0

    def __init__(self):
        mapping = pin_map()
        self.binding = {}

        def spec(output, original):
            names = [original] if isinstance(original, str) else original
            values = [mapping[name] for name in names]
            assert all(standard == "LVCMOS33" for _, standard in values)
            self.binding[output] = names
            return Pins(" ".join(pin for pin, _ in values))

        def vector(name, count):
            return [f"{name}[{i}]" for i in range(count)]

        io = [("clk50", 0, spec("clk50", "clk_50mhz"), IOStandard("LVCMOS33")),
              ("buttons_n", 0, spec("buttons_n", ["btn_" + name for name in
                 ("a", "b", "x", "y", "up", "down", "left", "right", "l", "r", "start", "select")]),
               IOStandard("LVCMOS33"), Misc("PULLUP")),
              ("esp_irq_gate", 0, spec("esp_irq_gate", "mcu_irq_n"), IOStandard("LVCMOS33"))]
        resources = {
            "lcd": {"dotclk": "lcd_dotclk", "de": "lcd_data_en", "hsync": "lcd_hsync", "vsync": "lcd_vsync",
                    "r": vector("lcd_data_r", 8), "g": vector("lcd_data_g", 8), "b": vector("lcd_data_b", 8)},
            "qspi": {"sck": "mcu_spi_clk", "cs_n": "mcu_spi_cs_n", "dq": vector("mcu_spi_d", 4)},
            "sram": {"a": vector("sram_a", 18), "dq": vector("sram_io", 16),
                     "ce_n": "sram_ce_n", "we_n": "sram_we_n", "oe_n": "sram_oe_n", "lb_n": "sram_lb_n", "ub_n": "sram_ub_n"},
            "sdram": {"a": vector("sdram_a", 13), "ba": vector("sdram_bs", 2), "dq": vector("sdram_dq", 16),
                      "dm": ["sdram_ldqm", "sdram_udqm"], "cs_n": vector("sdram_cs_n", 2), "cke": vector("sdram_cke", 2),
                      "ras_n": "sdram_ras_n", "cas_n": "sdram_cas_n", "we_n": "sdram_we_n", "clk": "sdram_clk"}}
        for name, fields in resources.items():
            io.append((name, 0, *(Subsignal(field, spec(name + "_" + field, original))
                                  for field, original in fields.items()), IOStandard("LVCMOS33")))
        self.safe = {
            "vibrate_in1": 0, "vibrate_in2": 0,
            "dac_mclk": 0, "dac_wclk": 0, "dac_bclk": 0, "dac_din": 0,
            "cart_oe_n": 1, "cart_bank0_dir": 0, "cart_bank1_dir": 0,
            "cart_bank2_dir": 0, "cart_bank3_dir": 0, "cart_pin30_dir": 0, "cart_pin31_dir": 0,
            "link_so_dir": 0, "link_si_dir": 0, "link_sd_dir": 0, "link_sc_dir": 0}
        for name in self.safe:
            io.append((name, 0, spec(name, name), IOStandard("LVCMOS33")))
        all_pins = [mapping[original][0] for names in self.binding.values() for original in names]
        assert len(all_pins) == len(set(all_pins)), "overlapping physical pins"
        super().__init__("xc7a100tcsg324-1", io, toolchain="openxc7", name="gamebub_phase4")
