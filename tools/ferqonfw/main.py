#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
main.py
-------
Main entry point for the ferqonfw (Ferqon Firmware) production CLI tool.

Production commands:
    ferqonfw list              - List available platforms
    ferqonfw build <platform>  - Build firmware for platform
    ferqonfw build all         - Build all production boards
    ferqonfw flash <platform>  - Flash firmware to platform
    ferqonfw flash <platform> --build  - Build + flash in one step
    ferqonfw clean <platform>  - Clean build artifacts
    ferqonfw clean all         - Clean all production boards
    ferqonfw doctor            - Check environment and dependencies
    ferqonfw packet encode <cmd> - Encode a command to hex
    ferqonfw packet decode <hex> - Decode a hex packet
    ferqonfw info <platform>   - Show platform capabilities
    ferqonfw identify --port P - Detect Ferqon firmware on device
    ferqonfw selftest --port P - Run self-test on device

Development commands (ferqonfw-dev):
    ferqonfw-dev gen core          - Generate board-agnostic protocol headers
    ferqonfw-dev gen board <name>  - Generate per-board capability tables
    ferqonfw-dev gen all           - Generate all artifacts
    ferqonfw-dev validate          - Validate SSOT JSON files
    ferqonfw-dev drivers list      - List drivers and their status
    ferqonfw-dev identify --emulator - Identify using in-process emulator
    ferqonfw-dev selftest --emulator - Self-test using in-process emulator

Usage:
    ferqonfw <command> [args]
"""

import sys
import argparse
from pathlib import Path

# When run as a script (not installed as a package), add tools/ to path
# so the ferqonfw package can be imported. This does NOT add tests/hil
# or any development-only paths.
_tools_dir = Path(__file__).resolve().parent.parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

# Import production command handlers
from ferqonfw.cmd_list import cmd_list
from ferqonfw.cmd_build import cmd_build
from ferqonfw.cmd_flash import cmd_flash
from ferqonfw.cmd_clean import cmd_clean
from ferqonfw.cmd_doctor import cmd_doctor
from ferqonfw.cmd_packet import cmd_packet_encode, cmd_packet_decode
from ferqonfw.cmd_info import cmd_info
from ferqonfw.cmd_identify import cmd_identify
from ferqonfw.cmd_selftest import cmd_selftest


def _add_common_args(parser):
    """Add arguments common to multiple subcommands."""
    pass


def main():
    parser = argparse.ArgumentParser(
        prog="ferqonfw",
        description="Ferqon Firmware CLI - Build, flash, and manage Ferqon firmware (production)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list command
    list_parser = subparsers.add_parser("list", help="List available platforms")
    list_parser.set_defaults(func=cmd_list)

    # build command
    build_parser = subparsers.add_parser("build", help="Build firmware for a platform")
    build_parser.add_argument(
        "platform",
        help="Platform name (e.g., pico, esp32) or 'all' for all production boards.",
    )
    build_parser.add_argument(
        "--project-dir",
        default=None,
        help="Path to firmware project directory (default: auto-detect). "
        "Can also be set via FERQON_FIRMWARE_DIR env var.",
    )
    build_parser.set_defaults(func=cmd_build)

    # flash command
    flash_parser = subparsers.add_parser("flash", help="Flash firmware to a platform")
    flash_parser.add_argument("platform", help="Platform name (e.g., pico, esp32)")
    flash_parser.add_argument(
        "--project-dir",
        default=None,
        help="Path to firmware project directory (default: auto-detect). "
        "Can also be set via FERQON_FIRMWARE_DIR env var.",
    )
    flash_parser.add_argument(
        "--port",
        default=None,
        help="Serial port for uploading (e.g., /dev/ttyACM0). "
        "Passed to PlatformIO as --upload-port.",
    )
    flash_parser.add_argument(
        "--build",
        action="store_true",
        help="Build firmware before flashing (combines build + flash in one step).",
    )
    flash_parser.set_defaults(func=cmd_flash)

    # clean command
    clean_parser = subparsers.add_parser("clean", help="Clean build artifacts")
    clean_parser.add_argument(
        "platform",
        help="Platform name (e.g., pico, esp32) or 'all' for all production boards.",
    )
    clean_parser.add_argument(
        "--project-dir",
        default=None,
        help="Path to firmware project directory (default: auto-detect). "
        "Can also be set via FERQON_FIRMWARE_DIR env var.",
    )
    clean_parser.set_defaults(func=cmd_clean)

    # doctor command
    doctor_parser = subparsers.add_parser(
        "doctor", help="Check environment and dependencies"
    )
    doctor_parser.set_defaults(func=cmd_doctor)

    # packet command
    packet_parser = subparsers.add_parser("packet", help="Encode/decode packets")
    packet_subparsers = packet_parser.add_subparsers(
        dest="packet_action", help="Packet action", required=True
    )

    packet_encode_parser = packet_subparsers.add_parser(
        "encode", help="Encode a command to hex"
    )
    packet_encode_parser.add_argument(
        "command", help="Command name (e.g., ping, pin_mode)"
    )
    packet_encode_parser.add_argument(
        "--param", action="append", help="Parameters (key=value)", default=[]
    )
    packet_encode_parser.set_defaults(func=cmd_packet_encode)

    packet_decode_parser = packet_subparsers.add_parser(
        "decode", help="Decode a hex packet"
    )
    packet_decode_parser.add_argument("hex", help='Hex packet (e.g., "AB 09 00 A2")')
    packet_decode_parser.set_defaults(func=cmd_packet_decode)

    # info command
    info_parser = subparsers.add_parser("info", help="Show platform capabilities")
    info_parser.add_argument("platform", help="Platform name (e.g., pico, esp32)")
    info_parser.set_defaults(func=cmd_info)

    # identify command (production: serial only, no emulator)
    identify_parser = subparsers.add_parser(
        "identify", help="Detect whether device is running Ferqon firmware"
    )
    identify_parser.add_argument(
        "--port",
        required=True,
        help="Serial port (e.g., /dev/ttyACM0). Required — no default.",
    )
    identify_parser.set_defaults(func=cmd_identify)

    # selftest command (production: serial only, no emulator)
    selftest_parser = subparsers.add_parser(
        "selftest", help="Run self-test against a real device"
    )
    selftest_parser.add_argument(
        "--port",
        required=True,
        help="Serial port (e.g., /dev/ttyACM0). Required — no default.",
    )
    selftest_parser.add_argument(
        "--json", action="store_true", help="Output JSON summary"
    )
    selftest_parser.set_defaults(func=cmd_selftest)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
