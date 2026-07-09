# Validation Model

Ferqon uses three layers of validation to keep hardware access safe and predictable.

## Layer 1: Build-Time (Schema)

`board.yml` is validated against `tools/schemas/board.schema.json` by `tools/gen_platform_caps.py` and the PlatformIO pre-build hook. This catches:

- Missing required fields
- Invalid backend values
- Malformed peripheral definitions

## Layer 2: Generate-Time (Code Generation)

`tools/gen_platform_caps.py` turns `board.yml` into typed headers:

- `platform_caps.h` — constants
- `pin_macros.h` — inline validation functions
- `device_channels.c` — channel descriptors

These are committed to git and checked for drift in CI.

## Layer 3: Runtime (Capability Guards)

Every platform I/O function must call `ferqon_cap_*()` helpers before hardware access:

```c
int pico_gpio_put(uint8_t pin, uint8_t val) {
    if (!ferqon_cap_pin_is_valid(pin))    return FERQON_ERR_INVALID_PIN;
    if (ferqon_cap_pin_is_reserved(pin))  return FERQON_ERR_RESERVED_PIN;
    gpio_put(pin, val);
    return FERQON_OK;
}
```

The CI pipeline runs `tools/lint_platform_guards.py` to statically enforce that every hardware operation in `platforms/` is preceded by a capability guard.

## Error Mapping

| Failure Mode | Layer | Error Code |
|--------------|-------|------------|
| Invalid `board.yml` | 1 | Tool error / build failure |
| Generated header drift | 2 | `gen_platform_caps.py --check` fails |
| Pin out of range | 3 | `FERQON_ERR_INVALID_PIN` |
| Reserved pin touched | 3 | `FERQON_ERR_RESERVED_PIN` |
| Missing capability guard | 3 | `FERQON_ERR_UNSUPPORTED` or linter error |
