# Desktop client scaffold

Planned stack: Python 3.11+ (pin exact version during implementation), PySide6 for UI, pyserial for USB CDC.

The client should not implement vault encryption or receive master keys. The ESP32 performs encryption/decryption. The client handles user-selected files and framed USB commands.

No working file transfer or GUI is implemented yet. Do not treat this directory as a finished application.
