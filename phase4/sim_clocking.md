# Physical CRG and verification

`clocking.py` exports `PhysicalCRG(platform, por_cycles=1024)` and alias `CRG`.
The platform must provide the 50 MHz `clk50` pad. Attributes `cd_sys`,
`cd_service`, `cd_video`, `cd_por`, `locked`, `por_done`, `reset_request` are
available to integration. The named clock signals have `keep` attributes.

One LiteX `S7MMCM` generates all three domain clocks. Its search is constrained
to DIVCLK=1, feedback multiply=16, and an 800 MHz VCO. Fractional CLKOUT0 is
created first for video; CLKOUT1 and CLKOUT2 use integer dividers.

| Domain | Divider | Actual frequency |
|---|---:|---:|
| sys | 16 | 50,000,000 Hz |
| service | 4 | 200,000,000 Hz |
| video | 27.25 | 29,357,798.165137615 Hz |

For the existing official-derived fixed LCD profile (605x809 total), refresh
is 59.98181238982443 Hz. Video differs by -142.395085 ppm from the historical
29,361,979.166667 Hz clock. This is an explicitly selected nearest frequency
with exact 50/200 MHz domains, rather than a claim of identical legacy clocks.

The POR counter runs from an independently BUFG-buffered input clock with no
reset. It holds MMCM reset for 1024 input edges. LiteX also provides its default
eight input-clock reset pipeline. Every output domain has a two-FDPE
`AsyncResetSynchronizer`, asynchronously asserting on POR or lost MMCM lock,
then releasing only on that domain's clock edges. No ESP32 enable/reset gate or
external reset pin participates. The physical module instantiates real
`MMCME2_ADV`, `BUFG`, `FDCE` and `FDPE` primitives; it contains no modeled clock
oscillator. Independent input POR prevents an output-clock reset deadlock.

## Open-source primitive support audit

The installed nextpnr-xilinx version is `e7a6fb0e`. Its executable contains the
MMCM fractional divide, fractional waveform and FRAC_EN feature names.
The maintained [openXC7 FASM backend](https://github.com/openXC7/nextpnr-xilinx/blob/main/xilinx/fasm.cc)
has `write_mmcm_clkout`: CLKOUT0 reads `DIVIDE_F`, computes fractional eighths,
and emits FRAC_EN, FRAC, FRAC_WF_R and the corresponding CLKOUT5 fractional
waveform/phase fields. This supports the selected standard CLKOUT0 /27.25
configuration in principle. The final build must still prove FASM assembly,
route and bitstream generation with this installed tool/database combination.

Expected final MMCM evidence includes CLKOUT0 FRAC_EN, FRAC=2 (2/8), and its
fractional waveform/phase features; sys/service remain integer /16 and /4.
No reserved MMCM site, broad clock timing exception or pin constraint is added
by this module. Input pin/package identity, dedicated clock placement, generated
clock propagation, output delays and CDC constraints belong to the main build.
The main wrapper should use ODDR for panel and inverted SDRAM forwarded clocks;
a logic inversion alone is not a forwarded-clock implementation signoff.

## Executed verification

Run `sim_clocking_run.py --output /path/to/new/evidence` with the isolated
LiteX Python environment and OSS CAD Suite Icarus on PATH. It generates the
actual physical CRG RTL, preserving real primitives in the generated netlist,
then compiles that RTL with separately named verification-only primitive models.
Do not include `sim_clocking_primitives.sv` in the synthesis source list.

Executed 2026-10-21: PASS at
`D:/xup_2026/bub/gamebub-phase4-clocking-test1/evidence.json`.
The test checks the exact elaborated MMCM parameters, autonomous POR, output
periods (20 ns, 5 ns, 34.062 ns at simulator 1 ps precision), two-clock reset
release in every domain, asynchronous assertion when lock is lost and output
clocks stop, then synchronized recovery after relock. It observed two lock
epochs. The JSON retains source hashes, commands, exits and frequency values.

Behavioral MMCM models do not establish analog lock range, phase noise/jitter,
physical route timing or board behavior. Those remain separate physical gates.
