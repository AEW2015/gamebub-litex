<!-- SPDX-License-Identifier: 0BSD -->
# ESP32 service endpoint (simulation subset)

`ESP32Service` wraps the unchanged portable `esp32_v102_endpoint.sv` using
Migen `Instance`. Use it from the phase-3 package path:

```python
from esp32.service import ESP32Service

self.esp32 = ESP32Service(platform, service_domain="service",
                           sys_domain="sys", with_overlay=True)
self.esp32.overlay.connect_video(self.video)
self.comb += [
    self.esp32.buttons_native.eq(~self.buttons_n),
    self.esp32.vblank.eq(self.video.frame_start),
    platform.request("esp_irq_gate").eq(self.esp32.irq_gate),
]
self.bus.add_slave("esp32_diag", self.esp32.bus,
                   SoCRegion(origin=0xB0000000, size=0x10000))
```

The board interrupt output is the Rev4 nFET gate: `irq_gate=0` is idle and
`irq_gate=1` asserts the shared active-low MCU interrupt. The 50MHz CPU-facing
Wishbone window is read-only diagnostic data; a bundled-data toggle/ack CDC
holds request fields and the service response stable across clock domains.
It does not turn the subset into the complete ESP32 register or mailbox ABI.

The overlay stores 360x240 2-bit opacity/luma pixels in a synchronous dual-clock
BRAM. Input data is ARGB1555; the RTL monochrome rule is retained
(`2R + 5G + B >= 128`) with alpha independent. Native output coordinates map
`x=0..479`, `y=12..731` to source index `(x>>1)*360 + ((y-12)>>1)`. The reader
has a one-video-cycle look-ahead interface matching `Video.overlay_*`.

## Verification

The preferred recorded-evidence run is Verilator (default):

```powershell
python D:\codex_archive_2026\gamebub-litex\phase3\esp32\run.py
```

It requires a fresh output path (default
`D:\xup_2026\bub\gamebub-phase3-esp32-final`) and stages the exact endpoint,
host BFM and testbench there. `evidence.json` records tool version, exact
commands, source hashes and PASS/FAIL; compiler and simulation output are
separate logs. Use `--output <new-path>` to preserve an earlier evidence run.
Verilator must support `--binary --timing`.

The first default invocation recorded `ERROR_SIMULATOR_NOT_FOUND` because the
configured OSS-CAD-Suite directory was not on the default Windows/WSL PATH.
The corrected passing evidence is in
`D:\xup_2026\bub\gamebub-phase3-esp32-pass` (Verilator 5.053 devel). Earlier
failed attempts are retained separately. The pinned upstream endpoint emits
width-expansion warnings; `-Wno-fatal` keeps all of them visible in
`compile.log` while still failing on compilation errors. The passing run's
simulation log reports `PASS: official QSPI reads/writes, buttons, IRQ W1C and
overlay bounds` and exits zero.

For simulator compatibility checks only, the runner accepts explicit
`--simulator icarus`; this is not the default evidence engine. The direct
pin-level test uses official v1.0.2 QSPI command fields and eight read-dummy
bytes. The equivalent manual WSL commands are:

```sh
iverilog -g2012 -s tb_endpoint_protocol -o /tmp/tb_endpoint_protocol.vvp \
  /mnt/d/codex_archive_2026/gamebub-litex/phase3/esp32/rtl/esp32_v102_endpoint.sv \
  /mnt/d/codex_archive_2026/gamebub-litex/phase3/esp32/qspi_host_bfm.sv \
  /mnt/d/codex_archive_2026/gamebub-litex/phase3/esp32/tb_endpoint_protocol.sv
vvp /tmp/tb_endpoint_protocol.vvp
```

Executed result under Icarus Verilog 11.0: `PASS: official QSPI reads/writes,
buttons, IRQ W1C and overlay bounds`. The test additionally requires quad
output enable during all read nibbles and checks that FPGA DQ ownership
releases immediately on raw CS deassertion. The current OSS-suite Icarus 14
direct compile fails because that release rejects the existing endpoint's
`physical_host` declaration-after-use (reported at source lines 69/85); the
endpoint/reference-engine source hash is unchanged. The preferred Verilator
run remains separate and is recorded by `run.py`. The LiteX wrapper has also
been imported and elaborated to Verilog with the phase-3 simulation platform.
These are simulation/source checks only; there is no hardware acceptance or
pin timing qualification.

ABI details, provenance and explicit unsupported features are in
[`PROVENANCE.md`](PROVENANCE.md).
