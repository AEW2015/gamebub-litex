# SPDX-License-Identifier: 0BSD
"""Execute frozen physical RTL with actual firmware, clock and pin models."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    out=a.output.resolve()
    if out.exists():p.error("choose a new output directory")
    out.mkdir(parents=True)
    stage=out/"inputs";stage.mkdir()
    evidence=dict(result="FAIL",timestamp_utc=datetime.now(timezone.utc).isoformat(),commands=[],cases=[],sources=[],limitation="Actual physical generated RTL with verification-only primitive and external-memory pin models; not board/electrical validation")
    def run(cmd,cwd,log):
        with log.open("w") as stream:
            r=subprocess.run(cmd,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,text=True,timeout=900)
        evidence["commands"].append(dict(argv=cmd,cwd=str(cwd),exit_code=r.returncode))
        if r.returncode:raise RuntimeError(f"failed command, see {log}")
        return log.read_text()
    try:
        bundle=a.bundle.resolve(strict=True)
        gw=list((bundle/"gateware").glob("*"))
        extra=[ROOT/"phase4/sim_clocking_primitives.sv",HERE/"tb_apps.sv",ROOT/"phase3/memory/pin_models.sv",ROOT/"phase3/esp32/qspi_host_bfm.sv",bundle/"simulation_bindings.vh"]
        files=[f for f in gw if f.suffix in (".v",".sv",".init")]+extra
        for f in files:shutil.copy2(f,stage/f.name)
        files+=[Path(__file__).resolve(),bundle/"firmware/diagnostic.elf",bundle/"firmware/diagnostic.bin"]
        evidence["sources"]=[dict(path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in files]
        run(["verilator","--version"],stage,out/"verilator-version.log")
        rtl=sorted(str(f) for f in stage.glob("*") if f.suffix in (".v",".sv"))
        image=out/"obj_dir/physical_sim"
        run(["verilator","--binary","--timing","-Wno-fatal","--top-module","tb_apps","--Mdir",str(image.parent),"-o",image.name,"-I"+str(stage),*rtl],stage,out/"compile.log")
        def simulate(case):
            cwd=out/case;cwd.mkdir()
            for f in stage.glob("*.init"):shutil.copy2(f,cwd/f.name)
            cmd=[str(image)]+([] if case=="normal" else ["+"+case])
            text=run(cmd,cwd,cwd/"simulation.log")
            marker="APPS_PASS" if case=="normal" else "APPS_NEGATIVE_PASS"
            if marker not in text:raise RuntimeError(f"completion marker missing in {case}")
            return dict(name=case,result="PASS",marker=marker)
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(simulate,case) for case in ("normal","corrupt_sram","corrupt_sdram")]
            for future in as_completed(futures):
                evidence["cases"].append(future.result())
                (out/"evidence.json").write_text(json.dumps(evidence,indent=2)+"\n")
        evidence["result"]="PASS"
    except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:evidence["error"]=str(exc)
    finally:
        evidence["captures"]=[dict(path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in out.glob("*/*.ppm")]
        (out/"evidence.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print(evidence["result"],out,evidence.get("error",""))
    return 0 if evidence["result"]=="PASS" else 1


if __name__=="__main__":raise SystemExit(main())
