<!-- SPDX-License-Identifier: 0BSD -->

# Third-party components and notices

This inventory describes the private Phase 2 environment recorded in
[`toolchain-lock.json`](toolchain-lock.json) and the installed package metadata
under `/opt/gamebub-litex-20261021`. The lockfile is the version and archive-hash
record; the installed `.dist-info` metadata and package license files are the
license evidence. License metadata can be incomplete or package-wide even when
a source bundle contains files under several licenses. Preserve the upstream
license files and notices with the package and any generated bundle that
contains its material.

## Project-authored material and GameBub pin data

- Files in this repository that identify themselves as
  `SPDX-License-Identifier: 0BSD` are project-authored material offered under 0BSD. This does not
  relicense third-party code or the board-derived pin map.
- [`litex_boards/platforms/gamebub.py`](litex_boards/platforms/gamebub.py) and
  its generated pin-constraint subset identify as
  `SPDX-License-Identifier: CERN-OHL-S-2.0`. The platform pin assignments are
  derived from the upstream GameBub Rev4 XDC. Keep this attribution/license
  boundary; do not change these files to 0BSD merely because surrounding bring-up
  software is 0BSD.
- Generated SoC bundles can contain both project-authored files and upstream
  LiteX/VexRiscv material, as well as constraints derived from the GameBub pin
  map. Retain source notices and applicable license texts alongside bundled
  generated output. Do not apply one blanket license to the whole generated
  bundle. The precise contents depend on the selected build outputs.

## Direct LiteX and CPU packages

The versions below are pinned in `toolchain-lock.json`. License descriptions
are from the installed package metadata/license files, not a claim that every
transitive or bundled source file has only that license.

| Package | Pinned version / source | Installed license evidence | Role and current use |
| --- | --- | --- | --- |
| LiteX | `litex` 2024.12; wheel SHA-256 in lockfile | Metadata says BSD; included license text describes BSD 2-Clause | SoC framework; used to generate the BRAM-only SoC |
| Migen | `migen` 0.10.0; wheel SHA-256 in lockfile | `BSD-2-Clause` | Gateware construction dependency; used by LiteX and the target |
| VexRiscv CPU package | `pythondata-cpu-vexriscv` 1.0.1.post407; embedded source pin `5f0c7a7faf6b65c907a93be6e3723e297d37ee71`; selected `VexRiscv_Min.v` SHA-256 in lockfile | Package metadata classifies its included `LICENSE` as MIT | The generated design uses the pre-generated minimal VexRiscv Verilog. It is not rebuilt from SpinalHDL/Java in this flow. Preserve the package license with generated RTL bundles. |
| Picolibc data package | `pythondata-software-picolibc` 1.7.9.post181; embedded source pin `f165dc22f1f67e3e8bdc8edf750ff7dc596de2ff` | Package metadata has a BSD license classifier; the installed source bundle includes `COPYING.picolibc`, `COPYING.NEWLIB`, `COPYING.GPL2` and other notices | Installed for toolchain compatibility, but current firmware uses `-nostdlib -nostartfiles`; Picolibc is not linked into the current firmware. Do not claim it is present in the ROM. |
| Compiler-rt data package | `pythondata-software-compiler-rt` 0.0.post6206; embedded source pin `81fb4f00c2cfe13814765968e09931ffa93b5138` | Metadata reports `License: UNKNOWN`, an Apache Software License classifier, and includes an Apache 2.0 `LICENSE`; its `data/` tree has its own license files | Installed, but not referenced by the current firmware link command and not claimed as linked into the ROM. Keep the full package notices if distributing the package or its source. |

The current diagnostic firmware is project-authored and marked 0BSD in
`firmware/main.c` and `firmware/start.S`. The generator invokes the pinned GCC
with `-nostdlib -nostartfiles`, so the current ROM is not claimed to contain
Picolibc, compiler-rt, or `libgcc`. This statement is about the present command
and output; recheck the link map and ELF whenever the command or firmware changes.

## Compiler and assembler packages

| Package | Pinned version | Installed license evidence | Role |
| --- | --- | --- | --- |
| `gcc-riscv64-unknown-elf` | `10.2.0-0ubuntu1` | Private Debian copyright file identifies GCC as GPL-3-or-later and identifies `libgcc` under GPL-3-or-later with GCC Runtime Library Exception 3.1 | Compiles and links the firmware. The current no-standard-library link does not claim `libgcc` is linked. |
| `binutils-riscv64-unknown-elf` | `2.35.1-0ubuntu1` | Private Debian copyright file identifies GNU Binutils as GPL-3-or-later | Supplies assembler/linker tools used by the RISC-V compiler driver. |

The `.deb` archives and SHA-256 hashes are listed in `toolchain-lock.json`.
Their installed copyright notices are under the private toolchain's
`usr/share/doc/gcc-riscv64-unknown-elf/` and
`usr/share/doc/binutils-riscv64-unknown-elf/` directories. Do not copy these
executables into a generated FPGA image; this note inventories the build
environment.

## Other pinned Python packages

These are the remaining packages in `python_pins` in `toolchain-lock.json`.
License labels below summarize their installed `.dist-info/METADATA`; keep the
package license files where present. They are build/bootstrap dependencies, not
claims about firmware contents.

| Package | Version | Installed metadata license label |
| --- | --- | --- |
| pip | 24.3.1 | MIT |
| setuptools | 75.6.0 | MIT |
| wheel | 0.45.1 | MIT |
| Meson | 1.6.1 | Apache-2.0 |
| Ninja | 1.11.1.3 | Apache and BSD classifiers; retain package `LICENSE` |
| pyserial | 3.5 | BSD |
| packaging | 24.2 | Apache and BSD classifiers |
| requests | 2.32.3 | Apache-2.0 |
| colorama | 0.4.6 | BSD |
| charset-normalizer | 3.4.0 | MIT |
| idna | 3.10 | BSD classifier |
| urllib3 | 2.2.3 | MIT |
| certifi | 2024.12.14 | MPL-2.0 |

The lockfile also pins Python 3.10.12 and identifies the Ubuntu 22.04 x86_64
build environment; that operating-system/toolchain base has its own package
notices and is not relicensed by this repository.

## Updating this inventory

When changing `toolchain-lock.json`, refreshing the private environment, changing
the VexRiscv variant, adding a library, or changing the firmware link flags:

1. Re-read installed package `METADATA`, bundled license files and the package
   copyright records for the exact pinned versions.
2. Check the generated RTL/software bundle and linker map to identify which
   source or runtime material is actually included. Installation alone does not
   mean a library is linked into firmware.
3. Preserve upstream attribution and license files in redistributed bundles;
   keep 0BSD project material distinct from CERN-OHL-S-2.0 board-derived pin
   mapping and all third-party components.
