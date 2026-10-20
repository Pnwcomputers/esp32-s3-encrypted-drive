# Desktop tools

Install `requirements.txt` with Python 3.10+ and run from the repository root:

```sh
python -m desktop.vault_cli ports
python -m desktop.vault_cli status
python -m desktop.vault_cli upload sample.txt
python -m desktop.vault_cli ls
python -m desktop.vault_cli download sample.txt
python -m desktop.vault_cli lock
python -m desktop.vault_gui
```

Use `--help` for per-command options and selecting a serial port. `example_cli.py` is a compatibility entry point to the same CLI. Unlock using the device's self-hosted Wi-Fi page before transferring files. USB CDC must be enabled in device settings. The host handles selected plaintext files; encryption and key management occur on the device. The GUI requires PySide6; CLI serial access requires pyserial.

Protocol and mock-client regressions do not need real hardware. Run `python tests/run_checks.py` from the project root for Python and Linux-host firmware checks. See `docs/VALIDATION.md` for prerequisites and limitations.
