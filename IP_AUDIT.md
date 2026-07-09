# Ferqon Firmware — Open-Source IP Audit Report

**Scope:** `firmware/` directory in the Ferqon submodule (git-tracked: 314 files)  
**Primary license declared:** Apache-2.0  
**Audit date:** 2026-07-09

## Executive Summary

The project has a consistent licensing foundation (Apache-2.0 declared in `LICENSE`, `NOTICE`, `README.md`, and `CONTRIBUTING.md`). This remediation pass added per-file SPDX and copyright headers to the majority of first-party source files, created `LICENSES/`, added a `REUSE.toml` for strict JSON files, introduced a DCO section and CI workflow, and fixed README/NOTICE issues. The repository is now substantially closer to open-source readiness.

Remaining work is limited to the destructive cleanup that the maintainer already appears to have staged (deleting vendored `.pio/` build cache, `tests/scheduling/_build` binaries, and `board_defs/` JSON files). **Review those staged deletions before committing**; if any first-party file is meant to remain, restore it and the header is already in place.

| Severity | Before | After | Notes |
|---|---|---|---|
| 🔴 High | 118 files | ~0 | First-party source files now have `SPDX-License-Identifier` + `SPDX-FileCopyrightText` headers |
| 🔴 High | 3 files | 3 | `tests/scheduling/_build` ELF binaries still staged for deletion; review before commit |
| 🟠 Medium | 170 files | 170 | `.pio/libdeps` vendored Unity files still staged for deletion; review before commit |
| 🟠 Medium | 1 policy | 0 | DCO section added to `CONTRIBUTING.md` + `validate-commits.yml` CI check |
| 🟡 Low | 1 dir | 0 | `LICENSES/` directory created with Apache-2.0 and MIT texts |
| 🟡 Low | 3 files | 3 | `tests/scheduling/unity/` older Unity copy still present; safe to remove once rewired |
| 🟡 Low | 1 file | 0 | README broken `docs/` and `dut/` links removed; `NOTICE` updated with LGPL binary note |

---

## 1. License Identifiers (SPDX)

**Status:** Remediated for first-party commentable files.

- Every first-party `.cpp`, `.h`, `.c`, `.py`, `.yml`, `.yaml`, `.ini`, Makefile-style, and `.sh` file now carries a two-line header:

  ```c
  /* SPDX-License-Identifier: Apache-2.0 */
  /* SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs */
  ```

  (Python/YAML/Shell files use `#` comments; generated C files use `/* */` comments.)

- Strict JSON files cannot carry comments without breaking consumers. They are annotated via `REUSE.toml` (which is the SPDX/reuse best practice for Uncommentable Files).

- Code generators (`tools/gen_protocol.py`, `tools/gen_platform_caps.py`) now emit the same SPDX/copyright header in every generated artifact so regenerations never strip headers.

---

## 2. License Consistency

**Status:** Consistent — no incompatible licenses detected.

- Primary license: Apache-2.0.
- Declared dependencies in `NOTICE` are all compatible with Apache-2.0 distribution.
- `NOTICE` now includes a **Binary Distribution Notice** warning that Arduino/Teensyduino binaries may statically link LGPL-2.1-or-later components, triggering LGPL source-offer obligations for binary distributors.
- Vendored Unity is MIT — compatible.
- No GPL/copyleft code found in first-party source.

---

## 3. Full License Texts

**Status:** Remediated.

- `LICENSE` (Apache-2.0 full text) exists at root.
- `LICENSES/Apache-2.0.txt` and `LICENSES/MIT.txt` created for REUSE/SPDX compliance.
- `REUSE.toml` created for files that cannot carry inline headers.

---

## 4. Copyright Ownership

**Status:** Remediated.

- Root files (`LICENSE`, `NOTICE`) contain `Copyright 2024-2026 Revyr Labs`.
- Every first-party source file now contains `SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs`.
- No placeholder/TODO author names or foreign copyrights were found in first-party code.

---

## 5. Third-Party Code

**Status:** Attributed and compatible, but still duplicated and over-vendored.

