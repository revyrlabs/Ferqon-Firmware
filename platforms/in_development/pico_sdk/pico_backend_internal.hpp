/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/* ── STUB / NON-COMPILABLE ──────────────────────────────────────────────────
 * This file is part of an in-development Pico-SDK platform abstraction
 * layer (PAL). It references platform/ferqon_plt_*.h headers that are NOT
 * yet present in this repository, so it does NOT compile. It is not built
 * by any PlatformIO environment and is excluded from the production
 * bundle. Kept for future PAL development only — do not depend on it.
 * ──────────────────────────────────────────────────────────────────────── */
/**
 * pico_backend_internal.hpp
 * -------------------------
 * Internal Pico factory functions for creating platform operation tables.
 *
 * These are called only by the backend initialization code.
 * General firmware code should never call these directly.
 */
#pragma once

#include "platform/ferqon_plt_system.h"
#include "platform/ferqon_plt_io.h"
#include "platform/ferqon_plt_config.h"

#ifdef __cplusplus
extern "C" {
#endif

FERQON_PLT_SystemOps pico_make_system_ops(void);
FERQON_PLT_IoOps pico_make_io_ops(void);
FERQON_PLT_ConfigOps pico_make_config_ops(void);

#ifdef __cplusplus
}
#endif
