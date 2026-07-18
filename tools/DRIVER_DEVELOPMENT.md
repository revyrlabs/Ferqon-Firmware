<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs -->

# Driver Development Guide

This guide helps you develop new command drivers for the Ferqon firmware.
A driver is a C++ implementation of one or more `FERQON_CMD_*` command IDs,
registered at runtime with the dispatcher via `ferqon_register_driver()`.

> **Scope:** This guide covers firmware-side drivers only. For server-side
> driver schemas and UI definitions, see the Ferqon server documentation.

## Architecture Overview

The firmware uses a single-core `loop()` in `src/main.cpp` that reads bytes
from `Serial`, feeds them to a frame parser, and dispatches complete frames
to registered drivers via `ferqon_dispatch_request()` in `src/dispatcher.cpp`.

```
Serial → ferqon_parser_feed() → ferqon_dispatch_request()
                                      ↓
                              for each registered driver:
                                driver.handle(seq, cmd_id, args, args_len, ...)
                                      ↓
                              if handled: send DONE (or error if already_responded)
                              if unhandled by all: send INVALID_COMMAND
```

Drivers are registered explicitly in `setup()` — there is no auto-discovery,
no constructor-based registration, and no separate runtime thread.

## Quick Start

### 1. Pick or add a command

Ferqon commands are defined in `protocol/ssot/commands.json` (the single
source of truth). The generated header `src/ferqon_commands.h` contains
`#define FERQON_CMD_*` constants for each command.

To add a new command:
1. Add an entry to `protocol/ssot/commands.json`
2. Run `python3 tools/gen_protocol.py` to regenerate `src/ferqon_commands.h`
3. Use the new `FERQON_CMD_*` constant in your driver

### 2. Create the driver file

Add a new `.cpp` file in `src/` (flat — there is no `src/drivers/` subdirectory):

```cpp
// src/my_driver.cpp
/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#include "dispatcher.h"
#include "ferqon_commands.h"
#include "protocol.h"
#include "ferqon_log.h"

static bool my_driver_handler(uint8_t seq, uint8_t cmd_id,
                               const uint8_t *params, uint8_t param_len,
                               uint8_t *response, uint8_t *response_len,
                               bool *already_responded) {
    if (cmd_id != FERQON_CMD_MY_COMMAND) {
        return false;  // Not our command — let the next driver try
    }

    /* Validate payload (the PKT_REQUEST byte has already been stripped
     * by the dispatcher — params starts at the first argument byte). */
    if (param_len < 1) {
        ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS,
                         FERQON_ECAT_COMMAND, /*retryable=*/false,
                         /*ctx=*/0, NULL, 0);
        *already_responded = true;
        return true;
    }

    uint8_t value = params[0];
    /* ... do work ... */

    response[0] = value;  /* example: echo back */
    *response_len = 1;
    return true;  /* Handled — dispatcher will send a DONE frame */
}

extern "C" const ferqon_driver_t my_driver = {
    .name = "my_driver",
    .id = FERQON_CMD_MY_COMMAND,
    .handle = my_driver_handler,
};
```

### 3. Register the driver

Add an `extern` declaration and a `ferqon_register_driver()` call in
`src/main.cpp`:

```cpp
/* In the extern block near the top: */
extern "C" const ferqon_driver_t my_driver;

/* In setup(), after ferqon_dispatcher_init(): */
ferqon_register_driver(&my_driver);
```

### 4. Add to the sealed source allowlist

Add your new `.cpp` file to `_src_filter` in `platformio.ini` AND to
`tools/production_manifest.json`. The build will not include it otherwise.

### 5. Build and test

```bash
# Build for the primary platform
ferqonfw build pico

# Run native unit tests to verify the command logic
ferqonfw-dev test
```

## Driver API

A driver implements a single `ferqon_driver_handler_t` function. The exact
signature (from `src/dispatcher.h`):

```cpp
typedef bool (*ferqon_driver_handler_t)(uint8_t seq, uint8_t cmd_id,
                                         const uint8_t *params, uint8_t param_len,
                                         uint8_t *response, uint8_t *response_len,
                                         bool *already_responded);
```

The `ferqon_driver_t` struct:

```cpp
typedef struct {
    const char *name;
    uint8_t id;
    ferqon_driver_handler_t handle;
} ferqon_driver_t;
```

### Parameters

| Parameter | Direction | Description |
|-----------|-----------|-------------|
| `seq` | in | Frame sequence number — echo in error responses |
| `cmd_id` | in | Command ID from the frame — check this first |
| `params` | in | Argument bytes (PKT_REQUEST already stripped by dispatcher) |
| `param_len` | in | Number of argument bytes |
| `response` | out | Buffer for OK response body (up to `FERQON_MAX_PAYLOAD_BYTES - 1`) |
| `response_len` | out | Set to the number of bytes written to `response` |
| `already_responded` | out | Set to `true` if you called `ferqon_send_error()` directly |

### Return value

- Return `true` if the command was handled. If `*already_responded` is
  `false`, the dispatcher prepends a `PKT_DONE` byte and sends the response.
  If `*already_responded` is `true`, the dispatcher does nothing (you already
  sent an error frame).
