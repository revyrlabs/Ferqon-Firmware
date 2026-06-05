# RGB LED Driver — Quick Start Guide

## Hardware Setup

Connect an RGB LED to your Pico:

| Pico Pin | LED Pin | Color |
|----------|---------|-------|
| GPIO 16  | Anode   | Red   |
| GPIO 17  | Anode   | Green |
| GPIO 18  | Anode   | Blue  |
| GND      | Cathode | GND   |

**Using a current-limiting resistor (recommended):** ~220Ω in series with each LED pin.

---

## Build & Flash

The RGB driver is already compiled in. Just build and flash:

```bash
cd pico
python3 flash_pico.py
```

This builds the complete firmware including the `rgb-led` driver.

---

## Test It!

### Option 1: Run Unit Tests

```bash
# Auto-detect Pico and run all RGB driver tests
python3 tests/test_rgb_driver.py

# Verbose output
python3 tests/test_rgb_driver.py -v

# Specify device explicitly
python3 tests/test_rgb_driver.py -d /dev/ttyACM0
```

Tests verify:
- Driver exists and is discoverable
- Basic colors (red, green, blue, white, black)
- Mixed colors (orange, cyan, magenta)
- Mid-range brightness
- Value clamping

### Option 2: Run Color Patterns (Interactive)

Display beautiful color patterns on your LED:

```bash
python3 tests/test_rgb_driver.py --test-pattern
```

This will:
1. Test all basic colors (red, green, blue, yellow, magenta, cyan, white, off)
2. Run a **pulsing color effect** 🌟
3. Run a **smooth rainbow cycle** 🌈

Press `Ctrl+C` to stop (LED will turn off automatically).

---

## Example Python Code

### Call the Driver Directly

```python
import serial
import json
import time

# Connect to Pico
ser = serial.Serial("/dev/ttyACM0", 115200, timeout=5)
time.sleep(0.2)

# Set LED to red
payload = json.dumps({"method": "set", "r": 255, "g": 0, "b": 0})
req = {
    "method": "driver.call",
    "driver_name": "rgb-led",
    "device_port": "",
    "payload": payload,
}
cmd = json.dumps(req, separators=(',', ':')) + "\n"
ser.write(cmd.encode())
ser.flush()

resp = json.loads(ser.readline().decode())
print(resp)  # {'ok': True, 'result': 'rgb.set:255,0,0'}

# Set LED to green
payload = json.dumps({"method": "set", "r": 0, "g": 255, "b": 0})
# ... repeat request ...

# Turn off
payload = json.dumps({"method": "set", "r": 0, "g": 0, "b": 0})
# ... repeat request ...

ser.close()
```

---

## API Reference

### Driver Method: `set`

**Request:**
```json
{
  "method": "driver.call",
  "driver_name": "rgb-led",
  "payload": "{\"method\": \"set\", \"r\": 255, \"g\": 0, \"b\": 0}"
}
```

**Parameters:**
- `r` (0-255): Red component
- `g` (0-255): Green component
- `b` (0-255): Blue component

Values outside 0-255 are automatically clamped.

**Response (Success):**
```json
{
  "ok": true,
  "result": "rgb.set:255,0,0"
}
```

**Response (Error):**
```json
{
  "ok": false,
  "error": "driver not found: rgb-led"
}
```

---

## Common Colors

| Color      | R   | G   | B   |
|------------|-----|-----|-----|
| Red        | 255 | 0   | 0   |
| Green      | 0   | 255 | 0   |
| Blue       | 0   | 0   | 255 |
| Cyan       | 0   | 255 | 255 |
| Magenta    | 255 | 0   | 255 |
| Yellow     | 255 | 255 | 0   |
| White      | 255 | 255 | 255 |
| Off        | 0   | 0   | 0   |
| Orange     | 255 | 165 | 0   |
| Pink       | 255 | 192 | 203 |
| Purple     | 128 | 0   | 128 |

---

## Troubleshooting

### LED doesn't turn on
- Check connections: Red→GPIO16, Green→GPIO17, Blue→GPIO18, Cathode→GND
- Check resistors: 220Ω in series (if common cathode)
- Test with: `python3 tests/test_rgb_driver.py -v`

### Test fails with "driver not found"
- Rebuild firmware: `python3 flash_pico.py`
- Ensure Pico is running the updated firmware

### Only one color works
- Check individual GPIO connections
- Verify resistor values are similar (balanced brightness)
- Try setting full white to test all channels

### Colors are wrong
- Might have Red/Green/Blue pins swapped—check your connections
- Adjust channel order in `drivers/src/rgb.c` if needed

---

## Driver Source Code

The RGB driver is implemented in:
```
firmware/drivers/src/rgb.c
```

It uses PWM (Pulse Width Modulation) for smooth brightness control on GPIO pins 16, 17, 18.

---

## Next Steps

- Try different color patterns
- Adjust PWM frequency by modifying `RGB_PWM_WRAP` in `drivers/src/rgb.c`
- Extend with new methods (fade, strobe, etc.) using the same pattern
- See [DRIVERS.md](DRIVERS.md) for how to add your own drivers
