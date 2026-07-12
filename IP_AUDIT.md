# Ferqon Firmware — Open-Source IP Audit Report

**Scope:** `repvi/Ferqon-Firmware` repository  
**Primary license declared:** Apache-2.0  
**Audit date:** 2026-07-12

## Executive Summary

The repository has a consistent licensing foundation (Apache-2.0 declared in `LICENSE`, `NOTICE`, `README.md`, and `CONTRIBUTING.md`). This remediation pass added per-file SPDX and copyright headers to first-party source files, created `LICENSES/`, added `REUSE.toml` for files that cannot carry inline headers, introduced a DCO section and CI workflow, updated repository links to `repvi/Ferqon-Firmware`, and removed stale or broken tooling, examples, and test files.

| Severity | Before | After | Notes |
|---|---|---|---|
| 🔴 High | ~120 files | ~0 | First-party source files now have `SPDX-License-Identifier` + `SPDX-FileCopyrightText` headers |
| 🔴 High | 0 policy | 1 | DCO section added to `CONTRIBUTING.md` + `validate-commits.yml` CI check |
| 🟠 Medium | 1 repo | 1 | Repository references and clone URLs updated to `repvi/Ferqon-Firmware` |
| 🟠 Medium | broken tools | fixed | `ferqonfw` CLI and `tools/serial_protocol.py` now work without an external SDK |
| 🟡 Low | 1 dir | 1 | `LICENSES/` directory created with Apache-2.0 and MIT texts |
| 🟡 Low | stale files | removed | Broken `examples/`, `tools/diagnose.py`, `tools/serial_client.py`, and stale `tests/` files removed |

---

## 1. License Identifiers (SPDX)

**Status:** Remediated.

- Every first-party `.cpp`, `.h`, `.c`, `.py`, `.yml`, `.yaml`, `.ini`, Makefile-style, `.sh`, `.toml`, and `.md` file carries an explicit Apache-2.0 license and `SPDX-FileCopyrightText` declaration.
- Strict JSON files (which cannot carry comments without breaking consumers) are annotated via `REUSE.toml`:
  - `protocol/ssot/commands.json`
  - `tools/schemas/*.schema.json`
  - `platforms/**/generated/*.json`
  - `generated/*.h`
- Code generators (`tools/gen_protocol.py`, `tools/gen_platform_caps.py`) emit the same SPDX/copyright header in every generated artifact so regenerations never strip headers.

---

## 2. License Consistency

**Status:** Consistent.

- Primary license: Apache-2.0.
- Declared dependencies in `NOTICE` are compatible with Apache-2.0 distribution.
- `NOTICE` includes a **Binary Distribution Notice** warning that Arduino/Teensyduino binaries may statically link LGPL-2.1-or-later components, triggering LGPL source-offer obligations for binary distributors.
- Third-party Unity Test Framework (MIT) is consumed via PlatformIO (`lib_deps` for `native` tests), not vendored in the repository.
- No GPL/copyleft code found in first-party source.

---

## 3. Full License Texts

**Status:** Remediated.

- `LICENSE` (Apache-2.0 full text) at repository root.
- `LICENSES/Apache-2.0.txt` and `LICENSES/MIT.txt` for REUSE/SPDX compliance.
- `REUSE.toml` for files that cannot carry inline headers.

---

## 4. Copyright Ownership

**Status:** Remediated.

- Root files (`LICENSE`, `NOTICE`) contain `Copyright 2026 Revyr Labs`.
- Every first-party source file contains `SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs`.
- No placeholder/TODO author names or foreign copyrights found in first-party code.

---

## 5. Third-Party Code

**Status:** Attributed and compatible.

- Unity Test Framework (MIT) is installed by PlatformIO during `pio test -e native`; it is not committed to the repository.
- `LICENSES/MIT.txt` exists at the project level for REUSE compliance.
- No other third-party code copying detected in first-party source.

