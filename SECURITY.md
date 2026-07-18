<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs -->

# Security Policy

## Supported Versions

| Version | Supported Until |
|---------|----------------|
| 1.1.x   | Latest release |
| < 1.1   | End of life (no security patches) |

## Reporting a Vulnerability

If you discover a security vulnerability in Ferqon Firmware, please report it privately to us before disclosing it publicly.

**Email:** [security@revyrlabs.com](mailto:security@revyrlabs.com)

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested mitigation (if known)

We will acknowledge receipt within 48 hours and provide a timeline for remediation.

## What This Firmware Provides

### Capability System (Pin Gating)

The capability gating system (`ferqon_cap_*()` functions in generated
`pin_macros.h`) prevents access to invalid or reserved pins. All hardware
operations in `src/` must call `ferqon_cap_pin_is_valid()` and
`ferqon_cap_pin_is_reserved()` before touching a pin. Always:
- Regenerate headers after modifying `board.yml`
- Verify capability guards are present in `src/` driver code
- Run `tools/lint_platform_guards.py` before committing

### Sealed Source Allowlist

The production build uses a sealed source allowlist (`_src_filter` in
`platformio.ini`) that explicitly lists every compiled `.cpp` file. No
directory-wide or implicit inclusion is permitted. To add a new source
file, it must be added to both `_src_filter` and
`tools/production_manifest.json`.

### Protocol Integrity

All frames are protected by CRC-16/CCITT-FALSE. The parser discards
frames with CRC mismatches and supports inter-byte and frame-assembly
timeouts for resynchronization. The dispatcher requires a `PKT_REQUEST`
packet-type byte on all command frames except `DEVICE_INFO` and
`DRIVER_INFO`, preventing accidental dispatch of malformed data.

### Device Identification

The `DEVICE_INFO` command returns a Ferqon signature TLV containing a
magic string and vendor identifier. This allows the host CLI to
classify a device as `ferqon_identified`, `ferqon_compatible`, or
`serial_unknown`. **This is an identification mechanism, not a
cryptographic authenticity guarantee** — the signature is a plaintext
magic string, not a signed token. Any device can emit it.

## What This Firmware Does NOT Provide

The following features are **not present** in this repository:

- **No OTA update mechanism** — there is no firmware-over-the-air update
  path, no signature verification of update images, and no bootloader
  integration in this codebase.
- **No networking** — there is no WiFi, MQTT, WebSocket, TLS, or HTTP
  client/server code. The firmware communicates solely over a serial
  byte stream (USB CDC or hardware UART).
- **No cryptographic operations** — there is no Ed25519, RSA, AES, or
  any other crypto implementation. The "signature" in `DEVICE_INFO` is
  a plaintext identifier, not a cryptographic signature.
- **No provisioning flows** — there is no SoftAP, BLE, or any
  first-boot provisioning code.

If your product requires any of these features, they must be implemented
in a higher layer (e.g., the Ferqon server) or in a future firmware
revision. Do not assume their presence based on documentation from
other Ferqon components.

## Disclosure Policy

- We will disclose vulnerabilities within 90 days of reporting
- Credit will be given to reporters who follow responsible disclosure
- We will coordinate with reporters on release timing

## Security Audits

External security audits are welcomed. Please contact [security@revyrlabs.com](mailto:security@revyrlabs.com) to coordinate.
