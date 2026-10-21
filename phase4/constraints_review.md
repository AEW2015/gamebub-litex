# Rev4 phase4 physical-interface constraints review

Reviewed 2026-10-21. This is a source and tool-capability review, not routed or
hardware timing evidence. The intended domains are sys=50 MHz, service=200 MHz,
and video=29,357,798.1651 Hz (800 MHz / 27.25). Phase3 remains frozen; physical adaptation belongs in
the phase4 wrapper/platform. No hardware or AMD tools were accessed for this review.

## Tool constraint coverage and evidence limits

The installed nextpnr revision is
`e7a6fb0e708ecac22c917ec70fc4cb3d47b5d2b5`. Its
[Xilinx XDC parser](https://github.com/YosysHQ/nextpnr/blob/e7a6fb0e708ecac22c917ec70fc4cb3d47b5d2b5/himbaechel/uarch/xilinx/xdc.cc)
handles `set_property`, `create_clock`, and limited destination-tagging
`set_multicycle_path`. Other commands issue ignored/unsupported warnings.
`create_clock` supports a period and concrete port/net targets; `-name`,
`-waveform`, `-add`, and virtual clocks are explicitly unsupported. A selector
that matches nothing can leave the domain at its default target, so each expected
domain must appear with the correct constraint in the final report.

| Constraint intent | Pinned tool result | Phase4 treatment |
|---|---|---|
| Pin location and LVCMOS33 | Supported set_property path | Generate explicit assignments from official Rev4 pins |
| Concrete clock period | Supported create_clock -period | Constrain oscillator and actual internal clock nets, without duplicate constraints |
| Generated clock waveform/phase | create_generated_clock unsupported | Preserve phase in actual primitives; review clock graph and report limitation |
| External input/output delay | set_input_delay/set_output_delay unsupported | Keep external timing budgets in this review; do not claim pin timing signoff |
| Async clock grouping or false paths | XDC commands unsupported | Add no blanket exceptions |
| Setup/hold uncertainty, bus skew, datapath bounds | Unsupported XDC commands | Report absent coverage explicitly |
| Multicycle relaxation | Limited destination setup tags; hold form supplies no setup tag | Do not reuse legacy SRAM SERDES exceptions for this new FSM |

The generic `--sdc` interface does not solve this gap. Its
[parser](https://github.com/YosysHQ/nextpnr/blob/e7a6fb0e708ecac22c917ec70fc4cb3d47b5d2b5/common/kernel/sdc.cc)
accepts a narrow clock/selector subset, and its `set_false_path` implementation
explicitly warns that it does nothing. External delay commands are unsupported.

The exact part name does not select a qualified speed-grade timing corner:
[Xilinx initialization](https://github.com/YosysHQ/nextpnr/blob/e7a6fb0e708ecac22c917ec70fc4cb3d47b5d2b5/himbaechel/uarch/xilinx/xilinx.cc)
calls `set_speed_grade("DEFAULT")`. This version also has internal minimum-delay
analysis and an optional `-o hold-fix` repair pass; those are useful diagnostics,
not evidence of complete -1/PVT or external setup/hold signoff. Preserve all
reported minimum-delay failures and any repairs; do not suppress them with
`--timing-allow-fail`, `--ignore-rel-clk`, or blanket timing exceptions.

The platform should emit its concrete clock declarations in its own final XDC.
Expected periods are 20.000 ns, 5.000 ns, and 34.0625 ns. Which clock nets
need explicit declarations depends on MMCM propagation in the final packed
netlist: inspect actual targets and avoid declaring the same net twice. The
global `--freq 50` fallback cannot establish a 200 MHz service requirement.

No supplemental active `board_timing.xdc` is supplied: the board pin mapping and
clock net names are owned by the physical platform, and the missing external
timing commands cannot be made effective by putting them in a second file.

## Clock forwarding at the physical wrapper

Phase3 SDRAM drives `pads.clk = ~sys`; phase3 video drives `dotclk = video`.
Those describe the required waveform but should not become LUT-routed clock
outputs in hardware. A phase4 wrapper should consume those child output wires
internally and drive each actual board clock pin through one dedicated ODDR.
Do not connect the child clock wire and the ODDR output to the same board net.

```verilog
// External SDRAM rising edge remains halfway between sys rising edges.
ODDR #(.DDR_CLK_EDGE("SAME_EDGE"), .INIT(1'b0), .SRTYPE("SYNC"))
  sdram_clock_forwarder(.Q(sdram_clk), .C(sys_clk), .CE(1'b1),
    .D1(1'b0), .D2(1'b1), .R(1'b0), .S(1'b0));

// Preserve the phase3 LCD polarity and the known-good physical app.
ODDR #(.DDR_CLK_EDGE("SAME_EDGE"), .INIT(1'b0), .SRTYPE("SYNC"))
  lcd_clock_forwarder(.Q(lcd_dotclk), .C(video_clk), .CE(1'b1),
    .D1(1'b1), .D2(1'b0), .R(1'b0), .S(1'b0));
```

Keep CE permanently asserted; inhibit commands/pixel data through reset rather
than combinationally gating clocks. Assert resets while MMCM lock is absent and
release each reset synchronously to its own running clock. Use the ODDR reset
policy consistently with the power-up model and repeat exact-wrapper simulation.
Check packed cells and routes actually use OLOGIC/ODDR clock forwarding; an RTL
instance name alone does not prove the intended physical implementation.

## SDRAM at sys50

The unchanged GENSDRPHY registers SDR command/address/write data and captures
read data at sys rising edges. Inverted forwarding gives a nominal 10 ns
launch-to-memory-sample interval. CL2 read outputs begin after the following
SDRAM edge and are sampled at the next sys rising edge. The independent model
uses a conservative 6 ns clock-to-data delay, leaving only 4 ns of the nominal
half-cycle for return trace/FPGA input route/setup plus clock skew and jitter.
That 4 ns is a simulation budget, not measured board slack.

For pin-level setup, the outgoing half-cycle must exceed FPGA command/data
clock-to-pad + board trace skew + SDRAM setup + clock uncertainty. Incoming read
setup must satisfy `10 ns > SDRAM tAC + return flight + FPGA pin-to-capture setup
path + relative clock uncertainty`. Minimum delays must separately satisfy hold;
the pin model does not qualify FPGA input hold, output hold or bus turnarounds
across voltage/temperature. Obtain the actual populated chip grade/BOM before
substituting datasheet numbers. The current MT48LC16M16 timing profile is a
compatible geometry profile, not a confirmed physical part marking.

The board interface uses A[12:0], BA[1:0], DQ[15:0], DM[1:0]. Selected rank zero
uses CS_n[0], CKE[0]; CS_n[1] remains high and CKE[1] remains high, matching the
known-good v1.6 command formatter. Preserve those constants. Use real bidirectional
I/O cells and inspect output-enable timing/ownership. Generic PHY flops becoming
fabric registers rather than I/O registers must be visible in the route review;
do not assume IOB packing from the functional model.

## Asynchronous SRAM at sys50

The new bridge has 40 ns setup, an 80 ns access pulse, 40 ns hold and a 20 ns
turnaround cycle per 16-bit halfword. It samples read DQ at the end of ACCESS.
The official interface is A[17:0], DQ[15:0], CE_n, WE_n, OE_n, LB_n and UB_n.
The tested byte masks and both halfword addresses must retain these mappings.

The legacy hardware `sram_timing.tcl` uses a 32 ns external read envelope, but its
100/400 MHz SERDES clocks and 32/31-cycle setup/hold exceptions are specific to
another controller. They cannot be copied into this 50 MHz FSM. The new read
budget is the actual address/CE/OE launch-to-sample interval minus output route,
SRAM tAA/tACE/tOE, board round trip and input setup. Write validation must bound
WE pulse width, address/data setup to WE deassertion, data hold, and CE/OE/byte
mask transitions. State-decode controls are combinational in phase3, so review
their routed glitches and output timing; no assertion of fully registered SRAM
pad controls is made. Any added physical output pipeline changes the pin-level
schedule and must be tested with the exact wrapper before use.

## LCD at video29.361979 MHz

The known-good physical app registers 27 LCD output bits at the pixel rising
edge and forwards a same-polarity ODDR clock. Its receiver constraints use the
forwarded falling edge with `-max 4 ns`, `-min -1 ns`. This is a historical
board design budget, not an independently verified panel datasheet limit.
Phase3 video likewise registers the output signals on video rising edges, so
preserving ODDR polarity supplies a nominal 17.0288 ns launch-to-panel falling
edge interval. Preserve the same native 480x800 scanout and 605x809 profile;
physical output data must match the frozen exact-RTL simulation.

For a future timing engine with the required support, define the forwarded LCD
generated clock and check every RGB/HSYNC/VSYNC/DE output against the falling
receiver edge with the confirmed panel setup/hold plus board skew. The legacy
wildcard omitted an explicit DE match; include DE in this design's review.
Do not claim external LCD timing from the internal video fmax alone.

## ESP32 QSPI and CDC

The actual endpoint oversamples SCK, CS_n and incoming DQ through two-stage
service200 synchronizers. SCK is an asynchronous input signal to that logic,
not an FPGA clock driving protocol flops. Do not add a fake 40 MHz FPGA domain
to make those paths appear source-synchronous. Review the first-stage placement,
ASYNC_REG preservation, metastability recovery stages, and the stability window
between synchronized SCK edges and synchronized multi-bit DQ.

Digital simulation covers writes up to 40 MHz and reads up to 16 MHz; it does
not establish board margins. A 16 MHz read half-cycle is 31.25 ns. The read
budget must include asynchronous phase uncertainty, two-stage SCK capture,
edge detection/data-update latency, output route, flight time, and ESP32 setup.
Any higher physical read rate needs its own evidence. Raw CS_n immediately
releases DQ output ownership; review and measure that asynchronous disable path
and ensure the ESP32 and FPGA never drive opposite directions simultaneously.
Do not pipeline raw-CS release in a way that changes this ownership guarantee.

sys/service/video can share a reference oscillator yet contain CDC protocols.
Inspect each actual crossing: synchronized buttons/flags, event toggles and
stable payload mailboxes, Gray/FIFO pointers, overlay memory ownership and reset
release. Keep related clock paths visible. A reported failure may identify a
real unregistered crossing; no clock-group or global false-path waiver is
justified by the fact that a FIFO exists elsewhere in the design. This pinned
flow cannot express all required CDC datapath/skew bounds, which remains an
explicit qualification gap.

## Source identities reviewed

Paths below are relative to `D:/codex_archive_2026/gamebub/gamebub-source/fpga`
unless qualified. These bindings distinguish source evidence from physical proof.

| Source | SHA256 |
|---|---|
| verilog/handheld/rev_4.xdc | af2d5b6e9a157ed9636330cc1105180bd4bc7384e8c67d622119944b923953b8 |
| vivado/gamebub_combined_av/timing_post.tcl | 76798ec68a4c80d84c5054f5059fc77f27426a05820881090635ba8848a94a40 |
| vivado/gamebub_combined_av/sram_timing.tcl | e8f977872caf2266db152a305c8291b36ee974067649b33732e06b3f44949adc |
| vivado/gamebub_combined_av/rtl/lcd_apps_top.sv | 10ac6b85f4cf30fd0e0982323883ec56a5aab53368bc19e14e5949f35f384de5 |
| gamebub-litex/phase3/memory/controllers.py | 4ba653a7381e76e71ebabf250ba1eeb44a49ae07b3f038ca672b559f949b7e4a |
| gamebub-litex/phase3/video/video.py | 0d7e6d5b873932c712d691c45a2a576e3d1c036ae7217336dc258db93a67c228 |

No phase3 source was changed. Board pin ownership remains with the phase4
platform. This review supports an explicitly experimental physical build and
subsequent authorized observation; it does not establish a hardware-qualified
release, positive external timing slack, or complete hold/PVT signoff.
