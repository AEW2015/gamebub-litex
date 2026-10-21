#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Install hash-pinned LiteDRAM into an isolated dependency directory."""

import sys
import json
import hashlib
import subprocess
import urllib.request
from pathlib import Path


# Run ---------------------------------------------------------------------------------------------

def main():
    lock = json.loads(Path(__file__).with_name("memory-dependencies.json").read_text(encoding="utf-8"))
    prefix = Path(lock["prefix"])
    if prefix.exists():
        raise SystemExit(f"Refusing to replace existing {prefix}")

    downloads = prefix.with_name("memory-downloads")
    downloads.mkdir(exist_ok=True)
    files = []
    for entry in lock["packages"]:
        path = downloads / entry["file"]
        if not path.exists():
            with urllib.request.urlopen(entry["url"], timeout=120) as source, path.open("xb") as target:
                while block := source.read(1024*1024):
                    target.write(block)
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise SystemExit(f"Hash mismatch: {path}")
        files.append(str(path))

    command = [sys.executable, "-m", "pip", "install", "--no-index", "--no-deps",
               "--target", str(prefix), *files]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
