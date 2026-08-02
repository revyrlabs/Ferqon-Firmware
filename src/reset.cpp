/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#include "dispatcher.h"
#include "ferqon_hal.h"

static bool reset_handler(uint8_t seq, uint8_t cmd_id,
                          const uint8_t *params, uint8_t param_len,
                          uint8_t *response, uint8_t *response_len,
                          bool *already_responded) {
    (void)params; (void)param_len; (void)response;
    if (cmd_id != FERQON_CMD_RESET) return false;

    /* Respond BEFORE resetting so the host sees a clean DONE. */
    ferqon_send_done(seq, cmd_id, NULL, 0);
    *already_responded = true;
    *response_len = 0;

    ferqon_hal_delay_ms(100);
    ferqon_hal_system_reset();
    return true;
}

extern "C" const ferqon_driver_t reset_driver = {
    .name = "reset",
    .id = FERQON_CMD_RESET,
    .cmd_mask = (uint64_t)1 << FERQON_CMD_RESET,
    .handle = reset_handler,
};
FERQON_REGISTER_DRIVER(reset);
