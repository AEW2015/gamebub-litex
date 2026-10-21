# Phase4 ESP32 endpoint timing variant

The physical endpoint variant is `rtl/esp32_v102_endpoint.sv`, SHA256
`0f544538c0ae027367450cfb6aae1953f0fe5d16f646206ba898411c21f542b8`.
It is derived from the frozen phase3 endpoint and retains the repository's
CERN-OHL-S-2.0 licensing and upstream attribution. Its bytes remain frozen while
the physical build is running; adding an SPDX header would require a new source
binding/build, so licensing is documented here and in the phase4 README.

The routed build2/build3 service-domain path measured 6.42 ns, limiting the
200 MHz domain to 155.76 MHz. The destination `$auto$ff.cc:337:slice$16531`
was traced through the synthesized JSON to `service_wr_pending`, an FDRE whose
Q is that named signal. The path started at `command[6]` and crossed lane decode,
counter-boundary and write-selection logic before reaching the pulse register's
synchronous reset input. This was a real setup failure, not an asynchronous CDC
exception or a valid candidate for a false/multicycle path.

The phase4-only variant continuously registers command lane/word configuration,
RX word-boundary and TX new-word predicates, address-region predicates, and the
general burst-address increment. One-/two-/four-lane shifts are explicit constant
concatenations rather than a variable barrel shifter. The byte/word counter
comparison and address decode therefore settle between serial edges rather than
forming the write-pulse reset cone on the consuming edge. Raw CS output-disable
behavior is preserved combinationally, and no FIFO, external clock rate, bus
protocol, or timing exception was changed.

The first timing variant had hash
`8169b2fdd233869ac57c14045e66e025e40c6bf2763697d68af8781bddbec65d`.
After removing that command/control cone and separately pipelining overlay
BRAM writes, routed build5 exposed a 5.90 ns address-decode path. Synthesized
JSON identifies `$auto$ff.cc:337:slice$16946` as `button_reads[0]`; its CE was
fed by the full `address==0xF1002000` comparison on a read-word boundary.
The current variant also continuously registers `address_is_buttons` and
`address_is_pending` (0xF1001004) and consumes those predicates at boundaries.
The address is stable long enough between serial word boundaries for this
predecode; no complete-address comparison remains on the consuming boundary.

At the tested 40 MHz write SCK, consecutive rising edges are nominally five
200 MHz service cycles apart. The command predecode and dependent boundary
predicate settle within two service cycles; the following address edge and each
word boundary retain the original serial schedule. This is a functional timing
relationship exercised in simulation, not a metastability or external-PVT
qualification. Read SCK remains limited to the tested 16 MHz envelope.

Reproduce the expanded regression under Linux with the phase2 Python venv:

```sh
python phase4/run_endpoint_timing.py --output /absolute/fresh/output
```

The runner stages the variant, the frozen phase3 endpoint, and
`tb_endpoint_timing.sv`. The reference transformation changes only the module
identifier to `esp32_v102_reference`; the original and derived hashes are both
recorded. It then compiles both endpoints with Verilator and compares driven DQ,
output ownership, service controls/counters, overlay write payload/address, and
mailbox write payload/address every service cycle. Explicit first-word expected
values additionally verify the service writes/reads rather than merely accepting
agreement between two nonfunctional implementations.

Coverage comprises all 36 combinations of lane widths 1/2/4, word sizes 8/16/32,
swap on/off, and burst/nonburst. Writes run at 40 MHz, reads at 16 MHz. Each
combination exercises service, overlay and mailbox writes plus service reads;
72 complete read words are checked. Twelve CS-abort cases cover incomplete
command, address and write data, and an active read for each lane width. Incomplete
writes must not commit. Raw-CS ownership release is checked after 0.5 ns.

The scratch precursor passed 72166 compared service cycles. The repository-based
rerun writes reproducible evidence to
`D:/xup_2026/bub/gamebub-phase4-endpoint-timing-final2/evidence.json`.
The original quad-only phase3 BFM also passes with this variant at 16 MHz:
`D:/xup_2026/bub/gamebub-phase4-endpoint2/evidence.json`.

This regression checks the implemented endpoint subset; it does not add complete
firmware ABI support or claim external-memory reads through unimplemented host
addresses. It is independent of the full CPU/panel pin simulation and the final
routed 200 MHz timing gate. Those must be reported separately, with the same
endpoint source hash. Placement-only improvement is not routed timing signoff.
