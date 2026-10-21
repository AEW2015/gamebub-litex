# Rev4 memory controllers and independent pin verification

`gamebub/memory.py` implements a 512 KiB asynchronous x16 SRAM Wishbone bridge and a
32 MiB SDR SDRAM Wishbone interface at 50 MHz. The SDRAM path instantiates pinned
LiteDRAM 2024.12 `GENSDRPHY`, `LiteDRAMController`, `LiteDRAMCrossbar`, and
`LiteDRAMWishbone2Native`; the SRAM bridge is a small Migen state machine with
40 ns setup, 80 ns access, 40 ns hold, and an idle bus-turnaround cycle per halfword.
Both interfaces accept 32-bit classic Wishbone transactions with four byte enables.

Imports are `GameBubSRAM(pads)`, `GameBubSDRAM(pads, sys_clk_freq=50e6)`,
`sram_pads()`, and `sdram_pads()`. Each controller exposes `.bus` and `.initialized`.
Wishbone addresses are word addresses; low aperture bits select external locations,
so the enclosing SoC must decode and align the 512 KiB and 32 MiB regions.
SRAM pads are `a[17:0], dq[15:0], ce_n, we_n, oe_n, lb_n, ub_n`.
SDRAM pads are `a[12:0], ba[1:0], dq[15:0], dm[1:0], cs_n[1:0], cke[1:0],
ras_n, cas_n, we_n, clk`. DQ is a true generic tristate in the generated RTL.
Both controllers use `sys`; the SDRAM forwarded clock is inverted `sys` and
requires no extra simulation clock domain. Physical clock forwarding, I/O timing,
board operation, and PVT qualification are outside this simulation result.

Autonomous SDRAM initialization blocks Wishbone requests for at least 200 us,
issues PRECHARGE ALL, eight AUTO REFRESH commands, and MODE REGISTER SET for
burst length one/CAS latency two, then hands DFI control to LiteDRAM. Periodic
refresh remains enabled in the upstream controller. No firmware init CSR sequence
or substitute transaction-level memory is needed.

The official Rev4 XDC confirms SRAM A[17:0]/DQ[15:0], SDRAM A[12:0]/BA[1:0]/DQ[15:0],
and two physical CS/CKE pins. The known-good v1.6 SDRAM command formatter explicitly
uses `{cke=2'b11, cs_n=2'b10, ...}`. This implementation likewise selects rank zero
and holds the second CS inactive; it does not invent two 16 MiB ranks. Legacy
`BurstSdramController.Config` specifies 13 row bits, nine column bits and two bank
bits, matching the upstream `MT48LC16M16` module geometry and its 32 MiB aperture.
That module is a compatible geometry/timing profile; the physical part marking
has not been independently confirmed because the PCB/BOM is absent locally.

`tools/memory-dependencies.json` pins hashes and published wheels for LiteDRAM/PyYAML.
`tools/bootstrap_memory.py` verifies both before installation into the isolated namespace
`/opt/gamebub-litex-20261021/memory-python`; it refuses an existing target.
The base virtual environment remains separate. Fixture READMEs record the
known-good reference hashes; test evidence records the sources actually used.

Run with the pinned Linux environment:

```sh
python tests/memory/run.py --output /absolute/new/output
```

The runner generates the actual controller RTL and compares every read against
two independent, full-aperture upstream LiteX `wishbone.SRAM` instances. The
unmodified known-good v1.6 `sram_test_pkg.sv` fixture is compiled and runs its nine
pattern families (zeros, ones, checkerboards, walking bits, address/complement,
and PRBS) through both external memories and both LiteX references. This is actual
differential data/byte-enable verification against LiteX, plus source-level
geometry/pin-selection comparison against the legacy controllers. The legacy
SERDES/MMCM controller itself is not differentially simulated here.

`pin_models.sv` observes only external pins. Its sparse tagged stores cover any
address across the complete apertures, with a 4096-written-halfword test capacity.
The SDRAM model checks the power-up wait, refresh count/period, mode, row/bank
commands, basic timing and CAS2 pipelining. Reads begin after T1 and are valid by
T2 as specified by the Micron SDR datasheet; a 6 ns modeled clock-to-data delay
fits the 10 ns half-cycle sample margin. These checks are a behavioral subset,
not a vendor timing model or full JEDEC/PVT qualification.

Each model exposes `fault_read`; driving it high corrupts bit zero of every
driven halfword. The runner executes normal, `+corrupt_sram`, and
`+corrupt_sdram` runs. Each negative run must fail at its first target-memory read
with the expected address, proving the functional assertions observe external DQ.

The standalone runner records `evidence.json` in its selected output directory.
The recorded comparison exercised 341 transactions,
14152 wait cycles, 170 SRAM halfword writes, 172 SDRAM halfword writes, and 23
refreshes. Both corruption runs fail as expected. Tests cover continuous CYC/STB
back-to-back requests, pre-init stalls, byte/halfword/zero masks, 1 KiB bank and
4 KiB row boundaries, last words of both apertures, and retention across refresh.
This test does not contain a CPU; integrated CPU evidence is recorded separately.

Primary references:

- https://github.com/enjoy-digital/litedram/blob/2024.12/litedram/phy/gensdrphy.py
- https://github.com/enjoy-digital/litedram/blob/2024.12/litedram/frontend/wishbone.py
- Micron MT48LC16M16A2 SDR datasheet, CAS latency description and CL2 timing.
