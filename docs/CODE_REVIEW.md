# ESP32-S3 Encrypted Vault — Code & Security Review

**Review date:** 2026-10-19
**Scope:** Firmware (`firmware/main/`, ~3,700 lines of C across 10 modules) and the
desktop host tools (`desktop/`, ~1,200 lines of Python).
**Method:** Multi-agent review across six dimensions (memory safety, cryptography,
auth/session/access-control, storage durability/block device, concurrency/runtime
gate, desktop client). Each candidate finding was adversarially verified by two
independent reviewers — one tracing reachability/guards, one checking impact — and
only survivors are reported. The storage, encrypted-block-device, and concurrency
dimensions were reviewed directly (inline) after the automated agents timed out on
the larger files; their conclusions are included below.

## Executive summary

No critical or high-severity issues were found. There is **no memory-corruption,
authentication-bypass, or data-at-rest exposure**: the core design goals hold up —
AES-256-GCM at rest with a random, PIN-wrapped data key, and web-unlock gating of
host access — and there is **no hard-coded vault PIN or unlock backdoor** anywhere in
the create/unlock/change-PIN paths. The catalog/index and the encrypted USB block
device are well hardened (authenticated headers/maps/blocks with AAD binding, a redo
journal, `.tmp`/`.bak` atomic replacement with rollback, `count ≤ MAX` and
NUL-termination checks on load, fail-closed on tag mismatch). All findings are
Medium/Low and appropriate to a development build for disposable test data.

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 0 |
| Medium | 1 (M-1) |
| Low / Info | 5 (L-1…L-4, S-1) |

**Status:** all six findings below have been **fixed** in code except M-1, which was
addressed as a **documentation change** by owner decision (see each entry).

---

## M-1 (Medium) — Firmware-embedded default Wi-Fi PSK is the sole network gate

**File:** `firmware/main/vault_config.h:12-14` (consumed at `vault_config.c:15-16`,
`main.c:78-89`; public endpoints at `vault_web.c`).

The SoftAP ships a hard-coded default SSID (`MyEarPods`) and WPA2 PSK (`53cur3ty`)
compiled into the firmware and identical on every un-reconfigured device. `main.c`
loads them into the AP config with `WIFI_AUTH_WPA2_PSK`, so this PSK *is* the only
network-layer access control. The unlock portal (`/`, `/api/status`, `/api/unlock`)
is reachable without a session token, and the `Origin`/`X-Vault-Request` checks are
satisfiable by any client — so anyone in radio range who knows the firmware can join
the AP and reach the (rate-limited) unlock surface and status metadata.

This is **not** a vault-auth bypass — the data key is random and PIN-wrapped, and
online `/api/unlock` attempts are exponentially throttled (2 s → 4 s → … → ~32 s,
HTTP 429 inside the window). It is distinct from the accepted "HTTP over WPA2"
limitation, which presumes a *user-chosen secret* PSK.

**Resolution (owner decision):** documentation only — strengthen the warning rather
than change onboarding. Proportionate for a disposable-dev-data build. See
`docs/THREAT_MODEL.md` and the README security notes. A per-device random PSK (shown
on the LCD) or a forced password change at provisioning remains the robust option if
this moves toward production.

---

## L-1 (Low) — PIN buffers left un-zeroed on `change_pin` error paths — FIXED

**File:** `firmware/main/vault_web.c` (`api_change_pin_handler`).
Two early-return error paths (short-new-PIN, credential-rejected) returned before the
success-path `vault_secure_zero`, leaving the current and proposed credentials — and
the raw request body — on the httpd task stack.

**Fix:** restructured the handler so `old_pin`, `new_pin`, and `buf` are scrubbed on
**every** exit path. Also scrubbed the credential copy in `api_settings_post` before
`cJSON_Delete` (which frees without zeroing).

## L-2 (Low) — CLI crashes / aborts whole listing on a malformed device response — FIXED

