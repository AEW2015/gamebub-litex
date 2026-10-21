# SPDX-License-Identifier: 0BSD
"""Pinned tool identities and fail-closed implementation checks."""

import re
import math
import hashlib
from pathlib import Path


# Tool Pins ---------------------------------------------------------------------------------------

PART = "xc7a100tcsg324-1"
PINS = {
    "openxc7.tgz":       "383785f4af92809671f08ebd7c97660c5d01f0145167538bb10667d9b929656c",
    "oss-cad-suite.tgz": "a6ccc6b96b2d985336a1061c78b2fd2bdd73e0f68690da17db88e00457881a11",
}
REVISIONS = {
    "nextpnr-xilinx-revision": "e7a6fb0e708ecac22c917ec70fc4cb3d47b5d2b5",
    "prjxray-db-revision":     "6a6debcd6209e251ce6e9c1d7d0782e37fe39c99",
    "prjxray-revision":        "317fdc1319a225f57b6a0e6993a37d1a4ae75e5a",
    "fasm-revision":           "2f57ccb1727a120e8cacbb95c578f3c71bdcc95a",
    "yosys-release-tag":       "2026-10-14",
}


# Helpers -----------------------------------------------------------------------------------------

def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_fmax(report):
    """Require every reported clock to meet its explicit positive constraint."""
    if not report.get("utilization") or not isinstance(report.get("fmax"), dict) or not report["fmax"]:
        raise ValueError("Place-and-route report lacks utilization or fmax")
    checked = {}
    for clock, values in report["fmax"].items():
        if not isinstance(values, dict):
            raise ValueError(f"Malformed fmax entry for {clock}")
        for key in ("achieved", "constraint"):
            value = values.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"Invalid fmax {key} for {clock}: {value!r}")
        checked[clock] = {
            "achieved_mhz":   values["achieved"],
            "constraint_mhz": values["constraint"],
            "status":         "PASS" if values["achieved"] >= values["constraint"] else "FAIL",
        }
    failures = [clock for clock, values in checked.items() if values["status"] == "FAIL"]
    if failures:
        raise ValueError("Reported clock frequency misses constraint: " + ", ".join(failures))
    return checked


def rejected_pnr_diagnostics(text):
    """Unsupported constraints and implicit clock defaults invalidate a build."""
    pattern = re.compile(
        r"no timing constraint|unconstrained|"
        r"(?:unsupported|not supported|ignor\w*)[^\n]*(?:xdc|create_clock|option|argument)|"
        r"(?:xdc|create_clock)[^\n]*(?:unsupported|not supported|ignor\w*)",
        re.IGNORECASE,
    )
    return [line for line in text.splitlines() if pattern.search(line)]
