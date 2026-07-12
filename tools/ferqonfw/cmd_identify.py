#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
cmd_identify.py
--------------
ferqonfw identify command — probe device and print detection classification.
"""

import argparse

from serial_protocol import encode_frame as _encode_frame
from ferqon_emulator import (
    FerqonEmulator,
    TLV_DEVICE_NAME,
    TLV_MCU_TYPE,
    TLV_FIRMWARE_VERSION,
    TLV_PROTOCOL_VERSION,
    TLV_FERQON_SIGNATURE,
    CMD_DEVICE_INFO,
    FERQON_SIGNATURE_MAGIC,
)
from ferqon_selftest import SerialTransport, EmulatorTransport


def cmd_identify(args: argparse.Namespace) -> int:
    """Run device identification."""
    if args.emulator:
        print("Using in-process emulator for identification")
        emulator = FerqonEmulator()
        transport = EmulatorTransport(emulator)
    else:
        if not args.port:
            print("Error: --port required when not using --emulator")
            return 1
        print(f"Identifying device on port: {args.port}")
        transport = SerialTransport(args.port)

    try:
        if args.port:
            transport.connect()

        # Send device_info command
        frame = _encode_frame(seq=1, cmd_id=CMD_DEVICE_INFO, payload=b"")
        resp = transport.send_frame(frame, timeout_s=2.0)

        if not resp.get("ok"):
            print(f"Error: {resp.get('error', 'unknown error')}")
            return 1

        body = resp.get("body", b"")

        # Parse TLVs
        def parse_tlv(data: bytes) -> dict[int, bytes]:
            result = {}
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
            value = tlvs.get(tlv_type, b"")
            try:
                return value.decode("utf-8", errors="replace").rstrip("\x00")
            except Exception:
                return ""

        tlvs = parse_tlv(body)

        device_name = parse_string_tlv(tlvs, TLV_DEVICE_NAME)
        mcu_type = parse_string_tlv(tlvs, TLV_MCU_TYPE)
        fw_version = parse_string_tlv(tlvs, TLV_FIRMWARE_VERSION)
        proto_version = parse_string_tlv(tlvs, TLV_PROTOCOL_VERSION)

        signature = tlvs.get(TLV_FERQON_SIGNATURE, b"")
        has_signature = signature.startswith(FERQON_SIGNATURE_MAGIC)

        # Determine classification
        if has_signature:
            status = "ferqon_verified"
        elif device_name and mcu_type and fw_version and proto_version:
            status = "ferqon_compatible"
        elif tlvs:
            status = "serial_unknown"
        else:
            status = "not_ferqon"

        print(f"\nDetection Result: {status}")
        print("-" * 40)
        print(f"Device Name:      {device_name}")
        print(f"MCU Type:         {mcu_type}")
        print(f"Firmware Version: {fw_version}")
        print(f"Protocol Version: {proto_version}")
        print(f"Signature:        {'Present' if has_signature else 'Absent'}")

        return 0

    except Exception as exc:
        print(f"Error: {exc}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        transport.close()
