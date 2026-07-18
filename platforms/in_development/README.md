# In-Development Platforms

This directory contains platform implementations that are **not yet production-ready**. Code here may be incomplete, experimental, or under active development.

## Production Platforms

The following boards have been promoted to production and live in `platforms/<board>/`:

- `platforms/pico/` — Raspberry Pi Pico (RP2040, Arduino backend)
- `platforms/esp32/` — ESP32 DevKit (Arduino backend)
- `platforms/esp32s3/` — ESP32-S3 DevKit (Arduino backend)
- `platforms/teensy40/` — Teensy 4.0 (Arduino backend)
- `platforms/teensy41/` — Teensy 4.1 (Arduino backend)

## Current In-Development Contents

- **pico_sdk/**: Pico-SDK/PAL implementation files for a future Pico-SDK backend.
  These reference a `core/` PAL layer that is not yet present in this repository.
  They are kept here for future development and are **not** compiled by any
  production PlatformIO environment.
- **rp2040/**: Generic RP2040 board definition — incomplete.
- **stm32f4/**: STM32F4 board definition — incomplete.
- **stm32f7/**: STM32F7 board definition — incomplete.

## Promotion Criteria

A platform can be promoted from this directory to the main `platforms/` directory when:

1. **Protocol Compliance**: Implements the v1 Ferqon protocol (0xAB + CRC-16/CCITT-FALSE)
2. **PlatformIO Environment**: Has a working `[env:<board>]` section in `platformio.ini`
3. **Generated Artifacts**: Has committed `generated/` headers verified by CI drift checks
4. **Documentation**: Has a README explaining pin mapping, capabilities, and usage
5. **Code Quality**: Passes all linting checks (naming conventions, formatting)
6. **Stability**: Has been tested on real hardware and verified to work

## Notes

- **Do not** depend on code in this directory from production firmware
- **Do not** assume any API stability in this directory
- Code here may be deleted or refactored without notice
- The production build bundle explicitly excludes this entire directory
