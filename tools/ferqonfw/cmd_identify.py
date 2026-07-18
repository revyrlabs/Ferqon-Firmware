#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
cmd_identify.py
--------------
ferqonfw identify command — probe device and print detection classification.

Production-safe: uses only the self-contained protocol.py module.
No imports from ferqon_emulator, ferqon_selftest, or test harnesses.
"""

import argparse

from ferqonfw.protocol import (
    SerialTransport,
    encode_frame,
    parse_device_info,
    load_command_ids,
    load_cli_timing,
)


def cmd_identify(args: argparse.Namespace) -> int:
    """Run device identification on a real serial port.

    The --emulator flag is NOT available in the production CLI.
    Use ``ferqonfw-dev identify --emulator`` for emulator-based testing.
    """
    if not args.port:
        print("Error: --port is required for production identify")
        print("There is no default port — specify one explicitly.")
        return 1

    print(f"Identifying device on port: {args.port}")
    transport = SerialTransport(args.port)

    try:
        transport.connect()

        # Load command IDs from SSOT
        try:
            cmd_ids = load_command_ids()
            cmd_device_info = cmd_ids.get("device_info", 11)
        except Exception:
            # Fall back to the known device_info ID
            cmd_device_info = 11

        # Load CLI timeout from production config
        cli_timeout_s, _ = load_cli_timing()

        # Send device_info command
        frame = encode_frame(seq=1, cmd_id=cmd_device_info, payload=b"")
        resp = transport.send_frame(frame, timeout_s=cli_timeout_s)

        if not resp.get("ok"):
            print(f"Error: {resp.get('error', 'unknown error')}")
            return 1

        body = resp.get("body", b"")
        identity = parse_device_info(body)

        print(f"\nDetection Result: {identity.classification}")
        print("-" * 40)
        print(f"Device Name:      {identity.device_name}")
        print(f"MCU Type:         {identity.mcu_type}")
        print(f"Firmware Version: {identity.firmware_version}")
        print(f"Protocol Version: {identity.protocol_version}")
        print(f"Signature:        {'Present' if identity.has_signature else 'Absent'}")
        if identity.has_signature:
            print(f"  Vendor:         {identity.signature_vendor}")
            print(f"  Cap Version:    {identity.signature_cap_version}")

        return 0

    except Exception as exc:
        print(f"Error: {exc}")
        return 1
    finally:
        transport.close()
