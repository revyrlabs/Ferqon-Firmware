#include "dispatcher.h"
#include "protocol.h"

// Command IDs (from commands.json)
#define FERQON_CMD_ECHO 0x08

static bool echo_handler(uint8_t cmd_id, const uint8_t *params, uint8_t param_len,
                         uint8_t *response, uint8_t *response_len) {
    if (cmd_id != FERQON_CMD_ECHO) {
        return false;
    }

    // Echo the payload back
    if (param_len <= 256) {
        for (uint8_t i = 0; i < param_len; i++) {
            response[i] = params[i];
        }
        *response_len = param_len;
        return true;
    }

    return false;
}

const ferqon_driver_t echo_driver = {
    .name = "echo",
    .id = FERQON_CMD_ECHO,
    .handle = echo_handler
};
