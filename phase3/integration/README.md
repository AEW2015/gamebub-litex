<!-- SPDX-License-Identifier: 0BSD -->

# Combined LCD, ESP32, SRAM and SDRAM simulation

The target instantiates the actual VexRiscv minimal CPU, LiteX interconnect,
UART and diagnostic CSRs, Migen LCD scanout, the portable known-good ESP32
QSPI engine with a Migen CDC/overlay wrapper, and both external-memory
controllers. There are no behavioral CPU or internal-BRAM substitutes for
external SRAM/SDRAM. The external devices are independently modeled at their
physical pins.

The simulation provides 50 MHz system, 200 MHz service and approximately
29.361979 MHz video clocks. These are testbench clock inputs: this target is
**not a hardware-ready FPGA top level**, and does not qualify MMCM lock/reset,
ODDR clock forwarding, I/O placement, external constraints or routed timing.
The earlier CPU-only bitstream is not the combined design. No hardware changed.

## CPU memory map

| Region | Base | Size |
| --- | --- | --- |
| Boot ROM | `0x00000000` | 16 KiB |
| Local SRAM/stack/BSS | `0x10000000` | 16 KiB |
| External asynchronous SRAM | `0x30000000` | 512 KiB |
| External SDR SDRAM | `0x40000000` | 32 MiB |
| CPU ESP32 diagnostic window | `0xB0000000` | 4 KiB decoded; first 64 bytes defined |
| LiteX CSRs | generated `csr.json` | generated |

The ESP32's **wire** addresses are separate: official v1.0.2 `0xF100...`
registers and `0xF2000000` overlay. The diagnostic CPU window is read-only,
crosses clock domains by a held request/acknowledge handshake, and returns
zero for undefined locations instead of aliasing defined registers.

## Reproduce

From the repository root in Linux/WSL, after the Phase 1/2 tool bootstraps:

```bash
export PATH=/opt/gamebub-litex-20261021/venv/bin:/opt/gamebub-litex-20261021/toolchain/usr/bin:/opt/gamebub-openxc7-20261021/bin:/opt/gamebub-openxc7-20261021/oss-cad-suite/bin:/usr/bin:/bin

# Only for a fresh environment; refuses to overwrite its private install.
python phase3/memory/bootstrap.py

python phase3/integration/generate.py --output /tmp/gamebub-combined-generated
python phase3/integration/run.py --generated /tmp/gamebub-combined-generated \
  --output /tmp/gamebub-combined-tests
python phase3/video/preview.py /tmp/gamebub-combined-tests/normal/combined.ppm \
  /tmp/gamebub-combined-tests/normal/combined.png
```

Choose fresh output paths. The runner compiles once with Verilator and runs
normal, corrupt-SRAM and corrupt-SDRAM cases. It stages all generated RTL/ROM,
models, protocol host, firmware, commands, tool version, logs and hashes.

## Actual coverage

- CPU writes/reads distributed addresses including each memory's last word,
  address-derived patterns, byte and halfword modifications. Code/stack stay
  in local BRAM. This is not a full sequential test of every memory location.
- CPU waits for real SDRAM initialization and checks real endpoint diagnostics
  through CDC, including ignored writes and nonaliasing undefined reads.
- The serial host uses the official firmware's quad command framing, byte
  swapping, dummy bytes and register addresses. It checks button press/release,
  pending IRQ/W1C, IRQ deassertion, and a real LCD-vblank IRQ.
- Real QSPI writes update 2-bit overlay BRAM. LCD pin capture checks black,
  white, luma threshold, transparency and rotated source coordinates over bars.
- LCD pin monitor requires two complete 480x800 frames and compares every
  sampled active pixel; it saves a full second-frame PPM. Component tests also
  compare every timing edge to the known-good raster in both timing profiles.
- Corrupting the SRAM or SDRAM model's read DQ must make the actual CPU print
  `GB3_FAIL` with `0xbad30001` or `0xbad30002`. Normal completion requires
  `0x600d300f` plus the complete independently decoded UART success sequence.

Final executed evidence: `D:/xup_2026/bub/gamebub-phase3-integration3/` using
`D:/xup_2026/bub/gamebub-phase3-combined3/`. Normal run: 1,745,036 system
cycles, two complete frames, 801,438 checked pixels, 68 read halfwords from
each external memory, 4,445 refreshes. Both CPU failure controls pass.

Verilator warnings remain in the compile log (primarily generated Migen
combinational nonblocking assignments and width sizing). No warning-free,
synthesis, physical timing or hardware qualification is claimed. The ESP32
model is a source-derived protocol host, not QEMU or execution of its binary.

The unchanged protocol endpoint is a supported subset, not the complete
official framework/core-command ABI. ESP32 panel initialization/backlight and
actual power/menu lifecycle are not physically tested by this simulation.
