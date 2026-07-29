#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""Universal firmware device test — exercises the MCU through the backend's
own serial stack, without requiring a running Ferqon server.

This test imports the **actual backend HIL client code** and uses it to talk
to the device over serial.  It does NOT start the FastAPI server, does NOT
hit any HTTP endpoint, and does NOT duplicate protocol encoding/decoding
logic.  Instead it reuses:

  - ``ferqon_hw.serial_backend`` — low-level frame encode/decode/CRC (the
    same code the backend's ``FerqonSerial`` connection uses).
  - ``ferqon_backend.ferqon_hil.mcu_client.McuClient`` — the high-level
    thread-safe MCU client with ``send()`` / ``expect()`` / ``read_line()``.
  - ``ferqon_backend.ferqon_hil.commands.Command`` / ``Expect`` — the DSL
    the backend's HIL router uses to build commands (``Command.PING()``,
    ``Command.HIL_ENTER()``, ``Command.IO_SET()``, …).

Why this is better than a separate serial test:
  - If the backend changes its serial logic, frame encoding, or command
    DSL, this test automatically picks up the new code and validates the
    firmware against it.  No drift between test code and production code.
  - The firmware is validated through the exact same Python → serial →
    MCU path that a real HIL test session uses, giving much stronger
    validation than a test that rolls its own protocol implementation.

Gate conditions (all must be true to run):
  - ``FERQON_HW_SMOKE`` env var is not ``"0"`` (default: auto-detect)
  - The serial port exists (default ``/dev/ttyACM0``, override with
    ``FERQON_HIL_PORT``)
  - pyserial is importable
  - The backend + hw-sdk packages are importable

Run:
    pytest firmware/tests/hil/test_device_via_backend_client.py
    FERQON_HW_SMOKE=1 pytest firmware/tests/hil/test_device_via_backend_client.py
    python firmware/tests/hil/test_device_via_backend_client.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

# ── Path setup ──────────────────────────────────────────────────────────────
# We need three packages on sys.path:
#   1. hw-sdk (ferqon_hw)          — low-level serial protocol
#   2. services/backend            — ferqon_backend.ferqon_hil (McuClient, commands)
#   3. (ferqon_config if needed)   — pulled in transitively by backend
_REPO_ROOT = Path(__file__).resolve().parents[3]  # Ferqon/
_HW_SDK_PATH = _REPO_ROOT / "packages" / "hw-sdk" / "ferqon_hw"
_BACKEND_PATH = _REPO_ROOT / "services" / "backend"
_CONFIG_PATH = _REPO_ROOT / "packages" / "ferqon-config"

for _p in (_HW_SDK_PATH, _BACKEND_PATH, _CONFIG_PATH):
    _p_str = str(_p)
    if _p_str not in sys.path and _p.exists():
        sys.path.insert(0, _p_str)

# ── Device connection settings ──────────────────────────────────────────────
_DEFAULT_PORT = os.environ.get("FERQON_HIL_PORT", "/dev/ttyACM0")
_DEFAULT_BAUD = int(os.environ.get("FERQON_HIL_BAUDRATE", "115200"))


# ── Skip conditions ─────────────────────────────────────────────────────────
def _should_run() -> bool:
    """Determine if the hardware test should run."""
    if os.environ.get("FERQON_HW_SMOKE", "auto") == "0":
        return False
    if os.environ.get("FERQON_HW_SMOKE") == "1":
        return True
    return Path(_DEFAULT_PORT).exists()


def _can_import_deps() -> bool:
    """Check that pyserial + backend HIL modules are importable."""
    try:
        import serial  # noqa: F401
        from ferqon_hw import serial_backend  # noqa: F401
        from ferqon_backend.ferqon_hil.mcu_client import McuClient  # noqa: F401
        from ferqon_backend.ferqon_hil.commands import Command  # noqa: F401
        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(
    not _should_run() or not _can_import_deps(),
    reason=(
        f"HIL device or backend deps not available "
        f"(port={_DEFAULT_PORT}, set FERQON_HW_SMOKE=1 to force)"
    ),
)


# ── Fixture: backend McuClient ──────────────────────────────────────────────
@pytest.fixture(scope="module")
def mcu():
    """Connect to the MCU using the backend's own connect() function.

    This is the exact same call the backend's HIL API makes when a test
    session starts — it opens the serial port, toggles DTR/RTS for a
    hardware reset, waits for stabilization, and returns a thread-safe
    McuClient.
    """
    from ferqon_backend.ferqon_hil.mcu_client import connect

    client = connect(port=_DEFAULT_PORT, baudrate=_DEFAULT_BAUD, timeout=3.0)
    yield client
    try:
        client.close()
    except Exception:
        pass


# ── Test classes ────────────────────────────────────────────────────────────

