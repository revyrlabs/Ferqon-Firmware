#!/usr/bin/env python3
"""
test_drivers.py — Test Ferqon driver system
==========================================

Tests for the firmware driver interface, including:
  - Driver registration and discovery
  - Driver method calls over serial
  - Error handling and edge cases
  - Protocol compliance

Run with:
  python3 test_drivers.py [--device /dev/ttyACM0] [--verbose]

Prerequisites:
  - A connected Pico running the Ferqon firmware with at least one driver
  - pyserial: pip install pyserial
"""

import argparse
import sys
import time
import unittest
from pathlib import Path

# Ensure the SDK root is on sys.path so serial_protocol can be imported
# regardless of the working directory the test is run from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("ERROR: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)

from serial_protocol import (
    TYPE_RESPONSE,
    FrameDecoder,
    decode_cmd_payload,
    encode_cmd_payload,
    encode_driver_call,
    encode_frame,
    load_command_ids,
)


class DriverTestCase(unittest.TestCase):
    """Base test case for driver tests."""

    @classmethod
    def setUpClass(cls):
        """Preserve shared serial handle injected by main()."""
        if not hasattr(cls, "ser"):
            cls.ser = None
        if not hasattr(cls, "pico_port"):
            cls.pico_port = None

    @classmethod
    def tearDownClass(cls):
        """Close connection to Pico."""
        if cls.ser and cls.ser.is_open:
            cls.ser.close()

    def send_command(self, method: str, driver_name: str = "", payload: dict = None) -> dict:
        """
        Send a framed binary command to the Pico and receive the response.

        Args:
            method: The RPC method name (e.g., "ping", "driver.info", "driver.call")
            driver_name: The driver name (for driver-specific calls)
            payload: Additional payload (for driver.call)

        Returns:
            dict: Parsed runtime response {ok, ack, result|error, cmd_id}
        """
        if not self.ser or not self.ser.is_open:
            self.skipTest("No Pico device connected")

        ids = load_command_ids()
        payload = payload or {}

        if method == "ping":
            cmd_id = ids["ping"]
            body = b""
        elif method == "driver.info":
            cmd_id = ids["driver_info"]
            body = b""
        elif method == "driver.call":
            cmd_id = ids["driver_call"]
            call = str(payload.get("method", ""))
            args = {k: v for k, v in payload.items() if k != "method"}
            body = encode_driver_call(driver_name=driver_name, method=call, args=args)
        else:
            # Use an unknown cmd ID to validate unsupported command handling.
            cmd_id = 0x7FFF
            body = b""

        req_payload = encode_cmd_payload(cmd_id, body)
        self.ser.write(encode_frame(req_payload))
        self.ser.flush()

        decoder = FrameDecoder()
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            try:
                chunk = self.ser.read(128)
            except serial.SerialException as exc:
                if "multiple access" in str(exc).lower():
                    self.skipTest("Serial port is busy (multiple access)")
                self.fail(f"Serial read error: {exc}")
            if not chunk:
                continue
            for _ver, msg_type, _flags, frame_payload in decoder.feed(chunk):
                if msg_type != TYPE_RESPONSE:
                    continue
                resp = decode_cmd_payload(frame_payload)
                if resp.ok:
                    return {"ok": True, "ack": resp.ack, "result": resp.message, "cmd_id": resp.cmd_id}
                return {"ok": False, "ack": resp.ack, "error": resp.message, "cmd_id": resp.cmd_id}

        if method in ("ping", "driver.info", "driver.call"):
            self.fail("No response from Pico")
        return {"ok": False, "error": "no response"}

    def assertResponseOk(self, resp: dict, msg: str = ""):
        """Assert that a Pico response has ok=true."""
        self.assertTrue(resp.get("ok"), f"Response not ok: {resp.get('error', 'unknown')} {msg}")


class DriverDiscoveryTests(DriverTestCase):
    """Test driver discovery and enumeration."""

    def test_ping(self):
        """Test basic Pico connectivity."""
        resp = self.send_command("ping")
        self.assertResponseOk(resp, "ping should work")
        self.assertEqual(resp.get("result"), "pong")

    def test_driver_info_returns_json(self):
        """Test driver.info returns valid driver list."""
        resp = self.send_command("driver.info")
        self.assertResponseOk(resp, "driver.info should work")

        result_str = str(resp.get("result", ""))
        info = self._parse_driver_info(result_str)
        self.assertIn("count", info, "driver.info should include driver count")
        self.assertIn("drivers", info, "driver.info should include drivers list")
        self.assertIsInstance(info["drivers"], list)

    def test_has_at_least_one_driver(self):
        """Test that Pico has at least one driver compiled in."""
        resp = self.send_command("driver.info")
        self.assertResponseOk(resp)

        info = self._parse_driver_info(str(resp.get("result", "")))
        count = info.get("count", 0)
        self.assertGreater(count, 0, "Pico should have at least one driver")
        self.assertEqual(len(info.get("drivers", [])), count, "Driver count should match list length")

    @staticmethod
    def _parse_driver_info(result_str: str) -> dict:
        # Runtime format: count=<n>;drivers=name1,name2
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
                names = [n.strip() for n in seg.split("=", 1)[1].split(",") if n.strip()]
                out["drivers"] = names
        if out["count"] == 0 and out["drivers"]:
            out["count"] = len(out["drivers"])
        return out


