/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/**
 * ferqon_helpers.h
 * ----------------
 * Shared inline helpers and macros used across driver handlers.
 *
 * These collapse the repetitive error-reply / pin-validation / little-endian
 * encode-decode boilerplate that was duplicated across gpio.cpp, adc.cpp,
 * pulse.cpp, uart.cpp, driver_call.cpp, and dispatcher.cpp.
 */
#ifndef FERQON_HELPERS_H
#define FERQON_HELPERS_H

#include "protocol.h"
#include "dispatcher.h"
#include "ferqon_commands.h"
#include "pin_macros.h"
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

/* --------------------------------------------------------------- Errors */

/* Reply with a structured error frame, mark the request as already
 * responded, and return true from the current handler.
 *
 * Before (4 lines, repeated ~50 times):
 *   ferqon_send_error(seq, cmd, FERQON_ERR_X, FERQON_ECAT_Y, false, 0, NULL, 0);
 *   *already_responded = true;
 *   return true;
 *
 * After (1 line):
 *   REPLY_ERROR(seq, cmd, FERQON_ERR_X, FERQON_ECAT_Y, false, 0, NULL, 0);
 */
#define REPLY_ERROR(seq, cmd, code, cat, retryable, ctx, detail, detail_len) \
    do { \
        ferqon_send_error((seq), (cmd), (code), (cat), (retryable), (ctx), \
                          (detail), (detail_len)); \
        *(already_responded) = true; \
        return true; \
    } while (0)

/* Reply with an error whose detail is a string literal. Avoids the
 * error-prone manual byte-count that was passed alongside every
 * string detail in driver_call.cpp (e.g. "payload too short", 17).
 *
 *   REPLY_ERROR_STR(seq, cmd, code, cat, retry, ctx, "payload too short");
 */
#define REPLY_ERROR_STR(seq, cmd, code, cat, retryable, ctx, str) \
    REPLY_ERROR((seq), (cmd), (code), (cat), (retryable), (ctx), \
                (const uint8_t *)(str), (uint8_t)(strlen(str)))

/* Reply with an invalid-params error (the most common case). */
#define REPLY_INVALID_PARAMS(seq, cmd) \
    REPLY_ERROR((seq), (cmd), FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND, \
                false, 0, NULL, 0)

/* Reply with an invalid-params error and a string detail. */
#define REPLY_INVALID_PARAMS_STR(seq, cmd, str) \
    REPLY_ERROR_STR((seq), (cmd), FERQON_ERR_INVALID_PARAMS, \
                    FERQON_ECAT_COMMAND, false, 0, (str))

/* --------------------------------------------------------- Pin validation */

/* Validate a GPIO pin for a command. On failure, sends an
 * UNSUPPORTED_PIN error, sets already_responded, and returns true
 * (claiming the command). On success, returns false and the caller
 * continues.
 *
 * Usage:
 *   if (ferqon_check_pin(seq, cmd_id, pin, already_responded)) return true;
 *
 * Returns true if the pin was REJECTED (error already sent).
 * Returns false if the pin is OK (caller proceeds).
 */
static inline bool ferqon_check_pin(uint8_t seq, uint8_t cmd_id, uint8_t pin,
                                    bool *already_responded) {
    if (!ferqon_cap_pin_is_valid(pin) || ferqon_cap_pin_is_reserved(pin)) {
        REPLY_ERROR(seq, cmd_id, FERQON_ERR_UNSUPPORTED_PIN, FERQON_ECAT_COMMAND,
                    false, pin, NULL, 0);
    }
    return false;
}

/* ------------------------------------------------ Little-endian primitives */

/* Read a little-endian u16 from a byte pointer. */
static inline uint16_t rd_u16_le(const uint8_t *p) {
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

/* Read a little-endian u32 from a byte pointer. */
static inline uint32_t rd_u32_le(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

/* Write a little-endian u16 into a byte pointer. */
static inline void wr_u16_le(uint8_t *p, uint16_t v) {
    p[0] = (uint8_t)(v & 0xFF);
    p[1] = (uint8_t)((v >> 8) & 0xFF);
}

/* Write a little-endian u32 into a byte pointer. */
static inline void wr_u32_le(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)(v & 0xFF);
    p[1] = (uint8_t)((v >> 8) & 0xFF);
    p[2] = (uint8_t)((v >> 16) & 0xFF);
    p[3] = (uint8_t)((v >> 24) & 0xFF);
}

#endif /* FERQON_HELPERS_H */
