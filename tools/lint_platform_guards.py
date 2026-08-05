#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
lint_platform_guards.py
-----------------------
Lint tool to enforce that all Arduino/hardware API calls in source code
are wrapped with ferqon_cap_*() capability guards.

This ensures hardware operations only happen if the board actually supports
the capability, preventing crashes on unsupported or reserved pins.

Usage:
    python3 tools/lint_platform_guards.py
"""

import sys
from pathlib import Path
from typing import List, Tuple

# Arduino API calls that require capability guards
ARDUINO_APIS = {
    "analogRead": "ferqon_cap_pin_supports_adc",
    "analogWrite": "ferqon_cap_pin_supports_pwm",
    "digitalWrite": "ferqon_cap_pin_is_valid",
    "digitalRead": "ferqon_cap_pin_is_valid",
    "pinMode": "ferqon_cap_pin_is_valid",
}

# Wrapper functions that internally call ferqon_cap_* guards. The lint
# tool recognises these as valid guards so that driver code using the
# shared ferqon_check_pin() helper (in ferqon_helpers.h) or local
# adc_check_channel() wrapper passes without needing to inline the
# ferqon_cap_ call in every .cpp file.
GUARD_WRAPPERS = {"ferqon_check_pin", "adc_check_channel"}

# Peripheral APIs that require instance validation
PERIPHERAL_APIS = {
    "SPI.begin": "ferqon_cap_spi_instance_is_valid",
    "Wire.begin": "ferqon_cap_i2c_instance_is_valid",
}

# Files where Arduino API calls are exempt from guard requirements:
# - main.cpp: initialization code uses known-valid pins (LED_BUILTIN) and
#   the control Serial port, which is not a peripheral UART.
# - ferqon_hal_arduino.cpp: HAL implementation layer. The capability guards
#   live in the callers (gpio.cpp, adc.cpp via ferqon_check_pin /
#   adc_check_channel). The HAL is the lowest-level wrapper that directly
#   calls the Arduino API after guards have already passed.
EXEMPT_FILES = {"main.cpp", "ferqon_hal_arduino.cpp"}

# How many lines to look backwards for a ferqon_cap_ guard call.
# Set generously to cover cases where error-handling code or switch
# statements sit between the guard check and the actual API call.
GUARD_LOOKBACK = 30


def check_file_for_guards(file_path: Path) -> List[Tuple[int, str, str]]:
    """Check a source file for missing capability guards.

    A guard is considered present if a ferqon_cap_*() call appears within
    the preceding GUARD_LOOKBACK lines of the Arduino API call.
    """
    issues = []

    content = file_path.read_text()
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        # Skip comments and preprocessor directives
        stripped = line.strip()
        if (
            stripped.startswith("//")
            or stripped.startswith("*")
            or stripped.startswith("#")
        ):
            continue

        # Check for Arduino API calls
        for api, guard in ARDUINO_APIS.items():
            if api in line:
                # Check if the line has the corresponding guard
                if guard in line or "ferqon_cap_" in line:
                    continue
                # Check if the line calls a recognised guard wrapper
                if any(w in line for w in GUARD_WRAPPERS):
                    continue
                # Look backwards for a ferqon_cap_ call or guard wrapper
                found_guard = False
                for j in range(max(0, i - GUARD_LOOKBACK - 1), i - 1):
                    if "ferqon_cap_" in lines[j] or any(
                        w in lines[j] for w in GUARD_WRAPPERS
                    ):
                        found_guard = True
                        break
                if not found_guard:
                    issues.append((i, api, guard))

        # Check for peripheral API calls
        for api, guard in PERIPHERAL_APIS.items():
            if api in line:
                if guard in line or "ferqon_cap_" in line:
                    continue
                if any(w in line for w in GUARD_WRAPPERS):
                    continue
                found_guard = False
                for j in range(max(0, i - GUARD_LOOKBACK - 1), i - 1):
                    if "ferqon_cap_" in lines[j] or any(
                        w in lines[j] for w in GUARD_WRAPPERS
                    ):
                        found_guard = True
                        break
                if not found_guard:
                    issues.append((i, api, guard))

    return issues


def main() -> None:
    firmware_dir = Path(__file__).parent.parent
    platforms_dir = firmware_dir / "platforms"
    src_dir = firmware_dir / "src"

    if not platforms_dir.exists():
        print(f"ERROR: platforms directory not found: {platforms_dir}")
        sys.exit(1)

    # Find all C/C++ source files in platform directories AND src/
    source_files = []
    for search_dir in [platforms_dir, src_dir]:
        if not search_dir.exists():
            continue
        for pattern in ["**/*.cpp", "**/*.c", "**/*.h", "**/*.hpp"]:
            source_files.extend(search_dir.glob(pattern))

    all_issues = []
    for source_file in source_files:
        # Skip generated files and in-development platforms
        if "generated" in source_file.parts or "in_development" in source_file.parts:
            continue
        # Skip exempt files (main.cpp initialization)
        if source_file.name in EXEMPT_FILES:
            continue

        issues = check_file_for_guards(source_file)
        if issues:
            for line_num, api, guard in issues:
                all_issues.append(
                    (str(source_file.relative_to(firmware_dir)), line_num, api, guard)
                )

    if all_issues:
        print("Found missing capability guards:")
        print()
        for file_path, line_num, api, guard in all_issues:
            print(f"  {file_path}:{line_num} - {api} should be guarded with {guard}()")
        print()
        print(f"Total issues: {len(all_issues)}")
        sys.exit(1)
    else:
        print("All Arduino API calls are properly guarded with capability checks.")
        sys.exit(0)


if __name__ == "__main__":
    main()
