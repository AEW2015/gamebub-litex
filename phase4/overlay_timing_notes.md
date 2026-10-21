# Phase4 overlay BRAM write pipeline

`esp32_service.py` is a phase4 copy of frozen `phase3/esp32/service.py`.
The endpoint source path now resolves naturally to phase4's `rtl/` directory.
The interface, diagnostic CDC and video read path retain their original behavior;
phase3 sources and the already staged endpoint RTL are unchanged.

Routed build4 removed the endpoint control critical path but exposed a separate
200 MHz write-data path from endpoint `ov_data[2]` through luma arithmetic to
overlay BRAM `memory.0.3.DIADI0`, measuring 5.36 ns / 186.43 MHz. This path
requires a real pipeline; no timing constraint or exception was relaxed.

The overlay write conversion now has two full-throughput register stages:

1. Capture 7-bit `2R+B` (maximum93), 8-bit `5G` (maximum155), alpha, 17-bit pixel
   address, and valid with the original even-address and bounds checks.
2. Capture `sum>=128` and alpha as the two-bit pixel, together with the delayed
   address and valid. Total luma is at most248 and fits eight bits exactly.

The memory write port receives only stage2 register values. Each stage advances
every service clock and accepts a valid pulse every cycle; there is no edge-only
capture, FIFO capacity or backpressure that can drop consecutive writes. The
write address, alpha, threshold result and enable stay aligned. The final pulse
drains through both stages before reaching BRAM. The synchronous video read port,
rotated address mapping, requested flag and one-cycle look-ahead remain unchanged.

An independent Migen simulation instantiates both original and phase4 readers,
drives the same input stream, and compares all requested pixels after pipeline
drain. The stream includes every ARGB1555 value at luma127 or128 (both alpha
values),256 further deterministic values, and the final valid framebuffer pixel.
All1077 valid writes are consecutive, one per service cycle. An odd address and
the first out-of-bounds address follow immediately and must not corrupt memory.
All1077 resulting pixels and opacity values agree with the frozen reference;
video latency and disabled-display valid behavior also agree.

Evidence and its standalone script are preserved at
`D:/xup_2026/bub/gamebub-phase4-overlay-pipeline1/evidence.json` and `run.py`.
Run the script with the pinned Linux venv; it uses only Migen source simulation,
not foreign RTL or hardware. The parent target separately regenerates the exact
combined physical RTL, repeats CPU/pin tests, and checks final routed200MHz timing.
This source-level differential result alone is not a routed timing or hardware
qualification result.

| Bound source | SHA256 |
|---|---|
| Frozen phase3 service.py | 3ce4699cd3c2753318f4f289ade8ced0d973384be209bd0dd67c2b60f251e61e |
| Phase4 esp32_service.py | 149ded596a18eb588af95e8f38740778e1e00b27f51e676f335f1454167c599b |
| Standalone differential script | 2a16c1b74e2478abfa21c32caa353a868ef9a1cef59cd7f6f040548973c04391 |
