/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#ifndef FERQON_LOG_H
#define FERQON_LOG_H

#include <stdint.h>
#include <stdarg.h>

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

/* Format and send a log through the protocol framing if level is enabled. */
void ferqon_vlog(uint8_t level, const char *fmt, ...);

/* Raw boot-time log before the protocol is initialized. */
void ferqon_log_raw(const char *msg);

#define FERQON_LOG_RAW(msg)      ferqon_log_raw(msg)
#define FERQON_LOG_DEBUG(...)    ferqon_vlog(FERQON_LOG_LEVEL_DEBUG, __VA_ARGS__)
#define FERQON_LOG_INFO(...)     ferqon_vlog(FERQON_LOG_LEVEL_INFO,  __VA_ARGS__)
#define FERQON_LOG_WARN(...)     ferqon_vlog(FERQON_LOG_LEVEL_INFO,  __VA_ARGS__)
#define FERQON_LOG_ERROR(...)    ferqon_vlog(FERQON_LOG_LEVEL_OFF,   __VA_ARGS__)

#endif /* FERQON_LOG_H */
