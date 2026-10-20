# Setup and recovery status

## Implemented first-use flow

Boot with FAT32 test media, connect to the persistent device Wi-Fi and open http://192.168.4.1. Create and confirm a 6–63-byte PIN/passphrase. The firmware generates a random data key and wraps it under a PBKDF2-derived key. Existing metadata, including a corrupt/truncated file, prevents automatic re-provisioning. Change credentials from the authenticated browser with the current credential.

No buttons, touchscreen, eFuse programming or physical enrollment steps are required. Setup and subsequent unlocking are available through Wi-Fi. Browser session tokens are discarded on reload or restart.

## Recovery limitations

There is currently no independent recovery key or FIDO security-key wrapper. Losing the vault PIN/passphrase loses access to files. Changing/resetting Wi-Fi settings or NVS does not recover the data key. Preserve backups and original SD media before recovery experiments. Metadata and catalog backup renames are for interrupted writes, not forgotten-credential recovery.

Independent high-entropy recovery wrapping and device-bound key derivation remain future design work. Secure Boot and flash encryption are not enabled by this source, and no eFuse-changing commands are included.