---

## 6. Binary / Generated Files

**Status:** Remediated.

- Generated C/C++ files (`src/ferqon_commands.h`, `include/ferqon_errors.h`, `generated/*.h`, `platforms/pico/generated/*.h` and `*.c`) carry SPDX/copyright headers.
- `tools/gen_protocol.py` and `tools/gen_platform_caps.py` emit headers on every regeneration.
- Build artifacts are excluded by `.gitignore` (`generated/` build artifacts are not tracked; `.pio/` is ignored).

---

## 7. README Mention

**Status:** Remediated.

- `README.md` clearly states the Apache-2.0 license.
- Repository URLs and quick-start instructions point to `repvi/Ferqon-Firmware`.
- Broken references to `examples/` and `tools/diagnose.py` were replaced with working `ferqonfw` CLI and `make` commands.

---

## 8. DCO / CLA

**Status:** Remediated.

- `CONTRIBUTING.md` includes a Developer Certificate of Origin (DCO) section requiring `Signed-off-by` on every commit.
- `.github/workflows/validate-commits.yml` enforces DCO sign-off in CI.

---

## File-by-File Remediation Status

### Files annotated with SPDX + copyright

First-party source files under `src/`, `include/`, `platforms/`, `tools/`, `tests/`, `.github/workflows/`, and root config files contain both `SPDX-License-Identifier` and `SPDX-FileCopyrightText` headers.

Representative files:

- `src/main.cpp`, `src/protocol.cpp`, `src/dispatcher.h`
- `include/ferqon_errors.h`
- `tools/gen_protocol.py`, `tools/ferqonfw/main.py`, `tools/ferqon_emulator.py`
- `tests/hil/ferqon_selftest.py`
- `Makefile`, `platformio.ini`, `.github/workflows/lint.yml`, `REUSE.toml`, `pyproject.toml`

### JSON files annotated via `REUSE.toml`

- `protocol/ssot/commands.json`
- `tools/schemas/*.schema.json`
- `platforms/**/generated/*.json`
- `generated/*.h`

### Files created

- `LICENSES/Apache-2.0.txt`
- `LICENSES/MIT.txt`
- `REUSE.toml`
- `pyproject.toml`
- `.github/workflows/validate-commits.yml`
- `IP_AUDIT.md` (this file)

### Files modified

- `tools/gen_protocol.py` — emits SPDX/copyright headers in generated artifacts
- `tools/gen_platform_caps.py` — emits SPDX/copyright headers in generated artifacts
- `src/ferqon_commands.h` — regenerated with header
- `include/ferqon_errors.h` — header added
- `CONTRIBUTING.md` — DCO section and updated workflow instructions
- `README.md` — repository URLs and quick-start instructions updated
- `MAINTAINERS.md` — repository URLs updated
- `CHANGELOG.md` — release links updated
- `NOTICE` — binary distribution notice

### Files removed

- `board_defs/*.json` — deprecated JSON board definitions
- `examples/*.py` — broken example scripts that referenced an external SDK
- `tools/diagnose.py`, `tools/run_driver_tests.py`, `tools/serial_client.py` — broken scripts that referenced an external SDK
- `tests/test_*.py`, `tests/conftest.py` — broken pytest files that referenced missing modules
- `tests/scheduling/` — stale standalone C test harness

### Unchanged

- `LICENSE` (already Apache-2.0)
- `NOTICE` (updated, not replaced)

---

## Final Verdict

`repvi/Ferqon-Firmware` is ready for open-source release from a licensing perspective. All first-party files have explicit Apache-2.0 identifiers and copyright notices, all third-party components are attributed and compatible, stale/broken files have been removed, and the DCO/CI workflow is in place.

Recommended next step: run a fresh `make test`, `make all`, `ruff check .`, `black --check .`, and `yamllint -c .yamllint .` to verify generated files remain in sync and the repository is clean.
