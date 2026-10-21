<!-- SPDX-License-Identifier: 0BSD -->

# Build and simulate

## Pinned environment

The recorded flow uses Ubuntu 22.04 x86-64 (WSL2), Python 3.10, Bash, curl,
tar/unzip/xz and dpkg-deb. Compiler and simulator host dependencies must also
be available. This is not a containerized or arbitrary-distribution guarantee.
Read the scripts before running them. `/opt` must be writable by the installing
user; the bootstraps do not grant privileges or run a system package manager.

From a fresh checkout, install into **new, unused** prefixes:

```bash
git clone https://github.com/AEW2015/gamebub-litex.git
cd gamebub-litex
bash tools/bootstrap_linux.sh /opt/gamebub-openxc7-20261021
bash soc/bootstrap_soc.sh
/opt/gamebub-litex-20261021/venv/bin/python phase3/memory/bootstrap.py
```

The bootstrap scripts verify exact archive hashes. Do not overwrite an existing
tool installation to reproduce a build. The dated `/opt` locations are deliberate
pins of the tested environment, not paths into a developer's private checkout.
`soc/toolchain-lock.json` and `phase3/memory/dependencies.json` record the packages.

```bash
export PATH=/opt/gamebub-litex-20261021/venv/bin:/opt/gamebub-litex-20261021/toolchain/usr/bin:/opt/gamebub-openxc7-20261021/bin:/opt/gamebub-openxc7-20261021/oss-cad-suite/bin:/usr/bin:/bin
```

All following commands run from the checkout root. Each output path must be
fresh; keep failed attempts and their logs rather than silently reusing them.

## Generate the current tester

```bash
python phase5/generate.py --output "$PWD/build/tester-rtl-001"
```

This builds the bare-metal RV32I ELF, embeds its ROM into generated RTL, and
records its bindings and address map. The firmware is not a Linux application.
The ELF is `build/tester-rtl-001/firmware/diagnostic.elf`.

## Test before implementation

```bash
python -m unittest discover -s tests -v
python phase5/run_host_test.py --bundle "$PWD/build/tester-rtl-001" --output "$PWD/build/host-test-001"
python phase5/run_protocol.py --output "$PWD/build/qspi-test-001"
python phase5/run_endpoint_timing.py --output "$PWD/build/qspi-matrix-001"
python phase5/sim_apps.py --bundle "$PWD/build/tester-rtl-001" --output "$PWD/build/tester-sim-001"
```

The full simulation takes substantially longer than the host and QSPI tests.
It runs the actual CPU/ROM with pin-level SRAM/SDRAM models and checks normal
operation plus injected SRAM and SDRAM faults. It does not prove physical
I/O timing, audible sound, motor movement or analog behavior.

An optional standalone memory comparison now uses the included fixture:

```bash
python phase3/memory/run_tests.py --output "$PWD/build/memory-test-001"
python phase3/video/run.py --reference "$PWD/phase3/video/reference/gamebub_axis_raster.v" --output "$PWD/build/video-test-001"
```

## Open-source implementation

```bash
python phase5/build.py \
  --tools /opt/gamebub-openxc7-20261021 \
  --gateware-dir "$PWD/build/tester-rtl-001/gateware" \
  --xdc "$PWD/build/tester-rtl-001/physical.xdc" \
  --output "$PWD/build/tester-route-001" \
  --seed 2 --timing-weight 30 --router router2
```

The recorded successful image used seed 2, timing weight 30 and standard
router2. Internal clock checks and strict diagnostics must pass; do not use a
timing-allow-fail switch. Source/host/tool changes can change the result. The
open-source DEFAULT timing model is **not** full external I/O, CDC or -1/PVT
qualification. See [STATUS.md](STATUS.md) before any experimental hardware use.

## Programming is separate

Building and simulating do not touch a board. The recorded load used Vivado
2025.2 only as a programmer. For the optional Windows helper, explicitly set
your own cable serial and calculate the new image's SHA-256:

```powershell
$env:GAMEBUB_JTAG_SERIAL = 'YOUR_HS2_SERIAL'
$bit = 'C:/your-build/gamebub_soc.bit' # use the actual generated bitstream path
$sha = (Get-FileHash -LiteralPath $bit -Algorithm SHA256).Hash
& 'C:/Xilinx/2025.2/Vivado/bin/vivado.bat' -mode batch -source phase4/hardware.tcl -tclargs program $bit $sha
```

The helper refuses missing serials, an unexpected device/chain or a wrong hash.
It programs only volatile FPGA configuration; it does not write persistent flash
or ESP32 firmware. Verify board revision, target, simulation and build results
yourself. Never select a cable simply because it is first in a target list.

After Vivado releases the target, `phase5/monitor.tcl` can be run in XSDB with
the same environment variable to read USER1 JTAG UART. `GB5_OK` means UI startup,
not interactive memory-test completion. Press A on each memory page and observe
its result. Avoid launching a game from the ESP32 menu while using this image.

## Earlier phases

`soc/` and `phase3/` READMEs retain the earlier simulation milestones.
`phase4/` records physical bring-up. The current target is always `phase5/`.
Historical private release packagers and frozen local build trees are omitted;
their absence does not affect the build and simulation commands above.
