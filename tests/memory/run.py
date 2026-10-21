#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Compare the actual memory controllers with independent SV pin models."""

import os
import sys
import json
import hashlib
import argparse
import subprocess
from pathlib import Path

from migen import Module, Signal, Mux
from migen.fhdl import verilog

from litex.soc.interconnect import wishbone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from gamebub.memory import GameBubSRAM, GameBubSDRAM, sram_pads, sdram_pads


# Run ---------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Fresh simulation directory.")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be fresh")
    args.output.mkdir(parents=True)
    out     = args.output.resolve()
    fixture = HERE / "reference/sram_test_pkg.sv"
    if not fixture.is_file():
        raise FileNotFoundError(f"Known-good v1.6 fixture required: {fixture}")

    # Independent pin memories and upstream Wishbone SRAM models see the same
    # address and byte enables. Neither model substitutes for the DUT controller.
    top = Module()
    s   = sram_pads()
    d   = sdram_pads()
    top.submodules.sram  = sr = GameBubSRAM(s)
    top.submodules.sdram = dr = GameBubSDRAM(d)
    wb = wishbone.Interface(data_width=32, address_width=32, addressing="word")
    for field, *_ in wb.layout:
        getattr(wb, field).name_override = "wb_" + field
    top.comb += [
        wb.connect(sr.bus), wb.connect(dr.bus),
        sr.bus.cyc.eq(wb.cyc & ~wb.adr[28]), sr.bus.stb.eq(wb.stb & ~wb.adr[28]),
        dr.bus.cyc.eq(wb.cyc & wb.adr[28]),  dr.bus.stb.eq(wb.stb & wb.adr[28]),
        wb.ack.eq(Mux(wb.adr[28], dr.bus.ack, sr.bus.ack)),
        wb.dat_r.eq(Mux(wb.adr[28], dr.bus.dat_r, sr.bus.dat_r)),
        wb.err.eq(0),
    ]
    top.submodules.sram_reference  = rs = wishbone.SRAM(512*1024)
    top.submodules.sdram_reference = rd = wishbone.SRAM(32*1024*1024)
    reference_data = Signal(32, name="reference_data")
    top.comb += [
        wb.connect(rs.bus), wb.connect(rd.bus),
        rs.bus.cyc.eq(wb.cyc & ~wb.adr[28]), rs.bus.stb.eq(wb.stb & ~wb.adr[28]),
        rd.bus.cyc.eq(wb.cyc & wb.adr[28]),  rd.bus.stb.eq(wb.stb & wb.adr[28]),
        reference_data.eq(Mux(wb.adr[28], rd.bus.dat_r, rs.bus.dat_r)),
        wb.ack.eq(Mux(wb.adr[28], dr.bus.ack, sr.bus.ack)),
        wb.dat_r.eq(Mux(wb.adr[28], dr.bus.dat_r, sr.bus.dat_r)),
        wb.err.eq(0),
    ]
    dr.initialized.name_override = "memory_ready"
    ios = set(s.flatten() + d.flatten() + wb.flatten() + [dr.initialized, reference_data])
    rtl = verilog.convert(top, ios=ios, name="memory_test_top")
    (out / "memory_test_top.v").write_text(str(rtl), encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = "/opt/gamebub-openxc7-20261021/oss-cad-suite/bin:/usr/bin:/bin"
    binary = str(out / "obj/Vtb_memory")
    commands = [
        ["verilator", "--binary", "--timing", "-Wno-fatal", "--top-module", "tb_memory",
         "--Mdir", str(out / "obj"), str(out / "memory_test_top.v"), str(fixture),
         str(HERE / "pin_models.sv"), str(HERE / "tb_memory.sv")],
        [binary],
        [binary, "+corrupt_sram"],
        [binary, "+corrupt_sdram"],
    ]
    evidence = {
        "schema": 1, "status": "FAIL", "steps": [],
        "claims": "Actual memory controller RTL and independent pin models; not hardware evidence.",
    }
    try:
        for index, command in enumerate(commands):
            logfile = out / f"{index}.log"
            with logfile.open("w", encoding="utf-8") as log:
                result = subprocess.run(command, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT)
            expected_failure = index >= 2
            expected_message = "Read mismatch addr" + ("00000000" if index == 2 else "40000000")
            passed = result.returncode == 0
            if expected_failure:
                passed = result.returncode != 0 and expected_message in logfile.read_text(encoding="utf-8")
            evidence["steps"].append({
                "command": command, "returncode": result.returncode,
                "expected_pin_fault": expected_failure, "status": "PASS" if passed else "FAIL",
            })
            if not passed:
                raise RuntimeError(f"Command failed; see {logfile}")
        evidence["status"] = "PASS"
    finally:
        sources = [ROOT / "gamebub/memory.py", HERE / "pin_models.sv", HERE / "tb_memory.sv",
                   fixture, out / "memory_test_top.v"]
        evidence["sources"] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
        (out / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"MEMORY_{evidence['status']} {out}")


if __name__ == "__main__":
    main()
