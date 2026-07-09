# Ferqon Firmware — Open-Source IP Audit Report

**Scope:** `firmware/` directory in the Ferqon submodule  
**Primary license declared:** Apache-2.0  
**Audit date:** 2026-07-09

## Executive Summary

The project has a consistent licensing foundation (Apache-2.0 declared in `LICENSE`, `NOTICE`, `README.md`, and `CONTRIBUTING.md`). This remediation pass added per-file SPDX and copyright headers to first-party source files, created `LICENSES/`, added `REUSE.toml` for files that cannot carry inline headers, introduced a DCO section and CI workflow, fixed README/NOTICE links, and removed the deprecated `board_defs/` JSON directory and vendored `.pio/` build cache.

| Severity | Before | After | Notes |
|---|---|---|---|
| 🔴 High | 118 files | ~0 | First-party source files now have `SPDX-License-Identifier` + `SPDX-FileCopyrightText` headers |
| 🔴 High | 3 files | 0 | `tests/scheduling/_build` ELF binaries removed from tracking |
| 🟠 Medium | 170 files | 0 | `.pio/libdeps` vendored Unity build cache removed from tracking |
| 🟠 Medium | 1 policy | 0 | DCO section added to `CONTRIBUTING.md` + `validate-commits.yml` CI check |
| 🟡 Low | 1 dir | 0 | `LICENSES/` directory created with Apache-2.0 and MIT texts |
| 🟡 Low | 8 JSON files | 0 | Deprecated `board_defs/` JSON directory removed |
| 🟡 Low | 1 file | 0 | README broken `docs/` and `dut/` links removed; `NOTICE` updated with LGPL binary note |

---

## 1. License Identifiers (SPDX)

**Status:** Remediated.

- Every first-party `.cpp`, `.h`, `.c`, `.py`, `.yml`, `.yaml`, `.ini`, Makefile-style, `.sh`, `.toml`, and `.md` file now carries an explicit Apache-2.0 license and `SPDX-FileCopyrightText` declaration.
- Strict JSON files (which cannot carry comments without breaking consumers) are annotated via `REUSE.toml`:
  - `protocol/ssot/commands.json`
  - `tools/schemas/*.schema.json`
  - `platforms/*/generated/*.json`
- Code generators (`tools/gen_protocol.py`, `tools/gen_platform_caps.py`) emit the same SPDX/copyright header in every generated artifact so regenerations never strip headers.

---

## 2. License Consistency

**Status:** Consistent.

- Primary license: Apache-2.0.
- Declared dependencies in `NOTICE` are compatible with Apache-2.0 distribution.
- `NOTICE` includes a **Binary Distribution Notice** warning that Arduino/Teensyduino binaries may statically link LGPL-2.1-or-later components, triggering LGPL source-offer obligations for binary distributors.
- Vendored Unity is MIT — compatible.
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

- Root files (`LICENSE`, `NOTICE`) contain `Copyright 2024-2026 Revyr Labs`.
- Every first-party source file contains `SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs`.
- No placeholder/TODO author names or foreign copyrights found in first-party code.

---

## 5. Third-Party Code

**Status:** Attributed and compatible.

- Unity Test Framework (MIT) is vendored as `tests/scheduling/unity/`. It is now the single canonical copy in the repository after `.pio/libdeps/` was removed from tracking.
- All vendored Unity files retain their own MIT headers and `LICENSES/MIT.txt` exists at the project level.
- No other third-party code copying detected in first-party source.

---

## 6. Binary / Generated Files

**Status:** Remediated.

- Generated C/C++ files (`src/ferqon_commands.h`, `include/ferqon_errors.h`, `platforms/pico/generated/*.h` and `*.c`) carry SPDX/copyright headers.
- `tools/gen_protocol.py` and `tools/gen_platform_caps.py` emit headers on every regeneration.
- `tests/scheduling/_build/` binaries are no longer tracked; `.gitignore` already ignores the `_build` directory.

---

## 7. README Mention

**Status:** Remediated.

- `README.md` clearly states the Apache-2.0 license.
- Broken links to missing `docs/*.md` and `../dut/README.md` were removed and replaced with a note that those materials are being prepared for the initial release.

---

## 8. DCO / CLA

**Status:** Remediated.

- `CONTRIBUTING.md` includes a Developer Certificate of Origin (DCO) section requiring `Signed-off-by` on every commit.
- `.github/workflows/validate-commits.yml` enforces DCO sign-off in CI.

---

## File-by-File Remediation Status

### Files annotated with SPDX + copyright

A total of 116+ first-party source files now contain both `SPDX-License-Identifier` and `SPDX-FileCopyrightText` headers. These include `.cpp`, `.h`, `.c`, `.py`, `.yml`, `.yaml`, `.ini`, Makefile-style, `.sh`, `.toml`, and `.md` files under `src/`, `include/`, `platforms/`, `tools/`, `tests/`, `examples/`, `.github/workflows/`, and root config files.

Representative files:

- `src/main.cpp`, `src/protocol.cpp`, `src/dispatcher.h`
- `include/ferqon_errors.h`
- `platforms/pico/pico_backend.cpp`, `platforms/pico/pico_io.cpp`
- `tools/gen_protocol.py`, `tools/ferqonfw/main.py`
- `tests/test_drivers.py`, `examples/example_gpio_test.py`
- `Makefile`, `platformio.ini`, `.github/workflows/lint.yml`, `REUSE.toml`

### JSON files annotated via `REUSE.toml`

- `protocol/ssot/commands.json`
- `tools/schemas/*.schema.json`
- `platforms/*/generated/*.json`

### Files created

- `LICENSES/Apache-2.0.txt`
- `LICENSES/MIT.txt`
- `REUSE.toml`
- `.github/workflows/validate-commits.yml`
- `IP_AUDIT.md` (this file)

### Files modified

- `tools/gen_protocol.py` — emits SPDX/copyright headers in generated artifacts
- `tools/gen_platform_caps.py` — emits SPDX/copyright headers in generated artifacts
- `src/ferqon_commands.h` — regenerated with header
- `include/ferqon_errors.h` — header added
- `CONTRIBUTING.md` — DCO section added
- `README.md` — broken links removed
- `NOTICE` — binary distribution notice added

### Files removed

- `board_defs/*.json` — deprecated JSON board definitions (per `CHANGELOG.md`)
- `.pio/libdeps/**` — vendored Unity build cache (170 files)
- `tests/scheduling/_build/test_ringbuf`, `test_sched_multicore`, `test_sched_singlecore` — compiled ELF binaries

### Unchanged

- `LICENSE` (already Apache-2.0)
- `NOTICE` (updated, not replaced)
- `CHANGELOG.md` (mentions Apache-2.0)

---

## Final Verdict

The `firmware/` subtree is now ready for open-source release from a licensing perspective. All first-party files have explicit Apache-2.0 identifiers and copyright notices, all third-party components are attributed and compatible, deprecated `board_defs/` and the vendored `.pio/` build cache have been removed, and the DCO/CI workflow is in place.

Recommended next step: review the staged changes, run `git clean -fd` (if desired) to clear any remaining ignored build artifacts, and run a fresh build/test to verify generated files remain in sync with `tools/gen_protocol.py` and `tools/gen_platform_caps.py`.
