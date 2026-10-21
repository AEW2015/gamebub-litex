#!/usr/bin/env bash
# Isolated Linux LiteX environment. No apt install, global pip or vendor tools.
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=/opt/gamebub-litex-20261021
if [[ -e "$ROOT" ]]; then
    echo "Refusing to replace existing namespace: $ROOT" >&2
    exit 1
fi
mkdir -p "$ROOT/downloads" "$ROOT/toolchain"
cd "$ROOT/downloads"
# Fetch exact locked URLs and check every hash before pip or dpkg runs.
python3 "$SCRIPT_DIR/verify_downloads.py" --directory "$ROOT/downloads" --download
python3 -m venv --without-pip "$ROOT/venv"
PIP_WHEEL=pip-24.3.1-py3-none-any.whl
PYTHONPATH="$ROOT/downloads/$PIP_WHEEL" "$ROOT/venv/bin/python" -m pip install --no-index "$PIP_WHEEL"
PIP="$ROOT/venv/bin/pip"
"$PIP" install --no-index --no-deps --report "$ROOT/pip-install-report.json" ./*.whl
# Extract verified Ubuntu GCC without changing the system package database.
for package in ./*.deb; do dpkg-deb -x "$package" "$ROOT/toolchain"; done
# Debian GCC embeds /usr/lib/... binutils paths. Relocate its unprefixed
# assembler/linker lookup inside this private compiler's executable prefix.
for tool in as ld; do
    ln -s "../../../riscv64-unknown-elf/bin/$tool" "$ROOT/toolchain/usr/lib/gcc/riscv64-unknown-elf/10.2.0/$tool"
done
"$ROOT/toolchain/usr/bin/riscv64-unknown-elf-gcc" -march=rv32i2p0 -mabi=ilp32 -x c -c -o /dev/null /dev/null
sha256sum ./* > "$ROOT/downloads.sha256"
"$PIP" freeze --all > "$ROOT/python-freeze.txt"
"$PIP" check
"$ROOT/toolchain/usr/bin/riscv64-unknown-elf-gcc" --version
"$ROOT/toolchain/usr/bin/riscv64-unknown-elf-gcc" -print-multi-lib
printf 'Environment ready. Add %s and %s to PATH.\n' "$ROOT/venv/bin" "$ROOT/toolchain/usr/bin"
