# Capability Reference

Ferqon uses a capability system to prevent hardware access outside the intended design surface for each board.

## How It Works

Each board's `board.yml` declares its pin count, ADC channels, reserved pins, PWM pins, and peripheral instances. The code generator (`tools/gen_platform_caps.py`) turns this into inline C functions that validate hardware access at compile time and runtime.

The generated headers live in `platforms/<board>/generated/`. The key file is `pin_macros.h`, which contains inline validation functions for pin and peripheral capabilities.

## Available Validation Functions

The generated `pin_macros.h` provides the following inline functions for each board:

**Pin validation:**
- `ferqon_cap_pin_is_valid(pin)` — true if the pin number is within the board's range
- `ferqon_cap_pin_is_reserved(pin)` — true if the pin is reserved (e.g. internal flash, USB)
- `ferqon_cap_pin_supports_adc(pin)` — true if the pin has ADC capability
- `ferqon_cap_pin_supports_pwm(pin)` — true if the pin has PWM capability

**Peripheral validation:**
- `ferqon_cap_spi_instance_is_valid(instance)` — true if the SPI instance exists
- `ferqon_cap_i2c_instance_is_valid(instance)` — true if the I2C instance exists
- `ferqon_cap_uart_instance_is_valid(instance)` — true if the UART instance exists

## Usage

Every hardware operation in the portable core must call the appropriate `ferqon_cap_*()` function before touching hardware. If the check fails, the driver returns a structured error and no hardware access occurs.

The CI linter (`tools/lint_platform_guards.py`) scans the portable core for Arduino API calls and verifies that each one is preceded by a capability guard within the same function.

## Regeneration

After editing a board's `board.yml`, regenerate its headers:

```bash
python3 tools/gen_platform_caps.py platforms/<board>/board.yml
```

To check all boards for drift in CI:

```bash
python3 tools/gen_platform_caps.py --all --check
```
