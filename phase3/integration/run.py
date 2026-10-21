# SPDX-License-Identifier: 0BSD
"""Execute exact generated combined RTL with pin models; record normal/fault runs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        parser.error("output must be fresh")
    out.mkdir(parents=True)
    stage = out / "inputs"
    shutil.copytree(args.generated / "gateware", stage)
    for source in (HERE / "tb_combined.sv", HERE.parent / "memory/pin_models.sv",
                   HERE.parent / "esp32/qspi_host_bfm.sv"):
        shutil.copy2(source, stage / source.name)
    shutil.copytree(args.generated / "firmware", out / "firmware")
    evidence = {"status": "FAIL", "hardware_programmed": False,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sources": {p.name: sha(p) for p in stage.iterdir() if p.is_file()}, "commands": []}
    env = os.environ.copy()
    env["PATH"] = "/opt/gamebub-openxc7-20261021/oss-cad-suite/bin:/usr/bin:/bin"
    def run(argv, cwd, logfile):
        step = {"argv": list(map(str, argv)), "cwd": str(cwd)}
        evidence["commands"].append(step)
        result = subprocess.run(argv, cwd=cwd, env=env, text=True,
                                capture_output=True, timeout=180)
        logfile.write_text(result.stdout + "\n[stderr]\n" + result.stderr)
        step["returncode"] = result.returncode
        if result.returncode:
            raise RuntimeError(f"command failed; see {logfile}")
        return result.stdout
    try:
        run(["verilator", "--version"], stage, out / "version.log")
        sources = [str(p) for p in sorted(stage.iterdir()) if p.suffix in (".v", ".sv")]
        binary = out / "obj" / "combined_sim"
        run(["verilator", "--binary", "--timing", "-Wno-fatal", "--top-module", "tb_combined",
             "--Mdir", str(binary.parent), "-o", binary.name, *sources], stage, out / "compile.log")
        for mode in ("normal", "corrupt_sram", "corrupt_sdram"):
            run_dir = out / mode
            run_dir.mkdir()
            for source in stage.glob("*.init"):
                shutil.copy2(source, run_dir / source.name)
            text = run([str(binary)] + ([] if mode == "normal" else ["+" + mode]),
                       run_dir, out / f"{mode}.log")
            marker = "COMBINED_PASS" if mode == "normal" else "COMBINED_NEGATIVE_PASS"
            if marker not in text:
                raise RuntimeError(f"missing {mode} pass marker")
        evidence["status"] = "PASS"
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        evidence["error"] = str(error)
        raise
    finally:
        evidence["artifacts"] = {str(p.relative_to(out)): sha(p) for p in out.rglob("*")
            if p.is_file() and "obj" not in p.relative_to(out).parts and p.name != "evidence.json"}
        (out / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"PASS combined normal/SRAM-fault/SDRAM-fault: {out}")


if __name__ == "__main__":
    main()
