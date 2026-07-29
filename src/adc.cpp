/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#include "dispatcher.h"
#include "ferqon_helpers.h"
#include "board_config.h"
#include <Arduino.h>

/* Convert a raw ADC sample to millivolts using board-specific reference
 * voltage and resolution. Centralised here so adc_read and adc_expect
 * cannot drift apart. */
static inline uint16_t adc_raw_to_mv(int raw) {
    return (uint16_t)((raw * FERQON_ADC_VREF_MV) /
                      ((1 << FERQON_ADC_RESOLUTION) - 1));
}

/* Validate an ADC channel and its backing pin. On failure, sends an
 * UNSUPPORTED_PIN error and returns true (rejected). On success returns
 * false and writes the resolved ADC pin to *out_pin. */
static bool adc_check_channel(uint8_t seq, uint8_t cmd_id, uint8_t channel,
                              uint8_t *out_pin, bool *already_responded) {
    if (channel > FERQON_ADC_CHANNEL_MAX) {
        REPLY_ERROR(seq, cmd_id, FERQON_ERR_UNSUPPORTED_PIN, FERQON_ECAT_COMMAND,
                    false, channel, NULL, 0);
    }
    uint8_t adc_pin = FERQON_ADC_PIN(channel);
    if (ferqon_cap_pin_is_reserved(adc_pin)) {
        REPLY_ERROR(seq, cmd_id, FERQON_ERR_UNSUPPORTED_PIN, FERQON_ECAT_COMMAND,
                    false, adc_pin, NULL, 0);
    }
    *out_pin = adc_pin;
    return false;  /* channel OK — caller proceeds */
}

static bool adc_read_handler(uint8_t seq, uint8_t cmd_id,
                            const uint8_t *params, uint8_t param_len,
                            uint8_t *response, uint8_t *response_len,
                            bool *already_responded) {
    /* Payload: channel (u8) */
    if (param_len != 1) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "invalid param length");
    }

    uint8_t channel = params[0];
    uint8_t adc_pin;
    if (adc_check_channel(seq, cmd_id, channel, &adc_pin, already_responded)) {
        return true;
    }

    uint16_t mv = adc_raw_to_mv(analogRead(adc_pin));
    wr_u16_le(response, mv);
    *response_len = 2;
    return true;
}

static bool adc_expect_handler(uint8_t seq, uint8_t cmd_id,
                              const uint8_t *params, uint8_t param_len,
                              uint8_t *response, uint8_t *response_len,
                              bool *already_responded) {
    /* Payload format: timeout_ms (u16 LE) + channel (u8) + min_mv (u16 LE) + max_mv (u16 LE) */
    if (param_len != 7) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "invalid param length");
    }

    uint16_t timeout_ms = rd_u16_le(params);
    uint8_t channel = params[2];
    uint16_t min_mv = rd_u16_le(params + 3);
    uint16_t max_mv = rd_u16_le(params + 5);

    uint8_t adc_pin;
    if (adc_check_channel(seq, cmd_id, channel, &adc_pin, already_responded)) {
        return true;
    }

    /* Wait for ADC to be within range with timeout.
     * BLOCKING: no other commands or heartbeats processed during this. */
    unsigned long start = millis();
    while ((millis() - start) < timeout_ms) {
        uint16_t mv = adc_raw_to_mv(analogRead(adc_pin));
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
