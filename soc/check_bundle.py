# SPDX-License-Identifier: 0BSD
"""Check ROM/source identity across generation, simulation and physical build."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--simulation", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must not already exist")
    checks = []
    generation = json.loads((args.generated / "generation.json").read_text())
    simulation = json.loads((args.simulation / "evidence.json").read_text())
    build = json.loads((args.build / "evidence.json").read_text())
    assert simulation["result"] == "PASS", "CPU simulation did not pass"
    assert build["build_status"] == "PASS", "open-source build did not pass"
    checks += ["CPU simulation PASS", "open-source build PASS"]
    gateware = args.generated / "gateware"
    frozen = {}
    for path in sorted(gateware.iterdir()):
        if path.suffix not in (".v", ".init"):
            continue
        value = digest(path)
        assert digest(args.simulation / "inputs" / path.name) == value, path.name
        assert digest(args.build / path.name) == value, path.name
        frozen[path.name] = value
    checks.append("identical generated/simulated/synthesized RTL and initialization")
    assert digest(args.generated / "gamebub_soc.xdc") == digest(args.build / "soc_constraints.xdc")
    for filename in ("diagnostic.elf", "diagnostic.bin"):
        staged = "firmware.elf" if filename.endswith("elf") else "firmware.bin"
        assert digest(args.generated / "firmware" / filename) == digest(args.simulation / "inputs" / staged)
    words = [int(line, 16) for line in (gateware / "gamebub_soc_rom.init").read_text().splitlines()]
    rom = b"".join(word.to_bytes(4, "little") for word in words)
    binary = (args.generated / "firmware/diagnostic.bin").read_bytes()
    assert len(rom) == 16384 and rom[:len(binary)] == binary
    assert not any(rom[len(binary):]), "nonzero bytes outside linked firmware"
    checks.append("compiled binary exactly embedded in 16KiB ROM with zero padding")

    # Check the new constraint subset independently against the frozen probe
    # assignments; UART is the only intentional additional pin assignment.
    root = Path(__file__).resolve().parents[1]
    def pins(path):
        return dict(re.findall(r"set_property PACKAGE_PIN (\S+) \[get_ports \{([^}]+)\}\]", path.read_text()))
    expected = pins(root / "constraints/rev4_probe.xdc")
    expected["P17"] = "clk50"
    expected.update(V14="serial_tx", U14="serial_rx")
    actual = pins(args.generated / "gamebub_soc.xdc")
    assert actual == expected, "constraint pin subset mismatch"
    assert len(actual) == 64 and len(set(actual.values())) == 64
    checks.append("all 64 requested pins match reviewed Rev4 subset plus opt-in PMOD UART")
    prior = json.loads((root / "HANDOFF.json").read_text())
    for entry in prior["artifacts"]:
        assert digest(root / entry["path"]) == entry["sha256"], entry["path"]
    checks.append(f"all {len(prior['artifacts'])} Phase1 handoff hashes preserved")
    evidence = {"result": "PASS", "checks": checks, "hardware_programmed": False,
                "generation_evidence_sha256": digest(args.generated / "generation.json"),
                "simulation_evidence_sha256": digest(args.simulation / "evidence.json"),
                "build_evidence_sha256": digest(args.build / "evidence.json"),
                "frozen_rtl_init": frozen, "firmware_bytes": generation["firmware_bytes"],
                "bitstream_sha256": digest(args.build / "gamebub_soc.bit")}
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    print("PASS: " + "; ".join(checks))


if __name__ == "__main__":
    main()
