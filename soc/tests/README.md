# Actual CPU verification

The exact generated LiteX/VexRiscv design is tested by
`../sim/run_cpu_sim.py` and `../sim/tb_gamebub_soc.sv`. The runner requires a
new output directory and retains staged inputs, their SHA-256 hashes, simulator
version, commands, exit codes, compile/simulation logs and JSON outcome.

Run in WSL `MRS-HDL-Research` using the isolated Python environment and prepend
`/opt/gamebub-openxc7-20261021/oss-cad-suite/bin` to PATH. Example:

```sh
python soc/sim/run_cpu_sim.py \
  --gateware-dir /path/to/generated/gateware \
  --bindings /path/to/generated/soc_bindings.vh \
  --firmware-elf /path/to/generated/firmware/diagnostic.elf \
  --firmware-bin /path/to/generated/firmware/diagnostic.bin \
  --output /path/to/new/evidence \
  --simulator verilator --trace-cpu
```

The binding header identifies exact generated top/status/reset signals and
asserts the specified safe static outputs. UART decoding checks every start,
data and stop bit at 50 MHz/115200 baud. Required output is exactly:

```text
GB_BOOT
RAM_OK
ID_OK
TIMER_OK
GB_PASS
```

It additionally requires result CSR `0x600d000f`, forces the actual generated
system reset, and requires the entire sequence and signature a second time.
Timeouts are 2,000,000 total cycles, 300,000 cycles without a received byte, and
180 wall seconds per command (configurable). Firmware covers BSS initialization,
256-word BRAM patterns/readback, byte/halfword writes and neighboring bytes,
identifier CSR and countdown progress/expiration. Timer coverage is polling;
interrupt delivery is not claimed. The success spin loop is intentional.

Repeat with a different new output directory and `--fault-id` for a negative
control. It forces the real identifier CSR source to zero while the actual CPU
executes unchanged firmware. Required output becomes `GB_BOOT`, `RAM_OK`,
`GB_FAIL`, with failure CSR `0xbad00002`; a success path fails this control.

## Executed results, 2026-10-21

- Final source set: `D:/xup_2026/bub/gamebub-litex-soc4`.
- Verilator 5.053 exact unmodified RTL positive run: PASS, two boots,
  76 decoded UART bytes, 420,735 cycles, final signature `0x600d000f`.
  Evidence: `D:/xup_2026/bub/gamebub-litex-cpusim-final/evidence.json`.
- Forced identifier negative control: PASS (correct rejection), full failure
  byte sequence and `0xbad00002` observed. Evidence:
  `D:/xup_2026/bub/gamebub-litex-cpusim-negative-id/evidence.json`.
- Earlier Icarus 14 run on `soc3` stalled before executing any instruction:
  `shared_adr=0`, decoder select `master=000`, instruction bus CYC/STB=1,
  ACK=0. The generated Migen `always @(*)` decoder did not evaluate when its
  initialized address input remained zero. Verilator evaluated the same
  unmodified RTL successfully. The Icarus failure remains evidence at
  `D:/xup_2026/bub/gamebub-litex-cpusim3`; it is not reported as a pass.

These are simulation results. Physical timing, external memory, display and
hardware programming require their own evidence.
