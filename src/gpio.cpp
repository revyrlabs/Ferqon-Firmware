/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#include "dispatcher.h"
#include "ferqon_helpers.h"
#include "board_config.h"
#include "ferqon_hal.h"

static bool pin_mode_call(uint8_t seq, const uint8_t *params, uint8_t param_len,
                          bool *already_responded) {
    if (param_len != 2) {
        REPLY_INVALID_PARAMS(seq, FERQON_CMD_PIN_MODE);
    }
    uint8_t pin = params[0], mode = params[1];

    if (ferqon_check_pin(seq, FERQON_CMD_PIN_MODE, pin, already_responded)) {
        return true;
    }

    switch (mode) {
        case FERQON_GPIO_INPUT:
        case FERQON_GPIO_OUTPUT:
        case FERQON_GPIO_INPUT_PULLUP:
        case FERQON_GPIO_INPUT_PULLDOWN:
            break;
        default: {
            uint8_t detail[2] = { pin, mode };
            REPLY_ERROR(seq, FERQON_CMD_PIN_MODE, FERQON_ERR_UNSUPPORTED_MODE,
                        FERQON_ECAT_COMMAND, false, mode, detail, 2);
        }
    }

    ferqon_hal_gpio_set_mode(pin, mode);
    return true;  /* core will send DONE */
}

static bool gpio_read_call(uint8_t seq, const uint8_t *params, uint8_t param_len,
                           uint8_t *response, uint8_t *response_len,
                           bool *already_responded) {
    if (param_len != 1) {
        REPLY_INVALID_PARAMS(seq, FERQON_CMD_GPIO_READ);
    }
    uint8_t pin = params[0];
    if (ferqon_check_pin(seq, FERQON_CMD_GPIO_READ, pin, already_responded)) {
        return true;
    }
    response[0] = (uint8_t)ferqon_hal_gpio_read(pin);
    *response_len = 1;
    return true;
}

static bool gpio_write_call(uint8_t seq, const uint8_t *params, uint8_t param_len,
                            bool *already_responded) {
    if (param_len != 2) {
        REPLY_INVALID_PARAMS(seq, FERQON_CMD_GPIO_WRITE);
    }
    uint8_t pin = params[0], value = params[1];
    if (ferqon_check_pin(seq, FERQON_CMD_GPIO_WRITE, pin, already_responded)) {
        return true;
    }
    ferqon_hal_gpio_write(pin, value);
    return true;
}

static bool gpio_handler(uint8_t seq, uint8_t cmd_id,
                          const uint8_t *params, uint8_t param_len,
                          uint8_t *response, uint8_t *response_len,
                          bool *already_responded) {
    switch (cmd_id) {
        case FERQON_CMD_PIN_MODE:
            *response_len = 0;
            return pin_mode_call(seq, params, param_len, already_responded);
        case FERQON_CMD_GPIO_READ:
            return gpio_read_call(seq, params, param_len, response, response_len,
                                  already_responded);
        case FERQON_CMD_GPIO_WRITE:
            *response_len = 0;
            return gpio_write_call(seq, params, param_len, already_responded);
        default:
            return false;
    }
}

extern "C" const ferqon_driver_t gpio_driver = {
    .name = "gpio",
    .id = FERQON_CMD_GPIO_READ,  /* primary id; handler also claims write/pin_mode */
    .handle = gpio_handler,
};
