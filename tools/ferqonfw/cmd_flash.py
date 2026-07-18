# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
cmd_flash.py
------------
Flash command for ferqonfw CLI - wraps PlatformIO upload.

With --build, the firmware is built first and then flashed in one step.
Without --build, a prior `ferqonfw build` is required.
"""

from ferqonfw.board_loader import (
    get_board_pio_env,
    get_pio_artifact,
    get_pio_path,
    require_pio,
    run_cmd,
    load_board,
    resolve_firmware_dir,
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
    firmware_dir = resolve_firmware_dir(getattr(args, "project_dir", None))
    artifact = get_pio_artifact(pio_env)

    try:
        require_pio()
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1

    # Build first if --build was passed
    build_first = getattr(args, "build", False)
    if build_first:
        print(f"Building firmware for {board_name}...")
        print(f"PlatformIO environment: {pio_env}")
        print(f"Running: pio run -e {pio_env}")
        print("-" * 60)
        build_result = run_cmd([get_pio_path(), "run", "-e", pio_env], cwd=firmware_dir)
        print("-" * 60)
        if build_result.returncode != 0:
            print(f"Build failed for {board_name}")
            return build_result.returncode
        print(f"Build successful for {board_name}")
        print()

    print(f"Flashing firmware to {board_name}...")
    print(f"PlatformIO environment: {pio_env}")
    print(f"Artifact: {artifact}")
    print()

    if not artifact.exists():
        print(
            f"Error: build artifact missing: {artifact}\n"
            f"Run 'ferqonfw build {board_name}' first, "
            f"or use 'ferqonfw flash {board_name} --build'."
        )
        return 1

    upload_port = getattr(args, "port", None)
    port_hint = f" --upload-port {upload_port}" if upload_port else ""
    print(f"Running: pio run -e {pio_env} -t upload{port_hint}")
    print("-" * 60)
    upload_cmd = [get_pio_path(), "run", "-e", pio_env, "-t", "upload"]

    if upload_port:
        upload_cmd += ["--upload-port", upload_port]

    result = run_cmd(upload_cmd, cwd=firmware_dir)
    print("-" * 60)

    if result.returncode == 0:
        print(f"Flash successful for {board_name}")
        return 0
    print(f"Flash failed for {board_name}")
    return result.returncode
