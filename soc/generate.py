# SPDX-License-Identifier: 0BSD
"""Generate a frozen CPU/ROM/RTL/XDC bundle; no hardware or vendor tools."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from litex.soc.integration import export
from litex_boards.targets.gamebub import BaseSoC
from litex_boards.platforms.gamebub import SAFE_IO

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--console-pmod", action="store_true",
                        help="explicitly assign PMOD0 TX/PMOD1 RX; not ESP32 USB")
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        parser.error("output must be a fresh directory")
    if not args.console_pmod:
        parser.error("this diagnostic requires --console-pmod (no hardware is programmed)")
    out.mkdir(parents=True)
    fw = out / "firmware"
    gw = out / "gateware"
    fw.mkdir(); gw.mkdir()

    # First elaboration allocates the address map. Software consumes only
    # exported addresses, never assumptions from another GameBub SoC.
    soc = BaseSoC(console_pmod=True)
    soc.finalize()
    csr_json = export.get_csr_json(soc.csr_regions, soc.constants, soc.mem_regions)
    (out / "csr.json").write_text(csr_json)
    mapping = json.loads(csr_json)
    definitions = ["/* Generated from csr.json; do not edit. */"]
    for name, reg in mapping["csr_registers"].items():
        definitions.append(f"#define GB_{name.upper()} 0x{reg['addr']:08x}u")
    (fw / "addresses.h").write_text("\n".join(definitions) + "\n")
    regions = soc.mem_regions
    rom, ram = regions["rom"], regions["sram"]
    linker = f"""/* Generated from this SoC's memory regions. */
OUTPUT_ARCH(riscv)
ENTRY(_start)
MEMORY {{ rom (rx) : ORIGIN = 0x{rom.origin:x}, LENGTH = 0x{rom.size:x}
         ram (rw) : ORIGIN = 0x{ram.origin:x}, LENGTH = 0x{ram.size:x} }}
SECTIONS {{
 .text : {{ KEEP(*(.text.start)) *(.text*) *(.rodata*) }} > rom
 .data : {{ *(.data*) *(.sdata*) }} > ram
 .bss (NOLOAD) : {{ . = ALIGN(4); _bss_start = .;
                  *(.bss*) *(.sbss*) *(COMMON) . = ALIGN(4); _bss_end = .; }} > ram
 _stack_top = ORIGIN(ram) + LENGTH(ram);
 ASSERT(SIZEOF(.data) == 0, "startup deliberately supports no initialized writable data")
 ASSERT(_bss_end + 2048 <= _stack_top, "reserve at least 2KiB stack")
}}\n"""
    (fw / "linker.ld").write_text(linker)
    cc = shutil.which("riscv64-unknown-elf-gcc")
    objcopy = shutil.which("riscv64-unknown-elf-objcopy")
    if not cc or not objcopy:
        raise RuntimeError("private RISC-V compiler tools missing from PATH")
    elf, binary = fw / "diagnostic.elf", fw / "diagnostic.bin"
    command = [cc, "-march=rv32i", "-mabi=ilp32", "-Os", "-Wall", "-Wextra",
               "-Werror", "-ffreestanding", "-fno-builtin", "-fno-pic",
               "-msmall-data-limit=0", "-nostdlib", "-nostartfiles",
               "-I", str(fw), "-T", str(fw / "linker.ld"),
               "-Wl,-Map=" + str(fw / "diagnostic.map"),
               str(HERE / "firmware/start.S"), str(HERE / "firmware/main.c"),
               "-o", str(elf)]
    result = subprocess.run(command, capture_output=True, text=True)
    (fw / "compile.log").write_text(result.stdout + result.stderr)
    result.check_returncode()
    subprocess.run([objcopy, "-O", "binary", str(elf), str(binary)], check=True)
    payload = binary.read_bytes()
    if len(payload) > rom.size:
        raise RuntimeError("firmware exceeds ROM")
    # Explicitly initialize the entire BRAM, for identical simulation and
    # synthesis behavior outside the linked firmware and no short-read files.
    padded = payload + bytes(rom.size - len(payload))
    words = [int.from_bytes(padded[i:i+4], "little") for i in range(0, len(padded), 4)]

    # Second elaboration embeds exactly the compiled ROM. Validate the map
    # stayed identical, then freeze every dependency beside the generated top.
    soc = BaseSoC(rom_init=words, console_pmod=True)
    soc.finalize()
    second_map = export.get_csr_json(soc.csr_regions, soc.constants, soc.mem_regions)
    (out / "embedded_csr.json").write_text(second_map)
    embedded = json.loads(second_map)
    if any(embedded[key] != mapping[key]
           for key in ("csr_bases", "csr_registers", "memories")):
        raise RuntimeError("CSR/memory map changed when embedding ROM")
    (out / "csr.json").write_text(second_map)
    fragment = soc.get_fragment()
    soc.platform.finalize(fragment)
    previous = Path.cwd()
    try:
        os.chdir(gw)
        verilog = soc.platform.get_verilog(fragment, name="gamebub_soc")
        verilog.write("gamebub_soc.v")
    finally:
        os.chdir(previous)
    for source, *_ in soc.platform.sources:
        shutil.copy2(source, gw / Path(source).name)
    sc, _ = soc.platform.resolve_signals(verilog.ns)
    xdc = ["# SPDX-License-Identifier: CERN-OHL-S-2.0",
           "# Rev4 pins from GameBub; generated subset, no external timing signoff."]
    for name, pins, others, _ in sc:
        for i, pin in enumerate(pins):
            port = name if len(pins) == 1 else f"{name}[{i}]"
            xdc += [f"set_property PACKAGE_PIN {pin} [get_ports {{{port}}}]",
                    f"set_property IOSTANDARD LVCMOS33 [get_ports {{{port}}}]"]
    xdc.append("create_clock -period 20.000 [get_ports {clk50}]")
    (out / "gamebub_soc.xdc").write_text("\n".join(xdc) + "\n")
    # Exact signal names are generated, not guessed by a behavioral CPU model.
    result_name = verilog.ns.get_name(soc.diagnostic.result.storage)
    reset_name = verilog.ns.get_name(soc.crg.cd_sys.rst)
    checks = []
    for name, pins, value in SAFE_IO:
        checks.append(f'if (dut.{name} !== {len(pins.split())}\'d{value}) $fatal(1, "unsafe {name}");')
    bindings = ["`define SOC_TOP gamebub_soc",
                f"`define SOC_STATUS dut.{result_name}",
                f"`define SOC_RESET dut.{reset_name}",
                "`define SOC_CHECK_SAFE " + (" " + chr(92) + "\n    ").join(checks)]
    (out / "soc_bindings.vh").write_text("\n".join(bindings) + "\n")
    sources = [p for p in HERE.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    outputs = [p for p in out.rglob("*") if p.is_file()]
    evidence = {"phase": 2, "result": "GENERATED_NOT_YET_SIMULATED_OR_ROUTED",
                "hardware_unchanged": True, "clock_hz": 50000000,
                "cpu": "VexRiscv minimal RV32I", "firmware_bytes": len(payload),
                "rom_bytes": rom.size, "sram_bytes": ram.size,
                "compiler_command": command,
                "inputs": [{"path": str(p), "sha256": sha(p)} for p in sources],
                "outputs": [{"path": str(p), "sha256": sha(p)} for p in outputs]}
    (out / "generation.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"GENERATED {out}; firmware {len(payload)} bytes; no hardware access")


if __name__ == "__main__":
    main()
