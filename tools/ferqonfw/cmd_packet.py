# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
cmd_packet.py
-------------
Packet command for ferqonfw CLI - encode/decode packets.
"""

import json

import serial_protocol as sp
from ferqonfw.board_loader import get_ssot_dir


def _load_commands() -> dict:
    ssot_dir = get_ssot_dir()
    commands_path = ssot_dir / "commands.json"
    with open(commands_path, encoding="utf-8") as f:
        return json.load(f)["commands"]


def _command_name_from_id(cmd_id: int, commands: dict) -> str:
    for name, meta in commands.items():
        if meta.get("id") == cmd_id:
            return name
    return "unknown"


def _encode_param(param_type: str, value: str) -> bytes:
    """Encode a single parameter value according to its type."""
    if param_type == "u8":
        return bytes([int(value) & 0xFF])
    if param_type == "u16":
        val = int(value) & 0xFFFF
        return bytes([val & 0xFF, (val >> 8) & 0xFF])
    if param_type == "u32":
        val = int(value) & 0xFFFFFFFF
        return bytes(
            [
                val & 0xFF,
                (val >> 8) & 0xFF,
                (val >> 16) & 0xFF,
                (val >> 24) & 0xFF,
            ]
        )
    if param_type == "i8":
        return bytes([int(value) & 0xFF])
    if param_type == "i16":
        val = int(value) & 0xFFFF
        return bytes([val & 0xFF, (val >> 8) & 0xFF])
    if param_type == "i32":
        val = int(value) & 0xFFFFFFFF
        return bytes(
            [
                val & 0xFF,
                (val >> 8) & 0xFF,
                (val >> 16) & 0xFF,
                (val >> 24) & 0xFF,
            ]
        )
    if param_type in ("bytes", "string"):
        if value.startswith("0x"):
            return bytes.fromhex(value[2:])
        return value.encode("utf-8")
    raise ValueError(f"Unsupported parameter type: {param_type}")


def encode_packet(command_name: str, params: dict, seq: int = 1) -> str:
    """Encode a command to a hex packet."""
    commands = _load_commands()

    if command_name not in commands:
        raise ValueError(f"Unknown command: {command_name}")

    cmd = commands[command_name]
    cmd_id = cmd["id"]

    body = bytearray()
    param_defs = cmd.get("params", [])
    for param_def in param_defs:
        param_name = param_def["name"]
        if param_name not in params:
            raise ValueError(f"Missing parameter: {param_name}")
        body.extend(_encode_param(param_def["type"], params[param_name]))

    payload = sp.encode_cmd_payload(cmd_id, bytes(body), packet_type=sp.PKT_REQUEST)
    frame = sp.encode_frame(seq=seq, cmd_id=cmd_id, payload=payload)
    return " ".join(f"{b:02X}" for b in frame)


def decode_packet(hex_str: str) -> str:
    """Decode a hex packet to human-readable form."""
    hex_bytes = hex_str.split()
    try:
        data = bytes(int(h, 16) for h in hex_bytes)
    except ValueError as e:
        raise ValueError(f"Invalid hex input: {e}") from e

    if len(data) < 6:
        raise ValueError("Packet too short")

    if data[0] != sp.START_BYTE:
        raise ValueError(f"Invalid start byte: 0x{data[0]:02X}")

    commands = _load_commands()
    decoder = sp.FrameDecoder()
    frames = decoder.feed(data)
    if not frames:
        raise ValueError("No valid frame found")

    seq, cmd_id, pkt_type, payload = frames[0]
    cmd_name = _command_name_from_id(cmd_id, commands)

    result = [
        f"START: 0x{sp.START_BYTE:02X}",
        f"SEQ: 0x{seq:02X}",
        f"CMD_ID: 0x{cmd_id:02X} ({cmd_name})",
        f"PARAM_LEN: 0x{len(payload):02X}",
        f"PAYLOAD: {' '.join(f'{b:02X}' for b in payload)}",
    ]

    type_names = {
        sp.PKT_REQUEST: "REQUEST",
        sp.PKT_ACK: "ACK",
        sp.PKT_DONE: "DONE",
        sp.PKT_ERROR: "ERROR",
        sp.PKT_HEARTBEAT: "HEARTBEAT",
        sp.PKT_EVENT: "EVENT",
        sp.PKT_LOG: "LOG",
    }
    result.append(f"TYPE: {type_names.get(pkt_type, f'0x{pkt_type:02X}')}")

    if pkt_type == sp.PKT_ERROR:
        if len(payload) >= 5:
            result.append(f"ERROR_CODE: {payload[1]}")
            result.append(f"CATEGORY: {payload[2]}")
            result.append(f"RETRYABLE: {bool(payload[3])}")
            result.append(f"CTX: {payload[4]}")
            result.append(f"DETAIL: {payload[5:].hex()}")
        else:
            result.append(f"ERROR_BODY: {payload.hex()}")
    else:
        result.append(f"BODY: {payload[1:].hex()}")

    return "\n".join(result)


def _parse_params(params: list[str]) -> dict:
    out: dict[str, str] = {}
    for param in params:
        if "=" in param:
            key, value = param.split("=", 1)
            out[key] = value
        else:
            out["mode"] = param
    return out


def cmd_packet_encode(args) -> int:
    """Encode a command to hex."""
    try:
        params = _parse_params(args.param)
        hex_str = encode_packet(args.command, params)
        print(hex_str)
        return 0
    except (ValueError, KeyError) as e:
        print(f"Error: {e}")
        return 1


def cmd_packet_decode(args) -> int:
    """Decode a hex packet."""
    try:
        result = decode_packet(args.hex)
        print(result)
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
