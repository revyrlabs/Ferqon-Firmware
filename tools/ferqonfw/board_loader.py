# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
board_loader.py
---------------
Shared utilities for ferqonfw CLI: path resolution, subprocess, board loading.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

# ---------------------------------------------------------------------------
# Path resolver — single source of truth for every filesystem location.
# ---------------------------------------------------------------------------


def get_firmware_dir() -> Path:
    """Return the firmware root directory.

    When running from the source tree or an editable install, the root is
    three levels above this file. When installed as a wheel, we locate it by
    walking up from the current working directory looking for platformio.ini."""
    source_root = Path(__file__).resolve().parent.parent.parent
    markers = ["platformio.ini", "src", "platforms"]
    if all((source_root / m).exists() for m in markers):
        return source_root
    cwd = Path.cwd()
    for path in [cwd, *cwd.parents]:
        if (path / "platformio.ini").exists() and (path / "src").is_dir():
            return path
    return source_root


def get_protocol_dir() -> Path:
    return get_firmware_dir() / "protocol"


def get_ssot_dir() -> Path:
    return get_protocol_dir() / "ssot"


def get_schemas_dir() -> Path:
    return get_firmware_dir() / "tools" / "schemas"


def get_generated_dir() -> Path:
    return get_firmware_dir() / "generated"


def get_platforms_dir() -> Path:
    return get_firmware_dir() / "platforms"


def get_board_yml_path(board_name: str) -> Path:
    return get_platforms_dir() / board_name / "board.yml"


def get_pio_artifact(pio_env: str) -> Path:
    """Return the most likely firmware artifact for the given PlatformIO env."""
    build_dir = get_firmware_dir() / ".pio" / "build" / pio_env
    if build_dir.exists():
        for ext in ("uf2", "bin", "hex", "elf"):
            candidate = build_dir / f"firmware.{ext}"
            if candidate.exists():
                return candidate
    return build_dir / "firmware.uf2"


def get_gen_caps_script() -> Path:
    # This is replaced by ferqonfw gen board
    return get_firmware_dir() / "tools" / "gen_platform_caps.py"


def get_board_generated_dir(board_name: str) -> Path:
    return get_platforms_dir() / board_name / "generated"


def get_pio_path() -> str:
    """Get the PlatformIO CLI executable path.

    Looks on PATH first, then in the same Python environment as this script
    (so a venv-ferqonfw invoked without activation still finds the venv pio)."""
    custom_path = os.getenv("FERQON_PIO_BIN")
    if custom_path:
        return custom_path
    pio_path = shutil.which("pio")
    if pio_path:
        return pio_path
    # Allow running from a venv binary directory even when it is not on PATH.
    venv_bin = os.path.dirname(sys.executable)
    pio_path = shutil.which("pio", path=venv_bin)
    if pio_path:
        return pio_path
    # Fallback to bare executable name; the caller should verify existence
    return "pio"


# ---------------------------------------------------------------------------
# Subprocess wrapper — single place where we shell out.
# ---------------------------------------------------------------------------


def run_cmd(
    argv: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    capture: bool = False,
    check: bool = False,
) -> subprocess.CompletedProcess:
    """Thin wrapper around subprocess.run.

    argv:    command + args
    cwd:     working directory (Path or None)
    capture: capture stdout/stderr as text
    check:   raise CalledProcessError on nonzero exit
    returns: CompletedProcess
    raises:  FileNotFoundError if the binary is missing;
             CalledProcessError if check=True and exit is nonzero.
    """
    # Use full path for pio if needed
    if argv[0] == "pio":
        argv = [get_pio_path()] + list(argv[1:])

    return subprocess.run(
        list(argv),
        cwd=str(cwd) if cwd is not None else None,
        capture_output=capture,
        text=capture,
        check=check,
    )


