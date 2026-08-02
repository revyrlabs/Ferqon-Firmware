#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
test_sil.py
-----------
Standard-library-only integration test for the Ferqon firmware
Software-in-the-Loop (SIL) desktop build.

Connects to the SIL TCP port, encodes/decodes the Ferqon serial protocol
frames, and verifies that the native firmware binary responds to a small
health-check suite: ping, echo, device_info, driver_info, gpio read/write,
adc_read, and pulse_measure.

Usage:
    python3 tests/sil/test_sil.py [HOST] [PORT]

Defaults to 127.0.0.1:3333. The script has no third-party dependencies.
"""

import os
import re
import socket
import sys
import time
from pathlib import Path

START_BYTE = 0xAB

PKT_REQUEST = 1
PKT_DONE = 3
PKT_ERROR = 4


def _load_cmd_ids():
    """Parse src/ferqon_commands.h for command ID defines."""
    header = Path(__file__).resolve().parent.parent.parent / "src" / "ferqon_commands.h"
    ids = {}
    if header.exists():
        text = header.read_text(encoding="utf-8")
        for name, val in re.findall(r"#define\s+FERQON_CMD_(\w+)\s+(\d+)", text):
            ids[name.lower()] = int(val)
    return ids


CMD = _load_cmd_ids()


def crc16_ccitt_false(data: bytes, init: int = 0xFFFF, poly: int = 0x1021) -> int:
    """CRC-16/CCITT-FALSE, matching src/protocol.cpp."""
    crc = init
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def encode_frame(seq: int, cmd_id: int, payload: bytes) -> bytes:
    """Encode a Ferqon protocol frame."""
    body = bytes([seq, cmd_id, len(payload)]) + payload
    c = crc16_ccitt_false(body)
    return bytes([START_BYTE]) + body + bytes([c & 0xFF, (c >> 8) & 0xFF])


def _parse_one(buf: bytearray):
    """If a complete, CRC-valid frame starts in buf, return (seq, cmd, payload)."""
    while True:
        try:
            start = buf.index(START_BYTE)
        except ValueError:
            buf.clear()
            return None

        if len(buf) - start < 6:
            # Need at least START + SEQ + CMD + LEN + CRC_LO + CRC_HI
            if start > 0:
                del buf[:start]
            return None

        payload_len = buf[start + 3]
        total = 6 + payload_len
        if len(buf) - start < total:
            if start > 0:
                del buf[:start]
            return None

        frame = buf[start : start + total]
        body = frame[1:-2]
        recv_crc = frame[-2] | (frame[-1] << 8)
        if crc16_ccitt_false(body) == recv_crc:
            seq = frame[1]
            cmd = frame[2]
            payload = bytes(frame[4 : 4 + payload_len])
            del buf[: start + total]
            return seq, cmd, payload

        # Bad CRC / false start: drop the START byte and keep scanning.
        del buf[start]


def recv_response(sock: socket.socket, buf: bytearray, timeout_s: float = 2.0):
    """Read the next valid frame from the wire (unolicited seq=0 frames are skipped)."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        parsed = _parse_one(buf)
        if parsed is not None:
            return parsed
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        sock.settimeout(min(remaining, 0.2))
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            continue
        if not chunk:
            raise ConnectionError("SIL TCP socket closed by peer")
        buf.extend(chunk)

    raise TimeoutError("Timed out waiting for a valid frame")


def expect_done(sock: socket.socket, buf: bytearray, seq: int, cmd_id: int, body_check=None, timeout_s: float = 5.0):
    """Receive frames until we get a DONE response for the given seq/cmd."""
    deadline = time.monotonic() + timeout_s
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"Timed out waiting for DONE response to seq={seq} cmd={cmd_id}")
        rseq, rcmd, payload = recv_response(sock, buf, timeout_s=remaining)
        if rseq == 0:
            # Unsolicited heartbeat/log/event — ignore.
            continue
        if rseq != seq:
            raise AssertionError(f"expected seq={seq}, got seq={rseq}")
        if rcmd != cmd_id:
            raise AssertionError(f"expected cmd={cmd_id}, got cmd={rcmd}")
        if not payload:
            raise AssertionError("empty response payload")
        if payload[0] != PKT_DONE:
            raise AssertionError(
                f"expected PKT_DONE ({PKT_DONE}), got {payload[0]}; "
                f"error code={payload[1] if len(payload) > 1 else 'n/a'}"
            )
        if body_check is not None:
            body_check(payload[1:])
        return payload


def pack_u16_le(v: int) -> bytes:
    return bytes([v & 0xFF, (v >> 8) & 0xFF])


def pack_u32_le(v: int) -> bytes:
    return bytes([v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF])


def cmd_payload(cmd_name: str, body: bytes = b"") -> bytes:
    """Build the packet-type prefixed payload for normal commands."""
    if cmd_name in ("device_info", "driver_info"):
        return body
    return bytes([PKT_REQUEST]) + body


def test_ping(sock: socket.socket, buf: bytearray):
    seq = 1
    payload = cmd_payload("ping")
    sock.sendall(encode_frame(seq, CMD["ping"], payload))
    expect_done(sock, buf, seq, CMD["ping"])
    print("[OK] ping")


