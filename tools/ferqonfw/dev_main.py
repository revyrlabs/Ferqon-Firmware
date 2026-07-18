#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
dev_main.py
-----------
Main entry point for the ferqonfw-dev (Ferqon Firmware Development) CLI tool.

This CLI provides development-only commands: code generation, validation,
emulator-based testing, and driver management. It is NOT part of the
production CLI package and must not be imported by production commands.

Development commands:
    ferqonfw-dev gen core          - Generate board-agnostic protocol headers
    ferqonfw-dev gen board <name>  - Generate per-board capability tables
    ferqonfw-dev gen all           - Generate all artifacts
    ferqonfw-dev validate          - Validate SSOT JSON files
    ferqonfw-dev drivers list      - List drivers and their status
    ferqonfw-dev test              - Run native unit tests (no hardware required)
    ferqonfw-dev identify --emulator - Identify using in-process emulator
    ferqonfw-dev selftest --emulator - Self-test using in-process emulator

Usage:
    ferqonfw-dev <command> [args]
"""

import sys
import argparse
from pathlib import Path

# Add tools and tests/hil to path for development imports.
# These paths are only needed when the dev commands are actually invoked;
# the imports below are lazy so that a production-only `pip install .`
# does not crash if dev-only dependencies (jsonschema, pytest, etc.) are
# missing.
_repo_root = Path(__file__).resolve().parents[2]


def _ensure_dev_paths() -> None:
    """Insert tools/ and tests/hil/ into sys.path (called lazily)."""
    tools_dir = str(_repo_root / "tools")
    hil_dir = str(_repo_root / "tests" / "hil")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    if hil_dir not in sys.path:
        sys.path.insert(0, hil_dir)


def cmd_dev_gen(args: argparse.Namespace) -> int:
    """Generate protocol artifacts (development only)."""
    _ensure_dev_paths()
    from ferqonfw.cmd_gen import cmd_gen

    return cmd_gen(args)


def cmd_dev_validate(args: argparse.Namespace) -> int:
    """Validate SSOT JSON files (development only)."""
    _ensure_dev_paths()
    from ferqonfw.cmd_validate import cmd_validate

    return cmd_validate(args)


def cmd_dev_drivers_list(args: argparse.Namespace) -> int:
    """List drivers and their status (development only)."""
    _ensure_dev_paths()
    from ferqonfw.cmd_drivers import cmd_drivers_list

    return cmd_drivers_list(args)


def cmd_dev_identify(args: argparse.Namespace) -> int:
    """Identify using emulator (development only)."""
    _ensure_dev_paths()
    from ferqonfw.cmd_identify_dev import cmd_identify_dev

    return cmd_identify_dev(args)


def cmd_dev_selftest(args: argparse.Namespace) -> int:
    """Self-test using emulator (development only)."""
    _ensure_dev_paths()
    from ferqonfw.cmd_selftest_dev import cmd_selftest_dev

    return cmd_selftest_dev(args)


def cmd_dev_test(args: argparse.Namespace) -> int:
    """Run native unit tests (development only)."""
    from ferqonfw.cmd_test_dev import cmd_test_dev

    return cmd_test_dev(args)


def main():
    parser = argparse.ArgumentParser(
        prog="ferqonfw-dev",
        description="Ferqon Firmware Development CLI - codegen, validation, emulator tests",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # gen command
    gen_parser = subparsers.add_parser("gen", help="Generate protocol artifacts")
    gen_subparsers = gen_parser.add_subparsers(
        dest="gen_target", help="Generation target"
    )

    gen_core_parser = gen_subparsers.add_parser(
        "core", help="Generate board-agnostic headers"
    )
    gen_core_parser.set_defaults(func=cmd_dev_gen, gen_target="core")

    gen_board_parser = gen_subparsers.add_parser(
        "board", help="Generate per-board tables"
    )
    gen_board_parser.add_argument("platform", help="Platform name (e.g., pico, esp32)")
    gen_board_parser.set_defaults(func=cmd_dev_gen, gen_target="board")

    gen_all_parser = gen_subparsers.add_parser("all", help="Generate all artifacts")
    gen_all_parser.set_defaults(func=cmd_dev_gen, gen_target="all")

    gen_parser.set_defaults(func=cmd_dev_gen, gen_target=None)

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate SSOT JSON files")
    validate_parser.add_argument(
        "--json", action="store_true", help="Output JSON format"
    )
    validate_parser.set_defaults(func=cmd_dev_validate)

    # test command
    test_parser = subparsers.add_parser(
        "test", help="Run native unit tests (no hardware required)"
    )
    test_parser.set_defaults(func=cmd_dev_test)

    # drivers command
    drivers_parser = subparsers.add_parser("drivers", help="Driver management")
    drivers_subparsers = drivers_parser.add_subparsers(
        dest="drivers_action", help="Driver action"
    )

    drivers_list_parser = drivers_subparsers.add_parser("list", help="List drivers")
    drivers_list_parser.set_defaults(func=cmd_dev_drivers_list)
    drivers_parser.set_defaults(func=cmd_dev_drivers_list)

    # identify command (development: emulator mode)
    identify_parser = subparsers.add_parser(
        "identify", help="Identify device (development: supports emulator)"
    )
    identify_group = identify_parser.add_mutually_exclusive_group(required=True)
    identify_group.add_argument("--port", help="Serial port (e.g., /dev/ttyACM0)")
    identify_group.add_argument(
        "--emulator", action="store_true", help="Use in-process emulator"
    )
    identify_parser.set_defaults(func=cmd_dev_identify)

    # selftest command (development: emulator mode)
    selftest_parser = subparsers.add_parser(
        "selftest", help="Run self-test (development: supports emulator)"
    )
    selftest_group = selftest_parser.add_mutually_exclusive_group(required=True)
    selftest_group.add_argument("--port", help="Serial port (e.g., /dev/ttyACM0)")
    selftest_group.add_argument(
        "--emulator", action="store_true", help="Use in-process emulator"
    )
    selftest_parser.add_argument(
        "--json", action="store_true", help="Output JSON summary"
    )
    selftest_parser.set_defaults(func=cmd_dev_selftest)

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
