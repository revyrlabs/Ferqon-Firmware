# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
protocol.py
-----------
Self-contained Ferqon serial protocol implementation for the production CLI.

This module does NOT import ferqon_emulator.py, ferqon_selftest.py,
or any test/backend/hardware-SDK module. It implements the framed
Ferqon protocol (CRC-16/CCITT-FALSE) and a serial transport suitable
for production identify/diagnose/ping workflows.

Frame format: [START=0xAB] [SEQ] [CMD] [LEN] [payload...] [CRC_LO] [CRC_HI]
CRC: CRC-16/CCITT-FALSE (poly=0x1021, init=0xFFFF)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# Protocol constants (match firmware/protocol/ssot/commands.json)
START_BYTE = 0xAB
CRC_POLY = 0x1021
CRC_INIT = 0xFFFF
MAX_PAYLOAD_BYTES = 255

# Packet types
PKT_REQUEST = 1
PKT_ACK = 2
PKT_DONE = 3
PKT_ERROR = 4
PKT_HEARTBEAT = 5
PKT_EVENT = 6
PKT_LOG = 7

# TLV types for device_info responses (namespace: device_info).
# These values mirror protocol/ssot/commands.json["tlv_types"] and are
# verified by the generator-drift CI check.  They are kept as module-level
# constants so this module remains pure on import (no file I/O at import
# time).  Use load_tlv_types() to read them from the SSOT at runtime.
TLV_DEVICE_NAME = 1
TLV_MCU_TYPE = 2
TLV_FIRMWARE_VERSION = 3
TLV_PROTOCOL_VERSION = 4
TLV_BUILD_TIMESTAMP = 5
TLV_FREE_RAM = 6
TLV_UPTIME_MS = 7
TLV_FERQON_SIGNATURE = 16

# TLV types for driver_info responses (namespace: driver_info).
# NOTE: DRIVER=1 and COMMAND=2 intentionally collide with DEVICE_NAME=1
# and MCU_TYPE=2 — they live in a different TLV scope (driver_info vs
# device_info) and are never mixed in the same response body.
TLV_DRIVER = 1
TLV_COMMAND = 2
TLV_METHOD = 3
TLV_VERSION = 4

# Default serial baud rate
DEFAULT_BAUD = 115200

# Default CLI transport timing (mirrors tools/production_config.json).
# Overridden at runtime by load_cli_timing() from the SSOT config.
DEFAULT_CLI_TIMEOUT_S = 2.0
DEFAULT_CLI_CONNECT_DELAY_MS = 500


def crc16_ccitt_false(data: bytes) -> int:
    """Calculate CRC-16/CCITT-FALSE."""
    crc = CRC_INIT
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ CRC_POLY
            else:
                crc = crc << 1
            crc &= 0xFFFF
    return crc


def encode_frame(seq: int, cmd_id: int, payload: bytes) -> bytes:
    """Encode a complete frame with CRC."""
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError(f"Payload too large: {len(payload)} > {MAX_PAYLOAD_BYTES}")
    header = bytes([seq, cmd_id, len(payload)])
    crc_data = header + payload
    crc = crc16_ccitt_false(crc_data)
    return (
        bytes([START_BYTE]) + header + payload + bytes([crc & 0xFF, (crc >> 8) & 0xFF])
    )


class FrameDecoder:
    """Streaming frame decoder for the Ferqon protocol."""

    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, data: bytes) -> list[tuple[int, int, int, bytes]]:
        """Feed bytes and return list of (seq, cmd_id, pkt_type, payload) tuples."""
        self._buf.extend(data)
        out: list[tuple[int, int, int, bytes]] = []

        while True:
            if len(self._buf) < 1:
                break
            if self._buf[0] != START_BYTE:
                del self._buf[0]
                continue

            if len(self._buf) < 6:
                break

            seq = self._buf[1]
            cmd_id = self._buf[2]
            payload_len = self._buf[3]
            total = 6 + payload_len

            if len(self._buf) < total:
                break

            payload = bytes(self._buf[4 : 4 + payload_len])
            crc_lo = self._buf[4 + payload_len]
            crc_hi = self._buf[4 + payload_len + 1]
            recv_crc = crc_lo | (crc_hi << 8)

            crc_data = bytes([seq, cmd_id, payload_len]) + payload
            calc_crc = crc16_ccitt_false(crc_data)

            if recv_crc == calc_crc:
                pkt_type = payload[0] if payload else 0
                out.append((seq, cmd_id, pkt_type, payload))
                del self._buf[:total]
            else:
                del self._buf[0]

        return out


