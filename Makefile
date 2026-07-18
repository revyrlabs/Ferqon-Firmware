# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
#
# Ferqon Firmware Makefile
#
# This Makefile handles ENVIRONMENT SETUP and PRODUCTION BUNDLING only.
# All build, flash, and device operations are handled by the ferqonfw CLI.
#
#   make init        — production setup
#   make init-dev    — development setup
#   make doctor      — check environment
#   make bundle      — create sealed production bundle
#   make cleanroom   — clean-room verification
#
# For everything else, use ferqonfw:
#   ferqonfw build pico       ferqonfw flash pico --port /dev/ttyACM0 --build
#   ferqonfw build all        ferqonfw identify --port /dev/ttyACM0
#   ferqonfw clean pico       ferqonfw selftest --port /dev/ttyACM0
#   ferqonfw list             ferqonfw info pico
#
# Run 'ferqonfw --help' for the full command list.
.PHONY: init init-dev doctor bundle cleanroom help

# Default target
.DEFAULT_GOAL := help

# Virtual environment path used when the system Python is externally
# managed (PEP 668 — modern Debian/Ubuntu/Fedora). Override with:
#   make init FERQON_VENV=/path/to/venv
# If you are already inside an active venv, the bare `pip install` path
# is used and FERQON_VENV is not created.
FERQON_VENV ?= .venv

# Detect a PEP 668 externally-managed Python. Prints "1" if installs must
# go into a venv, "0" otherwise. A venv is required when the system Python
# is externally managed AND the user is not already inside a venv.
ferqon_needs_venv = $(shell python3 -c "import sys,sysconfig,os; em=os.path.exists(os.path.join(sysconfig.get_path('stdlib'),'EXTERNALLY-MANAGED')); print('1' if (em and sys.prefix==sys.base_prefix) else '0')")

# ─────────────────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────────────────

# One-command setup for production builds.
# Installs the ferqonfw CLI and its dependencies (PlatformIO, pyserial, PyYAML).
init:
	@echo "=== Ferqon Firmware — Production Setup ==="
	@echo ""
	@python3 --version 2>/dev/null || { echo "Error: Python 3.10+ required but not found."; exit 1; }
	@echo "Installing ferqonfw CLI and production dependencies..."
	@if [ "$(ferqon_needs_venv)" = "1" ]; then \
		echo "System Python is externally managed (PEP 668). Creating a virtual environment at $(FERQON_VENV)..."; \
		python3 -m venv $(FERQON_VENV); \
		$(FERQON_VENV)/bin/python -m pip install --upgrade pip >/dev/null; \
		$(FERQON_VENV)/bin/pip install .; \
	else \
		python3 -m pip install .; \
	fi
	@echo ""
	@echo "Verifying environment..."
	@if [ "$(ferqon_needs_venv)" = "1" ]; then \
		$(FERQON_VENV)/bin/ferqonfw doctor || { echo "Warning: doctor check reported issues. See above."; }; \
	else \
		ferqonfw doctor || { echo "Warning: doctor check reported issues. See above."; }; \
	fi
	@echo ""
	@echo "=== Setup complete ==="
	@echo ""
	@if [ "$(ferqon_needs_venv)" = "1" ]; then \
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
	@echo "Installing ferqonfw CLI with development extras (pytest, ruff, black, yamllint)..."
	@if [ "$(ferqon_needs_venv)" = "1" ]; then \
		echo "System Python is externally managed (PEP 668). Creating a virtual environment at $(FERQON_VENV)..."; \
		python3 -m venv $(FERQON_VENV); \
		$(FERQON_VENV)/bin/python -m pip install --upgrade pip >/dev/null; \
		$(FERQON_VENV)/bin/pip install -e ".[dev]"; \
	else \
		python3 -m pip install -e ".[dev]"; \
	fi
	@echo ""
	@echo "Verifying environment..."
	@if [ "$(ferqon_needs_venv)" = "1" ]; then \
		$(FERQON_VENV)/bin/ferqonfw doctor || { echo "Warning: doctor check reported issues. See above."; }; \
	else \
		ferqonfw doctor || { echo "Warning: doctor check reported issues. See above."; }; \
	fi
	@echo ""
	@echo "=== Development setup complete ==="
	@echo ""
	@if [ "$(ferqon_needs_venv)" = "1" ]; then \
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
	@ferqonfw doctor

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
