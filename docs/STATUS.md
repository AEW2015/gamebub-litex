<!-- SPDX-License-Identifier: 0BSD -->

# Recorded acceptance — October 21, 2026

This summarizes the original Phase5 build, not a fresh claim that every later
checkout has completed physical implementation or hardware testing.

| Check | Recorded result |
| --- | --- |
| Exact CPU/ROM and LCD pin-level simulation | PASS; normal operation and injected SRAM/SDRAM fault cases |
| QSPI protocol/IRQ/overlay simulation | PASS |
| QSPI differential matrix | PASS; 36 lane/width/swap/burst combinations |
| Host C checks | PASS; supplemental, not FPGA evidence |
| Available open-source internal clocks / diagnostics | PASS |
| Volatile configuration | DONE=1, CRC=0; USER1 UART `GB5_OK` |
| UI and shoulder navigation | User-confirmed on hardware |
| SRAM and SDRAM 4 KiB scratch tests | User-confirmed PASS on hardware |
| Audio and vibration | Digital simulation PASS; sound/motion not separately confirmed |
| ESP32 overlay on final tester image | Not separately retested; appearance confirmed on earlier physical image |

## Original artifact identities

- Bitstream SHA-256: `64f6479349f26c2a62d71971ceecd332803f854d4a8b7bb6ad13654f4d36e15a`
- Firmware ELF SHA-256: `b52359c6556536b50e2259c850c09863c0cdd0b9caeceaafde20ada03109a651`

The original 142-artifact local evidence manifest was checked before source
publication. Binary artifacts and machine-specific raw logs are not included
in this initial repository import. Rebuilding may change generated file paths,
metadata or output hashes; run the tests for your own build.

The publishing copy adds public documentation, includes previously external
test fixtures, and makes cable selection explicit. The tested local workspace
and frozen release remain unchanged. Phase5 gateware and C firmware are copied
without functional modification.

## Source-publication checks

The separate publishing checkout was checked on October 21, 2026:

- 13 portable unit tests and Python syntax compilation: PASS.
- Phase5 RTL/ELF generation: PASS; the 2748-byte firmware binary is byte-identical
  to the recorded hardware build (ELF container metadata can differ by path).
- Host C test, QSPI protocol and 36-case endpoint differential matrix: PASS.
- LCD comparison against the included v1.5 raster fixture: both profiles PASS.
- Standalone SRAM/SDRAM comparison: normal case PASS and both injected corruptions
  detected as expected.
- Twelve current target gateware/firmware/build input files checked unchanged
  against the hardware-tested workspace.

The complete long-running tester simulation and place-and-route were not rerun
for this documentation/source import; their recorded results are summarized above.
The newly parameterized JTAG helper scripts were not used to reprogram hardware
during publication. CI runs portable source checks, not FPGA implementation.

## Limits

- Internal clocks: CPU 50 MHz; QSPI service 200 MHz; video ~29.358 MHz.
- Nextpnr's reported service-domain achieved fmax was 203.13 MHz against 200 MHz.
  That is an available DEFAULT-model result, not qualified physical signoff.
- External setup/hold, CDC bounds and speed-grade/PVT corners are not signed off.
- Memory checks cover reserved 4 KiB windows, not full capacity or bandwidth.
- Official ESP32 framework support is partial; do not assume SD-card/mailbox or
  complete game-core behavior. ESP32 menu game launch can replace this image.
- UI updates use a front buffer; redraws are not atomic/double-buffered.