def test_echo(sock: socket.socket, buf: bytearray):
    seq = 2
    data = b"sil"
    payload = cmd_payload("echo", data)
    sock.sendall(encode_frame(seq, CMD["echo"], payload))

    def check(body: bytes):
        if body != data:
            raise AssertionError(f"echo mismatch: {body!r} != {data!r}")

    expect_done(sock, buf, seq, CMD["echo"], check)
    print("[OK] echo")


def test_device_info(sock: socket.socket, buf: bytearray):
    seq = 3
    payload = cmd_payload("device_info")
    sock.sendall(encode_frame(seq, CMD["device_info"], payload))

    def check(body: bytes):
        # The device_info response must contain the Ferqon signature.
        if b"FERQON" not in body or b"revyrlabs" not in body:
            raise AssertionError("device_info missing Ferqon signature")

    expect_done(sock, buf, seq, CMD["device_info"], check)
    print("[OK] device_info")


def test_driver_info(sock: socket.socket, buf: bytearray):
    seq = 4
    payload = cmd_payload("driver_info")
    sock.sendall(encode_frame(seq, CMD["driver_info"], payload))

    def check(body: bytes):
        # Should list at least a few driver names as TLV data.
        if len(body) < 6:
            raise AssertionError("driver_info response too short")

    expect_done(sock, buf, seq, CMD["driver_info"], check)
    print("[OK] driver_info")


def test_gpio(sock: socket.socket, buf: bytearray):
    pin = 25
    value = 1

    # write
    seq = 5
    payload = cmd_payload("gpio_write", bytes([pin, value]))
    sock.sendall(encode_frame(seq, CMD["gpio_write"], payload))
    expect_done(sock, buf, seq, CMD["gpio_write"])
    print("[OK] gpio_write")

    # read back
    seq = 6
    payload = cmd_payload("gpio_read", bytes([pin]))
    sock.sendall(encode_frame(seq, CMD["gpio_read"], payload))

    def check(body: bytes):
        if len(body) < 1 or body[0] != value:
            raise AssertionError(f"gpio_read returned {body!r}, expected {value}")

    expect_done(sock, buf, seq, CMD["gpio_read"], check)
    print("[OK] gpio_read")


def test_adc(sock: socket.socket, buf: bytearray):
    seq = 7
    channel = 0  # maps to ADC pin 26 on pico
    payload = cmd_payload("adc_read", bytes([channel]))
    sock.sendall(encode_frame(seq, CMD["adc_read"], payload))

    def check(body: bytes):
        if len(body) < 2:
            raise AssertionError("adc_read response too short")
        mv = body[0] | (body[1] << 8)
        if not (0 < mv < 3300):
            raise AssertionError(f"adc_read returned {mv} mV, expected 0 < mv < 3300")

    expect_done(sock, buf, seq, CMD["adc_read"], check)
    print("[OK] adc_read")


def test_pulse(sock: socket.socket, buf: bytearray):
    pin = 25

    # Drive the pin high so the mock has a pulse to measure.
    seq = 8
    payload = cmd_payload("gpio_write", bytes([pin, 1]))
    sock.sendall(encode_frame(seq, CMD["gpio_write"], payload))
    expect_done(sock, buf, seq, CMD["gpio_write"])

    seq = 9
    timeout_ms = 1000
    min_us = 0
    max_us = 1_000_000
    pulse_payload = pack_u16_le(timeout_ms) + bytes([pin]) + pack_u32_le(min_us) + pack_u32_le(max_us)
    payload = cmd_payload("pulse_measure", pulse_payload)
    sock.sendall(encode_frame(seq, CMD["pulse_measure"], payload))

    def check(body: bytes):
        if len(body) < 4:
            raise AssertionError(f"pulse_measure returned {body!r}, expected 4-byte duration")
        us = (body[0] | (body[1] << 8) | (body[2] << 16) | (body[3] << 24))
        if not (min_us <= us <= max_us):
            raise AssertionError(f"pulse_measure returned {us} us, expected {min_us}-{max_us}")

    expect_done(sock, buf, seq, CMD["pulse_measure"], check)
    print("[OK] pulse_measure")


def main() -> int:
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else int(os.environ.get("FERQON_SIL_PORT", "3333"))

    if not CMD:
        print("ERROR: could not load command IDs from src/ferqon_commands.h", file=sys.stderr)
        return 1

    required = ["ping", "echo", "device_info", "driver_info", "gpio_read", "gpio_write", "adc_read", "pulse_measure"]
    missing = [c for c in required if c not in CMD]
    if missing:
        print(f"ERROR: missing command IDs: {missing}", file=sys.stderr)
        return 1

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(5.0)
        sock.connect((host, port))
        sock.settimeout(None)
        buf = bytearray()

        test_ping(sock, buf)
        test_echo(sock, buf)
        test_device_info(sock, buf)
        test_driver_info(sock, buf)
        test_gpio(sock, buf)
        test_adc(sock, buf)
        test_pulse(sock, buf)

    print("[PASS] SIL health-check suite passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
