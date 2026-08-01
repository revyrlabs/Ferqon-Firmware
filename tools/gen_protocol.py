#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
gen_protocol.py
---------------
Single-entry codegen: generates ALL firmware-side protocol artifacts from the
SSOT firmware/protocol/ssot/commands.json in one run.

This is a **development-time** tool. It is NOT invoked by the production
build hook (pio_pre_build.py). Its outputs are committed to the repository and
verified by CI drift checks.

Operates within the standalone firmware repository by default. The root monorepo
Makefile calls this script explicitly via the ``sync-protocol`` and
``check-protocol`` targets for monorepo-level synchronization.

Outputs:
  1. src/ferqon_commands.h            — C macros for firmware
  2. tools/ferqonfw/_generated.py   — Python generated constants
  3. tools/ferqonfw/protocol.py      — Python protocol SDK mirror

Usage:
    python3 tools/gen_protocol.py [--check]

    --check   Regenerate into temp files and diff; exit 1 if any file drifted.
              Used by pre-commit / CI to enforce no-drift.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SSOT_PATH = REPO_ROOT / "protocol" / "ssot" / "commands.json"
PINMAP_SOURCE = (
    REPO_ROOT.parent
    / "sandbox"
    / "protocol_sdk"
    / "sdk"
    / "serial"
    / "driver"
    / "pico_pinmap.json"
)

C_HEADER_PATH = REPO_ROOT / "src" / "ferqon_commands.h"
FW_GENERATED_PATH = REPO_ROOT / "tools" / "ferqonfw" / "_generated.py"
FW_PROTOCOL_PATH = REPO_ROOT / "tools" / "ferqonfw" / "protocol.py"
CANON_PROTOCOL_PATH = (
    REPO_ROOT.parent
    / "packages"
    / "hw-sdk"
    / "ferqon_hw"
    / "ferqon_hw"
    / "protocol.py"
)

_REGEN_NOTICE = "python3 tools/gen_protocol.py"

COPYRIGHT = "SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs"
SPDX_LICENSE = "SPDX-License-Identifier: Apache-2.0"


# Make the monorepo tools/ directory importable so we can reuse the backend
# generator logic without duplicating it.
sys.path.insert(0, str(REPO_ROOT.parent / "tools"))
from gen_backend_commands import generate_constants_module  # type: ignore[import-untyped]


def load_ssot() -> dict:
    with SSOT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_pinmap() -> dict | None:
    if PINMAP_SOURCE.exists():
        with PINMAP_SOURCE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _sorted_commands(data: dict) -> list[tuple[str, int]]:
    return sorted(
        ((name, int(info["id"])) for name, info in data.get("commands", {}).items()),
        key=lambda x: x[1],
    )


# ---------------------------------------------------------------------------
# 1. C header
# ---------------------------------------------------------------------------


