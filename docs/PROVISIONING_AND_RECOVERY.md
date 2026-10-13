# Provisioning and recovery runbook (design only)

## Development mode

1. Build and flash only the non-secure scaffold.
2. Confirm display, SD, USB, and buttons using a pin map checked against the exact board revision/schematic.
3. Use synthetic test data only.
4. Keep all eFuse-changing scripts absent/disabled in the normal build.

## First-use enrollment (future implementation)

1. Confirm supported ESP32-S3 target, silicon revision, eFuse state, and available key block/key purpose.
2. Initialize the hardware RNG according to ESP-IDF guidance.
3. Generate a random DEK and random salts/IDs.
4. Provision a unique device HMAC secret to an appropriate key block, with supported key purpose and read protection. Test the exact API against the selected ESP-IDF version before committing to this design.
5. Enroll PIN and high-entropy recovery secret, producing separate wrapped DEK records.
6. Test PIN unlock, wrong-PIN rejection, recovery unlock, change-PIN, and power-loss recovery.
7. Export/display the recovery secret once, with clear instructions to store it offline. Do not save it to the SD card or computer automatically.
8. Read back and verify the non-secret eFuse state. Do not repeat provisioning blindly if power or USB is interrupted.

## Recovery policy

- Recovery secret permits re-wrapping the same DEK under a new PIN; it should not require decrypting/re-encrypting all file contents.
- If the PIN is lost but recovery secret survives, recover and set a new PIN.
- If the recovery secret is lost but PIN works, implement a deliberate recovery-key rotation flow before it is lost.
- If both PIN and recovery secret are lost, data is unrecoverable by design.
- Replacing the board loses access to a DEK wrapped to the original device secret unless the recovery path can unwrap the DEK. Test this scenario.
- If the board fails physically, the recovery secret must be sufficient to unwrap the DEK on a replacement/recovery implementation. The format must not require the original eFuse secret for recovery. This requires a carefully designed recovery wrapper.

## Production eFuse stage — NOT INCLUDED

Only after independent review and a verified update/recovery process should production configuration be planned. Follow Espressif's current security enablement workflow for the exact ESP-IDF release. Keep power stable. Secure Boot and flash encryption settings can be irreversible and can disable ROM USB/UART update paths. Back up signing keys and maintain a tested signed firmware update process.
