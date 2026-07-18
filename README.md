<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs -->

# Ferqon Firmware

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![CI: Native Tests](https://img.shields.io/github/actions/workflow/status/revyrlabs/Ferqon-Firmware/native-tests.yml?label=native%20tests)](https://github.com/revyrlabs/Ferqon-Firmware/actions/workflows/native-tests.yml)
[![CI: Lint](https://img.shields.io/github/actions/workflow/status/revyrlabs/Ferqon-Firmware/lint.yml?label=lint)](https://github.com/revyrlabs/Ferqon-Firmware/actions/workflows/lint.yml)
[![Protocol Version](https://img.shields.io/badge/protocol-1.1.0-green.svg)](docs/protocol.md)
[![Firmware Version](https://img.shields.io/badge/firmware-1.1.0-green.svg)](CHANGELOG.md)

Portable, Apache-2.0 licensed firmware for the Ferqon real-time interaction node. Supports multiple MCU platforms (RP2040, ESP32, Teensy) with a portable core and board-specific configuration via generated capability headers.

## Table of Contents

- [Quick Start](#quick-start)
- [Supported Platforms](#supported-platforms)
- [Architecture](#architecture)
- [Documentation](#documentation)
- [CLI Reference](#cli-reference)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)
- [Security](#security)

## Quick Start

### Prerequisites

- **Python 3.10+** — for the build CLI and tools
- **Git** — to clone the repo
- **USB cable** — to flash and communicate with the board

PlatformIO is installed automatically by `make init`.

### One-Command Setup

```bash
git clone https://github.com/revyrlabs/Ferqon-Firmware.git
cd Ferqon-Firmware
make init
```

`make init` installs PlatformIO, pyserial, PyYAML, and the `ferqonfw` CLI, then verifies the environment with `ferqonfw doctor`.

> **Note (Linux):** On modern Debian/Ubuntu/Fedora the system Python is
> externally managed (PEP 668), so `make init` automatically creates a
> virtual environment at `.venv/` and installs there. Activate it before
> using the CLI:
> ```bash
> source .venv/bin/activate
> ```
> If you prefer to use your own venv, activate it first — `make init`
> detects an active venv and installs into it directly.

### Build

All building is done through the `ferqonfw` CLI — the Makefile handles setup only.

```bash
ferqonfw build pico          # Build for Raspberry Pi Pico
ferqonfw build esp32         # Build for ESP32
ferqonfw build all           # Build all production boards
ferqonfw list                # List available platforms
ferqonfw info pico           # Show Pico capabilities
```

### Flash and Test

All device operations are handled by the `ferqonfw` CLI.

```bash
# Build and flash in one step:
ferqonfw flash pico --port /dev/ttyACM0 --build

# Or build first, then flash separately:
ferqonfw build pico
ferqonfw flash pico --port /dev/ttyACM0

# Identify and test a connected device:
ferqonfw identify --port /dev/ttyACM0    # Detect Ferqon firmware
ferqonfw selftest --port /dev/ttyACM0    # Run command-matrix self-test
```

> **Note:** `--port` is optional — if omitted, PlatformIO auto-detects the serial port. On Linux, ports are typically `/dev/ttyACM0` or `/dev/ttyUSB0`. On macOS, `/dev/cu.usbmodem*`. On Windows, `COM3` etc.

### Advanced Build Options

Build configuration (baud rate, heartbeat interval, log level) can be overridden at build time via environment variables. See `tools/production_config.json` for defaults and constraints.

```bash
FERQON_SERIAL_BAUD=9600 ferqonfw build pico              # Custom baud rate
FERQON_HEARTBEAT_INTERVAL_MS=10000 ferqonfw build esp32   # Custom heartbeat
FERQON_LOG_LEVEL=VERBOSE ferqonfw build teensy40          # Custom log level
```

The CLI also supports building from a different project directory:

```bash
ferqonfw build pico --project-dir /path/to/firmware
```

### Development Setup

For development (includes test/lint tools and the `ferqonfw-dev` CLI):

```bash
make init-dev                      # Install with development extras (one command)
ferqonfw-dev test                  # Native unit tests (no hardware required)
ferqonfw-dev selftest --emulator   # Emulator-based self-test
```

## Supported Platforms

**Production:**

| Platform | MCU | Backend | Build Command |
|----------|-----|---------|---------------|
| pico | RP2040 | Arduino | `ferqonfw build pico` |
| esp32 | ESP32 | Arduino | `ferqonfw build esp32` |
| esp32s3 | ESP32-S3 | Arduino | `ferqonfw build esp32s3` |
| teensy40 | Teensy 4.0 | Arduino | `ferqonfw build teensy40` |
| teensy41 | Teensy 4.1 | Arduino | `ferqonfw build teensy41` |

**Community (in development):**

| Platform | MCU | Build Command |
|----------|-----|---------------|
| mega2560 | ATmega2560 (Arduino Mega) | `ferqonfw build mega2560` |
| esp8266 | ESP8266 (NodeMCU) | `ferqonfw build esp8266` |
| stm32bluepill | STM32F103C8 (Blue Pill) | `ferqonfw build stm32bluepill` |

All supported boards must have at least 2 hardware UARTs (one for the control protocol, one for the UART driver). Run `ferqonfw list` to see all available platforms. See [docs/adding_a_board.md](docs/adding_a_board.md) to add support for a new board.

## Architecture

The firmware has a portable core that calls Arduino hardware APIs directly, with board-specific limits enforced by generated capability headers. Each board is defined by a single `board.yml` file; the generator produces C headers that enforce pin validity, ADC support, and reserved-pin protection at compile time.

A platform abstraction layer (PAL) for non-Arduino backends is under development. See [docs/architecture.md](docs/architecture.md) for details.

### Production / Development Separation

- **Production CLI** (`ferqonfw`): Build, flash, identify, selftest. Self-contained, no dev-only imports.
- **Development CLI** (`ferqonfw-dev`): Code generation, validation, emulator-based testing. Not included in the production bundle.
- **Production Bundle**: A sealed source tree that excludes all development-only files. Created with `make bundle`, verified with `make cleanroom`.

## Documentation

- [PRODUCTION_BUILD.md](PRODUCTION_BUILD.md) — Production build guide, bundle creation, clean-room verification
- [docs/architecture.md](docs/architecture.md) — System architecture and design principles
- [docs/adding_a_board.md](docs/adding_a_board.md) — Guide for porting to new hardware
- [docs/protocol.md](docs/protocol.md) — Serial protocol specification
- [docs/validation_model.md](docs/validation_model.md) — Three-layer validation strategy
- [docs/capability_reference.md](docs/capability_reference.md) — Capability API reference
- [tools/DRIVER_DEVELOPMENT.md](tools/DRIVER_DEVELOPMENT.md) — How to write and register new command drivers
- [CHANGELOG.md](CHANGELOG.md) — Release history

## CLI Reference

The `ferqonfw` CLI is the primary interface for building, flashing, and testing firmware. The Makefile handles environment setup and production bundling only.

### `ferqonfw` — Production CLI

| Command | Purpose |
|---------|---------|
| `ferqonfw list` | List all available platforms |
| `ferqonfw build <board>` | Build firmware for a board |
| `ferqonfw build all` | Build all production boards |
| `ferqonfw flash <board> --port <port>` | Flash firmware to a device |
| `ferqonfw flash <board> --port <port> --build` | Build + flash in one step |
| `ferqonfw clean <board>` | Clean build artifacts for a board |
| `ferqonfw clean all` | Clean all production boards |
| `ferqonfw info <board>` | Show board capabilities (pins, ADC, peripherals) |
| `ferqonfw identify --port <port>` | Detect Ferqon firmware on a connected device |
| `ferqonfw selftest --port <port>` | Run a command-matrix self-test on a device |
| `ferqonfw doctor` | Check environment and dependencies |
| `ferqonfw packet encode <cmd>` | Encode a protocol command to hex |
| `ferqonfw packet decode <hex>` | Decode a hex packet |

### `ferqonfw-dev` — Development CLI

| Command | Purpose |
|---------|---------|
| `ferqonfw-dev gen all` | Generate all protocol and board artifacts |
| `ferqonfw-dev gen board <name>` | Generate per-board capability tables |
| `ferqonfw-dev validate` | Validate SSOT JSON files |
| `ferqonfw-dev drivers list` | List drivers and their status |
| `ferqonfw-dev test` | Run native unit tests (no hardware required) |
| `ferqonfw-dev selftest --emulator` | Self-test via in-process emulator |
| `ferqonfw-dev identify --emulator` | Identify via in-process emulator |

### `make` — Setup and Bundling

| Command | Purpose |
|---------|---------|
| `make init` | Install production deps + `ferqonfw` CLI |
| `make init-dev` | Install production + development deps |
| `make doctor` | Check environment |
| `make bundle` | Create sealed production source bundle |
| `make cleanroom` | Build all boards from clean-room bundle |

Run `ferqonfw --help`, `ferqonfw-dev --help`, or `make help` for the full command lists. See [TOOLS.md](TOOLS.md) for details on each tool.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow, coding standards, and DCO sign-off requirements.

## License

This project is licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full license text and [NOTICE](NOTICE) for third-party dependency attributions.

## Support

- **Bug reports & feature requests:** [GitHub Issues](https://github.com/revyrlabs/Ferqon-Firmware/issues)
- **Security vulnerabilities:** See [SECURITY.md](SECURITY.md) for private disclosure
- **Private questions:** [support@revyrlabs.com](mailto:support@revyrlabs.com)
- **Code of Conduct:** See [CONTRIBUTING.md](CONTRIBUTING.md)

## Security

See [SECURITY.md](SECURITY.md) for the security policy, supported versions, and vulnerability reporting instructions.
