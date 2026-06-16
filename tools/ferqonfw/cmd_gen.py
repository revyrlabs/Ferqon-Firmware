"""
cmd_gen.py
----------
Gen command for ferqonfw CLI - generate protocol artifacts.
"""

import json
import subprocess
import sys
from pathlib import Path

from ferqonfw.board_loader import (
    get_protocol_dir,
    get_generated_dir,
    get_ssot_dir,
    get_schemas_dir,
)
from ferqonfw.codegen.emit_errors import emit_errors_h

_TOOLS_DIR = Path(__file__).resolve().parents[1]


def cmd_gen(args) -> int:
    """Generate protocol artifacts."""
    if not args.gen_target:
        print("Error: gen target required (core, board, or all)")
        return 1

    protocol_dir = get_protocol_dir()
    generated_dir = get_generated_dir()
    ssot_dir = get_ssot_dir()

    # Ensure generated directory exists
    generated_dir.mkdir(parents=True, exist_ok=True)

    if args.gen_target == "core":
        print("Generating board-agnostic protocol headers...")

        # All command artifacts are emitted by gen_protocol.py
        gen_script = _TOOLS_DIR / "gen_protocol.py"
        result = subprocess.run([sys.executable, str(gen_script)], capture_output=False)
        if result.returncode != 0:
            return result.returncode

        # Emit errors.h from the separate errors SSOT if present
        errors_path = ssot_dir / "errors.json"
        try:
            with open(errors_path) as f:
                errors_data = json.load(f)
            errors_h_path = generated_dir / "errors.h"
            emit_errors_h(errors_data, errors_h_path)
            print(f"  Generated: {errors_h_path}")
        except FileNotFoundError:
            pass

        print("Code generation complete")
        return 0
    elif args.gen_target == "board":
        platform = args.platform
        print(f"Generating per-board tables for {platform}...")
        # TODO: Implement code generation
        print("TODO: Emit capabilities.h, pin_caps_table.c")
        print("Code generation not yet implemented")
        return 0
    elif args.gen_target == "all":
        print("Generating all protocol artifacts...")
        # TODO: Implement code generation
        print("TODO: Emit both board-agnostic and per-board artifacts")
        print("Code generation not yet implemented")
        return 0
    else:
        print(f"Error: unknown gen target: {args.gen_target}")
        return 1
