# Adding a Board

This guide walks through adding a new MCU board to Ferqon firmware. The process is purely additive — no existing code needs to change.

## Overview

Each board is defined by a single `board.yml` file that declares its capabilities (pin count, ADC channels, reserved pins, peripherals). A code generator turns this YAML into C headers that the portable core includes at compile time. No platform-specific `.cpp` files are needed — the generated headers provide all board-specific configuration.

## Steps

### 1. Create the Board Directory

New boards start in `platforms/in_development/` and move to `platforms/` when production-ready. Create a directory for your board under `platforms/in_development/`.

### 2. Write `board.yml`

This is the single source of truth for your board. It defines the MCU, backend, PlatformIO env name, pin count, memory, clock, and peripheral capabilities (ADC, PWM, SPI, I2C, UART).

Use an existing board as a template — see `platforms/pico/board.yml` for a complete example. The required fields are documented by the schema at `tools/schemas/board.schema.json`.

### 3. Generate Headers

Run the generator against your `board.yml`:

```bash
python3 tools/gen_platform_caps.py platforms/in_development/my_board/board.yml
```

This produces compile-time constants, inline capability validation functions, and channel descriptors in the `generated/` subdirectory.

### 4. Add a PlatformIO Environment

Add a new `[env:...]` section to `platformio.ini`. Use the shared build flags and source filter from `[common]` so your board gets the same firmware version, Serial1 support, and sealed source allowlist as all other boards. Add a `-DFERQON_BOARD_MY_BOARD` define and include your board's `generated/` directory.

Use an existing environment (e.g. `[env:pico_arduino]`) as a template. The key fields are platform, framework, board, build_flags, and the pre-build script hook.

### 5. Build and Test

```bash
ferqonfw build my_board        # Build for the new board
ferqonfw-dev test              # Run native unit tests (no hardware required)
```

The portable core calls Arduino APIs directly. Board-specific limits are enforced by the generated capability headers — invalid pins, reserved pins, and unsupported ADC channels are rejected before any hardware access.

### 6. Move to Production

When the board is ready:

1. Add it to `tools/production_manifest.json` so it is included in the sealed production bundle and CI matrix.
2. Move the directory from `platforms/in_development/` to `platforms/`.
3. Update the include path in `platformio.ini` to match the new location.
4. Rebuild and verify with `make cleanroom` (creates a sealed bundle and builds all boards from clean caches).
