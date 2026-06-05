#!/usr/bin/env python3
"""
lint_platform_guards.py
-----------------------
Lint tool to enforce that all Arduino/hardware API calls in platform code
are wrapped with ferqon_cap_*() capability guards.

This ensures hardware operations only happen if the board actually supports
the capability, preventing crashes on unsupported pins.

Usage:
    python3 tools/lint_platform_guards.py
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


# Arduino API calls that require capability guards
ARDUINO_APIS = {
    'analogRead': 'ferqon_cap_pin_supports_adc',
    'analogWrite': 'ferqon_cap_pin_supports_pwm',
    'digitalWrite': 'ferqon_cap_pin_is_valid',
    'digitalRead': 'ferqon_cap_pin_is_valid',
    'pinMode': 'ferqon_cap_pin_is_valid',
}

# Peripheral APIs that require instance validation
PERIPHERAL_APIS = {
    'SPI.begin': 'ferqon_cap_spi_instance_is_valid',
    'Wire.begin': 'ferqon_cap_i2c_instance_is_valid',
    'Serial.begin': 'ferqon_cap_uart_instance_is_valid',
}


def check_file_for_guards(file_path: Path) -> List[Tuple[int, str, str]]:
    """Check a source file for missing capability guards."""
    issues = []
    
    content = file_path.read_text()
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        # Skip comments and preprocessor directives
        stripped = line.strip()
        if stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('#'):
            continue
        
        # Check for Arduino API calls
        for api, guard in ARDUINO_APIS.items():
            if api in line:
                # Check if the line has the corresponding guard
                if guard not in line and 'ferqon_cap_' not in line:
                    issues.append((i, api, guard))
        
        # Check for peripheral API calls
        for api, guard in PERIPHERAL_APIS.items():
            if api in line:
                if guard not in line and 'ferqon_cap_' not in line:
                    issues.append((i, api, guard))
    
    return issues


def main() -> None:
    firmware_dir = Path(__file__).parent.parent
    platforms_dir = firmware_dir / "platforms"
    
    if not platforms_dir.exists():
        print(f"ERROR: platforms directory not found: {platforms_dir}")
        sys.exit(1)
    
    # Find all C/C++ source files in platform directories
    source_files = []
    for pattern in ['**/*.cpp', '**/*.c', '**/*.h', '**/*.hpp']:
        source_files.extend(platforms_dir.glob(pattern))
    
    all_issues = []
    for source_file in source_files:
        # Skip generated files
        if 'generated' in source_file.parts:
            continue
        
        issues = check_file_for_guards(source_file)
        if issues:
            for line_num, api, guard in issues:
                all_issues.append((str(source_file.relative_to(firmware_dir)), line_num, api, guard))
    
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
