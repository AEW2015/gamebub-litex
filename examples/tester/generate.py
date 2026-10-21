# SPDX-License-Identifier: 0BSD
"""Generate a frozen physical GameBub LiteX candidate, without vendor tools."""
import os
import sys
import json
import shutil
import hashlib
import argparse
import subprocess
from pathlib import Path

from litex.soc.integration import export

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from soc import BaseSoC
from gamebub.clocking import PhysicalCRG


# Helpers -----------------------------------------------------------------------------------------

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Run ---------------------------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    out = a.output.resolve()
    if out.exists():
        p.error("choose a fresh output path")
    out.mkdir(parents=True)
    fw, gw = out / "firmware", out / "gateware"
    fw.mkdir(); gw.mkdir()
    soc = BaseSoC()
    soc.finalize()
    mapping = json.loads(export.get_csr_json(soc.csr_regions, soc.constants, soc.mem_regions))
    header = ["/* Generated physical target addresses; do not edit. */"]
    for name, reg in mapping["csr_registers"].items():
        header.append(f"#define GB_{name.upper()} 0x{reg['addr']:08x}u")
    for name, reg in mapping["memories"].items():
        header += [f"#define GB_{name.upper()}_BASE 0x{reg['base']:08x}u",
                   f"#define GB_{name.upper()}_BYTES 0x{reg['size']:x}u"]
    (fw / "addresses.h").write_text("\n".join(header) + "\n")
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
 ASSERT(SIZEOF(.data) == 0, "no initialized writable data")
 ASSERT(_bss_end + 2048 <= _stack_top, "stack must fit internal BRAM")
}}\n""")
    command = ["riscv64-unknown-elf-gcc", "-march=rv32i", "-mabi=ilp32", "-Os", "-Wall", "-Wextra", "-Werror",
               "-ffreestanding", "-fno-builtin", "-msmall-data-limit=0", "-nostdlib", "-nostartfiles",
               "-I", str(fw), "-T", str(fw / "linker.ld"), "-Wl,-Map=" + str(fw / "diagnostic.map"),
               str(HERE / "firmware/start.S"), str(HERE / "firmware/main.c"), "-o", str(fw / "diagnostic.elf")]
    r = subprocess.run(command, text=True, capture_output=True)
    (fw / "compile.log").write_text(r.stdout + r.stderr)
    r.check_returncode()
    subprocess.run(["riscv64-unknown-elf-objcopy", "-O", "binary", str(fw / "diagnostic.elf"), str(fw / "diagnostic.bin")], check=True)
    binary = (fw / "diagnostic.bin").read_bytes()
    assert len(binary) <= rom.size
    payload = binary + bytes(rom.size - len(binary))
    words = [int.from_bytes(payload[i:i+4], "little") for i in range(0, len(payload), 4)]
    soc = BaseSoC(rom_init=words)
    soc.finalize()
    final_map = json.loads(export.get_csr_json(soc.csr_regions, soc.constants, soc.mem_regions))
    assert all(final_map[key] == mapping[key] for key in ("csr_bases", "csr_registers", "memories"))
    (out / "csr.json").write_text(json.dumps(final_map, indent=2) + "\n")
    fragment = soc.get_fragment()
    soc.platform.finalize(fragment)
    old_cwd = Path.cwd()
    try:
        os.chdir(gw)
        rtl = soc.platform.get_verilog(fragment, name="gamebub_soc")
        rtl.write("gamebub_soc.v")
    finally:
        os.chdir(old_cwd)
    for source, *_ in soc.platform.sources:
        # The pinned existing adapter stages .v files. This rename changes no
        # bytes or semantics; preserve the original name/hash in source binding.
        dest = gw / (Path(source).stem + ".v")
        shutil.copy2(source, dest)
    sc, _ = soc.platform.resolve_signals(rtl.ns)
    xdc = ["# SPDX-License-Identifier: CERN-OHL-S-2.0",
           "# Exact Rev4 pin subset. External I/O/CDC timing NOT signed off."]
    physical = []
    for name, pins, properties, _ in sc:
        for index, pin in enumerate(pins):
            port = name if len(pins) == 1 else f"{name}[{index}]"
            xdc += [f"set_property PACKAGE_PIN {pin} [get_ports {{{port}}}]",
                    f"set_property IOSTANDARD LVCMOS33 [get_ports {{{port}}}]"]
            if name == "buttons_n":
                xdc.append(f"set_property PULLTYPE PULLUP [get_ports {{{port}}}]")
            physical.append({"port": port, "package_pin": pin, "standard": "LVCMOS33"})
    assert len({item["package_pin"] for item in physical}) == len(physical)
    xdc.append("create_clock -period 20.000 [get_ports {clk50}]")
    # Yosys removes the clock-domain aliases despite their keep attributes.
    # These are the surviving canonical nets of this fixed physical target.
    # build.py verifies their presence in mapped JSON before starting P&R.
    for name, hz in (("basesoc_crg_clkin", 50e6), ("VexRiscv.clk", 50e6),
                     ("basesoc_crg_clkout_buf2", 200e6),
                     ("basesoc_crg_clkout_buf0", PhysicalCRG.frequencies()["video_hz"]),
                     ("basesoc_basesoc_jtag_tck", 10e6)):
        xdc.append(f"create_clock -period {1e9/hz:.9f} [get_nets {{{name}}}]")
    (out / "physical.xdc").write_text("\n".join(xdc) + "\n")
    (out / "pins.json").write_text(json.dumps(physical, indent=2) + "\n")
    (out / "simulation_bindings.vh").write_text(
        f"`define RESULT dut.{rtl.ns.get_name(soc.diagnostic.result.storage)}\n"
        f"`define PASSES dut.{rtl.ns.get_name(soc.diagnostic.memory_pass.storage)}\n"
        f"`define PAGE dut.{rtl.ns.get_name(soc.outputs.page.storage)}\n"
        f"`define STATE dut.{rtl.ns.get_name(soc.outputs.state.storage)}\n"
        f"`define PROGRESS dut.{rtl.ns.get_name(soc.outputs.progress.storage)}\n"
        f"`define QSPI_OE dut.{rtl.ns.get_name(soc.qspi_oe)}\n")
    evidence = {"scope": "experimental physical candidate; no timing waiver inferred", "hardware_programmed": False,
        "firmware_bytes": len(binary), "compiler_command": command, "clocking": PhysicalCRG.frequencies(),
        "physical_pin_count": len(physical), "part": soc.platform.device,
        "inputs": [{"path": str(path), "sha256": sha(path)} for base in (HERE, ROOT / "gamebub")
                   for path in sorted(base.rglob("*")) if path.is_file() and "__pycache__" not in path.parts],
        "generated": [{"path": str(path), "sha256": sha(path)} for path in sorted(out.rglob("*")) if path.is_file()]}
    (out / "generation.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"PHYSICAL_GENERATED {out} firmware={len(binary)} pins={len(physical)}")


if __name__ == "__main__": main()