def parse_tlv(data: bytes) -> dict[int, bytes]:
    """Parse TLV-encoded data into a {type: value} dict."""
    result: dict[int, bytes] = {}
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
    """Extract a UTF-8 string from a TLV dict."""
    value = tlvs.get(tlv_type, b"")
    try:
        return value.decode("utf-8", errors="replace").rstrip("\x00")
    except Exception:
        return ""


@dataclass
class DeviceIdentity:
    """Parsed device_info response."""

    device_name: str
    mcu_type: str
    firmware_version: str
    protocol_version: str
    has_signature: bool
    signature_vendor: str
    signature_cap_version: int

    @property
    def classification(self) -> str:
        if self.has_signature:
            return "ferqon_identified"
        if (
            self.device_name
            and self.mcu_type
            and self.firmware_version
            and self.protocol_version
        ):
            return "ferqon_compatible"
        return "serial_unknown"


def parse_device_info(body: bytes) -> DeviceIdentity:
    """Parse a device_info response body (TLV-encoded).

    TLV type IDs are loaded from the SSOT at runtime via load_tlv_types(),
    falling back to the module-level constants if the SSOT is unavailable.
    """
    try:
        tlv = load_tlv_types()
        tlv_device_name = tlv.get("DEVICE_NAME", TLV_DEVICE_NAME)
        tlv_mcu_type = tlv.get("MCU_TYPE", TLV_MCU_TYPE)
        tlv_fw_version = tlv.get("FIRMWARE_VERSION", TLV_FIRMWARE_VERSION)
        tlv_proto_version = tlv.get("PROTOCOL_VERSION", TLV_PROTOCOL_VERSION)
        tlv_signature = tlv.get("FERQON_SIGNATURE", TLV_FERQON_SIGNATURE)
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        tlv_device_name = TLV_DEVICE_NAME
        tlv_mcu_type = TLV_MCU_TYPE
        tlv_fw_version = TLV_FIRMWARE_VERSION
        tlv_proto_version = TLV_PROTOCOL_VERSION
        tlv_signature = TLV_FERQON_SIGNATURE

    tlvs = parse_tlv(body)
    device_name = parse_string_tlv(tlvs, tlv_device_name)
    mcu_type = parse_string_tlv(tlvs, tlv_mcu_type)
    fw_version = parse_string_tlv(tlvs, tlv_fw_version)
    proto_version = parse_string_tlv(tlvs, tlv_proto_version)

    sig_bytes = tlvs.get(tlv_signature, b"")
    has_sig = sig_bytes.startswith(b"FERQON")
    vendor = ""
    cap_version = 0
    if has_sig and len(sig_bytes) > 6:
        # signature = magic + vendor + cap_version_byte
        vendor = sig_bytes[6:-1].decode("utf-8", errors="replace")
        cap_version = sig_bytes[-1] if sig_bytes else 0

    return DeviceIdentity(
        device_name=device_name,
        mcu_type=mcu_type,
        firmware_version=fw_version,
        protocol_version=proto_version,
        has_signature=has_sig,
        signature_vendor=vendor,
        signature_cap_version=cap_version,
    )


