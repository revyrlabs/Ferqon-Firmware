#ifndef FERQON_LOG_H
#define FERQON_LOG_H

#include <Arduino.h>

/* Log levels */
#define FERQON_LOG_LEVEL_OFF    0
#define FERQON_LOG_LEVEL_INFO   1
#define FERQON_LOG_LEVEL_VERBOSE 2

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

/* Log macros - route through protocol framing when debug is enabled */
#define FERQON_LOG_DEBUG(msg) \
    do { \
        if (g_debug_level >= FERQON_LOG_LEVEL_VERBOSE) { \
            ferqon_send_log(msg); \
        } \
    } while (0)

#define FERQON_LOG_INFO(msg) \
    do { \
        if (g_debug_level >= FERQON_LOG_LEVEL_INFO) { \
            ferqon_send_log(msg); \
        } \
    } while (0)

#define FERQON_LOG_WARN(msg) \
    do { \
        if (g_debug_level >= FERQON_LOG_LEVEL_INFO) { \
            ferqon_send_log(msg); \
        } \
    } while (0)

#define FERQON_LOG_ERROR(msg) \
    do { \
        if (g_debug_level >= FERQON_LOG_LEVEL_OFF) { \
            ferqon_send_log(msg); \
        } \
    } while (0)

#endif /* FERQON_LOG_H */
