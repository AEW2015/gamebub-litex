# SPDX-License-Identifier: 0BSD
"""Simulate the complete GameBub probe top using open behavioral primitives."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    ROOT / "sim" / "open_primitives.v",
    ROOT / "gateware" / "gamebub_probe_core.v",
    ROOT / "gateware" / "gamebub_probe.v",
    ROOT / "sim" / "tb_gamebub_probe_top.sv",
)
PASS_MARKER = "PASS gamebub_probe_top:"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], cwd: Path, log: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    log.write_text(
        "$ " + " ".join(command) + "\n" + result.stdout
        + ("\n[stderr]\n" + result.stderr if result.stderr else ""),
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True,
        help="path to a new directory for logs and hash-bound simulation evidence",
    )
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.exists():
        parser.error(f"output directory already exists; choose a new path: {output}")
    output.mkdir(parents=True)

    missing = [str(path) for path in SOURCES if not path.is_file()]
    if missing:
        (output / "run.log").write_text("Missing source files:\n" + "\n".join(missing) + "\n", encoding="utf-8")
        print("Missing source file(s): " + ", ".join(missing), file=sys.stderr)
        return 2
    iverilog, vvp = shutil.which("iverilog"), shutil.which("vvp")
    if not iverilog or not vvp:
        (output / "run.log").write_text("Required executables iverilog and vvp were not found on PATH.\n", encoding="utf-8")
        print("Required executables iverilog and vvp were not found on PATH.", file=sys.stderr)
        return 2

    image = output / "gamebub_probe_top.vvp"
    compile_command = [iverilog, "-g2012", "-s", "tb_gamebub_probe_top", "-o", str(image),
                       *(str(path) for path in SOURCES)]
    compiled = run(compile_command, ROOT, output / "compile.log")
    if compiled.returncode:
        print(f"Icarus compile failed; see {output / 'compile.log'}", file=sys.stderr)
        return compiled.returncode or 1

    simulation = run([vvp, str(image)], ROOT, output / "simulation.log")
    passed = simulation.returncode == 0 and PASS_MARKER in simulation.stdout
    evidence = {
        "schema": 1,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "result": "PASS" if passed else "FAIL",
        "scope": "source-level top simulation with behavioral BUFG/BSCANE2 stubs",
        "user_chain": 4,
        "system_clock_mhz": 50,
        "simulated_drck_mhz": 10,
        "hardware_programmed": False,
        "iverilog": iverilog,
        "vvp": vvp,
        "platform": sys.platform,
        "source_root": str(ROOT),
        "compile_exit_code": compiled.returncode,
        "simulation_exit_code": simulation.returncode,
        "pass_marker_observed": PASS_MARKER in simulation.stdout,
        "sources": [
            {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}
            for path in SOURCES
        ],
        "logs": ["compile.log", "simulation.log"],
        "limitations": [
            "Behavioral primitive stubs do not model FPGA clock routing or physical JTAG.",
            "Simulation does not verify physical I/O levels or hardware operation.",
        ],
    }
    (output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    if not passed:
        print(f"Simulation failed or required PASS marker was absent; see {output}", file=sys.stderr)
        return simulation.returncode or 1
    print(f"PASS: top simulation evidence saved in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
