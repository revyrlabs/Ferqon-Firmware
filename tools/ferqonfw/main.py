#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
main.py
-------
Main entry point for the ferqonfw (Ferqon Firmware) CLI tool.

Commands:
    ferqonfw list              - List available platforms
    ferqonfw <platform> build - Build firmware for platform
    ferqonfw <platform> flash - Flash firmware to platform
    ferqonfw <platform> clean - Clean build artifacts
    ferqonfw doctor            - Check environment and dependencies
    ferqonfw gen core          - Generate board-agnostic protocol headers
    ferqonfw gen board <name>  - Generate per-board capability tables
    ferqonfw validate          - Validate SSOT JSON files
    ferqonfw packet encode <cmd> - Encode a command to hex
    ferqonfw packet decode <hex> - Decode a hex packet
    ferqonfw drivers list      - List drivers and their status
    ferqonfw info <platform>   - Show platform capabilities

Usage:
    ferqonfw <command> [args]
"""

import sys
import argparse
from pathlib import Path

# Add tools and tests/hil to path for imports
_repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo_root / "tools"))
sys.path.insert(0, str(_repo_root / "tests" / "hil"))

# Import command handlers
from ferqonfw.cmd_list import cmd_list
from ferqonfw.cmd_build import cmd_build
from ferqonfw.cmd_flash import cmd_flash
from ferqonfw.cmd_clean import cmd_clean
from ferqonfw.cmd_doctor import cmd_doctor
from ferqonfw.cmd_gen import cmd_gen
from ferqonfw.cmd_validate import cmd_validate
from ferqonfw.cmd_packet import cmd_packet_encode, cmd_packet_decode
from ferqonfw.cmd_drivers import cmd_drivers_list
from ferqonfw.cmd_info import cmd_info
from ferqonfw.cmd_identify import cmd_identify
from ferqonfw.cmd_selftest import cmd_selftest


def main():
    parser = argparse.ArgumentParser(
        prog="ferqonfw",
        description="Ferqon Firmware CLI - Build, flash, and manage Ferqon firmware",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list command
    list_parser = subparsers.add_parser("list", help="List available platforms")
    list_parser.set_defaults(func=cmd_list)

    # build command
    build_parser = subparsers.add_parser("build", help="Build firmware for a platform")
    build_parser.add_argument("platform", help="Platform name (e.g., pico, esp32)")
    build_parser.set_defaults(func=cmd_build)

    # flash command
    flash_parser = subparsers.add_parser("flash", help="Flash firmware to a platform")
    flash_parser.add_argument("platform", help="Platform name (e.g., pico, esp32)")
    flash_parser.set_defaults(func=cmd_flash)

    # clean command
    clean_parser = subparsers.add_parser("clean", help="Clean build artifacts")
    clean_parser.add_argument("platform", help="Platform name (e.g., pico, esp32)")
    clean_parser.set_defaults(func=cmd_clean)

    # doctor command
    doctor_parser = subparsers.add_parser(
        "doctor", help="Check environment and dependencies"
    )
    doctor_parser.set_defaults(func=cmd_doctor)

    # gen command
    gen_parser = subparsers.add_parser("gen", help="Generate protocol artifacts")
    gen_subparsers = gen_parser.add_subparsers(
        dest="gen_target", help="Generation target"
    )

    gen_core_parser = gen_subparsers.add_parser(
        "core", help="Generate board-agnostic headers"
    )
    gen_core_parser.set_defaults(func=cmd_gen, gen_target="core")

    gen_board_parser = gen_subparsers.add_parser(
        "board", help="Generate per-board tables"
    )
    gen_board_parser.add_argument("platform", help="Platform name (e.g., pico, esp32)")
    gen_board_parser.set_defaults(func=cmd_gen, gen_target="board")

    gen_all_parser = gen_subparsers.add_parser("all", help="Generate all artifacts")
    gen_all_parser.set_defaults(func=cmd_gen, gen_target="all")

    gen_parser.set_defaults(func=cmd_gen, gen_target=None)

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate SSOT JSON files")
    validate_parser.add_argument(
        "--json", action="store_true", help="Output JSON format"
    )
    validate_parser.set_defaults(func=cmd_validate)

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

    # drivers command
    drivers_parser = subparsers.add_parser("drivers", help="Driver management")
    drivers_subparsers = drivers_parser.add_subparsers(
        dest="drivers_action", help="Driver action"
    )

    drivers_list_parser = drivers_subparsers.add_parser("list", help="List drivers")
    drivers_list_parser.set_defaults(func=cmd_drivers_list)
    drivers_parser.set_defaults(func=cmd_drivers_list)

    # info command
    info_parser = subparsers.add_parser("info", help="Show platform capabilities")
    info_parser.add_argument("platform", help="Platform name (e.g., pico, esp32)")
    info_parser.set_defaults(func=cmd_info)

    # identify command
    identify_parser = subparsers.add_parser(
        "identify", help="Detect whether device is running Ferqon firmware"
    )
    identify_group = identify_parser.add_mutually_exclusive_group(required=True)
    identify_group.add_argument("--port", help="Serial port (e.g., /dev/ttyACM0)")
    identify_group.add_argument(
        "--emulator", action="store_true", help="Use in-process emulator"
    )
    identify_parser.set_defaults(func=cmd_identify)

    # selftest command
    selftest_parser = subparsers.add_parser(
        "selftest", help="Run self-test matrix against device or emulator"
    )
    selftest_group = selftest_parser.add_mutually_exclusive_group(required=True)
    selftest_group.add_argument("--port", help="Serial port (e.g., /dev/ttyACM0)")
    selftest_group.add_argument(
        "--emulator", action="store_true", help="Use in-process emulator"
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
