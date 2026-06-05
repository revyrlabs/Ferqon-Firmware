# Pico Build & Flash Tools

## Quick Reference

### Flash the firmware (core runtime only)
```bash
python3 pico/flash_pico.py
```
Builds the Pico runtime firmware and flashes it via BOOTSEL mass-storage or serial.

### Compile and upload a driver
```bash
python3 pico/flash_driver.py \
  --src pico/firmware_driver_runtime/drivers_user/user_echo.c \
  --port /dev/ttyACM0 \
  --address 0x100000 \
  --verify \
  --driver-name user-echo
```
Attempts to compile the driver and upload it to a running Pico. If that fails, falls back to recompiling the full firmware with the driver included.

### Upload a raw driver binary to flash
```bash
python3 pico/driver_uploader.py \
  --port /dev/ttyACM0 \
  --address 0x100000 \
  /path/to/driver.bin
```
Low-level: sends a prebuilt driver binary to the Pico via chunked base64 over serial.

## Tools Overview

| File | Purpose | Use Case |
|------|---------|----------|
| `flash_pico.py` | Build firmware; flash via BOOTSEL or serial | Firmware-only updates after code changes |
| `flash_driver.py` | Compile driver C source; try standalone upload then fallback to full rebuild | Iterating on a single driver implementation |
| `driver_uploader.py` | Send pre-compiled driver binary to Pico over serial | Advanced: uploading pre-signed or pre-tested binaries |
| `gen_commands.py` | Generate command.hpp from commands.json | Internal build step (auto-run by CMake) |
| `setup_generated.py` | Generate protocol stubs | Internal build step (auto-run by CMake) |

## Consolidation Notes

- **Removed:** `auto_flash_all.py` (merged into `flash_driver.py`)
- The new `flash_driver.py` is the all-in-one tool with full fallback logic and optional verification
- Both `flash_pico.py` and `flash_driver.py` are user-facing; the others are support scripts

## Environment Variables

- `FERQON_DRIVER_RPC_OVER_SERIAL=1` — Enable driver RPC forwarding from backend to Pico over serial (backend only)

## Dev Workflow Example

1. Build and flash base firmware once:
   ```bash
   cd pico && python3 flash_pico.py
   ```

2. Iteratively develop a driver:
   ```bash
   python3 pico/flash_driver.py --src pico/firmware_driver_runtime/drivers_user/my_driver.c --port /dev/ttyACM0 --address 0x100000 --verify --driver-name my-driver
   ```

3. When firmware changes, go back to step 1.
