#include "dispatcher.h"
#include "protocol.h"

// Command IDs (from commands.json)
#define FERQON_CMD_PING 0x09

static bool ping_handler(uint8_t cmd_id, const uint8_t *params, uint8_t param_len,
                         uint8_t *response, uint8_t *response_len) {
    if (cmd_id != FERQON_CMD_PING) {
        return false;
    }

    // PING has no parameters and no response data
    *response_len = 0;
    return true;
}

const ferqon_driver_t ping_driver = {
    .name = "ping",
    .id = FERQON_CMD_PING,
    .handle = ping_handler
};