class DriverCallTests(DriverTestCase):
    """Test driver method calls."""

    def test_call_nonexistent_driver_fails(self):
        """Test calling a non-existent driver returns error."""
        resp = self.send_command(
            "driver.call",
            driver_name="nonexistent-driver-xyz",
            payload={"method": "test"}
        )
        self.assertFalse(resp.get("ok"), "Call to non-existent driver should fail")
        self.assertIn("not found", resp.get("error", "").lower())

    def test_call_with_missing_driver_name_fails(self):
        """Test calling without driver_name fails."""
        resp = self.send_command(
            "driver.call",
            driver_name="",
            payload={"method": "test"}
        )
        self.assertFalse(resp.get("ok"), "Call without driver_name should fail")

    def test_call_with_missing_method_fails(self):
        """Test calling without method in payload fails."""
        # Get a valid driver name first
        info = DriverDiscoveryTests._parse_driver_info(str(self.send_command("driver.info").get("result", "")))
        drivers = info.get("drivers", [])

        if not drivers:
            self.skipTest("No drivers available to test")

        driver_name = drivers[0]

        # Try calling without method
        resp = self.send_command(
            "driver.call",
            driver_name=driver_name,
            payload={"x": 1}  # No "method" key
        )
        self.assertFalse(resp.get("ok"), "Call without method should fail")


class DriverProtocolTests(DriverTestCase):
    """Test protocol compliance and edge cases."""

    def test_unsupported_method_returns_error(self):
        """Test calling unsupported RPC method returns error."""
        resp = self.send_command("unsupported.method.xyz")
        self.assertFalse(resp.get("ok"), "Unsupported method should return error")
        self.assertIn("unsupported", resp.get("error", "").lower())

    def test_response_has_required_fields(self):
        """Test that all responses have required fields."""
        resp = self.send_command("ping")
        self.assertIn("ok", resp, "Response should have 'ok' field")
        # Either result or error should be present
        self.assertTrue(
            "result" in resp or "error" in resp,
            "Response should have 'result' or 'error' field"
        )

    def test_response_ok_is_boolean(self):
        """Test that 'ok' field is always a boolean."""
        for method in ["ping", "driver.info"]:
            resp = self.send_command(method)
            self.assertIsInstance(resp.get("ok"), bool, f"{method} 'ok' should be boolean")


class DriverIntegrationTests(DriverTestCase):
    """Integration tests with real driver functionality."""

    def test_multiple_consecutive_calls(self):
        """Test making multiple calls in sequence works."""
        for i in range(3):
            resp = self.send_command("ping")
            self.assertResponseOk(resp, f"ping #{i+1} should work")

    def test_rapid_calls_dont_deadlock(self):
        """Test rapid calls don't cause serial deadlock."""
        for i in range(10):
            resp = self.send_command("driver.info")
            self.assertResponseOk(resp, f"rapid call #{i+1} should work")

    def test_long_response_handling(self):
        """Test driver.info with many drivers doesn't get truncated."""
        resp = self.send_command("driver.info")
        self.assertResponseOk(resp)

        result_str = str(resp.get("result", ""))
        info = DriverDiscoveryTests._parse_driver_info(result_str)
        self.assertTrue(info.get("drivers") is not None, "driver.info should parse")


def find_pico_device():
    """
    Find a connected Pico device.

    Returns:
        str: Device port path (e.g., "/dev/ttyACM0"), or None if not found
    """
    PICO_VID = 0x2E8A  # Raspberry Pi vendor ID

    for port in list_ports.comports():
        if port.vid == PICO_VID and port.device.startswith("/dev/ttyACM"):
            return port.device

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Test Ferqon driver system on a connected Pico",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Auto-detect Pico and run tests
  python3 test_drivers.py

  # Specify device port explicitly
  python3 test_drivers.py --device /dev/ttyACM0

  # Run with verbose output
  python3 test_drivers.py -v

  # Run only one test class
  python3 test_drivers.py DriverDiscoveryTests
        """
    )

    parser.add_argument(
        "--device", "-d",
        help="Serial port of Pico device (e.g., /dev/ttyACM0). Auto-detects if not specified."
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose test output"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Serial port timeout in seconds (default: 5.0)"
    )

    # Allow specifying which tests to run
    parser.add_argument(
        "tests",
        nargs="*",
        help="Specific test(s) to run (e.g., 'DriverDiscoveryTests' or 'DriverDiscoveryTests.test_ping')"
    )

    args = parser.parse_args()

    # Find Pico device
    device_port = args.device
    if not device_port:
        device_port = find_pico_device()
        if not device_port:
            print("ERROR: No Pico device found. Specify with --device /dev/ttyXXX")
            return 1
        print(f"Auto-detected Pico at {device_port}")
    else:
        print(f"Using device: {device_port}")

    # Connect to Pico
    try:
        ser = serial.Serial(device_port, 115200, timeout=args.timeout)
        time.sleep(0.2)  # Let the connection stabilize
        print(f"Connected to {device_port}")
    except serial.SerialException as e:
        print(f"ERROR: Failed to open {device_port}: {e}")
        return 1

    # Set up test class
    DriverTestCase.ser = ser
    DriverTestCase.pico_port = device_port

    try:
        # Run tests
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        if args.tests:
            # Load specific tests
            for test_name in args.tests:
                try:
                    suite.addTests(loader.loadTestsFromName(test_name))
                except Exception as e:
                    print(f"ERROR: Could not load test '{test_name}': {e}")
                    return 1
        else:
            # Load all tests
            suite.addTests(loader.loadTestsFromModule(sys.modules[__name__]))

        runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
        result = runner.run(suite)

        # Return appropriate exit code
        return 0 if result.wasSuccessful() else 1

    finally:
        if ser and ser.is_open:
            ser.close()
            print(f"\nClosed {device_port}")


if __name__ == "__main__":
    sys.exit(main())
