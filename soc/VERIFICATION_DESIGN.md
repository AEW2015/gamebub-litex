# BRAM-only LiteX CPU verification design

Status: proposed contract; no simulation pass is claimed by this document.

The test must compile the generated LiteX SoC and its actual VexRiscv RTL with
Icarus or Verilator, loading the same compiled firmware ROM initialization used
by the synthesis source set. Do not replace CPU, ROM contents, or peripherals
with behavioral success generators. No vendor simulation libraries are needed
when the platform uses direct clocks and inferred Migen memories.

## Recommended observable contract

- A 50 MHz input clock and autonomous power-on reset, with an optional explicit
  reset input. Tests should exercise initial boot and a second reset/boot.
- A real UART TX output at a documented baud (115200, 8N1 recommended), RX tied
  idle high, and the documented safe board outputs.
- Ordered short firmware lines identifying boot, BRAM success, identifier CSR
  success, timer success, and final success. Failure paths print a distinct FAIL
  line and stop; success is emitted only after all comparisons succeed.
- Prefer a software-written diagnostic/status CSR with final signature and
  stage code, or a reserved RAM result structure with a symbol in the ELF map.
  This complements the independently decoded UART stream.
- Provide generated top module/port names, CPU variant, source list, all memory
  initialization filenames, firmware ELF/bin, generated csr.h/csr.csv and map.

## Firmware checks

Use a volatile scratch array in BRAM away from stack and executable storage.
Write and read address-derived patterns and their inverses across at least 256
words. Include byte and halfword stores and verify unchanged neighboring bytes;
include first and last scratch words to catch aliasing. Volatile readback must
drive branches to explicit failure markers, rather than merely calculating an
unused checksum. Keep ROM startup and initialized-data/BSS checks if the linker
uses those sections.

Read the actual generated identifier CSR and compare a fixed identifier or its
expected byte sequence. Program timer load/reload/enable registers, sample its
value twice and require progress, then observe zero/event pending and acknowledge
the event. If the CPU variant supports interrupts, additionally install a trap
handler, enable the timer interrupt, require one incremented ISR counter and
return to main. An unexpected trap records mcause/mepc and enters the failure
path. Polling alone must be labeled polling coverage, not interrupt coverage.

## Testbench checks

Decode UART from the actual serial pin at the bit centers, including start and
stop validity, and compare the complete expected ordered byte sequence. Fail
on unknown TX after reset, framing errors, explicit firmware failures, missing
stages or premature final success. Require success plus the final status/RAM
signature if the generated design exposes one. Assert every claimed unused
board output against its specified safe value throughout reset and operation.

Provide an absolute cycle timeout (initial recommendation 2,000,000 cycles at
50 MHz) and a progress timeout long enough for the maximum UART gap and memory
test. On timeout report the last decoded byte/stage, cycle, and accessible CPU
PC/bus status. Internal bus observations are diagnostics; UART/status evidence
determines success. A trap handler catches unexpected traps, while the watchdog
catches missing startup or firmware stalls.

## Runner and evidence

Run in a new output directory, stage exact init files with unchanged basenames,
and record SHA-256 for every RTL/init/firmware/testbench input. Record executable
paths and version strings, compile command/exit, simulation command/exit, full
logs, cycle/stage/UART counts and final outcome in JSON. Bound subprocess wall
time as well as HDL cycles. Missing inputs, failed compile, nonzero simulator
exit, timeout, or absent required success marker must return failure.

Add meaningful negative controls using an isolated copied source set: corrupt a
firmware ROM instruction to prevent boot, and corrupt an expected result or
exercise a testbench timeout. Each must fail without altering production RTL or
Phase 1 artifacts. These controls validate detection, not the CPU functionality.

## Prior workspace patterns inspected

`poc/run_rom_only_soc_sim.ps1` compiles real VexRiscv and generated LiteX sources
and runs from the directory containing matching ROM init files.
`poc/litex/gfx_bus_smoke.S` demonstrates CPU-accepted BRAM store/read comparison,
but shares a terminal signature on both success and failure; this new test must
use distinct outcomes. `tools/run_sim.py` in this workspace already establishes
new-directory evidence, source hashes, and explicit required PASS marker checks.

This phase provides BRAM, CPU execution, CSR/timer and safe-output simulation
evidence. It does not establish external memory, LCD scanout, physical timing,
board behavior, or hardware programming.
