#include "dispatcher.h"
#include <string.h>

static bool echo_handler(uint8_t seq, uint8_t cmd_id,
                         const uint8_t *params, uint8_t param_len,
                         uint8_t *response, uint8_t *response_len,
                         bool *already_responded) {
    (void)seq; (void)already_responded;
    if (cmd_id != FERQON_CMD_ECHO) return false;

    /* Response body = echoed request body. DONE type byte is added by core, so
     * the max body we can echo is MAX_PAYLOAD - 1. */
    uint8_t n = param_len;
    if (n > FERQON_MAX_PAYLOAD_BYTES - 1) {
        n = FERQON_MAX_PAYLOAD_BYTES - 1;
    }
    if (n > 0) memcpy(response, params, n);
    *response_len = n;
    return true;
}

extern "C" const ferqon_driver_t echo_driver = {
    .name = "echo",
    .id = FERQON_CMD_ECHO,
    .handle = echo_handler,
};
