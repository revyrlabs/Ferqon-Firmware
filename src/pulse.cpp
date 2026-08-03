/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#include "dispatcher.h"
#include "ferqon_helpers.h"
#include "ferqon_hal.h"

static bool pulse_measure_handler(uint8_t seq, uint8_t cmd_id,
                                  const uint8_t *params, uint8_t param_len,
                                  uint8_t *response, uint8_t *response_len,
                                  bool *already_responded) {
    /* Payload format: timeout_ms (u16 LE) + pin (u8) + min_us (u32 LE) + max_us (u32 LE) */
    if (param_len != 11) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "invalid param length");
    }

    uint16_t timeout_ms = rd_u16_le(params);
    uint8_t pin = params[2];
    uint32_t min_us = rd_u32_le(params + 3);
    uint32_t max_us = rd_u32_le(params + 7);

    if (ferqon_check_pin(seq, cmd_id, pin, already_responded)) {
        return true;
    }

    /* Measure pulse width using pulseIn.
     * BLOCKING: no other commands or heartbeats processed during this. */
    /* pulseIn(pin, state, timeout) - timeout is in microseconds */
    unsigned long pulse_us = ferqon_hal_pulse_in(pin, 1, timeout_ms * 1000);

    if (pulse_us == 0) {
        /* Timeout or no pulse */
        response[0] = 0; /* Failed */
        *response_len = 1;
        return true;
    }

    /* Check if pulse is within expected range */
    if (pulse_us >= min_us && pulse_us <= max_us) {
        /* Return pulse duration in microseconds as u32 little-endian */
        wr_u32_le(response, (uint32_t)pulse_us);
        *response_len = 4;
        return true;
    }

    /* Pulse out of range */
    response[0] = 0; /* Failed */
    *response_len = 1;
    return true;
}

static bool pulse_handler(uint8_t seq, uint8_t cmd_id,
                        const uint8_t *params, uint8_t param_len,
                        uint8_t *response, uint8_t *response_len,
                        bool *already_responded) {
    switch (cmd_id) {
        case FERQON_CMD_PULSE_MEASURE:
            return pulse_measure_handler(seq, cmd_id, params, param_len, response, response_len, already_responded);
        default:
            return false;
    }
}

extern "C" const ferqon_driver_t pulse_driver = {
    .name = "pulse",
    .id = FERQON_CMD_PULSE_MEASURE,
    .cmd_mask = FERQON_DRIVER_CMD_MASK_PULSE,
    .handle = pulse_handler,
};
FERQON_REGISTER_DRIVER(pulse);
