#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Generate complete Rev4 pinout documentation without changing gateware."""

import io
import re
import csv
import sys
import hashlib
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "gamebub/reference/rev_4.xdc"
REFERENCE_SHA = "af2d5b6e9a157ed9636330cc1105180bd4bc7384e8c67d622119944b923953b8"
UPSTREAM = "https://github.com/elipsitz/gamebub/blob/v1.0.2/fpga/verilog/handheld/rev_4.xdc"
BUTTONS = ("a", "b", "x", "y", "up", "down", "left", "right", "l", "r", "start", "select")
SAFE = {"cart_oe_n": 1, **{f"cart_bank{i}_dir": 0 for i in range(4)},
        "cart_pin30_dir": 0, "cart_pin31_dir": 0,
        **{f"link_{name}_dir": 0 for name in ("so", "si", "sd", "sc")}}
GROUPS = (
    ("Clock", "50 MHz oscillator input; clock generation is internal to the tester."),
    ("Buttons", "Pressed-low FPGA buttons with pull-ups. Bit order follows buttons_n[0..11]. "
     "Power, volume and the ESP32 menu button are not extra FPGA button GPIOs."),
    ("ESP32", "ESP32 is QSPI master; FPGA is slave. esp_irq_gate drives the external IRQ gate "
     "and resets low; do not infer pad polarity from the original mcu_irq_n name alone."),
    ("LCD", "Native RGB888 scanout. Panel setup and backlight remain ESP32-owned; "
     "there is no invented FPGA backlight/reset GPIO."),
    ("Audio", "DSP serial audio, not a claim of generic I2S framing. Clocks continue running "
     "while PCM is muted. ESP32 configures DAC volume/routing over its own control bus."),
    ("Vibration", "IN1 carries bounded forward/coast PWM; IN2 is fixed low. Outputs start off."),
    ("SRAM", "512 KiB asynchronous x16 interface. CPU accesses are 32-bit Wishbone transactions."),
    ("SDRAM", "32 MiB SDR SDRAM, fixed 50 MHz. Rank zero is selected; second CS stays inactive. "
     "No dynamic high-speed/phase/tap tester is implied."),
    ("Cartridge", "No cartridge controller. OE is held high and direction controls low. "
     "Data and cart_switch are not LiteX resources; review the schematic and electrical requirements before use."),
    ("Link port", "No link controller. Direction controls are held low; data pins are not mapped."),
    ("HDMI", "TMDS_33, not LVCMOS33. No transmitter is implemented. The upstream XDC notes "
     "dock-related polarity reversal; this table preserves the original p/n assignments."),
    ("USB-C sideband", "These SBU signals are not a USB data PHY or SD-card interface. "
     "Connector sharing and board ownership need review before enabling them."),
    ("PMOD", "Four FPGA PMOD signals appear in this reference; no PMOD peripheral is implemented."),
    ("Test points", "Four named test-point signals; not configured by the tester."),
)


# Signal Metadata ---------------------------------------------------------------------------------

