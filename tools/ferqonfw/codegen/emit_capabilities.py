# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
emit_capabilities.py
---------------------
Emit capabilities.h, pin_caps_table.c, and capabilities_<board>.py from capabilities.<board>.json.

These functions are not yet implemented. Use tools/gen_platform_caps.py
for board capability code generation.
"""

from pathlib import Path

_MSG = " is not yet implemented. Use tools/gen_platform_caps.py for code generation."


def emit_capabilities_h(caps_data: dict, output_path: Path) -> None:
    """Emit capabilities.h (C header)."""
    raise NotImplementedError("emit_capabilities_h" + _MSG)


def emit_pin_caps_table_c(caps_data: dict, output_path: Path) -> None:
    """Emit pin_caps_table.c (C source)."""
    raise NotImplementedError("emit_pin_caps_table_c" + _MSG)


def emit_capabilities_py(caps_data: dict, board_name: str, output_path: Path) -> None:
    """Emit capabilities_<board>.py (Python module)."""
    raise NotImplementedError("emit_capabilities_py" + _MSG)
