<!-- SPDX-License-Identifier: 0BSD -->
# ESP32 endpoint provenance and scope

`rtl/esp32_v102_endpoint.sv` is a byte-for-byte copy of GameBub's public
`gamebub_esp32_v102_v1_14/src/esp32_v102_endpoint.sv` (SHA-256
`b1dabe65572c8ad3ec6f1cdd5e149ae99bddcdbf8e5678eb7ba9403e53dc2db0`). It is
GameBub-derived FPGA RTL and retains the upstream CERN-OHL-S-2.0 terms; it is
not relicensed under this repository's 0BSD wrapper license. The upstream
repository's applicable license text is `../../LICENSES/CERN-OHL-S-2.0.txt`.

`reference/fpga_driver_v1.0.2.rs` is an unmodified reference copy from the
official `elipsitz/gamebub` tag `v1.0.2`, path
`firmware/handheld/src/device/drivers/fpga/mod.rs`, SHA-256
`d480fabf42491a9f128e8c14633bfee5e7718276f32917ab5cf1f2b01ab1f8d1`. It is
firmware material subject to upstream GPL-3.0-only terms (see
`../../LICENSES/GPL-3.0-only.txt`) and is included only to pin the simulated
wire/register contract.

The wrapper adds a read-only CPU diagnostic view, resets the external IRQ gate
low, stores the ESP32 overlay as monochrome+alpha, and binds it to the
phase-3 video look-ahead reader. It does not claim full official firmware ABI
support: framework version and several control/status/command/mailbox features
remain outside this endpoint subset. The official `0xF100...` addresses and
quad protocol are used; no older native-app aliases are provided.

## Protocol and ABI used by this subset

- Mode 0, MSB-first command on DQ0, quad address/data, reads with eight dummy
  bytes. The pinned official driver defaults to byte swap and auto-increment.
- Identity query `0xF1000000` intentionally returns zero; this is not a
  framework-version report. Service clock at `0xF1000004` reports 200 MHz.
- IRQ enable/pending are `0xF1001000`/`0xF1001004`; pending is W1C. The
  button-change source is bit 1 and wins against a simultaneous clear.
- Forced buttons/display control are `0xF1001008`/`0xF100100C`; pressed-high
  buttons are readable at `0xF1002000`.
- Overlay geometry/depth are `0xF1000100`/`0xF1000104` (360x240, 16-bit
  ARGB1555); framebuffer writes use `0xF2000000` and byte addresses.
- CPU diagnostic Wishbone offsets are byte offsets 0x00..0x3c, word-aligned:
  endpoint diag indices 0..15 respectively. It is read-only and is not the
  official ESP32 register aperture.

These are source-level/in-simulation claims only. They do not establish QSPI
electrical timing margins, board operation, or hardware acceptance.
