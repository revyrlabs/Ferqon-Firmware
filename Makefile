# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
#
# Ferqon Firmware Makefile
#
# This Makefile handles ENVIRONMENT SETUP, PRODUCTION BUNDLING, and the
# SOFTWARE-IN-THE-LOOP (SIL) native desktop target.
# All build, flash, and device operations are handled by the ferqonfw CLI.
#
#   make init        — production setup
#   make init-dev    — development setup
#   make doctor      — check environment
#   make bundle      — create sealed production bundle
#   make cleanroom   — clean-room verification
#   make sil         — build native desktop SIL binary
#   make test-sil    — run SIL integration test over TCP
#
# For everything else, use ferqonfw:
#   ferqonfw build pico       ferqonfw flash pico --port /dev/ttyACM0 --build
#   ferqonfw build all        ferqonfw identify --port /dev/ttyACM0
#   ferqonfw clean pico       ferqonfw selftest --port /dev/ttyACM0
#   ferqonfw list             ferqonfw info pico
#
# Run 'ferqonfw --help' for the full command list.
.PHONY: init init-dev doctor bundle cleanroom sil test-sil sil-clean help

# Default target
.DEFAULT_GOAL := help

# Virtual environment path used when the system Python is not already
# inside an active venv. Override with:
#   make init FERQON_VENV=/path/to/venv
FERQON_VENV ?= .venv

# Detect whether we are already running inside a Python virtual environment.
# When not, init/init-dev create one and install into it.
FERQON_IN_VENV := $(shell python3 -c "import sys; print('1' if sys.prefix != sys.base_prefix else '0')")

ifeq ($(FERQON_IN_VENV),1)
FERQON_PIP := python3 -m pip
FERQON_FW_BIN := ferqonfw
else
FERQON_PIP := $(FERQON_VENV)/bin/pip
FERQON_FW_BIN := $(FERQON_VENV)/bin/ferqonfw
endif

# ─────────────────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────────────────

# One-command setup for production builds.
# Installs the ferqonfw CLI and its dependencies (PlatformIO, pyserial, PyYAML).
init:
	@echo "=== Ferqon Firmware — Production Setup ==="
	@echo ""
	@python3 --version 2>/dev/null || { echo "Error: Python 3.10+ required but not found."; exit 1; }
	@if [ "$(FERQON_IN_VENV)" != "1" ]; then \
		echo "Creating virtual environment at $(FERQON_VENV)..."; \
		python3 -m venv $(FERQON_VENV); \
	fi
	@echo "Installing ferqonfw CLI and production dependencies..."
	@$(FERQON_PIP) install --upgrade pip setuptools wheel >/dev/null
	@$(FERQON_PIP) install .
	@echo ""
	@echo "Verifying environment..."
	@$(FERQON_FW_BIN) doctor || { echo "Warning: doctor check reported issues. See above."; }
	@echo ""
	@echo "=== Setup complete ==="
	@echo ""
	@if [ "$(FERQON_IN_VENV)" != "1" ]; then \
		echo "Activate the virtual environment before using ferqonfw:"; \
		echo "  source $(FERQON_VENV)/bin/activate"; \
		echo ""; \
	else \
		echo "ferqonfw is installed and on your PATH."; \
		echo ""; \
	fi
	@echo "Build firmware:"
	@echo "  ferqonfw build pico        # Build for Raspberry Pi Pico"
	@echo "  ferqonfw build all         # Build all production boards"
	@echo ""
	@echo "Flash and test:"
	@echo "  ferqonfw flash pico --port /dev/ttyACM0 --build"
	@echo "  ferqonfw identify --port /dev/ttyACM0"
	@echo "  ferqonfw selftest --port /dev/ttyACM0"

