"""Standalone MCU serial client for HIL testing.

Thin wrapper that provides the same :class:`McuClient` interface
used by the backend HIL module, but importable directly from the
device SDK without requiring the full backend package.

Usage::

    from serial_client import connect, Command, Expect
    from device_config import get_default_device_port, get_default_baudrate

    mcu = connect(get_default_device_port(), baudrate=get_default_baudrate())
    resp = mcu.send(Command.PING())
    print(resp.ok, resp.message)
    mcu.close()
"""

from __future__ import annotations

import sys
import threading
import time

from device_config import get_default_baudrate
from pathlib import Path
from typing import Any, Callable

# Ensure the ferqon_hw SDK is importable
_SDK_HW = Path(__file__).resolve().parent.parent / "hw_sdk" / "ferqon_hw"
if str(_SDK_HW) not in sys.path:
    sys.path.insert(0, str(_SDK_HW))

from ferqon_hw.serial_backend import (  # noqa: E402
    ConnLike,
    _decode_response,
    _encode_frame,
    open_serial,
    FerqonSerial,
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


def _encode(command: Command) -> bytes:
    """Encode a Command to bytes using the serial_backend."""
    # Not used anymore - we call send_command directly
    return b""


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
        # Use FerqonSerial for actual communication
        self._serial = FerqonSerial(port, baudrate, timeout_s=2.0)

    def send(self, command: Command, timeout: float = 2.0, retries: int = 1) -> RuntimeResponse:
        with self._lock:
            if self._closed:
                raise RuntimeError("McuClient is closed")

            # Map Command to FerqonSerial.call parameters
            ct = command.cmd_type
            kwargs = {}
            if ct == "driver_call":
                if command.driver is None or command.method is None:
                    raise ValueError("driver_call requires driver and method")
                kwargs["driver_name"] = command.driver
                kwargs["method"] = command.method
                if command.args:
                    # Parse args from bytes (format: "key=value;key=value")
                    args_str = command.args.decode("utf-8")
                    for pair in args_str.split(";"):
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            kwargs[k] = v
            elif ct == "echo":
                kwargs["payload"] = command.args.decode("utf-8")
            elif ct == "reboot_bootloader":
                ct = "reset"

            # Call FerqonSerial.call
            raw = self._serial.call(ct, **kwargs)
            return RuntimeResponse(
                cmd_id=int(raw.get("cmd_id", 0)),
                ok=bool(raw.get("ok", False)),
                ack=bool(raw.get("ack", False)),
                message=str(raw.get("message", "")),
            )

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._closed = True
                try:
                    self._conn.close()
                except Exception:
                    pass


def connect(port: str, baudrate: int | None = None, timeout: float = 2.0) -> McuClient:
    """Open a serial connection and return an McuClient."""
    if baudrate is None:
        baudrate = get_default_baudrate()
    conn = open_serial(port, baud=baudrate, timeout_s=timeout)
    return McuClient(conn, port=port, baudrate=baudrate)
