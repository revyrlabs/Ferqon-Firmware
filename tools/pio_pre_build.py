#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
pio_pre_build.py
----------------
PlatformIO pre-build hook for production Ferqon firmware builds.

Responsibilities (production-safe, fail-closed):
  1. Emit ``generated/build_timestamp.h`` (honors SOURCE_DATE_EPOCH).
  2. Emit ``generated/production_config.h`` from ``tools/production_config.json``,
     applying validated FERQON_* build-time overrides.
  3. Verify that the per-board committed generated artifacts
     (platform_caps.h) exist for the current environment.  Fail closed
     if they are missing — production builds must not silently fall back
     to stale root-level copies.

This hook does NOT run code generators (gen_protocol.py, gen_platform_caps.py).
Those are development-time tools.  Their outputs are committed to the
repository and verified by CI drift checks.

Called by PlatformIO before each build via:
    extra_scripts = pre:tools/pio_pre_build.py
"""

import json
import os
import sys
import time
from pathlib import Path

COPYRIGHT = "SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs"
SPDX_LICENSE = "SPDX-License-Identifier: Apache-2.0"


def get_firmware_dir() -> Path:
    """Get the firmware directory from the PlatformIO PROJECT_DIR env var."""
    project_dir = os.environ.get("PROJECT_DIR", ".")
    return Path(project_dir)


def get_board_for_env(env_name: str) -> str:
    """Map PlatformIO environment name to board slug.

    The native (host) test environment reuses the pico board's committed
    generated artifacts (platform_caps.h) — see the -I platforms/pico/generated
    include path in the [env:native] section of platformio.ini.  Without this
    mapping, verify_board_artifacts() would look for platforms/native/generated/
    which does not exist and would fail-closed the native test build.
    """
    env_map = {
        "pico": "pico",
        "pico_arduino": "pico",
        "pico_native": "pico",
        "esp32": "esp32",
        "esp32s3": "esp32s3",
        "teensy40": "teensy40",
        "teensy41": "teensy41",
        "native": "pico",
    }
    return env_map.get(env_name, env_name)


# ---------------------------------------------------------------------------
# production_config.h
# ---------------------------------------------------------------------------


def load_production_config(firmware_dir: Path) -> dict:
    """Load production_config.json. Fail closed if missing."""
    config_path = firmware_dir / "tools" / "production_config.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Production configuration not found: {config_path}\n"
            "This file is required for production builds."
        )
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def _validate_int_override(value_str: str, constraints: dict, name: str) -> int:
    """Parse and validate an integer override against constraints."""
    try:
        value = int(value_str)
    except ValueError:
        raise ValueError(f"FERQON override for {name} is not an integer: {value_str}")
    lo = constraints.get("min")
    hi = constraints.get("max")
    if lo is not None and value < lo:
        raise ValueError(f"{name}={value} below minimum {lo}")
    if hi is not None and value > hi:
        raise ValueError(f"{name}={value} above maximum {hi}")
    return value


def resolve_production_config(config: dict) -> dict:
    """Apply validated FERQON_* environment overrides to the production config."""
    constraints = config.get("constraints", {})
    resolved = {}

    # serial_baud
    baud = config.get("serial_baud", 115200)
    env_baud = os.environ.get("FERQON_SERIAL_BAUD")
    if env_baud is not None:
        baud = _validate_int_override(
            env_baud, constraints.get("serial_baud", {}), "serial_baud"
        )
    resolved["serial_baud"] = baud

    # heartbeat_interval_ms
    hb = config.get("heartbeat_interval_ms", 5000)
    env_hb = os.environ.get("FERQON_HEARTBEAT_INTERVAL_MS")
    if env_hb is not None:
        hb = _validate_int_override(
            env_hb,
            constraints.get("heartbeat_interval_ms", {}),
            "heartbeat_interval_ms",
        )
    resolved["heartbeat_interval_ms"] = hb

    # log_level_default
    log_levels = config.get("log_levels", {"OFF": 0, "INFO": 1, "VERBOSE": 2})
    log_level_name = config.get("log_level_default", "INFO")
    env_log = os.environ.get("FERQON_LOG_LEVEL")
    if env_log is not None:
        if env_log not in log_levels:
            raise ValueError(
                f"FERQON_LOG_LEVEL={env_log} not in {list(log_levels.keys())}"
            )
        log_level_name = env_log
    resolved["log_level_name"] = log_level_name
    resolved["log_level_value"] = log_levels.get(log_level_name, 1)

    # cli_timeout_s — used by the production CLI's SerialTransport
    cli_timeout = config.get("cli_timeout_s", 2)
    env_cli_timeout = os.environ.get("FERQON_CLI_TIMEOUT_S")
    if env_cli_timeout is not None:
        cli_timeout = _validate_int_override(
            env_cli_timeout, constraints.get("cli_timeout_s", {}), "cli_timeout_s"
        )
    resolved["cli_timeout_s"] = cli_timeout

    # cli_connect_delay_ms — used by the production CLI's SerialTransport.connect()
    cli_delay = config.get("cli_connect_delay_ms", 500)
    env_cli_delay = os.environ.get("FERQON_CLI_CONNECT_DELAY_MS")
    if env_cli_delay is not None:
        cli_delay = _validate_int_override(
            env_cli_delay,
            constraints.get("cli_connect_delay_ms", {}),
            "cli_connect_delay_ms",
        )
    resolved["cli_connect_delay_ms"] = cli_delay

    return resolved


def generate_production_config_h(resolved: dict) -> str:
    """Generate production_config.h content from resolved configuration."""
    lines = [
        f"/* {SPDX_LICENSE} */",
        f"/* {COPYRIGHT} */",
        "/* Auto-generated by pio_pre_build.py from tools/production_config.json.",
        " * DO NOT EDIT — edit production_config.json and rebuild.",
        " */",
        "#ifndef PRODUCTION_CONFIG_H",
        "#define PRODUCTION_CONFIG_H",
        "",
        "#include <stdint.h>",
        "",
        f"#define FERQON_SERIAL_BAUD           {resolved['serial_baud']}",
        f"#define FERQON_HEARTBEAT_INTERVAL_MS {resolved['heartbeat_interval_ms']}",
        f"#define FERQON_LOG_LEVEL_DEFAULT     {resolved['log_level_value']}",
        f'/* Default log level: {resolved["log_level_name"]} */',
        f"#define FERQON_CLI_TIMEOUT_S         {resolved['cli_timeout_s']}",
        f"#define FERQON_CLI_CONNECT_DELAY_MS  {resolved['cli_connect_delay_ms']}",
        "",
        "#endif /* PRODUCTION_CONFIG_H */",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# build_timestamp.h
# ---------------------------------------------------------------------------


def generate_build_timestamp_h() -> tuple[str, int]:
    """Generate build_timestamp.h content. Honors SOURCE_DATE_EPOCH for reproducibility."""
    source_date = os.environ.get("SOURCE_DATE_EPOCH")
    if source_date:
        try:
            build_time = int(source_date)
        except ValueError:
            raise ValueError(f"SOURCE_DATE_EPOCH is not a valid integer: {source_date}")
    else:
        build_time = int(time.time())

    content = f"""/* {SPDX_LICENSE} */
