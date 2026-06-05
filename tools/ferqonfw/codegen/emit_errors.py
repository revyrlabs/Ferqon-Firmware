"""
emit_errors.py
--------------
Emit errors.h and errors.py from errors.json.
"""

from pathlib import Path
import json


def emit_errors_h(errors_data: dict, output_path: Path) -> None:
    """Emit errors.h (C header)."""
    errors = errors_data.get("errors", [])

    lines = []
    lines.append("#ifndef FERQON_ERRORS_H")
    lines.append("#define FERQON_ERRORS_H")
    lines.append("")
    lines.append("// Error codes")
    for err in sorted(errors, key=lambda x: x["code"]):
        err_code = err["code"]
        err_name = err["name"]
        macro_name = f"FERQON_ERR_{err_name}"
        lines.append(f"#define {macro_name:30s} {err_code}")
    lines.append("")
    lines.append("#endif")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def emit_errors_py(errors_data: dict, output_path: Path) -> None:
    """Emit errors.py (Python module)."""
    errors = errors_data.get("errors", [])

    lines = []
    lines.append("from enum import IntEnum")
    lines.append("")
    lines.append("class FerqonErrorCode(IntEnum):")
    for err in sorted(errors, key=lambda x: x["code"]):
        err_code = err["code"]
        err_name = err["name"]
        lines.append(f"    {err_name:20s} = {err_code}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
