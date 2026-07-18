# Validation Model

Ferqon uses three layers of validation to keep hardware access safe and predictable.

## Layer 1: Build-Time (Schema)

`board.yml` is validated against a JSON schema by the code generator and the PlatformIO pre-build hook. This catches missing required fields, invalid backend values, and malformed peripheral definitions before any code is compiled.

## Layer 2: Generate-Time (Code Generation)

The code generator turns `board.yml` into typed C headers: compile-time constants, inline capability validation functions, and channel descriptors. These are committed to the repository and checked for drift in CI — if a generated header doesn't match what the generator would produce from the current `board.yml`, the build fails.

## Layer 3: Runtime (Capability Guards)

Every hardware operation in the portable core calls `ferqon_cap_*()` validation functions before touching hardware. These inline functions — generated from `board.yml` — check pin validity, reserved status, and peripheral support. Invalid access is rejected with a structured error before any hardware register is touched.

The CI linter (`tools/lint_platform_guards.py`) statically enforces that every Arduino API call in the portable core is preceded by a capability guard check.

## Error Mapping

| Failure Mode | Layer | Result |
|--------------|-------|--------|
| Invalid `board.yml` | 1 | Build failure |
| Generated header drift | 2 | CI drift check fails |
| Pin out of range | 3 | `FERQON_ERR_UNSUPPORTED_PIN` |
| Reserved pin touched | 3 | `FERQON_ERR_UNSUPPORTED_PIN` |
| Missing capability guard | 3 | Linter error in CI |
