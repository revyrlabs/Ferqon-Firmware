"""
cmd_build.py
------------
Build command for ferqonfw CLI - wraps PlatformIO.
"""

import sys
from typing import Any, Dict

from ferqonfw.board_loader import (
    get_board_pio_env,
    get_firmware_dir,
    get_pio_artifact,
    require_pio,
    run_cmd,
    load_board,
)
from ferqonfw.cmd_validate import cmd_validate


class ValidateArgs:
    """Mock args for validate command."""
    def __init__(self):
        self.json = False


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

    # TODO: Call ferqonfw gen board to generate per-board tables
    # For now, skip this step as it's not yet implemented
    print("TODO: ferqonfw gen board <platform> (not yet implemented)")
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
