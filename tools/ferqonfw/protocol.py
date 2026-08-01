#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""Canonical Ferqon serial protocol SDK.

This module is the single Python source of truth for the Ferqon wire protocol:
framing, CRC, packet types, command encoding, TLV parsing, and high-level
transport helpers.  Constants are generated from
``firmware/protocol/ssot/commands.json`` and live in ``ferqon_hw._generated``;
this module performs no file I/O at import time.

Frame format:
    [START=0xAB][SEQ:u8][CMD:u8][LEN:u8][PAYLOAD: LEN bytes][CRC_LO][CRC_HI]

CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection, no XOR-out)
covers SEQ..last payload byte.
"""

from __future__ import annotations

import logging
import socket
import time
from dataclasses import dataclass
from typing import Any, Protocol

from ._generated import (
    CMD_ADC_EXPECT,
    CMD_ADC_READ,
    CMD_CAPABILITIES,
    CMD_DEVICE_INFO,
    CMD_DRIVER_CALL,
    CMD_DRIVER_INFO,
    CMD_ECHO,
    CMD_GPIO_READ,
    CMD_GPIO_WRITE,
    CMD_PIN_MODE,
    CMD_PING,
    CMD_PULSE_MEASURE,
    CMD_RESET,
    CMD_SET_DEBUG_LEVEL,
    CMD_UART_EXPECT,
    CMD_UART_SEND,
    CRC_INIT,
    CRC_POLY,
    COMMANDS,
    COMMAND_PARAMS,
    DRIVER_METHOD_MAP,
    ERROR_CODES,
    FERQON_SIGNATURE_CAPABILITY_VERSION,
    FERQON_SIGNATURE_MAGIC,
    FERQON_SIGNATURE_VENDOR,
    FRAME_ASSEMBLY_TIMEOUT_MS,
    FRAME_OVERHEAD,
    GPIO_MODES,
    INFO_COMMAND_IDS,
    INTER_BYTE_TIMEOUT_MS,
    MAX_FRAME_BYTES,
    MAX_PAYLOAD_BYTES,
    PACKET_TYPES,
    PKT_ACK,
    PKT_DONE,
    PKT_ERROR,
    PKT_EVENT,
    PKT_HEARTBEAT,
    PKT_LOG,
    PKT_REQUEST,
    PROTOCOL_VERSION,
    SEQ_UNSOLICITED,
    START_BYTE,
    TLV_BUILD_TIMESTAMP,
    TLV_COMMAND,
    TLV_DEVICE_NAME,
    TLV_DRIVER,
    TLV_FERQON_SIGNATURE,
    TLV_FIRMWARE_VERSION,
    TLV_FREE_RAM,
    TLV_MCU_TYPE,
    TLV_METHOD,
    TLV_PROTOCOL_VERSION,
    TLV_UPTIME_MS,
    TLV_VERSION,
)

DEFAULT_SERIAL_BAUD = 115200
DEFAULT_SERIAL_TIMEOUT_S = 2.0
DEFAULT_BAUD = DEFAULT_SERIAL_BAUD
DEFAULT_TIMEOUT_S = DEFAULT_SERIAL_TIMEOUT_S

_logger = logging.getLogger("ferqonfw.protocol")


# Optional runtime dependency: pyserial is only needed for physical serial ports.
try:
    import serial  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - only hits runtime without pyserial
    serial = None


class ConnLike(Protocol):
    """Minimal connection protocol used by the SDK."""

    def write(self, data: bytes) -> int: ...
    def read(self, size: int = 1) -> bytes: ...
    def close(self) -> None: ...


@dataclass(frozen=True)
class DecodedFrame:
    """A successfully decoded frame.

    ``pkt_type`` is the first byte of the payload (0 when the payload is empty).
    The ``__iter__`` method yields ``(seq, cmd_id, pkt_type, payload)`` so
    existing tuple-unpacking consumers keep working.
    """

    seq: int
    cmd_id: int
    pkt_type: int
    payload: bytes

    def __iter__(self):
        return iter((self.seq, self.cmd_id, self.pkt_type, self.payload))


@dataclass(frozen=True)
class DeviceIdentity:
    """Parsed device_info response."""

    device_name: str
    mcu_type: str
    firmware_version: str
    protocol_version: str
    has_signature: bool = False
    signature_vendor: str = ""
    signature_cap_version: int = 0

    @property
    def classification(self) -> str:
        if self.has_signature:
            return "ferqon_identified"
        if self.device_name and self.mcu_type and self.firmware_version and self.protocol_version:
            return "ferqon_compatible"
        return "serial_unknown"


class FerqonError(Exception):
    """Base exception for protocol errors."""


class FerqonTimeoutError(FerqonError):
    """Raised when a response is not received within the configured timeout."""


# ---------------------------------------------------------------------------
# CRC / frame codec
# ---------------------------------------------------------------------------


def crc16_ccitt_false(data: bytes, init: int = CRC_INIT) -> int:
    """CRC-16/CCITT-FALSE (poly=0x1021, init=0xFFFF, no reflect, no xorout)."""
    crc = init & 0xFFFF
    for byte in data:
        crc ^= (byte & 0xFF) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ CRC_POLY) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF


# Backwards-compatible alias
crc16_ccitt = crc16_ccitt_false


def encode_frame(seq: int, cmd_id: int, payload: bytes = b"") -> bytes:
    """Encode a frame ready for the wire."""
    if not 0 <= seq <= 255:
        raise ValueError(f"seq out of range: {seq}")
    if not 0 <= cmd_id <= 255:
        raise ValueError(f"cmd_id out of range: {cmd_id}")
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError(f"payload too large: {len(payload)} > {MAX_PAYLOAD_BYTES}")

    body = bytearray()
    body.append(seq & 0xFF)
    body.append(cmd_id & 0xFF)
    body.append(len(payload) & 0xFF)
    body.extend(payload)
    crc = crc16_ccitt_false(bytes(body))

    out = bytearray()
    out.append(START_BYTE)
    out.extend(body)
    out.append(crc & 0xFF)
    out.append((crc >> 8) & 0xFF)
    return bytes(out)


class FrameDecoder:
    """Incremental, resync-capable frame decoder."""

    def __init__(self) -> None:
        self._buf = bytearray()

    def reset(self) -> None:
        self._buf.clear()

    def feed(self, data: bytes) -> list[DecodedFrame]:
        if data:
            self._buf.extend(data)
        out: list[DecodedFrame] = []

        while True:
            if not self._buf:
                break

            if self._buf[0] != START_BYTE:
                idx = self._buf.find(START_BYTE)
                if idx == -1:
                    self._buf.clear()
                    break
                del self._buf[:idx]
                continue

            if len(self._buf) < FRAME_OVERHEAD:
                break

            seq = self._buf[1]
            cmd_id = self._buf[2]
            payload_len = self._buf[3]

            if payload_len > MAX_PAYLOAD_BYTES:
                del self._buf[0]
                continue

            total = FRAME_OVERHEAD + payload_len
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
                out.append(DecodedFrame(seq=seq, cmd_id=cmd_id, pkt_type=pkt_type, payload=payload))
                del self._buf[:total]
            else:
                del self._buf[0]

        return out


# ---------------------------------------------------------------------------
# Packet / response decoding
# ---------------------------------------------------------------------------


def decode_response(payload: bytes) -> dict[str, Any]:
    """Decode a response payload: [pkt_type][body...]."""
    if len(payload) < 1:
        raise ValueError("response payload too short")

    pkt_type = payload[0]
    body = payload[1:]

    if pkt_type == PKT_DONE:
        return {"ok": True, "pkt_type": pkt_type, "body": body}
    if pkt_type == PKT_ACK:
        return {"ok": True, "pkt_type": pkt_type, "body": body}
    if pkt_type == PKT_ERROR:
        if len(body) < 4:
            return {"ok": False, "pkt_type": pkt_type, "body": body}
        return {
            "ok": False,
            "pkt_type": pkt_type,
            "code": body[0],
            "category": body[1],
            "retryable": bool(body[2]),
            "ctx": body[3],
            "detail": body[4:].decode("utf-8", errors="replace"),
        }
    if pkt_type == PKT_HEARTBEAT:
        if len(body) < 6:
            return {"ok": True, "pkt_type": pkt_type, "body": body}
        uptime = int.from_bytes(body[1:5], "little")
        return {
            "ok": True,
            "pkt_type": pkt_type,
            "state": body[0],
            "uptime_ms": uptime,
            "flags": body[5],
        }
    if pkt_type == PKT_EVENT:
        if len(body) < 2:
            return {"ok": True, "pkt_type": pkt_type, "body": body}
        event_id = int.from_bytes(body[:2], "little")
        return {
            "ok": True,
            "pkt_type": pkt_type,
            "event_id": event_id,
            "event_body": body[2:],
        }
    if pkt_type == PKT_LOG:
        return {
            "ok": True,
            "pkt_type": pkt_type,
            "log_text": body.decode("utf-8", errors="replace"),
        }
    return {"ok": False, "pkt_type": pkt_type, "body": body}


# ---------------------------------------------------------------------------
# TLV helpers
# ---------------------------------------------------------------------------


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


def parse_device_info(body: bytes) -> DeviceIdentity:
    """Parse a device_info response body (TLV-encoded)."""
    tlvs = parse_tlv(body)
    device_name = parse_string_tlv(tlvs, TLV_DEVICE_NAME)
    mcu_type = parse_string_tlv(tlvs, TLV_MCU_TYPE)
    fw_version = parse_string_tlv(tlvs, TLV_FIRMWARE_VERSION)
    proto_version = parse_string_tlv(tlvs, TLV_PROTOCOL_VERSION)

    sig_bytes = tlvs.get(TLV_FERQON_SIGNATURE, b"")
    magic_bytes = FERQON_SIGNATURE_MAGIC.encode("utf-8")
    has_sig = sig_bytes.startswith(magic_bytes)
    vendor = ""
    cap_version = 0
    if has_sig and len(sig_bytes) > len(magic_bytes):
        vendor = sig_bytes[len(magic_bytes) : -1].decode("utf-8", errors="replace")
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


# ---------------------------------------------------------------------------
# Command payload builders
# ---------------------------------------------------------------------------


def _to_bool_string(value: Any) -> str:
    if isinstance(value, str):
        return "1" if value.upper() in {"1", "TRUE", "HIGH", "ON", "YES"} else "0"
    return "1" if value else "0"


def _to_gpio_mode_string(value: Any) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        mode = GPIO_MODES.get(value.upper())
        if mode is not None:
            return str(mode)
    return str(int(value))


def _encode_arg_value(arg_type: str, value: Any) -> str:
    """Encode a single driver_call argument value as a decimal string."""
    if arg_type == "bool_high_low":
        return _to_bool_string(value)
    if arg_type == "gpio_mode":
        return _to_gpio_mode_string(value)
    if arg_type == "utf8_tail":
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return str(value)
    if arg_type.endswith("_optional"):
        if value is None or value == "":
            return ""
        base = arg_type[: -len("_optional")]
        return _encode_arg_value(base, value)
    # u8, u16_le, u32_le and variants all become decimal integers.
    return str(int(value))


def encode_driver_call_args(driver: str, method: str, kwargs: dict[str, Any]) -> bytes:
    """Encode driver_call kwargs into the args byte string.

    Uses the generated DRIVER_METHOD_MAP for ordering and type conversion.
    Unknown (driver, method) pairs fall back to a sorted ``key=value`` string.
    """
    mapping = DRIVER_METHOD_MAP.get((driver, method))
    if mapping is None:
        parts = [f"{k}={v}" for k, v in kwargs.items()]
        return ";".join(parts).encode("utf-8") if parts else b""

    arg_map = mapping.get("arg_map", {})
    parts: list[str] = []
    for arg_name, arg_type in arg_map.items():
        if arg_name not in kwargs:
            if arg_type.endswith("_optional"):
                continue
            raise ValueError(f"missing required argument '{arg_name}' for {driver}.{method}")
        encoded = _encode_arg_value(arg_type, kwargs[arg_name])
        if encoded == "":
            continue
        parts.append(f"{arg_name}={encoded}")
    return ";".join(parts).encode("utf-8") if parts else b""


def encode_driver_call_payload(
    driver: str,
    method: str,
    args: bytes | str | None = None,
    **kwargs: Any,
) -> bytes:
    """Build the payload for a native ``driver_call`` command.

    Format: [PKT_REQUEST][driver_len][driver...][method_len][method...][args...]
    """
    if args is None:
        args_bytes = encode_driver_call_args(driver, method, kwargs)
    elif isinstance(args, str):
        args_bytes = args.encode("utf-8")
    else:
        args_bytes = args

    driver_bytes = driver.encode("utf-8")
    method_bytes = method.encode("utf-8")
    return (
        bytes([PKT_REQUEST, len(driver_bytes)])
        + driver_bytes
        + bytes([len(method_bytes)])
        + method_bytes
        + args_bytes
    )


def _encode_direct_param(param_type: str, value: Any) -> bytes:
    if param_type in {"u8"}:
        if isinstance(value, bool):
            return int(value).to_bytes(1, "little")
        if isinstance(value, str):
            upper = value.upper()
            if upper in GPIO_MODES:
                return GPIO_MODES[upper].to_bytes(1, "little")
            if upper in {"HIGH", "ON", "1", "TRUE"}:
                return (1).to_bytes(1, "little")
            if upper in {"LOW", "OFF", "0", "FALSE"}:
                return (0).to_bytes(1, "little")
        return int(value).to_bytes(1, "little")
    if param_type in {"u16"}:
        return int(value).to_bytes(2, "little")
    if param_type in {"u32"}:
        return int(value).to_bytes(4, "little")
    if param_type == "bytes":
        if isinstance(value, (bytes, bytearray)):
            return bytes(value)
        if isinstance(value, list):
            return bytes(value)
        if isinstance(value, str):
            return value.encode("utf-8")
        raise TypeError(f"cannot encode {type(value)} as bytes")
    if param_type == "string":
        if isinstance(value, bytes):
            return value
        return str(value).encode("utf-8")
    raise ValueError(f"unsupported parameter type: {param_type}")


def encode_simple_command_payload(cmd_name: str, **kwargs: Any) -> bytes:
    """Build the payload body for a native command (frame payload, no header/CRC)."""
    cmd_id = COMMANDS.get(cmd_name)
    if cmd_id is None:
        raise ValueError(f"Unknown command: {cmd_name}")

    if cmd_name == "driver_call":
        driver_name = kwargs.get("driver_name", "")
        method_name = kwargs.get("method", "")
        args = kwargs.get("args")
        remaining = {k: v for k, v in kwargs.items() if k not in {"driver_name", "method", "args"}}
        return encode_driver_call_payload(driver_name, method_name, args, **remaining)

    params = COMMAND_PARAMS.get(cmd_name, [])
    if cmd_id in INFO_COMMAND_IDS:
        body = b""
    else:
        body = bytes([PKT_REQUEST])

    for param in params:
        name = param["name"]
        ptype = param["type"]
        if name not in kwargs:
            raise ValueError(f"missing required argument '{name}' for {cmd_name}")
        body += _encode_direct_param(ptype, kwargs[name])

    return body


def encode_simple_command(cmd_name: str, seq: int = 1, **kwargs: Any) -> bytes:
    """Build a complete frame for a native command."""
    cmd_id = COMMANDS.get(cmd_name)
    if cmd_id is None:
        raise ValueError(f"Unknown command: {cmd_name}")
    payload = encode_simple_command_payload(cmd_name, **kwargs)
    return encode_frame(seq, cmd_id, payload)


def encode_driver_call(
    driver: str,
    method: str,
    args: bytes | str | None = None,
    seq: int = 1,
    **kwargs: Any,
) -> bytes:
    """Build a complete ``driver_call`` frame."""
    payload = encode_driver_call_payload(driver, method, args, **kwargs)
    return encode_frame(seq, CMD_DRIVER_CALL, payload)


# ---------------------------------------------------------------------------
# Low-level serial transport
# ---------------------------------------------------------------------------


@dataclass
class _TcpConn:
    sock: socket.socket
    file: Any

    def write(self, data: bytes) -> int:
        self.file.write(data)
        self.file.flush()
        return len(data)

    def read(self, size: int = 1) -> bytes:
        return self.file.read(size)

    def close(self) -> None:
        self.file.close()
        self.sock.close()


def _open_serial_impl(
    port: str,
    baud: int = 115200,
    timeout_s: float = 2.0,
) -> ConnLike:
    """Open a connection to a Pico-like command endpoint.

    Supported ports:
      - ``/dev/tty*`` or ``COM*`` : physical serial via pyserial
      - ``tcp://host:port``      : TCP socket
    """
    if port.startswith("tcp://"):
        addr = port[len("tcp://") :]
        host, raw_port = addr.split(":", 1)
        sock = socket.create_connection((host, int(raw_port)), timeout=timeout_s)
        sock.settimeout(None)
        return _TcpConn(sock=sock, file=sock.makefile("rwb", buffering=0))

    if serial is None:
        raise RuntimeError("pyserial is required for non-tcp serial ports")
    return serial.Serial(port=port, baudrate=baud, timeout=timeout_s)


def open_serial(port: str, baud: int = 115200, timeout_s: float = 2.0) -> ConnLike:
    """Open a serial connection and set it as the global module-level connection."""
    global _global_serial
    conn = _open_serial_impl(port, baud, timeout_s)
    _global_serial = FerqonSerial.from_conn(conn)
    return conn


class SerialTransport:
    """Production serial transport using pyserial or a TCP stand-in."""

    DEFAULT_BAUD: int = 115200
    DEFAULT_TIMEOUT_S: float = 2.0
    DEFAULT_CONNECT_DELAY_MS: int = 0

    def __init__(
        self,
        port: str,
        baudrate: int = DEFAULT_BAUD,
        timeout: float | None = None,
        connect_delay_ms: int | None = None,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT_S
        self.connect_delay_ms = (
            connect_delay_ms if connect_delay_ms is not None else self.DEFAULT_CONNECT_DELAY_MS
        )
        self._conn: ConnLike | None = None
        self._decoder = FrameDecoder()

    def connect(self) -> None:
        self._conn = _open_serial_impl(self.port, self.baudrate, self.timeout)
        if self.connect_delay_ms:
            time.sleep(self.connect_delay_ms / 1000.0)

    def send_frame(self, frame: bytes, timeout_s: float = 2.0) -> dict[str, Any]:
        """Send a frame and return a parsed response dict."""
        if self._conn is None:
            raise RuntimeError("Transport not connected")
        self._conn.write(frame)
        if hasattr(self._conn, "flush"):
            self._conn.flush()

        deadline = time.time() + timeout_s
        response_types = {PKT_DONE, PKT_ACK, PKT_ERROR}
        while time.time() < deadline:
            chunk = self._conn.read(1)
            if not chunk:
                continue
            for dec_frame in self._decoder.feed(chunk):
                if dec_frame.seq == SEQ_UNSOLICITED:
                    # Heartbeat / log / event; keep waiting for the real response
                    continue
                pkt_type = dec_frame.pkt_type
                if pkt_type not in response_types:
                    continue
                payload = dec_frame.payload
                body = payload[1:] if payload else b""
                if pkt_type == PKT_ERROR:
                    return {"ok": False, "error": "error response", "pkt_type": pkt_type, "body": body}
                return {"ok": True, "pkt_type": pkt_type, "body": body}

        return {"ok": False, "error": "timeout"}

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def __enter__(self) -> SerialTransport:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


# ---------------------------------------------------------------------------
# High-level FerqonSerial API
# ---------------------------------------------------------------------------


class FerqonSerial:
    """High-level serial client for Ferqon devices."""

    DEFAULT_SERIAL_BAUD: int = 115200
    DEFAULT_SERIAL_TIMEOUT_S: float = 2.0

    def __init__(
        self,
        port: str,
        baud: int = DEFAULT_SERIAL_BAUD,
        timeout_s: float = DEFAULT_SERIAL_TIMEOUT_S,
    ) -> None:
        self.port = port
        self.baud = baud
        self.timeout_s = timeout_s
        self._conn = _open_serial_impl(port, baud, timeout_s)
        self._decoder = FrameDecoder()
        self._seq = 1

    @classmethod
    def from_conn(cls, conn: ConnLike, timeout_s: float = DEFAULT_SERIAL_TIMEOUT_S) -> FerqonSerial:
        """Wrap an existing connection without opening a second serial port."""
        instance = cls.__new__(cls)
        instance._conn = conn
        instance._decoder = FrameDecoder()
        instance._seq = 1
        instance.timeout_s = timeout_s
        return instance

    def close(self) -> None:
        self._conn.close()

    def _send_frame(self, cmd_id: int, payload: bytes = b"") -> None:
        frame = encode_frame(self._seq, cmd_id, payload)
        self._conn.write(frame)
        self._seq = (self._seq % 255) + 1  # Wrap 1..255

    def _recv_frame(self, timeout_s: float | None = None) -> DecodedFrame:
        timeout_s = timeout_s if timeout_s is not None else self.timeout_s
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            data = self._conn.read(1)
            if not data:
                continue
            for frame in self._decoder.feed(data):
                if frame.seq != SEQ_UNSOLICITED:
                    return frame
        raise FerqonTimeoutError("timeout waiting for response")

    def call(self, method: str, **kwargs: Any) -> dict[str, Any]:
        """Call a command or driver method by name.

        ``method`` may be a native command name (``"ping"``, ``"gpio_read"``) or a
        dotted driver method shorthand (``"hil.io_set"``).
        """
        if "." in method:
            driver_name, method_name = method.split(".", 1)
            kwargs.setdefault("driver_name", driver_name)
            kwargs.setdefault("method", method_name)
            cmd_name = "driver_call"
        else:
            cmd_name = method

        cmd_id = COMMANDS.get(cmd_name)
        if cmd_id is None:
            raise ValueError(f"Unknown command: {cmd_name}")

        payload = encode_simple_command_payload(cmd_name, **kwargs)
        self._send_frame(cmd_id, payload)
        frame = self._recv_frame()
        return decode_response(frame.payload)

    def __enter__(self) -> FerqonSerial:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Module-level helpers (backward compatibility)
# ---------------------------------------------------------------------------

_global_serial: FerqonSerial | None = None


def close() -> None:
    """Close the global serial connection created by :func:`open_serial`."""
    global _global_serial
    if _global_serial:
        _global_serial.close()
        _global_serial = None


def _resolve_client(conn: ConnLike | None) -> FerqonSerial:
    if conn is None:
        if _global_serial is None:
            raise RuntimeError("No serial connection open. Call open_serial first.")
        return _global_serial
    if isinstance(conn, FerqonSerial):
        return conn
    return FerqonSerial.from_conn(conn)


def configure_pin(conn: ConnLike | None, pin: int, mode: str | int) -> dict[str, Any]:
    """Configure a pin mode.  ``conn`` may be an explicit connection or ``None`` to use the global one."""
    return _resolve_client(conn).call("pin_mode", pin=pin, mode=mode)


def read_pin(conn: ConnLike | None, pin: int) -> dict[str, Any]:
    """Read a pin value."""
    return _resolve_client(conn).call("gpio_read", pin=pin)


def write_pin(conn: ConnLike | None, pin: int, level: bool | int) -> dict[str, Any]:
    """Write a pin value."""
    return _resolve_client(conn).call("gpio_write", pin=pin, value=level)


def send_command(conn: ConnLike | None, method: str, **kwargs: Any) -> dict[str, Any]:
    """Send a command to the device."""
    return _resolve_client(conn).call(method, **kwargs)





__all__ = [
    "ConnLike",
    "DecodedFrame",
    "DeviceIdentity",
    "FerqonError",
    "FerqonTimeoutError",
    "FerqonSerial",
    "FrameDecoder",
    "SerialTransport",
    "crc16_ccitt",
    "crc16_ccitt_false",
    "decode_response",
    "encode_driver_call",
    "encode_driver_call_args",
    "encode_driver_call_payload",
    "encode_frame",
    "encode_simple_command",
    "encode_simple_command_payload",
    "open_serial",
    "close",
    "configure_pin",
    "read_pin",
    "write_pin",
    "send_command",
    "parse_device_info",
    "parse_string_tlv",
    "parse_tlv",
    # Re-exported generated constants used by consumers
    "CMD_ADC_EXPECT",
    "CMD_ADC_READ",
    "CMD_CAPABILITIES",
    "CMD_DEVICE_INFO",
    "CMD_DRIVER_CALL",
    "CMD_DRIVER_INFO",
    "CMD_ECHO",
    "CMD_GPIO_READ",
    "CMD_GPIO_WRITE",
    "CMD_PIN_MODE",
    "CMD_PING",
    "CMD_PULSE_MEASURE",
    "CMD_RESET",
    "CMD_SET_DEBUG_LEVEL",
    "CMD_UART_EXPECT",
    "CMD_UART_SEND",
    "CRC_INIT",
    "CRC_POLY",
    "COMMANDS",
    "COMMAND_PARAMS",
    "DEFAULT_BAUD",
    "DEFAULT_SERIAL_BAUD",
    "DEFAULT_SERIAL_TIMEOUT_S",
    "DEFAULT_TIMEOUT_S",
    "DRIVER_METHOD_MAP",
    "ERROR_CODES",
    "FERQON_SIGNATURE_CAPABILITY_VERSION",
    "FERQON_SIGNATURE_MAGIC",
    "FERQON_SIGNATURE_VENDOR",
    "FRAME_ASSEMBLY_TIMEOUT_MS",
    "FRAME_OVERHEAD",
    "GPIO_MODES",
    "INFO_COMMAND_IDS",
    "INTER_BYTE_TIMEOUT_MS",
    "MAX_FRAME_BYTES",
    "MAX_PAYLOAD_BYTES",
    "PACKET_TYPES",
    "PKT_ACK",
    "PKT_DONE",
    "PKT_ERROR",
    "PKT_EVENT",
    "PKT_HEARTBEAT",
    "PKT_LOG",
    "PKT_REQUEST",
    "PROTOCOL_VERSION",
    "SEQ_UNSOLICITED",
    "START_BYTE",
    "TLV_BUILD_TIMESTAMP",
    "TLV_COMMAND",
    "TLV_DEVICE_NAME",
    "TLV_DRIVER",
    "TLV_FERQON_SIGNATURE",
    "TLV_FIRMWARE_VERSION",
    "TLV_FREE_RAM",
    "TLV_MCU_TYPE",
    "TLV_METHOD",
    "TLV_PROTOCOL_VERSION",
    "TLV_UPTIME_MS",
    "TLV_VERSION",
]
