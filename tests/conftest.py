# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
conftest.py
-----------
Pytest fixtures for Ferqon firmware driver tests.

Provides fixtures for:
- Hardware device detection and connection
- Emulator mode fallback
- Auto-flash capability
- Configuration management via device_config and device_discovery
"""

import os
import sys
from pathlib import Path
from typing import Generator

import pytest

# Add tools to path for imports
tools_dir = Path(__file__).parent.parent / "tools"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from device_config import (
    get_default_device_port,
    get_default_baudrate,
    get_board_name,
    get_emulator_enabled,
)
from device_discovery import find_board


# ---------------------------------------------------------------------------
# Pytest markers
# ---------------------------------------------------------------------------

def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "hardware: marks tests that require physical hardware"
    )
    config.addinivalue_line(
        "markers", "emulator: marks tests that can run with emulator fallback"
    )
    config.addinivalue_line(
        "markers", "auto_flash: marks tests that can auto-flash firmware"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


# ---------------------------------------------------------------------------
# Configuration fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_port() -> str:
    """Get the test serial port from environment or auto-discover."""
    port = os.environ.get("FERQON_TEST_DEVICE_PORT", "auto")
    if port == "auto":
        board = os.environ.get("FERQON_TEST_BOARD", get_board_name())
        try:
            discovered = find_board(board_name=board)
            if discovered:
                return discovered
        except Exception:
            pass
        # Fallback to default
        return get_default_device_port()
    return port


@pytest.fixture(scope="session")
def test_baudrate() -> int:
    """Get the test baud rate from environment or default."""
    return int(os.environ.get("FERQON_TEST_BAUDRATE", get_default_baudrate()))


@pytest.fixture(scope="session")
def test_board() -> str:
    """Get the test board name from environment or default."""
    return os.environ.get("FERQON_TEST_BOARD", get_board_name())


@pytest.fixture(scope="session")
def use_emulator() -> bool:
    """Determine if emulator mode should be used."""
    env_emulator = os.environ.get("FERQON_TEST_USE_EMULATOR")
    if env_emulator is not None:
        return env_emulator == "1"
    return get_emulator_enabled()


@pytest.fixture(scope="session")
def auto_flash() -> bool:
    """Determine if auto-flash should be enabled."""
    return os.environ.get("FERQON_AUTO_FLASH", "0") == "1"


# ---------------------------------------------------------------------------
# Device connection fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def device_connection(test_port: str, test_baudrate: int, use_emulator: bool):
    """
    Provide a device connection for tests.
    
    This fixture:
    1. Auto-discovers the device if port is "auto"
    2. Falls back to emulator if hardware not found and emulator enabled
    3. Returns a connection object or None if no device available
    
    Tests should skip if the fixture returns None (no hardware/emulator available).
    """
    if use_emulator:
        # Import emulator module only when needed
        try:
            from ferqon_emulator import FerqonEmulator
            emulator = FerqonEmulator()
            emulator.start()
            yield emulator.get_pty_path()
            emulator.stop()
            return
        except ImportError:
            pytest.skip("Emulator module not available")
        except Exception as e:
            pytest.skip(f"Failed to start emulator: {e}")
    
    # Hardware mode
    if test_port == "auto":
        pytest.skip("No hardware device found and emulator disabled")
    
    # Return port for tests to use
    yield test_port


# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to skip tests based on conditions.

    - Skip hardware tests if no device available and emulator disabled
    - Skip auto_flash tests if FERQON_AUTO_FLASH=0
    """
    use_emulator_mode = os.environ.get("FERQON_TEST_USE_EMULATOR") == "1" or get_emulator_enabled()
    auto_flash_enabled = os.environ.get("FERQON_AUTO_FLASH", "0") == "1"

    # Check if hardware is available
    hardware_available = False
    if not use_emulator_mode:
        try:
            board = os.environ.get("FERQON_TEST_BOARD", get_board_name())
            port = find_board(board_name=board)
            hardware_available = port is not None
        except Exception:
            hardware_available = False

    for item in items:
        # Skip hardware tests if no hardware and emulator disabled
        if "hardware" in item.keywords and not hardware_available and not use_emulator_mode:
            item.add_marker(pytest.mark.skip(reason="No hardware available and emulator disabled"))

        # Skip auto_flash tests if disabled
        if "auto_flash" in item.keywords and not auto_flash_enabled:
            item.add_marker(pytest.mark.skip(reason="Auto-flash disabled (set FERQON_AUTO_FLASH=1)"))


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def skip_if_no_hardware(device_connection):
    """Skip test if no hardware connection available."""
    if device_connection is None:
        pytest.skip("No hardware connection available")


@pytest.fixture
def skip_if_emulator(use_emulator):
    """Skip test if running in emulator mode."""
    if use_emulator:
        pytest.skip("Test requires real hardware (emulator mode active)")




@pytest.fixture
def skip_if_hardware(use_emulator):
    """Skip test if running on real hardware."""
    if not use_emulator:
        pytest.skip("Test requires emulator mode (hardware mode active)")