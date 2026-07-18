#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""Independent Ferqon firmware self-test program.

Runs a command matrix against a device (real serial or emulator)
and reports PASS/FAIL with a JSON summary. No backend required.

Usage:
    python ferqon_selftest.py --port /dev/ttyACM0
    python ferqon_selftest.py --emulator
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# Add tools to path for local imports.
tools_dir = Path(__file__).resolve().parent.parent.parent / "tools"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

try:
    import serial
except ImportError as exc:  # pragma: no cover - only hits runtime
    raise ImportError("pyserial is required: pip install pyserial") from exc

from ferqonfw.protocol import (
    encode_frame as _encode_frame,
    FrameDecoder,
    PKT_REQUEST,
    PKT_DONE,
    PKT_ACK,
    PKT_ERROR,
    START_BYTE,
)
from device_config import get_default_baudrate

# Module-level constants (no hardcoded string fallbacks)
_DEFAULT_EMPTY_STRING = ""
_DEFAULT_ZERO = 0


# Load SSOT
def _load_commands_json() -> dict[str, Any]:
    """Load commands.json SSOT. Use FERQON_COMMANDS_JSON to override."""
    commands_json_env = os.getenv("FERQON_COMMANDS_JSON")
    candidates = [Path(commands_json_env)] if commands_json_env else []
    candidates.append(
        Path(__file__).parent.parent.parent / "protocol" / "ssot" / "commands.json"
    )
    for p in candidates:
        if p.exists():
            with open(p, encoding="utf-8") as f:
                spec = json.load(f)
            required_keys = ("commands", "tlv_types", "ferqon_signature")
            missing = [k for k in required_keys if k not in spec]
            if missing:
                raise ValueError(
                    f"commands.json at {p} missing required keys: {missing}"
                )
            return spec
    # Fallback to minimal defaults
    return {
        "tlv_types": {
            "DEVICE_NAME": 1,
            "MCU_TYPE": 2,
            "FIRMWARE_VERSION": 3,
            "PROTOCOL_VERSION": 4,
            "FERQON_SIGNATURE": 16,
            "DRIVER": 1,
        },
        "ferqon_signature": {"magic": "FERQON"},
        "commands": {
            "ping": {"id": 9},
            "echo": {"id": 8},
            "driver_info": {"id": 2},
            "device_info": {"id": 11},
            "capabilities": {"id": 12},
            "gpio_read": {"id": 16},
            "gpio_write": {"id": 17},
        },
    }


_SPEC = _load_commands_json()

# Command IDs from SSOT
_commands = _SPEC.get("commands", {})
CMD_PING = _commands.get("ping", {}).get("id", 9)
CMD_ECHO = _commands.get("echo", {}).get("id", 8)
CMD_DRIVER_INFO = _commands.get("driver_info", {}).get("id", 2)
CMD_DEVICE_INFO = _commands.get("device_info", {}).get("id", 11)
CMD_CAPABILITIES = _commands.get("capabilities", {}).get("id", 12)
CMD_GPIO_READ = _commands.get("gpio_read", {}).get("id", 16)
CMD_GPIO_WRITE = _commands.get("gpio_write", {}).get("id", 17)

# TLV types from SSOT
_tlv_types = _SPEC.get("tlv_types", {})
TLV_DEVICE_NAME = _tlv_types.get("DEVICE_NAME", 0x01)
TLV_MCU_TYPE = _tlv_types.get("MCU_TYPE", 0x02)
TLV_FIRMWARE_VERSION = _tlv_types.get("FIRMWARE_VERSION", 0x03)
TLV_PROTOCOL_VERSION = _tlv_types.get("PROTOCOL_VERSION", 0x04)
TLV_FERQON_SIGNATURE = _tlv_types.get("FERQON_SIGNATURE", 0x10)
TLV_DRIVER = _tlv_types.get("DRIVER", 0x01)

# Signature configuration from SSOT
_signature_config = _SPEC.get("ferqon_signature", {})
FERQON_SIGNATURE_MAGIC = _signature_config.get("magic", "FERQON").encode("utf-8")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


