/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs */
#include "dispatcher.h"

static bool ping_handler(uint8_t seq, uint8_t cmd_id,
                         const uint8_t *params, uint8_t param_len,
                         uint8_t *response, uint8_t *response_len,
                         bool *already_responded) {
    (void)seq; (void)params; (void)param_len; (void)response; (void)already_responded;
    if (cmd_id != FERQON_CMD_PING) return false;
    *response_len = 0;
    return true;
}

extern "C" const ferqon_driver_t ping_driver = {
    .name = "ping",
    .id = FERQON_CMD_PING,
    .handle = ping_handler,
};