def describe(signal):
    """Return documented request name/flow without claiming unused pins are mapped."""
    scalar = {
        "clk_50mhz":   ("Clock", "clk50", "input"),
        "mcu_spi_clk": ("ESP32", "qspi.sck", "input"),
        "mcu_spi_cs_n": ("ESP32", "qspi.cs_n", "input"),
        "mcu_irq_n":   ("ESP32", "esp_irq_gate", "output"),
        "lcd_dotclk":  ("LCD", "lcd.dotclk", "output"),
        "lcd_data_en": ("LCD", "lcd.de", "output"),
        "lcd_hsync":   ("LCD", "lcd.hsync", "output"),
        "lcd_vsync":   ("LCD", "lcd.vsync", "output"),
        "sdram_clk":   ("SDRAM", "sdram.clk", "output"),
        "sdram_we_n":  ("SDRAM", "sdram.we_n", "output"),
        "sdram_ras_n": ("SDRAM", "sdram.ras_n", "output"),
        "sdram_cas_n": ("SDRAM", "sdram.cas_n", "output"),
        "sdram_ldqm":  ("SDRAM", "sdram.dm[0]", "output"),
        "sdram_udqm":  ("SDRAM", "sdram.dm[1]", "output"),
    }
    if signal in scalar:
        return (*scalar[signal], "tester")
    if signal.startswith("btn_") and signal[4:] in BUTTONS:
        return ("Buttons", f"buttons_n[{BUTTONS.index(signal[4:])}]", "input", "tester")
    if signal.startswith("dac_"):
        return ("Audio", signal, "output", "tester")
    if signal.startswith("vibrate_"):
        return ("Vibration", signal, "output", "tester")
    if signal in SAFE:
        group = "Cartridge" if signal.startswith("cart_") else "Link port"
        return (group, signal, "output", f"held {SAFE[signal]}")

    vectors = (
        (r"lcd_data_([rgb])\[(\d+)\]", "LCD", lambda m: f"lcd.{m[1]}[{m[2]}]", "output"),
        (r"mcu_spi_d\[(\d+)\]", "ESP32", lambda m: f"qspi.dq[{m[1]}]", "inout"),
        (r"sram_a\[(\d+)\]", "SRAM", lambda m: f"sram.a[{m[1]}]", "output"),
        (r"sram_io\[(\d+)\]", "SRAM", lambda m: f"sram.dq[{m[1]}]", "inout"),
        (r"sdram_a\[(\d+)\]", "SDRAM", lambda m: f"sdram.a[{m[1]}]", "output"),
        (r"sdram_bs\[(\d+)\]", "SDRAM", lambda m: f"sdram.ba[{m[1]}]", "output"),
        (r"sdram_dq\[(\d+)\]", "SDRAM", lambda m: f"sdram.dq[{m[1]}]", "inout"),
        (r"sdram_(cs_n|cke)\[(\d+)\]", "SDRAM", lambda m: f"sdram.{m[1]}[{m[2]}]", "output"),
    )
    for pattern, group, resource, direction in vectors:
        match = re.fullmatch(pattern, signal)
        if match:
            return (group, resource(match), direction, "tester")
    if signal.startswith("sram_"):
        return ("SRAM", "sram." + signal[5:], "output", "tester")
    for prefix, group in (("cart_", "Cartridge"), ("link_", "Link port"),
                          ("hdmi_", "HDMI"), ("usb_sbu_", "USB-C sideband"),
                          ("pmod[", "PMOD"), ("tp[", "Test points")):
        if signal.startswith(prefix):
            return (group, "", "not configured", "unmapped")
    raise ValueError(f"Document the new signal explicitly: {signal}")


def pin_rows():
    """Parse every constrained board signal, preserving the source bit order."""
    if hashlib.sha256(REFERENCE.read_bytes()).hexdigest() != REFERENCE_SHA:
        raise ValueError("Reference XDC hash changed; review the board revision before regenerating")
    pattern = r"PACKAGE_PIN\s+(\S+)\s+IOSTANDARD\s+(\S+)\s*\}\s*\[get_ports\s*\{\s*([^}]+?)\s*\}"
    rows = []
    for pad, standard, name in re.findall(pattern, REFERENCE.read_text(encoding="utf-8")):
        signal = name.strip()
        group, resource, direction, usage = describe(signal)
        rows.append(dict(group=group, signal=signal, package_pin=pad, iostandard=standard,
                         litex_resource=resource, fpga_direction=direction, tester_usage=usage))
    if len(rows) != 198 or len({row["package_pin"] for row in rows}) != len(rows):
        raise ValueError("Expected 198 unique package pins")
    if len({row["signal"] for row in rows}) != len(rows):
        raise ValueError("Duplicate signal name")
    return rows


