# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
.PHONY: pico esp32 esp32s3 teensy40 teensy41 clean all help selftest selftest-emu identify flash-and-test emu-start emu-stop emu-test

# Default target
.DEFAULT_GOAL := help

# Board-specific build targets
pico:
	@echo "Building for Raspberry Pi Pico (Arduino backend)..."
	pio run -e pico_arduino

esp32:
	@echo "Building for ESP32..."
	pio run -e esp32

esp32s3:
	@echo "Building for ESP32-S3..."
	pio run -e esp32s3

teensy40:
	@echo "Building for Teensy 4.0..."
	pio run -e teensy40

teensy41:
	@echo "Building for Teensy 4.1..."
	pio run -e teensy41

# Build all boards
all:
	@echo "Building for all boards..."
	pio run -e pico_arduino
	pio run -e esp32
	pio run -e esp32s3
	pio run -e teensy40
	pio run -e teensy41

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	pio run -t clean

# Upload to board (requires board-specific target)
upload-pico:
	@echo "Uploading to Raspberry Pi Pico..."
	pio run -e pico_arduino -t upload

upload-esp32:
	@echo "Uploading to ESP32..."
	pio run -e esp32 -t upload

upload-esp32s3:
	@echo "Uploading to ESP32-S3..."
	pio run -e esp32s3 -t upload

upload-teensy40:
	@echo "Uploading to Teensy 4.0..."
	pio run -e teensy40 -t upload

upload-teensy41:
	@echo "Uploading to Teensy 4.1..."
	pio run -e teensy41 -t upload

# Monitor serial port
monitor:
	@echo "Starting serial monitor..."
	pio device monitor

# Show configuration
config:
	@echo "Showing PlatformIO configuration..."
	pio project config

# Self-test targets
selftest:
	@echo "Running self-test on device..."
	@echo "Usage: make selftest PORT=/dev/ttyACM0"
	@if [ -z "$(PORT)" ]; then \
		echo "Error: PORT variable required (e.g., PORT=/dev/ttyACM0)"; \
		exit 1; \
	fi
	python3 tests/hil/ferqon_selftest.py --port $(PORT)

selftest-emu:
	@echo "Running self-test on emulator..."
	python3 tests/hil/ferqon_selftest.py --emulator

# Identify target
identify:
	@echo "Identifying device..."
	@echo "Usage: make identify PORT=/dev/ttyACM0"
	@if [ -z "$(PORT)" ]; then \
		echo "Error: PORT variable required (e.g., PORT=/dev/ttyACM0)"; \
		exit 1; \
	fi
	python3 tools/ferqonfw/ferqonfw identify --port $(PORT)

# Flash-and-test convenience target
flash-and-test:
	@echo "Flash and test workflow..."
	@if [ -z "$(BOARD)" ]; then \
		echo "Error: BOARD variable required (e.g., BOARD=pico_arduino)"; \
		exit 1; \
	fi
	@if [ -z "$(PORT)" ]; then \
		echo "Error: PORT variable required (e.g., PORT=/dev/ttyACM0)"; \
		exit 1; \
	fi
	@echo "Building for $(BOARD)..."
	pio run -e $(BOARD)
	@echo "Flashing to $(PORT)..."
	pio run -e $(BOARD) -t upload
	@echo "Waiting for device to enumerate..."
	sleep 3
	@echo "Running self-test..."
	python3 tests/hil/ferqon_selftest.py --port $(PORT)
	@echo "Identifying device..."
	python3 tools/ferqonfw/ferqonfw identify --port $(PORT)

# Emulator targets
EMU_PID_FILE := .emu.pid
EMU_PORT_FILE := .emu.port

emu-start:
	@echo "Starting emulator in PTY mode..."
	@cd tools && python3 -c "import sys; sys.path.insert(0, '.'); from ferqon_emulator import FerqonEmulator; e=FerqonEmulator(pty=True); print(e.start())" > ../$(EMU_PORT_FILE)
	@cd tools && python3 ferqon_emulator.py --pty &
	@echo $$! > $(EMU_PID_FILE)
	@sleep 1
	@echo "Emulator started on port: $$(cat $(EMU_PORT_FILE))"
	@echo "Use 'make emu-test' to run self-test, or 'make emu-stop' to stop"

emu-stop:
	@if [ -f $(EMU_PID_FILE) ]; then \
		kill $$(cat $(EMU_PID_FILE)) 2>/dev/null || true; \
		rm -f $(EMU_PID_FILE); \
		echo "Emulator stopped"; \
	else \
		echo "No emulator running"; \
	fi
	@rm -f $(EMU_PORT_FILE)

emu-test:
	@if [ ! -f $(EMU_PORT_FILE) ]; then \
		echo "Emulator not running. Start with 'make emu-start'"; \
		exit 1; \
	fi
	@echo "Running self-test on emulator at $$(cat $(EMU_PORT_FILE))..."
	@python3 tests/hil/ferqon_selftest.py --port $$(cat $(EMU_PORT_FILE))

emu-identify:
	@if [ ! -f $(EMU_PORT_FILE) ]; then \
		echo "Emulator not running. Start with 'make emu-start'"; \
		exit 1; \
	fi
	@echo "Identifying emulator at $$(cat $(EMU_PORT_FILE))..."
	@python3 tools/ferqonfw/ferqonfw identify --port $$(cat $(EMU_PORT_FILE))

# Help target
help:
	@echo "Ferqon Firmware Build System"
	@echo "=============================="
	@echo ""
	@echo "Build targets:"
	@echo "  make pico        - Build for Raspberry Pi Pico (default)"
	@echo "  make esp32       - Build for ESP32"
	@echo "  make esp32s3     - Build for ESP32-S3"
	@echo "  make teensy40    - Build for Teensy 4.0"
	@echo "  make teensy41    - Build for Teensy 4.1"
	@echo "  make all         - Build for all boards"
	@echo ""
	@echo "Upload targets:"
	@echo "  make upload-pico     - Upload to Raspberry Pi Pico"
	@echo "  make upload-esp32    - Upload to ESP32"
	@echo "  make upload-esp32s3  - Upload to ESP32-S3"
	@echo "  make upload-teensy40 - Upload to Teensy 4.0"
	@echo "  make upload-teensy41 - Upload to Teensy 4.1"
	@echo ""
	@echo "Utility targets:"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make monitor    - Start serial monitor"
	@echo "  make config     - Show PlatformIO configuration"
	@echo "  make help       - Show this help message"
	@echo ""
	@echo "Self-test and detection:"
	@echo "  make selftest PORT=/dev/ttyACM0   - Run self-test on device"
	@echo "  make selftest-emu                 - Run self-test on emulator (in-process)"
	@echo "  make identify PORT=/dev/ttyACM0   - Detect Ferqon firmware on device"
	@echo "  make flash-and-test BOARD=pico_arduino PORT=/dev/ttyACM0 - Build, flash, test, identify"
	@echo ""
	@echo "Emulator (PTY mode - acts like real serial port):"
	@echo "  make emu-start   - Start emulator in PTY mode (creates virtual serial port)"
	@echo "  make emu-test    - Run self-test on running emulator"
	@echo "  make emu-identify - Identify running emulator"
	@echo "  make emu-stop    - Stop emulator"
	@echo ""
	@echo "Direct pio commands also work:"
	@echo "  pio run -e <board>   - Build for specific board"
	@echo "  pio run               - Build for default board (pico_arduino)"