# Installation and local build

Use the exact Waveshare ESP32-S3-LCD-1.47 and expendable FAT32 media. This source was clean-built for ESP32-S3 with **ESP-IDF 5.5.5**; the manifest and lockfile pin the resolved components. ESP-IDF 6.2 is not the supported build environment for this snapshot.

From an ESP-IDF 5.5.5 terminal:

```sh
cd firmware
idf.py set-target esp32s3
idf.py build
```

On Ubuntu/WSL, `bash tools/build_wsl.sh --clean-config` installs a separate build cache and builds without touching a system ESP-IDF installation. This needs network access on first use. Outputs go to `artifacts/firmware`.

The supplied binaries passed compilation/linking, not physical-board validation. Confirm the board revision and flash size, then follow HARDWARE_VALIDATION.md before using important files. See the root README for desktop commands. No eFuse or security-provisioning commands are included.
