# Implementation status and next steps

## Integrated in this snapshot

- Persistent SoftAP and embedded web controller; no physical navigation input.
- First-use setup, PIN/passphrase unlock, browser session checks and retry delays.
- Encrypted chunk storage/catalog, lock, credential rotation, Wi-Fi and USB file operations.
- NVS-backed settings, idle locking, LCD status, GPIO38 LED normal/dim/off modes.
- Restored desktop framing/parsers and host regression coverage.

## Next validation gate

The clean ESP-IDF 5.5.5 build now passes with pinned components. Complete HARDWARE_VALIDATION.md: flash the exact board and verify both transports, storage integrity, all settings and memory use. VALIDATION.md distinguishes host checks from untested hardware behavior.

## Deferred security work

Device-bound key derivation and stronger KDF/version migration; separate recovery wrapping; HTTPS or another authenticated transport; persistent attempt limits; nonce management; signed updates/Secure Boot/flash encryption after review; anti-rollback and power-failure stress testing. FIDO security-key enrollment is not implemented. No eFuse provisioning is included.
