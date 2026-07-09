# Adding a Board

This guide walks through adding a new MCU board to Ferqon firmware.

## 1. Scaffold the Platform Directory

```bash
tools/new_board.py my_board --mcu rp2040 --backend arduino
```

If `new_board.py` does not exist, create the directory manually:

```
platforms/my_board/
  board.yml
  my_board_io.cpp
  my_board_backend.cpp
  my_board_system.cpp
  my_board_config.cpp
  generated/
```

## 2. Define Capabilities in `board.yml`

Example:

```yaml
board: my_board
device_type: my_board_v1
mcu: RP2040
backend: arduino
pio_env: my_board_arduino
max_gpio: 29
ram_size_bytes: 262144
flash_size_bytes: 2097152
sys_clock_hz: 133000000

adc:
  resolution_bits: 12
  vref_mv: 3300
  pins: [26, 27, 28]

pwm:
  pins: [0, 1, 2, 3, 4, 5, 6, 7]

spi:
  - instance: 0
    sck: [18]
    mosi: [19]
    miso: [16]
    cs: [17]

i2c:
  - instance: 0
    sda: [20]
    scl: [21]

uart:
  - instance: 0
    tx: [0]
    rx: [1]
```

## 3. Generate Headers

```bash
python3 tools/gen_platform_caps.py platforms/my_board/board.yml
```

This creates:

- `platforms/my_board/generated/platform_caps.h`
- `platforms/my_board/generated/pin_macros.h`
- `platforms/my_board/generated/device_channels.c`
- `platforms/my_board/generated/board.json`
- `platforms/my_board/generated/capabilities.json`

## 4. Add a PlatformIO Environment

Edit `platformio.ini`:

```ini
[env:my_board_arduino]
platform = raspberrypi
framework = arduino
board = pico
monitor_speed = 115200
build_flags =
    -I${PROJECT_DIR}/generated
    -I${PROJECT_DIR}/platforms/my_board/generated
    -DFERQON_FW_VERSION='"${common.protocol_version}"'
    -DFERQON_BOARD_MY_BOARD
lib_deps =
    Wire
    SPI
extra_scripts = pre:tools/pio_pre_build.py
```

## 5. Implement the IO Layer

Implement `my_board_io.cpp` with all hardware access gated by `ferqon_cap_*()` helpers:

```cpp
int my_board_gpio_put(uint8_t pin, uint8_t val) {
    if (!ferqon_cap_pin_is_valid(pin))   return FERQON_ERR_INVALID_PIN;
    if (ferqon_cap_pin_is_reserved(pin)) return FERQON_ERR_RESERVED_PIN;
    gpio_put(pin, val);
    return FERQON_OK;
}
```

## 6. Register the Backend

In `my_board_backend.cpp`:

```cpp
extern "C" void my_board_register_backend(void) {
    ferqon_set_write_func(my_board_serial_write);
    // register platform vtable or additional drivers
}
```

## 7. Build and Test

```bash
pio run -e my_board_arduino
pio test -e native
```

## 8. Commit

Commit the new `platforms/my_board/` directory, including `generated/`, and update `platformio.ini` and the CI matrix if needed.