class TestStatus(str, Enum):
    """Test result status."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class TestResult:
    """Result of a single test."""

    name: str
    status: TestStatus
    duration_ms: float
    error: str = _DEFAULT_EMPTY_STRING
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "details": self.details,
        }


@dataclass
class TestSummary:
    """Summary of all tests."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: float = 0.0
    results: list[TestResult] = field(default_factory=list)

    def add_result(self, result: TestResult) -> None:
        self.results.append(result)
        self.total += 1
        if result.status == TestStatus.PASS:
            self.passed += 1
        elif result.status == TestStatus.FAIL:
            self.failed += 1
        else:
            self.skipped += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "duration_ms": self.duration_ms,
            "results": [r.to_dict() for r in self.results],
        }


class Transport:
    """Transport interface for serial vs emulator."""

    def send_frame(self, frame: bytes, timeout_s: float = 2.0) -> dict[str, Any]:
        """Send a frame and return parsed response."""
        raise NotImplementedError

    def close(self) -> None:
        """Close the transport."""
        raise NotImplementedError


_RESPONSE_PACKET_TYPES = {PKT_DONE, PKT_ACK, PKT_ERROR}


class SerialTransport(Transport):
    """Real serial port transport."""

    def __init__(self, port: str, baudrate: int | None = None):
        self.port = port
        self.baudrate = baudrate if baudrate is not None else get_default_baudrate()
        self._conn = None

    def connect(self) -> None:
        self._conn = serial.Serial(self.port, self.baudrate, timeout=2.0)
        time.sleep(0.5)  # Wait for device to be ready

    def send_frame(self, frame: bytes, timeout_s: float = 2.0) -> dict[str, Any]:
        if self._conn is None:
            raise RuntimeError("Transport not connected")
        self._conn.write(frame)
        self._conn.flush()

        decoder = FrameDecoder()
        deadline = time.time() + timeout_s
        self._conn.timeout = timeout_s
        while time.time() < deadline:
            chunk = self._conn.read(1)
            if not chunk:
                continue
            for _, _, pkt_type, payload in decoder.feed(chunk):
                if pkt_type not in _RESPONSE_PACKET_TYPES:
                    continue
                body = payload[1:] if payload else b""
                if pkt_type == PKT_ERROR:
                    return {
                        "ok": False,
                        "error": "error response",
                        "pkt_type": pkt_type,
                        "body": body,
                    }
                return {"ok": True, "pkt_type": pkt_type, "body": body}

        return {"ok": False, "error": "timeout"}

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None


class EmulatorTransport(Transport):
    """In-process emulator transport."""

    def __init__(self, emulator):
        self.emulator = emulator

    def send_frame(self, frame: bytes, timeout_s: float = 2.0) -> dict[str, Any]:
        response = self.emulator.send_frame(frame)
        if not response:
            return {"ok": False, "error": "no response"}
        if response[0] != START_BYTE:
            return {"ok": False, "error": "invalid start byte"}

        decoder = FrameDecoder()
        frames = decoder.feed(response)
        if not frames:
            return {"ok": False, "error": "could not decode response"}

        _, _, pkt_type, payload = frames[0]
        body = payload[1:] if payload else b""
        if pkt_type == PKT_ERROR:
            return {
                "ok": False,
                "error": "error response",
                "pkt_type": pkt_type,
                "body": body,
            }
        return {"ok": True, "pkt_type": pkt_type, "body": body}

    def close(self) -> None:
        pass


def parse_tlv(data: bytes) -> dict[int, bytes]:
    """Parse TLV-encoded data."""
    result = {}
    i = 0
    while i + 2 <= len(data):
        tlv_type = data[i]
        length = data[i + 1]
        if i + 2 + length > len(data):
            break
        value = data[i + 2 : i + 2 + length]
        result[tlv_type] = value
        i += 2 + length
    return result


def parse_string_tlv(tlvs: dict[int, bytes], tlv_type: int) -> str:
    """Extract a string from a TLV."""
    value = tlvs.get(tlv_type, b"")
    try:
        return value.decode("utf-8", errors="replace").rstrip("\x00")
    except Exception:
        return ""


def run_test_ping(transport: Transport) -> TestResult:
    """Test PING command."""
    start = time.time()
    try:
        frame = _encode_frame(seq=1, cmd_id=CMD_PING, payload=b"")
        resp = transport.send_frame(frame, timeout_s=2.0)

        if resp.get("ok"):
            return TestResult(
                name="ping",
                status=TestStatus.PASS,
                duration_ms=(time.time() - start) * 1000,
                details={"pkt_type": resp.get("pkt_type")},
            )
        else:
            return TestResult(
                name="ping",
                status=TestStatus.FAIL,
                duration_ms=(time.time() - start) * 1000,
                error=resp.get("error", "unknown error"),
            )
    except Exception as exc:
        return TestResult(
            name="ping",
            status=TestStatus.FAIL,
            duration_ms=(time.time() - start) * 1000,
            error=str(exc),
        )


