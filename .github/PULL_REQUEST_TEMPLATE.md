## Summary
Explain what this PR changes and why.

## Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Security hardening
- [ ] Docs update
- [ ] Refactor
- [ ] Other (describe):

## Checklist
- [ ] `python tests/run_checks.py` passes (or `--python-only` if no native toolchain; say so)
- [ ] Firmware builds clean with ESP-IDF 5.5.5 (`idf.py build` or `tools/build_wsl.sh`)
- [ ] Secrets are scrubbed on every exit path; failures still fail closed
- [ ] `desktop/protocol.py` and `docs/PROTOCOL.md` match the firmware (if the wire format changed)
- [ ] Docs/README updated as needed, plus an entry under `[Unreleased]` in `Logs/CHANGELOG.md`
- [ ] Linked related issues (e.g., fixes #123)

## Verification
What was tested on a **physical board** vs. **host-only**?

## Breaking changes
On-card format, protocol or settings changes, and migration steps.
