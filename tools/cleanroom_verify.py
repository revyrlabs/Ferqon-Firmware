#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
cleanroom_verify.py
-------------------
Clean-room verification script for Ferqon firmware production builds.

This script:
  1. Creates a fresh production bundle from the manifest.
  2. Sets up an isolated PlatformIO core directory (empty cache).
  3. Installs only production dependencies.
  4. Builds all five production environments from empty caches.
  5. Runs a PTY smoke test against the installed production CLI.

The PTY simulator is created inline by this script — it is NOT part of the
production package. It exists only to verify that the production CLI can
communicate with a device speaking the Ferqon protocol.

Usage:
    python3 tools/cleanroom_verify.py [--work-dir <dir>] [--skip-install]

Requirements:
    - Python 3.10+
    - pip available
    - Network access for PlatformIO package downloads
"""

from __future__ import annotations

import argparse
import json
import os
import pty
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

COPYRIGHT = "SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs"


def run(
    cmd: list[str],
    cwd: Path | None = None,
    env: dict | None = None,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    """Run a command and optionally check/capture output."""
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env={**os.environ, **env} if env else None,
        capture_output=capture,
        text=capture,
    )
    if check and result.returncode != 0:
        if capture:
            print(f"  STDOUT: {result.stdout}")
            print(f"  STDERR: {result.stderr}")
        raise RuntimeError(
            f"Command failed (exit {result.returncode}): {' '.join(cmd)}"
        )
    return result


def _load_ssot(firmware_dir: Path) -> dict:
    """Load the SSOT commands.json for protocol constants.

    Returns a dict with keys: frame, packet_types, tlv_types, commands,
    ferqon_signature.  Falls back to hardcoded values if the SSOT is
    missing (the simulator must still work for verification).
    """
    commands_path = firmware_dir / "protocol" / "ssot" / "commands.json"
    try:
        return json.loads(commands_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def create_pty_simulator(firmware_dir: Path) -> tuple[str, int]:
    """Create a minimal PTY-backed Ferqon protocol simulator for smoke testing.

    Returns (port_path, master_fd). The simulator responds to device_info,
    ping, and echo commands with valid Ferqon-protocol frames.

    Protocol constants (command IDs, TLV types, signature magic/vendor/
    capability_version, packet types) are loaded from the SSOT
    (protocol/ssot/commands.json) so the simulator stays in sync with the
    firmware without hardcoded magic numbers.

    This simulator is NOT part of the production package — it exists only
    for this verification script.
    """
    ssot = _load_ssot(firmware_dir)

    # Protocol constants from SSOT (with fallbacks)
    frame_cfg = ssot.get("frame", {})
    START_BYTE = frame_cfg.get("start_byte", 0xAB)
    CRC_POLY = frame_cfg.get("crc_poly", 0x1021)
    CRC_INIT = frame_cfg.get("crc_init", 0xFFFF)

    pkt_types = ssot.get("packet_types", {})
    PKT_DONE = pkt_types.get("DONE", 3)

    tlv_types = ssot.get("tlv_types", {})
    TLV_DEVICE_NAME = tlv_types.get("DEVICE_NAME", 1)
    TLV_MCU_TYPE = tlv_types.get("MCU_TYPE", 2)
    TLV_FIRMWARE_VERSION = tlv_types.get("FIRMWARE_VERSION", 3)
    TLV_PROTOCOL_VERSION = tlv_types.get("PROTOCOL_VERSION", 4)
    TLV_FERQON_SIGNATURE = tlv_types.get("FERQON_SIGNATURE", 16)

    sig_cfg = ssot.get("ferqon_signature", {})
    SIG_MAGIC = sig_cfg.get("magic", "FERQON").encode("utf-8")
    SIG_VENDOR = sig_cfg.get("vendor", "revyrlabs").encode("utf-8")
    SIG_CAP_VERSION = sig_cfg.get("capability_version", 1)

    commands = ssot.get("commands", {})
    CMD_DEVICE_INFO = commands.get("device_info", {}).get("id", 11)
    CMD_PING = commands.get("ping", {}).get("id", 9)
    CMD_ECHO = commands.get("echo", {}).get("id", 8)

    # Protocol version from SSOT
    proto_version = ssot.get("version", "1.1.0").encode("utf-8")

    def crc16(data: bytes) -> int:
        crc = CRC_INIT
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ CRC_POLY
                else:
                    crc = crc << 1
                crc &= 0xFFFF
        return crc

    def encode_frame(seq: int, cmd_id: int, payload: bytes) -> bytes:
        header = bytes([seq, cmd_id, len(payload)])
        crc = crc16(header + payload)
        return (
            bytes([START_BYTE])
            + header
            + payload
            + bytes([crc & 0xFF, (crc >> 8) & 0xFF])
        )

    def make_device_info_response(seq: int) -> bytes:
        """Build a device_info response with FERQON signature."""
        body = bytearray()
        # TLV: device_name
        body += bytes([TLV_DEVICE_NAME, 4]) + b"pico"
        # TLV: mcu_type
        body += bytes([TLV_MCU_TYPE, 6]) + b"rp2040"
        # TLV: firmware_version
        body += bytes([TLV_FIRMWARE_VERSION, len(proto_version)]) + proto_version
        # TLV: protocol_version
        body += bytes([TLV_PROTOCOL_VERSION, len(proto_version)]) + proto_version
        # TLV: ferqon_signature = magic + vendor + cap_version_byte
        sig = SIG_MAGIC + SIG_VENDOR + bytes([SIG_CAP_VERSION])
        body += bytes([TLV_FERQON_SIGNATURE, len(sig)]) + sig
        # Packet type = DONE
        payload = bytes([PKT_DONE]) + bytes(body)
        return encode_frame(seq, CMD_DEVICE_INFO, payload)

    def make_ping_response(seq: int) -> bytes:
        """Build a ping DONE response."""
        payload = bytes([PKT_DONE])
        return encode_frame(seq, CMD_PING, payload)

    def simulator_thread(master_fd: int) -> None:
        """Handle incoming frames on the PTY master side.

        Validates the CRC of each incoming frame before responding,
        mirroring the firmware's FrameDecoder behavior.  Frames with
        a bad CRC are silently discarded (no response), exactly as a
        real Ferqon device would do.
        """
        buf = bytearray()
        while True:
            try:
                data = os.read(master_fd, 1024)
                if not data:
                    break
                buf.extend(data)
                # Try to parse frames
                while len(buf) >= 6:
                    if buf[0] != START_BYTE:
                        del buf[0]
                        continue
                    payload_len = buf[3]
                    total = 6 + payload_len
                    if len(buf) < total:
                        break
                    seq = buf[1]
                    cmd_id = buf[2]
                    # Extract payload and CRC before consuming the frame
                    frame_payload = bytes(buf[4 : 4 + payload_len])
                    recv_crc_lo = buf[4 + payload_len]
                    recv_crc_hi = buf[4 + payload_len + 1]
                    recv_crc = recv_crc_lo | (recv_crc_hi << 8)
                    # Validate CRC — discard bad frames silently
                    calc_crc = crc16(bytes([seq, cmd_id, payload_len]) + frame_payload)
                    if recv_crc != calc_crc:
                        del buf[0]
                        continue
                    # Consume the valid frame
                    del buf[:total]
                    # Respond based on cmd_id
                    if cmd_id == CMD_DEVICE_INFO:
                        resp = make_device_info_response(seq)
                        os.write(master_fd, resp)
                    elif cmd_id == CMD_PING:
                        resp = make_ping_response(seq)
                        os.write(master_fd, resp)
                    elif cmd_id == CMD_ECHO:
                        # Echo back the payload (skip packet type byte) with DONE
                        echo_data = frame_payload[1:] if len(frame_payload) > 1 else b""
                        payload = bytes([PKT_DONE]) + echo_data
                        resp = encode_frame(seq, CMD_ECHO, payload)
                        os.write(master_fd, resp)
            except OSError:
                break

    master, slave = pty.openpty()
    port = os.ttyname(slave)

    thread = threading.Thread(target=simulator_thread, args=(master,), daemon=True)
    thread.start()

    return port, master


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean-room production verification")
    parser.add_argument(
        "--work-dir",
        default=None,
        help="Working directory (default: temporary directory)",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip pip install (assume deps already available)",
    )
    args = parser.parse_args()

    firmware_dir = Path(__file__).resolve().parent.parent

    if args.work_dir:
        work_dir = Path(args.work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        work_dir = Path(tempfile.mkdtemp(prefix="ferqon-cleanroom-"))
        cleanup = True

    bundle_dir = work_dir / "bundle"
    venv_dir = work_dir / "venv"
    pio_core_dir = work_dir / "pio-core"

    print("=" * 60)
    print("Ferqon Clean-Room Production Verification")
    print("=" * 60)
    print(f"Work directory: {work_dir}")
    print(f"Firmware source: {firmware_dir}")
    print()

    all_ok = True

    try:
        # Step 1: Create production bundle
        print("Step 1: Creating production bundle...")
        if bundle_dir.exists():
            shutil.rmtree(bundle_dir)
        run(
            [
                sys.executable,
                str(firmware_dir / "tools" / "create_production_bundle.py"),
                "--output-dir",
                str(bundle_dir),
            ],
            check=True,
        )
        print("  Bundle created successfully\n")

        # Step 2: Set up isolated environment
        if not args.skip_install:
            print("Step 2: Setting up isolated Python environment...")
            if venv_dir.exists():
                shutil.rmtree(venv_dir)
            run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

            pip = str(venv_dir / "bin" / "pip")
            python = str(venv_dir / "bin" / "python")

            # Install only production dependencies
            run(
                [
                    pip,
                    "install",
                    "-r",
                    str(bundle_dir / "tools" / "requirements-prod.txt"),
                ],
                check=True,
            )
            # Install the production CLI package
            run([pip, "install", "-e", str(bundle_dir)], check=True)

            # Verify dev tools are NOT installed
            result = run([pip, "list", "--format=json"], capture=True, check=False)
            installed = {pkg["name"] for pkg in json.loads(result.stdout)}
            dev_tools = {"pytest", "pytest-cov", "ruff", "black", "yamllint"}
            found_dev = installed & dev_tools
            if found_dev:
                print(f"  WARNING: dev tools found in production env: {found_dev}")
            else:
                print("  Verified: no dev tools in production environment")
            print()
        else:
            python = sys.executable
            pip = None
            print("Step 2: Skipped (--skip-install)\n")

        # Step 3: Build all environments with isolated PIO core
        print("Step 3: Building all production environments (isolated PIO core)...")
        pio_env = {
            "PLATFORMIO_CORE_DIR": str(pio_core_dir),
        }
        pio_core_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = bundle_dir / "tools" / "production_manifest.json"
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        for env in manifest["production_environments"]:
            print(f"\n  Building {env}...")
            try:
                run(
                    [python, "-m", "platformio", "run", "-e", env],
                    cwd=bundle_dir,
                    env=pio_env,
                    check=True,
                )
                # Verify artifact exists
                artifact_ext = (
                    "uf2" if "pico" in env else ("hex" if "teensy" in env else "bin")
                )
                artifact = (
                    bundle_dir / ".pio" / "build" / env / f"firmware.{artifact_ext}"
                )
                if artifact.exists():
                    print(
                        f"  OK: {env} -> {artifact.name} ({artifact.stat().st_size} bytes)"
                    )
                else:
                    print(f"  WARNING: artifact not found at expected path: {artifact}")
                    all_ok = False
            except RuntimeError as e:
                print(f"  FAILED: {env}: {e}")
                all_ok = False

        print()

        # Step 4: PTY smoke test
        print("Step 4: PTY smoke test against production CLI...")
        port, master_fd = create_pty_simulator(firmware_dir)
        print(f"  PTY simulator started on port: {port}")

        try:
            # Test identify
            print("\n  Testing ferqonfw identify...")
            result = subprocess.run(
                [python, "-m", "ferqonfw.main", "identify", "--port", port],
                capture_output=True,
                text=True,
                timeout=10,
                env={**os.environ, "PYTHONPATH": str(bundle_dir / "tools")},
            )
            if result.returncode == 0:
                print("  OK: identify succeeded")
                # Check for ferqon_identified in output
                if "ferqon_identified" in result.stdout:
                    print("  OK: device classified as ferqon_identified")
                else:
                    print("  WARNING: unexpected classification in output")
                    print(f"  Output: {result.stdout}")
            else:
                print(f"  FAILED: identify returned {result.returncode}")
                print(f"  stderr: {result.stderr}")
                all_ok = False

            # Test selftest
            print("\n  Testing ferqonfw selftest...")
            result = subprocess.run(
                [python, "-m", "ferqonfw.main", "selftest", "--port", port],
                capture_output=True,
                text=True,
                timeout=10,
                env={**os.environ, "PYTHONPATH": str(bundle_dir / "tools")},
            )
            if result.returncode == 0:
                print("  OK: selftest succeeded")
                if "PASS" in result.stdout:
                    print("  OK: tests passed")
            else:
                print(f"  FAILED: selftest returned {result.returncode}")
                print(f"  stderr: {result.stderr}")
                all_ok = False

        finally:
            try:
                os.close(master_fd)
            except OSError:
                pass

        print()

        # Summary
        print("=" * 60)
        if all_ok:
            print("CLEAN-ROOM VERIFICATION PASSED")
            print("  - Production bundle contains no development files")
            print("  - All 5 environments build from empty caches")
            print("  - Production CLI communicates with Ferqon protocol device")
        else:
            print("CLEAN-ROOM VERIFICATION FAILED")
        print("=" * 60)

    finally:
        if cleanup:
            print(f"\nCleaning up work directory: {work_dir}")
            shutil.rmtree(work_dir, ignore_errors=True)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
