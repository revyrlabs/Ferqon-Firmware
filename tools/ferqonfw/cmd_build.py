# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs
"""
cmd_build.py
------------
Build command for ferqonfw CLI - wraps PlatformIO.
"""


from ferqonfw.board_loader import (
    get_board_pio_env,
    get_firmware_dir,
    get_pio_artifact,
    require_pio,
    run_cmd,
    load_board,
)
from ferqonfw.cmd_validate import cmd_validate
from ferqonfw.cmd_gen import cmd_gen


class ValidateArgs:
    """Mock args for validate command."""

    def __init__(self):
        self.json = False


class GenBoardArgs:
    """Mock args for gen board command."""

    def __init__(self, platform: str):
        self.gen_target = "board"
        self.platform = platform


def cmd_build(args) -> int:
    """Build firmware for a platform using PlatformIO."""
    board_name = args.platform
    board_data = load_board(board_name)

    if not board_data:
        print(f"Error: board '{board_name}' not found")
        print("Run 'ferqonfw list' to see available platforms")
        return 1

    pio_env = get_board_pio_env(board_data)
    firmware_dir = get_firmware_dir()

    print(f"Building firmware for {board_name}...")
    print(f"PlatformIO environment: {pio_env}")
    print()

    try:
        require_pio()
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1

    # Validate SSOT files before build
    print("Validating SSOT files...")
    validate_args = ValidateArgs()
    if cmd_validate(validate_args) != 0:
        print("Error: SSOT validation failed. Fix errors before building.")
        return 1
    print("SSOT validation passed")
    print()

    # Generate per-board capability tables before building
    print(f"Generating per-board tables for {board_name}...")
    gen_args = GenBoardArgs(board_name)
    gen_rc = cmd_gen(gen_args)
    if gen_rc != 0:
        print(f"Error: generation failed for {board_name} (exit code {gen_rc})")
        return gen_rc
    print()

    print(f"Running: pio run -e {pio_env}")
    print("-" * 60)
    result = run_cmd(["pio", "run", "-e", pio_env], cwd=firmware_dir)
    print("-" * 60)

    if result.returncode == 0:
        print(f"Build successful for {board_name}")
        print(f"Firmware location: {get_pio_artifact(pio_env)}")
        return 0
    print(f"Build failed for {board_name}")
    return result.returncode
