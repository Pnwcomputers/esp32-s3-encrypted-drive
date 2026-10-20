# Validation results — 2026-10-19

## Passed in this update

- **Clean ESP32-S3 target build and link** with ESP-IDF **5.5.5**, GCC **14.2.0** (`esp-14.2.0_20260121`), regenerated configuration and exact dependency pins. The application binary is **1,366,640 bytes**, leaving 67% of the 4 MiB application partition free. The final build log contains no compiler warnings or errors. No flashing was performed.
- Resolved components: esp_lvgl_port 2.9.0, esp_tinyusb 2.4.0, led_strip 3.1.0~1, TinyUSB 0.21.0~2, LVGL 9.6.0~1. `firmware/dependencies.lock` records the full resolution.
- Build configuration: ESP32-S3, 16 MB flash, custom partition table, FAT long filenames, one USB CDC interface with 1024-byte RX/TX buffers. Secure Boot and flash encryption are not enabled.
- **17 Python regressions**, run under Windows and Linux: framing/CRC/stream recovery, complete chunks and maximum catalogs, malformed dimensions, empty/exact-block/multiblock file transfers, partial/stalled serial writes, ambiguous port detection, truncated downloads, destination/temporary-file preservation, missing commit acknowledgements, invalid filenames, 14-byte filename and hex-ID downloads.
- **Native firmware web/storage/config/runtime regressions** under WSL Ubuntu with GCC, OpenSSL/cJSON adapters, AddressSanitizer and UndefinedBehaviorSanitizer. Checks cover fragmented HTTP reads, browser sessions, settings validation/write failures, key preservation during failed credential changes, credential rotation, authenticated empty files/catalogs, malformed lengths, incomplete uploads, idle locking, Host/Origin rejection and unauthenticated trailing catalog bytes. The final run passed without sanitizer diagnostics. The adapters do not exercise mbedTLS or ESP32 drivers.
- Python bytecode compilation, CLI help entry point, and embedded JavaScript syntax validation with Node.js.

## Reproduce

```sh
# Portable desktop checks (also works on Windows without native build packages)
python tests/run_checks.py --python-only

# Linux native regressions: GCC, OpenSSL headers, libcjson runtime/development package
python3 tests/run_checks.py

# Isolated Ubuntu/WSL target build; first run downloads official ESP-IDF/compiler
bash tools/build_wsl.sh --clean-config
```

The builder uses `/var/tmp/esp32-vault-toolchain` as a separate cache, preserving system ESP-IDF installations. It copies outputs to `artifacts/firmware` and never flashes. Build and host logs are included in the packaged artifacts. GitHub Actions has matching jobs, but no remote CI run is claimed.

## Still requires physical hardware or review

- Booting/flashing the exact PCB revision; LCD orientation/partial-refresh behavior, backlight, RMT LED patterns, microSD/FAT32 capacity and USB enumeration.
- Actual phone/browser interaction and desktop GUI rendering. Syntax and host checks are not a visual UI pass.
- Wi-Fi/USB concurrency and disconnect/reset handling, stack watermarks/minimum heap, long transfers and maximum catalogs on device.
- Power interruption during provisioning, catalog replacement, PIN changes and SD-full conditions.
- mbedTLS known-answer/runtime checks and hardware acceleration. Target compilation verifies API/link compatibility, not runtime cryptography.
- Device-bound key derivation, recovery wrappers, persistent retry limits, authenticated transport, nonce allocation policy, signed updates and production security review.

See HARDWARE_VALIDATION.md. The firmware remains a development build for disposable test data.
