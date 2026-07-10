#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""Software Ferqon firmware emulator for CI and no-hardware testing.

Pure class with no import-time side effects. Implements the framed
Ferqon protocol and responds to core commands including the
Ferqon signature TLV (for detection testing).

Usage:
    from ferqon_emulator import FerqonEmulator

    # In-process mode (for selftest)
    emulator = FerqonEmulator()
    emulator.send_frame(frame_bytes) -> response_bytes

    # PTY-backed virtual serial port (for backend testing)
    emulator = FerqonEmulator(pty=True)
    port = emulator.get_port()  # e.g. /dev/pts/5
    # Use port like a real serial device
"""

from __future__ import annotations

import json
import logging
import os
import pty
import select
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Module-level constants (no hardcoded string fallbacks)
_DEFAULT_EMPTY_STRING = b""
_DEFAULT_ZERO = 0


# Load SSOT
def _load_commands_json() -> dict[str, Any]:
    """Load commands.json SSOT from the firmware protocol directory."""
    path = Path(__file__).resolve().parents[1] / "protocol" / "ssot" / "commands.json"
    if not path.exists():
        raise FileNotFoundError(f"commands.json SSOT not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_board_json(board: str) -> dict[str, Any]:
    """Load generated board.json for the requested board."""
    path = Path(__file__).resolve().parents[1] / "platforms" / board / "generated" / "board.json"
    if not path.exists():
        raise FileNotFoundError(f"Generated board.json not found for board '{board}': {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


_SPEC = _load_commands_json()

# Protocol constants from SSOT
_frame = _SPEC["frame"]
START_BYTE = _frame["start_byte"]
CRC_POLY = _frame["crc_poly"]
CRC_INIT = _frame["crc_init"]

_packet_types = _SPEC["packet_types"]
PKT_REQUEST = _packet_types["REQUEST"]
PKT_ACK = _packet_types["ACK"]
PKT_DONE = _packet_types["DONE"]
PKT_ERROR = _packet_types["ERROR"]

# Command IDs from SSOT
_commands = _SPEC["commands"]
CMD_PING = _commands["ping"]["id"]
CMD_ECHO = _commands["echo"]["id"]
CMD_DRIVER_INFO = _commands["driver_info"]["id"]
CMD_DEVICE_INFO = _commands["device_info"]["id"]
CMD_CAPABILITIES = _commands["capabilities"]["id"]
CMD_GPIO_READ = _commands["gpio_read"]["id"]
CMD_GPIO_WRITE = _commands["gpio_write"]["id"]

# TLV types from SSOT
_tlv_types = _SPEC["tlv_types"]
TLV_DEVICE_NAME = _tlv_types["DEVICE_NAME"]
TLV_MCU_TYPE = _tlv_types["MCU_TYPE"]
TLV_FIRMWARE_VERSION = _tlv_types["FIRMWARE_VERSION"]
TLV_PROTOCOL_VERSION = _tlv_types["PROTOCOL_VERSION"]
TLV_BUILD_TIMESTAMP = _tlv_types["BUILD_TIMESTAMP"]
TLV_FREE_RAM = _tlv_types["FREE_RAM"]
TLV_UPTIME_MS = _tlv_types["UPTIME_MS"]
TLV_FERQON_SIGNATURE = _tlv_types["FERQON_SIGNATURE"]
TLV_DRIVER = _tlv_types["DRIVER"]
TLV_COMMAND = _tlv_types["COMMAND"]
TLV_VERSION = _tlv_types["VERSION"]

# Signature configuration from SSOT
_signature_config = _SPEC["ferqon_signature"]
FERQON_SIGNATURE_MAGIC = _signature_config["magic"].encode("utf-8")
FERQON_SIGNATURE_VENDOR = _signature_config["vendor"].encode("utf-8")
FERQON_SIGNATURE_CAP_VERSION = _signature_config["capability_version"]

log = logging.getLogger(__name__)


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
            crc = crc & 0xFFFF
    return crc


def build_frame(seq: int, cmd_id: int, payload: bytes) -> bytes:
    """Build a complete Ferqon protocol frame."""
    header = bytes([seq, cmd_id, len(payload)])
    crc_data = header + payload
    crc = crc16_ccitt_false(crc_data)
    return bytes([START_BYTE]) + crc_data + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def parse_frame(data: bytes) -> tuple[int, int, bytes] | None:
    """Parse a frame, returning (seq, cmd_id, payload) or None if invalid."""
    if len(data) < 6:
        return None
    if data[0] != START_BYTE:
        return None

    seq = data[1]
    cmd_id = data[2]
    payload_len = data[3]
    payload = data[4 : 4 + payload_len]
    crc_lo = data[4 + payload_len]
    crc_hi = data[5 + payload_len]
    recv_crc = crc_lo | (crc_hi << 8)

    header = bytes([seq, cmd_id, payload_len])
    calc_crc = crc16_ccitt_false(header + payload)

    if recv_crc != calc_crc:
        return None

    return seq, cmd_id, payload


@dataclass
class EmulatorState:
    """Mutable state for the emulator (kept separate for clean reset)."""

    gpio_pins: dict[int, int]  # pin -> value (0 or 1)
    uptime_ms: int = 0
    start_time: float = 0.0


class FerqonEmulator:
    """Software Ferqon firmware emulator.

    No import-time side effects. Must be explicitly started/stopped
    when using PTY mode. In-process mode is stateless per call.
    """

    def __init__(self, pty: bool = False, board: str = "pico"):
        """Initialize emulator.

        Args:
            pty: If True, create a PTY-backed virtual serial port.
                 If False, operate in in-process mode (send_frame method).
            board: Board name; used to load generated board.json.
        """
        self._pty = pty
        self._master_fd: int | None = None
        self._slave_fd: int | None = None
        self._pty_path: str | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._board = _load_board_json(board)
        self._state = EmulatorState(gpio_pins={i: 0 for i in range(self._board["max_gpio"] + 1)})
        self._state.start_time = time.time()

    def _update_uptime(self) -> None:
        """Update uptime counter."""
        with self._lock:
            self._state.uptime_ms = int((time.time() - self._state.start_time) * 1000)

    def _build_tlv(self, tlv_type: int, value: bytes) -> bytes:
        """Build a TLV triplet."""
        return bytes([tlv_type, len(value)]) + value

    def _build_u32_tlv(self, tlv_type: int, value: int) -> bytes:
        """Build a TLV with a u32 value (little-endian)."""
        return bytes([tlv_type, 4]) + value.to_bytes(4, byteorder="little")

    def _handle_ping(self, seq: int, payload: bytes) -> bytes:
        """Handle PING command."""
        return build_frame(seq, CMD_PING, bytes([PKT_DONE]))

    def _handle_echo(self, seq: int, payload: bytes) -> bytes:
        """Handle ECHO command."""
        # Echo back the payload after the packet type byte
        echo_payload = bytes([PKT_DONE]) + payload[1:] if payload else bytes([PKT_DONE])
        return build_frame(seq, CMD_ECHO, echo_payload)

    def _handle_driver_info(self, seq: int, payload: bytes) -> bytes:
        """Handle DRIVER_INFO command."""
        # Build TLV response listing drivers
        response = bytearray()
        # Driver: gpio
        response.extend(self._build_tlv(TLV_DRIVER, b"gpio"))
        # Command: GPIO_WRITE
        response.extend(bytes([TLV_COMMAND, 1 + 5, CMD_GPIO_WRITE]))
        response.extend(b"gpio")
        # Version from SSOT
        major, minor, patch = (int(v) for v in _SPEC["version"].split(".")[:3])
        response.extend(bytes([TLV_VERSION, 3, major, minor, patch]))
        return build_frame(seq, CMD_DRIVER_INFO, bytes(response))

    def _handle_device_info(self, seq: int, payload: bytes) -> bytes:
        """Handle DEVICE_INFO command with Ferqon signature."""
        self._update_uptime()
        response = bytearray()

        # Standard TLVs derived from generated board config and SSOT
        response.extend(self._build_tlv(TLV_DEVICE_NAME, self._board["board"].encode("utf-8")))
        response.extend(self._build_tlv(TLV_MCU_TYPE, self._board["mcu"].encode("utf-8")))
        version_bytes = _SPEC["version"].encode("utf-8")
        response.extend(self._build_tlv(TLV_FIRMWARE_VERSION, version_bytes))
        response.extend(self._build_tlv(TLV_PROTOCOL_VERSION, version_bytes))
        response.extend(self._build_u32_tlv(TLV_BUILD_TIMESTAMP, int(time.time())))
        response.extend(self._build_u32_tlv(TLV_FREE_RAM, self._board["ram_size_bytes"]))
        response.extend(self._build_u32_tlv(TLV_UPTIME_MS, self._state.uptime_ms))

        # Ferqon signature TLV (for detection)
        signature = (
            FERQON_SIGNATURE_MAGIC
            + FERQON_SIGNATURE_VENDOR
            + bytes([FERQON_SIGNATURE_CAP_VERSION])
        )
        response.extend(self._build_tlv(TLV_FERQON_SIGNATURE, signature))

        return build_frame(seq, CMD_DEVICE_INFO, bytes(response))

    def _handle_capabilities(self, seq: int, payload: bytes) -> bytes:
        """Handle CAPABILITIES command."""
        caps_json = json.dumps(
            {"mcu": self._board["mcu"], "device_name": self._board["board"]},
            separators=(",", ":"),
        ).encode("utf-8")
        caps_payload = bytes([PKT_DONE]) + caps_json
        return build_frame(seq, CMD_CAPABILITIES, caps_payload)

    def _handle_gpio_read(self, seq: int, payload: bytes) -> bytes:
        """Handle GPIO_READ command."""
        if len(payload) < 2:
            # Malformed, return error
            error_payload = bytes([PKT_ERROR, 2, 2, 0, 0])  # INVALID_PARAMS
            return build_frame(seq, CMD_GPIO_READ, error_payload)

        pin = payload[1]  # Skip packet type byte
        with self._lock:
            value = self._state.gpio_pins.get(pin, 0)

        done_payload = bytes([PKT_DONE, value])
        return build_frame(seq, CMD_GPIO_READ, done_payload)

    def _handle_gpio_write(self, seq: int, payload: bytes) -> bytes:
        """Handle GPIO_WRITE command."""
        if len(payload) < 3:
            # Malformed, return error
            error_payload = bytes([PKT_ERROR, 2, 2, 0, 0])  # INVALID_PARAMS
            return build_frame(seq, CMD_GPIO_WRITE, error_payload)

        pin = payload[1]
        value = payload[2]

        with self._lock:
            self._state.gpio_pins[pin] = value

        return build_frame(seq, CMD_GPIO_WRITE, bytes([PKT_DONE]))

    def _handle_frame(self, frame: bytes) -> bytes:
        """Process an incoming frame and return response."""
        parsed = parse_frame(frame)
        if parsed is None:
            # Invalid frame, ignore or send error
            return _DEFAULT_EMPTY_STRING

        seq, cmd_id, payload = parsed

        # Strip packet type byte if present
        if payload and payload[0] == PKT_REQUEST:
            payload = payload[1:]

        handlers = {
            CMD_PING: self._handle_ping,
            CMD_ECHO: self._handle_echo,
            CMD_DRIVER_INFO: self._handle_driver_info,
            CMD_DEVICE_INFO: self._handle_device_info,
            CMD_CAPABILITIES: self._handle_capabilities,
            CMD_GPIO_READ: self._handle_gpio_read,
            CMD_GPIO_WRITE: self._handle_gpio_write,
        }

        handler = handlers.get(cmd_id)
        if handler:
            return handler(seq, payload)
        else:
            # Unknown command, return error
            error_payload = bytes([PKT_ERROR, 1, 2, 0, 0])  # INVALID_COMMAND
            return build_frame(seq, cmd_id, error_payload)

    def send_frame(self, frame: bytes) -> bytes:
        """Send a frame and get response (in-process mode).

        This is a synchronous call for direct testing without PTY.
        """
        return self._handle_frame(frame)

    def _pty_loop(self) -> None:
        """PTY reader loop (runs in background thread)."""
        log.info("FerqonEmulator: PTY loop started on %s", self._pty_path)

        while self._running and self._master_fd is not None:
            try:
                # Wait for data with timeout
                rlist, _, _ = select.select([self._master_fd], [], [], 0.1)

                if self._master_fd in rlist:
                    # Read data
                    try:
                        data = os.read(self._master_fd, 1024)
                    except OSError:
                        break

                    if not data:
                        break

                    # Process frame(s) and send response(s)
                    # For simplicity, assume one frame per read
                    response = self._handle_frame(data)
                    if response:
                        try:
                            os.write(self._master_fd, response)
                        except OSError:
                            break

            except Exception as exc:
                log.warning("FerqonEmulator: PTY loop error: %s", exc)
                break

        log.info("FerqonEmulator: PTY loop stopped")

    def start(self) -> str:
        """Start the PTY and return the port path.

        Only valid when pty=True was passed to __init__.

        Returns:
            Path to the PTY slave device (e.g., /dev/pts/5)
        """
        if not self._pty:
            raise RuntimeError("PTY mode not enabled")

        if self._running:
            return self._pty_path or ""

        self._master_fd, self._slave_fd = pty.openpty()
        self._pty_path = os.ttyname(self._slave_fd)
        self._running = True

        self._thread = threading.Thread(target=self._pty_loop, daemon=True)
        self._thread.start()

        log.info("FerqonEmulator: started on %s", self._pty_path)
        return self._pty_path

    def stop(self) -> None:
        """Stop the PTY and cleanup."""
        if not self._running:
            return

        self._running = False

        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None

        if self._slave_fd is not None:
            try:
                os.close(self._slave_fd)
            except OSError:
                pass
            self._slave_fd = None

        self._pty_path = None
        log.info("FerqonEmulator: stopped")

    def get_port(self) -> str | None:
        """Get the PTY port path (if running)."""
        return self._pty_path

    def reset_state(self) -> None:
        """Reset emulator state (GPIO pins, uptime, etc.)."""
        with self._lock:
            self._state.gpio_pins = {i: 0 for i in range(30)}
            self._state.uptime_ms = 0
            self._state.start_time = time.time()


if __name__ == "__main__":
    # Standalone test: run emulator in PTY mode
    import argparse

    parser = argparse.ArgumentParser(description="Ferqon firmware emulator")
    parser.add_argument("--pty", action="store_true", help="Run in PTY mode")
    args = parser.parse_args()

    if args.pty:
        emu = FerqonEmulator(pty=True)
        port = emu.start()
        print(f"Emulator running on: {port}")
        print("Press Ctrl+C to stop")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            emu.stop()
    else:
        # In-process test
        emu = FerqonEmulator()
        print("Testing in-process mode...")

        # Test ping
        ping_frame = build_frame(seq=1, cmd_id=CMD_PING, payload=bytes([PKT_REQUEST]))
        resp = emu.send_frame(ping_frame)
        print(f"PING response: {resp.hex()}")

        # Test device_info
        info_frame = build_frame(seq=2, cmd_id=CMD_DEVICE_INFO, payload=b"")
        resp = emu.send_frame(info_frame)
        print(f"DEVICE_INFO response: {resp.hex()}")

        print("In-process test complete")
