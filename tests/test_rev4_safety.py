# SPDX-License-Identifier: 0BSD
"""Portable checks for the Rev4 probe pin map and inactive outputs."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
XDC = ROOT / "constraints" / "rev4_probe.xdc"
TOP = ROOT / "gateware" / "gamebub_probe.v"
OFFICIAL_XDC = (ROOT.parent / "gamebub" / "gamebub-source" / "fpga"
                / "verilog" / "handheld" / "rev_4.xdc")


# Independently reviewed Rev4 package pins for the probe's clock and exposed
# control/status outputs. The full original board XDC is an optional local
# cross-check, not a test dependency for published copies of this directory.
REVIEWED_PINS = {
    "clk_50mhz": "P17",
    "vibrate_in1": "F5",
    "vibrate_in2": "G6",
    "dac_mclk": "T15",
    "dac_wclk": "R15",
    "dac_bclk": "R16",
    "dac_din": "P15",
    "mcu_irq_n": "N15",
    "cart_oe_n": "A5",
    "cart_bank0_dir": "D15",
    "cart_bank1_dir": "A11",
    "cart_bank2_dir": "F6",
    "cart_bank3_dir": "B4",
    "cart_pin30_dir": "C16",
    "cart_pin31_dir": "F15",
    "link_so_dir": "K16",
    "link_si_dir": "J14",
    "link_sd_dir": "H14",
    "link_sc_dir": "G14",
    "sram_ce_n": "V4",
    "sram_we_n": "V9",
    "sram_oe_n": "T11",
    "sram_ub_n": "R10",
    "sram_lb_n": "T10",
    "sdram_clk": "J5",
    "sdram_we_n": "K2",
    "sdram_ras_n": "J2",
    "sdram_cas_n": "K1",
    "sdram_ldqm": "L1",
    "sdram_udqm": "K3",
    "sdram_cke[0]": "J4",
    "sdram_cke[1]": "H4",
    "sdram_cs_n[0]": "J3",
    "sdram_cs_n[1]": "G4",
    "lcd_dotclk": "T18",
    "lcd_hsync": "U18",
    "lcd_vsync": "T16",
    "lcd_data_en": "R18",
    "lcd_data_r[0]": "E18",
    "lcd_data_g[0]": "J17",
    "lcd_data_b[0]": "R17",
}


def package_pin_map(text):
    """Return scalar XDC PACKAGE_PIN assignments keyed by get_ports name."""
    assignments = []
    pattern = re.compile(
        r"set_property\s+(?:-dict\s+\{\s*)?PACKAGE_PIN\s+(\S+)"
        r"[^\n]*?\[get_ports\s+\{\s*([^}]+?)\s*\}\]",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        pin, port = match.groups()
        assignments.append((port.strip(), pin.strip()))
    return assignments


def constant_assignments(verilog):
    """Decode constant scalar/vector and concatenation assigns in the top."""
    result = {}
    vectors = {}
    header = re.search(r"module\s+gamebub_probe\s*\((.*?)\);",
                       verilog, re.DOTALL)
    if header:
        for match in re.finditer(
                r"\b(?:input|output|inout)\s+(?:wire|reg)?\s*"
                r"\[(\d+):(\d+)\]\s*"
                r"([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)",
                header.group(1)):
            first, last, port_names = match.groups()
            first, last = int(first), int(last)
            step = 1 if last >= first else -1
            for base in re.split(r"\s*,\s*", port_names):
                vectors[base] = [f"{base}[{index}]"
                                 for index in range(first, last + step, step)]
    assign_re = re.compile(
        r"\bassign\s+(\{[^}]+\}|[A-Za-z_]\w*(?:\[\d+(?::\d+)?\])?)\s*=\s*"
        r"(\d+\s*'\s*[bBoOdDhH][0-9a-fA-F_xXzZ]+|\d+)\s*;",
        re.MULTILINE,
    )
    for match in assign_re.finditer(verilog):
        lhs, literal = match.groups()
        if lhs.startswith("{"):
            names = [name.strip() for name in lhs[1:-1].split(",")]
        else:
            vector = re.fullmatch(r"([A-Za-z_]\w*)\[(\d+):(\d+)\]", lhs)
            if vector:
                base, first, last = vector.groups()
                first, last = int(first), int(last)
                step = 1 if last >= first else -1
                names = [f"{base}[{index}]"
                         for index in range(first, last + step, step)]
            else:
                names = vectors.get(lhs.strip(), [lhs.strip()])
        literal = re.sub(r"\s+", "", literal).replace("_", "")
        sized = re.fullmatch(r"(\d+)'([bBoOdDhH])([0-9a-fA-F_xXzZ]+)", literal)
        if sized:
            width, base, digits = sized.groups()
            width = int(width)
            radix = {"b": 2, "o": 8, "d": 10, "h": 16}[base.lower()]
            if re.search(r"[xXzZ]", digits):
                continue
            value = int(digits, radix)
            bit_string = format(value, f"0{width}b")
            if len(bit_string) > width:
                continue
        else:
            value = int(literal, 10)
            bit_string = format(value, f"0{len(names)}b")
        if len(bit_string) < len(names):
            continue
        for index, name in enumerate(names):
            result[name] = int(bit_string[index])
    return result


class Rev4SafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.xdc_text = XDC.read_text(encoding="utf-8")
        cls.top_text = TOP.read_text(encoding="utf-8")
        cls.assignments = package_pin_map(cls.xdc_text)
        cls.pin_map = dict(cls.assignments)

    def test_package_pins_and_ports_are_unique(self):
        ports = [port for port, _ in self.assignments]
        pins = [pin for _, pin in self.assignments]
        self.assertEqual(len(ports), len(set(ports)), "port assigned more than once")
        self.assertEqual(len(pins), len(set(pins)), "package pin assigned more than once")
        self.assertEqual(len(ports), 62, "unexpected Rev4 probe top-level pin count")

    def test_clock_is_50mhz_on_official_p17(self):
        self.assertEqual(self.pin_map.get("clk_50mhz"), "P17")
        self.assertEqual(REVIEWED_PINS["clk_50mhz"], "P17")
        clocks = re.findall(
            r"create_clock\b[^\n]*?-period\s+([0-9.]+)"
            r"[^\n]*?\[get_ports\s+\{\s*clk_50mhz\s*\}\]",
            self.xdc_text,
            re.IGNORECASE,
        )
        self.assertEqual(clocks, ["20.000"], "expected 20 ns / 50 MHz clock")

    def test_reviewed_outputs_use_rev4_pins(self):
        for port, expected_pin in REVIEWED_PINS.items():
            with self.subTest(port=port):
                self.assertEqual(self.pin_map.get(port), expected_pin)

    def test_pins_match_original_rev4_xdc_when_available(self):
        if not OFFICIAL_XDC.is_file():
            self.skipTest("original GameBub Rev4 XDC is not in this checkout")
        official = dict(package_pin_map(OFFICIAL_XDC.read_text(encoding="utf-8")))
        for port in REVIEWED_PINS:
            with self.subTest(port=port):
                self.assertEqual(self.pin_map[port], official[port])

    def test_no_fabricated_reset_backlight_or_pmod_ports(self):
        xdc_ports = {port for port, _ in self.assignments}
        self.assertFalse(
            any(re.search(r"reset|backlight|pmod", port, re.IGNORECASE)
                for port in xdc_ports),
            "probe XDC must not invent reset, backlight, or PMOD ports",
        )
        header = re.search(r"module\s+gamebub_probe\s*\((.*?)\);",
                           self.top_text, re.DOTALL)
        self.assertIsNotNone(header, "could not locate probe top-level ports")
        self.assertNotRegex(header.group(1), r"\b(?:reset|backlight|pmod)\w*\b")

    def test_safe_output_assignments(self):
        driven = constant_assignments(self.top_text)
        expected = {
            "mcu_irq_n": 0,
            "vibrate_in1": 0, "vibrate_in2": 0,
            "dac_mclk": 0, "dac_wclk": 0, "dac_bclk": 0, "dac_din": 0,
            "cart_oe_n": 1,
            "cart_bank0_dir": 0, "cart_bank1_dir": 0,
            "cart_bank2_dir": 0, "cart_bank3_dir": 0,
            "cart_pin30_dir": 0, "cart_pin31_dir": 0,
            "link_so_dir": 0, "link_si_dir": 0,
            "link_sd_dir": 0, "link_sc_dir": 0,
            "sram_ce_n": 1, "sram_we_n": 1, "sram_oe_n": 1,
            "sram_ub_n": 1, "sram_lb_n": 1,
            "sdram_cke[0]": 0, "sdram_cke[1]": 0,
            "sdram_cs_n[0]": 1, "sdram_cs_n[1]": 1,
        }
        for signal, value in expected.items():
            with self.subTest(signal=signal):
                self.assertEqual(driven.get(signal), value)


if __name__ == "__main__":
    unittest.main()
