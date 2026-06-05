# Ferqon Firmware

Portable, Apache-2.0 licensed firmware for the Ferqon real-time interaction node. Supports multiple MCU platforms (RP2040, ESP32, STM32, Teensy) with a Linux-kernel-style architecture separating portable `core/` from platform-specific `platforms/<device>/`.

## Quick Start

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/repvi/Ferqon.git
cd Ferqon/ferqon_firmware

# Install dependencies
pip install -r tools/requirements.txt
pio install  # PlatformIO Core

# Build for Raspberry Pi Pico (Arduino backend)
pio run -e pico_arduino

# Flash
pio run -e pico_arduino -t upload
```

See [docs/adding_a_board.md](docs/adding_a_board.md) for adding support for new hardware.

## Architecture

Ferqon Firmware follows a Linux-kernel-style split:

```
core/                    ← Portable: command parsing, scheduler, drivers
  ↕ talks only through FERQON_PLT_* vtable API
platforms/<device>/      ← Platform-specific: vendor SDK, Arduino lives here
  board.yml              ← Single source of truth
  generated/*.h          ← Committed, CI-verified headers
  <device>_io.cpp        ← Hardware access (gated by capability macros)
```

**Three invariants:**
1. `core/` must build against a `native` target with stub ops — no vendor includes leak in.
2. Every hardware op in `platforms/<device>/` must go through `ferqon_cap_*()` validators from generated headers.
3. One YAML → one header set → one platform folder. Adding a board is purely additive.

## Supported Platforms

| Platform | MCU | Backend | Status |
|----------|-----|---------|--------|
| pico | RP2040 | Arduino | ✅ Primary |
| rp2040 | RP2040 | Arduino | ✅ |
| pico_native | RP2040 | Pico SDK | ✅ |
| esp32 | ESP32 | Arduino | ✅ |
| esp32s3 | ESP32-S3 | Arduino | ✅ |
| stm32f4 | STM32F4 | Arduino | ✅ |
| stm32f7 | STM32F7 | Arduino | ✅ |
| teensy40 | Teensy 4.0 | Arduino | ✅ |
| teensy41 | Teensy 4.1 | Arduino | ✅ |

## Documentation

- [docs/architecture.md](docs/architecture.md) — System architecture and design principles
- [docs/adding_a_board.md](docs/adding_a_board.md) — Step-by-step guide for porting to new hardware
- [docs/capability_reference.md](docs/capability_reference.md) — Auto-generated capability API reference
- [docs/protocol.md](docs/protocol.md) — Device-side protocol subsystem
- [docs/validation_model.md](docs/validation_model.md) — Three-layer validation strategy

## DUT (Device Under Test)

For Ferqon Hardware-in-the-Loop testing, reference DUT firmware is provided in the `dut/` directory (sibling to `firmware/`). See [dut/README.md](../dut/README.md) for:
- Arduino DUT sketches (Uno/Nano, ESP32, RP2040)
- DUT flashing utilities
- Wiring diagrams
- System-HIL test harness

## Development Workflow

1. Edit `platforms/<slug>/board.yml` to define hardware capabilities
2. Run `tools/gen_platform_caps.py platforms/<slug>/board.yml` to regenerate headers
3. Commit both the YAML and the `generated/` diff
4. Build: `pio run -e <env>`
5. CI validates schema, checks for generator drift, and runs the full build matrix

## Testing

```bash
# Native unit tests (core portability)
pio test -e native_ringbuf
pio test -e native_multicore
pio test -e native_singlecore

# Hardware smoke test (requires attached device)
python3 tools/diagnose.py --port /dev/ttyACM0
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

## Notice

See [NOTICE](NOTICE) for third-party license information.
