# Tools

Ferqon firmware includes a set of tools for building, flashing, and managing firmware. All tools are in the `tools/` directory.

## Production CLI (`ferqonfw`)

The production CLI is the **only** interface for building, flashing, and communicating with devices. The Makefile handles environment setup and production bundling only. It is defined in `tools/ferqonfw/main.py` and installed by `make init`.

Key commands:
- `ferqonfw build <board>` — Build firmware for a board
- `ferqonfw build all` — Build all production boards
- `ferqonfw flash <board> --port <port>` — Flash firmware to a device
- `ferqonfw flash <board> --port <port> --build` — Build + flash in one step
- `ferqonfw clean <board>` — Clean build artifacts for a board
- `ferqonfw clean all` — Clean all production boards
- `ferqonfw identify --port <port>` — Detect Ferqon firmware on a device
- `ferqonfw selftest --port <port>` — Run self-test on a device
- `ferqonfw doctor` — Check environment and dependencies
- `ferqonfw list` — List available platforms
- `ferqonfw info <board>` — Show board capabilities
- `ferqonfw packet encode/decode` — Encode and decode protocol packets

Run `ferqonfw --help` for the full command list.

## Development CLI (`ferqonfw-dev`)

The development CLI extends `ferqonfw` with code generation, validation, testing, and emulator-based testing. It is defined in `tools/ferqonfw/dev_main.py` and installed by `make init-dev`.

Key commands:
- `ferqonfw-dev gen core` — Generate protocol headers from SSOT
- `ferqonfw-dev gen board <name>` — Generate per-board capability tables
- `ferqonfw-dev gen all` — Generate all artifacts
- `ferqonfw-dev validate` — Validate SSOT JSON files
- `ferqonfw-dev drivers list` — List drivers and their status
- `ferqonfw-dev test` — Run native unit tests (no hardware required)
- `ferqonfw-dev selftest --emulator` — Self-test using in-process emulator

## Code Generators

- `tools/gen_protocol.py` — Generates protocol constants header from `protocol/ssot/commands.json`
- `tools/gen_platform_caps.py` — Generates board capability headers from `platforms/<board>/board.yml`

These are development-time tools. Their output is committed to the repository and verified by CI drift checks. They are not invoked by the production build hook.

## Build Hook

`tools/pio_pre_build.py` is the PlatformIO pre-build hook. It generates runtime configuration (baud rate, heartbeat, log level) from `tools/production_config.json` and validates board artifacts before each build.

## Production Bundle

- `tools/create_production_bundle.py` — Creates a sealed source bundle excluding development-only files
- `tools/cleanroom_verify.py` — Builds all production environments from an isolated bundle with empty caches

## Linting

- `tools/lint_platform_guards.py` — Enforces that all Arduino API calls in the portable core are preceded by capability guard checks

## Emulator

`tools/ferqon_emulator.py` is an in-process serial emulator for development testing. It is not included in the production bundle.
