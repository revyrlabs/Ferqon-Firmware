/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs */
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