# One-command setup for development (includes test/lint tools + dev CLI).
init-dev:
	@echo "=== Ferqon Firmware — Development Setup ==="
	@echo ""
	@python3 --version 2>/dev/null || { echo "Error: Python 3.10+ required but not found."; exit 1; }
	@if [ "$(FERQON_IN_VENV)" != "1" ]; then \
		echo "Creating virtual environment at $(FERQON_VENV)..."; \
		python3 -m venv $(FERQON_VENV); \
	fi
	@echo "Installing ferqonfw CLI with development extras (pytest, ruff, black, yamllint)..."
	@$(FERQON_PIP) install --upgrade pip setuptools wheel >/dev/null
	@$(FERQON_PIP) install -e ".[dev]"
	@echo ""
	@echo "Verifying environment..."
	@$(FERQON_FW_BIN) doctor || { echo "Warning: doctor check reported issues. See above."; }
	@echo ""
	@echo "=== Development setup complete ==="
	@echo ""
	@if [ "$(FERQON_IN_VENV)" != "1" ]; then \
		echo "Activate the virtual environment before using the CLIs:"; \
		echo "  source $(FERQON_VENV)/bin/activate"; \
		echo ""; \
	else \
		echo "ferqonfw and ferqonfw-dev are installed and on your PATH."; \
		echo ""; \
	fi
	@echo "Production CLI:  ferqonfw"
	@echo "Development CLI: ferqonfw-dev"
	@echo ""
	@echo "Quick reference:"
	@echo "  ferqonfw build all              # Build all production boards"
	@echo "  ferqonfw-dev test               # Run native unit tests"
	@echo "  ferqonfw-dev gen all            # Generate all artifacts"
	@echo "  ferqonfw-dev validate           # Validate SSOT files"

# Check environment and dependencies without installing anything.
doctor:
	@$(FERQON_FW_BIN) doctor

# ─────────────────────────────────────────────────────────────────────────────
# Software-in-the-Loop (SIL) native desktop target
# ─────────────────────────────────────────────────────────────────────────────

# Build directory and binary names.
SIL_BUILD_DIR := build/sil
SIL_BIN       := $(SIL_BUILD_DIR)/ferqon_sil
SIL_CXX       := g++
SIL_PORT      ?= 3333

# Native compiler flags.  -Isil must come before the system include path so that
# firmware source files pick up the shim Arduino.h instead of the real Arduino.
# -Werror makes the build treat every warning as an error.
SIL_CXXFLAGS := \
	-std=gnu++17 -Wall -Wextra -Werror \
	-Isrc -Isil -Igenerated -Iplatforms/pico/generated \
	-DFERQON_BOARD_NATIVE -DFERQON_HAS_SERIAL1 \
	'-DFERQON_FW_VERSION="1.1.0"' \
	-pthread -D_GNU_SOURCE

SIL_LDFLAGS := -pthread

