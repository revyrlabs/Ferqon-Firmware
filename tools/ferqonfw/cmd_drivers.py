# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
cmd_drivers.py
--------------
Drivers command for ferqonfw CLI - driver management.
"""

import json
from ferqonfw.board_loader import get_ssot_dir


def cmd_drivers_list(args) -> int:
    """List drivers and their status."""
    ssot_dir = get_ssot_dir()
    drivers_path = ssot_dir / "drivers.json"

    try:
        with open(drivers_path, encoding="utf-8") as f:
            drivers_data = json.load(f)
    except FileNotFoundError:
        print("Error: drivers.json not found")
        return 1

    print("Builtin drivers (always compiled):")
    for driver in drivers_data.get("builtin", []):
        print(f"  {driver['name']:15s} ID: 0x{driver['id']:02X}  {driver['source']}")

    print("\nOptional drivers:")
    for driver in drivers_data.get("optional", []):
        status = "enabled" if driver.get("enabled", False) else "disabled"
        print(
            f"  {driver['name']:15s} ID: 0x{driver['id']:02X}  [{status:7s}]  {driver['source']}"
        )

    print("\nCustom drivers:")
    for driver in drivers_data.get("custom", []):
        status = "enabled" if driver.get("enabled", False) else "disabled"
        print(
            f"  {driver['name']:15s} ID: 0x{driver['id']:02X}  [{status:7s}]  {driver['source']}"
        )

    return 0
