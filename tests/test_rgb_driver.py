#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
test_rgb_driver.py — RGB LED Driver Test Suite (raw-byte protocol)
===================================================================

Tests the rgb-led driver running on Ferqon Pico via framed UART bytes.
"""

import argparse
import sys
import time
import unittest
from pathlib import Path

# Ensure the SDK root is on sys.path so serial_protocol can be imported
# regardless of the working directory the test is run from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))

from device_config import get_default_baudrate

try:
    import serial
except ImportError:
    print("ERROR: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)

# Use shared device discovery instead of duplicated find_pico_device
from device_discovery import find_board

from serial_protocol import (
    PKT_DONE,
    PKT_ERROR,
    PKT_REQUEST,
    FrameDecoder,
    decode_cmd_payload,
    encode_cmd_payload,
    encode_driver_call,
    encode_frame,
    load_command_ids,
)


class RGBDriverTest(unittest.TestCase):
    """Test the rgb-led driver."""

    ser = None
    pico_port = None

    def _send_driver_info(self) -> dict:
        if not self.ser or not self.ser.is_open:
            self.skipTest("No Pico device connected")
        ids = load_command_ids()
        cmd_id = ids["driver_info"]
        payload = encode_cmd_payload(cmd_id, b"", packet_type=PKT_REQUEST)
        self.ser.write(encode_frame(seq=1, cmd_id=cmd_id, payload=payload))
        self.ser.flush()
        return self._read_response()

    def _read_response(self, timeout: float = 3.0) -> dict:
        decoder = FrameDecoder()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                chunk = self.ser.read(128)
            except serial.SerialException as exc:
                return {"ok": False, "error": f"serial error: {exc}"}
            if not chunk:
                continue
            for seq, recv_cmd_id, pkt_type, frame_payload in decoder.feed(chunk):
                if pkt_type not in (PKT_DONE, PKT_ERROR):
                    continue
                resp = decode_cmd_payload(frame_payload)
                if resp.ok:
                    return {"ok": True, "ack": resp.ack, "result": resp.message, "cmd_id": recv_cmd_id}
                return {"ok": False, "ack": resp.ack, "error": resp.message, "cmd_id": recv_cmd_id}
        return {"ok": False, "error": "timeout"}

    @staticmethod
    def _parse_driver_info(result_str: str) -> dict:
        out = {"count": 0, "drivers": []}
        if not result_str:
            return out
        for seg in result_str.split(";"):
            seg = seg.strip()
            if seg.startswith("count="):
                try:
                    out["count"] = int(seg.split("=", 1)[1])
                except ValueError:
                    out["count"] = 0
            if seg.startswith("drivers="):
                out["drivers"] = [n.strip() for n in seg.split("=", 1)[1].split(",") if n.strip()]
        if out["count"] == 0 and out["drivers"]:
            out["count"] = len(out["drivers"])
        return out

    def _check_rgb_driver_available(self):
        """Check if rgb-led driver is available on the firmware."""
        try:
            resp = self._send_driver_info()
            if not resp.get("ok"):
                return False
            info = self._parse_driver_info(str(resp.get("result", "")))
            drivers = info.get("drivers", [])
            return "rgb-led" in drivers
        except Exception:
            return False

    def send_driver_call(self, method: str, r: int, g: int, b: int) -> dict:
        """Send a driver.call command for rgb-led."""
        if not self.ser or not self.ser.is_open:
            self.skipTest("No Pico device connected")

        ids = load_command_ids()
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))

        body = encode_driver_call(
            driver_name="rgb-led",
            method=method,
            args={"r": r, "g": g, "b": b},
        )
        cmd_id = ids["driver_call"]
        req_payload = encode_cmd_payload(cmd_id, body, packet_type=PKT_REQUEST)
        self.ser.write(encode_frame(seq=1, cmd_id=cmd_id, payload=req_payload))
        self.ser.flush()
        return self._read_response()

    def test_driver_exists(self):
        if not self._check_rgb_driver_available():
            self.skipTest("rgb-led driver not available on firmware")
        resp = self._send_driver_info()
        self.assertTrue(resp.get("ok"), f"driver.info failed: {resp.get('error')}")
        info = self._parse_driver_info(str(resp.get("result", "")))
        drivers = info.get("drivers", [])
        self.assertIn("rgb-led", drivers, "rgb-led driver not found")

    def test_set_red(self):
        if not self._check_rgb_driver_available():
            self.skipTest("rgb-led driver not available on firmware")
        self.assertTrue(self.send_driver_call("set", 255, 0, 0).get("ok"))

    def test_set_green(self):
        if not self._check_rgb_driver_available():
            self.skipTest("rgb-led driver not available on firmware")
        self.assertTrue(self.send_driver_call("set", 0, 255, 0).get("ok"))

    def test_set_blue(self):
        if not self._check_rgb_driver_available():
            self.skipTest("rgb-led driver not available on firmware")
        self.assertTrue(self.send_driver_call("set", 0, 0, 255).get("ok"))

    def test_set_white(self):
        if not self._check_rgb_driver_available():
            self.skipTest("rgb-led driver not available on firmware")
        self.assertTrue(self.send_driver_call("set", 255, 255, 255).get("ok"))

    def test_set_black(self):
        if not self._check_rgb_driver_available():
            self.skipTest("rgb-led driver not available on firmware")
        self.assertTrue(self.send_driver_call("set", 0, 0, 0).get("ok"))

    def test_set_half_brightness(self):
        if not self._check_rgb_driver_available():
            self.skipTest("rgb-led driver not available on firmware")
        self.assertTrue(self.send_driver_call("set", 128, 128, 128).get("ok"))

    def test_values_are_clamped(self):
        if not self._check_rgb_driver_available():
            self.skipTest("rgb-led driver not available on firmware")
        self.assertTrue(self.send_driver_call("set", 256, 300, 1000).get("ok"))

    def test_invalid_method_fails(self):
        if not self._check_rgb_driver_available():
            self.skipTest("rgb-led driver not available on firmware")
        resp = self.send_driver_call("invalid_method", 255, 0, 0)
        self.assertFalse(resp.get("ok"), "Invalid method should fail")


def _send_rgb(ser, r: int, g: int, b: int, method: str = "set") -> dict:
    ids = load_command_ids()
    body = encode_driver_call("rgb-led", method, {"r": r, "g": g, "b": b})
    payload = encode_cmd_payload(ids["driver_call"], body)
    ser.write(encode_frame(payload))
    ser.flush()

    decoder = FrameDecoder()
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        try:
            chunk = ser.read(128)
        except serial.SerialException as exc:
            return {"ok": False, "error": f"serial error: {exc}"}
        if not chunk:
            continue
        for _ver, msg_type, _flags, frame_payload in decoder.feed(chunk):
            if msg_type != TYPE_RESPONSE:
                continue
            resp = decode_cmd_payload(frame_payload)
            if resp.ok:
                return {"ok": True, "result": resp.message}
            return {"ok": False, "error": resp.message}
    return {"ok": False, "error": "timeout"}


def pattern_rainbow(ser, speed: float = 0.5):
    print("\nRAINBOW PATTERN")
    for hue in range(0, 360, 3):
        r = int(255 * max(0, min(1, 1.5 - abs(hue - 0) / 120)))
        g = int(255 * max(0, min(1, 1.5 - abs(hue - 120) / 120)))
        b = int(255 * max(0, min(1, 1.5 - abs(hue - 240) / 120)))
        resp = _send_rgb(ser, r, g, b)
        if resp.get("ok"):
            print(f"  Hue {hue:3d} deg -> RGB({r:3d}, {g:3d}, {b:3d})", end="\r")
        time.sleep(speed / 120)
    print()


def pattern_pulse(ser, speed: float = 1.0):
    print("\nPULSE PATTERN")
    colors = [
        ("Red", 255, 0, 0),
        ("Green", 0, 255, 0),
        ("Blue", 0, 0, 255),
        ("Yellow", 255, 255, 0),
        ("Magenta", 255, 0, 255),
        ("Cyan", 0, 255, 255),
    ]

    for color_name, r, g, b in colors:
        print(f"  Pulsing {color_name}...", end=" ")
        for brightness in list(range(0, 256, 10)) + list(range(255, -1, -10)):
            br = int(r * brightness / 255)
            bg = int(g * brightness / 255)
            bb = int(b * brightness / 255)
            _send_rgb(ser, br, bg, bb)
            time.sleep(speed / 52)
        print("OK")


def run_patterns(ser):
    print("\n" + "=" * 60)
    print("Ferqon RGB-LED DRIVER — RAW-BYTE INTERACTIVE TEST")
    print("=" * 60)

    try:
        print("\nTesting basic colors...")
        colors = [
            (255, 0, 0, "Red"),
            (0, 255, 0, "Green"),
            (0, 0, 255, "Blue"),
            (255, 255, 0, "Yellow"),
            (255, 0, 255, "Magenta"),
            (0, 255, 255, "Cyan"),
            (255, 255, 255, "White"),
            (0, 0, 0, "Off"),
        ]

        for r, g, b, name in colors:
            resp = _send_rgb(ser, r, g, b)
            status = "OK" if resp.get("ok") else "FAIL"
            print(f"  {status:4s} {name:10s} ({r:3d}, {g:3d}, {b:3d})")
            time.sleep(0.5)

        pattern_pulse(ser, speed=0.5)
        pattern_rainbow(ser, speed=0.3)
        _send_rgb(ser, 0, 0, 0)
        print("\nLED off. Test complete!")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        _send_rgb(ser, 0, 0, 0)


def main():
    parser = argparse.ArgumentParser(description="Test RGB-LED driver on Ferqon Pico")
    parser.add_argument("--device", "-d", help="Serial port (e.g., /dev/ttyACM0)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose test output")
    parser.add_argument("--test-pattern", action="store_true", help="Run color patterns instead of unit tests")
    parser.add_argument("--timeout", type=float, default=5.0, help="Serial timeout in seconds")
    args = parser.parse_args()

    device_port = args.device or find_board("pico")
    if not device_port:
        print("ERROR: No Pico device found")
        return 1

    try:
        ser = serial.Serial(device_port, get_default_baudrate(), timeout=args.timeout)
        time.sleep(0.2)
        print(f"Connected to {device_port}")
    except serial.SerialException as e:
        print(f"ERROR: Failed to open {device_port}: {e}")
        return 1

    if args.test_pattern:
        run_patterns(ser)
        ser.close()
        return 0

    RGBDriverTest.ser = ser
    RGBDriverTest.pico_port = device_port

    try:
        suite = unittest.TestLoader().loadTestsFromTestCase(RGBDriverTest)
        result = unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(suite)
        return 0 if result.wasSuccessful() else 1
    finally:
        if ser and ser.is_open:
            try:
                _send_rgb(ser, 0, 0, 0)
            except Exception:
                pass
            ser.close()
            print(f"\nClosed {device_port}")


if __name__ == "__main__":
    sys.exit(main())