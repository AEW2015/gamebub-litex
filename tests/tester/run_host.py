# SPDX-License-Identifier: 0BSD
"""Supplemental exact-C tester checks in anonymous host memory, not hardware."""
import json
import hashlib
import argparse
import subprocess
from pathlib import Path


# Run ---------------------------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", type=Path, required=True, help="Generated tester bundle.")
    p.add_argument("--output", type=Path, required=True, help="Fresh host-test directory.")
    a = p.parse_args()
    assert not a.output.exists(), "choose a fresh output directory"
    a.output.mkdir(parents=True)
    here   = Path(__file__).resolve().parent
    binary = a.output / "test_firmware"
    commands = [
        ["gcc", "-O2", "-Wall", "-Wextra", "-Werror", "-Wno-error=int-to-pointer-cast",
         "-I" + str(a.bundle / "firmware"), str(here / "test_firmware.c"), "-o", str(binary)],
        [str(binary)],
    ]
    evidence={"status":"FAIL","scope":"host C test, not FPGA evidence","commands":commands,
        "sources":{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in
                   (here.parents[1]/"examples/tester/firmware/main.c", here/"test_firmware.c",
                    a.bundle/"firmware/addresses.h")},
        "warning_review":"The only relaxed warning is uint32 MMIO to 64-bit host pointer; anonymous fixed virtual mappings are used, never /dev/mem or FPGA hardware."}
    for index, command in enumerate(commands):
        result = subprocess.run(command, capture_output=True, text=True)
        logfile = a.output / ("compile.log" if index == 0 else "test.log")
        logfile.write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode:
            raise RuntimeError(f"Host-test command failed; see {logfile}")
    assert "FIRMWARE_HOST_PASS" in (a.output / "test.log").read_text(encoding="utf-8")
    evidence["status"] = "PASS"
    (a.output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print("FIRMWARE_HOST_PASS", a.output)


if __name__ == "__main__":
    main()
