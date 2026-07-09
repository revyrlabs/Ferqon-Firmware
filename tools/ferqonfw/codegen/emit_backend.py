# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
emit_backend.py
---------------
Emit backend Python modules (commands.py, errors.py, pin_modes.py, capabilities_<board>.py).
"""

from pathlib import Path


def emit_backend_commands_py(commands_data: dict, output_path: Path) -> None:
    """Emit commands.py for backend."""
    # TODO: Implement Python module generation
    raise NotImplementedError("emit_backend_commands_py not yet implemented")


def emit_backend_errors_py(errors_data: dict, output_path: Path) -> None:
    """Emit errors.py for backend."""
    # TODO: Implement Python module generation
    raise NotImplementedError("emit_backend_errors_py not yet implemented")


def emit_backend_pin_modes_py(output_path: Path) -> None:
    """Emit pin_modes.py for backend."""
    # TODO: Implement Python module generation
    raise NotImplementedError("emit_backend_pin_modes_py not yet implemented")


def emit_backend_capabilities_py(
    caps_data: dict, board_name: str, output_path: Path
) -> None:
    """Emit capabilities_<board>.py for backend."""
    # TODO: Implement Python module generation
    raise NotImplementedError("emit_backend_capabilities_py not yet implemented")
