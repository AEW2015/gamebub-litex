<!-- SPDX-License-Identifier: 0BSD -->

# LiteX USER1 JTAG-UART post-program monitor

`read_jtag_uart.tcl` is a prepared XSDB helper for a later post-program smoke
check. It has **not** been executed against hardware. Do not run it until the
root build has passed its gates, programmed the approved image through Vivado,
and released the Vivado hardware target. No build, programming, or persistent
flash operation is performed by this helper.

## Target guard and XSDB use

The helper connects to the already-running local Xilinx `hw_server` at
`tcp:localhost:3121`; it does not start or stop Vivado or `hw_server`. It first
filters JTAG target properties to the exact Digilent HS2 serial
provided by `GAMEBUB_JTAG_SERIAL`, then requires exactly one XC7A100T FPGA child with IDCODE
`13631093`. Server metadata showed that `hw_server` auto-opens the cable;
`is_open` does not identify another client's ownership. The helper preserves
that state and acquires the documented `jtag lock 1000` on the selected chain
before scanning. If the lock is unavailable within one second, it stops. It
opens only that cable if necessary, releases its lock, and closes the cable
only if this invocation opened it. Run after the programming client releases
its hardware target.

From the 2025.2 XSDB shell, after the stated release condition:

```tcl
source D:/codex_archive_2026/gamebub-litex/phase4/loader/read_jtag_uart.tcl
```

The helper reads and restores the existing JTAG frequency, temporarily uses
1 MHz, and restores the prior value during cleanup. It leaves the TAP in
`IDLE` after IR/DR scans; it does not issue TAP reset or a configuration/flash
instruction. It disconnects its XSDB client when done but does not terminate
`hw_server`.

## LiteX JTAGPHY contract

The installed pinned LiteX package is version `2024.12`. Its local source is
`/opt/gamebub-litex-20261021/venv/lib/python3.10/site-packages/litex/soc/cores/jtag.py`,
SHA-256 `740ccee0d90f9540013d9ae05ebc430ab47ff7833b65dd372052ca6a45d98dde`.
`JTAGPHY` documents a 10-bit, LSB-first frame for its default 8-bit data width:

| Bit(s) | TDI: host to FPGA | TDO: FPGA to host |
| --- | --- | --- |
| 0 | `1` means host is ready to accept target output | target's stream-ready status |
| 1–8 | zero/don't-care for this read-only drain | output data byte, least-significant bit first |
| 9 | `0`: no host-to-target byte is being submitted | `1` if output data is valid |

`read_jtag_uart.tcl` selects the 6-bit USER1 instruction (`0x02`), shifts
10-bit frames, records only frames whose captured TDO bit 9 is valid, and
stops after four idle frames once output has begun (512-frame safety maximum,
with 5 ms waits on idle reads).
Its TDI ready bit consumes queued UART output; this is intentionally a FIFO
drain, not a passive non-consuming peek. It does not send application data,
change CPU registers, or write FPGA configuration/flash.

The script reports each valid byte and a final byte count, hex string, and
printable ASCII rendering (tabs/newlines are escaped). It requires the seven
consecutive bytes `GB4_OK\n` somewhere in the captured stream; the expected
hex is `4742345F4F4B0A`. It emits `JTAGUART_SMOKE_PASS` only on a match and
returns a Tcl error if the payload is absent. Preserve the XSDB console log
alongside the programming evidence.

## Evidence limits

No local XSDB command sequence in this file has been run against hardware, and
the helper is not a replacement for the verified Vivado-only programming
path. It proves a CPU-emitted message only when the integrated RTL contains
the LiteX JTAGPHY/JTAG-UART connection and the captured bytes match the
expected smoke message. Target identity, FPGA DONE/CRC/USERCODE and bitstream
hash remain separate programming evidence.

The firmware repeats its nonblocking success message every 60 display frames.
This allows late attachment and recovery if Vivado's automatic USER1 debug
discovery consumed queued bytes. The short exact-RTL test exercises initial
completion, not a full second of repeated UART delivery; record any successful
hardware capture separately.

The file passed a Tcl completeness/syntax check with the installed MSYS2 Tcl
interpreter (`info complete` returned `1`); this does not execute XSDB
commands or validate a hardware transaction. The command and sequence API
were reviewed from the installed Vivado 2025.2
XSDB Tcl sources:
`C:/Xilinx/2025.2/Vivado/scripts/xsdb/xsdb/jtag.tcl` and
`jtag_sequence.tcl`. The LiteX bit layout was checked against the installed
LiteX 2024.12 source noted above. No vendor RTL or tool scripts are copied into
this project.
