# ESP32-S3 Encrypted Vault Drive *via MicroSD Card*

Development firmware for the **Waveshare ESP32-S3-LCD-1.47**, with a self-hosted Wi-Fi controller, encrypted microSD storage exposed as a USB drive, USB CDC desktop tools, LCD status and GPIO38 RGB status LED. No buttons or touch input are required.

This snapshot integrates the firmware modules and browser configuration. **The ESP-IDF 5.5.5 target build and host regressions pass. Phone setup and encrypted USB-serial file round trips pass on the physical board. Normal USB-drive access has been added and is undergoing hardware validation.** Use test data until hardware validation and security review are complete.

## How To Use The Device

1. Insert a FAT32 microSD card and power the device over USB. Failed SD mounts never automatically format the card.
2. Connect your phone or computer to **MyEarPods**, password **53cur3ty** (factory defaults).
3. Open **http://192.168.4.1**. On first use, create and confirm a PIN or passphrase of 6–63 UTF-8 bytes. On later boots, enter the existing credential.
4. Press **Enable SD card drive** once, then use **ESP32 VAULT** in File Explorer. It uses nearly all currently free microSD capacity; user files are not stored in the ESP32 flash. **Safely eject in Windows before locking. Automatic locking waits while the drive is connected.** See [USB drive behavior and limits](docs/USB_DRIVE.md). Older phone/client files are preserved in their separate file area and can be downloaded/deleted after eject.
5. Open **Device settings** to change Wi-Fi name/password/channel, hidden SSID, idle lock, USB access, LED mode, screen brightness and screen rotation. Enter the current vault credential to save. Restart from the page to apply network, USB and display changes; reconnect using the new Wi-Fi credentials.
6. Change the vault PIN/passphrase separately using the old credential and confirmation. This rewraps the data key without rewriting file contents.

The device uses ESP32 **SoftAP** mode, often referred to in this project as “ad-hoc Wi-Fi.” It needs no router or internet access. The application assets are embedded in firmware. A browser unlock issues a random session token held only in that page's memory. Refreshing the page requires unlocking again; a new unlock replaces the previous browser token. USB access follows the device's global lock state.

## Build & Desktop Tools

Use ESP-IDF 5.5.5 (the manifest pins the verified framework and component versions). From an ESP-IDF terminal:

```sh
cd firmware
idf.py set-target esp32s3
idf.py build
idf.py -p YOUR_PORT flash monitor
```

The defaults select the supplied board's 16 MB flash, custom partition table, long FAT filenames and USB CDC. The committed dependency lockfile records the resolved `esp_tinyusb`, `esp_lvgl_port`, LVGL 9 and `led_strip` versions. Existing `sdkconfig` files can override defaults; check `idf.py menuconfig` when upgrading. Confirm the physical board/revision before flashing. Do not apply these pins to another similarly named model.

From the repository root, install `desktop/requirements.txt`, then use:

```sh
python -m desktop.vault_cli ports
python -m desktop.vault_cli status
python -m desktop.vault_cli ls
python -m desktop.vault_cli upload test.txt
python -m desktop.vault_cli download test.txt
python -m desktop.vault_cli lock
python -m desktop.vault_gui
```

Unlock through Wi-Fi before USB file operations. This is a file-transfer protocol, **not a USB Mass Storage device or an Explorer drive letter**. The firmware supports up to 256 records, 127 UTF-8 bytes per filename, and 4 GiB minus 1 byte per file; practical transfers are smaller. Browser downloads buffer the file in browser memory.

## Verification

```sh
python tests/run_checks.py
# Windows without GCC/OpenSSL: desktop checks only
python tests/run_checks.py --python-only
```

The runner executes 17 Python regression functions and a C regression executable containing the actual firmware web, configuration, runtime and storage code. The Linux host harness requires GCC, OpenSSL development headers and libcjson. It substitutes host crypto/HTTP/NVS/FreeRTOS adapters; it does not test mbedTLS or ESP32 drivers. AddressSanitizer and UndefinedBehaviorSanitizer are enabled. In a restricted process environment where LeakSanitizer cannot inspect `/proc`, run `ASAN_OPTIONS=detect_leaks=0 python tests/run_checks.py` to retain address/undefined checks without leak detection.

See [validation results](docs/VALIDATION.md), [configuration](docs/CONFIGURATION.md), [security limits](docs/THREAT_MODEL.md) and [next hardware checks](docs/HARDWARE_VALIDATION.md).

## Security Limits

- AES-256-GCM protects chunks and the catalog; PBKDF2-HMAC-SHA256 (10,000 rounds, preserved format) wraps the random data key. A short numeric PIN remains vulnerable to **offline guessing from a copied card**. No device-bound eFuse secret or recovery-key wrapper is implemented.
- Names and timestamps are encrypted in the catalog, but raw container headers, file counts, file lengths, allocation and access patterns remain observable. Nonces are random 96-bit values, not a counter with a mathematical uniqueness guarantee.
- The controller uses **HTTP over WPA2**, not HTTPS. The factory Wi-Fi password (`53cur3ty`) is **compiled into the firmware and identical on every un-reconfigured device**, so it provides no confidentiality until you change it in Device settings — do so before trusting the device. Anyone with USB access can operate the vault while it is globally unlocked. Browser tokens restrict web access; they do not make USB private to one computer.
- Retry delays are RAM-only and reset on power cycling. Settings are stored in NVS without enabling flash encryption. Secure Boot, flash encryption, FIDO security keys and credential recovery are not implemented.
- File replacement uses checked writes, flush/sync and a recoverable backup rename sequence. This is not a filesystem journal or a guarantee against arbitrary SD corruption and power loss. No anti-rollback protection exists.

No eFuses are programmed by this project.

For an isolated Ubuntu/WSL target build, run `bash tools/build_wsl.sh`. The first run downloads the official ESP-IDF sources and compiler into `/var/tmp/esp32-vault-toolchain`; subsequent runs reuse them. Outputs are copied to `artifacts/firmware`. Use `--clean-config` to verify the committed defaults. This helper builds without flashing.