- Return `false` to let the next driver attempt to handle the command.
- If no driver claims the command, the dispatcher sends `INVALID_COMMAND`.

### Error handling

To return a structured error, call `ferqon_send_error()` and set
`*already_responded = true`:

```cpp
ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS,
                 FERQON_ECAT_COMMAND, /*retryable=*/false,
                 /*ctx=*/0, NULL, 0);
*already_responded = true;
return true;
```

Error codes and categories are defined in `src/ferqon_commands.h`:

| Constant | Value | Meaning |
|----------|-------|---------|
| `FERQON_ERR_OK` | 0 | Success |
| `FERQON_ERR_INVALID_COMMAND` | 1 | Unknown command ID |
| `FERQON_ERR_INVALID_PARAMS` | 2 | Invalid parameters |
| `FERQON_ERR_UNSUPPORTED_MODE` | 3 | Unsupported mode |
| `FERQON_ERR_UNSUPPORTED_PIN` | 4 | Unsupported pin |
| `FERQON_ERR_BUSY` | 5 | Device busy |
| `FERQON_ERR_INTERNAL` | 6 | Internal error |
| `FERQON_ERR_NOT_IMPLEMENTED` | 13 | Hardware not ready |

## Common Patterns

### Multi-command driver

A single driver can handle multiple command IDs by switching on `cmd_id`:

```cpp
static bool my_driver_handler(uint8_t seq, uint8_t cmd_id, ...) {
    switch (cmd_id) {
        case FERQON_CMD_MY_READ:  return handle_read(seq, cmd_id, ...);
        case FERQON_CMD_MY_WRITE: return handle_write(seq, cmd_id, ...);
        default: return false;
    }
}
```

See `src/uart.cpp` and `src/gpio.cpp` for real examples.

### Pin validation

Always validate pins through the generated capability guards before
hardware access:

```cpp
#include "pin_macros.h"

if (!ferqon_cap_pin_is_valid(pin) || ferqon_cap_pin_is_reserved(pin)) {
    ferqon_send_error(seq, cmd_id, FERQON_ERR_UNSUPPORTED_PIN,
                     FERQON_ECAT_DEVICE, false, 0, NULL, 0);
    *already_responded = true;
    return true;
}
```

### Native testability

For the `native` test target, Arduino APIs are stubbed. Driver code should
compile without vendor SDK includes. If a driver needs Arduino types, gate
those blocks with `#ifdef ARDUINO` or move platform-specific code to a
`platforms/` file.

## Testing

### Native unit tests

Add tests under `tests/` for `ferqonfw-dev test`:

```cpp
// tests/test_my_driver.cpp
#include "unity.h"
#include "dispatcher.h"

extern "C" const ferqon_driver_t my_driver;

void test_my_driver_handles_my_command(void) {
    uint8_t params[] = {0x42};
    uint8_t response[8];
    uint8_t response_len = 0;
    bool already_responded = false;

    bool handled = my_driver.handle(1, FERQON_CMD_MY_COMMAND,
                                     params, sizeof(params),
                                     response, &response_len,
                                     &already_responded);

    TEST_ASSERT_TRUE(handled);
    TEST_ASSERT_FALSE(already_responded);
    TEST_ASSERT_EQUAL_UINT8(1, response_len);
    TEST_ASSERT_EQUAL_UINT8(0x42, response[0]);
}
```

### Device smoke tests

Use the `ferqonfw` CLI to exercise a command on real hardware:

```bash
ferqonfw selftest --port /dev/ttyACM0
ferqonfw packet --port /dev/ttyACM0 --cmd <cmd_id> --payload <hex>
```

Or use the in-process emulator for no-hardware testing:

```bash
ferqonfw-dev selftest --emulator
```

## Troubleshooting

### Command not dispatched

- Verify the command ID is in `src/ferqon_commands.h` (regenerate from
  `protocol/ssot/commands.json` if needed).
- Verify the driver is registered in `src/main.cpp` via
  `ferqon_register_driver()`.
- Verify the driver returns `true` for the correct `cmd_id`.
- Verify the source file is in `_src_filter` in `platformio.ini`.

### INVALID_PARAMS on a command that should work

The dispatcher requires `params[0] == FERQON_PKT_REQUEST` (0x01) for all
commands except `DEVICE_INFO` and `DRIVER_INFO`. If your host-side frame
builder omits the `PKT_REQUEST` byte, the firmware will reject the frame
with `INVALID_PARAMS` before your driver is even called. Ensure the host
payload starts with `0x01`.

### Build failures on `native`

- Remove any `#include <Arduino.h>` from the driver code, or wrap it in
  `#ifdef ARDUINO`.
- Ensure platform functions are declared in a header that is also provided
  by the native stub.

## Next Steps

1. Add a new command to `protocol/ssot/commands.json` and regenerate with
   `python3 tools/gen_protocol.py`.
2. Implement the driver in `src/my_driver.cpp`.
3. Register it in `src/main.cpp`.
4. Add it to `_src_filter` in `platformio.ini` and `tools/production_manifest.json`.
5. Run `ferqonfw-dev test` and `ferqonfw build pico`.
6. Open a pull request with `Signed-off-by` lines (see [CONTRIBUTING.md](../CONTRIBUTING.md)).
