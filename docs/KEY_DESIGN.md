> Design reference: device-held HMAC/recovery features in this document remain future work. Current behavior and limits are defined in README.md and THREAT_MODEL.md.

# Key design (proposal requiring implementation review)

## Key hierarchy

- `DEK`: random 256-bit data-encryption key; encrypts file chunks.
- `device_secret`: unique HMAC key provisioned into a supported ESP32-S3 eFuse key block with appropriate purpose and read protection. Application must call the supported hardware HMAC interface; it must not expect to read the secret bytes.
- `PIN wrapping key`: derived using a documented, reviewed construction combining the PIN, random per-vault salt, and device-secret output. This design must be reviewed before claiming offline-guess resistance.
- `recovery wrapping key`: derived from a separate high-entropy recovery secret and a separate random salt using a password-KDF suitable for high-entropy input.
- Store independent wrapped copies of the DEK for PIN and recovery paths. Never store the DEK in plaintext on SD or send it over USB.

## Caution about PIN KDF design

A short numeric PIN has low entropy. A generic KDF alone cannot make a 6–8 digit PIN resistant to offline guessing. The hardware secret can make card-only guessing materially harder if the design is correctly constructed and if the attacker cannot query the device as an oracle. Online attempts must be throttled with persistent state, and firmware replacement must be prevented by a production secure-boot policy. This needs cryptographic review, not improvised concatenation of secrets.

Do not invent a custom KDF. Select and document exact primitives, encodings, domain separation labels, salts, and test vectors before implementation. Use ESP-IDF-supported cryptographic APIs where possible and a maintained library for any missing primitive.

## AES-GCM rules

- Use 256-bit keys and 96-bit nonces unless a reviewed library/API design requires otherwise.
- A nonce MUST NOT repeat for the same AES-GCM key.
- Use a robust nonce allocation strategy that remains safe across power loss, retries, card cloning, and interrupted writes. A per-file random subkey plus per-chunk counter is one possible design, subject to review.
- Authenticate format version, file identifier, chunk number, declared plaintext length, and relevant metadata as AAD.
- Do not release unauthenticated plaintext to the host. For large files, verify each chunk before sending that chunk; define whole-file consistency and truncation detection in the container format.
- Include a final authenticated manifest/commit record so missing/reordered chunks are detected.
- Use fresh random file IDs and unique key/nonce domains for each file.

## Erasure

Clear key buffers with a compiler-resistant secure-zero function supported by the selected toolchain. This reduces residuals but does not prove that all copies have been removed from every register, stack frame, cache, or crash dump.
