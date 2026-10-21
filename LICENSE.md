<!-- SPDX-License-Identifier: 0BSD -->

# Licensing and provenance

There is no single blanket license for this source tree. File notices and
upstream provenance take precedence.

| Material | Applicable terms |
| --- | --- |
| Independent new wrappers, tools, tests and documentation explicitly marked `0BSD` | [0BSD](LICENSES/0BSD.txt) |
| GameBub pin maps, XDC references, board bindings, derived ESP32 FPGA endpoint RTL, and the derived Phase5 C tester font/layout | [CERN-OHL-S-2.0](LICENSES/CERN-OHL-S-2.0.txt) |
| Official ESP32 driver reference `phase3/esp32/reference/fpga_driver_v1.0.2.rs` | [GPL-3.0-only](LICENSES/GPL-3.0-only.txt) |
| Files marked `BSD-2-Clause`, including the memory wrappers/models | [BSD-2-Clause](LICENSES/BSD-2-Clause.txt); preserve any source notices |

Unmarked copied reference RTL in `phase3/memory/reference/` and
`phase3/video/reference/` is GameBub-derived FPGA material under
CERN-OHL-S-2.0, not 0BSD. Its source path and hash are recorded alongside it.
The ESP32 RTL copies in `phase3`, `phase4` and `phase5` share the provenance
described in [phase3/esp32/PROVENANCE.md](phase3/esp32/PROVENANCE.md).
Later copies contain the timing adaptations described by their phase READMEs.

Upstream GameBub: <https://github.com/elipsitz/gamebub>.
Related derived IP: <https://github.com/AEW2015/gamebub-vivado>.

LiteX, Migen, LiteDRAM, VexRiscv, the RISC-V toolchain, openXC7 and
OSS-CAD-Suite are installed separately under their own licenses. This source
repository does not relicense or redistribute those tool installations.
See [soc/THIRD_PARTY.md](soc/THIRD_PARTY.md), the dependency lockfiles, and
the upstream notices when distributing generated RTL or binaries.

The architecture illustration and its generator are independently authored
0BSD artwork. The external reference image used during design is not included.

No trademark rights or hardware warranty are granted. This is an independent
experimental project, not GameBub, AMD or LiteX certification.
