"""
emit_commands.py
----------------
Emit commands.h and commands.py from commands.json.
"""

from pathlib import Path
import json


def emit_commands_h(commands_data: dict, output_path: Path) -> None:
    """Emit commands.h (C header)."""
    commands = commands_data.get("commands", {})

    lines = []
    lines.append("#ifndef FERQON_COMMANDS_H")
    lines.append("#define FERQON_COMMANDS_H")
    lines.append("")
    lines.append("// Command IDs")
    for name, cmd in sorted(commands.items(), key=lambda x: x[1]["id"]):
        cmd_id = cmd["id"]
        macro_name = f"FERQON_CMD_{name.upper()}"
        lines.append(f"#define {macro_name:30s} 0x{cmd_id:02X}")
    lines.append("")
    lines.append("#endif")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def emit_commands_py(commands_data: dict, output_path: Path) -> None:
    """Emit commands.py (Python module)."""
    commands = commands_data.get("commands", {})

    lines = []
    lines.append("from enum import IntEnum")
    lines.append("")
    lines.append("class FerqonCommand(IntEnum):")
    for name, cmd in sorted(commands.items(), key=lambda x: x[1]["id"]):
        cmd_id = cmd["id"]
        lines.append(f"    {name.upper():20s} = 0x{cmd_id:02X}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
