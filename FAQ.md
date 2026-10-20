# Frequently asked questions

**How do I unlock it without buttons or a touchscreen?** Connect to the device's Wi-Fi and open http://192.168.4.1. The display provides status only. The browser provides the keypad, passphrase entry, file manager and settings.

**Does Wi-Fi turn off after unlocking?** No. SoftAP and HTTP remain available while powered, including while locked. This is not a radio-disabled air-gap design.

**Can I use a security key?** The current credential is a PIN or passphrase. FIDO hardware keys and recovery-key enrollment are not implemented.

**Does it appear as a USB drive letter?** No. Use the supplied Python CLI/GUI over USB CDC or the web file manager. USB operations require the global vault to be unlocked through Wi-Fi.

**What if I forget the credential?** There is no recovery wrapper. Resetting Wi-Fi settings does not recover encrypted files. Keep backups and preserve the original card before experimenting.

**Is the firmware ready for sensitive data?** No production security or physical-board validation is claimed. Read README.md and docs/THREAT_MODEL.md for the current limits.

**Why won't a 64 GB card mount?** The current build expects FAT32. Cards sold preformatted as exFAT need a suitable FAT32 partition prepared separately. The firmware never formats a failed mount.
