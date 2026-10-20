# Progress beyond the supplied update

The supplied `C:/GIT/esp32-s3-encrypted-drive-main.zip` is the integration baseline.
Changes in this working copy include:

- Added a composite CDC + USB Mass Storage interface backed by encrypted data on the microSD, sized to nearly all currently free card capacity. Added authenticated lazy block allocation, segmented backing files, a durable redo journal, FAT32 geometry, locked-medium gating and phone create/reconnect controls. Safe USB eject is required before locking/settings/legacy operations; auto-lock waits while exported. See `docs/USB_DRIVE.md`.
- Fixed first-time provisioning on ESP-IDF's accelerated AES-GCM path: provide non-null buffers for zero-byte catalog/file messages while retaining zero plaintext length. Added a strict driver-contract regression, and distinguished setup/storage failures from incorrect credentials in the web page.
- Fixed a real TinyUSB 2.4.0 target-build error: removed the obsolete `rx_unread_buf_sz` initializer; configured CDC buffers through sdkconfig defaults.
- Added a reproducible isolated WSL build script, a regenerated component lockfile, and exact framework/component pins after target compilation.
- Hardened the desktop client: partial serial writes, serialized command exchanges, monotonic timeouts, required acknowledgements, unique temporary downloads, fsync plus atomic replacement, and download cleanup. Ambiguous or unrelated ports require explicit selection.
- Resolved filename downloads to file IDs, including the ambiguous 14-byte legacy case; retained hex-ID downloads. Rejected path/control-character names. Protected existing destination and `.part` files on failed downloads.
- Added browser Host/Origin validation and hid storage usage from unauthenticated status requests. Added catalog/container trailing-byte checks and transfer ID validation.
- Corrected CDC command-length checks, bounded TX backpressure waits, and waited for the CDC worker before freeing its receive ringbuffer on shutdown.
- Preserved NVS configuration on startup errors, checked display allocation, and avoided closing the GUI while a transfer worker is still running.
- Replaced the unrelated Pester CI job with Python, sanitized native host checks, and an ESP32-S3 target build. Updated protocol documentation to describe the implemented wire format.
- Expanded portable Python regressions to 17 checks and added Windows-friendly `--python-only` mode. Added native browser-origin and trailing-catalog corruption checks.

See `docs/VALIDATION.md` for actual verification results and `docs/HARDWARE_VALIDATION.md` for the remaining physical-device checklist. The development board has been backed up and flashed; no eFuse programming was performed.
