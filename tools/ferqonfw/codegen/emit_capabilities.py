# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs
"""
emit_capabilities.py
---------------------
Emit capabilities.h, pin_caps_table.c, and capabilities_<board>.py from capabilities.<board>.json.
"""

from pathlib import Path


def emit_capabilities_h(caps_data: dict, output_path: Path) -> None:
    """Emit capabilities.h (C header)."""
    # TODO: Implement C header generation
    raise NotImplementedError("emit_capabilities_h not yet implemented")


def emit_pin_caps_table_c(caps_data: dict, output_path: Path) -> None:
    """Emit pin_caps_table.c (C source)."""
    # TODO: Implement C source generation
    raise NotImplementedError("emit_pin_caps_table_c not yet implemented")


def emit_capabilities_py(caps_data: dict, board_name: str, output_path: Path) -> None:
    """Emit capabilities_<board>.py (Python module)."""
    # TODO: Implement Python module generation
    raise NotImplementedError("emit_capabilities_py not yet implemented")
