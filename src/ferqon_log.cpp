/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/* Debug logging implementation and runtime level. */
#include "ferqon_log.h"
#include "production_config.h"

/* Runtime debug level — default from production_config.h (INFO). */
uint8_t g_debug_level = FERQON_LOG_LEVEL_DEFAULT;
