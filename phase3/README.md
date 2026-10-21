<!-- SPDX-License-Identifier: 0BSD -->

# Phase 3: usable board-interface simulation

Status: combined functional simulation passes. No hardware deployment is authorized by
this work. The Phase 1 and Phase 2 releases and handoff hashes are preserved.

The requested milestone is **not another CPU-only demo**. It includes:

1. Native 480x800 LCD RGB scanout with color bars and an ESP32 overlay path,
   comparing generated Migen logic with the known-good packaged LCD core.
2. An ESP32 QSPI slave and the Rev4 interrupt-gate behavior, including actual
   serial transactions, buttons, interrupt acknowledgement and overlay writes.
3. Memory-mapped 512 KiB asynchronous SRAM and 32 MiB SDR SDRAM, exercising
   physical bus models rather than substituting internal BRAM for those devices.
4. A combined LiteX/VexRiscv simulation with the real diagnostic firmware,
   controllers, serial host stimulus, external memories and LCD scanout.

Use standard Migen/LiteX stream, Wishbone and CDC components, and LiteDRAM
where suitable. Reuse the proven portable QSPI protocol RTL as an explicit
custom block: a generic SPI library is not automatically compatible with the
GameBub ESP32 wire protocol. Preserve upstream and derived-file licenses.

The LCD baseline is the official-derived fixed profile in `gamebub_lcd_axis`
v1.5: 480x800 active, 605x809 total, active start (123,6), active-high HS/VS,
approximately 29.361979 MHz pixel clock. The simulation must compare line/frame
edges, active pixels, RGB ordering and reset behavior; a PPM capture is useful
evidence but does not replace assertions.

Memory bring-up is conservative, not the prior dynamic 166–250 MHz SERDES
tester. No high-speed timing or hardware qualification is implied. ESP32 owns
panel configuration/backlight and SD-card access; the FPGA drives LCD video and
services the documented QSPI/IRQ contract. Do not modify ESP32 firmware here.

## Work ownership

- `video/`: Migen LCD and known-good RTL comparisons.
- `esp32/`: portable protocol wrapper, IRQ/buttons, overlay and host tests.
- `memory/`: library-based SRAM/SDRAM controllers and pin-level memory models.
- `integration/`: shared LiteX target, firmware and end-to-end simulation.

See [integration/README.md](integration/README.md) for the combined target,
executed normal/corruption results and reproduction commands. Component
results and reference limitations are recorded in [video/README.md](video/README.md),
[esp32/README.md](esp32/README.md) and [memory/README.md](memory/README.md).
Physical clocking, constraints, synthesis/routing and hardware acceptance remain
separate gates; this is not yet a new deployable combined bitstream.
