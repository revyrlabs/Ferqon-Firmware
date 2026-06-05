"""
cmd_gen.py
----------
Gen command for ferqonfw CLI - generate protocol artifacts.
"""

import json
from pathlib import Path

from ferqonfw.board_loader import (
    get_protocol_dir,
    get_generated_dir,
    get_ssot_dir,
    get_schemas_dir,
)
from ferqonfw.codegen.emit_commands import emit_commands_h
from ferqonfw.codegen.emit_errors import emit_errors_h


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

        # Load SSOT files
        commands_path = ssot_dir / "commands.json"
        errors_path = ssot_dir / "errors.json"

        try:
            with open(commands_path) as f:
                commands_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: {commands_path} not found")
            return 1

        try:
            with open(errors_path) as f:
                errors_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: {errors_path} not found")
            return 1

        # Emit commands.h
        commands_h_path = generated_dir / "commands.h"
        emit_commands_h(commands_data, commands_h_path)
        print(f"  Generated: {commands_h_path}")

        # Emit errors.h
        errors_h_path = generated_dir / "errors.h"
        emit_errors_h(errors_data, errors_h_path)
        print(f"  Generated: {errors_h_path}")

        # TODO: Emit pin_modes.h, drivers_table.h (stubs)
        print("  TODO: pin_modes.h, drivers_table.h (stubs)")
        print("  TODO: Backend Python modules (stubs)")
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
