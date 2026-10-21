# SPDX-License-Identifier: 0BSD
"""Check physical CRG elaboration with verification-only primitive models."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    out=a.output.resolve()
    if out.exists():p.error("choose a new output directory")
    result=subprocess.run([sys.executable,str(HERE/"sim_clocking_generate.py"),"--output",str(out)],capture_output=True,text=True,timeout=60)
    if result.returncode:print(result.stderr);return 1
    (out/"generate.log").write_text(result.stdout+result.stderr)
    evidence=dict(result="FAIL",timestamp_utc=datetime.now(timezone.utc).isoformat(),commands=[],limitation="MMCM analog lock/jitter and physical routing are not modeled; primitive models are verification only")
    def run(command,name):
        r=subprocess.run(command,cwd=out,capture_output=True,text=True,timeout=60)
        (out/name).write_text(r.stdout+"\n[stderr]\n"+r.stderr)
        evidence["commands"].append(dict(argv=command,exit_code=r.returncode))
        if r.returncode:raise RuntimeError(f"failed command; see {out/name}")
        return r.stdout
    try:
        run(["iverilog","-V"],"simulator-version.log")
        run(["iverilog","-g2012","-s","tb_clocking","-o","sim.vvp",str(out/"clocking_dut.v"),str(HERE/"sim_clocking_primitives.sv"),str(HERE/"sim_clocking_tb.sv")],"compile.log")
        log=run(["vvp","sim.vvp"],"simulation.log")
        if "CLOCKING_PASS" not in log:raise RuntimeError("completion marker missing")
        evidence["result"]="PASS"
    except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:evidence["error"]=str(exc)
    evidence["frequencies"]=json.loads((out/"frequencies.json").read_text())
    files=[HERE/"clocking.py",*HERE.glob("sim_clocking*"),out/"clocking_dut.v"]
    evidence["sources"]=[dict(path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in files if f.is_file()]
    (out/"evidence.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print(evidence["result"],out,evidence.get("error",""))
    return 0 if evidence["result"]=="PASS" else 1


if __name__=="__main__":raise SystemExit(main())
