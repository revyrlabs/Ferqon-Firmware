#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""Direct firmware test over serial port - no backend required.

Tests the Ferqon binary protocol with proper framing.
"""

import sys
from pathlib import Path

# Ensure the tools directory is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import serial
import time
import struct

from device_config import get_default_device_port, get_default_baudrate

# Protocol constants from ferqon_commands.h
FERQON_START_BYTE = 0xAB
FERQON_CMD_PING = 9
FERQON_CMD_ECHO = 8
FERQON_CMD_DRIVER_INFO = 2
FERQON_CMD_DEVICE_INFO = 11
FERQON_CMD_RESET = 10
FERQON_PKT_REQUEST = 1
FERQON_PKT_ACK = 2
FERQON_PKT_DONE = 3
FERQON_PKT_ERROR = 4
FERQON_CRC_INIT = 0xFFFF
FERQON_CRC_POLY = 0x1021


def crc16_ccitt_false(data):
    """Calculate CRC-16/CCITT-FALSE."""
    crc = FERQON_CRC_INIT
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ FERQON_CRC_POLY
            else:
                crc = (crc << 1)
        crc = crc & 0xFFFF
    return crc


def build_frame(seq, cmd_id, payload=b''):
    """Build a complete Ferqon protocol frame."""
    # Prepend PKT_REQUEST byte to payload for all commands except DRIVER_INFO/DEVICE_INFO
    if cmd_id not in [FERQON_CMD_DRIVER_INFO, FERQON_CMD_DEVICE_INFO]:
        payload = bytes([FERQON_PKT_REQUEST]) + payload

    # Header: SEQ + CMD + LEN
    header = bytes([seq, cmd_id, len(payload)])

    # Calculate CRC over header + payload
    crc_data = header + payload
    crc = crc16_ccitt_false(crc_data)

    # Build full frame: START + header + payload + CRC_LO + CRC_HI
    frame = bytes([FERQON_START_BYTE]) + crc_data + bytes([crc & 0xFF, (crc >> 8) & 0xFF])
    return frame


def test_firmware(port=None, baudrate=None):
    """Test basic firmware commands over serial."""
    if port is None:
        port = get_default_device_port()
    if baudrate is None:
        baudrate = get_default_baudrate()
    print(f"Testing firmware on {port} at {baudrate} baud")

    try:
        with serial.Serial(port, baudrate, timeout=2) as ser:
            time.sleep(2)  # Wait for MCU to be ready
            print(f"Connected to {port}")

            # Clear any pending data
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            # Test 1: PING command (CMD=9, no payload)
            print("\n--- Test 1: PING ---")
            frame = build_frame(seq=1, cmd_id=FERQON_CMD_PING)
            print(f"Sent frame: {frame.hex()}")
            ser.write(frame)
            time.sleep(0.5)
            response = ser.read_all()
            print(f"Response ({len(response)} bytes): {response.hex()}")
            if len(response) > 0:
                # Check for valid frame structure
                if response[0] == FERQON_START_BYTE:
                    print("✓ Valid frame start byte")
                    if len(response) >= 6:
                        pkt_type = response[4] if len(response) > 4 else None
                        if pkt_type == FERQON_PKT_ACK or pkt_type == FERQON_PKT_DONE:
                            print("✓ PING successful - received ACK/DONE")
                        else:
                            print(f"✓ PING response received (packet type: {pkt_type})")
                    else:
                        print("✓ PING response received (short frame)")
                else:
                    print(f"✗ Invalid response start byte: {response[0]:02x}")
            else:
                print("✗ PING failed - no response")

            # Test 2: ECHO command (CMD=8, payload="hello")
            print("\n--- Test 2: ECHO ---")
            payload = b'hello'
            frame = build_frame(seq=2, cmd_id=FERQON_CMD_ECHO, payload=payload)
            print(f"Sent frame: {frame.hex()}")
            ser.write(frame)
            time.sleep(0.5)
            response = ser.read_all()
            print(f"Response ({len(response)} bytes): {response.hex()}")
            if len(response) > 0 and response[0] == FERQON_START_BYTE:
                print("✓ ECHO response received")
                # Try to extract echoed data
                if len(response) > 6:
                    echo_data = response[5:-2]  # Skip header, get payload before CRC
                    print(f"  Echoed data: {echo_data}")
            else:
                print("✗ ECHO failed")

            # Test 3: DRIVER_INFO command (CMD=2, no payload)
            print("\n--- Test 3: DRIVER_INFO ---")
            frame = build_frame(seq=3, cmd_id=FERQON_CMD_DRIVER_INFO)
            print(f"Sent frame: {frame.hex()}")
            ser.write(frame)
            time.sleep(0.5)
            response = ser.read_all()
            print(f"Response ({len(response)} bytes): {response.hex()}")
            if len(response) > 0 and response[0] == FERQON_START_BYTE:
                print("✓ DRIVER_INFO response received")
            else:
                print("✗ DRIVER_INFO failed")

            # Test 4: RESET command (CMD=10, no payload)
            print("\n--- Test 4: RESET ---")
            frame = build_frame(seq=4, cmd_id=FERQON_CMD_RESET)
            print(f"Sent frame: {frame.hex()}")
            ser.write(frame)
            time.sleep(0.5)
            response = ser.read_all()
            print(f"Response ({len(response)} bytes): {response.hex()}")
            if len(response) > 0 and response[0] == FERQON_START_BYTE:
                print("✓ RESET response received")
            else:
                print("✗ RESET failed")

        print("\n=== Firmware test complete ===")
        return True

    except serial.SerialException as e:
        print(f"Serial error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else get_default_device_port()
    success = test_firmware(port)
    sys.exit(0 if success else 1)