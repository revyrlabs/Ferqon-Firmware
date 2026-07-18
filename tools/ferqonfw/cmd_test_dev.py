#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
cmd_test_dev.py
---------------
Development-only test command — runs native unit tests via PlatformIO.

This module is NOT part of the production CLI. It requires PlatformIO
and the native test environment to be configured.
"""

import argparse

from ferqonfw.board_loader import get_pio_path, require_pio, run_cmd


def cmd_test_dev(args: argparse.Namespace) -> int:
    """Run native unit tests (development only)."""
    try:
        require_pio()
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1

    print("Running native unit tests...")
    print("Running: pio test -e native")
    print("-" * 60)
    result = run_cmd([get_pio_path(), "test", "-e", "native"])
    print("-" * 60)

    if result.returncode == 0:
        print("All native tests passed.")
        return 0
    print("Native tests failed.")
    return result.returncode
