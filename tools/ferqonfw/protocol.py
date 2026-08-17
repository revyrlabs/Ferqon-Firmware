# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""Ferqon serial protocol for the production firmware CLI.

Framing, CRC, TLV parsing, device identity, and SerialTransport come from
``ferqon_hw.protocol``. SSOT file loaders stay here because they read files
under ``firmware/``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

_FERQON_ROOT = Path(__file__).resolve().parents[3]
_HW_SDK = _FERQON_ROOT / "packages" / "hw-sdk" / "ferqon_hw"
_ENV_CONSTANTS = _FERQON_ROOT / "packages" / "ferqon-env-constants" / "src"
for _path in (_HW_SDK, _ENV_CONSTANTS):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

from ferqon_hw._generated import (  # noqa: E402
    CRC_INIT,
    CRC_POLY,
    MAX_PAYLOAD_BYTES,
    PKT_ACK,
    PKT_DONE,
    PKT_ERROR,
    PKT_EVENT,
    PKT_HEARTBEAT,
    PKT_LOG,
    PKT_REQUEST,
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
from ferqon_hw.protocol import (  # noqa: E402
    DEFAULT_BAUD,
    DeviceIdentity,
    FrameDecoder,
    SerialTransport as _SdkSerialTransport,
    crc16_ccitt_false,
    encode_frame,
    parse_device_info,
    parse_string_tlv,
    parse_tlv,
)
from ferqon_env_constants import JSON_KEY_COMMANDS, JSON_KEY_ID, JSON_KEY_TLV_TYPES  # noqa: E402

JSON_KEY_CLI_TIMEOUT_S = "cli_timeout_s"
JSON_KEY_CLI_CONNECT_DELAY_MS = "cli_connect_delay_ms"
LIT_DEVICE_INFO = "device_info"
LIT_DRIVER_INFO = "driver_info"
DEFAULT_CLI_TIMEOUT_S = 2.0
DEFAULT_CLI_CONNECT_DELAY_MS = 500


def _firmware_root(firmware_dir: Path | None = None) -> Path:
    return firmware_dir if firmware_dir is not None else Path(__file__).resolve().parents[2]


def _load_ssot(firmware_dir: Path | None = None) -> dict:
    path = _firmware_root(firmware_dir) / "protocol" / "ssot" / "commands.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_command_ids(firmware_dir: Optional[Path] = None) -> dict[str, int]:
    """Load command IDs from the SSOT commands.json."""
    raw = _load_ssot(firmware_dir)[JSON_KEY_COMMANDS]
    return {
        name: int(entry[JSON_KEY_ID])
        for name, entry in raw.items()
        if isinstance(entry, dict) and isinstance(entry.get(JSON_KEY_ID), int)
    }


def load_tlv_types(firmware_dir: Optional[Path] = None) -> dict[str, int]:
    """Load TLV type IDs from the SSOT commands.json."""
    raw = _load_ssot(firmware_dir).get(JSON_KEY_TLV_TYPES, {})
    return {name: int(value) for name, value in raw.items()}


def load_cli_timing(firmware_dir: Optional[Path] = None) -> tuple[float, int]:
    """Load CLI transport timing from production_config.json."""
    config_path = _firmware_root(firmware_dir) / "tools" / "production_config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_CLI_TIMEOUT_S, DEFAULT_CLI_CONNECT_DELAY_MS
    timeout = config.get(JSON_KEY_CLI_TIMEOUT_S, DEFAULT_CLI_TIMEOUT_S)
    delay = config.get(JSON_KEY_CLI_CONNECT_DELAY_MS, DEFAULT_CLI_CONNECT_DELAY_MS)
    return float(timeout), int(delay)


def get_info_command_ids(firmware_dir: Optional[Path] = None) -> set[int]:
    """Return command IDs that do not require a REQUEST prefix."""
    try:
        ids = load_command_ids(firmware_dir)
        return {
            ids[LIT_DEVICE_INFO],
            ids[LIT_DRIVER_INFO],
        } & {v for v in ids.values() if v != 0}
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return set()


class SerialTransport(_SdkSerialTransport):
    """Serial transport with CLI timing defaults from production_config.json."""

    def __init__(
        self,
        port: str,
        baudrate: int = DEFAULT_BAUD,
        timeout: Optional[float] = None,
        connect_delay_ms: Optional[int] = None,
    ) -> None:
        default_timeout, default_delay = load_cli_timing()
        super().__init__(
            port,
            baudrate=baudrate,
            timeout=timeout if timeout is not None else default_timeout,
            connect_delay_ms=(
                connect_delay_ms if connect_delay_ms is not None else default_delay
            ),
        )


__all__ = [
    "CRC_INIT",
    "CRC_POLY",
    "DEFAULT_BAUD",
    "DEFAULT_CLI_CONNECT_DELAY_MS",
    "DEFAULT_CLI_TIMEOUT_S",
    "DeviceIdentity",
    "FrameDecoder",
    "MAX_PAYLOAD_BYTES",
    "PKT_ACK",
    "PKT_DONE",
    "PKT_ERROR",
    "PKT_EVENT",
    "PKT_HEARTBEAT",
    "PKT_LOG",
    "PKT_REQUEST",
    "START_BYTE",
    "SerialTransport",
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
    "crc16_ccitt_false",
    "encode_frame",
    "get_info_command_ids",
    "load_cli_timing",
    "load_command_ids",
    "load_tlv_types",
    "parse_device_info",
    "parse_string_tlv",
    "parse_tlv",
]
