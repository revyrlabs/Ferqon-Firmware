# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
emit_pin_modes.py
-----------------
Emit pin_modes.h and pin_modes.py.

These functions are not yet implemented.
"""

from pathlib import Path

_MSG = " is not yet implemented."


def emit_pin_modes_h(output_path: Path) -> None:
    """Emit pin_modes.h (C header)."""
    raise NotImplementedError("emit_pin_modes_h" + _MSG)


def emit_pin_modes_py(output_path: Path) -> None:
    """Emit pin_modes.py (Python module)."""
    raise NotImplementedError("emit_pin_modes_py" + _MSG)
