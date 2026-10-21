# SPDX-License-Identifier: 0BSD
"""Portable tests for strict clock and diagnostic gates."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_policy import validate_fmax, rejected_pnr_diagnostics


class BuildPolicyTests(unittest.TestCase):
    def test_all_clocks_must_pass(self):
        report = {"utilization": {"LUT": 2}, "fmax": {
            "sys":     {"achieved": 100, "constraint": 50},
            "service": {"achieved": 199, "constraint": 200},
        }}
        with self.assertRaisesRegex(ValueError, "service"):
            validate_fmax(report)
        report["fmax"]["service"]["achieved"] = 203
        self.assertEqual(len(validate_fmax(report)), 2)

    def test_invalid_reports_fail_closed(self):
        for fmax in (None, {}, {"sys": {}}, {"sys": {"achieved": True, "constraint": 50}},
                     {"sys": {"achieved": float("nan"), "constraint": 50}},
                     {"sys": {"achieved": 100, "constraint": 0}}):
            with self.subTest(fmax=fmax), self.assertRaises(ValueError):
                validate_fmax({"utilization": {"LUT": 2}, "fmax": fmax})

    def test_missing_utilization_fails(self):
        with self.assertRaises(ValueError):
            validate_fmax({"fmax": {"sys": {"achieved": 100, "constraint": 50}}})

    def test_unsupported_constraints_are_rejected(self):
        diagnostics = "\n".join([
            "Warning: ignoring unsupported XDC option '-name'",
            "Warning: clock has no timing constraint",
            "Warning: XDC command not supported",
        ])
        self.assertEqual(len(rejected_pnr_diagnostics(diagnostics)), 3)

    def test_normal_report_is_not_rejected(self):
        self.assertEqual(rejected_pnr_diagnostics("Info: Routing complete"), [])
