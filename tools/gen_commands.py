#!/usr/bin/env python3
"""
gen_commands.py
---------------
Generates a C++ header (commands.hpp) from commands.json so that
both the Pico firmware and the Pi backend share a single source of
truth for raw-byte command IDs and IO sub-command enums.

Usage:
    python3 gen_commands.py <commands.json> <output.hpp> [pinmap.json]
"""
import json
import sys
from pathlib import Path


def _load_json(path: str) -> dict:
    with open(path) as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return obj


def _resolve_io_peripherals(commands_data: dict, pinmap_path: str | None) -> dict[str, int]:
    io_peripherals = commands_data.get("io_peripherals")
    if io_peripherals:
        return io_peripherals

    if not pinmap_path:
        raise ValueError(
            "commands.json has no 'io_peripherals'. Provide a pinmap file as 3rd argument."
        )

    pinmap = _load_json(pinmap_path)
    pinmap_peripherals = pinmap.get("io_peripherals")
    if not pinmap_peripherals:
        raise ValueError(
            f"Pinmap '{pinmap_path}' has no 'io_peripherals' section."
        )
    return pinmap_peripherals


def generate(commands_path: str, output_path: str, pinmap_path: str | None = None) -> None:
    data = _load_json(commands_path)

    commands_raw = data["commands"]
    if not isinstance(commands_raw, dict):
        raise ValueError("commands must be a JSON object")

    # Raw-byte command schema only:
    # "ping": {"id": 1, ...}
    commands_ids: dict[str, int] = {}
    for name, value in commands_raw.items():
        if isinstance(value, dict) and isinstance(value.get("id"), int):
            commands_ids[name] = int(value["id"])
            continue
        raise ValueError(f"Unsupported command schema for '{name}': expected object with integer 'id'")

    io_periphs: dict[str, int] = _resolve_io_peripherals(data, pinmap_path)

    lines = [
        "// Auto-generated from commands.json — DO NOT EDIT",
        "#pragma once",
        "#include <cstdint>",
        "",
        "namespace ferqon {",
        "namespace cmd {",
        "",
    ]

    for name in commands_ids:
        lines.append(f'    constexpr const char* {name:<10} = "{name}";')

    lines += ["", "} // namespace cmd", "", "namespace cmd_id {", ""]
    for name, value in commands_ids.items():
        lines.append(f"    constexpr uint16_t {name:<10} = 0x{value:04X};")
    lines += ["", "} // namespace cmd_id", ""]

    # -- IO peripheral enum --
    lines.append("enum class IoPeripheral : uint8_t {")
    for name, val in io_periphs.items():
        lines.append(f"    {name:<16} = {val},")
    lines.append("};")
    lines.append("")

    # -- IO action enum --
    io_actions = data.get("io_actions", {})
    if io_actions:
        lines.append("enum class IoAction : uint8_t {")
        for name, val in io_actions.items():
            lines.append(f"    {name:<16} = {val},")
        lines.append("};")
        lines.append("")

    # -- GPIO mode enum --
    gpio_modes = data.get("gpio_modes", {})
    if gpio_modes:
        lines.append("enum class GpioMode : uint8_t {")
        for name, val in gpio_modes.items():
            lines.append(f"    {name:<16} = {val},")
        lines.append("};")
        lines.append("")

    # -- Test mode enum --
    test_modes = data.get("test_modes", {})
    if test_modes:
        lines.append("enum class TestMode : uint8_t {")
        for name, val in test_modes.items():
            lines.append(f"    {name:<16} = {val},")
        lines.append("};")
        lines.append("")

    # close outer namespace
    lines.append("} // namespace ferqon")

    # finally, emit the header file to disk
    outpath = Path(output_path)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    with outpath.open("w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        print(
            f"Usage: {sys.argv[0]} <commands.json> <output.hpp> [pinmap.json]",
            file=sys.stderr,
        )
        sys.exit(1)
    generate(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None)
