# SPDX-License-Identifier: 0BSD
"""Dependency-free checks of the public tester layout and source bindings."""

import ast
import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SourceLayoutTests(unittest.TestCase):
    def test_one_main_example(self):
        examples = sorted(path.name for path in (ROOT / "examples").iterdir() if path.is_dir())
        self.assertEqual(examples, ["tester"])

    def test_tester_entry_points_exist(self):
        for name in ("generate.py", "build.py", "soc.py", "firmware/main.c", "firmware/start.S"):
            with self.subTest(name=name):
                self.assertTrue((ROOT / "examples/tester" / name).is_file())

    def test_python_sources_parse(self):
        for folder in ("gamebub", "examples", "tools", "tests"):
            for path in (ROOT / folder).rglob("*.py"):
                with self.subTest(path=path.relative_to(ROOT)):
                    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_reference_hashes_are_preserved(self):
        references = {
            "gamebub/reference/rev_4.xdc": "af2d5b6e9a157ed9636330cc1105180bd4bc7384e8c67d622119944b923953b8",
            "tests/esp32/reference/esp32_v102_endpoint.sv": "b1dabe65572c8ad3ec6f1cdd5e149ae99bddcdbf8e5678eb7ba9403e53dc2db0",
            "tests/esp32/reference/fpga_driver_v1.0.2.rs": "d480fabf42491a9f128e8c14633bfee5e7718276f32917ab5cf1f2b01ab1f8d1",
            "tests/memory/reference/sram_test_pkg.sv": "724fd393ec09a812d8bda97a02c7639ad71ba19fb4be14f604264e512b7d6edc",
            "tests/video/reference/gamebub_axis_raster.v": "77690c67f95925eb551187c0ec37f81ac2782b0e978d03d55595f85efdef03f1",
        }
        for name, expected in references.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)

    def test_programmer_requires_explicit_target(self):
        script = (ROOT / "tools/program.tcl").read_text(encoding="utf-8")
        self.assertIn("GAMEBUB_JTAG_SERIAL", script)
        self.assertIn("BIT hash mismatch", script)
        self.assertIn('ne "xc7a100t"', script)

    def test_memory_tests_keep_scratch_bounds(self):
        source = (ROOT / "examples/tester/firmware/main.c").read_text(encoding="utf-8")
        self.assertIn("0x1000", source)
        self.assertIn("1024", source)
