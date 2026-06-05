#!/usr/bin/env python3
"""
setup_generated.py
------------------
Creates the pico/generated/ folder and generates commands.hpp from
the shared commands.json and board pinmap.

Run from anywhere inside the repo:
    python3 pico/setup_generated.py

Or from pico/:
    python3 setup_generated.py
"""

import subprocess
import sys
from pathlib import Path

# Locate repo root relative to this file (pico/setup_generated.py → Ferqon/)
PICO_DIR      = Path(__file__).resolve().parent
REPO_ROOT     = PICO_DIR.parent
COMMANDS_JSON_ROOT = REPO_ROOT / "commands.json"
COMMANDS_JSON_NEW = REPO_ROOT / "protocol_sdk" / "sdk" / "serial" / "commands.json"
COMMANDS_JSON_OLD = REPO_ROOT / "commands" / "commands.json"
PINMAP_JSON_ROOT = REPO_ROOT / "protocol_sdk" / "sdk" / "serial" / "driver" / "pico_pinmap.json"
PINMAP_JSON_NEW = REPO_ROOT / "protocol_sdk" / "sdk" / "serial" / "driver" / "pico_pinmap.json"
PINMAP_JSON_OLD = REPO_ROOT / "commands" / "pico_pinmap.json"
GENERATED_DIR = PICO_DIR / "generated"
OUTPUT_HPP    = GENERATED_DIR / "commands.hpp"
GEN_SCRIPT    = PICO_DIR / "gen_commands.py"


def resolve_commands_json() -> Path:
    if COMMANDS_JSON_ROOT.exists():
        return COMMANDS_JSON_ROOT
    if COMMANDS_JSON_NEW.exists():
        return COMMANDS_JSON_NEW
    if COMMANDS_JSON_OLD.exists():
        return COMMANDS_JSON_OLD
    raise FileNotFoundError(
        f"commands.json not found at {COMMANDS_JSON_NEW} or {COMMANDS_JSON_OLD}"
    )


def resolve_pinmap_json() -> Path:
    if PINMAP_JSON_ROOT.exists():
        return PINMAP_JSON_ROOT
    if PINMAP_JSON_NEW.exists():
        return PINMAP_JSON_NEW
    if PINMAP_JSON_OLD.exists():
        return PINMAP_JSON_OLD
    raise FileNotFoundError(
        f"pico_pinmap.json not found at {PINMAP_JSON_NEW} or {PINMAP_JSON_OLD}"
    )

def main() -> None:
    # Validate inputs
    try:
        commands_json = resolve_commands_json()
        pinmap_json = resolve_pinmap_json()
    except FileNotFoundError as exc:
        sys.exit(f"ERROR: {exc}")

    if not GEN_SCRIPT.exists():
        sys.exit(f"ERROR: gen_commands.py not found at {GEN_SCRIPT}")

    # Create generated/ directory
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[setup] directory ready: {GENERATED_DIR}")

    # Run generator
    result = subprocess.run(
        [
            sys.executable,
            str(GEN_SCRIPT),
            str(commands_json),
            str(OUTPUT_HPP),
            str(pinmap_json),
        ],
        check=False,
    )
    if result.returncode != 0:
        sys.exit(f"ERROR: gen_commands.py exited with code {result.returncode}")

    # Print the generated output
    print(f"[setup] generated header:")
    print(OUTPUT_HPP.read_text())

if __name__ == "__main__":
    main()
