#include "dispatcher.h"
#include <string.h>

/* Placeholder: a real build would return minified capabilities.json. */
static bool capabilities_handler(uint8_t seq, uint8_t cmd_id,
                                 const uint8_t *params, uint8_t param_len,
                                 uint8_t *response, uint8_t *response_len,
                                 bool *already_responded) {
    (void)seq; (void)params; (void)param_len; (void)already_responded;
    if (cmd_id != FERQON_CMD_CAPABILITIES) return false;

    const char *caps_json = "{\"mcu\":\"rp2040\",\"device_name\":\"pico\"}";
    uint8_t n = (uint8_t)strlen(caps_json);
    if (n > FERQON_MAX_PAYLOAD_BYTES - 1) n = FERQON_MAX_PAYLOAD_BYTES - 1;
    memcpy(response, caps_json, n);
    *response_len = n;
    return true;
}

const ferqon_driver_t capabilities_driver = {
    .name = "capabilities",
    .id = FERQON_CMD_CAPABILITIES,
    .handle = capabilities_handler,
};
