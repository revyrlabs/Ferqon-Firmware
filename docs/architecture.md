# Architecture

Ferqon firmware is a portable command processor that runs on multiple MCU families with minimal platform-specific code.

## Design Principles

The firmware follows a Linux-kernel-style split between portable and platform-specific code:

1. **Portable core** (`src/`): Command parser, protocol framing, dispatcher, and all driver implementations. This code is compiled unchanged for every board. It calls Arduino hardware APIs directly (`pinMode`, `digitalRead`, `analogRead`, `pulseIn`).

2. **Board configuration** (`platforms/<device>/`): Each board is defined by a single `board.yml` file — the single source of truth for that board's capabilities (pin count, ADC channels, reserved pins, peripherals). A code generator turns this YAML into C headers that the portable core includes at compile time.

3. **Build-time generation** (`generated/`): The pre-build hook produces runtime configuration (baud rate, heartbeat interval, log level) from `tools/production_config.json`. Environment variables can override these at build time.

## How It Works

The firmware is a single-threaded Arduino sketch:

1. **Setup**: Initialize the serial port, protocol parser, and register all drivers with the dispatcher.
2. **Loop**: Read bytes from `Serial`, feed them to the protocol parser, and dispatch complete frames to the registered driver for that command ID.
3. **Drivers**: Each driver validates inputs against board capability headers, then calls Arduino hardware APIs. Invalid or reserved pins are rejected before any hardware access.

The protocol layer is frame-based with CRC-16/CCITT-FALSE validation. All multi-byte integers in payloads are little-endian. See [protocol.md](protocol.md) for the full specification.

## Board Configuration

Each board is defined by a `board.yml` file. The generator (`tools/gen_platform_caps.py`) produces inline capability validation functions and compile-time constants from this YAML. The generated headers are committed to the repository and verified by CI drift checks.

Adding a board is purely additive: create a `board.yml`, generate headers, add a PlatformIO environment. See [adding_a_board.md](adding_a_board.md) for the step-by-step guide.

## Invariants

1. The portable core must build on a `native` target with stub platform ops — no vendor SDK includes leak into portable code.
2. `board.yml` is the single source of truth; generated headers are produced by `tools/gen_platform_caps.py` and verified by CI.
3. One YAML produces one header set for one platform folder. Adding a board is purely additive.

## Future Direction: Platform Abstraction Layer

A platform abstraction layer (PAL) with vtable-based dispatch is under development in `platforms/in_development/pico_sdk/`. This will allow non-Arduino backends (e.g. Pico SDK, ESP-IDF, Zephyr) to reuse the same portable core without Arduino dependencies. Until that work is complete, all production boards use the Arduino framework.
