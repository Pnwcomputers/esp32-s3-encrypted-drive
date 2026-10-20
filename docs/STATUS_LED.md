# Onboard RGB status LED

The Waveshare **ESP32-S3-LCD-1.47** board's schematic identifies its onboard WS2812B-0807 RGB LED data input as **GPIO38**. This mapping is for the non-B `ESP32-S3-LCD-1.47` board only; do not assume it applies to similarly named revisions. Confirm the silkscreen and schematic for the physical board before flashing.

The firmware uses Espressif's `led_strip` component and a low-priority, non-blocking task. Calling `vault_status_led_set_state()` changes the requested state without adding sleeps to authentication or transfer handlers. LED output is deliberately brightness-limited.

| State | Indicator | Firmware integration |
|---|---|---|
| `VAULT_LED_LOCKED` | Slow blue pulse | Default after reset/startup |
| `VAULT_LED_PIN_ENTRY` | Steady amber | PIN-entry feedback |
| `VAULT_LED_AUTH_SUCCESS` | Brief green, then green breathing | Successful authenticated unlock |
| `VAULT_LED_AUTH_FAILURE` | Two short red flashes, then amber | Rejected credential |
| `VAULT_LED_UNLOCKED` | Subtle green breathing | Unlocked state |
| `VAULT_LED_TRANSFER` | Purple pulse | Wi-Fi and USB transfer start |
| `VAULT_LED_TRANSFER_COMPLETE` | Brief green, then green breathing | Wi-Fi and USB transfer completion |
| `VAULT_LED_RECOVERY_ERROR` | Repeating triple white flash | API is available for recovery/security faults; is latched until `vault_status_led_clear_recovery_fault()` is called |

Transfer integration example:

```c
vault_status_led_set_state(VAULT_LED_TRANSFER);
/* Perform and validate transfer. */
vault_status_led_set_state(VAULT_LED_TRANSFER_COMPLETE);
```

Do not encode PIN digits, secret material, filenames, or detailed failure causes in LED patterns. Security/recovery faults should take precedence over ordinary progress indications; callers must explicitly clear the fault with `vault_status_led_clear_recovery_fault(next_state)` after handling it.

## Configuration and security status

The browser settings page supports normal, dim and off LED modes. Saved LED mode applies after restart. Off mode suppresses every pattern, including recovery errors. LED patterns supplement the display and are not an authentication boundary. The controller uses persistent Wi-Fi; locking and unlocking are handled through the web page. No physical-button PIN flow is used. See THREAT_MODEL.md for the remaining security limits.

## Build note

The `espressif/led_strip` component is declared in `firmware/main/idf_component.yml`. Component Manager will need to resolve it during an ESP-IDF build. The uploaded project was not built on physical hardware as part of this change; verify compilation and LED colors on the exact board before relying on the indicator.
