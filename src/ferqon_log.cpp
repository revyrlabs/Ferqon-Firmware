/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/* Debug logging implementation and runtime level. */
#include "ferqon_log.h"
#include "ferqon_hal.h"
#include "protocol.h"
#include "production_config.h"
#include <stdarg.h>
#include <stdio.h>

uint8_t g_debug_level = FERQON_LOG_LEVEL_DEFAULT;
static char s_log_buf[128];

void ferqon_vlog(uint8_t level, const char *fmt, ...) {
    if (g_debug_level < level) return;

    va_list ap;
    va_start(ap, fmt);
    vsnprintf(s_log_buf, sizeof(s_log_buf), fmt, ap);
    va_end(ap);

    ferqon_send_log(s_log_buf);
}

void ferqon_log_raw(const char *msg) {
    if (msg) ferqon_hal_log_raw(msg);
}
