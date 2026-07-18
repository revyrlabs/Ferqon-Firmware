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
# Create a new platform directory
mkdir -p platforms/in_development/my_board
cp platforms/pico/board.yml platforms/in_development/my_board/board.yml

# Fill in board.yml for your hardware
vim platforms/in_development/my_board/board.yml

# Generate headers
ferqonfw-dev gen board my_board

# Or generate all artifacts at once
ferqonfw-dev gen all

# Build and test
ferqonfw build my_board
ferqonfw-dev test
```

**Critical:** Never edit files in `platforms/*/generated/` manually. These are auto-generated from `board.yml`.

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run `ferqonfw-dev gen all` and commit any generated changes
5. Run `python3 tools/gen_platform_caps.py --all --check` and `python3 tools/gen_protocol.py --check` to verify no drift
6. Run tests: `ferqonfw-dev test` (native tests) and `ferqonfw build all` (build matrix)
7. Run lint: `ruff check .` and `black --check .`
8. Commit with clear messages (use `git commit -s` for DCO sign-off)
9. Push to your fork (`git push origin feature/amazing-feature`)
10. Open a Pull Request

### Development Workflow

1. **Clone the repo:**
   ```bash
   git clone https://github.com/revyrlabs/Ferqon-Firmware.git
   cd Ferqon-Firmware
   ```

2. **Install dependencies:**
   ```bash
   make init-dev
   ```
   This installs PlatformIO Core, the `ferqonfw` CLI, the `ferqonfw-dev` CLI,
   and all development tools (pytest, ruff, black, yamllint). The canonical
   dependency declarations are in `pyproject.toml`.

   On Linux systems with an externally-managed Python (PEP 668 — modern
   Debian/Ubuntu/Fedora), `make init-dev` creates a virtual environment at
   `.venv/` automatically. Activate it before running any commands:
   ```bash
   source .venv/bin/activate
   ```
   If you already have a venv active, `make init-dev` installs into it
   directly.

3. **Regenerate headers after YAML changes:**
   ```bash
   ferqonfw-dev gen all
   ```

4. **Check for drift (CI runs this):**
   ```bash
   python3 tools/gen_platform_caps.py --all --check
   python3 tools/gen_protocol.py --check
   ```

5. **Build:**
   ```bash
   ferqonfw build pico
   ```

6. **Test:**
   ```bash
   ferqonfw-dev test
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

Every hardware operation in `src/` that accesses pins must be gated with
the generated `ferqon_cap_*()` validators from `pin_macros.h`:

```c
#include "pin_macros.h"

if (!ferqon_cap_pin_is_valid(pin) || ferqon_cap_pin_is_reserved(pin)) {
    ferqon_send_error(seq, cmd_id, FERQON_ERR_UNSUPPORTED_PIN, ...);
    return true;
}
pinMode(pin, mode);
```

The CI linter `tools/lint_platform_guards.py` scans both `src/` and
`platforms/` for unguarded Arduino API calls.

## Testing

- **Native tests:** Run `ferqonfw-dev test` to verify `src/` portability
- **Hardware tests:** Use `ferqonfw selftest --port /dev/ttyACM0` for smoke testing on real devices, or `ferqonfw-dev selftest --emulator` for the in-process emulator
- **Flash + test workflow:** `ferqonfw flash <board> --port <port> --build` then `ferqonfw selftest --port <port>`
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
