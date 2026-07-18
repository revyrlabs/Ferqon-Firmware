# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
cmd_drivers.py
--------------
Drivers command for ferqonfw CLI - driver management.
"""

import json
from ferqonfw.board_loader import get_ssot_dir


def _load_driver_registry() -> dict:
    """Return the driver registry if it exists, otherwise an empty dict."""
    drivers_path = get_ssot_dir() / "drivers.json"
    if not drivers_path.exists():
        return {}
    with open(drivers_path, encoding="utf-8") as f:
        return json.load(f)


def _load_commands() -> dict:
    """Return the command registry from commands.json."""
    commands_path = get_ssot_dir() / "commands.json"
    with open(commands_path, encoding="utf-8") as f:
        return json.load(f).get("commands", {})


def cmd_drivers_list(args) -> int:
    """List drivers and their status."""
    drivers_data = _load_driver_registry()
    if drivers_data:
        print("Builtin drivers (always compiled):")
        for driver in drivers_data.get("builtin", []):
            print(
                f"  {driver['name']:15s} ID: 0x{driver['id']:02X}  {driver['source']}"
            )

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

    # No drivers.json registry yet; fall back to commands list.
    commands = _load_commands()
    if not commands:
        print("No driver or command registry found.")
        return 0

    print("Builtin command handlers (no drivers.json registry present):")
    for name, meta in sorted(commands.items(), key=lambda kv: kv[1].get("id", 0)):
        cmd_id = meta.get("id", 0)
        source = meta.get("source", "")
        print(f"  {name:15s} ID: 0x{cmd_id:02X}  {source}")

    return 0
