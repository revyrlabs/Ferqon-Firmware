# Capability Reference

Ferqon uses a capability system to prevent hardware access outside the intended design surface for each board.

## Generated Files

`tools/gen_platform_caps.py` produces the following from `platforms/<board>/board.yml`:

- `platform_caps.h` — constants and validation function prototypes
- `pin_macros.h` — inline macros for pin and peripheral capability checks
- `device_channels.c` — channel descriptor array for the board
- `board.json` — JSON mirror of `board.yml`
- `capabilities.json` — unified capability map for driver matching

## Key Macros

### Pin validation

```c
bool ferqon_cap_pin_is_valid(uint8_t pin);
bool ferqon_cap_pin_is_reserved(uint8_t pin);
bool ferqon_cap_pin_has_adc(uint8_t pin);
bool ferqon_cap_pin_has_pwm(uint8_t pin);
```

Generated as `static inline` in `pin_macros.h`.

### Peripheral validation

```c
bool ferqon_cap_spi_is_valid(uint8_t instance, uint8_t sck, uint8_t mosi, uint8_t miso, uint8_t cs);
bool ferqon_cap_i2c_is_valid(uint8_t instance, uint8_t sda, uint8_t scl);
bool ferqon_cap_uart_is_valid(uint8_t instance, uint8_t tx, uint8_t rx);
```

## Usage in Platform Code

Every platform I/O function must use the capability helpers before touching hardware:

```c
int pico_gpio_put(uint8_t pin, uint8_t val) {
    if (!ferqon_cap_pin_is_valid(pin))    return FERQON_ERR_INVALID_PIN;
    if (ferqon_cap_pin_is_reserved(pin))  return FERQON_ERR_RESERVED_PIN;
    gpio_put(pin, val);
    return FERQON_OK;
}
```

The CI linter `tools/lint_platform_guards.py` checks for the presence of these guards.

## Regeneration

After editing `board.yml`:

```bash
python3 tools/gen_platform_caps.py platforms/<board>/board.yml
```

To check for drift in CI:

```bash
python3 tools/gen_platform_caps.py --all --check
```
