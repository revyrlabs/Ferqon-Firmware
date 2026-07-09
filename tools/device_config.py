# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
Firmware-side test configuration.

This module provides the same environment variable contract as test/config.py
but is designed for firmware-side scripts that must not import the backend
test package. All values are retrieved via getter functions to ensure pure
imports (no side effects at import time).
"""

from __future__ import annotations

import os
import shutil


def get_default_device_port() -> str:
    """Get the default serial device port for tests."""
    return os.getenv("FERQON_TEST_DEVICE_PORT", "/dev/ttyACM0")


def get_mcu_port() -> str:
    """Get the MCU serial port for HIL tests."""
    return os.getenv("FERQON_MCU_PORT", get_default_device_port())


def get_dut_port() -> str:
    """Get the DUT serial port for HIL tests."""
    return os.getenv("FERQON_DUT_PORT", "/dev/ttyUSB0")


def get_default_baudrate() -> int:
    """Get the default baud rate for serial communication."""
    return int(os.getenv("FERQON_TEST_BAUDRATE", "115200"))


def get_board_name() -> str:
    """Get the board name for firmware tests."""
    return os.getenv("FERQON_TEST_BOARD", "pico")


def get_emulator_enabled() -> bool:
    """Check if emulator mode is enabled for tests."""
    return os.getenv("FERQON_TEST_USE_EMULATOR", "0") == "1"


def get_pio_path() -> str:
    """Get the PlatformIO CLI path."""
    # Allow override via env, otherwise use shutil.which to find it
    custom_path = os.getenv("FERQON_PIO_BIN")
    if custom_path:
        return custom_path
    pio_path = shutil.which("pio")
    if pio_path:
        return pio_path
    # Fallback to common executable name; the caller should check existence
    return "pio"


def get_backend_url() -> str:
    """Get the backend API URL for tests (firmware may need this for OTA)."""
    return os.getenv("FERQON_TEST_BACKEND_URL", "http://localhost:8000")


__all__ = [
    "get_default_device_port",
    "get_mcu_port",
    "get_dut_port",
    "get_default_baudrate",
    "get_board_name",
    "get_emulator_enabled",
    "get_pio_path",
    "get_backend_url",
]
