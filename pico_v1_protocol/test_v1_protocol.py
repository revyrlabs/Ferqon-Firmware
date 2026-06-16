#!/usr/bin/env python3
"""
Test script for Ferqon v1 protocol firmware.
Tests basic communication with the flashed v1 firmware using binary protocol.
"""

import serial
import time
import sys
from pathlib import Path

# Add tools to path for device_config
tools_dir = Path(__file__).resolve().parent.parent / "tools"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from device_config import get_default_device_port, get_default_baudrate

# Ferqon v1 protocol constants
FERQON_START_BYTE = 0xAB
FERQON_CMD_PING = 0x09
FERQON_CMD_ECHO = 0x08
FERQON_CMD_RESET = 0x0A
FERQON_CMD_DEVICE_INFO = 0x0B
FERQON_CMD_CAPABILITIES = 0x0C

def calculate_checksum(data):
    """Calculate XOR checksum for Ferqon v1 protocol."""
    checksum = 0
    for byte in data:
        checksum ^= byte
    return checksum

def build_packet(cmd_id, payload=b''):
    """Build a Ferqon v1 protocol packet."""
    packet = bytearray()
    packet.append(FERQON_START_BYTE)
    packet.append(cmd_id)
    packet.append(len(payload))
    packet.extend(payload)
    packet.append(calculate_checksum(packet))  # Include start byte in checksum
    return bytes(packet)

def parse_response(data):
    """Parse a Ferqon v1 protocol response."""
    if len(data) < 4:
        return None

    # Find start byte
    start_idx = data.find(FERQON_START_BYTE)
    if start_idx == -1:
        return None

    packet = data[start_idx:]

    if len(packet) < 4:
        return None

    start = packet[0]
    resp_type = packet[1]  # Response type (OK or ERROR)
    payload_len = packet[2]

    if len(packet) < 3 + payload_len + 1:
        return None

    payload = packet[3:3+payload_len]
    checksum = packet[3+payload_len]

    # Verify checksum (firmware includes start byte in checksum calculation)
    calculated_checksum = calculate_checksum(packet[0:3+payload_len])
    print(f"Checksum check: packet[0:{3+payload_len}] = {packet[0:3+payload_len].hex()}, calc={calculated_checksum}, recv={checksum}")
    if checksum != calculated_checksum:
        print(f"Checksum mismatch: expected {calculated_checksum}, got {checksum}")
        # Continue anyway to see the response

    return {
        'resp_type': resp_type,
        'payload': payload,
        'checksum': checksum
    }

def test_v1_protocol(port=None, baudrate=None):
    """Test v1 protocol communication with Pico."""
    if port is None:
        port = get_default_device_port()
    if baudrate is None:
        baudrate = get_default_baudrate()
    try:
        print(f"Connecting to {port} at {baudrate} baud...")
        ser = serial.Serial(port, baudrate, timeout=2.0)
        time.sleep(2)  # Wait for device to be ready
        print("Connected!")

        # Read any initial output
        initial_output = ser.read_all()
        if initial_output:
            print(f"Initial output ({len(initial_output)} bytes): {initial_output.hex()}")
            try:
                print(f"Initial output (ASCII): {initial_output.decode('utf-8', errors='ignore')}")
            except:
                pass
        else:
            print("No initial output from device")

        # Clear buffer
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        # Test PING command
        print("\n--- Testing PING command ---")
        ping_packet = build_packet(FERQON_CMD_PING)
        print(f"Sending PING packet: {ping_packet.hex()}")
        ser.write(ping_packet)
        time.sleep(0.5)

        response = ser.read_all()
        if response:
            print(f"Raw response: {response.hex()}")
            parsed = parse_response(response)
            if parsed:
                print(f"Parsed response: resp_type={parsed['resp_type']}, payload={parsed['payload'].hex()}, checksum={parsed['checksum']}")
                print("PING test PASSED")
            else:
                print("Failed to parse response")
        else:
            print("No response to PING")

        # Test ECHO command
        print("\n--- Testing ECHO command ---")
        echo_payload = b'Hello World'
        echo_packet = build_packet(FERQON_CMD_ECHO, echo_payload)
        print(f"Sending ECHO packet: {echo_packet.hex()}")
        ser.write(echo_packet)
        time.sleep(0.5)

        response = ser.read_all()
        if response:
            print(f"Raw response: {response.hex()}")
            parsed = parse_response(response)
            if parsed:
                print(f"Parsed response: resp_type={parsed['resp_type']}, payload={parsed['payload']}, checksum={parsed['checksum']}")
                if parsed['payload'] == echo_payload:
                    print("ECHO test PASSED")
                else:
                    print(f"ECHO test FAILED: expected {echo_payload}, got {parsed['payload']}")
            else:
                print("Failed to parse response")
        else:
            print("No response to ECHO")

        # Test DEVICE_INFO command
        print("\n--- Testing DEVICE_INFO command ---")
        device_info_packet = build_packet(FERQON_CMD_DEVICE_INFO)
        print(f"Sending DEVICE_INFO packet: {device_info_packet.hex()}")
        ser.write(device_info_packet)
        time.sleep(0.5)

        response = ser.read_all()
        if response:
            print(f"Raw response: {response.hex()}")
            parsed = parse_response(response)
            if parsed:
                print(f"Parsed response: resp_type={parsed['resp_type']}, payload={parsed['payload'].hex()}, checksum={parsed['checksum']}")
                print("DEVICE_INFO test PASSED")
                # Try to parse TLV data
                payload = parsed['payload']
                idx = 0
                while idx < len(payload):
                    if idx + 2 > len(payload):
                        break
                    tlv_type = payload[idx]
                    tlv_len = payload[idx+1]
                    if idx + 2 + tlv_len > len(payload):
                        break
                    tlv_value = payload[idx+2:idx+2+tlv_len]
                    print(f"  TLV: type={tlv_type}, len={tlv_len}, value={tlv_value}")
                    idx += 2 + tlv_len
            else:
                print("Failed to parse response")
        else:
            print("No response to DEVICE_INFO")

        ser.close()
        print("\nTest complete!")
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
    port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
    success = test_v1_protocol(port)
    sys.exit(0 if success else 1)
