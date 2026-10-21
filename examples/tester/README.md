<!-- SPDX-License-Identifier: 0BSD -->

# Basic LiteX tester apps

The main example uses VexRiscv/Migen/LiteX, not the MicroBlaze/AMD-IP app tester.
Build tools remain
open source; Vivado may be used only as the volatile hardware programmer.
See [build instructions](../../docs/BUILD.md) for setup and all test commands.

## Controls

Left/right **shoulder** buttons change pages. **A** starts the selected test;
**B** stops. A held at page entry cannot start another app until released.

| Page | Basic operation |
| --- | --- |
| Color | A cycles bars, white, red, green, blue and black backgrounds. |
| SRAM | A runs four address-mixed 32-bit patterns in a reserved 4 KiB scratch window. |
| SDRAM | Same scratch test at the conservative fixed 50 MHz system clock. |
| Audio | A starts a low-level 440 Hz square tone for at most one second. |
| Vibration | A starts a 200 ms forward/coast pulse, 20 kHz PWM at 50% duty. |

Memory status is READY/RUNNING/PASS/FAIL/STOPPED with a progress bar. Only byte
offsets `0x1000..0x1fff` are overwritten in each external memory. These are
basic scratch tests, **not** full-capacity, performance, dynamic-phase/tap or
PVT qualification. ROM, stack and software state stay in internal BRAM.

Audio and motor are off at boot. Hardware counters bound each activation even
if the CPU stops. B has a hardware stop path; app changes also stop outputs.
There is no automatic physical audio/motor test on configuration. The normal
installed ESP32 firmware continues to own DAC analog volume/routing.
For these two output pages, PASS indicates the digital activation ended; confirm
audible sound and physical motor motion manually. It is not a sensor measurement.

## Display and clocks

A compact black-center/white-text software panel sits over the background.
Its separate 384x240 packed 2-bit alpha/luma BRAM has a visible 360x240 window.
The existing ESP32 QSPI overlay is higher priority. The CPU never writes the
ESP32's overlay memory. Panel updates are direct/front-buffer, not atomic
double-buffered frames. Occasional UI redraw tearing is possible.

System: 50 MHz. QSPI service: 200 MHz. Video/MCLK: 800 MHz / 27.25,
29,357,798.165 Hz. Native LCD: 480x800, total605x809, about59.982 Hz.
DAC DSP framing matches the known-good transmitter: BCLK=MCLK/8, 608 MCLK
per stereo frame, 16-bit signed left then right, DAC sampling on falling BCLK.
The DDS uses the actual sample rate (~48,286 samples/sec), not a 48 kHz
assumption. Peak amplitude is 2048/32767; this is not an analog-volume setting.

## Addresses

- External SRAM: `0x30000000`, 512 KiB.
- External SDRAM: `0x40000000`, 32 MiB.
- Read-only ESP32 diagnostic window: `0xb0000000`.
- CPU UI: `0xc0000000`, 32 KiB aperture; first5760 words are pixel memory.
- CSR addresses: generated `firmware/addresses.h` and `csr.json`.

The VexRiscv IO region begins at `0x80000000`; the CPU UI is deliberately
inside it. Each 32-bit pixel word holds16 pixels, alpha/luma codes0=transparent,
2=opaque black and3=opaque white. A five-bit concatenation forms the pixel
shift amount; a nested four-bit shift would wrap at pixel8, a bug caught by
the first physical-RTL simulation and fixed before deployment.

## Reproduce

Use the installed `MRS-HDL-Research` WSL environment and fresh output paths:

```sh
export PATH=/opt/gamebub-litex-20261021/venv/bin:/opt/gamebub-litex-20261021/toolchain/usr/bin:/opt/gamebub-openxc7-20261021/bin:/opt/gamebub-openxc7-20261021/oss-cad-suite/bin:/usr/bin:/bin
# Run from the checkout root; each output directory must be fresh.
python examples/tester/generate.py --output "$PWD/build/tester-rtl-001"
python tests/tester/run.py --bundle "$PWD/build/tester-rtl-001" --output "$PWD/build/tester-sim-001"
python examples/tester/build.py --tools /opt/gamebub-openxc7-20261021 --gateware-dir "$PWD/build/tester-rtl-001/gateware" --xdc "$PWD/build/tester-rtl-001/physical.xdc" --output "$PWD/build/tester-route-001" --seed 2 --timing-weight 30 --router router2
```

The firmware is embedded in the generated ROM and also supplied as an ELF.
`GB5_OK` means the UI initialized, SDRAM initialization completed and the local
ESP32 diagnostic identity was read. It **does not** claim both
memory app tests passed; those require pressing A and observing their results.

The private build backend exposes placement seed, timing weight and router
selection; actual arguments are retained in the build log. The final build uses
seed2, timing weight30 and standard router2. An experimental timing-driven
rip-up attempt did not converge and was stopped; it is not the released image.
No clock requirement or warning policy is relaxed. Diagnostic transaction/read/
write counters have a documented one-service-cycle event latency in this image;
all QSPI pin/control/commit behavior is compared cycle-for-cycle to the frozen
reference, with that counter latency checked separately.

The installed ESP32 can replace a volatile JTAG image when a game is launched
from its menu. This build does not change that firmware behavior. Avoid launching
a game while testing; an ESP32 menu visibly above the tester still owns its
normal navigation actions.

The exact-RTL test drives physical buttons, external memory pins, QSPI writes,
LCD pixels and DAC/motor outputs. Normal and injected-SRAM/SDRAM-corruption
cases must pass their respective positive/negative assertions. No CPU mock is
used. Simulation-only primitive models are never synthesized.

Available internal clock checks must pass. External setup/hold,
CDC bounds and qualified -1/PVT timing remain explicitly **not signed off** by
the pinned DEFAULT open-source timing model. This remains experimental.

## Licensing

New independent Migen/Python/Tcl is 0BSD. Board bindings and reused ESP32 RTL
retain CERN-OHL-S-2.0; the font/layout-derived C tester retains CERN-OHL-S-2.0.
See [licenses](../../LICENSES/) and [endpoint provenance](../../docs/ESP32_PROTOCOL.md).
No AMD licensed netlists, proprietary IP or software libraries enter the build.
