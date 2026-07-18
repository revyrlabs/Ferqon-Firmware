#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
cmd_selftest.py
--------------
ferqonfw selftest command — run a basic self-test against a real device.

Production-safe: uses only the self-contained protocol.py module.
No imports from ferqon_emulator or ferqon_selftest.
The --emulator flag is NOT available in the production CLI.
Use ``ferqonfw-dev selftest --emulator`` for emulator-based testing.
"""

import argparse
import time

from ferqonfw.protocol import (
    SerialTransport,
    encode_frame,
    PKT_REQUEST,
    load_command_ids,
    load_cli_timing,
)


def _run_ping(
    transport: SerialTransport, cmd_ping: int, timeout_s: float
) -> tuple[bool, float, str]:
    """Run a ping test. Returns (passed, duration_ms, detail)."""
    start = time.time()
    payload = bytes([PKT_REQUEST])
    frame = encode_frame(seq=1, cmd_id=cmd_ping, payload=payload)
    resp = transport.send_frame(frame, timeout_s=timeout_s)
    elapsed = (time.time() - start) * 1000
    if resp.get("ok"):
        return True, elapsed, f"pkt_type={resp.get('pkt_type')}"
    return False, elapsed, resp.get("error", "unknown")


def _run_echo(
    transport: SerialTransport, cmd_echo: int, timeout_s: float
) -> tuple[bool, float, str]:
    """Run an echo test."""
    start = time.time()
    payload = bytes([PKT_REQUEST]) + b"hello"
    frame = encode_frame(seq=2, cmd_id=cmd_echo, payload=payload)
    resp = transport.send_frame(frame, timeout_s=timeout_s)
    elapsed = (time.time() - start) * 1000
    if resp.get("ok"):
        body = resp.get("body", b"")
        if body == b"hello":
            return True, elapsed, f"echoed={body.decode('utf-8', errors='replace')}"
        return False, elapsed, f"unexpected response: {body.hex()}"
    return False, elapsed, resp.get("error", "unknown")


def cmd_selftest(args: argparse.Namespace) -> int:
    """Run a basic self-test on a real device."""
    if not args.port:
        print("Error: --port is required for production selftest")
        print("There is no default port — specify one explicitly.")
        return 1

    print(f"Running self-test on port: {args.port}")
    transport = SerialTransport(args.port)

    try:
        transport.connect()

        try:
            cmd_ids = load_command_ids()
            cmd_ping = cmd_ids.get("ping", 9)
            cmd_echo = cmd_ids.get("echo", 8)
        except Exception:
            cmd_ping = 9
            cmd_echo = 8

        # Load CLI timeout from production config
        cli_timeout_s, _ = load_cli_timing()

        results = []

        print("\nRunning ping test...")
        passed, ms, detail = _run_ping(transport, cmd_ping, cli_timeout_s)
        status = "PASS" if passed else "FAIL"
        print(f"  ping: {status} ({ms:.1f}ms) {detail}")
        results.append(("ping", passed))

        print("Running echo test...")
        passed, ms, detail = _run_echo(transport, cmd_echo, cli_timeout_s)
        status = "PASS" if passed else "FAIL"
        print(f"  echo: {status} ({ms:.1f}ms) {detail}")
        results.append(("echo", passed))

        passed_count = sum(1 for _, p in results if p)
        total = len(results)

        print(f"\n{'=' * 60}")
        print(f"SUMMARY: {passed_count}/{total} passed")
        print(f"{'=' * 60}")

        if args.json:
            import json

            summary = {
                "total": total,
                "passed": passed_count,
                "failed": total - passed_count,
                "results": [
                    {"name": name, "status": "PASS" if p else "FAIL"}
                    for name, p in results
                ],
            }
            print(json.dumps(summary, indent=2))

        return 0 if passed_count == total else 1

    except Exception as exc:
        print(f"Error: {exc}")
        return 1
    finally:
        transport.close()
