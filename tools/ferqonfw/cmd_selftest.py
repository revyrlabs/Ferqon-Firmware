#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
cmd_selftest.py
--------------
ferqonfw selftest command — run self-test matrix against device or emulator.
"""

import argparse

from ferqon_selftest import SerialTransport, EmulatorTransport, run_tests


def cmd_selftest(args: argparse.Namespace) -> int:
    """Run self-test matrix."""
    if args.emulator:
        print("Using in-process emulator for self-test")
        from ferqon_emulator import FerqonEmulator

        emulator = FerqonEmulator()
        transport = EmulatorTransport(emulator)
    else:
        if not args.port:
            print("Error: --port required when not using --emulator")
            return 1
        print(f"Running self-test on port: {args.port}")
        transport = SerialTransport(args.port)

    try:
        if args.port:
            transport.connect()

        summary = run_tests(transport)

        print("\n" + "=" * 60)
        print(f"SUMMARY: {summary.passed}/{summary.total} passed")
        if summary.failed > 0:
            print(f"FAILED: {summary.failed} tests failed")
        print(f"Duration: {summary.duration_ms:.1f}ms")
        print("=" * 60)

        if args.json:
            import json

            print("\n" + json.dumps(summary.to_dict(), indent=2))

        return 0 if summary.failed == 0 else 1

    except Exception as exc:
        print(f"Error: {exc}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        transport.close()
