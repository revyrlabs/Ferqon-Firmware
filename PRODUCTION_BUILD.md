# Production Build Guide

This document describes how to build Ferqon firmware for production targets, create sealed production bundles, and verify builds in a clean-room environment.

## Production Targets

| Board | PlatformIO Env | Platform | Framework | Artifact |
|-------|---------------|----------|-----------|----------|
| Raspberry Pi Pico | `pico_arduino` | raspberrypi@1.19.0 | Arduino | `.uf2` |
| ESP32 DevKit | `esp32` | espressif32@7.0.1 | Arduino | `.bin` |
| ESP32-S3 DevKit | `esp32s3` | espressif32@7.0.1 | Arduino | `.bin` |
| Teensy 4.0 | `teensy40` | teensy@5.2.0 | Arduino | `.hex` |
| Teensy 4.1 | `teensy41` | teensy@5.2.0 | Arduino | `.hex` |

## Quick Start

```bash
make init              # Install dependencies and CLI
ferqonfw build pico    # Build for Pico
ferqonfw flash pico --port /dev/ttyACM0   # Flash to device
ferqonfw selftest --port /dev/ttyACM0     # Run self-test
```

## Production Configuration

Runtime defaults are centralized in `tools/production_config.json`:

| Parameter | Default | Constraint | Override |
|-----------|---------|------------|----------|
| Serial baud | 115200 | 1200–921600 | `FERQON_SERIAL_BAUD` env var |
| Heartbeat interval | 5000 ms | 1000–60000 | `FERQON_HEARTBEAT_INTERVAL_MS` env var |
| Log level | INFO | OFF / INFO / VERBOSE | `FERQON_LOG_LEVEL` env var |

The pre-build hook reads this file and emits a generated config header before each build. Build-time overrides are validated against the constraints — invalid values fail the build.

```bash
FERQON_SERIAL_BAUD=9600 ferqonfw build pico
```

## Sealed Source Selection

The production build compiles only the files listed in the `_src_filter` section of `platformio.ini`. This is an explicit allowlist — no directory-wide or implicit inclusion. To add a new source file, add it to both `_src_filter` in `platformio.ini` and `tools/production_manifest.json`. A CI test verifies these stay in sync.

## Production Bundle

The production bundle is a sealed, self-contained source tree that excludes all development-only files (tests, emulator, code generators, dev CLI). It contains only what is needed to build and flash firmware.

```bash
make bundle      # Create bundle at dist/production-bundle/
make cleanroom   # Create bundle + build all boards from clean cache
```

Clean-room verification creates a fresh bundle, sets up an isolated PlatformIO core with an empty cache, builds all five production environments from scratch, and runs a smoke test against the production CLI.

## CLI Reference

The production CLI (`ferqonfw`) is self-contained — it does not import any development-only modules. Commands are defined in `tools/ferqonfw/main.py`.

```bash
ferqonfw list                      # List available platforms
ferqonfw build <platform>          # Build firmware
ferqonfw flash <platform>          # Flash firmware
ferqonfw flash <platform> --port P # Flash to specific port
ferqonfw flash <platform> --build  # Build + flash in one step
ferqonfw clean <platform>          # Clean build artifacts
ferqonfw doctor                    # Check environment
ferqonfw packet encode <cmd>       # Encode a command to hex
ferqonfw packet decode <hex>       # Decode a hex packet
ferqonfw info <platform>           # Show platform capabilities
ferqonfw identify --port <port>    # Detect Ferqon firmware on device
ferqonfw selftest --port <port>    # Run self-test on device
```

The development CLI (`ferqonfw-dev`) adds code generation, validation, and emulator-based testing. Install with `make init-dev`.

## Reproducible Builds

For reproducible builds, set the `SOURCE_DATE_EPOCH` environment variable. This fixes the build timestamp to the specified Unix epoch.

```bash
SOURCE_DATE_EPOCH=1783708542 ferqonfw build pico
```

## CI Verification

The CI pipeline (defined in `.github/workflows/`) performs:

1. **Build Matrix**: Builds all five production environments with production-only dependencies, uploads artifacts, runs clean-room verification.
2. **Generator Drift**: Verifies that committed generated artifacts match what the generators would produce.
3. **Lint**: Python linting (ruff, black, yamllint) and platform guard checks.
4. **Native Tests**: Unity-based unit tests on the host and production CLI regression tests.
