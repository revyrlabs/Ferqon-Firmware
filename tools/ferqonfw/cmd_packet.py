# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs
"""
cmd_packet.py
-------------
Packet command for ferqonfw CLI - encode/decode packets.
"""

from ferqonfw.board_loader import get_ssot_dir
import json


def calculate_checksum(packet: bytes) -> int:
    """Calculate XOR checksum of packet bytes."""
    checksum = 0
    for byte in packet:
        checksum ^= byte
    return checksum


def encode_packet(command_name: str, params: dict) -> str:
    """Encode a command to a hex packet."""
    ssot_dir = get_ssot_dir()
    commands_path = ssot_dir / "commands.json"

    try:
        with open(commands_path, encoding="utf-8") as f:
            commands_data = json.load(f)
    except FileNotFoundError:
        raise ValueError("commands.json not found")

    if command_name not in commands_data["commands"]:
        raise ValueError(f"Unknown command: {command_name}")

    cmd = commands_data["commands"][command_name]
    cmd_id = cmd["id"]

    # Build payload from params
    payload = bytearray()
    param_defs = cmd.get("params", [])

    if params:
        for param_def in param_defs:
            param_name = param_def["name"]
            param_type = param_def["type"]
            if param_name not in params:
                raise ValueError(f"Missing parameter: {param_name}")

            value = params[param_name]

            if param_type == "u8":
                payload.append(int(value) & 0xFF)
            elif param_type == "u16":
                val = int(value) & 0xFFFF
                payload.append(val & 0xFF)
                payload.append((val >> 8) & 0xFF)
            elif param_type == "u32":
                val = int(value) & 0xFFFFFFFF
                payload.append(val & 0xFF)
                payload.append((val >> 8) & 0xFF)
                payload.append((val >> 16) & 0xFF)
                payload.append((val >> 24) & 0xFF)
            elif param_type == "i8":
                payload.append(int(value) & 0xFF)
            elif param_type == "i16":
                val = int(value) & 0xFFFF
                payload.append(val & 0xFF)
                payload.append((val >> 8) & 0xFF)
            elif param_type == "i32":
                val = int(value) & 0xFFFFFFFF
                payload.append(val & 0xFF)
                payload.append((val >> 8) & 0xFF)
                payload.append((val >> 16) & 0xFF)
                payload.append((val >> 24) & 0xFF)
            elif param_type == "bytes":
                if isinstance(value, str):
                    payload.extend(value.encode())
                else:
                    payload.extend(value)

    # Build packet
    packet = bytearray()
    packet.append(0xAB)  # START
    packet.append(cmd_id)  # CMD_ID
    packet.append(len(payload))  # PARAM_LEN
    packet.extend(payload)  # PARAMS
    checksum = calculate_checksum(packet)
    packet.append(checksum)  # CHECKSUM

    return " ".join(f"{b:02X}" for b in packet)


def decode_packet(hex_str: str) -> str:
    """Decode a hex packet to human-readable form."""
    # Parse hex string
    hex_bytes = hex_str.split()
    packet = [int(h, 16) for h in hex_bytes]

    if len(packet) < 3:
        raise ValueError("Packet too short")

    # Parse packet
    start = packet[0]
    status_or_cmd = packet[1]
    length = packet[2]

    result = []
    result.append(f"START: 0x{start:02X}")

    if status_or_cmd == 0x00:
        result.append("STATUS: 0x00 (OK)")
        result.append(f"DATA_LEN: 0x{length:02X}")
        if length > 0:
            data = packet[3 : 3 + length]
            result.append(f"DATA: {' '.join(f'{b:02X}' for b in data)}")
        checksum_idx = 3 + length
        if checksum_idx < len(packet):
            checksum = packet[checksum_idx]
            expected_checksum = calculate_checksum(bytes(packet[:checksum_idx]))
            result.append(
                f"CHECKSUM: 0x{checksum:02X} ({'valid' if checksum == expected_checksum else 'invalid'})"
            )
    elif status_or_cmd == 0xFF:
        result.append("STATUS: 0xFF (ERROR)")
        result.append(f"DATA_LEN: 0x{length:02X}")
        if length > 0:
            error_code = packet[3]
            result.append(f"ERROR_CODE: 0x{error_code:02X}")
            if length > 1:
                detail = packet[4 : 4 + length - 1]
                result.append(f"DETAIL: {' '.join(f'{b:02X}' for b in detail)}")
        checksum_idx = 3 + length
        if checksum_idx < len(packet):
            checksum = packet[checksum_idx]
            expected_checksum = calculate_checksum(bytes(packet[:checksum_idx]))
            result.append(
                f"CHECKSUM: 0x{checksum:02X} ({'valid' if checksum == expected_checksum else 'invalid'})"
            )
    else:
        # Request
        ssot_dir = get_ssot_dir()
        commands_path = ssot_dir / "commands.json"
        try:
            with open(commands_path, encoding="utf-8") as f:
                commands_data = json.load(f)
            cmd_name = None
            for name, cmd in commands_data["commands"].items():
                if cmd["id"] == status_or_cmd:
                    cmd_name = name
                    break
            if cmd_name:
                result.append(f"CMD_ID: 0x{status_or_cmd:02X} ({cmd_name})")
            else:
                result.append(f"CMD_ID: 0x{status_or_cmd:02X} (unknown)")
        except FileNotFoundError:
            result.append(f"CMD_ID: 0x{status_or_cmd:02X}")

        result.append(f"PARAM_LEN: 0x{length:02X}")
        if length > 0:
            params = packet[3 : 3 + length]
            result.append(f"PARAMS: {' '.join(f'{b:02X}' for b in params)}")
        checksum_idx = 3 + length
        if checksum_idx < len(packet):
            checksum = packet[checksum_idx]
            expected_checksum = calculate_checksum(bytes(packet[:checksum_idx]))
            result.append(
                f"CHECKSUM: 0x{checksum:02X} ({'valid' if checksum == expected_checksum else 'invalid'})"
            )

    return "\n".join(result)


def cmd_packet_encode(args) -> int:
    """Encode a command to hex."""
    try:
        params = {}
        for param in args.param:
            if "=" in param:
                key, value = param.split("=", 1)
                params[key] = value
            else:
                # Handle mode strings like GPIO_OUT
                params["mode"] = param

        hex_str = encode_packet(args.command, params)
        print(hex_str)
        return 0
    except ValueError as e:
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
