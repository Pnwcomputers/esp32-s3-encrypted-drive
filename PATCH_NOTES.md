# Progress beyond the supplied update

The supplied `C:/GIT/esp32-s3-encrypted-drive-main.zip` is the integration baseline.
Changes in this working copy include:

- Fixed a real TinyUSB 2.4.0 target-build error: removed the obsolete `rx_unread_buf_sz` initializer; configured CDC buffers through sdkconfig defaults.
- Added a reproducible isolated WSL build script, a regenerated component lockfile, and exact framework/component pins after target compilation.
- Hardened the desktop client: partial serial writes, serialized command exchanges, monotonic timeouts, required acknowledgements, unique temporary downloads, fsync plus atomic replacement, and download cleanup. Ambiguous or unrelated ports require explicit selection.
- Resolved filename downloads to file IDs, including the ambiguous 14-byte legacy case; retained hex-ID downloads. Rejected path/control-character names. Protected existing destination and `.part` files on failed downloads.
- Added browser Host/Origin validation and hid storage usage from unauthenticated status requests. Added catalog/container trailing-byte checks and transfer ID validation.
- Corrected CDC command-length checks, bounded TX backpressure waits, and waited for the CDC worker before freeing its receive ringbuffer on shutdown.
- Preserved NVS configuration on startup errors, checked display allocation, and avoided closing the GUI while a transfer worker is still running.
- Replaced the unrelated Pester CI job with Python, sanitized native host checks, and an ESP32-S3 target build. Updated protocol documentation to describe the implemented wire format.
- Expanded portable Python regressions to 17 checks and added Windows-friendly `--python-only` mode. Added native browser-origin and trailing-catalog corruption checks.

See `docs/VALIDATION.md` for actual verification results and `docs/HARDWARE_VALIDATION.md` for the physical-device checklist. No flashing or eFuse programming was performed.
