# Implementation plan

## Stage 0 — resolve hardware and version facts

- Obtain the exact board revision and official schematic/pinout.
- Confirm LCD controller/driver and display library version.
- Confirm microSD bus mode, pin assignments, supported filesystem and maximum card behavior.
- Confirm which physical GPIOs are actually available and safe for external buttons.
- Confirm USB connector/data path and whether the chosen port is native USB-OTG or USB-UART bridge.
- Pin exact ESP-IDF release and component versions; commit `sdkconfig.defaults` only after a real build.
- Verify ESP32-S3 silicon revision and eFuse state before security design is finalized.

## Stage 1 — development bring-up

- Minimal app boots and reports version over serial.
- LCD driver, SD mount/unmount, buttons with debounce, USB CDC are individually tested.
- No real secrets, no irreversible eFuse operations.

## Stage 2 — file container

- Define a versioned binary format with explicit endianness, maximum sizes, chunk size, IDs, nonce policy, AAD fields, tag placement, manifest authentication and commit semantics.
- Unit tests for empty files, maximum file sizes, truncation, reordered/duplicated chunks, corrupt tags, wrong key, power loss and SD full.
- Ensure no plaintext names or user metadata appear in raw card images.

## Stage 3 — key management

- Write a cryptographic design note before code.
- Select exact hardware HMAC API and key purpose supported by selected ESP-IDF version.
- Define PIN KDF and device-secret combination with domain separation and test vectors.
- Define recovery wrapper independent of the original device secret.
- Add online retry throttling and anti-rollback strategy.
- Test power loss during enrollment, PIN change, and recovery rotation.

## Stage 4 — USB protocol

- Framed messages with version, request ID, command, length, and CRC for accidental corruption detection. CRC is not authentication.
- Strict parser, maximum lengths, timeouts, duplicate request behavior, state machine and authorization rules.
- Locked state only allows status and limited diagnostics.
- Host sends plaintext file data to the device for encryption; device sends plaintext only after successful authentication and unlock.
- No command accepts a key export request.

## Stage 5 — desktop application

- Python + PySide6 UI; pyserial transport.
- Explicit serial-port selection and device identity display.
- Upload/download with temporary files and atomic rename on host.
- Never log file contents, PIN, recovery secret, or key material.
- Package/test on Windows, macOS, Linux; document permissions/driver requirements.

## Stage 6 — security review and production provisioning

- Threat-model review, code review, fuzz the frame parser, run crypto known-answer tests.
- Verify signed update and rollback policy.
- Follow the exact ESP-IDF release's Secure Boot v2 + flash encryption enablement order and eFuse constraints.
- Use a spare board for rehearsals. Never test first-time eFuse provisioning on the only device.
- Keep an auditable provisioning record that contains no secret key material.
- Do not call the product secure until the implemented design has been tested and reviewed.
