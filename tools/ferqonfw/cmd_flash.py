"""
cmd_flash.py
------------
Flash command for ferqonfw CLI - wraps PlatformIO upload.
"""

from typing import Any, Dict

from ferqonfw.board_loader import (
    get_board_pio_env,
    get_firmware_dir,
    get_pio_artifact,
    require_pio,
    run_cmd,
    load_board,
)


def cmd_flash(args) -> int:
    """Flash firmware to a platform using PlatformIO."""
    board_name = args.platform
    board_data = load_board(board_name)

    if not board_data:
        print(f"Error: board '{board_name}' not found")
        print("Run 'ferqonfw list' to see available platforms")
        return 1

    pio_env = get_board_pio_env(board_data)
    firmware_dir = get_firmware_dir()
    artifact = get_pio_artifact(pio_env)

    print(f"Flashing firmware to {board_name}...")
    print(f"PlatformIO environment: {pio_env}")
    print(f"Artifact: {artifact}")
    print()

    try:
        require_pio()
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1

    if not artifact.exists():
        print(
            f"Error: build artifact missing: {artifact}\n"
            f"Run 'ferqonfw build {board_name}' first."
        )
        return 1

    print(f"Running: pio run -e {pio_env} -t upload")
    print("-" * 60)
    result = run_cmd(
        ["/home/alx/.local/bin/pio", "run", "-e", pio_env, "-t", "upload"],
        cwd=firmware_dir,
    )
    print("-" * 60)

    if result.returncode == 0:
        print(f"Flash successful for {board_name}")
        return 0
    print(f"Flash failed for {board_name}")
    return result.returncode
