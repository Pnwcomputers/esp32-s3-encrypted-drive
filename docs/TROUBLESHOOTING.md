# 🔍 Troubleshooting

Before experimenting, keep a copy of the microSD card. **Never accept a Windows
"format this disk" prompt** for the vault drive; it replaces the logical filesystem.

## Wi-Fi & web portal

### I can't see the `MyEarPods` network
- Make sure the device is powered and the LCD shows status.
- If you enabled **Hidden network**, join it manually by name.
- If you changed the network name/password, the new settings apply only after
  **Restart** or a power cycle.
- Lost the Wi-Fi credentials? There is no physical reset. Resetting NVS needs ESP-IDF
  access (`idf.py erase-flash` and reflash, or erase the NVS partition). This resets
  settings only; it does **not** erase or recover the vault on the card.

### `http://192.168.4.1` won't load
- Phones may drop a Wi-Fi network that has no internet. Choose "stay connected" or
  turn off mobile data while using the portal.
- Type the address exactly; the server rejects other Host names, and HTTPS isn't
  supported.

### The page says I'm logged out after a refresh
That's expected. Session tokens live only in the page; reloading discards them. Unlock
again.

## Unlocking

### Wrong PIN, or unlock is slow
After failed attempts the device adds a growing delay (up to ~32 s). Wait and try
again. The delay resets on power cycle.

### Setup/storage error instead of "wrong PIN"
The card couldn't be read or written. Check that it's FAT32, inserted fully, and not
write-protected or full. See the serial log (`idf.py monitor`) for details.

### I forgot the PIN/passphrase
There is no recovery. The data key can't be unwrapped without it. See
[PROVISIONING_AND_RECOVERY.md](PROVISIONING_AND_RECOVERY.md).

## microSD card

### "Storage unavailable" / card not detected
- The card must be **FAT32**. Large cards often ship as exFAT; reformat them to FAT32
  on a computer first (with no vault data on them).
- Reseat the card and power-cycle. The firmware never auto-formats a card that fails
  to mount.

## USB drive (MSC)

### "USB drive could not be opened."
- Unlock first, and check **USB access** is enabled in Device settings.
- Make sure the card has at least ~66 MB free.
- Older firmware built without PSRAM fails here; rebuild from this repo (PSRAM is
  enabled in `sdkconfig.defaults`).

### The drive doesn't appear after unlock or eject
Press **Reconnect SD card drive**. If Windows removed the whole USB device, unplug
and replug the cable, then unlock and reconnect.

### I can't lock, or auto-lock doesn't fire
Locking, settings changes and legacy file operations wait until you **safely eject**
the drive in Windows, so cached writes aren't lost. Eject, then lock.

### Writes are very slow
Expected for now (tens of KB/s). Each 4 KB block is encrypted and journaled with
`fsync` before Windows is told it's written. Faster batching is on the roadmap.

### I/O error reading a file
The stored block failed authentication or is missing (corruption, an external edit
to the card, or a power loss outside the journal's protection). The drive fails
closed instead of returning bad data. Restore from your card copy.

## USB CDC desktop tools

### `vault_cli` can't find the device or picks the wrong port
Run `python -m desktop.vault_cli ports` and pass the port explicitly (see `--help`).
Make sure **USB access** is enabled and the device has been restarted after changing
it.

### Commands return "locked"
USB has no unlock command. Unlock through the web portal first.

### An upload was interrupted and now everything says "busy"
The interrupted transfer holds its slot. Lock and unlock the vault, then retry.

## Building

### Build fails with ESP-IDF 6.x or a different 5.x
Use ESP-IDF **5.5.5**, or run `bash tools/build_wsl.sh`, which downloads the pinned
toolchain into a separate cache.

### Native tests fail with LeakSanitizer errors
In containers where LeakSanitizer can't read `/proc`, run
`ASAN_OPTIONS=detect_leaks=0 python tests/run_checks.py`.

---

Still stuck? Open an issue with the board revision, ESP-IDF version, card details and
the `idf.py monitor` log.
