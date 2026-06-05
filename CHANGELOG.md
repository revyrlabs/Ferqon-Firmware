# Changelog

All notable changes to Ferqon Firmware will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- OSS restructure as Apache-2.0 licensed submodule
- YAML-based board definition system
- Capability gating with runtime validation
- Protocol subsystem with state machines
- CI pipeline with generator drift detection

### Changed
- Moved `drivers/` under `core/drivers/`
- Renamed `hil_configs/` to `examples/`
- Archived legacy CommandParser/IOController to `legacy/`

### Deprecated
- JSON board definitions (use YAML `board.yml` instead)

## [1.0.0] - 2024-XX-XX

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

[Unreleased]: https://github.com/repvi/ferqon_firmware/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/repvi/ferqon_firmware/releases/tag/v1.0.0
