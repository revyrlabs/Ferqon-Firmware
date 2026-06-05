#!/usr/bin/env python3
"""
gen_driver_map.py
-----------------
Generates driver method mapping from commands.json for the backend.

Outputs:
  - hw_sdk/ferqon_hw/ferqon_hw/_driver_method_map.py

This script reads the driver_methods section from commands.json and generates
a Python dictionary mapping (driver, method) tuples to their native command
encodings.
"""

import json
import sys
from pathlib import Path

# Paths relative to repo root
REPO_ROOT = Path(__file__).parent.parent.parent
SSOT_PATH = REPO_ROOT / "firmware" / "protocol" / "ssot" / "commands.json"
OUTPUT_PATH = REPO_ROOT / "hw_sdk" / "ferqon_hw" / "ferqon_hw" / "_driver_method_map.py"


def load_commands() -> dict:
    with open(SSOT_PATH) as f:
        return json.load(f)


def generate_driver_map(data: dict) -> str:
    """Generate Python driver method mapping."""
    lines = [
        "# Auto-generated from firmware/protocol/ssot/commands.json.",
        "# DO NOT EDIT — regenerate with: python3 firmware/tools/gen_driver_map.py",
        "",
        "# Mapping of (driver, method) tuples to native command encodings.",
        "# Each entry contains:",
        "#   - native_cmd: the native command name (e.g., 'gpio_write')",
        "#   - arg_map: dict of arg_name -> type (e.g., {'pin': 'u8', 'level': 'bool_high_low'})",
        "#   - sub_handler: optional sub-handler name for driver_call dispatch",
        "",
        "DRIVER_METHOD_MAP = {",
    ]

    commands = data.get("commands", {})
    driver_call = commands.get("driver_call", {})
    driver_methods = driver_call.get("driver_methods", {})

    for driver, methods in driver_methods.items():
        for method, config in methods.items():
            native_cmd = config.get("native_cmd", "")
            arg_map = config.get("arg_map", {})
            sub_handler = config.get("sub_handler", "")

            # Format arg_map as Python dict literal
            arg_map_str = "{"
            for i, (arg_name, arg_type) in enumerate(arg_map.items()):
                if i > 0:
                    arg_map_str += ", "
                arg_map_str += f'"{arg_name}": "{arg_type}"'
            arg_map_str += "}"

            # Format sub_handler if present
            sub_handler_str = f', "sub_handler": "{sub_handler}"' if sub_handler else ""

            lines.append(f'    ("{driver}", "{method}"): {{')
            lines.append(f'        "native_cmd": "{native_cmd}",')
            lines.append(f'        "arg_map": {arg_map_str},')
            if sub_handler:
                lines.append(f'        "sub_handler": "{sub_handler}",')
            lines.append(f'    }},')

    lines.append("}")
    return "\n".join(lines)


def main() -> int:
    data = load_commands()

    content = generate_driver_map(data)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(content)
    print(f"Generated: {OUTPUT_PATH}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
