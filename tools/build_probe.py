#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Build the Rev4 probe with pinned open-source tools; never load hardware."""
import argparse
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time

PART = "xc7a100tcsg324-1"
PINS = {
    "openxc7.tgz": "383785f4af92809671f08ebd7c97660c5d01f0145167538bb10667d9b929656c",
    "oss-cad-suite.tgz": "a6ccc6b96b2d985336a1061c78b2fd2bdd73e0f68690da17db88e00457881a11",
}
REVISIONS = {
    "nextpnr-xilinx-revision": "e7a6fb0e708ecac22c917ec70fc4cb3d47b5d2b5",
    "prjxray-db-revision": "6a6debcd6209e251ce6e9c1d7d0782e37fe39c99",
    "prjxray-revision": "317fdc1319a225f57b6a0e6993a37d1a4ae75e5a",
    "fasm-revision": "2f57ccb1727a120e8cacbb95c578f3c71bdcc95a",
    "yosys-release-tag": "2026-10-14",
}
INPUTS = ("gateware/gamebub_probe.v", "gateware/gamebub_probe_core.v",
          "constraints/rev4_probe.xdc")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bram_counts(netlist):
    """Count mapped block RAM in the flattened top, not library declarations."""
    cells = netlist["modules"]["gamebub_probe"]["cells"]
    return dict(collections.Counter(cell["type"] for cell in cells.values()
                                    if cell["type"].startswith("RAMB")))


def validate_fmax(report):
    """Require every reported clock to meet its explicit report constraint."""
    if not report.get("utilization") or not isinstance(report.get("fmax"), dict) or not report["fmax"]:
        raise ValueError("Place-and-route report lacks utilization or fmax")
    checked = {}
    for clock, values in report["fmax"].items():
        if not isinstance(values, dict):
            raise ValueError(f"Malformed fmax entry for {clock}")
        for key in ("achieved", "constraint"):
            value = values.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"Invalid fmax {key} for {clock}: {value!r}")
        checked[clock] = {"achieved_mhz": values["achieved"],
                          "constraint_mhz": values["constraint"],
                          "status": "PASS" if values["achieved"] >= values["constraint"] else "FAIL"}
    failures = [clock for clock, values in checked.items() if values["status"] == "FAIL"]
    if failures:
        raise ValueError("Reported clock frequency misses constraint: " + ", ".join(failures))
    return checked


