# Device configuration

Connect to the device's Wi-Fi and open http://192.168.4.1. All management uses this self-hosted page; there are no physical navigation buttons or touch controls.

| Setting | Accepted values | Factory default | Applies |
|---|---|---|---|
| Network name | 1–32 UTF-8 bytes, no control characters | MyEarPods | Restart |
| Wi-Fi password | 8–63 printable ASCII characters; blank keeps existing | 53cur3ty | Restart |
| Channel | 1–11 | 1 | Restart |
| Hidden network | On/off | Off | Restart |
| Idle lock | 0 disables, otherwise 30–86400 seconds | 600 | After saving |
| USB CDC access | Enabled/disabled | Enabled | Restart |
| LED mode | Normal / dim / off | Normal | Restart |
| LCD brightness | 10–100% | 100% | Restart |
| LCD rotation | 0 / 90 / 180 / 270 degrees | 180 | Restart |

Saving settings requires an unlocked browser session and the current vault credential. The Wi-Fi password is never returned by the settings API. Settings are persisted as a single versioned NVS blob; old per-setting NVS values are read for migration. An invalid saved configuration falls back to defaults. Write failures are reported and do not replace the active configuration in RAM.

The idle timer is refreshed by file and management operations over either transport, not by status polling. HTTP requests, USB commands and idle locking share a mutex. A running HTTP file transfer holds that mutex; the timer cannot interrupt a transfer halfway through a storage operation. USB transfers with a long gap between chunk requests can time out. Wi-Fi remains available when the vault locks.

After saving a new network name/password, use Restart device or power-cycle. The existing connection remains usable until then. Record the new settings before restarting: this hardware has no physical settings-reset control. A hidden network must be joined manually. If Wi-Fi credentials are lost, configuration recovery currently requires ESP-IDF access to reset NVS; do not erase the SD card. That procedure is not exposed as a web action.

PIN/passphrase setup accepts 6–63 UTF-8 bytes. Existing shorter credentials can still unlock imported version-1 vaults, but new credentials must meet the minimum. A forgotten vault credential cannot be recovered by resetting Wi-Fi/NVS. No FIDO/security-key or recovery-secret enrollment exists.

## HTTP API

All POST requests require `X-Vault-Request: 1`. Protected requests also require the `X-Vault-Token` returned by `/api/unlock`. The server requires the Host header to be 192.168.4.1 (optionally with :80), rejects foreign Origin headers, and does not enable cross-origin access. Page/session responses use `Cache-Control: no-store`.

| Endpoint | Method | Access / purpose |
|---|---|---|
| `/` | GET | Embedded local page |
| `/api/status` | GET | Public provisioning/session state; public file count hidden |
| `/api/unlock` | POST | JSON `pin`; creates a new vault only if no metadata file exists, or unlocks an existing vault; returns token |
| `/api/settings` | GET | Session; returns settings excluding Wi-Fi password |
| `/api/settings` | POST | Session + JSON `current_pin`; optional changed settings; blank `wifi_pass` preserves existing |
| `/api/change_pin` | POST | Session + JSON `old_pin`, `new_pin` |
| `/api/restart` | POST | Session; locks then restarts |
| `/api/lock` | POST | Session; closes transfers and erases data key |
| `/api/files` | GET | Session; JSON catalog |
| `/api/upload?name=...` | POST | Session; raw file body |
| `/api/download?id=...` | GET | Session; decrypted file response |
| `/api/delete` | POST | Session; JSON hex `id` |

Tokens are not persisted or put in URLs. Refreshing the page discards its token. Only one browser token is active at a time. An interrupted USB upload may hold its transfer slot until the vault is locked; lock and unlock before retrying. USB commands have no PIN-unlock operation; authenticate through Wi-Fi first.
