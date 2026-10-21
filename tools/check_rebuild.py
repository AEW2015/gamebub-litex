#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Compare two successful probe builds without mistaking header dates for logic."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('first', type=Path)
    cli.add_argument('second', type=Path)
    cli.add_argument('--report', type=Path, required=True)
    args = cli.parse_args()
    if args.report.exists():
        cli.error('Use a NEW report path to preserve previous evidence')
    builds = [json.loads((p / 'evidence.json').read_text())
              for p in (args.first, args.second)]
    if any(b['build_status'] != 'PASS' for b in builds):
        cli.error('Both builds must have passed')
    if builds[0]['sources'] != builds[1]['sources']:
        cli.error('Builds do not bind identical RTL/constraints')
    if builds[0]['build_script_sha256'] != builds[1]['build_script_sha256']:
        cli.error('Build scripts differ')
    results = {}
    for name in ('gamebub_probe.json', 'gamebub_probe.fasm', 'gamebub_probe.frames'):
        first, second = [(p / name).read_bytes() for p in (args.first, args.second)]
        results[name] = {'identical': first == second, 'first_sha256': digest(first),
                         'second_sha256': digest(second)}
    bits = [(p / 'gamebub_probe.bit').read_bytes() for p in (args.first, args.second)]
    # Xilinx configuration sync word follows the host-only .bit metadata header.
    # The assembler writes wall-clock dates in that header on each invocation.
    payloads = []
    for bit in bits:
        offset = bit.find(bytes.fromhex('aa995566'))
        if offset < 0:
            cli.error('Configuration sync word absent')
        payloads.append(bit[offset:])
    results['configuration_payload'] = {
        'identical': payloads[0] == payloads[1],
        'first_sha256': digest(payloads[0]), 'second_sha256': digest(payloads[1])}
    passed = all(item['identical'] for item in results.values())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({
        'result': 'PASS' if passed else 'FAIL', 'builds': [str(args.first), str(args.second)],
        'checks': results, 'complete_bit_headers_identical': bits[0] == bits[1],
        'limitation': 'Hardware and independent timing qualification are not tested.'
    }, indent=2) + '\n')
    print('REBUILD_PAYLOAD_IDENTICAL' if passed else 'REBUILD_MISMATCH')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
