# SPDX-License-Identifier: 0BSD
"""Generate video RTL and compare full frames to the unmodified public raster."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--reference", required=True, type=Path)
    args = p.parse_args()
    out = args.output.resolve()
    if out.exists(): p.error("choose a new output directory")
    out.mkdir(parents=True)
    evidence = dict(result="FAIL", timestamp_utc=datetime.now(timezone.utc).isoformat(), commands=[], profiles=[])

    def run(cmd, cwd, log):
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
        evidence["commands"].append(dict(argv=cmd, cwd=str(cwd), exit_code=result.returncode))
        log.write_text(result.stdout+"\n[stderr]\n"+result.stderr)
        if result.returncode: raise RuntimeError(f"failed command, see {log}")
        return result.stdout

    try:
        reference = args.reference.resolve(strict=True)
        run(["iverilog", "-V"], out, out/"simulator-version.log")
        for profile in (0, 1):
            stage=out/f"profile{profile}"
            stage.mkdir()
            shutil.copy2(reference, stage/"gamebub_axis_raster.v")
            shutil.copy2(HERE/"tb_video.sv", stage/"tb_video.sv")
            run([sys.executable,str(HERE/"generate.py"),"--output",str(stage/"gamebub_video.v"),"--profile",str(profile)],stage,stage/"generate.log")
            run(["iverilog","-g2012",f"-DPROFILE={profile}","-s","tb_video","-o","sim.vvp","gamebub_video.v","gamebub_axis_raster.v","tb_video.sv"],stage,stage/"compile.log")
            stdout=run(["vvp","sim.vvp"],stage,stage/"simulation.log")
            if f"VIDEO_PASS profile={profile}" not in stdout:raise RuntimeError("missing video completion marker")
            evidence["profiles"].append(dict(profile=profile,result="PASS",frames=2,pixels=768000,active_lines=1600,overlay_pixels=400))
        evidence["result"]="PASS"
    except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:
        evidence["error"]=str(exc)
    finally:
        files=list(HERE.glob("*.py"))+[HERE/"tb_video.sv",args.reference]
        files+=list(out.glob("profile*/*.v"))+list(out.glob("profile*/*.ppm"))
        evidence["files"]=[dict(path=str(f.resolve()),sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in files if f.is_file()]
        (out/"evidence.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print(evidence["result"],out,evidence.get("error",""))
    return 0 if evidence["result"]=="PASS" else 1


if __name__=="__main__":raise SystemExit(main())
