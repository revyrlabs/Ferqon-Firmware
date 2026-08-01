#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
gen_protocol.py
---------------
Single-entry codegen: generates ALL protocol artifacts from the SSOT
firmware/protocol/ssot/commands.json in one run.

This is a **development-time** tool. It is NOT invoked by the production
build hook (pio_pre_build.py). Its output (src/ferqon_commands.h) is
committed to the repository and verified by CI drift checks.

Operates within the standalone firmware repository by default.
The root monorepo Makefile calls this script explicitly via the
``sync-protocol`` and ``check-protocol`` targets for monorepo-level
synchronization.

Outputs:
  1. src/ferqon_commands.h — C macros for firmware

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

OUTPUTS: dict[str, Path] = {
    "c_header": REPO_ROOT / "src" / "ferqon_commands.h",
}

_REGEN_NOTICE = "python3 tools/gen_protocol.py"

COPYRIGHT = "SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs"
SPDX_LICENSE = "SPDX-License-Identifier: Apache-2.0"


def load_ssot() -> dict:
    with SSOT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _sorted_commands(data: dict) -> list[tuple[str, int]]:
    return sorted(
        ((name, int(info["id"])) for name, info in data.get("commands", {}).items()),
        key=lambda x: x[1],
    )


# ---------------------------------------------------------------------------
# 1. C header
# ---------------------------------------------------------------------------


def _parse_version(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Expected MAJOR.MINOR.PATCH version, got: {version}")
    major, minor, patch = (int(p) for p in parts)
    for p, name in ((major, "major"), (minor, "minor"), (patch, "patch")):
        if p < 0 or p > 255:
            raise ValueError(f"Version {name} component out of u8 range: {p}")
    return major, minor, patch


def generate_c_header(data: dict) -> str:
    protocol_version = data.get("version", "0.0.0")
    major, minor, patch = _parse_version(protocol_version)
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
        f"#define FERQON_PROTOCOL_VERSION_MAJOR   {major}",
        f"#define FERQON_PROTOCOL_VERSION_MINOR   {minor}",
        f"#define FERQON_PROTOCOL_VERSION_PATCH   {patch}",
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
# Main
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  Generated: {path.relative_to(REPO_ROOT)}")


def run_generate(data: dict) -> None:
    print("Generating protocol artifacts from SSOT...")
    _write(OUTPUTS["c_header"], generate_c_header(data))
    print(f"Done. Protocol version: {data.get('version', '?')}")


def run_check(data: dict) -> int:
    print("Checking protocol artifact drift...")
    expected = generate_c_header(data)
    output_path = OUTPUTS["c_header"]
    if not output_path.exists():
        print(f"  MISSING: {output_path.relative_to(REPO_ROOT)}")
        print(
            "\nERROR: src/ferqon_commands.h is out of sync with the SSOT.\n"
            "Run: python3 tools/gen_protocol.py"
        )
        return 1
    actual = output_path.read_text(encoding="utf-8")
    if actual != expected:
        print(f"  DRIFT:   {output_path.relative_to(REPO_ROOT)}")
        print(
            "\nERROR: src/ferqon_commands.h is out of sync with the SSOT.\n"
            "Run: python3 tools/gen_protocol.py"
        )
        return 1

    print(f"  OK:      {output_path.relative_to(REPO_ROOT)}")
    print(f"\nProtocol artifacts are in sync. (v{data.get('version', '?')})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ferqon protocol artifact generator")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check for drift without writing files (exits 1 if any file is stale)",
    )
    args = parser.parse_args()

    data = load_ssot()
    if args.check:
        return run_check(data)
    run_generate(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
