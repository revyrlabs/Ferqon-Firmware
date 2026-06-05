#!/usr/bin/env python3
"""
Simple serial test for Pico firmware.
Tests basic communication with the flashed firmware.
"""

import serial
import time
import sys

def test_pico_serial(port="/dev/ttyACM0", baudrate=115200):
    """Test serial communication with Pico."""
    try:
        print(f"Connecting to {port} at {baudrate} baud...")
        ser = serial.Serial(port, baudrate, timeout=2.0)
        time.sleep(2)  # Wait for device to be ready
        print("Connected!")

        # Try to read any initial output
        print("\nReading initial output...")
        initial_output = ser.read_all()
        if initial_output:
            print(f"Initial output: {initial_output.decode('utf-8', errors='ignore')}")
        else:
            print("No initial output")

        # Send a simple ping (newline to trigger response)
        print("\nSending test command...")
        ser.write(b'\n')
        time.sleep(0.5)

        response = ser.read_all()
        if response:
            print(f"Response: {response.decode('utf-8', errors='ignore')}")
        else:
            print("No response to test command")

        # Try sending "ping" command
        print("\nSending 'ping'...")
        ser.write(b'ping\n')
        time.sleep(0.5)

        response = ser.read_all()
        if response:
            print(f"Response: {response.decode('utf-8', errors='ignore')}")
        else:
            print("No response to ping")

        ser.close()
        print("\nTest complete!")
        return True

    except serial.SerialException as e:
        print(f"Serial error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
    success = test_pico_serial(port)
    sys.exit(0 if success else 1)
