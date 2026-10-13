# Threat model

## Primary goals

- A removed microSD card alone does not reveal file contents or filenames.
- Card-only attackers cannot cheaply verify PIN guesses using only card contents.
- Modified ciphertext or metadata is detected.
- Unauthorized USB commands cannot list or export plaintext while locked.
- Firmware updates are authenticated before production security is enabled.

## Out of scope / residual risks

- Malware or a compromised host OS can copy plaintext files after download.
- An unlocked device may expose data to a physically present attacker.
- Physical fault injection, side-channel analysis, invasive probing, and sophisticated hardware attacks are not guaranteed to be defeated.
- Denial of service, SD-card destruction, and rollback attacks require separate design choices.
- The ESP32-S3 is not a dedicated tamper-resistant secure element.

## Important distinction

Secure Boot authenticates firmware. Flash encryption protects supported on-chip flash contents. Neither automatically encrypts files stored on a removable microSD card. The application-level vault format must do that.

## Threats that need explicit design decisions

- PIN retry counter rollback or erasure
- Firmware downgrade and signed-update policy
- Card cloning and replay of older valid file versions
- Power loss during file replacement
- USB command abuse and host impersonation
- Data leakage through logs, filenames, file sizes, timestamps, or error messages
- Key erasure limits in compiler-managed memory