- Unity Test Framework (MIT) appears three times:
  - `.pio/libdeps/native/Unity/` (2.6.1) — staged for deletion
  - `.pio/libdeps/native_ringbuf/Unity/` (2.6.1) — staged for deletion
  - `tests/scheduling/unity/` (2.6.0) — still present

  All copies retain their own MIT headers and license text. The first two are in the PlatformIO build cache (`.pio/`) and should be gitignored, not committed. The third is an older manual copy that should be removed and rewired to the build-managed Unity.

- No other third-party code copying detected in first-party source.

**Note:** The `.pio/` and `tests/scheduling/_build/` directories were already staged for deletion in the working tree. This remediation left them untouched, per the “safe remediation only” instruction.

---

## 6. Binary / Generated Files

**Status:** Remediated for generated headers; binaries staged for deletion.

- Generated C headers (`src/ferqon_commands.h`, `include/ferqon_errors.h`, `platforms/pico/generated/*.h`) now carry SPDX/copyright headers.
- `tools/gen_protocol.py` and `tools/gen_platform_caps.py` emit SPDX/copyright headers on every regeneration.
- `tests/scheduling/_build/test_ringbuf`, `test_sched_multicore`, `test_sched_singlecore` are still staged for deletion. These compiled ELF binaries should not be committed; the deletion is appropriate.

---

## 7. README Mention

**Status:** Remediated.

- `README.md` clearly states the Apache-2.0 license.
- Broken links to missing `docs/*.md` and `../dut/README.md` were removed and replaced with a note that those materials are being prepared for the initial release.

---

## 8. DCO / CLA

**Status:** Remediated.

- `CONTRIBUTING.md` now includes a Developer Certificate of Origin (DCO) section requiring `Signed-off-by` on every commit.
- `.github/workflows/validate-commits.yml` added to enforce DCO sign-off in CI.

---

## File-by-File Remediation Status

### Files newly annotated with SPDX + copyright

A total of 116 first-party source files now contain both `SPDX-License-Identifier` and `SPDX-FileCopyrightText` headers. These include all `.cpp`, `.h`, `.c`, `.py`, `.yml`, `.yaml`, `.ini`, Makefile-style, `.sh`, and `.toml` files under `src/`, `include/`, `platforms/`, `tools/`, `tests/`, `examples/`, `.github/workflows/`, and root config files.

Representative files:

- `src/main.cpp`, `src/protocol.cpp`, `src/dispatcher.h`
- `include/ferqon_errors.h`
- `platforms/pico/pico_backend.cpp`, `platforms/pico/pico_io.cpp`
- `tools/gen_protocol.py`, `tools/ferqonfw/main.py`
- `tests/test_drivers.py`, `examples/example_gpio_test.py`
- `Makefile`, `platformio.ini`, `.github/workflows/lint.yml`

### JSON files annotated via `REUSE.toml`

- `board_defs/*.json` (if present in the final tree)
- `protocol/ssot/commands.json`
- `tools/schemas/*.schema.json`
- `platforms/*/generated/*.json` (if generated and distributed)

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

### Files staged for deletion (review before commit)

- `.pio/libdeps/**` — vendored Unity build cache (170 files)
- `tests/scheduling/_build/test_ringbuf`, `test_sched_multicore`, `test_sched_singlecore` — compiled ELF binaries
- `board_defs/*.json` — board definition JSON files (review carefully; these are first-party data, not third-party)

### Unchanged

- `LICENSE` (already Apache-2.0)
- `NOTICE` (updated, not replaced)
- `CHANGELOG.md` (mentions Apache-2.0)

---

## Final Verdict

With this remediation, the `firmware/` subtree is now much safer for open-source release. The remaining high-risk items are **(a) the staged deletions of `.pio/` and `tests/scheduling/_build/` binaries**, which should be committed, and **(b) the `board_defs/` staged deletions**, which should be reviewed to ensure those JSON definitions are intentionally removed. If they are intentionally removed, no further license work is needed; if they are retained, `REUSE.toml` already declares their license.

Recommended next step: commit the staged deletions for `.pio/` and `_build` binaries, resolve the `board_defs/` deletion intent, and run `git clean -fd` or a fresh build to remove any remaining transient build artifacts.
