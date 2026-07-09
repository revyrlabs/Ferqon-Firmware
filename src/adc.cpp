/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs */
#include "dispatcher.h"
#include "ferqon_commands.h"
#include "protocol.h"
#include "ferqon_log.h"
#include "board_config.h"
#include <Arduino.h>

static bool adc_read_handler(uint8_t seq, uint8_t cmd_id,
                            const uint8_t *params, uint8_t param_len,
                            uint8_t *response, uint8_t *response_len,
                            bool *already_responded) {
    /* Payload: channel (u8) */
    if (param_len != 1) {
        ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                        false, 0, (const uint8_t *)"invalid param length", 18);
        *already_responded = true;
        return true;
    }

    uint8_t channel = params[0];
    if (channel > FERQON_ADC_CHANNEL_MAX) {
        ferqon_send_error(seq, cmd_id, FERQON_ERR_UNSUPPORTED_PIN, FERQON_ECAT_COMMAND,
                        false, channel, NULL, 0);
        *already_responded = true;
        return true;
    }

    /* Read ADC value and convert to millivolts */
    /* Use board-specific ADC base pin and reference voltage */
    int raw = analogRead(FERQON_ADC_PIN(channel));
    uint16_t mv = (uint16_t)((raw * FERQON_ADC_VREF_MV) / ((1 << FERQON_ADC_RESOLUTION) - 1));

    /* Return millivolts as u16_le */
    response[0] = (mv >> 8) & 0xFF;
    response[1] = mv & 0xFF;
    *response_len = 2;
    return true;
}

static bool adc_expect_handler(uint8_t seq, uint8_t cmd_id,
                              const uint8_t *params, uint8_t param_len,
                              uint8_t *response, uint8_t *response_len,
                              bool *already_responded) {
    /* Payload format: timeout_ms (u16_le) + channel (u8) + min_mv (u16_le) + max_mv (u16_le) */
    if (param_len != 7) {
        ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                        false, 0, (const uint8_t *)"invalid param length", 18);
        *already_responded = true;
        return true;
    }

    uint16_t timeout_ms = (uint16_t)((params[0] << 8) | params[1]);
    uint8_t channel = params[2];
    uint16_t min_mv = (uint16_t)((params[3] << 8) | params[4]);
    uint16_t max_mv = (uint16_t)((params[5] << 8) | params[6]);

    if (channel > FERQON_ADC_CHANNEL_MAX) {
        ferqon_send_error(seq, cmd_id, FERQON_ERR_UNSUPPORTED_PIN, FERQON_ECAT_COMMAND,
                        false, channel, NULL, 0);
        *already_responded = true;
        return true;
    }

    /* Wait for ADC to be within range with timeout */
    unsigned long start = millis();
    while ((millis() - start) < timeout_ms) {
        int raw = analogRead(FERQON_ADC_PIN(channel));
        uint16_t mv = (uint16_t)((raw * FERQON_ADC_VREF_MV) / ((1 << FERQON_ADC_RESOLUTION) - 1));

        if (mv >= min_mv && mv <= max_mv) {
            response[0] = 1; /* Success */
            *response_len = 1;
            return true;
        }

        delay(10); /* Sample every 10ms */
    }

    /* Timeout */
    response[0] = 0; /* Failed */
    *response_len = 1;
    return true;
}

static bool adc_handler(uint8_t seq, uint8_t cmd_id,
                       const uint8_t *params, uint8_t param_len,
                       uint8_t *response, uint8_t *response_len,
                       bool *already_responded) {
    switch (cmd_id) {
        case FERQON_CMD_ADC_READ:
            return adc_read_handler(seq, cmd_id, params, param_len, response, response_len, already_responded);
        case FERQON_CMD_ADC_EXPECT:
            *response_len = 0;
            return adc_expect_handler(seq, cmd_id, params, param_len, response, response_len, already_responded);
        default:
            return false;
    }
}

extern "C" const ferqon_driver_t adc_driver = {
    .name = "adc",
    .id = FERQON_CMD_ADC_READ,
    .handle = adc_handler,
};
