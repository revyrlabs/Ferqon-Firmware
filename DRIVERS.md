# Ferqon Driver System Guide

## Overview

Ferqon drivers are firmware-based handlers compiled directly into the Pico firmware. On boot, the Pico announces which drivers are available, and the backend can call driver methods over the serial interface.

**Key changes from previous architecture:**
- ✅ Drivers are now **compiled into the firmware** as a single .bin/.uf2 image
- ✅ **No separate driver uploading**  — use `flash_pico.py` to build and flash everything at once
- ✅ **No deploy/lifecycle management** — drivers are available automatically on Pico boot
- ✅ **Simple RPC protocol** — only `ping`, `driver.info`, `driver.call`

## Architecture

### Firmware Side (Pico)

```
main.cpp
├─ Core0: Command parser (CommandParser.cpp)
└─ Core1: Driver runtime (runtime_loop)
   ├─ Driver registry (driver_registry.c)
   │  └─ Registered drivers (auto-discovered via constructors)
   └─ Protocol handler
      ├─ driver.announce (on boot)
      ├─ driver.info (query available drivers)
      ├─ driver.call (execute driver method)
      └─ ping (health check)
```

### Backend Side (Pi)

```
/api/drivers/
├─ POST /announce
│  └─ Ingest driver list from Pico on boot
├─ GET /
│  └─ List drivers available on a device
└─ POST /{device_id}/{driver_name}/call
   └─ Execute a driver method
```

## Adding a New Driver

### 1. Create the Driver File

Create a new `.c` file in `pico/firmware_driver_runtime/src/drivers/`:

```c
// drivers/my_sensor.c
#include "driver.h"
#include <stdio.h>
#include <string.h>

// Your driver implementation
static bool my_sensor_call(const char* method, const char* payload, runtime_response_t* out) {
    if (strcmp(method, "read_temperature") == 0) {
        // Parse payload, read sensor, return result
        // out->ok = true/false
        // snprintf(out->result, sizeof(out->result), "...");
        return true;
    }
    return false; // Method not supported
}

// Driver registration (automatically called on startup)
static const driver_t my_sensor_driver = {
    .name = "my-sensor",
    .call = my_sensor_call,
};

static void __attribute__((constructor, used)) _register_my_sensor(void) {
    driver_registry_register(&my_sensor_driver);
}
```

### 2. CMakeLists.txt

The CMakeLists.txt automatically discovers drivers in the `src/drivers/` directory. Just add your `.c` file and it will be compiled in.

```
drivers/
├── rgb.c            ← built-in RGB LED driver
└── my_sensor.c      ← your new driver
```

### 3. Build and Flash

```bash
cd pico
python3 flash_pico.py
```

The firmware will include `my-sensor` driver.

## Driver API

### Driver Interface (`driver.h`)

```c
typedef struct {
    const char* name;                    // Driver name (e.g., "rgb-led")
    driver_call_fn call;                 // Function pointer to handle calls
} driver_t;

// Function signature for driver method handler:
typedef bool (*driver_call_fn)(
    const char* call_name,               // Method to execute
    const char* payload,                 // JSON payload
    runtime_response_t* out              // Response struct
);

// Register your driver (call in constructor)
bool driver_registry_register(const driver_t* drv);
```

### Protocol

All communication is JSON-RPC over USB-CDC serial (115200 baud).

#### Driver Announcement (on Pico boot)

```json
{
  "event": "driver.announce",
  "source": "pico",
  "device_id": "e5614da2a3d0d12e",
  "count": 2,
  "drivers": [
    {"name": "rgb-led"},
    {"name": "my-sensor"}
  ]
}
```

#### Query Available Drivers

Request:
```json
{
  "method": "driver.info",
  "driver_name": "",
  "device_port": "",
  "payload": ""
}
```

Response:
```json
{
  "ok": true,
  "result": "{\"count\": 2, \"drivers\": [\"rgb-led\", \"my-sensor\"]}"
}
```

#### Execute Driver Method

Request:
```json
{
  "method": "driver.call",
  "driver_name": "rgb-led",
  "payload": "{\"method\": \"set_color\", \"r\": 255, \"g\": 128, \"b\": 0}"
}
```

Response:
```json
{
  "ok": true,
  "result": "color set"
}
```

Or on error:
```json
{
  "ok": false,
  "error": "driver not found: invalid-driver"
}
```

## Backend API

### Ingest Driver Announcement

```http
POST /api/drivers/announce
Content-Type: application/json

{
  "event": "driver.announce",
  "source": "pico",
  "device_id": "e5614da2a3d0d12e",
  "drivers": [
    {"name": "rgb-led"},
    {"name": "my-sensor"}
  ]
}
```

Response:
```json
{
  "ok": true,
  "ingested": 2,
  "device_id": "e5614da2a3d0d12e"
}
```

### List Available Drivers

```http
GET /api/drivers?device_id=e5614da2a3d0d12e
Authorization: Bearer <token>
```

Response:
```json
[
  {
    "device_id": "e5614da2a3d0d12e",
    "driver_name": "rgb-led",
    "manifest": {}
  },
  {
    "device_id": "e5614da2a3d0d12e",
    "driver_name": "my-sensor",
    "manifest": {}
  }
]
```

