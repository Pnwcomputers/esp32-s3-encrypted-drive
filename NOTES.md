# ESP32-S3 Encrypted Hardware Vault: Project Blueprint

## 1. Project Overview
A stealthy, self-contained hardware vault that encrypts files on a microSD card. It unlocks via a temporary, air-gapped Wi-Fi Access Point and a smartphone browser. Once unlocked, the radios are permanently disabled and files are transferred to a computer over a USB connection without exposing the vault's master encryption key to the host operating system.

## 2. Hardware Specifications
*   **Microcontroller:** Waveshare ESP32-S3-LCD-1.47 (USB-A Thumb-Drive Form Factor, 16MB Flash).
*   **Display:** 1.47" ST7789 IPS LCD (SPI interface) for status readout.
*   **Storage:** 64 GB microSD card (4-bit SDMMC interface).
*   **Host Interface:** Native USB (USB CDC / TinyUSB v2.4.0).
*   **Input Method:** Temporary Wi-Fi SoftAP + Lightweight HTTP Web Server (Smartphone UI).

## 3. Security Architecture
*   **Core Encryption:** AES-256-GCM authenticated encryption for all files and metadata.
*   **Key Protection:** 
    *   Device-specific secret stored in the ESP32-S3 eFuse (HMAC accelerator).
    *   Randomly generated 256-bit vault master key.
    *   The vault key is wrapped (encrypted) by a Key Encryption Key (KEK) derived from the eFuse secret, a random salt, and the user's PIN.
*   **Air-Gapped Radio Silence:** The Wi-Fi AP is only broadcast while the device is locked and disconnected from the host data interface. Immediately upon a successful PIN entry, the Wi-Fi and Bluetooth radios are **permanently disabled at the hardware level** for the duration of the session to eliminate remote attack surfaces.
*   **Hardware Hardening:** 
    *   Secure Boot V2 to prevent unauthorized firmware modifications.
    *   Flash Encryption to protect the firmware and on-board storage.
*   **Threat Mitigation:** 
    *   *Stolen SD Card:* Files remain encrypted. Offline brute-forcing the PIN is impractical without the physical ESP32 eFuse secret.
    *   *Stolen Device:* Firmware enforces persistent, increasing delays after failed PIN attempts (rate limiting) via NVS storage.

## 4. Software Architecture
### Firmware (ESP-IDF v6.1, C/C++)
*   **Web Server (HTTPD):** Serves the HTML/CSS PIN-pad interface locally at `192.168.4.1`.
*   **UI/Display (LVGL):** Handles the ST7789 display to show connection status, lock state, and transfer progress.
*   **Crypto Core:** Manages eFuse HMAC, key derivation, key wrapping, and AES-GCM chunk processing.
*   **Storage Layer:** Handles FATFS, the encrypted file manifest, and crash-safe file writes.
*   **USB Protocol:** TinyUSB CDC command-and-response protocol. Only initializes *after* the Wi-Fi radio is torn down.

### Desktop Client (Python, PySide6)
*   Cross-platform (Windows, macOS, Linux) file manager utility.
*   Communicates with the ESP32 via serial USB CDC (`pyserial`).
*   Provides a conventional GUI (list, upload, download, delete) without ever receiving the master encryption key.

## 5. Implementation Phases

*   **Phase 1: Hardware Bring-up & Air-Gap UI (Completed)**
    *   [x] Initialize ST7789 LCD display and backlight.
    *   [x] Mount SDMMC 4-bit microSD card via FATFS.
    *   [x] Initialize Wi-Fi SoftAP and local HTTP web server.
    *   [x] Implement "Radio Silence" transition (disable Wi-Fi, then enable TinyUSB CDC).

*   **Phase 2: Cryptographic Core & Storage (Current Phase)**
    *   [ ] Implement key derivation (PBKDF2 / HMAC) and key wrapping.
    *   [ ] Write AES-GCM chunk processing layer for SD card streaming.
    *   [ ] Validate crypto implementations with known-answer tests.

*   **Phase 3: PIN and Recovery Flow**
    *   [ ] Implement initial device enrollment and recovery key generation.
    *   [ ] Build PIN retry throttling and NVS lockout logic.

*   **Phase 4: Desktop File Manager & USB Protocol**
    *   [ ] Finalize USB CDC command protocol.
    *   [ ] Build the Python PySide6 cross-platform desktop application.
    *   [ ] Test interrupted transfers and large files.

*   **Phase 5: Production Hardening**
    *   [ ] Audit security boundaries.
    *   [ ] Enable Secure Boot V2 and Flash Encryption eFuses.
    *   [ ] Disable JTAG/debug interfaces.

## 6. USB CDC Command Protocol Definition
The desktop client and ESP32 communicate using a strict, versioned command-response protocol over serial:

| Command | Purpose |
| :--- | :--- |
| `GET_STATUS` | Returns the current locked/unlocked state and protocol version. |
| `LIST_FILES` | Returns encrypted manifest filenames (only if unlocked). |
| `UPLOAD_BEGIN` | Starts a new encrypted file transfer to the SD card. |
| `UPLOAD_CHUNK` | Sends a chunk of plaintext to be encrypted on-device. |
| `DOWNLOAD_BEGIN` | Requests an authorized file download. |
| `DOWNLOAD_CHUNK` | Returns authenticated, decrypted file data to the host. |
| `DELETE_FILE` | Deletes a specified file (only if unlocked). |
| `LOCK` | Ends the session, stops operations, and clears the active key from RAM. |

## 7. Project Directory Structure
```text
esp32-vault/
├── firmware/
│   ├── main/                 # Startup, hardware init, application state
│   ├── web_ui/               # HTML/CSS payload, HTTP endpoint handlers
│   ├── display/              # LVGL rendering for LCD status screen
│   ├── crypto/               # AES-GCM, HMAC, key wrapping
│   ├── storage/              # SD FATFS, encrypted manifest
│   ├── usb/                  # TinyUSB CDC command protocol
│   └── security/             # PIN throttling, lock state, recovery
├── desktop/
│   ├── shared/               # USB protocol and validation logic
│   ├── app/                  # PySide6 Cross-platform file manager
│   └── tests/                # Protocol and transfer tests
├── tools/
│   ├── provision/            # Explicit first-use setup scripts
│   └── vault-inspect/        # Safe encrypted-container diagnostics
├── docs/
│   ├── THREAT_MODEL.md
│   ├── KEY_DESIGN.md
│   └── PROTOCOL.md
└── tests/                    # Firmware unit tests