/* {COPYRIGHT} */
/* Auto-generated by pio_pre_build.py */

#ifndef BUILD_TIMESTAMP_H
#define BUILD_TIMESTAMP_H

#define FERQON_BUILD_TIMESTAMP {build_time}U

#endif /* BUILD_TIMESTAMP_H */
"""
    return content, build_time


# ---------------------------------------------------------------------------
# Per-board artifact verification (fail-closed)
# ---------------------------------------------------------------------------


def verify_board_artifacts(firmware_dir: Path, board_name: str) -> None:
    """Verify that committed per-board generated artifacts exist.

    Raises FileNotFoundError if any required artifact is missing.
    Production builds must not silently fall back to stale copies.
    """
    board_generated = firmware_dir / "platforms" / board_name / "generated"
    required = ["platform_caps.h"]
    missing = [f for f in required if not (board_generated / f).exists()]
    if missing:
        raise FileNotFoundError(
            f"Required board artifacts missing for '{board_name}' in {board_generated}:\n"
            + "\n".join(f"  - {f}" for f in missing)
            + "\nRun: python3 tools/gen_platform_caps.py "
            f"platforms/{board_name}/board.yml"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """Main entry point for PlatformIO pre-build hook."""
    print("=" * 60)
    print("Ferqon PlatformIO Pre-Build Hook (production)")
    print("=" * 60)

    env_name = os.environ.get("PLATFORMIO_ENV_NAME", "pico_arduino")
    print(f"Environment: {env_name}")

    firmware_dir = get_firmware_dir()
    print(f"Firmware directory: {firmware_dir}")

    generated_dir = firmware_dir / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)

    # 1. Build timestamp
    try:
        ts_content, build_time = generate_build_timestamp_h()
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    (generated_dir / "build_timestamp.h").write_text(ts_content, encoding="utf-8")
    print(
        f"Generated build timestamp: {build_time} "
        f"({time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(build_time))} UTC)"
    )

    # 2. Production configuration
    try:
        config = load_production_config(firmware_dir)
        resolved = resolve_production_config(config)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1

    config_h = generate_production_config_h(resolved)
    (generated_dir / "production_config.h").write_text(config_h, encoding="utf-8")
    print(
        f"Generated production_config.h: "
        f"baud={resolved['serial_baud']} "
        f"heartbeat={resolved['heartbeat_interval_ms']}ms "
        f"log={resolved['log_level_name']} "
        f"cli_timeout={resolved['cli_timeout_s']}s "
        f"cli_delay={resolved['cli_connect_delay_ms']}ms"
    )

    # 3. Verify per-board committed artifacts (fail-closed)
    board_name = get_board_for_env(env_name)
    print(f"Board: {board_name}")
    try:
        verify_board_artifacts(firmware_dir, board_name)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1
    print(f"Verified board artifacts for {board_name}")

    print("=" * 60)
    print("Pre-build hook complete")
    print("=" * 60)
    return 0


# Run as a PlatformIO pre-build hook (imported by SCons) or as a standalone
# script. When imported by SCons, __name__ is not __main__ and env is available
# via Import("env"); execute the pre-build logic once. When run standalone,
# guard with if __name__ == "__main__" so the script can be imported without
# side effects.
if __name__ == "__main__":
    sys.exit(main())
else:
    # When imported by SCons/PlatformIO, run the pre-build logic but do NOT
    # call sys.exit() — that would terminate the SCons process before the
    # actual build starts. Just print errors and let SCons continue (or fail
    # naturally if artifacts are missing).
    try:
        Import("env")
    except NameError:
        pass
    else:
        try:
            rc = main()
            if rc != 0:
                # Raise an exception to fail the build, but don't sys.exit()
                raise RuntimeError(f"pio_pre_build.py failed with exit code {rc}")
        except Exception as e:
            raise RuntimeError(f"pio_pre_build.py failed: {e}") from e
