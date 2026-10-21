# 🔒 Security Policy

## Status

This is a **development build for disposable test data**. It has not had an
independent security audit, and several protections are knowingly missing
(device-bound keys, HTTPS, Secure Boot, flash encryption, persistent retry limits).
These are listed in [`docs/THREAT_MODEL.md`](../docs/THREAT_MODEL.md) and the README
roadmap. They're known limitations, so there's no need to report them as
vulnerabilities.

## Supported versions

No release has been tagged yet. Only the latest commit on `main` gets security fixes.

## Reporting a vulnerability

**Please don't open a public issue.** Instead, use either:

- GitHub's private reporting: **Security → Report a vulnerability** on this repository
- Email: **[support@pnwcomputers.com](mailto:support@pnwcomputers.com)**

Please include:

- The commit you tested and your board revision
- What an attacker needs (Wi-Fi range, USB access, a copied card, etc.)
- Steps to reproduce, or a proof of concept if it's safe to share
- The impact you observed

We'll acknowledge your report, keep you informed of progress, and credit you in the
changelog if you'd like. Please give us reasonable time to ship a fix before public
disclosure.

## In scope

- Authentication or lock bypass (web portal, USB CDC, USB drive)
- Plaintext or key material exposure on the card, over USB or over Wi-Fi
- Memory-safety bugs in firmware request parsing or storage code
- Failures of AES-GCM authentication checks to fail closed
- Secrets not being scrubbed after lock

## Out of scope

- The limitations already documented in `docs/THREAT_MODEL.md` (for example offline
  guessing of a short PIN from a copied card, or the shared factory Wi-Fi password)
- Physical attacks such as probing, fault injection and side channels
- Attacks that need malicious firmware already flashed on the device
