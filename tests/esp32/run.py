# SPDX-License-Identifier: 0BSD
"""Run the endpoint pin-level simulation into a fresh evidence directory.

The default simulator is Verilator 5+ (``--binary --timing``). Icarus is an
explicit compatibility option for toolchains that parse the endpoint source.
"""

import sys
import json
import time
import shutil
import hashlib
import argparse
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCES = (
    HERE.parents[1] / "gamebub" / "rtl" / "esp32_v102_endpoint.sv",
    HERE / "qspi_host_bfm.sv",
    HERE / "tb_endpoint_protocol.sv",
)
DEFAULT_OUTPUT = HERE.parents[1] / "build" / "esp32-protocol"
PASS_TEXT = "PASS: official QSPI reads/writes, buttons, IRQ W1C and overlay bounds"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def capture(command, *, cwd, logfile):
    result = subprocess.run(command, cwd=cwd, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    logfile.write_text(result.stdout, encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="new evidence directory (must not already exist)")
    parser.add_argument("--simulator", choices=("verilator", "icarus"),
                        default="verilator")
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.exists():
        parser.error(f"evidence output already exists; choose a fresh path: {output}")
    output.mkdir(parents=True)
    staged = output / "source"
    staged.mkdir()
    for source in SOURCES:
        shutil.copy2(source, staged / source.name)

    simulator = "verilator" if args.simulator == "verilator" else "iverilog"
    tool = shutil.which(simulator)
    evidence = {
        "status": "RUNNING",
        "simulator": args.simulator,
        "created_utc_epoch": int(time.time()),
        "working_directory": str(output),
        "staged_sources": [
            {"path": f"source/{source.name}",
             "sha256": sha256(staged / source.name),
             "original_sha256": sha256(source)}
            for source in SOURCES
        ],
        "runner_sha256": sha256(Path(__file__)),
        "commands": [],
    }
    if not tool:
        evidence["status"] = "ERROR_SIMULATOR_NOT_FOUND"
        evidence["error"] = f"{simulator} not found on PATH"
        missing_version_command = [simulator, "--version"] if args.simulator == "verilator" else [simulator, "-V"]
        evidence["simulator_version_command"] = missing_version_command
        evidence["commands"].append(missing_version_command)
        (output / "simulator-version.txt").write_text(
            f"{simulator} not found on PATH\n", encoding="utf-8")
        (output / "compile.log").write_text("", encoding="utf-8")
        (output / "simulation.log").write_text("", encoding="utf-8")
        (output / "evidence.json").write_text(
            json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(f"ERROR: {simulator} not found; evidence: {output}", file=sys.stderr)
        return 2

    version_args = [tool, "--version"] if args.simulator == "verilator" else [tool, "-V"]
    version = subprocess.run(version_args, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (output / "simulator-version.txt").write_text(version.stdout, encoding="utf-8")
    evidence["simulator_version_command"] = version_args
    evidence["simulator_version"] = version.stdout.strip()
    source_args = [f"source/{source.name}" for source in SOURCES]

    if args.simulator == "verilator":
        obj_dir = output / "obj_dir"
        compile_command = [tool, "--binary", "--timing", "-Wno-fatal", "--top-module",
                           "tb_endpoint_protocol", "--Mdir", str(obj_dir),
                           *source_args]
        compile_result = capture(compile_command, cwd=output,
                                 logfile=output / "compile.log")
        evidence["commands"].append(compile_command)
        if compile_result.returncode:
            evidence["status"] = "FAIL_COMPILE"
            evidence["compile_exit_code"] = compile_result.returncode
            (output / "simulation.log").write_text("not run\n", encoding="utf-8")
        else:
            executable = obj_dir / "Vtb_endpoint_protocol"
            simulation_command = [str(executable)]
            simulation_result = capture(simulation_command, cwd=output,
                                         logfile=output / "simulation.log")
            evidence["commands"].append(simulation_command)
            evidence["simulation_exit_code"] = simulation_result.returncode
            passed = simulation_result.returncode == 0 and PASS_TEXT in simulation_result.stdout
            evidence["status"] = "PASS" if passed else "FAIL_SIMULATION"
    else:
        executable = output / "tb_endpoint_protocol.vvp"
        compile_command = [tool, "-g2012", "-s", "tb_endpoint_protocol",
                           "-o", str(executable), *source_args]
        compile_result = capture(compile_command, cwd=output,
                                 logfile=output / "compile.log")
        evidence["commands"].append(compile_command)
        if compile_result.returncode:
            evidence["status"] = "FAIL_COMPILE"
            evidence["compile_exit_code"] = compile_result.returncode
            (output / "simulation.log").write_text("not run\n", encoding="utf-8")
        else:
            vvp = shutil.which("vvp")
            if not vvp:
                evidence["status"] = "ERROR_VVP_NOT_FOUND"
                (output / "simulation.log").write_text("vvp not found on PATH\n",
                                                       encoding="utf-8")
            else:
                simulation_command = [vvp, str(executable)]
                simulation_result = capture(simulation_command, cwd=output,
                                             logfile=output / "simulation.log")
                evidence["commands"].append(simulation_command)
                evidence["simulation_exit_code"] = simulation_result.returncode
                passed = simulation_result.returncode == 0 and PASS_TEXT in simulation_result.stdout
                evidence["status"] = "PASS" if passed else "FAIL_SIMULATION"

    (output / "evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"{evidence['status']}: {output}")
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
