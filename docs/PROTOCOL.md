# USB CDC protocol proposal

Transport: USB CDC-ACM byte stream. This is not USB Mass Storage.

## Prototype frame

Little-endian header:
- magic: 4 bytes `VLT1`
- version: u8
- command: u8
- request_id: u32
- payload_length: u32
- payload bytes
- CRC32: u32 over header + payload

CRC detects accidental corruption; it does not authenticate a host or protect against malicious modification. The protocol is not implemented in firmware yet.

## Proposed commands

- `0x01 GET_STATUS` — locked state, protocol version, firmware version
- `0x02 UNLOCK_SESSION` — do not send PIN over USB; PIN is entered on device
- `0x10 LIST_FILES` — allowed only when unlocked; response contains encrypted-manifest-derived filenames
- `0x20 UPLOAD_BEGIN`
- `0x21 UPLOAD_CHUNK`
- `0x22 UPLOAD_COMMIT`
- `0x30 DOWNLOAD_BEGIN`
- `0x31 DOWNLOAD_CHUNK`
- `0x32 DOWNLOAD_END`
- `0x40 DELETE_FILE`
- `0x50 LOCK`

Implementation requirements:
- Locked state should not disclose filenames, file counts, sizes, or metadata unless deliberately accepted by the threat model.
- Bound all lengths and counts; reject unknown commands and malformed frames.
- Avoid logging payloads.
- Define a session timeout and behavior on USB disconnect/reset.
- Require a physical unlock state before any plaintext transfer.
- Consider explicit user confirmation on the device for sensitive operations.
- Define anti-replay/request-ID semantics and behavior for duplicate chunks.
- Never rely on CRC as an authentication mechanism.
