# Validation results — 2026-10-19

## Passed in this update

- **ESP32-S3 target build and link** with ESP-IDF **5.5.5**, GCC **14.2.0** (`esp-14.2.0_20260121`), regenerated configuration and exact dependency pins. The latest application binary is **1,383,648 bytes**, leaving 67% of the 4 MiB application partition free. The final build log contains no compiler warnings or errors.
- Resolved components: esp_lvgl_port 2.9.0, esp_tinyusb 2.4.0, led_strip 3.1.0~1, TinyUSB 0.21.0~2, LVGL 9.6.0~1. `firmware/dependencies.lock` records the full resolution.
- Build configuration: ESP32-S3, 16 MB flash, custom partition table, FAT long filenames, one USB CDC interface with 1024-byte RX/TX buffers plus USB MSC with a 4096-byte transfer buffer. Secure Boot and flash encryption are not enabled.
- **17 Python regressions**, run under Windows and Linux: framing/CRC/stream recovery, complete chunks and maximum catalogs, malformed dimensions, empty/exact-block/multiblock file transfers, partial/stalled serial writes, ambiguous port detection, truncated downloads, destination/temporary-file preservation, missing commit acknowledgements, invalid filenames, 14-byte filename and hex-ID downloads.
- **Native firmware web/storage/config/runtime regressions** under WSL Ubuntu with GCC, OpenSSL/cJSON adapters, AddressSanitizer and UndefinedBehaviorSanitizer. Checks cover fragmented HTTP reads, browser sessions, settings validation/write failures, key preservation during failed credential changes, credential rotation, authenticated empty files/catalogs, malformed lengths, incomplete uploads, idle locking, Host/Origin rejection and unauthenticated trailing catalog bytes. The final run passed without sanitizer diagnostics. The adapters do not exercise mbedTLS or ESP32 drivers.
- Python bytecode compilation, CLI help entry point, and embedded JavaScript syntax validation with Node.js.
- A strict AES-GCM driver adapter tests the real `vault_crypto.c` wrapper with the ESP-IDF driver's requirement for non-null zero-byte buffers. It covers empty encryption/decryption, authentication failure propagation and invalid nonempty buffers. This contract test does not test cryptographic correctness. Web regressions cover short setup credentials and SD write failure reporting without incorrect-PIN messages or retry penalties.

## Physical board progress

- Inspected an ESP32-S3 revision 0.2 with 16 MB flash and 8 MB embedded PSRAM. Saved and verified a complete private flash backup before writes. The backup is excluded from the source package.
- Flashed the development firmware using esptool 5.6.0 with successful write-hash verification. User confirmed the screen and phone setup page run. USB CDC enumerates as COM4; real desktop status and locked-file-list rejection passed.
- The card initially failed to mount. A temporary disposable-card formatter was loaded, then normal firmware restored. Its serial write/read test output was not captured, so no formatter test pass is claimed. The phone now reaches setup rather than reporting unavailable storage.
- First-time setup exposed an empty-catalog AES-GCM incompatibility: the ESP-IDF accelerated driver rejects null buffers even for length zero. The corrected image was built and flashed with hash verification. User confirmed phone setup/unlock works.
- Physical USB-serial storage tests passed for **0, 1, 4095, 4096, 4097 and 65536 bytes**: upload, list metadata, download with matching SHA-256, delete, then lock and reject listing. Only generated uniquely named test files were used, and they were deleted. The device was left locked.
- The new native USB-drive feature passes sanitized block/MSC tests: FAT32 geometry, cross-block/cross-segment I/O, persistence across unlock and credential rotation, three journal interruption points, primary-header recovery, ciphertext/map/missing-segment rejection, capacity/range checks, medium-change signaling, eject and lock gating. An independent `fsck.fat -n` check validates a generated test volume. Real Windows drive testing is pending.
- No eFuses were programmed. Secure Boot and flash encryption remain disabled.

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

- LCD orientation/partial-refresh behavior, backlight, RMT LED patterns and microSD/FAT32 capacity under load.
- Actual phone/browser interaction and desktop GUI rendering. Syntax and host checks are not a visual UI pass.
- Wi-Fi/USB concurrency and disconnect/reset handling, stack watermarks/minimum heap, long transfers and maximum catalogs on device.
- Power interruption during provisioning, catalog replacement, PIN changes and SD-full conditions.
- mbedTLS known-answer/runtime checks and hardware acceleration. Target compilation verifies API/link compatibility, not runtime cryptography.
- Device-bound key derivation, recovery wrappers, persistent retry limits, authenticated transport, nonce allocation policy, signed updates and production security review.

See HARDWARE_VALIDATION.md. The firmware remains a development build for disposable test data.
