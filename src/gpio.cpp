/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#include "dispatcher.h"
#include "board_config.h"
#include <Arduino.h>

static bool pin_mode_call(uint8_t seq, const uint8_t *params, uint8_t param_len,
                          bool *already_responded) {
    if (param_len != 2) {
        ferqon_send_error(seq, FERQON_CMD_PIN_MODE,
                        FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND, false, 0, NULL, 0);
        *already_responded = true;
        return true;
    }
    uint8_t pin = params[0], mode = params[1];

    if (pin > FERQON_PIN_MAX) {
        uint8_t detail[1] = { pin };
        ferqon_send_error(seq, FERQON_CMD_PIN_MODE,
                        FERQON_ERR_UNSUPPORTED_PIN, FERQON_ECAT_COMMAND, false,
                        /*ctx=*/pin, detail, 1);
        *already_responded = true;
        return true;
    }

    int arduino_mode;
    switch (mode) {
        case FERQON_GPIO_INPUT:          arduino_mode = INPUT;          break;
        case FERQON_GPIO_OUTPUT:         arduino_mode = OUTPUT;         break;
        case FERQON_GPIO_INPUT_PULLUP:   arduino_mode = INPUT_PULLUP;   break;
        case FERQON_GPIO_INPUT_PULLDOWN: arduino_mode = INPUT_PULLDOWN; break;
        default: {
            uint8_t detail[2] = { pin, mode };
            ferqon_send_error(seq, FERQON_CMD_PIN_MODE,
                            FERQON_ERR_UNSUPPORTED_MODE, FERQON_ECAT_COMMAND, false,
                            /*ctx=*/mode, detail, 2);
            *already_responded = true;
            return true;
        }
    }

    pinMode(pin, arduino_mode);
    return true;  /* core will send DONE */
}

static bool gpio_read_call(uint8_t seq, const uint8_t *params, uint8_t param_len,
                           uint8_t *response, uint8_t *response_len,
                           bool *already_responded) {
    if (param_len != 1) {
        ferqon_send_error(seq, FERQON_CMD_GPIO_READ,
                        FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND, false, 0, NULL, 0);
        *already_responded = true;
        return true;
    }
    uint8_t pin = params[0];
    if (pin > FERQON_PIN_MAX) {
        uint8_t detail[1] = { pin };
        ferqon_send_error(seq, FERQON_CMD_GPIO_READ,
                        FERQON_ERR_UNSUPPORTED_PIN, FERQON_ECAT_COMMAND, false, pin, detail, 1);
        *already_responded = true;
        return true;
    }
    response[0] = (uint8_t)digitalRead(pin);
    *response_len = 1;
    return true;
}

static bool gpio_write_call(uint8_t seq, const uint8_t *params, uint8_t param_len,
                            bool *already_responded) {
    if (param_len != 2) {
        ferqon_send_error(seq, FERQON_CMD_GPIO_WRITE,
                        FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND, false, 0, NULL, 0);
        *already_responded = true;
        return true;
    }
    uint8_t pin = params[0], value = params[1];
    if (pin > FERQON_PIN_MAX) {
        uint8_t detail[1] = { pin };
        ferqon_send_error(seq, FERQON_CMD_GPIO_WRITE,
                        FERQON_ERR_UNSUPPORTED_PIN, FERQON_ECAT_COMMAND, false, pin, detail, 1);
        *already_responded = true;
        return true;
    }
    digitalWrite(pin, value ? HIGH : LOW);
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
