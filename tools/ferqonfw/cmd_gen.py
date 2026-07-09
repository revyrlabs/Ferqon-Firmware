# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs
"""
cmd_gen.py
----------
Gen command for ferqonfw CLI - generate protocol and board capability artifacts.
"""

import json
import subprocess
import sys
from pathlib import Path

from ferqonfw.board_loader import (
    get_generated_dir,
    get_ssot_dir,
    get_platforms_dir,
)
from ferqonfw.codegen.emit_errors import emit_errors_h

_TOOLS_DIR = Path(__file__).resolve().parents[1]


def cmd_gen(args) -> int:
    """Generate protocol and board capability artifacts."""
    if not args.gen_target:
        print("Error: gen target required (core, board, or all)")
        return 1

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
            with open(errors_path, encoding="utf-8") as f:
                errors_data = json.load(f)
            errors_h_path = generated_dir / "errors.h"
            emit_errors_h(errors_data, errors_h_path)
            print(f"  Generated: {errors_h_path}")
        except FileNotFoundError:
            pass

        print("Code generation complete")
        return 0

    if args.gen_target == "board":
        platform = args.platform
        board_yml = get_platforms_dir() / platform / "board.yml"
        if not board_yml.exists():
            print(f"Error: board.yml not found for platform '{platform}': {board_yml}")
            return 1

        print(f"Generating per-board capability tables for {platform}...")
        gen_script = _TOOLS_DIR / "gen_platform_caps.py"
        result = subprocess.run(
            [sys.executable, str(gen_script), str(board_yml)],
            capture_output=False,
        )
        if result.returncode != 0:
            print(f"Error: failed to generate capability tables for {platform}")
            return result.returncode

        print(f"Generated capability tables for {platform}")
        return 0

    if args.gen_target == "all":
        print("Generating all protocol artifacts...")

        gen_script = _TOOLS_DIR / "gen_platform_caps.py"
        result = subprocess.run(
            [sys.executable, str(gen_script), "--all"],
            capture_output=False,
        )
        if result.returncode != 0:
            print("Error: failed to generate all board capability tables")
            return result.returncode

        gen_script = _TOOLS_DIR / "gen_protocol.py"
        result = subprocess.run([sys.executable, str(gen_script)], capture_output=False)
        if result.returncode != 0:
            print("Error: failed to generate protocol headers")
            return result.returncode

        # Emit errors.h from the separate errors SSOT if present
        errors_path = ssot_dir / "errors.json"
        try:
            with open(errors_path, encoding="utf-8") as f:
                errors_data = json.load(f)
            errors_h_path = generated_dir / "errors.h"
            emit_errors_h(errors_data, errors_h_path)
            print(f"  Generated: {errors_h_path}")
        except FileNotFoundError:
            pass

        print("All code generation complete")
        return 0

    print(f"Error: unknown gen target: {args.gen_target}")
    return 1
