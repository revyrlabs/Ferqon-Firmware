#include "dispatcher.h"
#include "protocol.h"
#include <Arduino.h>

// Command IDs (from commands.json)
#define FERQON_CMD_RESET 0x0A

static bool reset_handler(uint8_t cmd_id, const uint8_t *params, uint8_t param_len,
                          uint8_t *response, uint8_t *response_len) {
    if (cmd_id != FERQON_CMD_RESET) {
        return false;
    }

    // Send OK response before resetting
    ferqon_send_ok(NULL, 0);

    // Small delay to allow response to be sent
    delay(100);

    // Reset the MCU
    NVIC_SystemReset();

    return true;
}

const ferqon_driver_t reset_driver = {
    .name = "reset",
    .id = FERQON_CMD_RESET,
    .handle = reset_handler
};
