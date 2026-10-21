# SPDX-License-Identifier: 0BSD
"""Supplemental exact-C tester checks in anonymous host memory, not hardware."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    assert not a.output.exists(), "choose a fresh output directory"
    a.output.mkdir(parents=True)
    here=Path(__file__).resolve().parent
    binary=a.output/"test_firmware"
    commands=[["gcc","-O2","-Wall","-Wextra","-Werror","-Wno-error=int-to-pointer-cast",
               "-I"+str(a.bundle/"firmware"),str(here/"test_firmware.c"),"-o",str(binary)], [str(binary)]]
    evidence={"status":"FAIL","scope":"host C test, not FPGA evidence","commands":commands,
        "sources":{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in
                   (here/"firmware/main.c",here/"test_firmware.c",a.bundle/"firmware/addresses.h")},
        "warning_review":"The only relaxed warning is uint32 MMIO to 64-bit host pointer; anonymous fixed virtual mappings are used, never /dev/mem or FPGA hardware."}
    for i,cmd in enumerate(commands):
        r=subprocess.run(cmd,capture_output=True,text=True)
        (a.output/("compile.log" if i==0 else "test.log")).write_text(r.stdout+r.stderr)
        assert r.returncode==0
    assert "FIRMWARE_HOST_PASS" in (a.output/"test.log").read_text()
    evidence["status"]="PASS"
    (a.output/"evidence.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print("FIRMWARE_HOST_PASS",a.output)


if __name__=="__main__": main()
