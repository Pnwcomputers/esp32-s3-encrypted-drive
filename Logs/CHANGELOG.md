# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- Scrub the current and proposed credentials (and the raw request body) on **every**
  `change_pin` exit path, not only on success; also scrub the credential copy held in
  the parsed settings JSON before freeing it (`vault_web.c`). (Review L-1)
- Strengthened documentation of the hard-coded default Wi-Fi PSK: it is embedded in
  firmware and identical across un-reconfigured devices, so it provides no
  confidentiality until changed. No behavior change. (Review M-1; see
  `docs/THREAT_MODEL.md`, `docs/CODE_REVIEW.md`)

### Fixed
- **Enabled the board's 8 MB octal PSRAM** (`sdkconfig.defaults`) and allocate the USB
  drive's ~32 KB working set from it (`vault_drive.c`, runtime `heap_caps_calloc`, with
  an internal fallback — nothing static). Previously PSRAM was off, so the whole stack
  (Wi-Fi + LCD + USB + HTTP) competed for ~512 KB internal SRAM and the drive-state
  allocation failed under pressure, making **Enable SD card drive** always report
  "USB drive could not be opened." Confirmed fixed on hardware: the volume now mounts
  in Windows as a FAT32 drive ("ESP32 VAULT", ~57.8 GB). The drive capacity is still
  measured dynamically from the card's free space.
- CDC RX path now applies brief backpressure and logs an overflow instead of silently
  dropping received bytes when the worker falls behind (`cdc_protocol.c`). (Review L-4)
- `nvs_flash_init()` recovers from a blank/unformatted or version-changed NVS
  (erase-once-and-retry) instead of aborting the boot (`main.c`). (Review S-1)
- Desktop CLI reports malformed device responses cleanly instead of crashing with a
  traceback, and `ls` skips a single bad record instead of aborting the whole listing
  (`desktop/protocol.py`, `desktop/vault_cli.py`). (Review L-2)
- Desktop download verifies the device-returned `file_id` matches the requested file
  before writing, guarding against a firmware bug or session mix-up
  (`desktop/vault_client.py`). (Review L-3)

### Added
- `docs/CODE_REVIEW.md`: a full correctness + security review of the firmware and
  desktop tools (find → adversarial verify → synthesize), with findings and fixes.

## Earlier development

- Composite CDC + USB Mass Storage interface backed by AES-256-GCM encrypted data on
  the microSD, exposed only while unlocked; authenticated block/map/root records, a
  durable redo journal, FAT32 geometry, locked-medium gating and safe-eject handling.
- First-use provisioning, PIN/passphrase unlock, browser session tokens, bounded
  RAM-only retry delays, NVS-backed settings, idle locking, credential rotation that
  preserves the data key.
- Non-blocking WS2812 RGB status LED controller for the onboard LED (GPIO38), wired to
  locked / PIN-entry / auth success+failure / unlocked / transfer / recovery states.
- Hardened desktop client (partial-write-safe serial, serialized exchanges, monotonic
  timeouts, required acknowledgements, atomic downloads) and a 17-check Python
  regression suite plus native firmware regressions under ASan/UBSan.
- Reproducible isolated WSL target build (`tools/build_wsl.sh`) with pinned ESP-IDF
  5.5.5 and component lockfile.
