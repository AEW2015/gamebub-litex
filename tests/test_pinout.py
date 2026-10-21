# SPDX-License-Identifier: 0BSD
"""Portable pinout completeness, electrical-standard and documentation checks."""

import io
import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from pinout import pin_rows, render_markdown, render_csv


class PinoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = pin_rows()
        cls.by_signal = {row["signal"]: row for row in cls.rows}

    def test_every_reference_signal_is_documented(self):
        self.assertEqual(len(self.rows), 198)
        self.assertEqual(len(self.by_signal), 198)
        self.assertEqual(len({row["package_pin"] for row in self.rows}), 198)

    def test_defined_vs_unmapped_is_explicit(self):
        self.assertEqual(sum(bool(row["litex_resource"]) for row in self.rows), 145)
        self.assertEqual(sum(row["tester_usage"] == "unmapped" for row in self.rows), 53)
        self.assertEqual(sum(row["tester_usage"].startswith("held ") for row in self.rows), 11)

    def test_tmds_is_not_general_gpio(self):
        tmds = [row for row in self.rows if row["iostandard"] == "TMDS_33"]
        self.assertEqual(len(tmds), 8)
        self.assertTrue(all(row["group"] == "HDMI" for row in tmds))
        self.assertTrue(all(row["fpga_direction"] == "not configured" for row in tmds))
        self.assertTrue(all(not row["litex_resource"] for row in tmds))

    def test_critical_and_extra_pins(self):
        for signal, pin in {"clk_50mhz": "P17", "mcu_irq_n": "N15", "mcu_spi_clk": "T14",
                            "pmod[0]": "V14", "tp[0]": "M14", "usb_sbu_1": "G13"}.items():
            with self.subTest(signal=signal):
                self.assertEqual(self.by_signal[signal]["package_pin"], pin)

    def test_button_order_is_native(self):
        self.assertEqual(self.by_signal["btn_a"]["litex_resource"], "buttons_n[0]")
        self.assertEqual(self.by_signal["btn_l"]["litex_resource"], "buttons_n[8]")
        self.assertEqual(self.by_signal["btn_r"]["litex_resource"], "buttons_n[9]")
        self.assertEqual(self.by_signal["btn_select"]["litex_resource"], "buttons_n[11]")

    def test_csv_contains_every_row(self):
        self.assertEqual(list(csv.DictReader(io.StringIO(render_csv(self.rows)))), self.rows)

    def test_generated_documents_are_current(self):
        self.assertEqual((ROOT / "docs/PINOUT.md").read_text(encoding="utf-8"), render_markdown(self.rows))
        self.assertEqual((ROOT / "docs/pinout.csv").read_text(encoding="utf-8"), render_csv(self.rows))
