# SPDX-License-Identifier: 0BSD
"""Generate combined functional-simulation RTL and actual VexRiscv firmware."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from litex.soc.integration import export

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))
from integration.soc import BaseSoC


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("choose a fresh output directory")
    output.mkdir(parents=True)
    fw, gw = output / "firmware", output / "gateware"
    fw.mkdir(); gw.mkdir()
    soc = BaseSoC()
    soc.finalize()
    mapping = json.loads(export.get_csr_json(soc.csr_regions, soc.constants, soc.mem_regions))
    definitions = ["/* Generated from this target's exported CSR and memory map. */"]
    for name, register in mapping["csr_registers"].items():
        definitions.append(f"#define GB_{name.upper()} 0x{register['addr']:08x}u")
    for name, region in mapping["memories"].items():
        definitions += [f"#define GB_{name.upper()}_BASE 0x{region['base']:08x}u",
                        f"#define GB_{name.upper()}_BYTES 0x{region['size']:x}u"]
    (fw / "addresses.h").write_text("\n".join(definitions) + "\n")
    rom, ram = soc.mem_regions["rom"], soc.mem_regions["sram"]
    (fw / "linker.ld").write_text(f"""OUTPUT_ARCH(riscv)
ENTRY(_start)
MEMORY {{ rom (rx) : ORIGIN = 0x{rom.origin:x}, LENGTH = 0x{rom.size:x}
         ram (rw) : ORIGIN = 0x{ram.origin:x}, LENGTH = 0x{ram.size:x} }}
SECTIONS {{
 .text : {{ KEEP(*(.text.start)) *(.text*) *(.rodata*) }} > rom
 .data : {{ *(.data*) *(.sdata*) }} > ram
 .bss (NOLOAD) : {{ . = ALIGN(4); _bss_start = .; *(.bss*) *(.sbss*) *(COMMON)
                   . = ALIGN(4); _bss_end = .; }} > ram
 _stack_top = ORIGIN(ram) + LENGTH(ram);
 ASSERT(SIZEOF(.data) == 0, "no initialized writable data in startup")
 ASSERT(_bss_end + 2048 <= _stack_top, "stack must fit local BRAM")
}}\n""")
    command = ["riscv64-unknown-elf-gcc", "-march=rv32i", "-mabi=ilp32", "-Os",
               "-Wall", "-Wextra", "-Werror", "-ffreestanding", "-fno-builtin",
               "-msmall-data-limit=0", "-nostdlib", "-nostartfiles", "-I", str(fw),
               "-T", str(fw / "linker.ld"), "-Wl,-Map=" + str(fw / "diagnostic.map"),
               str(ROOT / "soc/firmware/start.S"), str(HERE / "main.c"),
               "-o", str(fw / "diagnostic.elf")]
    result = subprocess.run(command, text=True, capture_output=True)
    (fw / "compile.log").write_text(result.stdout + result.stderr)
    result.check_returncode()
    subprocess.run(["riscv64-unknown-elf-objcopy", "-O", "binary", str(fw / "diagnostic.elf"),
                    str(fw / "diagnostic.bin")], check=True)
    binary = (fw / "diagnostic.bin").read_bytes()
    assert len(binary) <= rom.size
    payload = binary + bytes(rom.size - len(binary))
    words = [int.from_bytes(payload[i:i+4], "little") for i in range(0, len(payload), 4)]
    soc = BaseSoC(rom_init=words)
    soc.finalize()
    final_map = json.loads(export.get_csr_json(soc.csr_regions, soc.constants, soc.mem_regions))
    assert all(final_map[key] == mapping[key] for key in ("csr_bases", "csr_registers", "memories"))
    (output / "csr.json").write_text(json.dumps(final_map, indent=2) + "\n")
    fragment = soc.get_fragment()
    soc.platform.finalize(fragment)
    previous = Path.cwd()
    try:
        os.chdir(gw)
        verilog = soc.platform.get_verilog(fragment, name="gamebub_phase3")
        verilog.write("gamebub_phase3.v")
    finally:
        os.chdir(previous)
    for path, *_ in soc.platform.sources:
        shutil.copy2(path, gw / Path(path).name)
    source_paths = sorted(p for p in (ROOT / "phase3").rglob("*")
                          if p.is_file() and "__pycache__" not in p.parts)
    evidence = {"status": "GENERATED_NOT_YET_SIMULATED", "hardware_programmed": False,
                "scope": "functional simulation; injected sys/service/video clocks; no physical timing signoff",
                "compiler_command": command, "firmware_bytes": len(binary),
                "sources": [{"path": str(p), "sha256": sha(p)} for p in source_paths],
                "generated": [{"path": str(p), "sha256": sha(p)}
                              for p in sorted(output.rglob("*")) if p.is_file()]}
    (output / "generation.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"GENERATED combined target {output}; ROM payload={len(binary)} bytes")


if __name__ == "__main__":
    main()
