#!/usr/bin/env python3
"""
Simple test script for Pico v1 firmware.
"""

import sys
import logging
from pathlib import Path

# Enable debug logging to see firmware logs
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

# Add hw_sdk to path (relative to repo root)
repo_root = Path(__file__).parent.parent.parent
hw_sdk = repo_root / "packages" / "hw-sdk" / "ferqon_hw"
if str(hw_sdk) not in sys.path:
    sys.path.insert(0, str(hw_sdk))

from ferqon_hw.serial_backend import open_serial, FerqonSerial
from device_config import get_default_device_port, get_default_baudrate
from device_discovery import find_board

def test_pico():
    """Test Pico v1 firmware via serial."""
    port = find_board("pico") or get_default_device_port()

    try:
        print(f"Connecting to {port}...")
        serial = FerqonSerial(port, baud=get_default_baudrate(), timeout_s=2.0)
        print("Connected!")

        # Test ping
        print("\n--- Testing PING ---")
        # Read any initial data
        import time
        time.sleep(0.5)
        if hasattr(serial._conn, 'in_waiting'):
            pending = serial._conn.read(serial._conn.in_waiting)
            if pending:
                print(f"Pending data before ping: {pending.hex()}")
        
        resp = serial.call("ping")
        print(f"Response: ok={resp.get('ok', False)}, pkt_type={resp.get('pkt_type', 0)}")
        print(f"Raw response: {resp}")

        # Test driver_info
        print("\n--- Testing DRIVER_INFO ---")
        resp = serial.call("driver_info")
        print(f"Response: ok={resp.get('ok', False)}, pkt_type={resp.get('pkt_type', 0)}")
        if not resp.get('ok'):
            print(f"Error: code={resp.get('code', 0)}, category={resp.get('category', 0)}, detail={resp.get('detail', '')}")
        else:
            print(f"Payload length: {len(resp.get('body', b''))}")
            print(f"Payload hex: {resp.get('body', b'').hex()}")

        # Test device_info
        print("\n--- Testing DEVICE_INFO ---")
        resp = serial.call("device_info")
        print(f"Response: ok={resp.get('ok', False)}, pkt_type={resp.get('pkt_type', 0)}")
        if not resp.get('ok'):
            print(f"Error: code={resp.get('code', 0)}, category={resp.get('category', 0)}, detail={resp.get('detail', '')}")
        else:
            print(f"Payload length: {len(resp.get('body', b''))}")
            print(f"Payload hex: {resp.get('body', b'').hex()}")

        # Test echo
        print("\n--- Testing ECHO ---")
        resp = serial.call("echo", message="hello")
        print(f"Response: ok={resp.get('ok', False)}, pkt_type={resp.get('pkt_type', 0)}")
        if resp.get('ok'):
            print(f"Echoed: {resp.get('body', b'')}")

        serial.close()
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
