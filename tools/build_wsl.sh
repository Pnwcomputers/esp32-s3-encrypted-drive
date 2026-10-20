#!/usr/bin/env bash
# Reproducible target build isolated from system ESP-IDF installations.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cache_root="${VAULT_BUILD_CACHE:-/var/tmp/esp32-vault-toolchain}"
idf_root="$cache_root/esp-idf-v5.5.5"
export IDF_TOOLS_PATH="$cache_root/tools"
mkdir -p "$cache_root"
if [ ! -f "$idf_root/tools/idf.py" ]; then
    git clone --branch v5.5.5 --depth 1 --recursive --shallow-submodules https://github.com/espressif/esp-idf.git "$idf_root"
fi
if ! compgen -G "$IDF_TOOLS_PATH/python_env/idf5.5_py*_env/bin/python" > /dev/null; then
    "$idf_root/install.sh" esp32s3
fi
# ESP-IDF activation scripts may inspect unset shell variables.
set +u
. "$idf_root/export.sh"
set -u
project="$cache_root/project"
mkdir -p "$project"
tar -C "$repo_root" --exclude='./build' --exclude='./managed_components' --exclude='./.git' --exclude='./artifacts' --exclude='__pycache__' -cf - . | tar -C "$project" -xf -
cd "$project/firmware"
if [ "${1:-}" = "--clean-config" ]; then rm -f sdkconfig; fi
if [ ! -f sdkconfig ]; then idf.py set-target esp32s3; fi
idf.py reconfigure > "$cache_root/configure.log" 2>&1 || { tail -60 "$cache_root/configure.log"; exit 1; }
if ! idf.py build > "$cache_root/build.log" 2>&1; then tail -80 "$cache_root/build.log"; exit 1; fi
tail -18 "$cache_root/build.log"
mkdir -p "$repo_root/artifacts/firmware/bootloader" "$repo_root/artifacts/firmware/partition_table"
cp dependencies.lock "$repo_root/firmware/dependencies.lock"
cp build/esp32_vault.bin build/esp32_vault.elf build/flash_args "$repo_root/artifacts/firmware/"
cp build/bootloader/bootloader.bin "$repo_root/artifacts/firmware/bootloader/"
cp build/partition_table/partition-table.bin "$repo_root/artifacts/firmware/partition_table/"
cp sdkconfig "$repo_root/artifacts/firmware/sdkconfig.built"
echo "Build artifacts copied to $repo_root/artifacts/firmware"
cp "$cache_root/build.log" "$repo_root/artifacts/firmware/build.log"
