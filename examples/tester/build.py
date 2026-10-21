# SPDX-License-Identifier: 0BSD
"""Pinned openXC7 adapter with narrowly checked physical-primitive diagnostics."""
import re
import sys
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import build_backend as baseline

original_policy = baseline.synthesis_diagnostics
original_fmax = baseline.validate_fmax


# Physical Build Policy ---------------------------------------------------------------------------

def physical_fmax(report):
    checked = original_fmax(report)
    expected = {"basesoc_crg_clkin": 50.0, "VexRiscv.clk": 50.0,
                "basesoc_crg_clkout_buf2": 200.0,
                "basesoc_crg_clkout_buf0": 800.0 / 27.25,
                "basesoc_basesoc_jtag_tck": 10.0}
    for name, mhz in expected.items():
        assert name in checked, f"Missing clock report: {name}"
        assert abs(checked[name]["constraint_mhz"] - mhz) < 0.001, f"Wrong clock constraint: {name}"
    return checked


def physical_policy(log, netlist, cpu_sha):
    clock_names = ("basesoc_crg_clkin", "VexRiscv.clk", "basesoc_crg_clkout_buf2",
                   "basesoc_crg_clkout_buf0", "basesoc_basesoc_jtag_tck")
    nets = netlist["modules"]["gamebub_soc"]["netnames"]
    for name in clock_names:
        assert name in nets and len(nets[name]["bits"]) == 1, f"Missing physical clock net: {name}"
    cells = list(netlist["modules"]["gamebub_soc"]["cells"].values())
    inouts = {bit for port in netlist["modules"]["gamebub_soc"]["ports"].values()
              if port["direction"] == "inout" for bit in port["bits"]}
    buffers = [cell for cell in cells if cell["type"] == "IOBUF"]
    io_ok = len(buffers) == 36 and len(inouts) == 36 and all(
        cell["connections"]["IO"][0] in inouts for cell in buffers)
    assert not any("TBUF" in cell["type"] or "tribuf" in cell["type"] for cell in cells)
    mmcms = [cell for cell in cells if cell["type"] == "MMCME2_ADV"]
    assert len(mmcms) == 1 and mmcms[0]["parameters"]["CLKOUT0_DIVIDE_F"] == "27.250000"
    filtered, extra = [], []
    for line in log.splitlines():
        reason = None
        if re.fullmatch(r"gamebub_soc.v:\d+: Warning: Yosys has only limited support for tri-state logic at the moment\.", line) and io_ok:
            reason = "All36 data bits map to top-level IOBUFs; no internal tristate cells survive"
        elif re.fullmatch(r"gamebub_soc.v:\d+: Warning: Replacing floating point parameter MMCME2_ADV\.(CLKIN1_PERIOD = 20\.000000|CLKOUT0_DIVIDE_F = 27\.250000|REF_JITTER1 = 0\.010000) with string\.", line):
            reason = "Yosys parameter representation; physical MMCM fractional divider retained and checked"
        if reason:
            extra.append({"diagnostic": line, "reason": reason})
        else:
            filtered.append(line)
    result = original_policy("\n".join(filtered), netlist, cpu_sha)
    result["synthesis_diagnostics_allowlisted"].extend(extra)
    result["physical_primitive_checks"] = {"top_level_iobufs": len(buffers), "all36_inout_bits_mapped": io_ok,
        "mmcm_count": 1, "fractional_video_divider": "27.250000",
        "canonical_clock_nets_present": list(clock_names),
        "wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    return result


if __name__ == "__main__":
    baseline.synthesis_diagnostics = physical_policy
    baseline.validate_fmax = physical_fmax
    raise SystemExit(baseline.main())
