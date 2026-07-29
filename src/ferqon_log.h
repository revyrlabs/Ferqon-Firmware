/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#ifndef FERQON_LOG_H
#define FERQON_LOG_H

#include <Arduino.h>
#include <stdio.h>

/* Structured logging helpers and runtime level control. */

/* Log levels — ordered by verbosity. Higher value = more verbose.
 * OFF(0) → INFO(1) → DEBUG(2, alias of VERBOSE). ERROR always fires.
 * WARN shares the INFO threshold by design: warnings are at least as
 * severe as info, so any level that shows INFO also shows WARN. */
#define FERQON_LOG_LEVEL_OFF     0
#define FERQON_LOG_LEVEL_INFO    1
#define FERQON_LOG_LEVEL_VERBOSE 2
#define FERQON_LOG_LEVEL_DEBUG   FERQON_LOG_LEVEL_VERBOSE

/* Log subtypes for structured binary logs */
#define FERQON_LOG_SUBTYPE_PARSER_RESET    0x01
#define FERQON_LOG_SUBTYPE_CRC_MISMATCH    0x02
#define FERQON_LOG_SUBTYPE_FRAME_RECEIVED  0x03
#define FERQON_LOG_SUBTYPE_DISPATCH_ROUTED 0x10
#define FERQON_LOG_SUBTYPE_DISPATCH_UNHANDLED 0x11
#define FERQON_LOG_SUBTYPE_STATE_CHANGE    0x30

/* Runtime debug level (default: INFO) */
extern uint8_t g_debug_level;

/* Protocol forward declaration for log routing */
void ferqon_send_log(const char *msg);

/* Raw log for boot-time messages before protocol is initialized */
#define FERQON_LOG_RAW(msg) \
    Serial.print("[RAW] "); Serial.println(msg)

/* Internal generator macro — do not use directly. All four public
 * log macros below share the same body; only the threshold differs.
 * ERROR uses FERQON_LOG_LEVEL_OFF so it always fires. */
#define FERQON_LOG_IMPL(level, fmt, ...) \
    do { \
        if (g_debug_level >= (level)) { \
            char _ferqon_log_buf[128]; \
            snprintf(_ferqon_log_buf, sizeof(_ferqon_log_buf), fmt, ##__VA_ARGS__); \
            ferqon_send_log(_ferqon_log_buf); \
        } \
    } while (0)

/* Log macros - route through protocol framing when debug is enabled.
 * They support printf-style formatting: FERQON_LOG_INFO("x=%d", x). */
#define FERQON_LOG_DEBUG(fmt, ...) FERQON_LOG_IMPL(FERQON_LOG_LEVEL_DEBUG, fmt, ##__VA_ARGS__)
#define FERQON_LOG_INFO(fmt, ...)  FERQON_LOG_IMPL(FERQON_LOG_LEVEL_INFO,  fmt, ##__VA_ARGS__)
#define FERQON_LOG_WARN(fmt, ...)  FERQON_LOG_IMPL(FERQON_LOG_LEVEL_INFO,  fmt, ##__VA_ARGS__)
#define FERQON_LOG_ERROR(fmt, ...) FERQON_LOG_IMPL(FERQON_LOG_LEVEL_OFF,   fmt, ##__VA_ARGS__)

#endif /* FERQON_LOG_H */
