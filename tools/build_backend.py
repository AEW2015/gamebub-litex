#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Build already-generated LiteX RTL with pinned openxc7; never access hardware."""
import re
import sys
import json
import time
import shutil
import argparse
import platform
import collections
import subprocess
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE / "tools"))
# Keep tool pins and diagnostic policy shared by builds and portable tests.
from build_policy import PART, PINS, REVISIONS, sha256, validate_fmax, rejected_pnr_diagnostics

CPU_SHA256 = "a2f6dbdab57278866f6b371b5b7d8b74bc813444757ef06195e8559f0d02e279"


def synthesis_diagnostics(text, netlist, cpu_sha256):
    """Classify exact upstream diagnostics; fail closed on any unknown warning."""
    diagnostics = [line for line in text.splitlines()
                   if re.search(r"\b(?:warning|error)\s*:", line, re.IGNORECASE)]
    isrvc = [
        "Warning: Wire VexRiscv.\\IBusSimplePlugin_rspJoin_fetchRsp_isRvc is used but has no driver.",
        "Warning: Wire gamebub_soc.\\VexRiscv.IBusSimplePlugin_rspJoin_fetchRsp_isRvc is used but has no driver.",
    ]
    check_counts = re.findall(r"Found and reported (\d+) problems\.", text)
    clean_final_check = bool(check_counts and check_counts[-1] == "0")
    no_isrvc_netlist = "isRvc" not in json.dumps(netlist)
    exact_isrvc_pair = sorted(line for line in diagnostics if line in isrvc) == sorted(isrvc)
    isrvc_allowed = (cpu_sha256 == CPU_SHA256 and exact_isrvc_pair
                     and clean_final_check and no_isrvc_netlist)
    allowed, rejected = [], []
    for line in diagnostics:
        reason = None
        if line in isrvc and isrvc_allowed:
            reason = "Pinned no-C CPU metadata has no consumer; removed before clean final CHECK"
        elif line == "ABC: Warning: The network is combinational.":
            reason = "ABC9 combinational mapping; registers are external timing boxes"
        elif re.fullmatch(
            r"Lexer warning: The SystemVerilog keyword `bit' \(at "
            r"[^\s]+/oss-cad-suite/lib/\.\./share/yosys/abc9_map\.v:35\) "
            r"is not recognized unless read_verilog is called with -sv!", line):
            reason = "Pinned Yosys abc9_map.v uses bit as a Verilog identifier"
        if reason:
            allowed.append({"diagnostic": line, "reason": reason})
        else:
            rejected.append(line)
    failures = []
    if rejected:
        failures.append("Unknown or unaccepted synthesis diagnostics")
    if not clean_final_check:
        failures.append("Final synthesis CHECK is absent or reports problems")
    if not no_isrvc_netlist:
        failures.append("Unused isRvc metadata survives in mapped netlist")
    if "ABC: Networks are equivalent." not in text:
        failures.append("ABC9 mapped-network equivalence did not pass")
    if re.search(r"^ABC: \+ &mfs(?:\s|$)", text, re.MULTILINE):
        failures.append("Disabled optional ABC9 mfs optimization was unexpectedly executed")
    return {"synthesis_diagnostics_allowlisted": allowed,
            "synthesis_diagnostics_rejected": rejected,
            "synthesis_diagnostic_checks": {
                "status": "FAIL" if failures else "PASS", "failures": failures,
                "cpu_sha256": cpu_sha256, "exact_isrvc_warning_pair": exact_isrvc_pair,
                "final_check_clean": clean_final_check, "mapped_netlist_has_no_isrvc": no_isrvc_netlist,
                "abc9_equivalence_passed": "ABC: Networks are equivalent." in text}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", type=Path, required=True)
    parser.add_argument("--gateware-dir", type=Path, required=True)
    parser.add_argument("--xdc", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=2)
    parser.add_argument("--timing-weight", type=int, default=30)
    parser.add_argument("--router", choices=("router1", "router2"), default="router2")
    parser.add_argument("--timing-ripup", action="store_true")
    args = parser.parse_args(argv)
    if not args.output.is_absolute() or args.output.exists():
        parser.error("--output must be an absolute, nonexistent directory")
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
        parser.error("The pinned tools require Linux x86_64")
    gateware = args.gateware_dir.resolve()
    if not (gateware / "gamebub_soc.v").is_file() or not (gateware / "VexRiscv_Min.v").is_file():
        parser.error("--gateware-dir must contain gamebub_soc.v and VexRiscv_Min.v")
    if not args.xdc.is_file():
        parser.error("--xdc must name an existing file")
    tools, output = args.tools.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / "logs").mkdir()
    (output / "tmp").mkdir()
    evidence = {
        "schema": 1, "overall_status": "INCOMPLETE", "build_status": "FAIL",
        "part": PART, "top": "gamebub_soc", "frequency_mhz": 50,
        "source_root": str(SOURCE), "gateware_dir": str(gateware), "xdc": str(args.xdc.resolve()),
        "tools_root": str(tools), "build_script_sha256": sha256(__file__),
        "build_policy_sha256": sha256(SOURCE / "tools/build_policy.py"),
        "invocation": [sys.executable, str(Path(__file__).resolve()), "--tools", str(tools),
                       "--gateware-dir", str(gateware), "--xdc", str(args.xdc.resolve()),
                       "--output", str(output)],
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": {"system": platform.system(), "machine": platform.machine()},
        "steps": [], "sources": {}, "artifacts": {}, "hardware_programmed": False,
        "unverified": ["Hardware operation and physical board outputs",
                       "Speed-grade-1 timing signoff (engine uses DEFAULT corner)",
                       "Hold timing signoff", "Full GameBub functional coverage"],
    }
    env = {"PATH": "", "LANG": "C", "LC_ALL": "C", "TZ": "UTC", "TMPDIR": str(output / "tmp")}

    def save():
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")

    def run(name, command):
        step = {"name": name, "command": list(map(str, command)), "cwd": str(output), "status": "RUNNING"}
        evidence["steps"].append(step)
        save()
        start = time.monotonic()
        with (output / "logs" / (name + ".stdout.log")).open("wb") as stdout, \
             (output / "logs" / (name + ".stderr.log")).open("wb") as stderr:
            result = subprocess.run(command, cwd=output, env=env, stdout=stdout, stderr=stderr, check=False)
        step.update(returncode=result.returncode, elapsed_seconds=round(time.monotonic() - start, 3),
                    status="PASS" if result.returncode == 0 else "FAIL")
        save()
        if result.returncode:
            raise RuntimeError(f"{name} failed with exit {result.returncode}; see logs")

    try:
        openxc7 = tools / "openxc7" if (tools / "openxc7/bin").is_dir() else tools
        suite = tools / "oss-cad-suite"
        env["PATH"] = f"{openxc7 / 'bin'}:{suite / 'bin'}:/usr/bin:/bin"
        evidence["environment"] = env.copy()
        evidence["archive_sha256"] = {}
        for name, expected in PINS.items():
            actual = sha256(tools / "downloads" / name)
            evidence["archive_sha256"][name] = actual
            if actual != expected:
                raise RuntimeError(f"Pinned archive checksum mismatch: {name}")
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
        if not chipdb.is_file() or not chipdb.stat().st_size:
            raise RuntimeError("Missing exact-device chipdb")
        db = openxc7 / "share/nextpnr/external/prjxray-db/artix7"
        part_file = db / PART / "part.yaml"
        evidence["part_yaml_sha256"] = sha256(part_file)
        verilog = []
        staged = sorted(p for p in gateware.rglob("*") if p.is_file() and p.suffix in (".v", ".init"))
        if not any(p.suffix == ".init" for p in staged):
            raise RuntimeError("Missing ROM/RAM .init source; refusing uninitialized CPU build")
        for src in staged:
            relative = src.relative_to(gateware)
            if not re.fullmatch(r"[A-Za-z0-9_./-]+", relative.as_posix()):
                raise RuntimeError(f"Unsupported source filename: {relative}")
            if relative.parts[0] in ("logs", "tmp") or relative.name == "soc_constraints.xdc":
                raise RuntimeError(f"Reserved staged source filename: {relative}")
            dest = output / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            evidence["sources"][relative.as_posix()] = sha256(dest)
            if sha256(src) != evidence["sources"][relative.as_posix()]:
                raise RuntimeError(f"Source changed while staging: {src}")
            if src.suffix == ".v":
                verilog.append(relative.as_posix())
        shutil.copy2(args.xdc, output / "soc_constraints.xdc")
        evidence["sources"]["soc_constraints.xdc"] = sha256(output / "soc_constraints.xdc")
        for binary in ("yosys", "nextpnr-xilinx", "fasm2frames", "xc7frames2bit"):
            resolved = shutil.which(binary, path=env["PATH"])
            if not resolved:
                raise RuntimeError(f"Missing tool: {binary}")
            evidence.setdefault("executables", {})[binary] = {"path": resolved, "wrapper_sha256": sha256(resolved)}
        save()
        run("yosys_version", ["yosys", "-V"])
        run("nextpnr_version", ["nextpnr-xilinx", "--version"])
        run("synthesis", ["yosys", "-p", "scratchpad -set abc9.nomfs 1; read_verilog " + " ".join(verilog) + "; "
            "synth_xilinx -flatten -arch xc7 -top gamebub_soc; check -assert; write_json gamebub_soc.json"])
        netlist = json.loads((output / "gamebub_soc.json").read_text())
        synthesis_logs = "\n".join((output / "logs" / ("synthesis." + stream + ".log")).read_text(errors="replace")
                                    for stream in ("stdout", "stderr"))
        evidence.update(synthesis_diagnostics(synthesis_logs, netlist, evidence["sources"]["VexRiscv_Min.v"]))
        save()
        if evidence["synthesis_diagnostic_checks"]["status"] != "PASS":
            raise RuntimeError("; ".join(evidence["synthesis_diagnostic_checks"]["failures"]))
        counts = dict(collections.Counter(c["type"] for c in netlist["modules"]["gamebub_soc"]["cells"].values()
                                          if c["type"].startswith("RAMB")))
        evidence["inferred_bram_cells"] = counts
        if not counts:
            raise RuntimeError("Synthesis did not infer RAMB block RAM cells")
        run("place_route", ["nextpnr-xilinx", "--device", PART, "--json", "gamebub_soc.json",
            "-o", "xdc=soc_constraints.xdc", "-o", "fasm=gamebub_soc.fasm", "--freq", "50",
            "--seed", str(args.seed), "--placer-heap-timingweight", str(args.timing_weight),
            "--router", args.router, *(["--tmg-ripup"] if args.timing_ripup else []), "--report", "report.json"])
        report = json.loads((output / "report.json").read_text())
        evidence["pnr_report"] = report
        logs = "\n".join((output / "logs" / ("place_route." + stream + ".log")).read_text(errors="replace")
                          for stream in ("stdout", "stderr"))
        rejected = rejected_pnr_diagnostics(logs)
        evidence["rejected_pnr_diagnostics"] = rejected
        evidence["pnr_warnings"] = [line for line in logs.splitlines() if "warning" in line.lower()]
        if rejected:
            raise RuntimeError("Unaccepted PNR constraints: " + "; ".join(rejected))
        evidence["reported_fmax_checks"] = validate_fmax(report)
        run("frames", ["fasm2frames", "--part", PART, "--db-root", str(db), "gamebub_soc.fasm"])
        shutil.copyfile(output / "logs/frames.stdout.log", output / "gamebub_soc.frames")
        if (output / "logs/frames.stderr.log").stat().st_size:
            raise RuntimeError("fasm2frames emitted diagnostics; refusing bitstream")
        run("bitstream", ["xc7frames2bit", "--part_file", str(part_file), "--part_name", PART,
            "--frm_file", "gamebub_soc.frames", "--output_file", "gamebub_soc.bit"])
        if not (output / "gamebub_soc.bit").stat().st_size:
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
