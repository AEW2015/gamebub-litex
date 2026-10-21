# SPDX-License-Identifier: 0BSD
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "build_probe", Path(__file__).resolve().parents[1] / "tools/build_probe.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class ProbeTests(unittest.TestCase):
    def test_all_fmax_clocks_checked(self):
        report = {"utilization": {"LUT": 2}, "fmax": {
            "clk": {"achieved": 174.0, "constraint": 50.0},
            "drck": {"achieved": 8.0, "constraint": 10.0}}}
        with self.assertRaisesRegex(ValueError, "drck"):
            probe.validate_fmax(report)
        report["fmax"]["drck"]["achieved"] = 10.0
        self.assertEqual(len(probe.validate_fmax(report)), 2)

    def test_malformed_fmax_rejected(self):
        for value in (None, {}, {"clk": {}},
                      {"clk": {"achieved": float("nan"), "constraint": 50}},
                      {"clk": {"achieved": 100, "constraint": 0}},
                      {"clk": {"achieved": True, "constraint": 50}}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                probe.validate_fmax({"utilization": {"LUT": 2}, "fmax": value})

    def test_unconstrained_and_unsupported_xdc_rejected(self):
        text = "\n".join((
            "Warning: ignoring unsupported XDC option '-name' (on line 130)",
            "Warning: Clock net 'drck' has no timing constraint and will be timed at the default 50.00 MHz.",
            "Warning: XDC command not supported",
            "Info: Routing complete"))
        self.assertEqual(len(probe.rejected_pnr_diagnostics(text)), 3)
        self.assertEqual(probe.rejected_pnr_diagnostics("Info: Max frequency 174 MHz"), [])

    def test_bram_counts_ignore_library_modules(self):
        design = {"modules": {
            "gamebub_probe": {"cells": {"a": {"type": "RAMB18E1"},
                                            "b": {"type": "FDRE"}}},
            "RAMB36E1": {"cells": {"fake": {"type": "RAMB36E1"}}}}}
        self.assertEqual(probe.bram_counts(design), {"RAMB18E1": 1})

    def test_no_bram_is_empty(self):
        self.assertEqual(probe.bram_counts(
            {"modules": {"gamebub_probe": {"cells": {}}}}), {})

    def test_existing_output_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SystemExit) as result:
                probe.main(["--tools", directory, "--output", directory])
            self.assertEqual(result.exception.code, 2)

    def test_relative_output_rejected(self):
        with self.assertRaises(SystemExit) as result:
            probe.main(["--tools", "/irrelevant", "--output", "relative-output"])
        self.assertEqual(result.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
