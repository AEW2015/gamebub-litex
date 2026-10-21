<!-- SPDX-License-Identifier: 0BSD -->

# Experimental physical LiteX interface demo

This target adapts the frozen Phase3 combined simulation to the actual Rev4
XC7A100T-CSG324 board. Generation, synthesis, placement, routing and bitstream
assembly use open-source tools. Vivado is used only for hardware discovery and
volatile configuration, as authorized by the user.

## Implemented

- VexRiscv RV32I at 50 MHz; 16 KiB ROM and 16 KiB internal RAM. Firmware,
  stack and test state remain internal while testing external memory.
- One MMCM: 50 MHz system, 200 MHz ESP32 service, and 29.357798 MHz video.
  The actual fractional pixel rate is recorded in `generation.json`; it is
  not the slightly different nominal rate used by older Vivado designs.
- Native 480x800 color bars, 605x809 total timing, about 59.982 Hz, with
  ODDR-forwarded LCD clock. ESP32 overlay pixels have priority.
- ESP32 QSPI slave, button/vblank IRQ handling, and 360x240 2-bit alpha/luma
  overlay BRAM. This is the documented v1.0.2-compatible **subset**, not
  complete core/framework, cartridge or SD-card support.
- 512 KiB asynchronous SRAM and 32 MiB SDR SDRAM at conservative 50 MHz.
  Startup performs distributed-address, pattern and byte/halfword smoke tests;
  this is not an exhaustive memory or high-speed timing sweep.
- Two native-panel 10x10 status squares near the lower-right corner: SRAM
  and SDRAM respectively, red before success and green after success.
- Standard LiteX USER1 JTAG UART. The seven bytes `GB4_OK\n` are emitted
  after memory, local ESP32 diagnostic identity and frame-counter checks,
  then repeated nonblocking every 60 frames for late monitor attachment.
  No JTAG host is needed for boot or normal operation.

## Reproduce

Use fresh output directories. These commands run inside the already-installed
`MRS-HDL-Research` WSL environment:

```sh
export PATH=/opt/gamebub-litex-20261021/venv/bin:/opt/gamebub-litex-20261021/toolchain/usr/bin:/opt/gamebub-openxc7-20261021/bin:/opt/gamebub-openxc7-20261021/oss-cad-suite/bin:/usr/bin:/bin
python /mnt/d/codex_archive_2026/gamebub-litex/phase4/generate.py --output /mnt/d/xup_2026/bub/gamebub-phase4-physical5
python /mnt/d/codex_archive_2026/gamebub-litex/phase4/sim_physical.py --bundle /mnt/d/xup_2026/bub/gamebub-phase4-physical5 --output /mnt/d/xup_2026/bub/gamebub-phase4-physical-sim5
python /mnt/d/codex_archive_2026/gamebub-litex/phase4/build.py --tools /opt/gamebub-openxc7-20261021 --gateware-dir /mnt/d/xup_2026/bub/gamebub-phase4-physical5/gateware --xdc /mnt/d/xup_2026/bub/gamebub-phase4-physical5/physical.xdc --output /mnt/d/xup_2026/bub/gamebub-phase4-build6
```

The generator freezes the exact ROM, physical RTL, pin mapping and input
hashes. The simulator uses these exact files, real CPU firmware, independent
memory pin models, QSPI host traffic, and verification-only primitive models.
Injected SRAM and SDRAM read corruption must produce the corresponding CPU
failure result. Simulation models never enter the physical build.

`build.py` reuses the immutable Phase2 pinned adapter and retains its strict
diagnostic/timing gates. The additional narrow diagnostic policy verifies
that all 36 bidirectional data bits become top-level IOBUFs and that the
fractional MMCM divider survives synthesis. Unknown warnings are not ignored.
Phase4's separate endpoint registers command decode and transaction predicates
to remove a real service-clock critical path; Phase3 remains unchanged.
The Phase4 service wrapper separately pipelines overlay luma conversion before
BRAM writes, with matched address, alpha and valid stages. This preserves
one-write-per-service-cycle throughput and the original video read latency.

## Programming and acceptance

Only after inspecting final build and simulation evidence, calculate the final
BIT's SHA-256, then run from PowerShell:

```powershell
C:/Xilinx/2025.2/Vivado/bin/vivado.bat -mode batch -notrace -nojournal -source D:/codex_archive_2026/gamebub-litex/phase4/hardware.tcl -tclargs program <BIT> <SHA256>
```

The public script requires your explicit `GAMEBUB_JTAG_SERIAL` environment
variable and exactly one `xc7a100t`. See [public build instructions](../docs/BUILD.md).
It programs configuration SRAM only and checks DONE=1 / CRC=0. It does not
modify ESP32 firmware, persistent flash, USB drivers or the other connected
FPGA. After the target closes, the [JTAG UART helper](loader/README.md) can
check the firmware's queued smoke result. Separately observe color bars and
tap Volume-minus to check real ESP32 overlay behavior. A configuration success
alone does not prove the CPU, memories, panel or ESP32 are working.

## Qualification boundary

The user explicitly authorized an experimental volatile load with the pinned
open-source timing engine's limitations. Available internal clock checks must
still pass. No `--timing-allow-fail`, false-path blanket or clock-rate reduction
is used to hide failures. See [constraints review](constraints_review.md).

This toolchain uses a DEFAULT timing model, not independently qualified -1/PVT
corners, and cannot sign off external setup/hold, board trace margins or CDC
datapath bounds. Functional simulation and a successful board smoke test do
not remove those gaps. Do not describe this image as fully timing-qualified.

## Licensing and history

New independent Python/C/Tcl is 0BSD. Board-derived bindings and the modified
GameBub endpoint retain CERN-OHL-S-2.0; see `../LICENSES/` and the original
[endpoint provenance](../phase3/esp32/PROVENANCE.md). Third-party CPU, LiteX,
Migen and LiteDRAM notices remain applicable.

Earlier Phase1/2/3 handoffs are immutable. Failed physical candidates are
retained as failure evidence, not advertised as releasable bitstreams.
