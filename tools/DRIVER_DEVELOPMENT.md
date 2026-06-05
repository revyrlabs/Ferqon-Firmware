# Driver Development Guide

This guide helps you develop drivers for the Ferqon server efficiently.

## Quick Start

### 1. Create a Driver YAML

Create a YAML file for your driver:

```yaml
name: led_pwm
version: "1.0.0"
description: LED driver with PWM brightness control

commands:
  set_brightness:
    args:
      brightness:
        type: int
        min: 0
        max: 100
    returns: status

  toggle:
    args: {}
    returns: status

modes:
  - id: normal
    label: Normal
    default: true
    type: runtime
    commands:
      - set_brightness
      - toggle

ui:
  groups:
    - id: control
      label: Control
      order: 1
      layout: sliders
```

### 2. Validate the Driver

Check for errors before generating JSON:

```bash
python3 tools/gen_driver_json.py --check my_led.driver.yml
```

### 3. Generate Canonical JSON

Generate the final JSON for server storage:

```bash
python3 tools/gen_driver_json.py my_led.driver.yml
```

### 4. Upload to Server

Use the API to upload your driver:

```bash
curl -X POST http://localhost:8000/api/drivers \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@my_led.json"
```

## Developer-Friendly Features

### YAML Authoring
- Human-readable format
- Comments supported
- Easier to maintain than JSON

### Validation Tools
- Schema validation (Pydantic models)
- UI block validation
- Mode transition validation
- Pin capability matching
- Configuration guard for safety

### IDE Support
- JSON Schema for validation
- VS Code extension (coming soon)
- Syntax highlighting

## Configuration Guard

The system includes a configuration guard that validates driver definitions for safety:

### Protection Features
- **Schema Validation**: Ensures structure matches expected format
- **Type Safety**: Validates argument types and return types
- **Range Validation**: Enforces min/max constraints on numeric values
- **Reference Validation**: Ensures all referenced commands and groups exist
- **Mode Safety**: Validates mode transitions and default mode constraints
- **Pin Safety**: Validates pin assignments against device capabilities
- **UI Consistency**: Ensures UI groups and binds are valid

### Using the Configuration Guard

The configuration guard is automatically applied when:
- Uploading drivers via the API
- Creating driver bindings
- Switching driver modes

You can also manually validate:

```bash
python3 tools/gen_driver_json.py --check my_led.driver.yml
```

This will report any safety violations before the driver is deployed.

## Common Patterns

### LED Driver
```yaml
commands:
  set_brightness:
    args:
      brightness: {type: int, min: 0, max: 100}
    returns: status
  toggle: {args: {}, returns: status}
```

### Servo Driver
```yaml
commands:
  set_angle:
    args:
      angle: {type: int, min: 0, max: 180}
    returns: status
  calibrate: {args: {}, returns: status}

modes:
  - id: normal
    label: Normal
    default: true
    type: runtime
  - id: calibrating
    label: Calibrating
    type: runtime
    enter_command: calibrate
```

### Sensor Driver
```yaml
commands:
  read: {args: {}, returns: value}
  calibrate: {args: {}, returns: status}

provides:
  channels:
    - name: reading
      type: float
      unit: °C

ui:
  groups:
    - id: readout
      label: Readout
      layout: readouts
```

## Testing Your Driver

Use the validation API to test before deploying:

```bash
curl -X POST http://localhost:8000/api/drivers/validate \
  -H "Content-Type: application/json" \
  -d '{"driver_def": {...}, "device_type": "pico"}'
```

The configuration guard will automatically validate:
- Schema structure
- Type safety
- Range constraints
- Reference validity
- Mode transitions
- Pin assignments
- UI consistency

## Future Features

The following features are planned for future releases but are not currently integrated:

### AI-Powered Analysis (Future)
Planned AI-powered static analysis for driver configurations:
- Intelligent summary generation
- Improvement suggestions
- Complexity assessment
- Automatic documentation
- Warning detection

This feature is currently stubbed for future development when base features are complete.

## Advanced Topics

### Custom UI Layouts
```yaml
ui:
  groups:
    - id: advanced
      label: Advanced Settings
      order: 2
      layout: form
      bind: [config_mode]
```

### Conditional Visibility
```yaml
commands:
  advanced_config:
    ui:
      visible_when:
        mode: config
```

### Mode Transitions
```yaml
modes:
  - id: normal
    type: runtime
    enter_command: initialize
    exit_command: cleanup
```

## Testing Your Driver

Use the validation API to test before deploying:

```bash
curl -X POST http://localhost:8000/api/drivers/validate \
  -H "Content-Type: application/json" \
  -d '{"driver_def": {...}, "device_type": "pico"}'
```

## Troubleshooting

### Validation Errors
- Check error codes in output
- Review schema documentation
- Use `--check` flag for detailed errors
- Configuration guard prevents invalid configurations from being deployed

### Pin Conflicts
- Check device capabilities in `platforms/<device>/generated/capabilities.json`
- Configuration guard validates pin assignments against device capabilities
- Use validation API to test before deploying

### Mode Issues
- Ensure exactly one mode has `default: true`
- Verify all referenced commands exist
- Check transition commands are valid
- Configuration guard validates mode transitions

## Next Steps

1. Create your first driver using the YAML template
2. Validate with the configuration guard
3. Test with a real device
4. Contribute to the driver library
5. Share your patterns for others to use
