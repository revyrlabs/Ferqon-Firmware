#include "dispatcher.h"
#include "ferqon_commands.h"
#include "protocol.h"
#include "ferqon_log.h"
#include "board_config.h"
#include <Arduino.h>

static bool pulse_measure_handler(uint8_t seq, uint8_t cmd_id,
                                  const uint8_t *params, uint8_t param_len,
                                  uint8_t *response, uint8_t *response_len,
                                  bool *already_responded) {
    /* Payload format: timeout_ms (u16_le) + pin (u8) + min_us (u32_le) + max_us (u32_le) */
    if (param_len != 11) {
        ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                        false, 0, (const uint8_t *)"invalid param length", 18);
        *already_responded = true;
        return true;
    }

    uint16_t timeout_ms = (uint16_t)((params[0] << 8) | params[1]);
    uint8_t pin = params[2];
    uint32_t min_us = (uint32_t)((params[3] << 24) | (params[4] << 16) | (params[5] << 8) | params[6]);
    uint32_t max_us = (uint32_t)((params[7] << 24) | (params[8] << 16) | (params[9] << 8) | params[10]);

    if (pin > FERQON_PIN_MAX) {
        ferqon_send_error(seq, cmd_id, FERQON_ERR_UNSUPPORTED_PIN, FERQON_ECAT_COMMAND,
                        false, pin, NULL, 0);
        *already_responded = true;
        return true;
    }

    /* Measure pulse width using pulseIn */
    /* pulseIn(pin, state, timeout) - timeout is in microseconds */
    unsigned long pulse_us = pulseIn(pin, HIGH, timeout_ms * 1000);

    if (pulse_us == 0) {
        /* Timeout or no pulse */
        response[0] = 0; /* Failed */
        *response_len = 1;
        return true;
    }

    /* Check if pulse is within expected range */
    if (pulse_us >= min_us && pulse_us <= max_us) {
        /* Return pulse duration in microseconds as u32_le */
        response[0] = (pulse_us >> 24) & 0xFF;
        response[1] = (pulse_us >> 16) & 0xFF;
        response[2] = (pulse_us >> 8) & 0xFF;
        response[3] = pulse_us & 0xFF;
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
    .handle = pulse_handler,
};