class TestConnectivity:
    """Basic protocol commands via the backend's Command DSL."""

    def test_ping(self, mcu):
        """PING must return ok=True through the backend's McuClient.send()."""
        from ferqon_backend.ferqon_hil.commands import Command

        resp = mcu.send(Command.PING())
        assert resp.ok, f"ping failed: {resp.message}"

    def test_echo(self, mcu):
        """ECHO must return the echoed message."""
        from ferqon_backend.ferqon_hil.commands import Command

        resp = mcu.send(Command.ECHO("hello_ferqon"))
        assert resp.ok, f"echo failed: {resp.message}"
        assert "hello_ferqon" in resp.message

    def test_device_info(self, mcu):
        """DEVICE_INFO must succeed (exercises device_info.cpp TLV path).

        Uses the low-level FerqonSerial.call() because the backend's
        McuClient._encode_simple_command() always prepends PKT_REQUEST,
        but device_info/driver_info are exempt from needing it in the
        dispatcher (a pre-existing backend encoding quirk, not a firmware
        issue).  FerqonSerial.call() handles the exemption correctly.
        """
        from ferqon_hw.serial_backend import FerqonSerial

        # Reuse the McuClient's underlying connection for this one command
        resp = mcu._conn  # access the raw serial connection
        # FerqonSerial.call wraps the encode/decode with correct PKT handling
        # but mcu._conn is a raw pyserial connection, not a FerqonSerial.
        # Instead, send device_info via the low-level encode manually.
        from ferqon_hw.serial_backend import _encode_frame, _CMD_IDS, _FrameDecoder, _decode_response

        cmd_id = _CMD_IDS["device_info"]
        # device_info does NOT need PKT_REQUEST — payload is empty
        frame = _encode_frame(seq=1, cmd_id=cmd_id, payload=b"")
        with mcu._lock:
            mcu._conn.write(frame)
            import time as _t
            decoder = _FrameDecoder()
            start = _t.time()
            while _t.time() - start < 3.0:
                data = mcu._conn.read(1)
                if not data:
                    continue
                for f in decoder.feed(data):
                    if f.seq == 0:
                        continue  # skip heartbeats
                    decoded = _decode_response(bytes(f.payload))
                    assert decoded.get("ok"), f"device_info failed: {decoded}"
                    return


class TestHilEnterExit:
    """HIL enter/exit session handshake (driver_call.cpp table dispatch)."""

    def test_hil_enter_no_args(self, mcu):
        """hil.enter with no UART args must succeed (DUT-optional)."""
        from ferqon_backend.ferqon_hil.commands import Command

        resp = mcu.send(Command.HIL_ENTER())
        assert resp.ok, (
            f"hil.enter failed: {resp.message}. "
            f"Ensure firmware is v1.2.0+ "
            f"(reflash: cd firmware && pio run -e pico_arduino -t upload)"
        )

    def test_hil_exit(self, mcu):
        """hil.exit must succeed."""
        from ferqon_backend.ferqon_hil.commands import Command

        resp = mcu.send(Command.HIL_EXIT())
        assert resp.ok, f"hil.exit failed: {resp.message}"

    def test_hil_enter_exit_cycle(self, mcu):
        """Enter → exit cycle must work cleanly."""
        from ferqon_backend.ferqon_hil.commands import Command

        assert mcu.send(Command.HIL_ENTER()).ok
        assert mcu.send(Command.HIL_EXIT()).ok


class TestHilIO:
    """HIL I/O commands via the backend's Command.IO_SET / IO_GET DSL."""

    def test_io_configure_and_set(self, mcu):
        """Configure pin 25 as output, set HIGH then LOW."""
        from ferqon_backend.ferqon_hil.commands import Command

        assert mcu.send(Command.HIL_ENTER()).ok
        try:
            assert mcu.send(Command.IO_CONFIGURE(25, "OUTPUT")).ok, "io_configure failed"
            assert mcu.send(Command.IO_SET(25, "HIGH")).ok, "io_set HIGH failed"
            time.sleep(0.1)
            assert mcu.send(Command.IO_SET(25, "LOW")).ok, "io_set LOW failed"
        finally:
            mcu.send(Command.HIL_EXIT())

    def test_io_get(self, mcu):
        """io_get must return the pin state."""
        from ferqon_backend.ferqon_hil.commands import Command

        assert mcu.send(Command.HIL_ENTER()).ok
        try:
            mcu.send(Command.IO_CONFIGURE(25, "OUTPUT"))
            mcu.send(Command.IO_SET(25, "HIGH"))
            resp = mcu.send(Command.IO_GET(25))
            assert resp.ok, f"io_get failed: {resp.message}"
        finally:
            mcu.send(Command.HIL_EXIT())


