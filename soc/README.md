<!-- SPDX-License-Identifier: 0BSD -->

# Phase 2: BRAM-only LiteX CPU

This experimental `litex-boards`-style target uses VexRiscv minimal (RV32I,
no caches), a 50 MHz system clock, 16 KiB ROM, 16 KiB SRAM, LiteX UART and a
countdown timer. It runs a small standalone diagnostic, **not the stock LiteX
BIOS**. No Vivado, Vitis, proprietary IP or vendor simulation library is used.

The board interfaces are not all implemented. See
[INTERFACE_SUPPORT.md](../INTERFACE_SUPPORT.md) and
[STATUS_PHASE2.md](../STATUS_PHASE2.md). The earlier Phase 1 probe and its
hash-bound handoff remain unchanged. This directory is a local namespace, not
an installed or upstream-accepted `litex-boards` platform.

## Safety and console

Hardware deployment is deferred by the user's request. These commands never
scan JTAG, program the board, attach USB devices, or modify ESP32 firmware.
The LCD stays inactive and this image does **not** service ESP32 QSPI/menus.

`--console-pmod` explicitly assigns UART TX to PMOD0/V14 and RX to PMOD1/U14,
115200 baud, 8N1, LVCMOS33. This is not the ESP32 USB console. Before any future
hardware test, verify the board revision, electrical levels and pinout, remove
incompatible PMOD accessories, and separately authorize programming. All
enumerated memory enables, cartridge/link directions, motor/audio outputs and
LCD outputs remain at their reviewed inactive values.

## Build and simulate in Linux / WSL

Run from `gamebub-litex`. The tested environment is Ubuntu 22.04 x86-64 in WSL.
The Phase 1 tool bootstrap is `tools/bootstrap_linux.sh`; the separate LiteX/GCC
bootstrap is `soc/bootstrap_soc.sh`. Both refuse replacing an existing prefix.
Version pins and download hashes are recorded in `soc/toolchain-lock.json` and
the Phase 1 tool evidence. Read [THIRD_PARTY.md](THIRD_PARTY.md) for licenses.

```bash
export PATH=/opt/gamebub-litex-20261021/venv/bin:/opt/gamebub-litex-20261021/toolchain/usr/bin:/opt/gamebub-openxc7-20261021/bin:/opt/gamebub-openxc7-20261021/oss-cad-suite/bin:/usr/bin:/bin

# Choose fresh, absolute output paths; scripts refuse overwriting old evidence.
python soc/generate.py --console-pmod --output /tmp/gamebub-cpu-generated

python soc/sim/run_cpu_sim.py --simulator verilator \
  --gateware-dir /tmp/gamebub-cpu-generated/gateware \
  --bindings /tmp/gamebub-cpu-generated/soc_bindings.vh \
  --firmware-elf /tmp/gamebub-cpu-generated/firmware/diagnostic.elf \
  --firmware-bin /tmp/gamebub-cpu-generated/firmware/diagnostic.bin \
  --output /tmp/gamebub-cpu-simulation

python soc/build_openxc7.py --tools /opt/gamebub-openxc7-20261021 \
  --gateware-dir /tmp/gamebub-cpu-generated/gateware \
  --xdc /tmp/gamebub-cpu-generated/gamebub_soc.xdc \
  --output /tmp/gamebub-cpu-build

python soc/check_bundle.py --generated /tmp/gamebub-cpu-generated \
  --simulation /tmp/gamebub-cpu-simulation --build /tmp/gamebub-cpu-build \
  --output /tmp/gamebub-cpu-identity.json
```

For the independent bad-identifier negative control, add `--fault-id` to the
simulation command and select a different fresh output directory. See
[tests/README.md](tests/README.md) for the exact executed evidence and the
Icarus initial-decoder scheduling issue. Do not stimulate the bus artificially
to turn that failed simulation into a nominal pass.

## What the diagnostic verifies

The real CPU executes the linked ELF's embedded ROM. It checks zeroed BSS,
four address-dependent BRAM patterns, byte/halfword write enables and adjacent
bytes, a read-only identifier CSR, and a running timer reaching zero. It emits:

```text
GB_BOOT
RAM_OK
ID_OK
TIMER_OK
GB_PASS
```

The testbench independently decodes the serial pin, checks the software-written
`0x600d000f` result, asserts the specified inactive outputs, then resets the SoC
and requires another complete boot. The negative control forces the identifier
wrong and requires `GB_FAIL` / `0xbad00002`, not the normal success marker.
Timer IRQ delivery, UART RX traffic and external memories are not covered.

## Physical timing limitations

The openXC7 report checks the explicit 50 MHz clock under its **DEFAULT** timing
model. Device selection is `xc7a100tcsg324-1`, but this engine does not provide
speed-grade-1 setup/hold, external-I/O or full CDC signoff. A successful build
is not a hardware-qualified release. No false paths or invented board delays
are added to hide these limitations.
