<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs -->

# Changelog

All notable changes to Ferqon Firmware will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- `tools/DRIVER_DEVELOPMENT.md` rewritten with correct `ferqon_driver_t` API
  signature, correct SSOT paths (`protocol/ssot/commands.json` +
  `tools/gen_protocol.py`), and correct error code constants
- `SECURITY.md` rewritten to accurately reflect features present in the
  firmware (removed false claims about Ed25519, OTA, MQTT, WebSocket, TLS,
  BLE, and SoftAP provisioning)
- Removed stale `RGB_DRIVER.md` and `DRIVERS.md` (documented non-existent
  drivers, architectures, and file paths)
- Removed `IP_AUDIT.md` (internal remediation report with inaccurate claims;
  not appropriate for public release)
- `docs/protocol.md` now documents the `PKT_REQUEST` requirement and the
  `DEVICE_INFO`/`DRIVER_INFO` exemption
- `NOTICE` corrected: STM32 HAL license is BSD-3-Clause, not Apache-2.0
- `ferqon_emulator.py` now enforces the `PKT_REQUEST` requirement matching
  the firmware dispatcher (previously accepted frames without it)
- `ferqon_verified` classification renamed to `ferqon_identified` to avoid
  implying cryptographic authenticity
- `platformio.ini` firmware version decoupled from protocol version
- CI `native-tests.yml` checkout SHA inconsistency fixed
- `uart.cpp` dead `#ifndef FERQON_HAS_SERIAL1` branch removed (unreachable
  on all production boards)

### Added
- `.clang-format` for C/C++ style enforcement
- `SUPPORT.md`, `GOVERNANCE.md`, `ROADMAP.md`, `CITATION.cff`
- Emulator round-trip test (`tests/test_production/test_emulator_roundtrip.py`)
- C/C++ format check step in CI lint workflow

## [1.1.0] - 2026-07-01

### Added
- Apache-2.0 open-source release with DCO and SPDX/REUSE compliance
- `pyproject.toml` with ruff and black configuration
- `ferqonfw` CLI for build, flash, info, identify, selftest, packet, and validation
- In-process serial emulator (`tools/ferqon_emulator.py`) and HIL self-test script
- `make test` target for native unit tests
- UART driver (`UART_SEND`, `UART_EXPECT`) with lazy `Serial1` initialization
- ADC driver with channel-based addressing
- Pulse measurement driver
- Debug level control command (`SET_DEBUG_LEVEL`)
- Capabilities command returning board JSON
- `FERQON_HAS_SERIAL1` build flag for secondary UART support
- Sealed source allowlist (`_src_filter`) in `platformio.ini`
- Production config system (`tools/production_config.json` + `pio_pre_build.py`)
- `tools/serial_client.py` compatibility wrapper for legacy imports

### Changed
- `src/` now contains all portable command handlers and drivers
- `tests/hil/` now contains hardware-in-the-loop test helpers
- `ferqonfw` commands now use the local `tools/serial_protocol.py` instead of an external SDK
- CI workflows now use least-privilege `permissions` and no longer clone submodules
- Dispatcher requires `PKT_REQUEST` byte on all commands except `DEVICE_INFO` and `DRIVER_INFO`

### Deprecated
- JSON board definitions (use YAML `board.yml` instead)
- `board_defs/` directory removed in favor of `platforms/<board>/board.yml`

### Removed
- `board_defs/` deprecated JSON board definitions
- Broken `examples/` scripts, `tools/diagnose.py`, `tools/run_driver_tests.py`
- Stale `tests/test_*.py`, `tests/conftest.py`, and `tests/scheduling/` unit tests

### Fixed
- `device_channels.c` regenerated with a new `device_descriptor.h` so it is self-contained and compiles
- `tools/serial_protocol.py` frame encoder and driver-call payload now match the firmware dispatcher
- `src/protocol.cpp` removed a dead `param_len > MAX_PAYLOAD` guard that caused a compiler warning
- `tools/ferqonfw` board loader, generator, and doctor commands now support `platforms/in_development/`
- `tools/ferqonfw` packet command now uses the correct CRC-16 frame format
- UART driver crash on first `UART_SEND` call (Serial1 not initialized)
- ADC driver rejecting valid reads due to pin-vs-channel parameter mismatch
- C/C++ linkage mismatch on `capabilities_driver` declaration

## [1.0.0] - 2024-08-01

### Added
- Initial release
- Support for RP2040 (Raspberry Pi Pico, Arduino backend)
- Support for ESP32, ESP32-S3 (Arduino backend)
- Support for Teensy 4.0, 4.1 (Arduino backend)
- YAML-based board definitions with generated capability headers
- Driver runtime system with command dispatcher
- Serial protocol with CRC-16/CCITT-FALSE framing
- Native unit tests (Unity framework)

[Unreleased]: https://github.com/revyrlabs/Ferqon-Firmware/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/revyrlabs/Ferqon-Firmware/releases/tag/v1.1.0
[1.0.0]: https://github.com/revyrlabs/Ferqon-Firmware/releases/tag/v1.0.0
