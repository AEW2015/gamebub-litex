# SPDX-License-Identifier: 0BSD
"""Audit this GameBub target's button pull-ups and fixed MMCM FASM fields."""
import re
import csv
import sys
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone

BUTTON_PADS = ("L6", "K6", "M6", "N5", "N16", "L13", "L14", "M16", "K13", "K5", "H6", "H5")
EXPECTED_MMCM = {
    "IN_USE": 1, "ZINV_PWRDWN": 1,
    "DIVCLK_DIVCLK_HIGH_TIME[5:0]": 1,
    "DIVCLK_DIVCLK_LOW_TIME[5:0]": 1,
    "DIVCLK_DIVCLK_NO_COUNT[0]": 1,
    "CLKFBOUT_CLKOUT1_OUTPUT_ENABLE[0]": 1,
    "CLKFBOUT_CLKOUT1_HIGH_TIME[5:0]": 8,
    "CLKFBOUT_CLKOUT1_LOW_TIME[5:0]": 8,
    "CLKOUT0_CLKOUT1_OUTPUT_ENABLE[0]": 1,
    "CLKOUT0_CLKOUT1_HIGH_TIME[5:0]": 13,
    "CLKOUT0_CLKOUT1_LOW_TIME[5:0]": 13,
    "CLKOUT0_CLKOUT1_PHASE_MUX[2:0]": 0,
    "CLKOUT0_CLKOUT2_EDGE[0]": 1,
    "CLKOUT0_CLKOUT2_NO_COUNT[0]": 0,
    "CLKOUT0_CLKOUT2_DELAY_TIME[5:0]": 0,
    "CLKOUT0_CLKOUT2_FRAC_EN[0]": 1,
    "CLKOUT0_CLKOUT2_FRAC[2:0]": 2,
    "CLKOUT0_CLKOUT2_FRAC_WF_R[0]": 0,
    "CLKOUT5_CLKOUT2_FRACTIONAL_FRAC_WF_F[0]": 0,
    "CLKOUT5_CLKOUT2_FRACTIONAL_PHASE_MUX_F[2:0]": 5,
    "CLKOUT1_CLKOUT1_OUTPUT_ENABLE[0]": 1,
    "CLKOUT1_CLKOUT1_HIGH_TIME[5:0]": 8,
    "CLKOUT1_CLKOUT1_LOW_TIME[5:0]": 8,
    "CLKOUT2_CLKOUT1_OUTPUT_ENABLE[0]": 1,
    "CLKOUT2_CLKOUT1_HIGH_TIME[5:0]": 2,
    "CLKOUT2_CLKOUT1_LOW_TIME[5:0]": 2,
    "POWER_REG_POWER_REG_POWER_REG[15:0]": 0x9900,
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fasm", type=Path, required=True)
    p.add_argument("--pins", type=Path, required=True)
    p.add_argument("--package-db", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    output = a.output.resolve()
    if output.exists(): p.error("refusing to replace an existing audit")
    result = dict(result="FAIL", timestamp_utc=datetime.now(timezone.utc).isoformat(),
                  command=[sys.executable, *sys.argv], python_version=sys.version,
                  script=dict(path=str(Path(__file__).resolve()), sha256=digest(Path(__file__))),
                  inputs=[], buttons=[], mmcm={}, failures=[])
    try:
        for role, path in (("fasm", a.fasm), ("pin_manifest", a.pins), ("package_database", a.package_db)):
            result["inputs"].append(dict(role=role, path=str(path.resolve()), sha256=digest(path)))
        lines = [line.strip() for line in a.fasm.read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")]
        fields = {}
        for line in lines:
            name, separator, value = line.partition(" = ")
            if separator:
                match = re.fullmatch(r"(\d+)'b([01]+)", value)
                if not match: raise ValueError(f"unexpected FASM value: {line}")
                fields[name] = int(match.group(2), 2)
            else:
                fields[name] = 1
        with a.package_db.open(newline="") as stream:
            database = {row["pin"]: row for row in csv.DictReader(stream)}
        pin_manifest = {item["port"]: item for item in json.loads(a.pins.read_text())}
        expected_pullups = set()
        for index, expected_pad in enumerate(BUTTON_PADS):
            port = f"buttons_n[{index}]"
            actual_pad = pin_manifest[port]["package_pin"]
            if actual_pad != expected_pad:
                result["failures"].append(f"{port}: pad {actual_pad}, expected {expected_pad}")
            row = database[actual_pad]
            # XC7A100T-CSG324 IOB_Y0/Y1 names alternate with absolute site Y;
            # the package's single-IOB tile retains its physical slot index.
            slot = int(row["site"].split("Y")[1]) % 2
            feature = f"{row['tile']}.IOB_Y{slot}.PULLTYPE.PULLUP"
            expected_pullups.add(feature)
            present = fields.get(feature, 0) == 1
            result["buttons"].append(dict(port=port, package_pin=actual_pad,
                site=row["site"], tile=row["tile"], feature=feature, present=present))
            if not present: result["failures"].append(f"missing pull-up: {port} {feature}")
        actual_pullups = {name for name, value in fields.items() if name.endswith(".PULLTYPE.PULLUP") and value}
        result["unexpected_pullups"] = sorted(actual_pullups - expected_pullups)
        if result["unexpected_pullups"]: result["failures"].append("unexpected additional pull-ups")
        prefixes = [name.removesuffix(".IN_USE") for name, value in fields.items() if name.endswith(".MMCME2_ADV.IN_USE") and value]
        if len(prefixes) != 1: raise ValueError(f"expected one active MMCM, found {len(prefixes)}")
        prefix = prefixes[0]
        result["mmcm"]["prefix"] = prefix
        result["mmcm"]["checks"] = []
        for name, expected in EXPECTED_MMCM.items():
            key = prefix + "." + name
            actual = fields.get(key, 0)
            result["mmcm"]["checks"].append(dict(field=name, expected=expected,
                actual=actual, explicitly_present=key in fields, passed=actual == expected))
            if actual != expected: result["failures"].append(f"MMCM {name}: {actual}, expected {expected}")
        result["mmcm"]["all_emitted_fields"] = {name[len(prefix)+1:]: value for name, value in fields.items() if name.startswith(prefix + ".")}
        result["mmcm"]["interpretation"] = dict(input_hz=50_000_000,
            vco_hz=800_000_000, sys_hz=50_000_000, service_hz=200_000_000,
            video_hz=800_000_000/27.25, video_divider=27.25,
            fractional_eighths=2, fractional_phase_mux_f=5,
            fractional_waveform_r=0, fractional_waveform_f=0,
            power_register_hex="0x9900")
        result["scope"] = "FASM configuration audit only; does not establish electrical timing, analog lock, or board operation"
        result["result"] = "PASS" if not result["failures"] else "FAIL"
    except (OSError, ValueError, KeyError) as exc:
        result["failures"].append(str(exc))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["result"], output)
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
