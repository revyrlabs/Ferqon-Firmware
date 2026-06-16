#!/usr/bin/env python3
"""Raw-byte framed serial client for Ferqon Pico runtime.

This helper centralizes command encoding/decoding for the Ferqon protocol.
Frame format: [START=0xAB] [SEQ] [CMD] [LEN] [payload...] [CRC_LO] [CRC_HI]
CRC: CRC-16/CCITT-FALSE (poly=0x1021, init=0xFFFF)

This matches the firmware protocol defined in firmware/protocol/ssot/commands.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Protocol constants from commands.json
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


@dataclass
class RuntimeResponse:
    cmd_id: int
    ok: bool
    ack: bool
    message: str


def crc16_ccitt_false(data: bytes) -> int:
    """Calculate CRC-16/CCITT-FALSE."""
    crc = CRC_INIT
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ CRC_POLY
            else:
                crc = (crc << 1)
            crc &= 0xFFFF
    return crc


class FrameDecoder:
    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, data: bytes) -> list[tuple[int, int, int, bytes]]:
        self._buf.extend(data)
        out: list[tuple[int, int, int, bytes]] = []

        while True:
            # Find START byte
            if len(self._buf) < 1:
                break
            if self._buf[0] != START_BYTE:
                del self._buf[0]
                continue

            # Need at least: START + SEQ + CMD + LEN + CRC_LO + CRC_HI = 6 bytes
            if len(self._buf) < 6:
                break

            seq = self._buf[1]
            cmd_id = self._buf[2]
            payload_len = self._buf[3]
            total = 6 + payload_len  # START + SEQ + CMD + LEN + payload + CRC_LO + CRC_HI

            if len(self._buf) < total:
                break

            payload = bytes(self._buf[4 : 4 + payload_len])
            crc_lo = self._buf[4 + payload_len]
            crc_hi = self._buf[4 + payload_len + 1]
            recv_crc = crc_lo | (crc_hi << 8)

            # Calculate CRC over SEQ + CMD + LEN + payload
            crc_data = bytes([seq, cmd_id, payload_len]) + payload
            calc_crc = crc16_ccitt_false(crc_data)

            if recv_crc == calc_crc:
                # Extract packet type from first byte of payload
                pkt_type = payload[0] if payload else 0
                out.append((seq, cmd_id, pkt_type, payload))
                del self._buf[:total]
            else:
                # CRC mismatch - discard and resync
                del self._buf[0]

        return out


def load_command_ids() -> dict[str, int]:
    """Load command IDs from commands.json."""
    defaults = {
        "pin_mode": 1,
        "driver_info": 2,
        "driver_call": 3,
        "echo": 8,
        "ping": 9,
        "reset": 10,
        "device_info": 11,
        "capabilities": 12,
        "gpio_read": 16,
        "gpio_write": 17,
        "uart_send": 18,
        "uart_expect": 19,
        "adc_read": 20,
        "adc_expect": 21,
        "pulse_measure": 22,
        "set_debug_level": 23,
    }
    root = Path(__file__).resolve().parent.parent
    commands_path = root / "protocol" / "ssot" / "commands.json"
    try:
        data = json.loads(commands_path.read_text(encoding="utf-8"))
        commands = data.get("commands", {})
        for key in list(defaults):
            item = commands.get(key)
            if isinstance(item, dict) and isinstance(item.get("id"), int):
                defaults[key] = int(item["id"])
    except Exception:
        pass
    return defaults


def encode_frame(seq: int, cmd_id: int, payload: bytes) -> bytes:
    """Encode a complete frame with CRC."""
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError(f"Payload too large: {len(payload)} > {MAX_PAYLOAD_BYTES}")

    # Build header: SEQ + CMD + LEN
    header = bytes([seq, cmd_id, len(payload)])

    # Calculate CRC over header + payload
    crc_data = header + payload
    crc = crc16_ccitt_false(crc_data)

    # Build frame: START + header + payload + CRC_LO + CRC_HI
    return bytes([START_BYTE]) + header + payload + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def encode_cmd_payload(cmd_id: int, body: bytes = b"", packet_type: int = PKT_REQUEST, meta: int = 0) -> bytes:
    """Encode command payload with packet type header."""
    return bytes([packet_type, meta]) + body


def encode_driver_call(driver_name: str, method: str, args: dict[str, object] | None = None) -> bytes:
    """Encode driver call payload."""
    args = args or {}
    driver = driver_name.encode("utf-8")
    call = method.encode("utf-8")
    if len(driver) > 255 or len(call) > 255:
        raise ValueError("driver/method too long")

    parts: list[str] = []
    for key, value in args.items():
        parts.append(f"{key}={value}")
    kv = ";".join(parts).encode("utf-8")

    body = bytearray()
    body.append(len(driver))
    body.extend(driver)
    body.append(len(call))
    body.extend(call)
    body.extend(kv)
    return bytes(body)


def decode_cmd_payload(payload: bytes) -> RuntimeResponse:
    """Decode command response payload.

    For PKT_DONE: [PKT_DONE][meta][message...]
    For PKT_ERROR: [PKT_ERROR][code][category][retryable][ctx][detail...]
    """
    if len(payload) < 1:
        raise ValueError("payload too short")

    pkt_type = payload[0]

    if pkt_type == PKT_DONE:
        # DONE: [type][meta][message...]
        meta = payload[1] if len(payload) > 1 else 0
        msg = payload[2:].decode("utf-8", errors="replace")
        return RuntimeResponse(
            cmd_id=0,
            ok=True,
            ack=((meta & 0x01) != 0),
            message=msg,
        )
    elif pkt_type == PKT_ERROR:
        # ERROR: [type][code][category][retryable][ctx][detail...]
        if len(payload) < 5:
            msg = f"error (truncated: {payload.hex()})"
        else:
            code = payload[1]
            category = payload[2]
            retryable = bool(payload[3])
            ctx = payload[4]
            detail = payload[5:].decode("utf-8", errors="replace")
            msg = f"error code={code} category={category} retryable={retryable} ctx={ctx} detail={detail}"
        return RuntimeResponse(
            cmd_id=0,
            ok=False,
            ack=False,
            message=msg,
        )
    else:
        # Unknown packet type
        msg = f"unknown packet type {pkt_type}: {payload.hex()}"
        return RuntimeResponse(
            cmd_id=0,
            ok=False,
            ack=False,
            message=msg,
        )
