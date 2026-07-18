# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
cmd_build.py
------------
Build command for ferqonfw CLI — the production build interface.

Production-safe: does NOT run code generators. Builds from committed
artifacts only. The pre-build hook (pio_pre_build.py) verifies that
required board artifacts exist and fails closed if they are missing.

Usage:
    ferqonfw build <board>       Build a single board
    ferqonfw build all           Build all production boards
"""

from pathlib import Path

from ferqonfw.board_loader import (
    get_board_pio_env,
    get_pio_artifact,
    get_pio_path,
    require_pio,
    run_cmd,
    load_board,
    load_production_boards,
    resolve_firmware_dir,
)


def _build_single(board_name: str, pio_env: str, firmware_dir: Path) -> int:
    """Build a single board. Returns exit code."""
    print(f"Running: pio run -e {pio_env}")
    print("-" * 60)
    result = run_cmd([get_pio_path(), "run", "-e", pio_env], cwd=firmware_dir)
    print("-" * 60)

    if result.returncode == 0:
        print(f"Build successful for {board_name}")
        print(f"Firmware location: {get_pio_artifact(pio_env)}")
        return 0
    print(f"Build failed for {board_name}")
    return result.returncode


def cmd_build(args) -> int:
    """Build firmware for a platform (or all production platforms)."""
    board_name = args.platform

    try:
        require_pio()
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1

    firmware_dir = resolve_firmware_dir(getattr(args, "project_dir", None))

    # Build all production boards
    if board_name == "all":
        prod_boards = load_production_boards()
        if not prod_boards:
            print("Error: no production boards found")
            return 1

        print(f"Building {len(prod_boards)} production board(s)...")
        print()
        failed = []
        for name in sorted(prod_boards.keys()):
            pio_env = get_board_pio_env(prod_boards[name])
            print(f"=== Building: {name} (env: {pio_env}) ===")
            rc = _build_single(name, pio_env, firmware_dir)
            print()
            if rc != 0:
                failed.append(name)

        if failed:
            print(f"Build failed for: {', '.join(failed)}")
            return 1
        print("All production boards built successfully.")
        return 0

    # Build a single board
    board_data = load_board(board_name)
    if not board_data:
        print(f"Error: board '{board_name}' not found")
        print("Run 'ferqonfw list' to see available platforms")
        print("Use 'ferqonfw build all' to build all production boards.")
        return 1

    pio_env = get_board_pio_env(board_data)
    print(f"Building firmware for {board_name}...")
    print(f"PlatformIO environment: {pio_env}")
    print(f"Firmware directory: {firmware_dir}")
    print()
    return _build_single(board_name, pio_env, firmware_dir)
