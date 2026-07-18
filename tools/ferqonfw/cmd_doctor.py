# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
cmd_doctor.py
-------------
Doctor command for ferqonfw CLI - checks environment and dependencies.
"""

import sys
from pathlib import Path

from ferqonfw.board_loader import (
    get_platforms_dir,
    get_firmware_dir,
    load_all_boards,
    get_ssot_dir,
    get_schemas_dir,
    run_cmd,
)


def check_platformio() -> bool:
    try:
        result = run_cmd(["pio", "--version"], capture=True, check=True)
        print(f"  PlatformIO: {result.stdout.strip()}")
        return True
    except Exception:
        print("  PlatformIO: not found")
        print("    Install with: pip install platformio")
        return False


def check_python() -> bool:
    v = sys.version_info
    ok = v.major >= 3 and v.minor >= 10
    mark = "" if ok else "(requires 3.10+)"
    print(f"  Python: {v.major}.{v.minor}.{v.micro} {mark}".rstrip())
    return ok


def check_pyserial() -> bool:
    try:
        import serial  # noqa: F401

        print("  pyserial: installed")
        return True
    except ImportError:
        print("  pyserial: not found (install with: pip install pyserial)")
        return False


def _check_paths(
    checks: list[tuple[str, Path]], optional: set[str] | None = None
) -> bool:
    all_ok = True
    optional = optional or set()
    for name, path in checks:
        if path.exists():
            print(f"  {name}: found")
        else:
            mark = " (optional)" if name in optional else ""
            print(f"  {name}: not found{mark}")
            if name not in optional:
                all_ok = False
    return all_ok


def check_protocol_dir() -> bool:
    ssot_dir = get_ssot_dir()
    checks = [
        ("protocol/ssot/", ssot_dir),
    ]
    return _check_paths(checks)


def check_ssot_files() -> bool:
    ssot_dir = get_ssot_dir()
    checks = [
        ("commands.json", ssot_dir / "commands.json"),
    ]
    return _check_paths(checks)


def check_schema_files() -> bool:
    schemas_dir = get_schemas_dir()
    checks = [
        ("board.schema.json", schemas_dir / "board.schema.json"),
        ("driver.schema.json", schemas_dir / "driver.schema.json"),
    ]
    # Schemas are optional in the standalone firmware repo.
    return _check_paths(checks, optional={n for n, _ in checks})


def check_boards() -> bool:
    platforms_dir = get_platforms_dir()
    if not platforms_dir.exists():
        print(f"  Platforms directory: not found ({platforms_dir})")
        return False
    print(f"  Platforms directory: {platforms_dir}")

    boards = load_all_boards()
    if not boards:
        print("  Board definitions: none found")
        return False

    print(f"  Board definitions: {len(boards)} board(s)")
    for name, data in sorted(boards.items()):
        pio_env = data.get("pio_env", "?")
        backend = data.get("backend", "?")
        print(f"    - {name} ({backend}) -> env:{pio_env}")
    return True


def check_firmware_dir() -> bool:
    firmware_dir = get_firmware_dir()
    checks = [
        ("platformio.ini", firmware_dir / "platformio.ini"),
        ("src/", firmware_dir / "src"),
        ("platforms/", firmware_dir / "platforms"),
    ]
    return _check_paths(checks)


def cmd_doctor(args) -> int:
    print("=" * 60)
    print("ferqonfw doctor - Environment Health Check")
    print("=" * 60)
    print()

    checks = [
        ("Python", check_python),
        ("PlatformIO", check_platformio),
        ("pyserial", check_pyserial),
        ("Firmware Directory", check_firmware_dir),
        ("Protocol Directory", check_protocol_dir),
        ("SSOT Files", check_ssot_files),
        ("Schema Files", check_schema_files),
        ("Boards", check_boards),
    ]
    results = []
    for name, fn in checks:
        print(f"{name}:")
        results.append(fn())
        print()

    print("=" * 60)
    if all(results):
        print("All checks passed - environment is ready!")
        return 0
    print("Some checks failed - see above for details")
    return 1
