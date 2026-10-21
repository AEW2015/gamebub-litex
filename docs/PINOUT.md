<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# GameBub Rev4 LiteX pinout

All **198 board signal pins** in the pinned Rev4 XDC: **145 defined** by the
current LiteX platform and **53 not mapped**. A defined pin may be held
inactive rather than driven by a working peripheral. This document does not enable pins.

Source: [official GameBub v1.0.2 Rev4 constraints](https://github.com/elipsitz/gamebub/blob/v1.0.2/fpga/verilog/handheld/rev_4.xdc).
The per-signal pin/standard tuples were checked against that upstream version.
The byte-frozen local reference is [rev_4.xdc](../gamebub/reference/rev_4.xdc).

Reference SHA-256: `af2d5b6e9a157ed9636330cc1105180bd4bc7384e8c67d622119944b923953b8`.

## Scope and safety

- These are FPGA **package balls**, not connector pin numbers or I/O bank numbers.
- This covers all named signals in the reference, not all 324 package contacts.
  Power, ground, dedicated configuration/JTAG pins and unlisted nets are not inferred.
- `tester` means connected to the current example; `held 0/1` means an inactive
  control output; `unmapped` means no corresponding LiteX request exists yet.
- Unmapped pins have **no tester-configured direction**. Their electrical default
  pull/termination state is not guaranteed by this table.
- LVCMOS33/TMDS_33 are the reference I/O standards, not permission to attach arbitrary
  external voltages or treat a board-connected signal as general GPIO.
- Cartridge/link electrical controls and shared USB-C/dock signals require schematic
  review before adding controllers. No HDMI, USB PHY or cartridge operation is claimed.
- The SD card and normal power/volume/menu functions remain ESP32-owned. No direct
  FPGA SD-card, panel-backlight or ESP32 button GPIOs are invented here.

## Reading the LiteX names

A name such as `sram.dq[0]` means bit zero of the `dq` field returned by
`platform.request("sram")`; `buttons_n[0]` is bit zero of `platform.request("buttons_n")`.
The name `esp_irq_gate` deliberately differs from the original `mcu_irq_n` net.
A dash in the LiteX column means the signal is documented but **not requestable**.

## Interface summary

| Interface | Signal pins | Defined by platform | Not mapped |
| --- | ---: | ---: | ---: |
| Clock | 1 | 1 | 0 |
| Buttons | 12 | 12 | 0 |
| ESP32 | 7 | 7 | 0 |
| LCD | 28 | 28 | 0 |
| Audio | 4 | 4 | 0 |
| Vibration | 2 | 2 | 0 |
| SRAM | 39 | 39 | 0 |
| SDRAM | 41 | 41 | 0 |
| Cartridge | 38 | 7 | 31 |
| Link port | 8 | 4 | 4 |
| HDMI | 8 | 0 | 8 |
| USB-C sideband | 2 | 0 | 2 |
| PMOD | 4 | 0 | 4 |
| Test points | 4 | 0 | 4 |

## Clock

50 MHz oscillator input; clock generation is internal to the tester.

| Official signal | Package pin | I/O standard | LiteX request / field | FPGA flow | Tester use |
| --- | --- | --- | --- | --- | --- |
| `clk_50mhz` | `P17` | `LVCMOS33` | `clk50` | input | tester |

## Buttons

Pressed-low FPGA buttons with pull-ups. Bit order follows buttons_n[0..11]. Power, volume and the ESP32 menu button are not extra FPGA button GPIOs.

| Official signal | Package pin | I/O standard | LiteX request / field | FPGA flow | Tester use |
| --- | --- | --- | --- | --- | --- |
| `btn_a` | `L6` | `LVCMOS33` | `buttons_n[0]` | input | tester |
| `btn_b` | `K6` | `LVCMOS33` | `buttons_n[1]` | input | tester |
| `btn_x` | `M6` | `LVCMOS33` | `buttons_n[2]` | input | tester |
| `btn_y` | `N5` | `LVCMOS33` | `buttons_n[3]` | input | tester |
| `btn_up` | `N16` | `LVCMOS33` | `buttons_n[4]` | input | tester |
| `btn_down` | `L13` | `LVCMOS33` | `buttons_n[5]` | input | tester |
| `btn_left` | `L14` | `LVCMOS33` | `buttons_n[6]` | input | tester |
| `btn_right` | `M16` | `LVCMOS33` | `buttons_n[7]` | input | tester |
| `btn_l` | `K13` | `LVCMOS33` | `buttons_n[8]` | input | tester |
| `btn_r` | `K5` | `LVCMOS33` | `buttons_n[9]` | input | tester |
| `btn_start` | `H6` | `LVCMOS33` | `buttons_n[10]` | input | tester |
| `btn_select` | `H5` | `LVCMOS33` | `buttons_n[11]` | input | tester |

## ESP32

ESP32 is QSPI master; FPGA is slave. esp_irq_gate drives the external IRQ gate and resets low; do not infer pad polarity from the original mcu_irq_n name alone.

| Official signal | Package pin | I/O standard | LiteX request / field | FPGA flow | Tester use |
| --- | --- | --- | --- | --- | --- |
| `mcu_spi_clk` | `T14` | `LVCMOS33` | `qspi.sck` | input | tester |
| `mcu_spi_cs_n` | `U17` | `LVCMOS33` | `qspi.cs_n` | input | tester |
| `mcu_spi_d[0]` | `V15` | `LVCMOS33` | `qspi.dq[0]` | inout | tester |
| `mcu_spi_d[1]` | `V16` | `LVCMOS33` | `qspi.dq[1]` | inout | tester |
| `mcu_spi_d[2]` | `U16` | `LVCMOS33` | `qspi.dq[2]` | inout | tester |
| `mcu_spi_d[3]` | `V17` | `LVCMOS33` | `qspi.dq[3]` | inout | tester |
| `mcu_irq_n` | `N15` | `LVCMOS33` | `esp_irq_gate` | output | tester |

## LCD

Native RGB888 scanout. Panel setup and backlight remain ESP32-owned; there is no invented FPGA backlight/reset GPIO.

| Official signal | Package pin | I/O standard | LiteX request / field | FPGA flow | Tester use |
| --- | --- | --- | --- | --- | --- |
| `lcd_dotclk` | `T18` | `LVCMOS33` | `lcd.dotclk` | output | tester |
| `lcd_hsync` | `U18` | `LVCMOS33` | `lcd.hsync` | output | tester |
| `lcd_vsync` | `T16` | `LVCMOS33` | `lcd.vsync` | output | tester |
| `lcd_data_en` | `R18` | `LVCMOS33` | `lcd.de` | output | tester |
| `lcd_data_b[0]` | `R17` | `LVCMOS33` | `lcd.b[0]` | output | tester |
| `lcd_data_b[1]` | `P18` | `LVCMOS33` | `lcd.b[1]` | output | tester |
| `lcd_data_b[2]` | `N17` | `LVCMOS33` | `lcd.b[2]` | output | tester |
| `lcd_data_b[3]` | `M17` | `LVCMOS33` | `lcd.b[3]` | output | tester |
| `lcd_data_b[4]` | `M18` | `LVCMOS33` | `lcd.b[4]` | output | tester |
| `lcd_data_b[5]` | `L16` | `LVCMOS33` | `lcd.b[5]` | output | tester |
| `lcd_data_b[6]` | `L18` | `LVCMOS33` | `lcd.b[6]` | output | tester |
| `lcd_data_b[7]` | `K17` | `LVCMOS33` | `lcd.b[7]` | output | tester |
| `lcd_data_g[0]` | `J17` | `LVCMOS33` | `lcd.g[0]` | output | tester |
| `lcd_data_g[1]` | `J18` | `LVCMOS33` | `lcd.g[1]` | output | tester |
| `lcd_data_g[2]` | `H16` | `LVCMOS33` | `lcd.g[2]` | output | tester |
| `lcd_data_g[3]` | `H17` | `LVCMOS33` | `lcd.g[3]` | output | tester |
| `lcd_data_g[4]` | `G18` | `LVCMOS33` | `lcd.g[4]` | output | tester |
| `lcd_data_g[5]` | `G17` | `LVCMOS33` | `lcd.g[5]` | output | tester |
| `lcd_data_g[6]` | `F18` | `LVCMOS33` | `lcd.g[6]` | output | tester |
| `lcd_data_g[7]` | `E17` | `LVCMOS33` | `lcd.g[7]` | output | tester |
| `lcd_data_r[0]` | `E18` | `LVCMOS33` | `lcd.r[0]` | output | tester |
| `lcd_data_r[1]` | `E16` | `LVCMOS33` | `lcd.r[1]` | output | tester |
| `lcd_data_r[2]` | `D18` | `LVCMOS33` | `lcd.r[2]` | output | tester |
| `lcd_data_r[3]` | `D17` | `LVCMOS33` | `lcd.r[3]` | output | tester |
| `lcd_data_r[4]` | `C17` | `LVCMOS33` | `lcd.r[4]` | output | tester |
| `lcd_data_r[5]` | `B18` | `LVCMOS33` | `lcd.r[5]` | output | tester |
| `lcd_data_r[6]` | `B17` | `LVCMOS33` | `lcd.r[6]` | output | tester |
| `lcd_data_r[7]` | `A18` | `LVCMOS33` | `lcd.r[7]` | output | tester |

## Audio

DSP serial audio, not a claim of generic I2S framing. Clocks continue running while PCM is muted. ESP32 configures DAC volume/routing over its own control bus.

| Official signal | Package pin | I/O standard | LiteX request / field | FPGA flow | Tester use |
| --- | --- | --- | --- | --- | --- |
| `dac_mclk` | `T15` | `LVCMOS33` | `dac_mclk` | output | tester |
| `dac_wclk` | `R15` | `LVCMOS33` | `dac_wclk` | output | tester |
| `dac_bclk` | `R16` | `LVCMOS33` | `dac_bclk` | output | tester |
| `dac_din` | `P15` | `LVCMOS33` | `dac_din` | output | tester |

## Vibration

IN1 carries bounded forward/coast PWM; IN2 is fixed low. Outputs start off.

| Official signal | Package pin | I/O standard | LiteX request / field | FPGA flow | Tester use |
| --- | --- | --- | --- | --- | --- |
| `vibrate_in1` | `F5` | `LVCMOS33` | `vibrate_in1` | output | tester |
| `vibrate_in2` | `G6` | `LVCMOS33` | `vibrate_in2` | output | tester |

## SRAM

512 KiB asynchronous x16 interface. CPU accesses are 32-bit Wishbone transactions.

| Official signal | Package pin | I/O standard | LiteX request / field | FPGA flow | Tester use |
| --- | --- | --- | --- | --- | --- |
| `sram_a[0]` | `V1` | `LVCMOS33` | `sram.a[0]` | output | tester |
| `sram_a[1]` | `U2` | `LVCMOS33` | `sram.a[1]` | output | tester |
| `sram_a[2]` | `V2` | `LVCMOS33` | `sram.a[2]` | output | tester |
| `sram_a[3]` | `U3` | `LVCMOS33` | `sram.a[3]` | output | tester |
| `sram_a[4]` | `U4` | `LVCMOS33` | `sram.a[4]` | output | tester |
| `sram_a[5]` | `V10` | `LVCMOS33` | `sram.a[5]` | output | tester |
| `sram_a[6]` | `U11` | `LVCMOS33` | `sram.a[6]` | output | tester |
| `sram_a[7]` | `V11` | `LVCMOS33` | `sram.a[7]` | output | tester |
| `sram_a[8]` | `U12` | `LVCMOS33` | `sram.a[8]` | output | tester |
| `sram_a[9]` | `V12` | `LVCMOS33` | `sram.a[9]` | output | tester |
| `sram_a[10]` | `T1` | `LVCMOS33` | `sram.a[10]` | output | tester |
| `sram_a[11]` | `U1` | `LVCMOS33` | `sram.a[11]` | output | tester |
| `sram_a[12]` | `R3` | `LVCMOS33` | `sram.a[12]` | output | tester |
| `sram_a[13]` | `P5` | `LVCMOS33` | `sram.a[13]` | output | tester |
| `sram_a[14]` | `T3` | `LVCMOS33` | `sram.a[14]` | output | tester |
| `sram_a[15]` | `R11` | `LVCMOS33` | `sram.a[15]` | output | tester |
| `sram_a[16]` | `R12` | `LVCMOS33` | `sram.a[16]` | output | tester |
| `sram_a[17]` | `T13` | `LVCMOS33` | `sram.a[17]` | output | tester |
| `sram_io[0]` | `T5` | `LVCMOS33` | `sram.dq[0]` | inout | tester |
| `sram_io[1]` | `V5` | `LVCMOS33` | `sram.dq[1]` | inout | tester |
| `sram_io[2]` | `U6` | `LVCMOS33` | `sram.dq[2]` | inout | tester |
| `sram_io[3]` | `V6` | `LVCMOS33` | `sram.dq[3]` | inout | tester |
| `sram_io[4]` | `U7` | `LVCMOS33` | `sram.dq[4]` | inout | tester |
| `sram_io[5]` | `V7` | `LVCMOS33` | `sram.dq[5]` | inout | tester |
| `sram_io[6]` | `U8` | `LVCMOS33` | `sram.dq[6]` | inout | tester |
| `sram_io[7]` | `U9` | `LVCMOS33` | `sram.dq[7]` | inout | tester |
| `sram_io[8]` | `T4` | `LVCMOS33` | `sram.dq[8]` | inout | tester |
| `sram_io[9]` | `R5` | `LVCMOS33` | `sram.dq[9]` | inout | tester |
| `sram_io[10]` | `R6` | `LVCMOS33` | `sram.dq[10]` | inout | tester |
| `sram_io[11]` | `T6` | `LVCMOS33` | `sram.dq[11]` | inout | tester |
| `sram_io[12]` | `R7` | `LVCMOS33` | `sram.dq[12]` | inout | tester |
| `sram_io[13]` | `R8` | `LVCMOS33` | `sram.dq[13]` | inout | tester |
| `sram_io[14]` | `T8` | `LVCMOS33` | `sram.dq[14]` | inout | tester |
| `sram_io[15]` | `T9` | `LVCMOS33` | `sram.dq[15]` | inout | tester |
| `sram_ce_n` | `V4` | `LVCMOS33` | `sram.ce_n` | output | tester |
| `sram_we_n` | `V9` | `LVCMOS33` | `sram.we_n` | output | tester |
| `sram_oe_n` | `T11` | `LVCMOS33` | `sram.oe_n` | output | tester |
| `sram_ub_n` | `R10` | `LVCMOS33` | `sram.ub_n` | output | tester |
| `sram_lb_n` | `T10` | `LVCMOS33` | `sram.lb_n` | output | tester |

## SDRAM

32 MiB SDR SDRAM, fixed 50 MHz. Rank zero is selected; second CS stays inactive. No dynamic high-speed/phase/tap tester is implied.

| Official signal | Package pin | I/O standard | LiteX request / field | FPGA flow | Tester use |
| --- | --- | --- | --- | --- | --- |
| `sdram_dq[0]` | `R2` | `LVCMOS33` | `sdram.dq[0]` | inout | tester |
| `sdram_dq[1]` | `R1` | `LVCMOS33` | `sdram.dq[1]` | inout | tester |
| `sdram_dq[2]` | `P2` | `LVCMOS33` | `sdram.dq[2]` | inout | tester |
| `sdram_dq[3]` | `N2` | `LVCMOS33` | `sdram.dq[3]` | inout | tester |
| `sdram_dq[4]` | `N1` | `LVCMOS33` | `sdram.dq[4]` | inout | tester |
| `sdram_dq[5]` | `M2` | `LVCMOS33` | `sdram.dq[5]` | inout | tester |
| `sdram_dq[6]` | `M1` | `LVCMOS33` | `sdram.dq[6]` | inout | tester |
| `sdram_dq[7]` | `L3` | `LVCMOS33` | `sdram.dq[7]` | inout | tester |
| `sdram_dq[8]` | `L4` | `LVCMOS33` | `sdram.dq[8]` | inout | tester |
| `sdram_dq[9]` | `L5` | `LVCMOS33` | `sdram.dq[9]` | inout | tester |
| `sdram_dq[10]` | `M4` | `LVCMOS33` | `sdram.dq[10]` | inout | tester |
| `sdram_dq[11]` | `M3` | `LVCMOS33` | `sdram.dq[11]` | inout | tester |
| `sdram_dq[12]` | `N6` | `LVCMOS33` | `sdram.dq[12]` | inout | tester |
| `sdram_dq[13]` | `N4` | `LVCMOS33` | `sdram.dq[13]` | inout | tester |
| `sdram_dq[14]` | `P3` | `LVCMOS33` | `sdram.dq[14]` | inout | tester |
| `sdram_dq[15]` | `P4` | `LVCMOS33` | `sdram.dq[15]` | inout | tester |
| `sdram_a[0]` | `G2` | `LVCMOS33` | `sdram.a[0]` | output | tester |
| `sdram_a[1]` | `F1` | `LVCMOS33` | `sdram.a[1]` | output | tester |
| `sdram_a[2]` | `E2` | `LVCMOS33` | `sdram.a[2]` | output | tester |
| `sdram_a[3]` | `E1` | `LVCMOS33` | `sdram.a[3]` | output | tester |
| `sdram_a[4]` | `E7` | `LVCMOS33` | `sdram.a[4]` | output | tester |
| `sdram_a[5]` | `D3` | `LVCMOS33` | `sdram.a[5]` | output | tester |
| `sdram_a[6]` | `D2` | `LVCMOS33` | `sdram.a[6]` | output | tester |
| `sdram_a[7]` | `E6` | `LVCMOS33` | `sdram.a[7]` | output | tester |
| `sdram_a[8]` | `E3` | `LVCMOS33` | `sdram.a[8]` | output | tester |
| `sdram_a[9]` | `F3` | `LVCMOS33` | `sdram.a[9]` | output | tester |
| `sdram_a[10]` | `G1` | `LVCMOS33` | `sdram.a[10]` | output | tester |
| `sdram_a[11]` | `F4` | `LVCMOS33` | `sdram.a[11]` | output | tester |
| `sdram_a[12]` | `G3` | `LVCMOS33` | `sdram.a[12]` | output | tester |
| `sdram_bs[0]` | `H1` | `LVCMOS33` | `sdram.ba[0]` | output | tester |
| `sdram_bs[1]` | `H2` | `LVCMOS33` | `sdram.ba[1]` | output | tester |
| `sdram_clk` | `J5` | `LVCMOS33` | `sdram.clk` | output | tester |
| `sdram_we_n` | `K2` | `LVCMOS33` | `sdram.we_n` | output | tester |
| `sdram_ldqm` | `L1` | `LVCMOS33` | `sdram.dm[0]` | output | tester |
| `sdram_udqm` | `K3` | `LVCMOS33` | `sdram.dm[1]` | output | tester |
| `sdram_cas_n` | `K1` | `LVCMOS33` | `sdram.cas_n` | output | tester |
| `sdram_ras_n` | `J2` | `LVCMOS33` | `sdram.ras_n` | output | tester |
| `sdram_cke[0]` | `J4` | `LVCMOS33` | `sdram.cke[0]` | output | tester |
| `sdram_cke[1]` | `H4` | `LVCMOS33` | `sdram.cke[1]` | output | tester |
| `sdram_cs_n[0]` | `J3` | `LVCMOS33` | `sdram.cs_n[0]` | output | tester |
| `sdram_cs_n[1]` | `G4` | `LVCMOS33` | `sdram.cs_n[1]` | output | tester |

## Cartridge

No cartridge controller. OE is held high and direction controls low. Data and cart_switch are not LiteX resources; review the schematic and electrical requirements before use.

| Official signal | Package pin | I/O standard | LiteX request / field | FPGA flow | Tester use |
| --- | --- | --- | --- | --- | --- |
| `cart_bank0[0]` | `A16` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank0[1]` | `B16` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank0[2]` | `D12` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank0[3]` | `C12` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank0[4]` | `D13` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank0[5]` | `F13` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank0[6]` | `C14` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank0[7]` | `D14` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank1[0]` | `B11` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank1[1]` | `B12` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank1[2]` | `A13` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank1[3]` | `B13` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank1[4]` | `A14` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank1[5]` | `B14` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank1[6]` | `A15` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank1[7]` | `C15` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank2[0]` | `D5` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank2[1]` | `C5` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank2[2]` | `C6` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank2[3]` | `D7` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank2[4]` | `C7` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank2[5]` | `D8` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank2[6]` | `D4` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank2[7]` | `E5` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank3[0]` | `C4` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank3[1]` | `B7` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank3[2]` | `A6` | `LVCMOS33` | — | not configured | unmapped |
| `cart_bank3[3]` | `B6` | `LVCMOS33` | — | not configured | unmapped |
| `cart_pin30` | `E15` | `LVCMOS33` | — | not configured | unmapped |
| `cart_pin30_dir` | `C16` | `LVCMOS33` | `cart_pin30_dir` | output | held 0 |
| `cart_pin31` | `F16` | `LVCMOS33` | — | not configured | unmapped |
| `cart_pin31_dir` | `F15` | `LVCMOS33` | `cart_pin31_dir` | output | held 0 |
| `cart_bank0_dir` | `D15` | `LVCMOS33` | `cart_bank0_dir` | output | held 0 |
| `cart_bank1_dir` | `A11` | `LVCMOS33` | `cart_bank1_dir` | output | held 0 |
| `cart_bank2_dir` | `F6` | `LVCMOS33` | `cart_bank2_dir` | output | held 0 |
| `cart_bank3_dir` | `B4` | `LVCMOS33` | `cart_bank3_dir` | output | held 0 |
| `cart_switch` | `J13` | `LVCMOS33` | — | not configured | unmapped |
| `cart_oe_n` | `A5` | `LVCMOS33` | `cart_oe_n` | output | held 1 |

## Link port

No link controller. Direction controls are held low; data pins are not mapped.

| Official signal | Package pin | I/O standard | LiteX request / field | FPGA flow | Tester use |
| --- | --- | --- | --- | --- | --- |
| `link_so` | `K15` | `LVCMOS33` | — | not configured | unmapped |
| `link_si` | `J15` | `LVCMOS33` | — | not configured | unmapped |
| `link_sd` | `H15` | `LVCMOS33` | — | not configured | unmapped |
| `link_sc` | `G16` | `LVCMOS33` | — | not configured | unmapped |
| `link_so_dir` | `K16` | `LVCMOS33` | `link_so_dir` | output | held 0 |
| `link_si_dir` | `J14` | `LVCMOS33` | `link_si_dir` | output | held 0 |
| `link_sd_dir` | `H14` | `LVCMOS33` | `link_sd_dir` | output | held 0 |
| `link_sc_dir` | `G14` | `LVCMOS33` | `link_sc_dir` | output | held 0 |

## HDMI

TMDS_33, not LVCMOS33. No transmitter is implemented. The upstream XDC notes dock-related polarity reversal; this table preserves the original p/n assignments.

| Official signal | Package pin | I/O standard | LiteX request / field | FPGA flow | Tester use |
| --- | --- | --- | --- | --- | --- |
| `hdmi_clk_p` | `C2` | `TMDS_33` | — | not configured | unmapped |
| `hdmi_clk_n` | `C1` | `TMDS_33` | — | not configured | unmapped |
| `hdmi_data_p[0]` | `A4` | `TMDS_33` | — | not configured | unmapped |
| `hdmi_data_n[0]` | `A3` | `TMDS_33` | — | not configured | unmapped |
| `hdmi_data_p[1]` | `B3` | `TMDS_33` | — | not configured | unmapped |
| `hdmi_data_n[1]` | `B2` | `TMDS_33` | — | not configured | unmapped |
| `hdmi_data_p[2]` | `B1` | `TMDS_33` | — | not configured | unmapped |
| `hdmi_data_n[2]` | `A1` | `TMDS_33` | — | not configured | unmapped |

## USB-C sideband

These SBU signals are not a USB data PHY or SD-card interface. Connector sharing and board ownership need review before enabling them.

| Official signal | Package pin | I/O standard | LiteX request / field | FPGA flow | Tester use |
| --- | --- | --- | --- | --- | --- |
| `usb_sbu_1` | `G13` | `LVCMOS33` | — | not configured | unmapped |
| `usb_sbu_2` | `F14` | `LVCMOS33` | — | not configured | unmapped |

## PMOD

Four FPGA PMOD signals appear in this reference; no PMOD peripheral is implemented.

| Official signal | Package pin | I/O standard | LiteX request / field | FPGA flow | Tester use |
| --- | --- | --- | --- | --- | --- |
| `pmod[0]` | `V14` | `LVCMOS33` | — | not configured | unmapped |
| `pmod[1]` | `U14` | `LVCMOS33` | — | not configured | unmapped |
| `pmod[2]` | `U13` | `LVCMOS33` | — | not configured | unmapped |
| `pmod[3]` | `R13` | `LVCMOS33` | — | not configured | unmapped |

## Test points

Four named test-point signals; not configured by the tester.

| Official signal | Package pin | I/O standard | LiteX request / field | FPGA flow | Tester use |
| --- | --- | --- | --- | --- | --- |
| `tp[0]` | `M14` | `LVCMOS33` | — | not configured | unmapped |
| `tp[1]` | `M13` | `LVCMOS33` | — | not configured | unmapped |
| `tp[2]` | `N14` | `LVCMOS33` | — | not configured | unmapped |
| `tp[3]` | `P14` | `LVCMOS33` | — | not configured | unmapped |

## Regeneration

```bash
python tools/pinout.py --write
python tools/pinout.py --check
python tools/pinout.py --check --check-platform
```

The last command additionally instantiates the LiteX platform and checks every
defined resource against `Platform.binding`; it needs the pinned Migen/LiteX environment.
The first two commands need only the Python standard library. [CSV export](pinout.csv).
