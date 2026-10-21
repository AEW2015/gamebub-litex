# SPDX-License-Identifier: 0BSD
"""Run the portable GameBub probe testbench with Icarus Verilog."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    ROOT / "gateware" / "gamebub_probe_core.v",
    ROOT / "sim" / "tb_gamebub_probe.sv",
)
PASS_MARKER = "PASS gamebub_probe:"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(command: list[str], log_path: Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    log_path.write_text(
        "$ " + " ".join(command) + "\n"
        + result.stdout
        + ("\n[stderr]\n" + result.stderr if result.stderr else ""),
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="new, previously nonexistent directory for simulation evidence",
    )
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.exists():
        parser.error(f"output directory already exists; choose a new path: {output}")
    output.mkdir(parents=True)

    missing = [str(path) for path in SOURCES if not path.is_file()]
    if missing:
        (output / "run.log").write_text("Missing source files:\n" + "\n".join(missing) + "\n", encoding="utf-8")
        print("Missing simulation source(s): " + ", ".join(missing), file=sys.stderr)
        return 2

    iverilog = shutil.which("iverilog")
    vvp = shutil.which("vvp")
    if not iverilog or not vvp:
        (output / "run.log").write_text("Required executables iverilog and vvp were not found on PATH.\n", encoding="utf-8")
        print("Required executables iverilog and vvp were not found on PATH.", file=sys.stderr)
        return 2

    compiled_image = output / "gamebub_probe.vvp"
    compile_command = [
        iverilog,
        "-g2012",
        "-s",
        "tb_gamebub_probe",
        "-o",
        str(compiled_image),
        *(str(path) for path in SOURCES),
    ]
    compile_result = run(compile_command, output / "compile.log", ROOT)
    if compile_result.returncode != 0:
        print(f"Icarus compile failed; see {output / 'compile.log'}", file=sys.stderr)
        return compile_result.returncode or 1

    sim_result = run([vvp, str(compiled_image)], output / "simulation.log", ROOT)
    passed = sim_result.returncode == 0 and PASS_MARKER in sim_result.stdout
    evidence = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "result": "PASS" if passed else "FAIL",
        "simulator": "Icarus Verilog / vvp",
        "iverilog": iverilog,
        "vvp": vvp,
        "platform": sys.platform,
        "cwd": str(ROOT),
        "compile_exit_code": compile_result.returncode,
        "simulation_exit_code": sim_result.returncode,
        "pass_marker_observed": PASS_MARKER in sim_result.stdout,
        "sources": [
            {"path": str(path.relative_to(ROOT)), "sha256": digest(path)}
            for path in SOURCES
        ],
        "logs": ["compile.log", "simulation.log"],
    }
    (output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    if not passed:
        print(f"Simulation failed or did not print the required PASS marker; see {output}", file=sys.stderr)
        return sim_result.returncode or 1

    print(f"PASS: simulation evidence saved in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
