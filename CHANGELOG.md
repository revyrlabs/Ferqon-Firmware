# Changelog

All notable changes to Ferqon Firmware will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- OSS restructure as Apache-2.0 licensed submodule
- YAML-based board definition system (single source of truth)
- Capability gating via generated `ferqon_cap_*()` helpers
- Protocol subsystem with frame-based serial parser
- CI pipeline with generator drift detection and build matrix
- Native unit tests with Unity

### Changed
- `src/` now contains all portable command handlers and drivers
- `examples/` now contains HIL example scripts
- `tests/hil/` now contains hardware-in-the-loop test helpers

### Deprecated
- JSON board definitions (use YAML `board.yml` instead)
- `board_defs/` directory removed in favor of `platforms/<board>/board.yml`

### Removed
- `board_defs/` deprecated JSON board definitions

### Fixed
- `device_channels.c` regenerated with a new `device_descriptor.h` so it is self-contained and compiles

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

[Unreleased]: https://github.com/repvi/Ferqon/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/repvi/Ferqon/releases/tag/v1.0.0