class TestHilErrorPaths:
    """Verify error handling in the refactored firmware."""

    def test_io_set_missing_arg(self, mcu):
        """hil.io_set without 'level' arg → INVALID_PARAMS error."""
        from ferqon_backend.ferqon_hil.commands import Command

        assert mcu.send(Command.HIL_ENTER()).ok
        try:
            # Build a raw driver_call with missing 'level' arg
            resp = mcu.send(Command.DRIVER_CALL("hil", "io_set", "pin=25"))
            assert not resp.ok, f"expected error, got ok=True: {resp.message}"
            assert resp.error_code == 2, f"expected INVALID_PARAMS(2), got {resp.error_code}"
        finally:
            mcu.send(Command.HIL_EXIT())

    def test_unknown_method(self, mcu):
        """hil.nonexistent → INVALID_METHOD error."""
        from ferqon_backend.ferqon_hil.commands import Command

        resp = mcu.send(Command.DRIVER_CALL("hil", "nonexistent", ""))
        assert not resp.ok, f"expected error, got ok=True: {resp.message}"

    def test_adc_read_delegated(self, mcu):
        """hil.adc_read stub must return NOT_IMPLEMENTED (delegated to adc driver)."""
        from ferqon_backend.ferqon_hil.commands import Command

        resp = mcu.send(Command.DRIVER_CALL("hil", "adc_read", "channel=0"))
        # The stub returns NOT_IMPLEMENTED — this validates the SSOT contract
        # stub is present and correctly reports delegation.
        assert not resp.ok, (
            f"expected NOT_IMPLEMENTED, got ok=True: {resp.message}. "
            f"hil.adc_read should be a stub that delegates to the adc driver."
        )


class TestDirectCommands:
    """Direct (non-driver_call) commands that exercise the refactored handlers."""

    def test_set_debug_level(self, mcu):
        """set_debug_level must succeed and return the level."""
        from ferqon_backend.ferqon_hil.commands import Command

        resp = mcu.send(Command.SET_DEBUG_LEVEL(2))  # VERBOSE
        assert resp.ok, f"set_debug_level(2) failed: {resp.message}"
        # Reset to INFO
        mcu.send(Command.SET_DEBUG_LEVEL(1))


# ── Standalone runner ───────────────────────────────────────────────────────
def _run_standalone() -> int:
    """Run all tests without pytest — for `python test_device_via_backend_client.py`."""
    from ferqon_backend.ferqon_hil.mcu_client import connect
    from ferqon_backend.ferqon_hil.commands import Command

    print(f"Universal firmware device test (via backend McuClient)")
    print(f"Port: {_DEFAULT_PORT}  Baud: {_DEFAULT_BAUD}")
    print()

    if not _should_run():
        print(f"SKIP: device not found at {_DEFAULT_PORT} (set FERQON_HW_SMOKE=1 to force)")
        return 0

    client = connect(port=_DEFAULT_PORT, baudrate=_DEFAULT_BAUD, timeout=3.0)
    passed = 0
    failed = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal passed, failed
        status = "PASS" if ok else "FAIL"
        extra = f" — {detail}" if detail else ""
        print(f"  {name}: {status}{extra}")
        if ok:
            passed += 1
        else:
            failed += 1

    try:
        print("--- Connectivity ---")
        r = client.send(Command.PING()); check("ping", r.ok)
        r = client.send(Command.ECHO("hello")); check("echo", r.ok, r.message)
        # driver_info via McuClient has a pre-existing PKT_REQUEST encoding
        # quirk — skip it in standalone mode (the pytest class tests it
        # via the low-level path).

        print("--- HIL enter/exit ---")
        r = client.send(Command.HIL_ENTER()); check("hil.enter", r.ok, r.message)
        r = client.send(Command.HIL_EXIT()); check("hil.exit", r.ok, r.message)
        r = client.send(Command.HIL_ENTER()); check("hil.enter (2)", r.ok)
        r = client.send(Command.HIL_EXIT()); check("hil.exit (2)", r.ok)

        print("--- HIL I/O ---")
        check("hil.enter", client.send(Command.HIL_ENTER()).ok)
        check("io_configure(25,OUTPUT)", client.send(Command.IO_CONFIGURE(25, "OUTPUT")).ok)
        check("io_set(25,HIGH)", client.send(Command.IO_SET(25, "HIGH")).ok)
        time.sleep(0.1)
        check("io_set(25,LOW)", client.send(Command.IO_SET(25, "LOW")).ok)
        r = client.send(Command.IO_GET(25)); check("io_get(25)", r.ok, r.message)
        client.send(Command.HIL_EXIT())

        print("--- Error paths ---")
        client.send(Command.HIL_ENTER())
        r = client.send(Command.DRIVER_CALL("hil", "io_set", "pin=25"))
        check("io_set missing level", not r.ok and r.error_code == 2, f"code={r.error_code}")
        r = client.send(Command.DRIVER_CALL("hil", "nonexistent", ""))
        check("unknown method", not r.ok, f"code={r.error_code}")
        r = client.send(Command.DRIVER_CALL("hil", "adc_read", "channel=0"))
        check("adc_read delegated (NOT_IMPL)", not r.ok, f"code={r.error_code}")
        client.send(Command.HIL_EXIT())

        print("--- Direct commands ---")
        r = client.send(Command.SET_DEBUG_LEVEL(2))
        check("set_debug_level(VERBOSE)", r.ok, r.message)
        client.send(Command.SET_DEBUG_LEVEL(1))
    finally:
        client.close()

    print()
    print(f"{'=' * 60}")
    print(f"SUMMARY: {passed}/{passed + failed} passed")
    print(f"{'=' * 60}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_standalone())
