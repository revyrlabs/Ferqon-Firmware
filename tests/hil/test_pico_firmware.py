#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
Test script for Pico firmware using serial_client.
"""

import sys
from pathlib import Path

# Add hw_sdk to path. Use FERQON_HW_SDK_PATH if set, otherwise assume the
# sibling packages/hw-sdk layout in the workspace root.
import os
hw_sdk_env = os.getenv("FERQON_HW_SDK_PATH")
if hw_sdk_env:
    hw_sdk = Path(hw_sdk_env)
else:
    repo_root = Path(__file__).parent.parent.parent
    hw_sdk = repo_root / "packages" / "hw-sdk" / "ferqon_hw"
if str(hw_sdk) not in sys.path:
    sys.path.insert(0, str(hw_sdk))

# Add tools to path
tools_dir = Path(__file__).parent.parent.parent / "tools"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from serial_client import connect, Command
from device_config import get_default_device_port, get_default_baudrate
from device_discovery import find_board

def test_pico():
    """Test Pico firmware via serial."""
    port = find_board("pico") or get_default_device_port()

    try:
        print(f"Connecting to {port}...")
        mcu = connect(port, baudrate=get_default_baudrate())
        print("Connected!")

        # Test ping
        print("\n--- Testing PING ---")
        resp = mcu.send(Command.PING(), timeout=2.0)
        print(f"Response: ok={resp.ok}, ack={resp.ack}, message={resp.message}")

        # Test driver info
        print("\n--- Testing DRIVER_INFO ---")
        resp = mcu.send(Command.DRIVER_INFO(), timeout=2.0)
        print(f"Response: ok={resp.ok}, ack={resp.ack}, message={resp.message}")

        # Test echo
        print("\n--- Testing ECHO ---")
        resp = mcu.send(Command.ECHO("hello"), timeout=2.0)
        print(f"Response: ok={resp.ok}, ack={resp.ack}, message={resp.message}")

        mcu.close()
        print("\n✓ All tests passed!")
        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pico()
    sys.exit(0 if success else 1)