# In-Development Platforms

This directory contains platform implementations that are **not yet production-ready**. Code here may be incomplete, experimental, or under active development.

## Promotion Criteria

A platform can be promoted from this directory to the main `platforms/` directory when:

1. **Protocol Compliance**: Implements the v1 Ferqon protocol (0xAB + CRC-16/CCITT-FALSE)
2. **Test Coverage**: Has unit tests for platform-specific drivers
3. **Documentation**: Has a README explaining pin mapping, capabilities, and usage
4. **Code Quality**: Passes all linting checks (naming conventions, formatting)
5. **Stability**: Has been tested on real hardware and verified to work

## Current Status

- **arduino/**: Legacy Arduino backend (pre-v1 protocol) - needs v1 protocol implementation
- **esp32/**: ESP32 platform - incomplete
- **esp32s3/**: ESP32-S3 platform - incomplete
- **rp2040/**: Generic RP2040 platform - incomplete
- **stm32f4/**: STM32F4 platform - incomplete
- **stm32f7/**: STM32F7 platform - incomplete
- **teensy40/**: Teensy 4.0 platform - incomplete
- **teensy41/**: Teensy 4.1 platform - incomplete
- **core/**: Legacy core runtime - being replaced by new modular structure
- **protocol/**: Legacy protocol implementation - replaced by v1 protocol in src/protocol/

## Migration Path

1. Update platform to use v1 protocol
2. Add platform-specific drivers in the new structure
3. Add tests
4. Add documentation
5. Submit for review and promotion

## Notes

- **Do not** depend on code in this directory from production firmware
- **Do not** assume any API stability in this directory
- Code here may be deleted or refactored without notice
