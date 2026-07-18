#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
test_protocol.py
----------------
Tests for the self-contained production protocol module (ferqonfw.protocol).

These tests verify CRC, frame encoding/decoding, TLV parsing, and device
identity classification without importing any development-only modules.
"""

import sys
from pathlib import Path

# Add tools to path for imports
tools_dir = Path(__file__).resolve().parent.parent.parent / "tools"
sys.path.insert(0, str(tools_dir))

import pytest
from ferqonfw.protocol import (
    START_BYTE,
    CRC_INIT,
    MAX_PAYLOAD_BYTES,
    TLV_DEVICE_NAME,
    TLV_MCU_TYPE,
    TLV_FIRMWARE_VERSION,
    TLV_PROTOCOL_VERSION,
    TLV_FERQON_SIGNATURE,
    crc16_ccitt_false,
    encode_frame,
    FrameDecoder,
    parse_tlv,
    parse_string_tlv,
    parse_device_info,
)


class TestCRC:
    def test_known_crc_value(self):
        """CRC-16/CCITT-FALSE of '123456789' is 0x29B1."""
        data = b"123456789"
        assert crc16_ccitt_false(data) == 0x29B1

    def test_empty_data(self):
        """CRC of empty data is the init value."""
        assert crc16_ccitt_false(b"") == CRC_INIT

    def test_single_byte(self):
        """CRC of a single byte."""
        assert crc16_ccitt_false(b"\x00") == 0xE1F0


class TestFrameEncoding:
    def test_encode_basic_frame(self):
        """Encode a simple frame and verify structure.

        Note: a ping frame with an empty payload is structurally valid
        at the encoding level, but the firmware dispatcher requires a
        PKT_REQUEST byte (0x01) in the payload for all commands except
        DEVICE_INFO and DRIVER_INFO. See test_emulator_roundtrip.py for
        dispatch-level validation.
        """
        frame = encode_frame(seq=1, cmd_id=9, payload=b"")
        assert frame[0] == START_BYTE
        assert frame[1] == 1  # seq
        assert frame[2] == 9  # cmd_id
        assert frame[3] == 0  # len
        assert len(frame) == 6  # start + seq + cmd + len + crc_lo + crc_hi

    def test_encode_with_payload(self):
        """Encode a frame with payload."""
        payload = b"hello"
        frame = encode_frame(seq=2, cmd_id=8, payload=payload)
        assert frame[0] == START_BYTE
        assert frame[3] == len(payload)
        assert frame[4:9] == payload

    def test_encode_payload_too_large(self):
        """Payload exceeding max should raise ValueError."""
        with pytest.raises(ValueError, match="Payload too large"):
            encode_frame(seq=1, cmd_id=1, payload=b"\x00" * (MAX_PAYLOAD_BYTES + 1))

    def test_crc_correctness(self):
        """Verify CRC in encoded frame matches manual calculation."""
        frame = encode_frame(seq=1, cmd_id=9, payload=b"test")
        crc_data = frame[1:-2]  # seq + cmd + len + payload
        expected_crc = crc16_ccitt_false(crc_data)
        recv_crc = frame[-2] | (frame[-1] << 8)
        assert recv_crc == expected_crc


class TestFrameDecoder:
    def test_decode_valid_frame(self):
        """Decode a valid frame."""
        frame = encode_frame(seq=1, cmd_id=9, payload=b"")
        decoder = FrameDecoder()
        results = decoder.feed(frame)
        assert len(results) == 1
        seq, cmd_id, pkt_type, payload = results[0]
        assert seq == 1
        assert cmd_id == 9

    def test_decode_with_garbage_prefix(self):
        """Decoder should skip garbage bytes before START."""
        frame = encode_frame(seq=1, cmd_id=9, payload=b"")
        decoder = FrameDecoder()
        results = decoder.feed(b"\x00\xFF\xEE" + frame)
        assert len(results) == 1

    def test_decode_partial_frame(self):
        """Decoder should handle partial frames across feed calls."""
        frame = encode_frame(seq=1, cmd_id=9, payload=b"")
        decoder = FrameDecoder()
        results = decoder.feed(frame[:3])
        assert len(results) == 0
        results = decoder.feed(frame[3:])
        assert len(results) == 1

    def test_decode_bad_crc(self):
        """Decoder should discard frames with bad CRC."""
        frame = encode_frame(seq=1, cmd_id=9, payload=b"")
        # Corrupt the CRC
        frame = frame[:-1] + b"\x00"
        decoder = FrameDecoder()
        results = decoder.feed(frame)
        assert len(results) == 0


class TestTLVParsing:
    def test_parse_simple_tlv(self):
        """Parse a simple TLV buffer."""
        data = bytes([TLV_DEVICE_NAME, 4]) + b"pico"
        tlvs = parse_tlv(data)
        assert TLV_DEVICE_NAME in tlvs
        assert tlvs[TLV_DEVICE_NAME] == b"pico"

    def test_parse_string_tlv(self):
        """Parse a string TLV."""
        data = bytes([TLV_MCU_TYPE, 6]) + b"rp2040"
        tlvs = parse_tlv(data)
        assert parse_string_tlv(tlvs, TLV_MCU_TYPE) == "rp2040"

    def test_parse_multiple_tlvs(self):
        """Parse multiple TLVs in sequence."""
        data = (
            bytes([TLV_DEVICE_NAME, 4]) + b"pico" + bytes([TLV_MCU_TYPE, 6]) + b"rp2040"
        )
        tlvs = parse_tlv(data)
        assert len(tlvs) == 2
        assert parse_string_tlv(tlvs, TLV_DEVICE_NAME) == "pico"
        assert parse_string_tlv(tlvs, TLV_MCU_TYPE) == "rp2040"

    def test_parse_truncated_tlv(self):
        """Parse a truncated TLV — should stop gracefully."""
        data = bytes([TLV_DEVICE_NAME, 10]) + b"short"
        tlvs = parse_tlv(data)
        assert len(tlvs) == 0  # Truncated, nothing parsed


class TestDeviceIdentity:
    def test_ferqon_identified(self):
        """Device with FERQON signature is classified as identified."""
        # Build a device_info body with signature
        sig = b"FERQON" + b"revyrlabs" + bytes([1])
        body = (
            bytes([TLV_DEVICE_NAME, 4])
            + b"pico"
            + bytes([TLV_MCU_TYPE, 6])
            + b"rp2040"
            + bytes([TLV_FIRMWARE_VERSION, 5])
            + b"1.1.0"
            + bytes([TLV_PROTOCOL_VERSION, 5])
            + b"1.1.0"
            + bytes([TLV_FERQON_SIGNATURE, len(sig)])
            + sig
        )
        identity = parse_device_info(body)
        assert identity.has_signature is True
        assert identity.classification == "ferqon_identified"
        assert identity.device_name == "pico"

    def test_ferqon_compatible(self):
        """Device with all fields but no signature is compatible."""
        body = (
            bytes([TLV_DEVICE_NAME, 4])
            + b"pico"
            + bytes([TLV_MCU_TYPE, 6])
            + b"rp2040"
            + bytes([TLV_FIRMWARE_VERSION, 5])
            + b"1.1.0"
            + bytes([TLV_PROTOCOL_VERSION, 5])
            + b"1.1.0"
        )
        identity = parse_device_info(body)
        assert identity.has_signature is False
        assert identity.classification == "ferqon_compatible"

    def test_serial_unknown(self):
        """Device with some TLVs but missing fields is serial_unknown."""
        body = bytes([TLV_DEVICE_NAME, 4]) + b"pico"
        identity = parse_device_info(body)
        assert identity.classification == "serial_unknown"
