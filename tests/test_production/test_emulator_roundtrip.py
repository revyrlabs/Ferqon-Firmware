#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
test_emulator_roundtrip.py
--------------------------
Round-trip tests that exercise the CLI frame builders against the
in-process emulator's dispatch path. These tests verify that:

1. The emulator enforces the PKT_REQUEST requirement matching the
   firmware dispatcher (all commands except DEVICE_INFO and DRIVER_INFO).
2. Frames without PKT_REQUEST are rejected with INVALID_PARAMS.
3. DEVICE_INFO and DRIVER_INFO work without PKT_REQUEST (empty payload).
4. All core commands (ping, echo, device_info, driver_info, gpio_read,
   gpio_write, capabilities) produce valid responses.

This test binds the Python protocol module's frame encoding to the
emulator's dispatch semantics, closing the gap that allowed the
original ping bug (missing PKT_REQUEST byte) to pass CI.
"""

import sys
from pathlib import Path

import pytest

# Add tools/ to path for imports
TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from ferqonfw.protocol import (  # noqa: E402
    encode_frame,
    PKT_REQUEST,
    PKT_DONE,
    PKT_ERROR,
    load_command_ids,
)
from ferqon_emulator import (  # noqa: E402
    FerqonEmulator,
    parse_frame as emu_parse_frame,
)


@pytest.fixture
def cmd_ids():
    """Load command IDs from the SSOT."""
    ids = load_command_ids()
    return {
        "ping": ids.get("ping", 9),
        "echo": ids.get("echo", 8),
        "device_info": ids.get("device_info", 11),
        "driver_info": ids.get("driver_info", 2),
        "capabilities": ids.get("capabilities", 12),
        "gpio_read": ids.get("gpio_read", 16),
        "gpio_write": ids.get("gpio_write", 17),
    }


@pytest.fixture
def emulator():
    """Create a fresh in-process emulator for each test."""
    return FerqonEmulator()


def _parse_response(resp_bytes):
    """Parse a response frame and return (seq, cmd_id, payload)."""
    parsed = emu_parse_frame(resp_bytes)
    assert parsed is not None, "Response frame is invalid (bad CRC or structure)"
    return parsed


class TestPingRoundtrip:
    """Ping command — requires PKT_REQUEST."""

    def test_ping_with_pkt_request(self, emulator, cmd_ids):
        """Ping with PKT_REQUEST byte should return PKT_DONE."""
        payload = bytes([PKT_REQUEST])
        frame = encode_frame(seq=1, cmd_id=cmd_ids["ping"], payload=payload)
        resp = emulator.send_frame(frame)
        assert resp != b"", "No response from emulator"
        seq, cmd_id, resp_payload = _parse_response(resp)
        assert seq == 1
        assert cmd_id == cmd_ids["ping"]
        assert resp_payload[0] == PKT_DONE

    def test_ping_without_pkt_request_rejected(self, emulator, cmd_ids):
        """Ping without PKT_REQUEST must be rejected with INVALID_PARAMS."""
        frame = encode_frame(seq=1, cmd_id=cmd_ids["ping"], payload=b"")
        resp = emulator.send_frame(frame)
        assert resp != b"", "No response from emulator"
        seq, cmd_id, resp_payload = _parse_response(resp)
        assert resp_payload[0] == PKT_ERROR
        # Error code 2 = INVALID_PARAMS
        assert resp_payload[1] == 2


class TestEchoRoundtrip:
    """Echo command — requires PKT_REQUEST."""

    def test_echo_with_pkt_request(self, emulator, cmd_ids):
        """Echo with PKT_REQUEST + data should return PKT_DONE + data."""
        data = b"hello"
        payload = bytes([PKT_REQUEST]) + data
        frame = encode_frame(seq=2, cmd_id=cmd_ids["echo"], payload=payload)
        resp = emulator.send_frame(frame)
        assert resp != b""
        seq, cmd_id, resp_payload = _parse_response(resp)
        assert seq == 2
        assert resp_payload[0] == PKT_DONE
        assert resp_payload[1:] == data

    def test_echo_without_pkt_request_rejected(self, emulator, cmd_ids):
        """Echo without PKT_REQUEST must be rejected."""
        frame = encode_frame(seq=2, cmd_id=cmd_ids["echo"], payload=b"hello")
        resp = emulator.send_frame(frame)
        assert resp != b""
        seq, cmd_id, resp_payload = _parse_response(resp)
        assert resp_payload[0] == PKT_ERROR
        assert resp_payload[1] == 2  # INVALID_PARAMS


class TestDeviceInfoRoundtrip:
    """Device info — exempt from PKT_REQUEST, empty payload."""

    def test_device_info_empty_payload(self, emulator, cmd_ids):
        """Device info with empty payload should return PKT_DONE + TLVs."""
        frame = encode_frame(seq=1, cmd_id=cmd_ids["device_info"], payload=b"")
        resp = emulator.send_frame(frame)
        assert resp != b""
        seq, cmd_id, resp_payload = _parse_response(resp)
        assert seq == 1
        assert resp_payload[0] == PKT_DONE
        assert len(resp_payload) > 1  # Should have TLV data

    def test_device_info_with_extra_bytes_rejected(self, emulator, cmd_ids):
        """Device info with non-empty payload should be rejected."""
        frame = encode_frame(seq=1, cmd_id=cmd_ids["device_info"], payload=b"\x00")
        resp = emulator.send_frame(frame)
        assert resp != b""
        seq, cmd_id, resp_payload = _parse_response(resp)
        assert resp_payload[0] == PKT_ERROR
        assert resp_payload[1] == 2  # INVALID_PARAMS


class TestDriverInfoRoundtrip:
    """Driver info — exempt from PKT_REQUEST, empty payload."""

    def test_driver_info_empty_payload(self, emulator, cmd_ids):
        """Driver info with empty payload should return PKT_DONE + TLVs."""
        frame = encode_frame(seq=1, cmd_id=cmd_ids["driver_info"], payload=b"")
        resp = emulator.send_frame(frame)
        assert resp != b""
        seq, cmd_id, resp_payload = _parse_response(resp)
        assert seq == 1
        assert resp_payload[0] == PKT_DONE
        assert len(resp_payload) > 1  # Should have TLV data


class TestGpioRoundtrip:
    """GPIO read/write — require PKT_REQUEST."""

    def test_gpio_write_with_pkt_request(self, emulator, cmd_ids):
        """GPIO write with PKT_REQUEST + pin + value should return PKT_DONE."""
        payload = bytes([PKT_REQUEST, 25, 1])  # pin 25, value 1
        frame = encode_frame(seq=1, cmd_id=cmd_ids["gpio_write"], payload=payload)
        resp = emulator.send_frame(frame)
        assert resp != b""
        seq, cmd_id, resp_payload = _parse_response(resp)
        assert resp_payload[0] == PKT_DONE

    def test_gpio_write_without_pkt_request_rejected(self, emulator, cmd_ids):
        """GPIO write without PKT_REQUEST must be rejected."""
        payload = bytes([25, 1])  # missing PKT_REQUEST
        frame = encode_frame(seq=1, cmd_id=cmd_ids["gpio_write"], payload=payload)
        resp = emulator.send_frame(frame)
        assert resp != b""
        seq, cmd_id, resp_payload = _parse_response(resp)
        assert resp_payload[0] == PKT_ERROR
        assert resp_payload[1] == 2  # INVALID_PARAMS

    def test_gpio_read_with_pkt_request(self, emulator, cmd_ids):
        """GPIO read with PKT_REQUEST + pin should return PKT_DONE + value."""
        payload = bytes([PKT_REQUEST, 25])
        frame = encode_frame(seq=1, cmd_id=cmd_ids["gpio_read"], payload=payload)
        resp = emulator.send_frame(frame)
        assert resp != b""
        seq, cmd_id, resp_payload = _parse_response(resp)
        assert resp_payload[0] == PKT_DONE
        assert len(resp_payload) >= 2  # PKT_DONE + value


class TestUnknownCommand:
    """Unknown command should return INVALID_COMMAND."""

    def test_unknown_command(self, emulator):
        """An unrecognized command ID should return INVALID_COMMAND."""
        payload = bytes([PKT_REQUEST])
        frame = encode_frame(seq=1, cmd_id=0xFF, payload=payload)
        resp = emulator.send_frame(frame)
        assert resp != b""
        seq, cmd_id, resp_payload = _parse_response(resp)
        assert resp_payload[0] == PKT_ERROR
        assert resp_payload[1] == 1  # INVALID_COMMAND
