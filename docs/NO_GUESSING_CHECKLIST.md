# Verification status and unresolved facts

This starter is intentionally conservative. The following items are **not yet verified on physical hardware**:

- Exact Waveshare board PCB revision and GPIO assignments for the external navigation buttons.
- Exact ESP-IDF release and component versions that will compile and run this project.
- LCD driver/controller configuration and working display initialization.
- 64 GB card filesystem, bus mode, and maximum supported behavior in the chosen driver.
- USB connector route on the exact board and native USB CDC enumeration on the selected computer.
- Correct eFuse key-block availability and the selected HMAC key purpose/API for the exact chip revision.
- Complete cryptographic design, PIN key derivation, recovery wrapper, nonce allocation and anti-rollback.
- Firmware update and recovery behavior after production security eFuses are set.
- Cross-platform desktop packaging and USB permissions/drivers.

Before implementation, consult:
- Official Waveshare board wiki/schematic: https://www.waveshare.com/wiki/ESP32-S3-LCD-1.47
- ESP-IDF ESP32-S3 USB device documentation: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/usb_device.html
- ESP-IDF ESP32-S3 Secure Boot v2: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/security/secure-boot-v2.html
- ESP-IDF ESP32-S3 security feature enablement workflows: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/security/security-features-enablement-workflows.html

The Waveshare wiki could not be independently fetched in this research pass (HTTP access denied by the site), so no pin assignments are asserted here. Do not treat earlier generic GPIO statements as a verified wiring plan.
