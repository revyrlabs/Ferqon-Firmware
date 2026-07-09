# Security Policy

## Supported Versions

| Version | Supported Until |
|---------|----------------|
| 2.x.x   | Latest release |
| 1.x.x   | End of life (no security patches) |

## Reporting a Vulnerability

If you discover a security vulnerability in Ferqon Firmware, please report it privately to us before disclosing it publicly.

**Email:** [security@revyrlabs.com](mailto:security@revyrlabs.com)

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested mitigation (if known)

We will acknowledge receipt within 48 hours and provide a timeline for remediation.

## Security Best Practices

### Firmware Signing

Ferqon Firmware supports Ed25519 signature verification for OTA updates. Ensure:
- Private keys are stored securely (hardware security module when possible)
- Public keys are embedded in firmware at build time from files outside version control
- Signature verification is enabled in production builds

### Capability System

The capability gating system (`ferqon_cap_*` macros) prevents unauthorized hardware access. Always:
- Regenerate headers after modifying `board.yml`
- Verify capability guards are present in platform code
- Run `tools/lint_platform_guards.py` before committing

### Network Security

When using network-enabled platforms (ESP32, Pico-W):
- Use TLS for all MQTT/WebSocket connections
- Validate server certificates
- Rotate credentials regularly
- Use secure credential storage (e.g., ESP32 eFuse, STM32 RDP)

### Provisioning

First-boot provisioning flows (SoftAP, BLE) should:
- Use unique SSIDs/passphrases
- Time out after a reasonable period
- Clear credentials from memory after configuration
- Support factory reset via documented procedure

## Disclosure Policy

- We will disclose vulnerabilities within 90 days of reporting
- Credit will be given to reporters who follow responsible disclosure
- We will coordinate with reporters on release timing

## Security Audits

External security audits are welcomed. Please contact [security@revyrlabs.com](mailto:security@revyrlabs.com) to coordinate.