def run_test_echo(transport: Transport) -> TestResult:
    """Test ECHO command."""
    start = time.time()
    try:
        payload = bytes([PKT_REQUEST]) + b"hello"
        frame = _encode_frame(seq=2, cmd_id=CMD_ECHO, payload=payload)
        resp = transport.send_frame(frame, timeout_s=2.0)

        if resp.get("ok"):
            body = resp.get("body", b"")
            if body == b"hello":
                return TestResult(
                    name="echo",
                    status=TestStatus.PASS,
                    duration_ms=(time.time() - start) * 1000,
                    details={"echoed": body.decode("utf-8", errors="replace")},
                )
            else:
                return TestResult(
                    name="echo",
                    status=TestStatus.FAIL,
                    duration_ms=(time.time() - start) * 1000,
                    error=f"echo mismatch: expected 'hello', got '{body}'",
                )
        else:
            return TestResult(
                name="echo",
                status=TestStatus.FAIL,
                duration_ms=(time.time() - start) * 1000,
                error=resp.get("error", "unknown error"),
            )
    except Exception as exc:
        return TestResult(
            name="echo",
            status=TestStatus.FAIL,
            duration_ms=(time.time() - start) * 1000,
            error=str(exc),
        )


def run_test_device_info(transport: Transport) -> TestResult:
    """Test DEVICE_INFO command and check for Ferqon signature."""
    start = time.time()
    try:
        frame = _encode_frame(seq=3, cmd_id=CMD_DEVICE_INFO, payload=b"")
        resp = transport.send_frame(frame, timeout_s=2.0)

        if not resp.get("ok"):
            return TestResult(
                name="device_info",
                status=TestStatus.FAIL,
                duration_ms=(time.time() - start) * 1000,
                error=resp.get("error", "unknown error"),
            )

        body = resp.get("body", b"")
        tlvs = parse_tlv(body)

        device_name = parse_string_tlv(tlvs, TLV_DEVICE_NAME)
        mcu_type = parse_string_tlv(tlvs, TLV_MCU_TYPE)
        fw_version = parse_string_tlv(tlvs, TLV_FIRMWARE_VERSION)
        proto_version = parse_string_tlv(tlvs, TLV_PROTOCOL_VERSION)

        # Check for signature
        signature = tlvs.get(TLV_FERQON_SIGNATURE, b"")
        has_signature = signature.startswith(FERQON_SIGNATURE_MAGIC)

        details = {
            "device_name": device_name,
            "mcu_type": mcu_type,
            "firmware_version": fw_version,
            "protocol_version": proto_version,
            "has_signature": has_signature,
        }

        if device_name and mcu_type and fw_version and proto_version:
            return TestResult(
                name="device_info",
                status=TestStatus.PASS,
                duration_ms=(time.time() - start) * 1000,
                details=details,
            )
        else:
            return TestResult(
                name="device_info",
                status=TestStatus.FAIL,
                duration_ms=(time.time() - start) * 1000,
                error="Missing required TLVs",
                details=details,
            )
    except Exception as exc:
        return TestResult(
            name="device_info",
            status=TestStatus.FAIL,
            duration_ms=(time.time() - start) * 1000,
            error=str(exc),
        )


def run_test_driver_info(transport: Transport) -> TestResult:
    """Test DRIVER_INFO command."""
    start = time.time()
    try:
        frame = _encode_frame(seq=4, cmd_id=CMD_DRIVER_INFO, payload=b"")
        resp = transport.send_frame(frame, timeout_s=2.0)

        if resp.get("ok"):
            body = resp.get("body", b"")
            tlvs = parse_tlv(body)
            # Check for at least one driver
            has_driver = TLV_DRIVER in tlvs
            return TestResult(
                name="driver_info",
                status=TestStatus.PASS if has_driver else TestStatus.FAIL,
                duration_ms=(time.time() - start) * 1000,
                details={"has_driver": has_driver, "body_len": len(body)},
            )
        else:
            return TestResult(
                name="driver_info",
                status=TestStatus.FAIL,
                duration_ms=(time.time() - start) * 1000,
                error=resp.get("error", "unknown error"),
            )
    except Exception as exc:
        return TestResult(
            name="driver_info",
            status=TestStatus.FAIL,
            duration_ms=(time.time() - start) * 1000,
            error=str(exc),
        )


