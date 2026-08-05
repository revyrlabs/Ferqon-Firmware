/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#include "dispatcher.h"
#include "ferqon_helpers.h"
#include "ferqon_log.h"

static bool debug_handler(uint8_t seq, uint8_t cmd_id,
                         const uint8_t *params, uint8_t param_len,
                         uint8_t *response, uint8_t *response_len,
                         bool *already_responded) {
    if (cmd_id != FERQON_CMD_SET_DEBUG_LEVEL) return false;

    if (param_len < 1) {
        REPLY_INVALID_PARAMS(seq, cmd_id);
    }

    uint8_t level = params[0];
    if (level > FERQON_LOG_LEVEL_VERBOSE) {
        level = FERQON_LOG_LEVEL_VERBOSE;
    }

    g_debug_level = level;
    // Unconditional log to verify MCU can send logs
    ferqon_send_log("DEBUG_LEVEL_SET");
    response[0] = level;
    *response_len = 1;
    return true;
}

FERQON_DEFINE_DRIVER(debug, FERQON_CMD_SET_DEBUG_LEVEL, FERQON_DRIVER_CMD_MASK_DEBUG, debug_handler);