def render_markdown(rows):
    mapped = sum(bool(row["litex_resource"]) for row in rows)
    lines = [
        "<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->", "", "# GameBub Rev4 LiteX pinout", "",
        f"All **{len(rows)} board signal pins** in the pinned Rev4 XDC: **{mapped} defined** by the",
        f"current LiteX platform and **{len(rows)-mapped} not mapped**. A defined pin may be held",
        "inactive rather than driven by a working peripheral. This document does not enable pins.", "",
        f"Source: [official GameBub v1.0.2 Rev4 constraints]({UPSTREAM}).",
        "The per-signal pin/standard tuples were checked against that upstream version.",
        "The byte-frozen local reference is [rev_4.xdc](../gamebub/reference/rev_4.xdc).", "",
        f"Reference SHA-256: `{REFERENCE_SHA}`.", "",
        "## Scope and safety", "",
        "- These are FPGA **package balls**, not connector pin numbers or I/O bank numbers.",
        "- This covers all named signals in the reference, not all 324 package contacts.",
        "  Power, ground, dedicated configuration/JTAG pins and unlisted nets are not inferred.",
        "- `tester` means connected to the current example; `held 0/1` means an inactive",
        "  control output; `unmapped` means no corresponding LiteX request exists yet.",
        "- Unmapped pins have **no tester-configured direction**. Their electrical default",
        "  pull/termination state is not guaranteed by this table.",
        "- LVCMOS33/TMDS_33 are the reference I/O standards, not permission to attach arbitrary",
        "  external voltages or treat a board-connected signal as general GPIO.",
        "- Cartridge/link electrical controls and shared USB-C/dock signals require schematic",
        "  review before adding controllers. No HDMI, USB PHY or cartridge operation is claimed.",
        "- The SD card and normal power/volume/menu functions remain ESP32-owned. No direct",
        "  FPGA SD-card, panel-backlight or ESP32 button GPIOs are invented here.", "",
        "## Reading the LiteX names", "",
        "A name such as `sram.dq[0]` means bit zero of the `dq` field returned by",
        '`platform.request("sram")`; `buttons_n[0]` is bit zero of `platform.request("buttons_n")`.',
        "The name `esp_irq_gate` deliberately differs from the original `mcu_irq_n` net.",
        "A dash in the LiteX column means the signal is documented but **not requestable**.", "",
        "## Interface summary", "",
        "| Interface | Signal pins | Defined by platform | Not mapped |",
        "| --- | ---: | ---: | ---: |",
    ]
    for group, _ in GROUPS:
        group_rows = [row for row in rows if row["group"] == group]
        count = sum(bool(row["litex_resource"]) for row in group_rows)
        lines.append(f"| {group} | {len(group_rows)} | {count} | {len(group_rows)-count} |")
    for group, note in GROUPS:
        lines.extend(["", f"## {group}", "", note, "",
                      "| Official signal | Package pin | I/O standard | LiteX request / field | FPGA flow | Tester use |",
                      "| --- | --- | --- | --- | --- | --- |"])
        for row in rows:
            if row["group"] == group:
                resource = f"`{row['litex_resource']}`" if row["litex_resource"] else "—"
                lines.append(f"| `{row['signal']}` | `{row['package_pin']}` | `{row['iostandard']}` | "
                             f"{resource} | {row['fpga_direction']} | {row['tester_usage']} |")
    lines.extend(["", "## Regeneration", "", "```bash", "python tools/pinout.py --write",
                  "python tools/pinout.py --check", "python tools/pinout.py --check --check-platform",
                  "```", "", "The last command additionally instantiates the LiteX platform and checks every",
                  "defined resource against `Platform.binding`; it needs the pinned Migen/LiteX environment.",
                  "The first two commands need only the Python standard library. [CSV export](pinout.csv).", ""])
    return "\n".join(lines)


def render_csv(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def check_platform(rows):
    sys.path.insert(0, str(ROOT))
    from gamebub.board import Platform

    expected = {}
    for row in rows:
        resource = row["litex_resource"]
        if not resource:
            continue
        match = re.fullmatch(r"(.+?)(?:\[(\d+)\])?", resource)
        key   = match[1].replace(".", "_")
        index = int(match[2] or 0)
        expected.setdefault(key, {})[index] = row["signal"]
    expected = {key: [bits[index] for index in sorted(bits)] for key, bits in expected.items()}
    platform = Platform()
    if expected != platform.binding:
        raise ValueError("Documented resources differ from the actual LiteX platform bindings")
    if SAFE.keys() - platform.safe.keys():
        raise ValueError("Documented inactive controls are not in the platform safe defaults")
    for name, value in SAFE.items():
        if platform.safe[name] != value:
            raise ValueError(f"Safe level changed: {name}")


# Run ---------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Regenerate Markdown/CSV documentation.")
    mode.add_argument("--check", action="store_true", help="Check generated documentation is current.")
    parser.add_argument("--check-platform", action="store_true", help="Also validate actual LiteX bindings.")
    args = parser.parse_args()
    rows = pin_rows()
    outputs = {ROOT / "docs/PINOUT.md": render_markdown(rows), ROOT / "docs/pinout.csv": render_csv(rows)}
    for path, text in outputs.items():
        if args.write:
            path.write_text(text, encoding="utf-8", newline="")
        elif not path.exists() or path.read_text(encoding="utf-8") != text:
            raise SystemExit(f"Pinout documentation is stale: {path.name}; run --write")
    if args.check_platform:
        check_platform(rows)
    print(f"PINOUT_PASS: {len(rows)} pins; {sum(bool(row['litex_resource']) for row in rows)} platform-defined")


if __name__ == "__main__":
    main()
