#!/usr/bin/env python3
"""Raw-byte framed serial client for Ferqon Pico runtime.

This helper centralizes command encoding/decoding for:
- ping
- driver_info
- driver_call
- reboot_bootloader
- echo
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

MAGIC = b"\xA5\x5A"
VERSION = 1
TYPE_REQUEST = 1
TYPE_RESPONSE = 2

PKT_REQUEST = 1
PKT_RESPONSE_OK = 2
PKT_RESPONSE_ERR = 3


@dataclass
class RuntimeResponse:
    cmd_id: int
    ok: bool
    ack: bool
    message: str


class FrameDecoder:
    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, data: bytes) -> list[tuple[int, int, int, bytes]]:
        self._buf.extend(data)
        out: list[tuple[int, int, int, bytes]] = []

        while True:
            if len(self._buf) < 2:
                break
            if self._buf[0:2] != MAGIC:
                del self._buf[0]
                continue
            if len(self._buf) < 7:
                break

            version = self._buf[2]
            msg_type = self._buf[3]
            flags = self._buf[4]
            payload_len = (self._buf[5] << 8) | self._buf[6]
            total = 7 + payload_len + 2
            if len(self._buf) < total:
                break

            payload = bytes(self._buf[7 : 7 + payload_len])
            recv = (self._buf[7 + payload_len] << 8) | self._buf[7 + payload_len + 1]
            calc = checksum(version, msg_type, flags, payload)

            if recv == calc and version == VERSION:
                out.append((version, msg_type, flags, payload))
                del self._buf[:total]
            else:
                del self._buf[0]

        return out


def load_command_ids() -> dict[str, int]:
    defaults = {
        "ping": 1,
        "driver_info": 2,
        "driver_call": 3,
        "reboot_bootloader": 4,
        "echo": 5,
    }
    root = Path(__file__).resolve().parent.parent
    commands_path = root / "commands.json"
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


def checksum(version: int, msg_type: int, flags: int, payload: bytes) -> int:
    acc = version + msg_type + flags
    acc += (len(payload) >> 8) & 0xFF
    acc += len(payload) & 0xFF
    acc += sum(payload)
    return acc & 0xFFFF


def encode_frame(payload: bytes, msg_type: int = TYPE_REQUEST, flags: int = 0) -> bytes:
    csum = checksum(VERSION, msg_type, flags, payload)
    return (
        MAGIC
        + bytes(
            [
                VERSION,
                msg_type & 0xFF,
                flags & 0xFF,
                (len(payload) >> 8) & 0xFF,
                len(payload) & 0xFF,
            ]
        )
        + payload
        + bytes([(csum >> 8) & 0xFF, csum & 0xFF])
    )


def encode_cmd_payload(cmd_id: int, body: bytes = b"", packet_type: int = PKT_REQUEST, meta: int = 0) -> bytes:
    return bytes([cmd_id & 0xFF, (cmd_id >> 8) & 0xFF, packet_type & 0xFF, meta & 0xFF]) + body


def encode_driver_call(driver_name: str, method: str, args: dict[str, object] | None = None) -> bytes:
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
    if len(payload) < 4:
        raise ValueError("payload too short")
    cmd_id = payload[0] | (payload[1] << 8)
    pkt = payload[2]
    meta = payload[3]
    msg = payload[4:].decode("utf-8", errors="replace")
    return RuntimeResponse(
        cmd_id=cmd_id,
        ok=(pkt == PKT_RESPONSE_OK),
        ack=((meta & 0x01) != 0),
        message=msg,
    )
