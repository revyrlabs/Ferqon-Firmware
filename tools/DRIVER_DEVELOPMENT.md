# Driver Development Guide

This guide helps you develop new `command drivers` for the Ferqon firmware. A driver is a C++ implementation of one or more `FERQON_CMD_*` command IDs, registered at runtime with the dispatcher in `src/dispatcher.cpp`.

> **Scope:** This guide covers firmware-side drivers only. For server-side driver schemas and UI definitions, see the Ferqon server documentation.

## Quick Start

### 1. Pick a command to implement

Ferqon commands are defined in `src/ferqon_commands.h` (generated from `commands.yml`). Pick an existing command or add a new command ID to `commands.yml` and run `tools/gen_commands.py` to regenerate the header.

### 2. Create the driver file

Add a new file in `src/drivers/` or `src/` directly:

```cpp
// src/drivers/my_driver.cpp
#include "dispatcher.h"
#include "protocol.h"
#include "ferqon_log.h"

#include <Arduino.h>  // only for Arduino backends; native target uses stubs

static bool my_driver_handler(uint8_t cmd, const uint8_t *params, uint8_t param_len,
                               uint8_t *response, uint8_t *response_len) {
    if (cmd != FERQON_CMD_MY_COMMAND) {
        return false;
    }

    // Validate payload
    if (param_len < 1) {
        response[0] = FERQON_ERR_INVALID_PARAM;
        *response_len = 1;
        return true;
    }

    // Do work
    uint8_t value = params[0];
    // ...

    response[0] = FERQON_OK;
    *response_len = 1;
    return true;
}

extern "C" const ferqon_driver_t my_driver = {
    .handler = my_driver_handler,
};
```

### 3. Register the driver

Add an `extern` declaration in `src/main.cpp` and include it in the `drivers[]` array:

```cpp
extern "C" const ferqon_driver_t my_driver;

static const ferqon_driver_t *g_drivers[] = {
    &ping_driver,
    &echo_driver,
    &my_driver,
    // ...
};
```

### 4. Build and test

```bash
# Build for the primary platform
pio run -e pico_arduino

# Run native unit tests to verify the command logic
pio test -e native
```

## Driver API

A driver implements a single `ferqon_driver_t.handler` function:

```cpp
typedef bool (*ferqon_driver_handler_t)(uint8_t cmd,
                                          const uint8_t *params,
                                          uint8_t param_len,
                                          uint8_t *response,
                                          uint8_t *response_len);
```

- Return `true` if the command was handled. The contents of `response` (up to `response_len` bytes) are sent back as the OK response body.
- Return `false` to let the next driver attempt to handle the command.
- The dispatcher copies `response` out immediately; the driver owns the buffer only for the duration of the call.

## Common patterns

### Validating command parameters

Always validate `cmd` and `param_len` before accessing `params`:

```cpp
if (cmd != FERQON_CMD_MY_COMMAND) return false;
if (param_len < 2) {
    response[0] = FERQON_ERR_INVALID_PARAM;
    *response_len = 1;
    return true;
}
```

### Hardware access in Arduino drivers

Keep platform-specific I/O in the `platforms/<device>/` directory. Call through the platform vtable or `ferqon_cap_*()` helpers:

```cpp
// Good: delegate to platform IO layer
extern int pico_gpio_put(uint8_t pin, uint8_t val);

if (!ferqon_cap_pin_is_valid(pin)) {
    response[0] = FERQON_ERR_INVALID_PIN;
    *response_len = 1;
    return true;
}

int rc = pico_gpio_put(pin, value);
```

### Native testability

For the `native` test target, the platform IO functions are stubbed. Driver code should compile without any vendor SDK includes. If a driver needs Arduino types, gate those blocks with `#ifdef ARDUINO` or move the platform-specific code to a `platforms/` file.

## Testing

### Native unit tests

Add tests under `test/` for `pio test -e native`:

```cpp
// test/test_my_driver.cpp
#include "unity.h"
#include "dispatcher.h"

extern "C" const ferqon_driver_t my_driver;

void test_my_driver_handles_my_command(void) {
    uint8_t params[] = {0x42};
    uint8_t response[8];
    uint8_t response_len = 0;

    bool handled = my_driver.handler(FERQON_CMD_MY_COMMAND, params, sizeof(params),
                                      response, &response_len);

    TEST_ASSERT_TRUE(handled);
    TEST_ASSERT_EQUAL_UINT8(1, response_len);
    TEST_ASSERT_EQUAL_UINT8(FERQON_OK, response[0]);
}
```

### Device smoke tests

Use the Python self-test utilities in `tools/ferqon_selftest.py` or the `ferqonfw` CLI to exercise a command on real hardware:

```bash
python3 tools/ferqon_selftest.py --port /dev/ttyACM0
```

## Troubleshooting

### Command not dispatched

- Verify the command ID is in `src/ferqon_commands.h`.
- Verify the driver is registered in `src/main.cpp`.
- Verify the driver returns `true` for the correct `cmd`.

### Unknown command at runtime

The dispatcher logs `FERQON_LOG_SUBTYPE_UNKNOWN_CMD` when no driver claims a command. Enable verbose logging to see the raw command byte.

### Build failures on `native`

- Remove any `#include <Arduino.h>` from the driver code, or wrap it in `#ifdef ARDUINO`.
- Ensure platform functions are declared in a header that is also provided by the native stub.

## Next Steps

1. Add a new command to `commands.yml` and regenerate `src/ferqon_commands.h`.
2. Implement the driver in `src/drivers/`.
3. Register it in `src/main.cpp`.
4. Run `pio test -e native` and `pio run -e pico_arduino`.
5. Open a pull request with `Signed-off-by` lines.