**Files:** `desktop/protocol.py`, `desktop/vault_cli.py`.
Parsers raise `ValueError`/`UnicodeDecodeError`, which the client methods and
`vault_cli.main()` did not catch, so a malformed response produced a raw traceback;
and one bad filename record aborted the entire `ls` listing.

**Fix:** `vault_cli.main()` now catches `ValueError` and reports it cleanly;
`parse_list_files_response` skips a single malformed record (preserving the
structural length checks that must still fail closed) instead of aborting the listing.

## L-3 (Low) — Download did not bind the device response to the request — FIXED

**File:** `desktop/vault_client.py` (`download_file`).
The client reused the device-returned `file_id` for all chunk/end requests without
checking it matched the requested id, so a firmware bug/session mix-up could write a
different file to the user's destination (defense-in-depth; device is trusted).

**Fix:** after `DOWNLOAD_BEGIN`, assert the device-returned `file_id` equals the
requested id; raise `VaultException` on mismatch.

## L-4 (Low) — Unchecked `xRingbufferSend` could silently drop CDC bytes — FIXED

**File:** `firmware/main/cdc_protocol.c` (`cdc_rx_callback`).
Host RX bytes were pushed with a 0-tick timeout and an ignored return value; under
worker backpressure a 512-byte chunk could be dropped, truncating a frame. (Not a
memory-safety issue — the consumer is correctly bounded and the CRC check rejects the
truncated frame.)

**Fix:** apply brief backpressure (up to 20 ms) and log an overflow if the byte still
cannot be enqueued, instead of a silent drop.

## S-1 (Low) — `nvs_flash_init()` had no erase-retry on a blank/changed NVS — FIXED

**File:** `firmware/main/main.c` (`app_main`).
`nvs_flash_init()` was `ESP_ERROR_CHECK`'d directly; on a factory-fresh/unformatted
NVS (`ESP_ERR_NVS_NO_FREE_PAGES`) or a format-version change
(`ESP_ERR_NVS_NEW_VERSION_FOUND`) this aborts the boot instead of recovering.

**Fix:** restored the canonical erase-once-and-retry idiom (acts only in the error
path). Surfaced by the inline boot/concurrency review.

---

## Dropped during verification

- A claimed file-descriptor leak in `desktop/vault_client.py` `download_file` (if
  `os.fdopen` raises after `tempfile.mkstemp`) was dropped as a **false positive**:
  CPython's `io.open` cleanup closes the owning `FileIO` for the cited failure modes,
  so the fd is released. Verified empirically on Python 3.15.

## Dimensions reviewed with no actionable findings

- **Encrypted block device (`vault_drive.c`):** journal replay is idempotent across
  the test-stop interruption points; FAT32 geometry (`valid_root`, `initial_block`)
  and segment/map/block arithmetic are bounded; `transfer()` range-checks against
  capacity; crafted/truncated structures fail closed (no reformat).
- **Catalog/storage (`vault_storage.c`):** key wrap/unwrap and credential rotation
  preserve the data key; index load validates count, rejects trailing bytes, and
  enforces filename NUL-termination; upload/download validate id, sequence, and exact
  lengths with AAD binding; atomic replace with rollback throughout.
- **Concurrency/runtime gate (`vault_runtime.c`, `vault_msc.c`, `cdc_protocol.c`,
  `main.c`):** a single mutex serializes web/CDC/MSC/idle operations; idle-lock
  (`vault_runtime_poll`) runs only under the gate and is suppressed while the USB
  drive is exported; the CDC worker is drained before its ringbuffer is freed on
  shutdown. Only L-4 and S-1 (above) were raised here.

## Verification of the fixes

- Full host suite passes: 17 Python regressions + native firmware regressions
  (fragmented HTTP, sessions, settings, credentials, idle lock, USB ownership) +
  encrypted-SD-drive checks (FAT32, block IO, recovery, auth, MSC, lock/eject) under
  AddressSanitizer/UBSan.
- Clean ESP-IDF 5.5.5 target build of the fixed firmware (no warnings/errors).
