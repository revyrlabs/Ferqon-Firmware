#include "dispatcher.h"
#include "protocol.h"
#include "board_config.h"
#include <Arduino.h>

// Command IDs (from commands.json)
#define FERQON_CMD_GPIO_READ 0x10
#define FERQON_CMD_GPIO_WRITE 0x11
#define FERQON_CMD_PIN_MODE 0x01

// Mode IDs (from pin_modes.json)
#define FERQON_MODE_GPIO_IN 0x00
#define FERQON_MODE_GPIO_OUT 0x01

// Error codes
#define FERQON_ERR_UNSUPPORTED_PIN 0x04
#define FERQON_ERR_UNSUPPORTED_MODE 0x03

static bool pin_mode_handler(uint8_t cmd_id, const uint8_t *params, uint8_t param_len,
                            uint8_t *response, uint8_t *response_len) {
    if (cmd_id != FERQON_CMD_PIN_MODE) {
        return false;
    }

    if (param_len != 2) {
        return false;
    }

    uint8_t pin = params[0];
    uint8_t mode = params[1];

    // Validate pin range
    if (pin > FERQON_PIN_MAX) {
        uint8_t detail[1] = {pin};
        ferqon_send_error(FERQON_ERR_UNSUPPORTED_PIN, detail, 1);
        return false;
    }

    // Validate and set mode
    if (mode == FERQON_MODE_GPIO_IN) {
        pinMode(pin, INPUT);
    } else if (mode == FERQON_MODE_GPIO_OUT) {
        pinMode(pin, OUTPUT);
    } else {
        uint8_t detail[2] = {pin, mode};
        ferqon_send_error(FERQON_ERR_UNSUPPORTED_MODE, detail, 2);
        return false;
    }

    *response_len = 0;
    return true;
}

static bool gpio_read_handler(uint8_t cmd_id, const uint8_t *params, uint8_t param_len,
                                uint8_t *response, uint8_t *response_len) {
    if (cmd_id != FERQON_CMD_GPIO_READ) {
        return false;
    }

    if (param_len != 1) {
        return false;
    }

    uint8_t pin = params[0];

    // Validate pin range
    if (pin > FERQON_PIN_MAX) {
        uint8_t detail[1] = {pin};
        ferqon_send_error(FERQON_ERR_UNSUPPORTED_PIN, detail, 1);
        return false;
    }

    response[0] = digitalRead(pin);
    *response_len = 1;
    return true;
}

static bool gpio_write_handler(uint8_t cmd_id, const uint8_t *params, uint8_t param_len,
                                 uint8_t *response, uint8_t *response_len) {
    if (cmd_id != FERQON_CMD_GPIO_WRITE) {
        return false;
    }

    if (param_len != 2) {
        return false;
    }

    uint8_t pin = params[0];
    uint8_t value = params[1];

    // Validate pin range
    if (pin > FERQON_PIN_MAX) {
        uint8_t detail[1] = {pin};
        ferqon_send_error(FERQON_ERR_UNSUPPORTED_PIN, detail, 1);
        return false;
    }

    digitalWrite(pin, value);
    *response_len = 0;
    return true;
}

static bool gpio_handler(uint8_t cmd_id, const uint8_t *params, uint8_t param_len,
                          uint8_t *response, uint8_t *response_len) {
    switch (cmd_id) {
        case FERQON_CMD_PIN_MODE:
            return pin_mode_handler(cmd_id, params, param_len, response, response_len);
        case FERQON_CMD_GPIO_READ:
            return gpio_read_handler(cmd_id, params, param_len, response, response_len);
        case FERQON_CMD_GPIO_WRITE:
            return gpio_write_handler(cmd_id, params, param_len, response, response_len);
        default:
            return false;
    }
}

const ferqon_driver_t gpio_driver = {
    .name = "gpio",
    .id = 0x10,
    .handle = gpio_handler
};