def generate_c_header(data: dict) -> str:
    protocol_version = data.get("version", "0.0.0")
    lines = [
        f"/* {SPDX_LICENSE} */",
        f"/* {COPYRIGHT} */",
        "/* Ferqon serial protocol constants.",
        " *",
        f" * Auto-generated from protocol/ssot/commands.json (v{protocol_version}).",
        f" * DO NOT EDIT — regenerate with: {_REGEN_NOTICE}",
        " */",
        "",
        "#ifndef FERQON_COMMANDS_H",
        "#define FERQON_COMMANDS_H",
        "",
        "#include <stdint.h>",
        "",
        "/* ------------------------------------------------------------------ Frame */",
        "",
    ]

    frame = data["frame"]
    limits = data["limits"]
    lines += [
        f"#define FERQON_START_BYTE               0x{frame['start_byte']:02X}",
        f"#define FERQON_MAX_PAYLOAD_BYTES        {limits['max_payload_bytes']}",
        "#define FERQON_FRAME_OVERHEAD           6   /* start + seq + cmd + len + crc_lo + crc_hi */",
        f"#define FERQON_INTER_BYTE_TIMEOUT_MS    {limits['inter_byte_timeout_ms']}",
        f"#define FERQON_FRAME_ASSEMBLY_TIMEOUT_MS {limits['frame_assembly_timeout_ms']}",
        "",
        "/* CRC-16/CCITT-FALSE */",
        f"#define FERQON_CRC_POLY                 0x{frame['crc_poly']:04X}",
        f"#define FERQON_CRC_INIT                 0x{frame['crc_init']:04X}",
        "",
        "/* Seq=0 is reserved for unsolicited MCU pushes (heartbeat, event, log). */",
        f"#define FERQON_SEQ_UNSOLICITED          {data['reserved_seq']['UNSOLICITED']}",
        "",
        "/* Protocol version (from SSOT) */",
        f'#define FERQON_PROTOCOL_VERSION         "{protocol_version}"',
        "",
        "/* --------------------------------------------------------- Packet types */",
        "",
    ]

    for name, val in sorted(data["packet_types"].items(), key=lambda x: x[1]):
        lines.append(f"#define FERQON_PKT_{name:<20} {val}")

    lines += [
        "",
        "/* ----------------------------------------------------------- Commands */",
        "",
    ]

    for name, cmd_id in _sorted_commands(data):
        macro = f"FERQON_CMD_{name.upper()}"
        lines.append(f"#define {macro:<30} {cmd_id}")

    lines += [
        "",
        "/* ----------------------------------------------------------- TLV types */",
        "/* NOTE: TLV type IDs are context-dependent. DEVICE_NAME, MCU_TYPE,",
        " * FIRMWARE_VERSION, PROTOCOL_VERSION, BUILD_TIMESTAMP, FREE_RAM, and",
        " * UPTIME_MS appear in DEVICE_INFO responses. DRIVER, COMMAND, METHOD,",
        " * and VERSION appear in DRIVER_INFO responses. Some IDs overlap",
        " * (e.g. DEVICE_NAME=DRIVER=1) — always use the correct constant for",
        " * the response context.",
        " */",
        "",
    ]

    for name, value in sorted(data.get("tlv_types", {}).items(), key=lambda x: x[1]):
        lines.append(f"#define TLV_{name.upper():<26} {value}")

    sig = data.get("ferqon_signature", {})
    if sig:
        lines += [
            "",
            "/* -------------------------------------------------- Ferqon signature */",
            "",
            f'#define FERQON_SIGNATURE_MAGIC         "{sig.get("magic", "FERQON")}"',
            f'#define FERQON_SIGNATURE_VENDOR        "{sig.get("vendor", "revyrlabs")}"',
            f"#define FERQON_SIGNATURE_CAP_VERSION    {sig.get('capability_version', 1)}",
        ]

    lines += [
        "",
        "/* ---------------------------------------------------------- GPIO modes */",
        "",
    ]

    for name, val in sorted(data.get("gpio_modes", {}).items(), key=lambda x: x[1]):
        lines.append(f"#define FERQON_GPIO_{name:<22} {val}")

    lines += [
        "",
        "/* -------------------------------------------------------- App states */",
        "",
    ]

    for name, val in sorted(data.get("states", {}).items(), key=lambda x: x[1]):
        lines.append(f"#define FERQON_STATE_{name:<20} {val}")

    lines += [
        "",
        "/* -------------------------------------------------- Error categories */",
        "",
    ]

    for name, val in sorted(data["errors"]["categories"].items(), key=lambda x: x[1]):
        lines.append(f"#define FERQON_ECAT_{name:<21} {val}")

    lines += [
        "",
        "/* ---------------------------------------------------- Error codes */",
        "",
    ]

    for name, entry in sorted(
        data["errors"]["codes"].items(), key=lambda x: x[1]["code"]
    ):
        desc = entry.get("description", "")
        code = entry["code"]
        lines.append(f"#define FERQON_ERR_{name:<23} {code}  /* {desc} */")

    lines += ["", "#endif /* FERQON_COMMANDS_H */", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2. Python generated constants for ferqonfw
# ---------------------------------------------------------------------------


def generate_fw_generated(data: dict, pinmap: dict | None) -> str:
    """Generate the firmware-side _generated.py module."""
    return generate_constants_module(data, pinmap)


# ---------------------------------------------------------------------------
# 3. Python protocol SDK mirror for ferqonfw
# ---------------------------------------------------------------------------


def generate_fw_protocol() -> str:
    """Mirror the canonical ferqon_hw/protocol.py into ferqonfw/protocol.py."""
    if not CANON_PROTOCOL_PATH.exists():
        raise FileNotFoundError(
            f"Canonical protocol SDK not found at {CANON_PROTOCOL_PATH}. "
            "Run python3 tools/gen_backend_commands.py first."
        )
    source = CANON_PROTOCOL_PATH.read_text(encoding="utf-8")
    # Use the firmware package name for logging instead of the SDK package name.
    return source.replace('logging.getLogger("ferqon_hw")', 'logging.getLogger("ferqonfw.protocol")')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  Generated: {path.relative_to(REPO_ROOT)}")


def run_generate(data: dict, pinmap: dict | None) -> None:
    print("Generating firmware protocol artifacts from SSOT...")
    _write(C_HEADER_PATH, generate_c_header(data))
    _write(FW_GENERATED_PATH, generate_fw_generated(data, pinmap))
    _write(FW_PROTOCOL_PATH, generate_fw_protocol())
    print(f"Done. Protocol version: {data.get('version', '?')}")


def _check_file(path: Path, expected: str, label: str) -> bool:
    if not path.exists():
        print(f"  MISSING: {path.relative_to(REPO_ROOT)}")
        return False
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        print(f"  DRIFT:   {path.relative_to(REPO_ROOT)}")
        return False
    print(f"  OK:      {path.relative_to(REPO_ROOT)}")
    return True


def run_check(data: dict, pinmap: dict | None) -> int:
    print("Checking firmware protocol artifact drift...")
    ok = True
    ok &= _check_file(C_HEADER_PATH, generate_c_header(data), "C header")
    ok &= _check_file(FW_GENERATED_PATH, generate_fw_generated(data, pinmap), "ferqonfw/_generated.py")
    ok &= _check_file(FW_PROTOCOL_PATH, generate_fw_protocol(), "ferqonfw/protocol.py")

    if ok:
        print(f"\nFirmware protocol artifacts are in sync. (v{data.get('version', '?')})")
        return 0

    print(
        "\nERROR: Firmware protocol artifacts are out of sync with the SSOT.\n"
        "Run: python3 tools/gen_protocol.py"
    )
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Ferqon firmware protocol artifact generator")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check for drift without writing files (exits 1 if any file is stale)",
    )
    args = parser.parse_args()

    data = load_ssot()
    pinmap = _load_pinmap()
    if args.check:
        return run_check(data, pinmap)
    run_generate(data, pinmap)
    return 0


if __name__ == "__main__":
    sys.exit(main())