def require_pio() -> None:
    """Raise RuntimeError with an install hint if `pio` is not on PATH."""
    try:
        run_cmd([get_pio_path(), "--version"], capture=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError(
            "PlatformIO CLI not found. Install with: pip install platformio"
        )


# ---------------------------------------------------------------------------
# Board YAML loading.
# ---------------------------------------------------------------------------


def load_board_schema() -> Optional[Dict[str, Any]]:
    schema_path = get_firmware_dir() / "tools" / "schemas" / "board.schema.json"
    if not schema_path.exists():
        return None
    try:
        with open(schema_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def validate_board_yaml(
    board_data: Dict[str, Any], schema: Optional[Dict[str, Any]]
) -> bool:
    if schema is None:
        return True

    # Check required fields
    for field in schema.get("required", []):
        if field not in board_data:
            print(f"Warning: Board YAML missing required field: {field}")
            return False

    # Validate backend enum
    properties = schema.get("properties", {})
    if "backend" in properties:
        backend = board_data.get("backend")
        valid_backends = properties["backend"].get("enum", [])
        if valid_backends and backend not in valid_backends:
            print(
                f"Warning: Invalid backend '{backend}' "
                f"(expected: {', '.join(valid_backends)})"
            )
            return False

    return True


def load_all_boards() -> Dict[str, Dict[str, Any]]:
    """Load all board YAML files from platforms/<slug>/board.yml."""
    platforms_dir = get_platforms_dir()
    boards: Dict[str, Dict[str, Any]] = {}
    schema = load_board_schema()

    if not platforms_dir.exists():
        print(f"Error: Platforms directory not found: {platforms_dir}")
        return boards

    search_paths = [platforms_dir.glob("*/board.yml")]
    in_development = platforms_dir / "in_development"
    if in_development.exists():
        search_paths.append(in_development.glob("*/board.yml"))

    for board_yml in sorted(p for paths in search_paths for p in paths):
        board_slug = board_yml.parent.name
        try:
            import yaml

            with open(board_yml, encoding="utf-8") as f:
                board_data = yaml.safe_load(f)
            if validate_board_yaml(board_data, schema):
                board_name = board_data.get("board", board_slug)
                boards[board_name] = board_data
        except Exception as e:
            print(f"Warning: Failed to load {board_yml}: {e}")

    return boards


def load_production_boards() -> Dict[str, Dict[str, Any]]:
    """Load only production boards (platforms/<slug>/board.yml).

    Excludes boards under platforms/in_development/.
    """
    platforms_dir = get_platforms_dir()
    boards: Dict[str, Dict[str, Any]] = {}
    schema = load_board_schema()

    if not platforms_dir.exists():
        return boards

    for board_yml in sorted(platforms_dir.glob("*/board.yml")):
        # Skip the in_development directory itself
        if board_yml.parent.name == "in_development":
            continue
        board_slug = board_yml.parent.name
        try:
            import yaml

            with open(board_yml, encoding="utf-8") as f:
                board_data = yaml.safe_load(f)
            if validate_board_yaml(board_data, schema):
                board_name = board_data.get("board", board_slug)
                boards[board_name] = board_data
        except Exception:
            pass

    return boards


def load_board(board_name: str) -> Optional[Dict[str, Any]]:
    """Load a single board YAML directly — no directory scan."""
    yml_path = get_board_yml_path(board_name)
    if not yml_path.exists():
        # In-development boards are kept under platforms/in_development/.
        yml_path = get_platforms_dir() / "in_development" / board_name / "board.yml"
        if not yml_path.exists():
            return None
    try:
        import yaml

        with open(yml_path, encoding="utf-8") as f:
            board_data = yaml.safe_load(f)
    except Exception:
        return None

    schema = load_board_schema()
    if not validate_board_yaml(board_data, schema):
        return None
    return board_data


def get_board_pio_env(board_data: Dict[str, Any]) -> str:
    env = board_data.get("pio_env")
    if not env:
        raise ValueError("board YAML missing required field 'pio_env'")
    return env


def get_board_backend(board_data: Dict[str, Any]) -> str:
    backend = board_data.get("backend")
    if not backend:
        raise ValueError("board YAML missing required field 'backend'")
    return backend


def resolve_firmware_dir(project_dir: Optional[str] = None) -> Path:
    """Resolve firmware directory from an explicit path, env var, or default.

    Priority: explicit project_dir arg > FERQON_FIRMWARE_DIR env var >
    auto-detected firmware dir (parent of tools/).
    """
    firmware_dir = get_firmware_dir()
    override = project_dir or os.environ.get("FERQON_FIRMWARE_DIR")
    if override:
        firmware_dir = Path(override)
    return firmware_dir
