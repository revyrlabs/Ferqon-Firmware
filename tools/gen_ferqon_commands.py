#!/usr/bin/env python3
"""
gen_ferqon_commands.py
--------------------
Generates Ferqon protocol constants from the single source of truth
(firmware/protocol/ssot/commands.json) for both firmware and backend.

This is the standalone version for the open-source firmware repository.
It only generates the C header file for firmware use.

Outputs:
  - firmware/src/ferqon_commands.h (C macros)

Usage:
    python3 tools/gen_ferqon_commands.py
"""

import json
import sys
from pathlib import Path

# Paths relative to firmware directory
FIRMWARE_ROOT = Path(__file__).parent.parent
SSOT_PATH = FIRMWARE_ROOT / "protocol" / "ssot" / "commands.json"
C_OUTPUT = FIRMWARE_ROOT / "src" / "ferqon_commands.h"


def load_commands() -> dict:
    with open(SSOT_PATH) as f:
        return json.load(f)


def generate_c_header(data: dict) -> str:
    """Generate C header with FERQON_CMD_* macros."""
    lines = [
        "/* Ferqon serial protocol constants.",
        " *",
        " * Auto-generated from firmware/protocol/ssot/commands.json.",
        " * DO NOT EDIT — regenerate with: python3 tools/gen_ferqon_commands.py",
        " */",
        "",
        "#ifndef FERQON_COMMANDS_H",
        "#define FERQON_COMMANDS_H",
        "",
        "#include <stdint.h>",
        "",
        "/* ------------------------------------------------------------------ Frame */",
        "",
        "#define FERQON_START_BYTE               0xAB",
        "#define FERQON_MAX_PAYLOAD_BYTES        255",
        "#define FERQON_FRAME_OVERHEAD           6   /* start + seq + cmd + len + crc_lo + crc_hi */",
        "#define FERQON_INTER_BYTE_TIMEOUT_MS    50",
        "#define FERQON_FRAME_ASSEMBLY_TIMEOUT_MS 200",
        "#define FERQON_HEARTBEAT_INTERVAL_MS    1000",
        "",
        "/* CRC-16/CCITT-FALSE */",
        "#define FERQON_CRC_POLY                 0x1021",
        "#define FERQON_CRC_INIT                 0xFFFF",
        "",
        "/* Seq=0 is reserved for unsolicited MCU pushes (heartbeat, event, log). */",
        "#define FERQON_SEQ_UNSOLICITED          0",
        "",
        "/* --------------------------------------------------------- Packet types */",
        "",
        "#define FERQON_PKT_REQUEST              1",
        "#define FERQON_PKT_ACK                  2",
        "#define FERQON_PKT_DONE                 3",
        "#define FERQON_PKT_ERROR                4",
        "#define FERQON_PKT_HEARTBEAT            5",
        "#define FERQON_PKT_EVENT                6",
        "#define FERQON_PKT_LOG                  7",
        "",
        "/* ----------------------------------------------------------- Commands */",
        "",
    ]

    commands = data.get("commands", {})
    for name, info in sorted(commands.items(), key=lambda x: x[1].get("id", 0)):
        cmd_id = info.get("id")
        if cmd_id is not None:
            macro_name = f"FERQON_CMD_{name.upper()}"
            lines.append(f"#define {macro_name:<30} {cmd_id}")

    lines.extend([
        "",
        "/* ----------------------------------------------------------- TLV types */",
        "",
    ])

    tlv_types = data.get("tlv_types", {})
    for name, value in sorted(tlv_types.items(), key=lambda x: x[1]):
        macro_name = f"TLV_{name.upper()}"
        lines.append(f"#define {macro_name:<30} {value}")

    signature = data.get("ferqon_signature", {})
    if signature:
        magic = signature.get("magic", "FERQON")
        vendor = signature.get("vendor", "revyrlabs")
        cap_version = signature.get("capability_version", 1)
        lines.extend([
            "",
            "/* -------------------------------------------------- Ferqon signature */",
            "",
            f"#define FERQON_SIGNATURE_MAGIC         \"{magic}\"",
            f"#define FERQON_SIGNATURE_VENDOR        \"{vendor}\"",
            f"#define FERQON_SIGNATURE_CAP_VERSION    {cap_version}",
        ])

    lines.extend([
        "",
        "/* ---------------------------------------------------------- GPIO modes */",
        "",
        "#define FERQON_GPIO_INPUT               0",
        "#define FERQON_GPIO_OUTPUT              1",
        "#define FERQON_GPIO_INPUT_PULLUP        2",
        "#define FERQON_GPIO_INPUT_PULLDOWN      3",
        "",
        "/* -------------------------------------------------------- App states */",
        "",
        "#define FERQON_STATE_APP_BOOT           0",
        "#define FERQON_STATE_APP_READY          1",
        "#define FERQON_STATE_APP_BUSY           2",
        "#define FERQON_STATE_APP_FAULT          3",
        "#define FERQON_STATE_APP_UPDATE         4",
        "",
        "/* -------------------------------------------------- Error categories */",
        "",
        "#define FERQON_ECAT_NONE                0",
        "#define FERQON_ECAT_PROTOCOL            1",
        "#define FERQON_ECAT_COMMAND             2",
        "#define FERQON_ECAT_DEVICE              3",
        "#define FERQON_ECAT_INTERNAL            4",
        "#define FERQON_ECAT_TIMEOUT             5",
        "",
        "/* ---------------------------------------------------- Error codes */",
        "",
        "#define FERQON_ERR_OK                   0",
        "#define FERQON_ERR_INVALID_COMMAND      1",
        "#define FERQON_ERR_INVALID_PARAMS       2",
        "#define FERQON_ERR_UNSUPPORTED_MODE     3",
        "#define FERQON_ERR_UNSUPPORTED_PIN      4",
        "#define FERQON_ERR_BUSY                 5",
        "#define FERQON_ERR_INTERNAL             6",
        "#define FERQON_ERR_CHECKSUM_FAIL        7",
        "#define FERQON_ERR_PAYLOAD_TOO_LARGE    9",
        "#define FERQON_ERR_TIMEOUT              10",
        "#define FERQON_ERR_INVALID_DRIVER       11  /* No driver registered with that name */",
        "#define FERQON_ERR_INVALID_METHOD       12  /* Driver exists but method unknown */",
        "#define FERQON_ERR_NOT_IMPLEMENTED      13  /* Driver/method known but hardware not ready */",
        "",
        "#endif /* FERQON_COMMANDS_H */",
    ])

    return "\n".join(lines)


def main() -> int:
    data = load_commands()

    # Validate output parent directory exists
    if not C_OUTPUT.parent.exists():
        print(f"Error: Output directory does not exist: {C_OUTPUT.parent}", file=sys.stderr)
        print(f"Please create the directory or check the path configuration.", file=sys.stderr)
        return 1

    # Generate C header
    c_content = generate_c_header(data)
    with open(C_OUTPUT, "w") as f:
        f.write(c_content)
    print(f"Generated: {C_OUTPUT}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
