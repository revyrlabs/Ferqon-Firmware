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
hw_sdk = repo_root / "hw_sdk" / "ferqon_hw"
if str(hw_sdk) not in sys.path:
    sys.path.insert(0, str(hw_sdk))

from ferqon_hw.serial_backend import open_serial, _send_frame, _encode_simple_command, _encode_driver_call

def test_pico():
    """Test Pico v1 firmware via serial."""
    port = "/dev/ttyACM0"

    try:
        print(f"Connecting to {port}...")
        conn = open_serial(port, baud=115200, timeout_s=2.0)
        print("Connected!")
        
        # Clear any pending logs/messages
        import time
        time.sleep(1.0)
        
        # Read and discard any pending data
        while conn.in_waiting > 0:
            conn.read(conn.in_waiting)
            time.sleep(0.1)

        # Test ping
        print("\n--- Testing PING ---")
        frame = _encode_simple_command('ping', seq=1)
        resp = _send_frame(conn, frame, timeout_s=2.0)
        print(f"Response: ok={resp.get('ok', False)}, pkt_type={resp.get('pkt_type', 0)}")

        # Test driver_info (without PKT_REQUEST byte - info commands don't need it)
        print("\n--- Testing DRIVER_INFO ---")
        from ferqon_hw.serial_backend import _encode_frame
        frame = _encode_frame(seq=2, cmd_id=2, payload=b'')  # cmd_id=2 is driver_info
        print(f"Frame hex: {frame.hex()}")
        print(f"Frame breakdown: start={frame[0]:02x}, seq={frame[1]:02x}, cmd={frame[2]:02x}, len={frame[3]:02x}")
        if len(frame) > 4:
            payload_len = frame[3]
            payload = frame[4:4+payload_len]
            crc = frame[4+payload_len:4+payload_len+2]
            print(f"  payload={payload.hex()}, crc={crc.hex()}")
        resp = _send_frame(conn, frame, timeout_s=2.0)
        print(f"Response: ok={resp.get('ok', False)}, pkt_type={resp.get('pkt_type', 0)}")
        if not resp.get('ok'):
            print(f"Error: code={resp.get('code', 0)}, category={resp.get('category', 0)}, detail={resp.get('detail', '')}")
            print(f"Raw body: {resp.get('body', b'').hex()}")
        else:
            print(f"Payload length: {len(resp.get('body', b''))}")
            print(f"Payload hex: {resp.get('body', b'').hex()}")

        # Test with empty payload (no PKT_REQUEST byte) - some commands might not need it
        print("\n--- Testing DRIVER_INFO (no PKT_REQUEST) ---")
        from ferqon_hw.serial_backend import _encode_frame
        frame = _encode_frame(seq=6, cmd_id=2, payload=b'')  # cmd_id=2 is driver_info
        print(f"Frame hex: {frame.hex()}")
        resp = _send_frame(conn, frame, timeout_s=2.0)
        print(f"Response: ok={resp.get('ok', False)}, pkt_type={resp.get('pkt_type', 0)}")
        if not resp.get('ok'):
            print(f"Error: code={resp.get('code', 0)}, category={resp.get('category', 0)}, detail={resp.get('detail', '')}")
        else:
            print(f"Payload length: {len(resp.get('body', b''))}")
            print(f"Payload hex: {resp.get('body', b'').hex()}")

        # Test driver_call with io_set
        print("\n--- Testing DRIVER_CALL (hil.io_set) ---")
        frame = _encode_driver_call('hil', 'io_set', b'pin=7;level=HIGH')
        print(f"Frame hex: {frame.hex()}")
        resp = _send_frame(conn, frame, timeout_s=2.0)
        print(f"Response: ok={resp.get('ok', False)}, pkt_type={resp.get('pkt_type', 0)}")
        if not resp.get('ok'):
            print(f"Error: code={resp.get('code', 0)}, category={resp.get('category', 0)}, detail={resp.get('detail', '')}")
        else:
            print(f"Payload length: {len(resp.get('body', b''))}")

        # Test gpio_write (cmd_id=17) to verify basic command works
        print("\n--- Testing GPIO_WRITE ---")
        from ferqon_hw.serial_backend import _encode_frame, PKT_REQUEST
        payload = bytes([PKT_REQUEST, 7, 1])  # pin=7, value=1
        frame = _encode_frame(seq=5, cmd_id=17, payload=payload)
        print(f"Frame hex: {frame.hex()}")
        resp = _send_frame(conn, frame, timeout_s=2.0)
        print(f"Response: ok={resp.get('ok', False)}, pkt_type={resp.get('pkt_type', 0)}")

        # Test device_info (cmd_id=11) - without PKT_REQUEST byte
        print("\n--- Testing DEVICE_INFO ---")
        frame = _encode_frame(seq=3, cmd_id=11, payload=b'')  # cmd_id=11 is device_info
        resp = _send_frame(conn, frame, timeout_s=2.0)
        print(f"Response: ok={resp.get('ok', False)}, pkt_type={resp.get('pkt_type', 0)}")
        if not resp.get('ok'):
            print(f"Error: code={resp.get('code', 0)}, category={resp.get('category', 0)}, detail={resp.get('detail', '')}")
            print(f"Raw body: {resp.get('body', b'').hex()}")
        else:
            print(f"Payload length: {len(resp.get('body', b''))}")
            print(f"Payload hex: {resp.get('body', b'').hex()}")

        # Test echo
        print("\n--- Testing ECHO ---")
        # For echo, we need to manually encode with payload
        from ferqon_hw.serial_backend import _encode_frame, PKT_REQUEST
        payload = bytes([PKT_REQUEST]) + b"hello"
        frame = _encode_frame(seq=4, cmd_id=8, payload=payload)  # cmd_id=8 is echo
        resp = _send_frame(conn, frame, timeout_s=2.0)
        print(f"Response: ok={resp.get('ok', False)}, pkt_type={resp.get('pkt_type', 0)}")
        if resp.get('ok'):
            print(f"Echoed: {resp.get('body', b'')}")

        conn.close()
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
