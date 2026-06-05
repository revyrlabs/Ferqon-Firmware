.PHONY: pico esp32 esp32s3 teensy40 teensy41 clean all help

# Default target
.DEFAULT_GOAL := help

# Board-specific build targets
pico:
	@echo "Building for Raspberry Pi Pico..."
	pio run -e pico

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
	pio run -e pico
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
	pio run -e pico -t upload

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
	@echo "Direct pio commands also work:"
	@echo "  pio run -e <board>   - Build for specific board"
	@echo "  pio run               - Build for default board (pico)"
