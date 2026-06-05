"""Standalone MCU serial client for HIL testing.

Thin wrapper that provides the same :class:`McuClient` interface
used by the backend HIL module, but importable directly from the
device SDK without requiring the full backend package.

Usage::

    from serial_client import connect, Command, Expect

    mcu = connect("/dev/ttyACM0", baudrate=115200)
    resp = mcu.send(Command.PING())
    print(resp.ok, resp.message)
    mcu.close()
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

# Ensure the ferqon_hw SDK is importable
_SDK_HW = Path(__file__).resolve().parent.parent / "hw_sdk" / "ferqon_hw"
if str(_SDK_HW) not in sys.path:
    sys.path.insert(0, str(_SDK_HW))

from ferqon_hw.serial_backend import (  # noqa: E402
    ConnLike,
    _CMD_IDS,
    _encode_driver_call,
    _encode_frame,
    _encode_simple_command,
    _send_frame,
    _wait_for_response,
    MSG_TYPE_REQUEST,
    PKT_REQUEST,
    open_serial,
)

# ---------------------------------------------------------------------------
# Re-export core types inline so users don't need the backend package
# ---------------------------------------------------------------------------

import re
from dataclasses import dataclass, field


class HilTimeoutError(Exception):
    """Raised when an expect() call exceeds its timeout."""


@dataclass(frozen=True)
class Command:
    cmd_type: str
    driver: str | None = None
    method: str | None = None
    args: bytes = field(default=b"", repr=False)

    @staticmethod
    def PING() -> "Command":
        return Command(cmd_type="ping")

    @staticmethod
    def DRIVER_INFO() -> "Command":
        return Command(cmd_type="driver_info")

    @staticmethod
    def DRIVER_CALL(driver: str, method: str, args: str = "") -> "Command":
        return Command(cmd_type="driver_call", driver=driver, method=method,
                       args=args.encode("utf-8") if args else b"")

    @staticmethod
    def RESET() -> "Command":
        return Command(cmd_type="reboot_bootloader")

    @staticmethod
    def ECHO(message: str) -> "Command":
        return Command(cmd_type="echo", args=message.encode("utf-8"))

    @staticmethod
    def SET_MODE(mode: str) -> "Command":
        return Command.DRIVER_CALL("config", "set_mode", mode)

    @staticmethod
    def READ_PIN(pin: int) -> "Command":
        return Command.DRIVER_CALL("gpio", "get", str(pin))

    @staticmethod
    def WRITE_PIN(pin: int, value: int) -> "Command":
        return Command.DRIVER_CALL("gpio", "set", f"{pin}={1 if value else 0}")


class Expect:
    @staticmethod
    def line_contains(text: str) -> Callable[[str], bool]:
        return lambda line: text in line

    @staticmethod
    def ok() -> Callable[[str], bool]:
        return lambda _: True

    @staticmethod
    def regex(pattern: str) -> Callable[[str], bool]:
        c = re.compile(pattern)
        return lambda line: c.search(line) is not None

    @staticmethod
    def exact(text: str) -> Callable[[str], bool]:
        return lambda line: line == text


@dataclass
class RuntimeResponse:
    cmd_id: int
    ok: bool
    ack: bool
    message: str


# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------


def _encode_echo(message: bytes) -> bytes:
    cmd_id = _CMD_IDS.get("echo")
    if cmd_id is None:
        raise RuntimeError("echo command missing from commands schema")
    payload = bytearray([cmd_id & 0xFF, (cmd_id >> 8) & 0xFF, PKT_REQUEST, 0])
    payload.extend(message)
    return _encode_frame(MSG_TYPE_REQUEST, bytes(payload), flags=0)


def _encode(command: Command) -> bytes:
    ct = command.cmd_type
    if ct == "driver_call":
        if command.driver is None or command.method is None:
            raise ValueError("driver_call requires driver and method")
        return _encode_driver_call(command.driver, command.method, command.args)
    if ct == "echo":
        return _encode_echo(command.args)
    return _encode_simple_command(ct)


# ---------------------------------------------------------------------------
# McuClient
# ---------------------------------------------------------------------------


class McuClient:
    """Thread-safe MCU communication handle."""

    def __init__(self, conn: ConnLike, port: str, baudrate: int) -> None:
        self._conn = conn
        self.port = port
        self.baudrate = baudrate
        self._lock = threading.Lock()
        self._closed = False

    def send(self, command: Command, timeout: float = 2.0, retries: int = 1) -> RuntimeResponse:
        with self._lock:
            if self._closed:
                raise RuntimeError("McuClient is closed")
            frame = _encode(command)
            raw = _send_frame(self._conn, frame, timeout_s=timeout, retries=retries)
            return RuntimeResponse(
                cmd_id=int(raw["cmd_id"]),
                ok=bool(raw["ok"]),
                ack=bool(raw["ack"]),
                message=str(raw["message"]),
            )

    def read_line(self, timeout: float = 2.0) -> RuntimeResponse:
        with self._lock:
            if self._closed:
                raise RuntimeError("McuClient is closed")
            raw = _wait_for_response(self._conn, timeout_s=timeout)
            return RuntimeResponse(
                cmd_id=int(raw["cmd_id"]),
                ok=bool(raw["ok"]),
                ack=bool(raw["ack"]),
                message=str(raw["message"]),
            )

    def expect(self, predicate: Callable[[str], bool], timeout: float = 5.0) -> RuntimeResponse:
        deadline = time.time() + timeout
        while time.time() < deadline:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            try:
                resp = self.read_line(timeout=min(remaining, 1.0))
                if predicate(resp.message):
                    return resp
            except RuntimeError:
                continue
        raise HilTimeoutError(f"expect() timed out after {timeout}s")

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._closed = True
                try:
                    self._conn.close()
                except Exception:
                    pass


def connect(port: str, baudrate: int = 115200, timeout: float = 2.0) -> McuClient:
    """Open a serial connection and return an McuClient."""
    conn = open_serial(port, baud=baudrate, timeout_s=timeout)
    return McuClient(conn, port=port, baudrate=baudrate)
