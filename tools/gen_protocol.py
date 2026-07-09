#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
gen_protocol.py
---------------
Single-entry codegen: generates ALL protocol artifacts from the SSOT
firmware/protocol/ssot/commands.json in one run.

Outputs:
  1. firmware/src/ferqon_commands.h          — C macros for firmware
  2. services/backend/ferqon_backend/ferqon_hil/commands_generated.py
  3. packages/hw-sdk/ferqon_hw/ferqon_hw/commands_generated.py
  4. packages/hw-sdk/ferqon_hw/ferqon_hw/_driver_method_map.py

Usage:
    python3 firmware/tools/gen_protocol.py [--check]

    --check   Regenerate into temp files and diff; exit 1 if any file drifted.
              Used by pre-commit / CI to enforce no-drift.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SSOT_PATH = REPO_ROOT / "firmware" / "protocol" / "ssot" / "commands.json"

OUTPUTS: dict[str, Path] = {
    "c_header": REPO_ROOT / "firmware" / "src" / "ferqon_commands.h",
    "backend_py": REPO_ROOT
    / "services"
    / "backend"
    / "ferqon_backend"
    / "ferqon_hil"
    / "commands_generated.py",
    "hwsdk_py": REPO_ROOT
    / "packages"
    / "hw-sdk"
    / "ferqon_hw"
    / "ferqon_hw"
    / "commands_generated.py",
    "driver_map": REPO_ROOT
    / "packages"
    / "hw-sdk"
    / "ferqon_hw"
    / "ferqon_hw"
    / "_driver_method_map.py",
}

_REGEN_NOTICE = "python3 firmware/tools/gen_protocol.py"

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


def generate_c_header(data: dict) -> str:
    protocol_version = data.get("version", "0.0.0")
    lines = [
        f"/* {SPDX_LICENSE} */",
        f"/* {COPYRIGHT} */",
        "/* Ferqon serial protocol constants.",
        " *",
        f" * Auto-generated from firmware/protocol/ssot/commands.json (v{protocol_version}).",
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
        f"#define FERQON_HEARTBEAT_INTERVAL_MS    {limits['heartbeat_interval_ms']}",
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
# 2 + 3. Python IntEnum (shared template for backend and hw-sdk)
# ---------------------------------------------------------------------------


def generate_commands_py(data: dict) -> str:
    protocol_version = data.get("version", "0.0.0")
    lines = [
        f"# {SPDX_LICENSE}",
        f"# {COPYRIGHT}",
        f"# Auto-generated from firmware/protocol/ssot/commands.json (v{protocol_version}).",
        f"# DO NOT EDIT — regenerate with: {_REGEN_NOTICE}",
        "",
        "from enum import IntEnum",
        "",
        "",
        "class FerqonCommand(IntEnum):",
        '    """Ferqon protocol command IDs."""',
    ]

    for name, cmd_id in _sorted_commands(data):
        lines.append(f"    {name.upper()} = {cmd_id}")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. Driver method map
# ---------------------------------------------------------------------------


def generate_driver_map(data: dict) -> str:
    protocol_version = data.get("version", "0.0.0")
    lines = [
        f"# {SPDX_LICENSE}",
        f"# {COPYRIGHT}",
        f"# Auto-generated from firmware/protocol/ssot/commands.json (v{protocol_version}).",
        f"# DO NOT EDIT — regenerate with: {_REGEN_NOTICE}",
        "",
        "# Mapping of (driver, method) tuples to native command encodings.",
        "# Each entry contains:",
        "#   - native_cmd: the native command name (e.g., 'gpio_write')",
        "#   - arg_map: dict of arg_name -> type (e.g., {'pin': 'u8', 'level': 'bool_high_low'})",
        "#   - sub_handler: optional sub-handler name for driver_call dispatch",
        "",
        "DRIVER_METHOD_MAP = {",
    ]

    driver_methods = data.get("driver_methods", {})
    if not driver_methods:
        # Tolerate older SSOT format where driver_methods live nested under driver_call command
        for _cmd_name, cmd_info in data.get("commands", {}).items():
            if isinstance(cmd_info, dict) and "driver_methods" in cmd_info:
                driver_methods = cmd_info["driver_methods"]
                break

    for driver_name, methods in driver_methods.items():
        for method_name, method_info in methods.items():
            native_cmd = method_info.get("native_cmd", "driver_call")
            arg_map = method_info.get("arg_map", {})
            sub_handler = method_info.get("sub_handler")

            arg_map_str = (
                "{" + ", ".join(f'"{k}": "{v}"' for k, v in arg_map.items()) + "}"
            )

            lines.append(f'    ("{driver_name}", "{method_name}"): {{')
            lines.append(f'        "native_cmd": "{native_cmd}",')
            lines.append(f'        "arg_map": {arg_map_str},')
            if sub_handler:
                lines.append(f'        "sub_handler": "{sub_handler}",')
            lines.append("    },")

    lines += ["}", ""]
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
    _write(OUTPUTS["backend_py"], generate_commands_py(data))
    _write(OUTPUTS["hwsdk_py"], generate_commands_py(data))
    _write(OUTPUTS["driver_map"], generate_driver_map(data))
    print(f"Done. Protocol version: {data.get('version', '?')}")


def run_check(data: dict) -> int:
    print("Checking protocol artifact drift...")
    drifted: list[str] = []

    generators = {
        "c_header": generate_c_header,
        "backend_py": generate_commands_py,
        "hwsdk_py": generate_commands_py,
        "driver_map": generate_driver_map,
    }

    for key, generator in generators.items():
        expected = generator(data)
        output_path = OUTPUTS[key]
        if not output_path.exists():
            print(f"  MISSING: {output_path.relative_to(REPO_ROOT)}")
            drifted.append(str(output_path.relative_to(REPO_ROOT)))
            continue
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            print(f"  DRIFT:   {output_path.relative_to(REPO_ROOT)}")
            drifted.append(str(output_path.relative_to(REPO_ROOT)))
        else:
            print(f"  OK:      {output_path.relative_to(REPO_ROOT)}")

    if drifted:
        print(
            f"\nERROR: {len(drifted)} file(s) are out of sync with the SSOT.\n"
            f"Run: python3 firmware/tools/gen_protocol.py\n"
            f"Drifted: {', '.join(drifted)}"
        )
        return 1

    print(f"\nAll protocol artifacts are in sync. (v{data.get('version', '?')})")
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
