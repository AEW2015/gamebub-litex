# SPDX-License-Identifier: 0BSD
"""Bind CPU, peripheral comparisons and captured LCD frame to exact sources."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("generated", "combined", "video", "memory", "esp32", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), "choose a fresh audit output"
    results, hashes = {}, {}
    for name in ("combined", "video", "memory", "esp32"):
        path = getattr(args, name) / "evidence.json"
        result = json.loads(path.read_text())
        assert result.get("status", result.get("result")) == "PASS", name
        hashes[name] = sha(path)
        results[name] = "PASS"
    for path in (args.generated / "gateware").iterdir():
        if path.suffix in (".v", ".sv", ".init"):
            assert sha(path) == sha(args.combined / "inputs" / path.name), path.name
    for name in ("esp32_v102_endpoint.sv", "qspi_host_bfm.sv"):
        assert sha(args.combined / "inputs" / name) == sha(args.esp32 / "source" / name)
    binary = (args.generated / "firmware/diagnostic.bin").read_bytes()
    words = (args.generated / "gateware/gamebub_phase3_rom.init").read_text().splitlines()
    embedded = b"".join(int(word, 16).to_bytes(4, "little") for word in words)
    assert len(embedded) == 16384 and embedded[:len(binary)] == binary
    assert not any(embedded[len(binary):]), "unexpected ROM tail"
    for name in ("diagnostic.bin", "diagnostic.elf"):
        assert sha(args.generated / "firmware" / name) == sha(args.combined / "firmware" / name)
    generation = json.loads((args.generated / "generation.json").read_text())
    bound = {entry["path"]: entry["sha256"] for entry in generation["sources"]}
    core = ["integration/soc.py", "integration/main.c", "integration/generate.py",
            "video/video.py", "memory/controllers.py", "esp32/service.py"]
    for name in core:
        path = ROOT / "phase3" / name
        assert bound[str(path)] == sha(path), f"core source changed: {name}"
    results["exact_generated_rom_and_core_sources"] = "PASS"
    previous = {}
    for name in ("HANDOFF.json", "HANDOFF_PHASE2.json"):
        manifest = json.loads((ROOT / name).read_text())
        for entry in manifest["artifacts"]:
            assert sha(ROOT / entry["path"]) == entry["sha256"], entry["path"]
        previous[name] = len(manifest["artifacts"])
    results["previous_releases_unchanged"] = previous
    magic, geometry, maximum, pixels = (args.combined / "normal/combined.ppm").read_bytes().split(b"\n", 3)
    assert (magic, geometry, maximum) == (b"P6", b"480 800", b"255")
    assert len(pixels) == 480 * 800 * 3
    results["complete_native_lcd_capture"] = "PASS"
    compile_log = (args.combined / "compile.log").read_text()
    warnings = Counter(re.findall(r"%Warning-([A-Z0-9_]+):", compile_log))
    allowed = {"TIMESCALEMOD", "WIDTHEXPAND", "WIDTHTRUNC", "CASEINCOMPLETE", "COMBDLY"}
    assert not (set(warnings) - allowed), f"unreviewed warning classes: {set(warnings)-allowed}"
    assert "%Error" not in compile_log
    logs = {name: (args.combined / f"{name}.log").read_text()
            for name in ("normal", "corrupt_sram", "corrupt_sdram")}
    assert "COMBINED_PASS" in logs["normal"] and "QSPI_IRQ_OVERLAY_HOST_PASS" in logs["normal"]
    assert "status=bad30001" in logs["corrupt_sram"]
    assert "status=bad30002" in logs["corrupt_sdram"]
    evidence = {"status": "PASS", "hardware_programmed": False, "checks": results,
                "evidence_sha256": hashes, "firmware_bytes": len(binary),
                "verilator_warning_counts": dict(warnings),
                "warnings_note": "Migen/reference width, case, timescale and combinational-NBA warnings retained; not a warning-free build",
                "physical_timing": "NOT_RUN", "physical_bitstream": "NOT_BUILT",
                "simulated_esp32": "firmware-derived pin-level QSPI host, not an emulated ESP32 CPU"}
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    print("PASS: exact CPU/peripheral/ROM/frame evidence and prior-release preservation")


if __name__ == "__main__":
    main()
