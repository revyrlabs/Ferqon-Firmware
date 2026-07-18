# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
cmd_clean.py
------------
Clean command for ferqonfw CLI — removes build artifacts.

Usage:
    ferqonfw clean <board>       Clean artifacts for a single board
    ferqonfw clean all           Clean artifacts for all production boards
"""

from pathlib import Path

from ferqonfw.board_loader import (
    get_board_pio_env,
    get_pio_path,
    require_pio,
    run_cmd,
    load_board,
    load_production_boards,
    resolve_firmware_dir,
)


def _clean_single(board_name: str, pio_env: str, firmware_dir: Path) -> int:
    """Clean a single board. Returns exit code."""
    print(f"Running: pio run -e {pio_env} -t clean")
    print("-" * 60)
    result = run_cmd(
        [get_pio_path(), "run", "-e", pio_env, "-t", "clean"],
        cwd=firmware_dir,
    )
    print("-" * 60)

    if result.returncode == 0:
        print(f"Clean successful for {board_name}")
        return 0
    print(f"Clean failed for {board_name}")
    return result.returncode


def cmd_clean(args) -> int:
    """Clean build artifacts for a platform (or all production platforms)."""
    board_name = args.platform

    try:
        require_pio()
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1

    firmware_dir = resolve_firmware_dir(getattr(args, "project_dir", None))

    # Clean all production boards
    if board_name == "all":
        prod_boards = load_production_boards()
        if not prod_boards:
            print("Error: no production boards found")
            return 1

        print(f"Cleaning {len(prod_boards)} production board(s)...")
        print()
        failed = []
        for name in sorted(prod_boards.keys()):
            pio_env = get_board_pio_env(prod_boards[name])
            print(f"=== Cleaning: {name} (env: {pio_env}) ===")
            rc = _clean_single(name, pio_env, firmware_dir)
            print()
            if rc != 0:
                failed.append(name)

        if failed:
            print(f"Clean failed for: {', '.join(failed)}")
            return 1
        print("All production boards cleaned successfully.")
        return 0

    # Clean a single board
    board_data = load_board(board_name)
    if not board_data:
        print(f"Error: board '{board_name}' not found")
        print("Run 'ferqonfw list' to see available platforms")
        print("Use 'ferqonfw clean all' to clean all production boards.")
        return 1

    pio_env = get_board_pio_env(board_data)
    print(f"Cleaning build artifacts for {board_name}...")
    print(f"PlatformIO environment: {pio_env}")
    print()
    return _clean_single(board_name, pio_env, firmware_dir)