def load_command_ids(firmware_dir: Optional[Path] = None) -> dict[str, int]:
    """Load command IDs from the SSOT commands.json.

    Raises FileNotFoundError if the SSOT is missing.
    """
    if firmware_dir is None:
        # Resolve relative to this file: tools/ferqonfw/ -> firmware/
        firmware_dir = Path(__file__).resolve().parents[2]
    commands_path = firmware_dir / "protocol" / "ssot" / "commands.json"
    data = json.loads(commands_path.read_text(encoding="utf-8"))
    raw = data["commands"]
    return {
        name: int(entry["id"])
        for name, entry in raw.items()
        if isinstance(entry, dict) and isinstance(entry.get("id"), int)
    }


def load_tlv_types(firmware_dir: Optional[Path] = None) -> dict[str, int]:
    """Load TLV type IDs from the SSOT commands.json.

    Returns a flat dict mapping TLV name -> numeric ID.  Names from
    different TLV scopes (device_info vs driver_info) are disambiguated
    by the caller based on context.

    Raises FileNotFoundError if the SSOT is missing.
    """
    if firmware_dir is None:
        firmware_dir = Path(__file__).resolve().parents[2]
    commands_path = firmware_dir / "protocol" / "ssot" / "commands.json"
    data = json.loads(commands_path.read_text(encoding="utf-8"))
    raw = data.get("tlv_types", {})
    return {name: int(value) for name, value in raw.items()}


def load_cli_timing(firmware_dir: Optional[Path] = None) -> tuple[float, int]:
    """Load CLI transport timing from production_config.json.

    Returns (timeout_s, connect_delay_ms).  Falls back to module-level
    defaults if the config file is missing or unreadable — the production
    CLI must still work without the config file present.
    """
    if firmware_dir is None:
        firmware_dir = Path(__file__).resolve().parents[2]
    config_path = firmware_dir / "tools" / "production_config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_CLI_TIMEOUT_S, DEFAULT_CLI_CONNECT_DELAY_MS
    timeout = config.get("cli_timeout_s", DEFAULT_CLI_TIMEOUT_S)
    delay = config.get("cli_connect_delay_ms", DEFAULT_CLI_CONNECT_DELAY_MS)
    return float(timeout), int(delay)


def get_info_command_ids(firmware_dir: Optional[Path] = None) -> set[int]:
    """Return command IDs that do not require a REQUEST prefix.

    Filters out the reserved seq=0 value so it is never treated as a
    valid command ID.
    """
    try:
        ids = load_command_ids(firmware_dir)
        return {
            ids["device_info"],
            ids["driver_info"],
        } & {v for v in ids.values() if v != 0}
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return set()


class SerialTransport:
    """Production serial transport using pyserial.

    Requires an explicit port — no default port fallback.

    Timing defaults (timeout_s, connect_delay_ms) are loaded from
    production_config.json via load_cli_timing() if not provided
    explicitly.
    """

    def __init__(
        self,
        port: str,
        baudrate: int = DEFAULT_BAUD,
        timeout: Optional[float] = None,
        connect_delay_ms: Optional[int] = None,
    ):
        self.port = port
        self.baudrate = baudrate
        default_timeout, default_delay = load_cli_timing()
        self.timeout = timeout if timeout is not None else default_timeout
        self.connect_delay_ms = (
            connect_delay_ms if connect_delay_ms is not None else default_delay
        )
        self._conn: Any = None

    def connect(self) -> None:
        import serial  # imported lazily so the module is pure on import

        self._conn = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        time.sleep(self.connect_delay_ms / 1000.0)

    def send_frame(self, frame: bytes, timeout_s: float = 2.0) -> dict[str, Any]:
        """Send a frame and return parsed response."""
        if self._conn is None:
            raise RuntimeError("Transport not connected")
        self._conn.write(frame)
        self._conn.flush()

        decoder = FrameDecoder()
        deadline = time.time() + timeout_s
        self._conn.timeout = timeout_s
        response_types = {PKT_DONE, PKT_ACK, PKT_ERROR}
        while time.time() < deadline:
            chunk = self._conn.read(1)
            if not chunk:
                continue
            for _, _, pkt_type, payload in decoder.feed(chunk):
                if pkt_type not in response_types:
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
