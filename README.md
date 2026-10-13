# ESP32-S3-LCD-1.47 Encrypted Vault — Starter Scaffold

**Status: architecture and development scaffold only. Not production-ready and not yet hardware-verified.**

This repository intentionally does not burn eFuses, enable Secure Boot, enable flash-encryption release mode, or provision real secrets. Those operations can be irreversible. The starter firmware is deliberately minimal and does not yet implement encryption, PIN handling, SD-card access, or USB commands.

## Target

- Board family: Waveshare ESP32-S3-LCD-1.47 (confirm exact PCB revision before wiring)
- Storage: 64 GB microSD (actual usable capacity and filesystem support depend on card/partition and chosen driver)
- Firmware: ESP-IDF, C
- Host application: Python + PySide6 planned; pyserial for USB CDC
- Transport: USB CDC-ACM command protocol, not USB Mass Storage
- PIN input: external navigation buttons; GPIO assignments intentionally TBD pending schematic/revision verification

## Repository map

- `firmware/`: minimal ESP-IDF application scaffold
- `desktop/`: protocol specification and Python host skeleton
- `docs/`: threat model, key design, provisioning/recovery, hardware validation
- `tests/`: initial host-side protocol-format tests
- `tools/`: no destructive provisioning commands are included

## Important security design decisions

1. Use a random 256-bit vault data-encryption key (DEK), generated from the ESP32-S3 hardware RNG after entropy is initialized.
2. Encrypt file contents with AES-256-GCM. Each encryption invocation must use a unique 96-bit nonce for the same key. Never reuse a nonce with a key.
3. Use independently authenticated chunks with unique nonces and bind file ID, chunk index, format version, and expected chunk length as authenticated additional data (AAD).
4. Encrypt filenames and the file index. Do not expose plaintext names, directory paths, or user metadata on the card.
5. Use a per-device eFuse HMAC key only after confirming supported key purpose/API and the exact chip/eFuse state. A read-protected HMAC key is intended to be used by hardware HMAC APIs; application design must not assume it can read the key bytes.
6. A PIN is low entropy. Do not use a fast plain hash of the PIN as the only key derivation. Use a reviewed construction with a hardware-held secret and a random salt; rate-limit online attempts. Have an independent security review before claiming offline-guess resistance.
7. Recovery uses a separate high-entropy random recovery secret, not a short recovery PIN. Store it outside the device and card. Verify recovery before the user confirms setup.
8. Never send the DEK, wrapping keys, HMAC secret, or recovery secret over USB.
9. Secure Boot and flash encryption protect firmware/on-chip flash, not the microSD card. The vault file encryption is separate.
10. Keep eFuse programming disabled until the complete firmware, update path, and recovery procedure have been tested on a spare device.

## Build status

The firmware skeleton uses standard ESP-IDF project conventions but is not claimed to compile against every ESP-IDF release or to drive this board's display. Pin the exact ESP-IDF version and board revision before hardware integration.

See `docs/IMPLEMENTATION_PLAN.md` and `docs/NO_GUESSING_CHECKLIST.md`.
