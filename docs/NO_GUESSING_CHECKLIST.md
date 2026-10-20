# Verify before hardware use

- Exact Waveshare ESP32-S3-LCD-1.47 board revision, pin map and 16 MB flash.
- FAT32 card, long filenames and the actual SD interface wiring.
- ESP-IDF 5.x component versions, build/link result and USB CDC configuration.
- Display rotation/brightness and GPIO38 RGB colors on the physical board.
- Persistent SoftAP reachability during lock/unlock and saved Wi-Fi reconnection.
- Idle lock, interrupted transfers and metadata backup recovery on copied test data.
- Firmware stack watermarks and available heap with Wi-Fi, LCD and USB active.
- Security claims against THREAT_MODEL.md; no offline-guess resistance or recovery key is implemented.

No physical navigation buttons or touch controls are required. Do not add guessed button GPIO assignments.
