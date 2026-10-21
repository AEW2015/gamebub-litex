# SPDX-License-Identifier: 0BSD
"""Run exact generated LiteX/VexRiscv RTL; retain bound evidence."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

PASS = "PASS gamebub_soc: actual VexRiscv boots=2"
HERE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gateware-dir", type=Path, required=True)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--firmware-elf", type=Path, required=True)
    parser.add_argument("--firmware-bin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wall-timeout", type=float, default=180)
    parser.add_argument("--trace-cpu", action="store_true", help="log startup retirement and periodic CPU/bus state")
    parser.add_argument("--simulator", choices=("icarus", "verilator"), default="icarus")
    parser.add_argument("--fault-id", action="store_true", help="negative control: force bad identifier; require firmware rejection")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error(f"output already exists: {output}")
    output.mkdir(parents=True)
    evidence = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "result": "FAIL", "commands": [], "inputs": [], "claims": ["actual VexRiscv RTL execution", "two UART boot sequences", "firmware BRAM/identifier/timer checks", "diagnostic signature", "bound safe outputs"]}
    marker = PASS
    if args.fault_id:
        marker = "PASS gamebub_soc negative control: bad identifier rejected"
        evidence["claims"] = ["negative control: actual CPU firmware rejects forced bad identifier", "GB_FAIL UART sequence", "failure status bad00002", "bound safe outputs"]
    evidence["simulator"] = args.simulator
    evidence["negative_control"] = args.fault_id

    def run(command: list[str], name: str, cwd: Path) -> subprocess.CompletedProcess:
        entry = {"argv": command, "cwd": str(cwd)}
        evidence["commands"].append(entry)
        try:
            result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=args.wall_timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            entry["timed_out"] = True
            (output / name).write_text(str(exc), encoding="utf-8")
            raise RuntimeError(f"wall timeout: {name}") from exc
        entry["exit_code"] = result.returncode
        (output / name).write_text(result.stdout + "\n[stderr]\n" + result.stderr, encoding="utf-8")
        return result

    try:
        gateware = args.gateware_dir.resolve(strict=True)
        rtl = sorted(p for p in gateware.rglob("*") if p.suffix in (".v", ".sv"))
        init = sorted(gateware.rglob("*.init"))
        if not rtl or not init:
            raise RuntimeError("generated RTL and ROM .init files are required")
        if not any("VexRiscv" in p.name for p in rtl):
            raise RuntimeError("actual generated VexRiscv RTL not found")
        inputs = rtl + init + [args.bindings.resolve(strict=True), args.firmware_elf.resolve(strict=True), args.firmware_bin.resolve(strict=True), Path(__file__).resolve(), HERE / "tb_gamebub_soc.sv"]
        evidence["inputs"] = [{"path": str(p), "sha256": sha256(p)} for p in inputs]
        stage = output / "inputs"
        stage.mkdir()
        for p in rtl + init:
            destination = stage / p.name
            if destination.exists():
                raise RuntimeError(f"duplicate source basename: {p.name}")
            shutil.copy2(p, destination)
        shutil.copy2(args.bindings, stage / "soc_bindings.vh")
        shutil.copy2(HERE / "tb_gamebub_soc.sv", stage / "tb_gamebub_soc.sv")
        for name, p in (("firmware.elf", args.firmware_elf), ("firmware.bin", args.firmware_bin)):
            shutil.copy2(p, stage / name)
        sources = [*(str(stage / p.name) for p in rtl), str(stage / "tb_gamebub_soc.sv")]
        if args.simulator == "icarus":
            compiler, runtime = shutil.which("iverilog"), shutil.which("vvp")
            if not compiler or not runtime:
                raise RuntimeError("iverilog and vvp must be on PATH")
            run([compiler, "-V"], "iverilog-version.log", stage)
            run([runtime, "-V"], "vvp-version.log", stage)
            image = output / "cpu.vvp"
            compile_command = [compiler, "-g2012", "-Wall", "-I", str(stage), "-s", "tb_gamebub_soc", "-o", str(image), *sources]
            sim_command = [runtime, str(image)]
        else:
            compiler = shutil.which("verilator")
            if not compiler:
                raise RuntimeError("verilator must be on PATH")
            run([compiler, "--version"], "verilator-version.log", stage)
            image = output / "obj_dir" / "cpu_sim"
            compile_command = [compiler, "--binary", "--timing", "-Wno-fatal", "--top-module", "tb_gamebub_soc", "--Mdir", str(image.parent), "-o", image.name, "-I" + str(stage), *sources]
            sim_command = [str(image)]
        result = run(compile_command, "compile.log", stage)
        if result.returncode:
            raise RuntimeError("RTL compilation failed")
        result = run([*sim_command, *(["+trace_cpu"] if args.trace_cpu else []), *(["+fault_id"] if args.fault_id else [])], "simulation.log", stage)
        evidence["pass_marker_observed"] = marker in result.stdout
        evidence["uart_byte_count"] = result.stdout.count("UART boot=")
        if result.returncode or marker not in result.stdout:
            raise RuntimeError("simulation failed or required PASS marker absent")
        evidence["result"] = "PASS"
    except (OSError, RuntimeError) as exc:
        evidence["error"] = str(exc)
        print(f"FAIL: {exc}; evidence {output}", file=sys.stderr)
    finally:
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    if evidence["result"] == "PASS":
        print(f"PASS: exact CPU simulation evidence in {output}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
