# Changelog

All notable changes to Ferqon Firmware will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Apache-2.0 open-source release with DCO and SPDX/REUSE compliance
- `pyproject.toml` with ruff and black configuration
- `ferqonfw` CLI for build, flash, info, identify, selftest, packet, and validation
- In-process serial emulator (`tools/ferqon_emulator.py`) and HIL self-test script
- `make test` target for native unit tests

### Changed
- `src/` now contains all portable command handlers and drivers
- `tests/hil/` now contains hardware-in-the-loop test helpers
- `ferqonfw` commands now use the local `tools/serial_protocol.py` instead of an external SDK
- CI workflows now use least-privilege `permissions` and no longer clone submodules

### Deprecated
- JSON board definitions (use YAML `board.yml` instead)
- `board_defs/` directory removed in favor of `platforms/<board>/board.yml`

### Removed
- `board_defs/` deprecated JSON board definitions
- Broken `examples/` scripts, `tools/diagnose.py`, `tools/run_driver_tests.py`, `tools/serial_client.py`
- Stale `tests/test_*.py`, `tests/conftest.py`, and `tests/scheduling/` unit tests

### Fixed
- `device_channels.c` regenerated with a new `device_descriptor.h` so it is self-contained and compiles
- `tools/serial_protocol.py` frame encoder and driver-call payload now match the firmware dispatcher
- `src/protocol.cpp` removed a dead `param_len > MAX_PAYLOAD` guard that caused a compiler warning
- `tools/ferqonfw` board loader, generator, and doctor commands now support `platforms/in_development/`
- `tools/ferqonfw` packet command now uses the correct CRC-16 frame format

## [1.0.0] - 2024-08-01

### Added
- Initial release
- Support for RP2040 (Pico, generic RP2040)
- Support for ESP32, ESP32-S3
- Support for STM32F4, STM32F7
- Support for Teensy 4.0, 4.1
- Arduino and Pico SDK backends
- JSON-based board definitions
- Driver runtime system
- Multicore scheduling
- Native unit tests

[Unreleased]: https://github.com/repvi/Ferqon-Firmware/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/repvi/Ferqon-Firmware/releases/tag/v1.0.0
