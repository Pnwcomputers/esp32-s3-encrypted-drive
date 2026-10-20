# 🤝 Contributing to ESP32-S3 Encrypted Vault Drive

Thanks for your interest in contributing! This is **security-sensitive embedded firmware** (ESP-IDF/C) plus a Python desktop client. This guide covers how to build, test, and submit changes.

> ⚠️ This is a development build for disposable test data. Treat anything touching crypto, authentication, storage format, or lock state with extra care — see [`docs/THREAT_MODEL.md`](../docs/THREAT_MODEL.md) and [`docs/CODE_REVIEW.md`](../docs/CODE_REVIEW.md).

## 🎯 Ways to Contribute

### 🐛 Bug Reports
- Use the bug report template
- Include your **exact board revision**, ESP-IDF version, and microSD details
- Attach the serial/`idf.py monitor` log and clear reproduction steps

### 💡 Feature Requests
- Use the feature request template; tag the title with `[FEATURE]`
- Describe the use case and the security/reliability impact
- Check the [Roadmap](../README.md#-roadmap-reliability--security) first — it may already be planned

### 🔧 Code Contributions
- Fork, branch, keep the host test suite green, and update docs
- Match the surrounding code style (the firmware is deliberately compact C)
- Keep the desktop `protocol.py` wire format in sync with the firmware and [`docs/PROTOCOL.md`](../docs/PROTOCOL.md)

### 📖 Documentation
- Clarify the README/docs, add validation evidence, fix typos
- Don't overstate security posture — keep claims aligned with what's actually verified

## 🧰 Development Environment

**Firmware** (ESP-IDF **5.5.5**, target `esp32s3`):

```sh
cd firmware
idf.py set-target esp32s3
idf.py build
idf.py -p YOUR_PORT flash monitor
```

Or build in an isolated, reproducible toolchain without touching a system ESP-IDF:

```sh
bash tools/build_wsl.sh               # first run downloads pinned ESP-IDF + compiler
bash tools/build_wsl.sh --clean-config  # verify the committed sdkconfig defaults
```

**Desktop client** (Python): install `desktop/requirements.txt`, then run `python -m desktop.vault_cli ...`.

## ✅ Testing Requirements

Run the regression suite before opening a PR:

```sh
python tests/run_checks.py              # Python + native (ASan/UBSan) firmware checks
python tests/run_checks.py --python-only  # desktop checks only (no GCC/OpenSSL needed)
```

- The native harness needs **GCC, OpenSSL dev headers, and libcjson**, and runs the real firmware web/config/runtime/storage/drive code under AddressSanitizer + UndefinedBehaviorSanitizer.
- **New firmware logic should keep the host suite green and add coverage** where the host adapters allow (crypto/HTTP/NVS/FreeRTOS are substituted; mbedTLS and ESP32 drivers are not exercised).
- A clean `idf.py build` / `tools/build_wsl.sh` (no warnings — `-Werror` is on) is required.
- Changes that affect hardware behavior should note what was verified on a physical board vs. host-only.

## 🔒 Security-Sensitive Code — Please Keep In Mind

- **Fail closed.** Decryption/authentication failures must not degrade to fail-open. Preserve AAD binding and tag checks.
- **Scrub secrets.** Zero PIN/passphrase buffers and key material on every exit path (`vault_secure_zero`).
- **No hard-coded credentials or bypasses.** The only unlock path is the PIN/passphrase that unwraps the random data key.
- **Don't weaken durability.** Keep the redo-journal + atomic `.tmp`/`.bak` replacement semantics intact.
- **No casual eFuse / Secure Boot / flash-encryption changes.** These are irreversible on hardware — propose them as reviewed, opt-in changes.

## 🔄 Pull Request Flow

1. Fork and clone your fork
2. Branch: `git checkout -b feature/your-feature-name`
3. Make changes; build clean and keep tests green
4. Commit with clear messages (see below)
5. Push and open a PR using the template
6. A maintainer reviews correctness, security impact, and docs before merge

## 🏷️ Commit Message Format

Conventional-commits style:

```text
type(scope): description

feat(drive): coalesce redo-journal writes to speed up USB writes
fix(web): scrub change_pin buffers on all error paths
docs(readme): add reliability & security roadmap
test(storage): add truncated-catalog regression
```

## 🛡️ Security Issues

**Do not open a public issue for vulnerabilities.** Email **[support@pnwcomputers.com](mailto:support@pnwcomputers.com)** with a proof of concept (if safe) and allow reasonable time for a fix before disclosure.

## 📞 Getting Help

- Check existing issues and the [`docs/`](../docs/) folder
- Open a GitHub issue or discussion
- Email **[support@pnwcomputers.com](mailto:support@pnwcomputers.com)**

Thank you for helping make this project better and safer! 🙏
