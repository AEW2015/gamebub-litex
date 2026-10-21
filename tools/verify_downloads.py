#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Verify locked archives; optionally fetch missing exact URLs without running them."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--download", action="store_true", help="Fetch missing archives only")
    args = parser.parse_args()
    lock = json.loads(Path(__file__).with_name("toolchain-lock.json").read_text())
    if args.download:
        args.directory.mkdir(parents=True, exist_ok=True)
    entries = lock["downloads"]
    names = [entry["file"] for entry in entries]
    if len(set(names)) != len(names):
        raise RuntimeError("Duplicate archive filename in lock")
    for entry in entries:
        if Path(entry["file"]).name != entry["file"]:
            raise RuntimeError("Locked archive filename is not a basename")
        archive = args.directory / entry["file"]
        if not archive.exists() and args.download:
            if not entry["url"].startswith("https://"):
                raise RuntimeError("Download requires an exact HTTPS URL")
            temporary = archive.with_name(archive.name + ".part")
            with urllib.request.urlopen(entry["url"], timeout=120) as response, temporary.open("xb") as dest:
                while block := response.read(1024 * 1024):
                    dest.write(block)
            if digest(temporary) != entry["sha256"]:
                raise RuntimeError(f"SHA256 mismatch for {archive.name}; retained .part for inspection")
            temporary.rename(archive)
        if not archive.is_file() or digest(archive) != entry["sha256"]:
            raise RuntimeError(f"Missing or hash-mismatched locked archive: {archive}")
        print(f"PASS {archive.name}")
    extras = sorted(path.name for path in args.directory.iterdir() if path.is_file() and path.name not in names)
    if extras:
        raise RuntimeError("Unexpected unpinned downloads: " + ", ".join(extras))
    print(f"Verified all {len(entries)} locked archives; no archive code executed")


if __name__ == "__main__":
    main()
