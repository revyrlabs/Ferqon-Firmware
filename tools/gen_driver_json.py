#!/usr/bin/env python3
"""
gen_driver_json.py
------------------
YAML→JSON compiler for driver definitions.

Validates driver YAML against schema, UI blocks, and modes,
then emits canonical JSON for server storage.

Usage:
    python3 tools/gen_driver_json.py <driver.yml> [output_dir]
    python3 tools/gen_driver_json.py --check <driver.yml>
"""

import yaml
import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# Add server backend to path for validators
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "server" / "backend"))

from app.utils.flash.driver_schema import DriverDefinition
from app.utils.flash.ui_validator import UIValidator
from app.utils.flash.mode_resolver import ModeResolver


def load_driver_yaml(path: Path) -> Dict[str, Any]:
    """Load and parse driver YAML."""
    with open(path) as f:
        return yaml.safe_load(f)


def validate_driver(driver_def: Dict[str, Any]) -> tuple[bool, list[Dict[str, Any]], list[Dict[str, Any]]]:
    """
    Validate driver definition against schema, UI, and modes.
    
    Returns:
        (is_valid, errors, warnings)
    """
    errors = []
    warnings = []

    # 1. Pydantic schema validation
    try:
        DriverDefinition(**driver_def)
    except Exception as e:
        errors.append({
            "code": "SCHEMA_VALIDATION_FAILED",
            "message": str(e),
            "context": {}
        })
        return False, errors, warnings

    # 2. UI validation
    ui_validator = UIValidator(driver_def)
    ui_validator.validate()
    errors.extend(ui_validator.get_errors())
    warnings.extend(ui_validator.get_warnings())

    # 3. Mode validation
    mode_resolver = ModeResolver(driver_def)
    mode_resolver.validate()
    errors.extend(mode_resolver.get_errors())
    warnings.extend(mode_resolver.get_warnings())

    return len(errors) == 0, errors, warnings


def generate_canonical_json(driver_def: Dict[str, Any]) -> str:
    """Generate canonical JSON from driver definition."""
    # Use Pydantic to normalize the structure
    try:
        normalized = DriverDefinition(**driver_def)
        return json.dumps(normalized.model_dump(mode='json'), indent=2)
    except Exception as e:
        # If Pydantic fails, fall back to direct JSON dump
        return json.dumps(driver_def, indent=2)


def process_driver(
    input_path: Path,
    output_dir: Path | None = None,
    check_mode: bool = False
) -> bool:
    """
    Process a driver YAML file.
    
    Returns:
        True if successful (or check passes), False otherwise
    """
    driver_def = load_driver_yaml(input_path)
    is_valid, errors, warnings = validate_driver(driver_def)

    if check_mode:
        # In check mode, just report validation status
        if errors:
            print(f"VALIDATION FAIL: {input_path}")
            for err in errors:
                print(f"  ERROR: {err['code']} - {err['message']}")
            if warnings:
                print("  Warnings:")
                for warn in warnings:
                    print(f"    {warn['code']} - {warn['message']}")
            return False
        else:
            print(f"VALIDATION PASS: {input_path}")
            if warnings:
                print("  Warnings:")
                for warn in warnings:
                    print(f"    {warn['code']} - {warn['message']}")
            return True
    else:
        # Generate mode: write canonical JSON
        if not is_valid:
            print(f"VALIDATION FAIL: {input_path}")
            for err in errors:
                print(f"  ERROR: {err['code']} - {err['message']}")
            return False

        if output_dir is None:
            output_dir = input_path.parent

        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate canonical JSON
        canonical_json = generate_canonical_json(driver_def)
        output_path = output_dir / input_path.stem.replace('.driver', '') + ".json"
        
        with open(output_path, 'w') as f:
            f.write(canonical_json)

        print(f"Generated canonical JSON: {output_path}")
        
        if warnings:
            print("Warnings:")
            for warn in warnings:
                print(f"  {warn['code']} - {warn['message']}")
        
        return True


def main():
    parser = argparse.ArgumentParser(description="Generate canonical JSON from driver YAML")
    parser.add_argument("input", help="Path to driver YAML file")
    parser.add_argument("output_dir", nargs="?", help="Output directory for JSON (defaults to input dir)")
    parser.add_argument("--check", action="store_true", help="Check mode: validate without generating JSON")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"ERROR: Input file not found: {input_path}")

    output_dir = Path(args.output_dir) if args.output_dir else None
    success = process_driver(input_path, output_dir, args.check)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