### Call Driver Method

```http
POST /api/drivers/e5614da2a3d0d12e/rgb-led/call
Authorization: Bearer <token>
Content-Type: application/json

{
  "method": "set_color",
  "args": {"r": 255, "g": 128, "b": 0}
}
```

Response:
```json
{
  "ok": true,
  "device_id": "e5614da2a3d0d12e",
  "driver_name": "rgb-led",
  "method": "set_color",
  "result": "color set"
}
```

## Testing Drivers

### Unit Tests (Firmware)

The drivers are tested as part of the firmware build. Run unit tests:

```bash
cd pico
python3 test_drivers.py
```

This requires a connected Pico and will test:
- Driver discovery
- Method calls
- Error handling
- Protocol compliance

### Integration Testing

If you're developing a new driver:

1. **Add test methods to your driver** in the `call` function
2. **Flash the firmware**: `python3 flash_pico.py`
3. **Run the test suite**: `python3 test_drivers.py --verbose`
4. **Test via API** (if connected to backend):

```bash
# Assuming Pico announces on boot
curl -X GET http://localhost:8000/api/drivers \
  -H "Authorization: Bearer <token>"

# Call a driver method
curl -X POST http://localhost:8000/api/drivers/e5614da2a3d0d12e/my-sensor/call \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"method": "read_temperature", "args": {}}'
```

## Best Practices

### Payload Parsing

Use the provided JSON extraction helpers:

```c
#include "runtime_protocol.h"

// Extract JSON string field
char result[64];
runtime_extract_json_string(payload, "field_name", result, sizeof(result));

// Extract JSON int field
int value = 0;
runtime_extract_json_int(payload, "field_name", &value);
```

### Error Handling

Always set `ok` and either `result` or `error`:

```c
static bool my_call(const char* method, const char* payload, runtime_response_t* out) {
    if (strcmp(method, "get_value") == 0) {
        int pin = 0;
        if (!runtime_extract_json_int(payload, "pin", &pin)) {
            out->ok = false;
            snprintf(out->error, sizeof(out->error), "missing pin");
            return false;
        }

        if (pin < 0 || pin > 28) {
            out->ok = false;
            snprintf(out->error, sizeof(out->error), "invalid pin %d", pin);
            return false;
        }

        // Success
        out->ok = true;
        snprintf(out->result, sizeof(out->result), "value=%d", read_pin(pin));
        return true;
    }

    return false; // Method not implemented
}
```

### Resource Management

Use the resource manager for GPIO/PIO allocation:

```c
#include "resource_manager.h"

// In your driver call handler:
static resource_state_t* res = NULL;  // Set by runtime initialization

// Claim GPIO
if (!resource_claim_gpio(res, pin_num)) {
    snprintf(out->error, sizeof(out->error), "GPIO %d already in use", pin_num);
    return false;
}

// Use GPIO...

// Release GPIO when done
resource_release_gpio(res, pin_num);
```

## Troubleshooting

### Driver Not Appearing in `driver.info`

1. **Check registration**: Call `driver_registry_register()` in constructor
2. **Check constructor attribute**: Use `__attribute__((constructor, used))`
3. **Rebuild**: Run `python3 flash_pico.py`
4. **Check for errors**: Look at build output

### Driver Method Call Fails

1. **Check method name**: Ensure it matches the `strcmp` in your call handler
2. **Check payload**: Ensure JSON is valid
3. **Check return value**: Driver must return `true`/`false` and set `out->ok`

### Out of Memory / Too Many Drivers

Maximum 8 drivers can be registered (defined by `MAX_DRIVERS` in `driver_registry.c`).
If you need more, increase this and rebuild.

## Quick Start Example

Here's a minimal driver that reads a GPIO pin:

```c
// drivers/simple_gpio.c
#include "driver.h"
#include "pico/gpio.h"

static bool simple_gpio_call(const char* method, const char* payload, runtime_response_t* out) {
    if (strcmp(method, "read_pin") == 0) {
        int pin = 0;
        runtime_extract_json_int(payload, "pin", &pin);

        if (pin < 0 || pin > 28) {
            out->ok = false;
            snprintf(out->error, sizeof(out->error), "invalid pin");
            return false;
        }

        int value = gpio_get(pin);
        out->ok = true;
        snprintf(out->result, sizeof(out->result), "{\"value\": %d}", value);
        return true;
    }

    return false;
}

static const driver_t simple_gpio_driver = {
    .name = "simple-gpio",
    .call = simple_gpio_call,
};

static void __attribute__((constructor, used)) _register_simple_gpio(void) {
    driver_registry_register(&simple_gpio_driver);
}
```

Then:
1. Save as `pico/firmware_driver_runtime/src/drivers/simple_gpio.c`
2. Run `cd pico && python3 flash_pico.py`
3. Test with:
   ```
   curl -X POST http://localhost:8000/api/drivers/{device_id}/simple-gpio/call \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"method": "read_pin", "args": {"pin": 16}}'
   ```