def rejected_pnr_diagnostics(text):
    """Unsupported constraints and implicit clock defaults invalidate the gate."""
    pattern = re.compile(
        r"no timing constraint|unconstrained|"
        r"(?:unsupported|not supported|ignor\w*)[^\n]*(?:xdc|create_clock|option|argument)|"
        r"(?:xdc|create_clock)[^\n]*(?:unsupported|not supported|ignor\w*)",
        re.IGNORECASE)
    return [line for line in text.splitlines() if pattern.search(line)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="Absolute path to a NEW output directory")
    args = parser.parse_args(argv)
    if not args.output.is_absolute() or args.output.exists():
        parser.error("--output must be an absolute, nonexistent directory")
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
        parser.error("The pinned tools require Linux x86_64")
    source = Path(__file__).resolve().parents[1]
    tools = args.tools.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / "logs").mkdir()
    (output / "tmp").mkdir()
    evidence = {
        "schema": 1, "overall_status": "INCOMPLETE", "build_status": "FAIL",
        "part": PART, "top": "gamebub_probe", "frequency_mhz": 50,
        "source_root": str(source), "tools_root": str(tools),
        "build_script_sha256": sha256(Path(__file__)),
        "invocation": [sys.executable, str(Path(__file__).resolve()),
                       "--tools", str(tools), "--output", str(output)],
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": {"system": platform.system(), "machine": platform.machine()},
        "steps": [], "sources": {}, "artifacts": {},
        "unverified": ["Hardware operation and all physical board outputs",
                       "Speed-grade-1 timing signoff (engine uses DEFAULT corner)",
                       "Hold timing signoff", "Full GameBub functional coverage"],
        "hardware_programmed": False,
    }
    env = {"PATH": "", "LANG": "C", "LC_ALL": "C", "TZ": "UTC",
           "TMPDIR": str(output / "tmp")}

    def save():
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")

    def run(name, command):
        step = {"name": name, "command": list(map(str, command)),
                "cwd": str(output), "status": "RUNNING"}
        evidence["steps"].append(step)
        save()
        start = time.monotonic()
        with (output / "logs" / (name + ".stdout.log")).open("wb") as stdout, \
             (output / "logs" / (name + ".stderr.log")).open("wb") as stderr:
            result = subprocess.run(command, cwd=output, env=env,
                                    stdout=stdout, stderr=stderr, check=False)
        step.update(returncode=result.returncode,
                    elapsed_seconds=round(time.monotonic() - start, 3),
                    status="PASS" if result.returncode == 0 else "FAIL")
        save()
        if result.returncode:
            raise RuntimeError(f"{name} failed with exit {result.returncode}; see logs")

    try:
        # The installer may extract the openxc7 tree directly into its prefix.
        openxc7 = tools / "openxc7" if (tools / "openxc7/bin").is_dir() else tools
        suite = tools / "oss-cad-suite"
        env["PATH"] = f"{openxc7 / 'bin'}:{suite / 'bin'}:/usr/bin:/bin"
        evidence["environment"] = env.copy()
        evidence["archive_sha256"] = {}
        for name, expected in PINS.items():
            archive = tools / "downloads" / name
            actual = sha256(archive)
            evidence["archive_sha256"][name] = actual
            if actual != expected:
                raise RuntimeError(f"Pinned archive checksum mismatch: {archive}")
        info_path = openxc7 / "BUILD-INFO.json"
        info = json.loads(info_path.read_text())
        evidence["tool_build_info"] = info
        evidence["tool_build_info_sha256"] = sha256(info_path)
        for key, expected in REVISIONS.items():
            if info.get(key) != expected:
                raise RuntimeError(f"Tool source pin mismatch: {key}")
        chipdir = openxc7 / "share/nextpnr/himbaechel/xilinx"
        inventory_path = chipdir / "XILINX-PARTS-INVENTORY.json"
        inventory = json.loads(inventory_path.read_text())
        item = inventory["parts"][PART]
        evidence["part_inventory"] = item
        evidence["inventory_sha256"] = sha256(inventory_path)
        if not item.get("generated") or item.get("speed") != "1":
            raise RuntimeError("Exact -1 part is not generated in packaged inventory")
        if inventory.get("chipdb-id") != "8d0d92232f31f3db":
            raise RuntimeError("Unexpected chip database identity")
        chipdb = chipdir / "chipdb-xc7a100t.bin"
        if not chipdb.is_file() or chipdb.stat().st_size == 0:
            raise RuntimeError("Missing exact-device chipdb")
        db = openxc7 / "share/nextpnr/external/prjxray-db/artix7"
        part_file = db / PART / "part.yaml"
        evidence["part_yaml_sha256"] = sha256(part_file)
        for relative in INPUTS:
            src = source / relative
            dest = output / src.name
            shutil.copy2(src, dest)
            evidence["sources"][relative] = sha256(dest)
        for binary in ("yosys", "nextpnr-xilinx", "fasm2frames", "xc7frames2bit"):
            resolved = shutil.which(binary, path=env["PATH"])
            if not resolved:
                raise RuntimeError(f"Missing tool: {binary}")
            evidence.setdefault("executables", {})[binary] = {
                "path": resolved, "wrapper_sha256": sha256(resolved)}
        save()
        run("yosys_version", ["yosys", "-V"])
        run("nextpnr_version", ["nextpnr-xilinx", "--version"])
        run("synthesis", ["yosys", "-p",
            "read_verilog gamebub_probe.v gamebub_probe_core.v; "
            "synth_xilinx -flatten -arch xc7 -top gamebub_probe; "
            "write_json gamebub_probe.json"])
        counts = bram_counts(json.loads((output / "gamebub_probe.json").read_text()))
        evidence["inferred_bram_cells"] = counts
        if not counts:
            raise RuntimeError("Synthesis did not infer any RAMB block RAM cells")
        run("place_route", ["nextpnr-xilinx", "--device", PART,
            "--json", "gamebub_probe.json", "-o", "xdc=rev4_probe.xdc",
            "-o", "fasm=gamebub_probe.fasm", "--freq", "50", "--seed", "1",
            "--report", "report.json"])
        report = json.loads((output / "report.json").read_text())
        evidence["pnr_report"] = report
        pnr_logs = "\n".join((output / "logs" / ("place_route." + stream + ".log")).read_text(errors="replace")
                             for stream in ("stdout", "stderr"))
        rejected = rejected_pnr_diagnostics(pnr_logs)
        evidence["rejected_pnr_diagnostics"] = rejected
        evidence["pnr_warnings"] = [line for line in pnr_logs.splitlines() if "warning" in line.lower()]
        if rejected:
            raise RuntimeError("Unaccepted PNR constraints: " + "; ".join(rejected))
        evidence["reported_fmax_checks"] = validate_fmax(report)
        run("frames", ["fasm2frames", "--part", PART, "--db-root", str(db),
                       "gamebub_probe.fasm"])
        shutil.copyfile(output / "logs/frames.stdout.log", output / "gamebub_probe.frames")
        if (output / "logs/frames.stderr.log").stat().st_size:
            raise RuntimeError("fasm2frames emitted diagnostics; refusing bitstream")
        run("bitstream", ["xc7frames2bit", "--part_file", str(part_file),
            "--part_name", PART, "--frm_file", "gamebub_probe.frames",
            "--output_file", "gamebub_probe.bit"])
        if (output / "gamebub_probe.bit").stat().st_size == 0:
            raise RuntimeError("Empty bitstream")
        evidence["build_status"] = "PASS"
    except (Exception, KeyboardInterrupt) as error:
        evidence["error"] = f"{type(error).__name__}: {error}"
        for step in evidence["steps"]:
            if step["status"] == "RUNNING":
                step["status"] = "FAIL"
        print(evidence["error"], file=sys.stderr)
    finally:
        for artifact in sorted(output.rglob("*")):
            if artifact.is_file() and artifact.name != "evidence.json":
                evidence["artifacts"][str(artifact.relative_to(output))] = {
                    "bytes": artifact.stat().st_size, "sha256": sha256(artifact)}
        evidence["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        save()
    print(f"Build {evidence['build_status']}; overall INCOMPLETE; evidence: {output / 'evidence.json'}")
    return 0 if evidence["build_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
