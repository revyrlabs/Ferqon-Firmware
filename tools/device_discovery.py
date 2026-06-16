"""
Device discovery and resolution for Ferqon testing.

Provides multi-board auto-detection via USB VID/PID and emulator fallback.
Pure module with no import-time side effects.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

log = logging.getLogger(__name__)

# USB VID/PID registry for known boards (extend as needed)
# Format: board_name -> (vid, pid) or vid only (pid=None for any PID)
_BOARD_USB_REGISTRY = {
    "pico": (0x2E8A, None),  # Raspberry Pi Pico (any PID)
    "rpipico": (0x2E8A, None),  # Raspberry Pi Pico (DUT profile name)
    "esp32": (0x10C4, 0x805A),  # Espressif ESP32
    "esp32s3": (0x10C4, 0x805B),  # Espressif ESP32-S3
    "teensy40": (0x16C0, 0x0478),  # Teensy 4.0
    "teensy41": (0x16C0, 0x0478),  # Teensy 4.1 (same VID/PID)
}

# Port hint patterns from board_profiles.yaml
_PORT_HINT_PATTERNS = {
    "pico": "/dev/ttyACM",
    "rpipico": "/dev/ttyACM",
    "uno": "/dev/ttyACM",
    "nano": "/dev/ttyUSB",
    "esp32": "/dev/ttyUSB",
}


def find_board(board: Optional[str] = None) -> Optional[str]:
    """Find a connected board by USB VID/PID or port pattern.

    Args:
        board: Board name to search for (e.g., "pico", "esp32").
               If None, searches for any known board.

    Returns:
        Serial port path (e.g., "/dev/ttyACM0") or None if not found.
    """
    if serial is None or list_ports is None:
        log.warning("pyserial not available; device discovery disabled")
        return None

    boards_to_check = [board] if board else list(_BOARD_USB_REGISTRY.keys())

    for board_name in boards_to_check:
        vid_pid = _BOARD_USB_REGISTRY.get(board_name)
        if not vid_pid:
            continue

        vid, pid = vid_pid

        for port_info in list_ports.comports():
            # Check VID match
            if port_info.vid != vid:
                continue

            # Check PID if specified
            if pid is not None and port_info.pid != pid:
                continue

            # Check port pattern if available
            port_hint = _PORT_HINT_PATTERNS.get(board_name)
            if port_hint and not port_info.device.startswith(port_hint):
                continue

            log.info("Found board '%s' at %s (VID:PID=0x%04X:0x%04X)",
                     board_name, port_info.device, port_info.vid, port_info.pid)
            return port_info.device

    if board:
        log.info("Board '%s' not found", board)
    else:
        log.info("No known boards found")

    return None


def resolve_device(prefer_hw: bool = True, board: Optional[str] = None) -> str:
    """Resolve a device target: auto-detect hardware or start emulator.

    Args:
        prefer_hw: If True, try hardware first, fall back to emulator.
                   If False, use emulator immediately.
        board: Board name to search for (e.g., "pico", "esp32").
               Only used when prefer_hw=True.

    Returns:
        Serial port path (real or PTY) for use with serial clients.

    Raises:
        RuntimeError: If neither hardware nor emulator is available.
    """
    if prefer_hw:
        hw_port = find_board(board)
        if hw_port:
            log.info("Using hardware device: %s", hw_port)
            return hw_port
        log.info("No hardware device found → falling back to emulator")

    # Fallback to emulator
    return _start_emulator()


def _start_emulator() -> str:
    """Start the Ferqon emulator in PTY mode and return its port.

    Returns:
        PTY port path (e.g., "/dev/pts/5").

    Raises:
        RuntimeError: If emulator cannot be started.
    """
    try:
        # Add tools to path to import ferqon_emulator
        tools_dir = Path(__file__).parent
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))

        from ferqon_emulator import FerqonEmulator

        emulator = FerqonEmulator(pty=True)
        port = emulator.start()
        log.info("Started emulator on PTY: %s", port)

        # Store emulator instance for cleanup (caller's responsibility)
        # For now, we return the port and let the emulator run as daemon
        return port

    except ImportError as e:
        raise RuntimeError(f"Failed to import ferqon_emulator: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to start emulator: {e}")


def list_connected_boards() -> dict[str, str]:
    """List all connected boards and their ports.

    Returns:
        Dict mapping board name to port path.
    """
    if serial is None or list_ports is None:
        return {}

    result = {}
    for board_name, (vid, pid) in _BOARD_USB_REGISTRY.items():
        for port_info in list_ports.comports():
            if port_info.vid != vid:
                continue
            if pid is not None and port_info.pid != pid:
                continue
            if board_name not in result:  # First match wins
                result[board_name] = port_info.device

    return result


__all__ = [
    "find_board",
    "resolve_device",
    "list_connected_boards",
]