# All firmware source files plus the SIL host shim and entry point.
# The Arduino HAL implementation is not used on the host build.
SIL_SRCS := $(filter-out src/ferqon_hal_arduino.cpp,$(wildcard src/*.cpp)) $(wildcard sil/*.cpp)
SIL_OBJS := $(SIL_SRCS:%.cpp=$(SIL_BUILD_DIR)/%.o)

# Generate the build_timestamp.h and production_config.h headers that the
# firmware source expects. This reuses the existing PlatformIO pre-build hook.
$(SIL_BUILD_DIR)/generated.stamp:
	@mkdir -p $(SIL_BUILD_DIR)
	@python3 tools/pio_pre_build.py
	@touch $@

# Compile rule preserving the src/ and sil/ directory structure under build/sil/.
$(SIL_BUILD_DIR)/%.o: %.cpp $(SIL_BUILD_DIR)/generated.stamp
	@mkdir -p $(dir $@)
	$(SIL_CXX) $(SIL_CXXFLAGS) -c $< -o $@

# src/uart.cpp has a pre-existing unused-parameter warning in uart_send_handler.
# We silence it only for this object so the original source is not modified and
# the rest of the build still runs with -Werror.
$(SIL_BUILD_DIR)/src/uart.o: src/uart.cpp $(SIL_BUILD_DIR)/generated.stamp
	@mkdir -p $(dir $@)
	$(SIL_CXX) $(SIL_CXXFLAGS) -Wno-unused-parameter -c $< -o $@

# Link the native SIL executable.
$(SIL_BIN): $(SIL_OBJS)
	@mkdir -p $(dir $@)
	$(SIL_CXX) $(SIL_LDFLAGS) $^ -o $@

# Convenience target.
sil: $(SIL_BIN)

# Run the standard-library-only SIL integration test. Starts the SIL binary on
# port 3333 in the background, runs the Python test, then tears the binary down.
test-sil: $(SIL_BIN) tests/sil/test_sil.py
	@printf "[test-sil] Starting SIL binary on TCP port $(SIL_PORT)...\n"
	@rm -f .sil.pid
	$(SIL_BIN) $(SIL_PORT) & echo $$! > .sil.pid
	@sleep 0.5
	@PYTHONPATH= python3 tests/sil/test_sil.py 127.0.0.1 $(SIL_PORT); rc=$$?; kill `cat .sil.pid` 2>/dev/null || true; rm -f .sil.pid; exit $$rc

sil-clean:
	@rm -rf $(SIL_BUILD_DIR) .sil.pid

# ─────────────────────────────────────────────────────────────────────────────
# Production bundle
# ─────────────────────────────────────────────────────────────────────────────

bundle:
	@echo "Creating sealed production source bundle..."
	python3 tools/create_production_bundle.py --output-dir dist/production-bundle

cleanroom: bundle
	@echo "Building all production environments from clean-room bundle..."
	python3 tools/create_production_bundle.py --output-dir dist/production-bundle --verify

# ─────────────────────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────────────────────

help:
	@echo "Ferqon Firmware — Makefile"
	@echo "=========================="
	@echo ""
	@echo "This Makefile handles environment setup and production bundling only."
	@echo "All build, flash, and device operations are handled by the ferqonfw CLI."
	@echo ""
	@echo "Setup:"
	@echo "  make init        - Install production deps + ferqonfw CLI"
	@echo "  make init-dev    - Install production + development deps (ferqonfw + ferqonfw-dev)"
	@echo "  make doctor      - Check environment and dependencies"
	@echo ""
	@echo "Production bundle:"
	@echo "  make bundle      - Create a sealed production source bundle"
	@echo "  make cleanroom   - Build all boards from a fresh clean-room bundle"
	@echo ""
	@echo "Software-in-the-Loop (SIL):"
	@echo "  make sil         - Build native desktop SIL binary"
	@echo "  make test-sil    - Run SIL integration test over TCP"
	@echo "  make sil-clean   - Remove SIL build artifacts"
	@echo ""
	@echo "Build (ferqonfw):"
	@echo "  ferqonfw build <board>   - Build firmware for a board"
	@echo "  ferqonfw build all       - Build all production boards"
	@echo "  ferqonfw clean <board>   - Clean build artifacts"
	@echo "  ferqonfw clean all       - Clean all production boards"
	@echo "  ferqonfw list            - List available platforms"
	@echo "  ferqonfw info <board>    - Show board capabilities"
	@echo ""
	@echo "Flash and test (ferqonfw):"
	@echo "  ferqonfw flash <board> --port <port> [--build]  - Flash firmware"
	@echo "  ferqonfw identify --port <port>                 - Detect Ferqon firmware"
	@echo "  ferqonfw selftest --port <port>                 - Run self-test"
	@echo "  ferqonfw doctor                                 - Check environment"
	@echo ""
	@echo "Development (ferqonfw-dev):"
	@echo "  ferqonfw-dev gen all            - Generate all artifacts"
	@echo "  ferqonfw-dev validate           - Validate SSOT files"
	@echo "  ferqonfw-dev test               - Run native unit tests"
	@echo "  ferqonfw-dev selftest --emulator - Self-test via emulator"
	@echo ""
	@echo "Run 'ferqonfw --help' or 'ferqonfw-dev --help' for full command lists."
