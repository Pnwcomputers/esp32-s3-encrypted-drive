# Hardware validation checklist

Do not wire external buttons based on guessed GPIOs.

Before hardware integration, verify from the exact board revision's schematic:
- LCD SPI pins and reset/backlight pins
- SD-card SPI/SDMMC pins and card-detect behavior
- USB D+/D- route and connector
- onboard BOOT and RESET buttons
- pins used by onboard peripherals, strapping, flash/PSRAM, and any expansion connector
- actual supply/logic levels for external buttons

Then:
1. Record board PCB revision and source document version.
2. Test each proposed button input with a non-destructive GPIO test.
3. Confirm no boot-strapping conflict at reset.
4. Confirm USB CDC still enumerates after button wiring.
5. Confirm SD reads/writes remain reliable.
6. Test button bounce and stuck-button conditions.
7. Keep wiring diagram and tested pin map in version control.
