"""
cmd_validate.py
---------------
Validate command for ferqonfw CLI - validate SSOT JSON files.
"""

import json
import jsonschema
from pathlib import Path

from ferqonfw.board_loader import (
    get_ssot_dir,
    get_schemas_dir,
)


def validate_json_schema(data: dict, schema_path: Path) -> tuple[bool, str]:
    """Validate JSON data against a schema."""
    try:
        with open(schema_path) as f:
            schema = json.load(f)
        jsonschema.validate(instance=data, schema=schema)
        return True, ""
    except FileNotFoundError:
        return False, f"Schema file not found: {schema_path}"
    except json.JSONDecodeError as e:
        return False, f"Schema JSON decode error: {e}"
    except jsonschema.ValidationError as e:
        return False, f"Validation error: {e.message}"


def cmd_validate(args) -> int:
    """Validate SSOT JSON files against their schemas."""
    ssot_dir = get_ssot_dir()
    schemas_dir = get_schemas_dir()

    # Define SSOT files and their schemas
    ssot_files = [
        ("commands.json", "commands.schema.json"),
        ("drivers.json", "drivers.schema.json"),
        ("errors.json", "errors.schema.json"),
        ("capabilities.pico.json", "capabilities.schema.json"),
        ("capabilities.esp32.json", "capabilities.schema.json"),
    ]

    all_ok = True
    errors = []

    for ssot_name, schema_name in ssot_files:
        ssot_path = ssot_dir / ssot_name
        schema_path = schemas_dir / schema_name

        if not ssot_path.exists():
            print(f"SKIP: {ssot_name} not found")
            continue

        print(f"Validating {ssot_name}...")

        try:
            with open(ssot_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  ERROR: JSON decode error: {e}")
            all_ok = False
            errors.append((ssot_name, str(e)))
            continue

        ok, msg = validate_json_schema(data, schema_path)
        if ok:
            print(f"  OK")
        else:
            print(f"  ERROR: {msg}")
            all_ok = False
            errors.append((ssot_name, msg))

    # Additional static analysis checks
    print("\nRunning static analysis...")

    # Check for duplicate command IDs
    commands_path = ssot_dir / "commands.json"
    if commands_path.exists():
        with open(commands_path) as f:
            commands_data = json.load(f)
        cmd_ids = {}
        for name, cmd in commands_data["commands"].items():
            cmd_id = cmd["id"]
            if cmd_id in cmd_ids:
                print(f"  ERROR: Duplicate command ID {cmd_id} used by {cmd_ids[cmd_id]} and {name}")
                all_ok = False
                errors.append(("commands.json", f"Duplicate command ID {cmd_id}"))
            else:
                cmd_ids[cmd_id] = name

    # Check for duplicate driver IDs
    drivers_path = ssot_dir / "drivers.json"
    if drivers_path.exists():
        with open(drivers_path) as f:
            drivers_data = json.load(f)
        driver_ids = {}
        for category in ["builtin", "optional", "custom"]:
            for driver in drivers_data.get(category, []):
                driver_id = driver["id"]
                driver_name = driver["name"]
                if driver_id in driver_ids:
                    print(f"  ERROR: Duplicate driver ID {driver_id} used by {driver_ids[driver_id]} and {driver_name}")
                    all_ok = False
                    errors.append(("drivers.json", f"Duplicate driver ID {driver_id}"))
                else:
                    driver_ids[driver_id] = driver_name

    # Check for duplicate error codes
    errors_path = ssot_dir / "errors.json"
    if errors_path.exists():
        with open(errors_path) as f:
            errors_data = json.load(f)
        error_codes = {}
        for err in errors_data["errors"]:
            err_code = err["code"]
            err_name = err["name"]
            if err_code in error_codes:
                print(f"  ERROR: Duplicate error code {err_code} used by {error_codes[err_code]} and {err_name}")
                all_ok = False
                errors.append(("errors.json", f"Duplicate error code {err_code}"))
            else:
                error_codes[err_code] = err_name

    if all_ok:
        print("\nAll validations passed!")
        return 0
    else:
        print(f"\n{len(errors)} validation error(s) found")
        if args.json:
            print(json.dumps({"errors": errors}, indent=2))
        return 1
