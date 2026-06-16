#!/usr/bin/env python3
"""Quick diagnostic test for Pico communication (raw-byte protocol)."""

import json
import time
import sys
from pathlib import Path

import serial

# Add tools to path for device_config/discovery
tools_dir = Path(__file__).parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from device_config import get_default_device_port, get_default_baudrate
from device_discovery import find_board

from serial_protocol import (
    TYPE_RESPONSE,
    FrameDecoder,
    decode_cmd_payload,
    encode_cmd_payload,
    encode_frame,
    load_command_ids,
)


def send_and_print(ser: serial.Serial, cmd_name: str) -> dict | None:
    ids = load_command_ids()
    cmd_id = ids[cmd_name]
    req_payload = encode_cmd_payload(cmd_id)
    frame = encode_frame(req_payload)

    print(f"\nSending {cmd_name} (cmd=0x{cmd_id:04X})")
    print(f"   TX: {frame.hex()}")
    ser.write(frame)
    ser.flush()

    decoder = FrameDecoder()
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        try:
            chunk = ser.read(128)
        except serial.SerialException as exc:
            print(f"   Serial read error: {exc}")
            return None
        if not chunk:
            continue
        for _ver, msg_type, _flags, payload in decoder.feed(chunk):
            if msg_type != TYPE_RESPONSE:
                continue
            decoded = decode_cmd_payload(payload)
            resp = {
                "ok": decoded.ok,
                "ack": decoded.ack,
                "cmd_id": decoded.cmd_id,
                "result": decoded.message if decoded.ok else "",
                "error": "" if decoded.ok else decoded.message,
            }
            print(f"   RX payload: {payload.hex()}")
            print(f"   Parsed: {json.dumps(resp, indent=2)}")
            return resp

    print("   No response (timeout)")
    return None


def main() -> int:
    port = find_board("pico") or get_default_device_port()
    baudrate = get_default_baudrate()
    ser = serial.Serial(port, baudrate, timeout=0.1)
    time.sleep(0.5)

    print(f"Pico connection test ({port} @ {baudrate}):")
    print(f"Open: {ser.is_open}")

    send_and_print(ser, "ping")
    send_and_print(ser, "driver_info")

    ser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
