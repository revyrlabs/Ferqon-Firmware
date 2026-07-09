/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs */
/* Application state machine and last-error tracking. */
#include "app_state.h"
#include "ferqon_log.h"
#include "protocol.h"

static uint8_t g_state = FERQON_STATE_APP_BOOT;
static uint8_t g_last_error = FERQON_ERR_OK;

void app_state_init(void) {
    g_state = FERQON_STATE_APP_READY;
    g_last_error = FERQON_ERR_OK;
}

void app_state_set(uint8_t state) {
    uint8_t old_state = g_state;
    g_state = state;
    if (g_debug_level >= FERQON_LOG_LEVEL_VERBOSE && old_state != state) {
        uint8_t payload[2] = {old_state, state};
        ferqon_send_log_bin(FERQON_LOG_SUBTYPE_STATE_CHANGE, payload, 2); /* STATE_CHANGE */
    }
}

uint8_t app_state_get(void) {
    return g_state;
}

void app_state_set_last_error(uint8_t code) {
    g_last_error = code;
}

uint8_t app_state_last_error(void) {
    return g_last_error;
}
