#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
run_driver_tests.py
-------------------
Single entry point for running Ferqon firmware driver tests.

This script provides a unified interface for running driver tests with:
- Automatic device discovery (USB VID/PID detection)
- Emulator fallback when no hardware is available
- Configurable port, baudrate, and board selection
- Support for both pytest and direct script execution

Usage:
    python run_driver_tests.py                    # Auto-discover device
    python run_driver_tests.py --port /dev/ttyACM0  # Specific port
    python run_driver_tests.py --emulator         # Force emulator mode
    python run_driver_tests.py --board pico        # Specific board
    python run_driver_tests.py --pytest           # Run via pytest
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add tools to path for imports
tools_dir = Path(__file__).parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from device_config import (  # noqa: E402
    get_default_device_port,
    get_default_baudrate,
    get_board_name,
    get_emulator_enabled,
)
from device_discovery import find_board  # noqa: E402


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Ferqon firmware driver tests with auto-discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_driver_tests.py                    # Auto-discover device
  python run_driver_tests.py --port /dev/ttyACM0  # Specific port
  python run_driver_tests.py --emulator         # Force emulator mode
  python run_driver_tests.py --board pico        # Specific board
  python run_driver_tests.py --pytest           # Run via pytest
        """,
    )
    parser.add_argument(
        "--port",
        help="Serial port (default: auto-discover or FERQON_TEST_DEVICE_PORT)",
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        help="Baud rate (default: 115200 or FERQON_TEST_BAUDRATE)",
    )
    parser.add_argument(
        "--board",
        help="Board name (default: FERQON_TEST_BOARD or 'pico')",
    )
    parser.add_argument(
        "--emulator",
        action="store_true",
        help="Force emulator mode (ignores hardware detection)",
    )
    parser.add_argument(
        "--no-emulator",
        action="store_true",
        help="Disable emulator fallback (require hardware)",
    )
    parser.add_argument(
        "--pytest",
        action="store_true",
        help="Run tests via pytest instead of direct execution",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    return parser.parse_args()


def run_direct_tests(args):
    """Run tests via direct script execution."""
    print("=" * 70)
    print("Ferqon Driver Tests (Direct Execution)")
    print("=" * 70)

    # Determine configuration
    port = args.port or get_default_device_port()
    baudrate = args.baudrate or get_default_baudrate()
    board = args.board or get_board_name()

    # Handle emulator mode
    use_emulator = args.emulator or (get_emulator_enabled() and not args.no_emulator)

    if use_emulator:
        print("\n📱 Emulator mode enabled")
        print(f"   Port: {port} (emulator PTY)")
    else:
        # Auto-discover if port is "auto"
        if port == "auto":
            print("\n🔍 Auto-discovering device...")
            try:
                discovered = find_board(board_name=board)
                if discovered:
                    port = discovered
                    print(f"   Found device at: {port}")
                else:
                    print("   ⚠️  No device found, falling back to emulator")
                    use_emulator = True
            except Exception as e:
                print(f"   ⚠️  Discovery failed: {e}")
                if not args.no_emulator:
                    print("   Falling back to emulator")
                    use_emulator = True
                else:
                    print("   ❌ No emulator fallback allowed")
                    return 1

    print("\n⚙️  Configuration:")
    print(f"   Port: {port}")
    print(f"   Baudrate: {baudrate}")
    print(f"   Board: {board}")
    print(f"   Mode: {'emulator' if use_emulator else 'hardware'}")

    # Set environment for subprocess calls
    env = os.environ.copy()
    env["FERQON_TEST_DEVICE_PORT"] = port
    env["FERQON_TEST_BAUDRATE"] = str(baudrate)
    env["FERQON_TEST_BOARD"] = board
    env["FERQON_TEST_USE_EMULATOR"] = "1" if use_emulator else "0"

    # Run driver tests
    tests_dir = Path(__file__).parent.parent / "tests"
    test_scripts = [
        tests_dir / "test_drivers.py",
        tests_dir / "test_rgb_driver.py",
    ]

    results = []
    for script in test_scripts:
        if not script.exists():
            print(f"\n⚠️  Test script not found: {script}")
            continue

        print(f"\n🧪 Running: {script.name}")
        try:
            result = subprocess.run(
                [sys.executable, str(script)],
                env=env,
                cwd=str(tests_dir),
                capture_output=not args.verbose,
            )
            results.append((script.name, result.returncode == 0))
            if result.returncode == 0:
                print("   ✅ Passed")
            else:
                print(f"   ❌ Failed (exit code {result.returncode})")
                if not args.verbose and result.stderr:
                    print(f"   Error: {result.stderr.decode()[:200]}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append((script.name, False))

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    passed = sum(1 for _, success in results if success)
    total = len(results)
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"   {status} {name}")
    print(f"\n   Total: {passed}/{total} passed")

    return 0 if passed == total else 1


def run_pytest_tests(args):
    """Run tests via pytest."""
    print("=" * 70)
    print("Ferqon Driver Tests (pytest)")
    print("=" * 70)

    # Determine configuration
    port = args.port or get_default_device_port()
    baudrate = args.baudrate or get_default_baudrate()
    board = args.board or get_board_name()

    # Handle emulator mode
    use_emulator = args.emulator or (get_emulator_enabled() and not args.no_emulator)

    if use_emulator:
        print("\n📱 Emulator mode enabled")
    else:
        # Auto-discover if port is "auto"
        if port == "auto":
            print("\n🔍 Auto-discovering device...")
            try:
                discovered = find_board(board_name=board)
                if discovered:
                    port = discovered
                    print(f"   Found device at: {port}")
                else:
                    print("   ⚠️  No device found, falling back to emulator")
                    use_emulator = True
            except Exception as e:
                print(f"   ⚠️  Discovery failed: {e}")
                if not args.no_emulator:
                    print("   Falling back to emulator")
                    use_emulator = True
                else:
                    print("   ❌ No emulator fallback allowed")
                    return 1

    print("\n⚙️  Configuration:")
    print(f"   Port: {port}")
    print(f"   Baudrate: {baudrate}")
    print(f"   Board: {board}")
    print(f"   Mode: {'emulator' if use_emulator else 'hardware'}")

    # Set environment for pytest
    env = os.environ.copy()
    env["FERQON_TEST_DEVICE_PORT"] = port
    env["FERQON_TEST_BAUDRATE"] = str(baudrate)
    env["FERQON_TEST_BOARD"] = board
    env["FERQON_TEST_USE_EMULATOR"] = "1" if use_emulator else "0"

    # Run pytest
    tests_dir = Path(__file__).parent.parent / "tests"
    pytest_args = [
        sys.executable,
        "-m",
        "pytest",
        str(tests_dir / "test_drivers.py"),
        str(tests_dir / "test_rgb_driver.py"),
        "-v",
    ]

    if args.verbose:
        pytest_args.append("-vv")

    print("\n🧪 Running pytest...")
    result = subprocess.run(pytest_args, env=env, cwd=str(tests_dir.parent))
    return result.returncode


def main():
    """Main entry point."""
    args = parse_args()

    if args.pytest:
        return run_pytest_tests(args)
    else:
        return run_direct_tests(args)


if __name__ == "__main__":
    sys.exit(main())
