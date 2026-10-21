#!/usr/bin/env bash
# SPDX-License-Identifier: 0BSD
# Install verified open-source tool distributions into a NEW isolated prefix.
set -euo pipefail

if [[ $# != 1 || $1 != /* || -e $1 ]]; then
    printf '%s\n' 'Usage: bootstrap_linux.sh /absolute/NEW/prefix' >&2
    exit 2
fi
prefix=$1
case "$(uname -sm)" in
    'Linux x86_64') ;;
    *) printf '%s\n' 'This pinned distribution requires Linux x86_64.' >&2; exit 2 ;;
esac
mkdir -p "$prefix/downloads"

fetch() {
    local url=$1 file=$2 digest=$3
    curl --fail --location --retry 3 --output "$prefix/downloads/$file" "$url"
    printf '%s  %s\n' "$digest" "$prefix/downloads/$file" | sha256sum --check --status
}

# Independent downloads can overlap. A failed checksum never reaches extraction.
fetch 'https://github.com/cavearr/toolchain-openxc7-releases/releases/download/2026-10-19/openxc7-toolchain-linux-x86-64-20261019.tgz' \
    openxc7.tgz 383785f4af92809671f08ebd7c97660c5d01f0145167538bb10667d9b929656c &
openxc7_pid=$!
fetch 'https://github.com/YosysHQ/oss-cad-suite-build/releases/download/2026-10-14/oss-cad-suite-linux-x64-20261014.tgz' \
    oss-cad-suite.tgz a6ccc6b96b2d985336a1061c78b2fd2bdd73e0f68690da17db88e00457881a11 &
suite_pid=$!
wait "$openxc7_pid"
wait "$suite_pid"

# Save inventories before extracting. Only relative, non-traversing archive
# entries are accepted; this is a tool install, not permission to overwrite OS.
python3 - "$prefix" <<'PY'
import pathlib
import sys
import tarfile

prefix = pathlib.Path(sys.argv[1])
for name in ('openxc7', 'oss-cad-suite'):
    with tarfile.open(prefix / 'downloads' / (name + '.tgz')) as archive:
        members = archive.getmembers()
        for item in members:
            p = pathlib.PurePosixPath(item.name)
            if p.is_absolute() or '..' in p.parts:
                raise SystemExit('Unsafe archive member: ' + item.name)
        (prefix / 'downloads' / (name + '-inventory.txt')).write_text(
            '\n'.join(item.name for item in members) + '\n')
PY
tar -xzf "$prefix/downloads/openxc7.tgz" -C "$prefix"
tar -xzf "$prefix/downloads/oss-cad-suite.tgz" -C "$prefix"
printf 'TOOLS_EXTRACTED prefix=%s\n' "$prefix"
printf '%s\n' 'Use packaged bin wrappers, not raw libexec executables.'