def run_test_gpio_roundtrip(transport: Transport) -> TestResult:
    """Test GPIO write then read."""
    start = time.time()
    try:
        # Write GPIO 7 = 1
        write_payload = bytes([PKT_REQUEST, 7, 1])
        write_frame = _encode_frame(seq=5, cmd_id=CMD_GPIO_WRITE, payload=write_payload)
        write_resp = transport.send_frame(write_frame, timeout_s=2.0)

        if not write_resp.get("ok"):
            return TestResult(
                name="gpio_roundtrip",
                status=TestStatus.FAIL,
                duration_ms=(time.time() - start) * 1000,
                error=f"GPIO write failed: {write_resp.get('error', 'unknown')}",
            )

        # Read GPIO 7
        read_payload = bytes([PKT_REQUEST, 7])
        read_frame = _encode_frame(seq=6, cmd_id=CMD_GPIO_READ, payload=read_payload)
        read_resp = transport.send_frame(read_frame, timeout_s=2.0)

        if not read_resp.get("ok"):
            return TestResult(
                name="gpio_roundtrip",
                status=TestStatus.FAIL,
                duration_ms=(time.time() - start) * 1000,
                error=f"GPIO read failed: {read_resp.get('error', 'unknown')}",
            )

        body = read_resp.get("body", b"")
        value = body[0] if body else -1

        if value == 1:
            return TestResult(
                name="gpio_roundtrip",
                status=TestStatus.PASS,
                duration_ms=(time.time() - start) * 1000,
                details={"pin": 7, "value": value},
            )
        else:
            return TestResult(
                name="gpio_roundtrip",
                status=TestStatus.FAIL,
                duration_ms=(time.time() - start) * 1000,
                error=f"GPIO read value mismatch: expected 1, got {value}",
                details={"pin": 7, "value": value},
            )
    except Exception as exc:
        return TestResult(
            name="gpio_roundtrip",
            status=TestStatus.FAIL,
            duration_ms=(time.time() - start) * 1000,
            error=str(exc),
        )


def run_tests(transport: Transport) -> TestSummary:
    """Run all tests and return summary."""
    summary = TestSummary()
    start = time.time()

    tests = [
        run_test_ping,
        run_test_echo,
        run_test_device_info,
        run_test_driver_info,
        run_test_gpio_roundtrip,
    ]

    for test in tests:
        result = test(transport)
        summary.add_result(result)
        print(
            f"{result.status.value:4} | {result.name:20} | {result.duration_ms:6.1f}ms"
        )
        if result.error:
            print(f"      Error: {result.error}")

    summary.duration_ms = (time.time() - start) * 1000
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Ferqon firmware self-test")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--port", help="Serial port (e.g., /dev/ttyACM0)")
    group.add_argument(
        "--emulator", action="store_true", help="Use in-process emulator"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON summary")
    args = parser.parse_args()

    transport: Transport
    emulator = None

    if args.emulator:
        # Import emulator
        from ferqon_emulator import FerqonEmulator

        emulator = FerqonEmulator()
        transport = EmulatorTransport(emulator)
        print("Using in-process emulator")
    else:
        transport = SerialTransport(args.port)
        print(f"Using serial port: {args.port}")

    try:
        if args.port:
            transport.connect()

        print("\nRunning self-test matrix...")
        print("-" * 60)
        print(f"{'STATUS':6} | {'TEST':20} | {'TIME':8}")
        print("-" * 60)

        summary = run_tests(transport)

        print("-" * 60)
        print(
            f"Total: {summary.total} | Passed: {summary.passed} | Failed: {summary.failed} | Skipped: {summary.skipped}"
        )
        print(f"Duration: {summary.duration_ms:.1f}ms")

        if args.json:
            print("\n" + json.dumps(summary.to_dict(), indent=2))

        return 0 if summary.failed == 0 else 1

    except Exception as exc:
        print(f"Error: {exc}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        transport.close()


if __name__ == "__main__":
    sys.exit(main())
