# Contributing to Ferqon Firmware

Thank you for your interest in contributing to Ferqon Firmware! This document provides guidelines for contributing.

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to [conduct@revyrlabs.com](mailto:conduct@revyrlabs.com).

## How to Contribute

### Reporting Bugs

Report bugs using GitHub Issues. Include:
- Hardware platform (MCU, board variant)
- Backend (Arduino, Pico SDK, etc.)
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs or error messages

### Suggesting Enhancements

Use GitHub Issues to propose new features or enhancements. Provide:
- Clear description of the proposed change
- Motivation and use case
- Potential implementation approach

### Adding a New Board

See [docs/adding_a_board.md](docs/adding_a_board.md) for a complete guide. The short version:

```bash
# Scaffold a new platform
tools/new_board.py my_board --mcu rp2040 --backend arduino

# Fill in board.yml
vim platforms/my_board/board.yml

# Implement platform files
# - my_board_backend.cpp (vtable registration)
# - my_board_io.cpp (hardware ops, gated by ferqon_cap_* macros)
# - my_board_system.cpp (clocks, watchdog, USB-CDC)
# - my_board_config.cpp (persistent storage)

# Generate headers
tools/gen_platform_caps.py platforms/my_board/board.yml

# Build and test
pio run -e my_board_arduino
```

**Critical:** Never edit files in `platforms/*/generated/` manually. These are auto-generated from `board.yml`.

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run `tools/gen_platform_caps.py --all` and commit any generated changes
5. Run tests: `pio test -e native` (native tests) and `pio run` (build matrix)
6. Commit with clear messages
7. Push to your fork (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Workflow

1. **Clone with submodules:**
   ```bash
   git clone --recurse-submodules https://github.com/repvi/Ferqon.git
   cd Ferqon/firmware
   ```

2. **Install dependencies:**
   ```bash
   pip install -r tools/requirements.txt
   ```
   This installs PlatformIO Core and the Python tools used by the build.

3. **Regenerate headers after YAML changes:**
   ```bash
   tools/gen_platform_caps.py --all
   ```

4. **Check for drift (CI runs this):**
   ```bash
   tools/gen_platform_caps.py --check
   ```

5. **Build:**
   ```bash
   pio run -e pico_arduino
   ```

6. **Test:**
   ```bash
   pio test -e native
   ```

## Coding Standards

### C/C++ Code

- Use 4-space indentation (no tabs)
- Follow existing style in `src/` and `platforms/`
- Platform-specific code must use `ferqon_cap_*()` guards before hardware access
- Never include vendor SDK headers in `src/`
- Keep functions under 50 lines when possible
- Add comments for non-obvious logic

### Python Code

- Use `ruff` for linting (`ruff check tools/`)
- Use `black` for formatting (`black tools/`)
- Follow PEP 8
- Add type hints where helpful

### YAML Files

- Use 2-space indentation
- Sort arrays alphabetically where order doesn't matter
- Add comments for non-obvious fields

## Generator Drift

The CI pipeline runs `tools/gen_platform_caps.py --check` on every PR. If `board.yml` and `generated/` are out of sync, the build fails. Always regenerate headers after modifying YAML and commit both together.

## Platform Capability Guards

Every hardware operation in `platforms/<slug>/` must be gated:

```c
int pico_gpio_put(uint8_t pin, uint8_t val) {
    if (!ferqon_cap_pin_is_valid(pin))    return FERQON_ERR_INVALID_PIN;
    if (ferqon_cap_pin_is_reserved(pin))  return FERQON_ERR_RESERVED_PIN;
    gpio_put(pin, val);
    return FERQON_OK;
}
```

The CI linter `tools/lint_platform_guards.py` enforces this.

## Testing

- **Native tests:** Run `pio test -e native` to verify `src/` portability
- **Hardware tests:** Use `tools/diagnose.py` for smoke testing on real devices
- **PlatformIO matrix:** CI builds all environments to catch platform-specific breakage

## Developer Certificate of Origin (DCO)

This project uses the [Developer Certificate of Origin](https://developercertificate.org/) (DCO) to certify that every contribution is submitted by someone who has the right to do so. By contributing, you agree to the terms of the DCO.

To indicate agreement, every commit message must include a `Signed-off-by:` line that matches the commit author's name and email:

```text
This is my commit message

Signed-off-by: Your Name <your.email@example.com>
```

You can add this automatically with `git commit -s`.

Pull requests without a `Signed-off-by` line on every commit will be blocked by CI.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

## Questions?

- Open an issue for bugs or feature requests
- Check [docs/](docs/) for detailed documentation
- Email [support@revyrlabs.com](mailto:support@revyrlabs.com) for private questions
