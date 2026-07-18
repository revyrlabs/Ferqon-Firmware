#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
test_frame_roundtrip.py
-----------------------
Tests the host-side frame encoder/decoder (ferqonfw.protocol) to verify
that encoded frames can be decoded back correctly, and that CRC validation
rejects corrupted frames.

These tests exercise the same CRC-16/CCITT-FALSE algorithm and frame
layout that the firmware parser in src/protocol.cpp uses.
"""

import json
import sys
from pathlib import Path

import pytest

# Add tools/ to path so we can import ferqonfw.protocol
TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from ferqonfw.protocol import (  # noqa: E402
    START_BYTE,
    crc16_ccitt_false,
    encode_frame,
    FrameDecoder,
    PKT_REQUEST,
)

# Load info-command IDs (those exempt from PKT_REQUEST prefix) from the SSOT
# so this test fails fast if commands.json drifts rather than silently passing
# with stale hardcoded values.
_SSOT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "protocol"
    / "ssot"
    / "commands.json"
)
try:
    _ssot = json.loads(_SSOT_PATH.read_text(encoding="utf-8"))
    _INFO_COMMAND_IDS = {
        _ssot["commands"]["device_info"]["id"],
        _ssot["commands"]["driver_info"]["id"],
    }
except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
    raise RuntimeError(
        f"Cannot load info-command IDs from SSOT at {_SSOT_PATH}: {exc}. "
        f"Ensure protocol/ssot/commands.json defines device_info and driver_info."
    ) from exc


def encode_cmd_payload(
    cmd_id: int, body: bytes = b"", packet_type: int = PKT_REQUEST
) -> bytes:
    """Encode command payload with packet type header.

    Info commands (device_info, driver_info) do not take a REQUEST prefix.
    The exempt IDs are loaded from protocol/ssot/commands.json at module
    import time to detect SSOT drift.
    """
    if cmd_id in _INFO_COMMAND_IDS:
        return body
    return bytes([packet_type]) + body


class TestCRC:
    """CRC-16/CCITT-FALSE algorithm tests."""

    def test_standard_vector(self):
        """CRC-16/CCITT-FALSE of '123456789' must be 0x29B1."""
        data = b"123456789"
        assert crc16_ccitt_false(data) == 0x29B1

    def test_empty_input(self):
        """Empty input must return the init value 0xFFFF."""
        assert crc16_ccitt_false(b"") == 0xFFFF

    def test_single_zero(self):
        """Single byte 0x00 must produce 0xE1F0."""
        assert crc16_ccitt_false(b"\x00") == 0xE1F0


class TestFrameEncoder:
    """Frame encoding structure tests."""

    def test_frame_starts_with_start_byte(self):
        frame = encode_frame(1, 9, b"\x01")
        assert frame[0] == START_BYTE

    def test_frame_has_correct_header(self):
        """Frame: [START] [SEQ] [CMD] [LEN] [payload] [CRC_LO] [CRC_HI]"""
        frame = encode_frame(0x01, 0x09, b"\x01\x42")
        assert frame[0] == 0xAB  # START
        assert frame[1] == 0x01  # SEQ
        assert frame[2] == 0x09  # CMD
        assert frame[3] == 0x02  # LEN
        assert frame[4] == 0x01  # payload[0]
        assert frame[5] == 0x42  # payload[1]

    def test_frame_crc_is_little_endian(self):
        """CRC must be stored low byte first, then high byte."""
        frame = encode_frame(1, 9, b"\x01")
        crc = crc16_ccitt_false(bytes([frame[1], frame[2], frame[3]]) + b"\x01")
        assert frame[-2] == crc & 0xFF
        assert frame[-1] == (crc >> 8) & 0xFF

    def test_frame_total_length(self):
        """Total = 6 + payload_len (START+SEQ+CMD+LEN+CRC_LO+CRC_HI + payload)."""
        payload = b"\x01\x02\x03"
        frame = encode_frame(1, 9, payload)
        assert len(frame) == 6 + len(payload)

    def test_payload_too_large_raises(self):
        with pytest.raises(ValueError):
            encode_frame(1, 9, b"\x00" * 256)


class TestFrameDecoder:
    """Frame decoder round-trip tests."""

    def test_roundtrip_single_frame(self):
        """Encode a frame, feed it to the decoder, verify it decodes."""
        payload = encode_cmd_payload(9, b"", PKT_REQUEST)
        frame = encode_frame(1, 9, payload)
        decoder = FrameDecoder()
        results = decoder.feed(frame)
        assert len(results) == 1
        seq, cmd_id, pkt_type, decoded_payload = results[0]
        assert seq == 1
        assert cmd_id == 9
        assert pkt_type == PKT_REQUEST
        assert decoded_payload == payload

    def test_roundtrip_multiple_frames(self):
        """Two frames in a single feed should produce two results."""
        p1 = encode_cmd_payload(9, b"", PKT_REQUEST)
        p2 = encode_cmd_payload(8, b"hello", PKT_REQUEST)
        f1 = encode_frame(1, 9, p1)
        f2 = encode_frame(2, 8, p2)
        decoder = FrameDecoder()
        results = decoder.feed(f1 + f2)
        assert len(results) == 2
        assert results[0][0] == 1
        assert results[1][0] == 2

    def test_crc_mismatch_rejected(self):
        """A corrupted frame should not produce a result."""
        payload = encode_cmd_payload(9, b"", PKT_REQUEST)
        frame = encode_frame(1, 9, payload)
        # Corrupt the last payload byte (not the CRC)
        frame = bytearray(frame)
        frame[4] ^= 0xFF
        decoder = FrameDecoder()
        results = decoder.feed(bytes(frame))
        assert len(results) == 0

    def test_partial_frame_buffers(self):
        """A partial frame should buffer until more data arrives."""
        payload = encode_cmd_payload(9, b"", PKT_REQUEST)
        frame = encode_frame(1, 9, payload)
        decoder = FrameDecoder()
        # Feed first half
        results = decoder.feed(frame[:4])
        assert len(results) == 0
        # Feed second half
        results = decoder.feed(frame[4:])
        assert len(results) == 1

    def test_garbage_before_frame_ignored(self):
        """Non-START bytes before a frame should be skipped."""
        payload = encode_cmd_payload(9, b"", PKT_REQUEST)
        frame = encode_frame(1, 9, payload)
        decoder = FrameDecoder()
        results = decoder.feed(b"\x00\xFF\x42" + frame)
        assert len(results) == 1
        assert results[0][0] == 1

    def test_empty_payload_frame(self):
        """A frame with zero-length payload should decode correctly."""
        frame = encode_frame(1, 11, b"")  # device_info, no payload
        decoder = FrameDecoder()
        results = decoder.feed(frame)
        assert len(results) == 1
        seq, cmd_id, pkt_type, payload = results[0]
        assert seq == 1
        assert cmd_id == 11
        assert len(payload) == 0
