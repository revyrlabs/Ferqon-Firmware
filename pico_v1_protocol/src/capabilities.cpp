#include "dispatcher.h"
#include "protocol.h"
#include <Arduino.h>

// Command IDs (from commands.json)
#define FERQON_CMD_CAPABILITIES 0x0C

// This is a placeholder - in the full implementation, this would return
// the minified capabilities.json as bytes
static bool capabilities_handler(uint8_t cmd_id, const uint8_t *params, uint8_t param_len,
                                 uint8_t *response, uint8_t *response_len) {
    if (cmd_id != FERQON_CMD_CAPABILITIES) {
        return false;
    }

    // Return a simple JSON string for now
    const char *caps_json = "{\"mcu\":\"rp2040\",\"device_name\":\"pico\"}";
    uint8_t caps_len = strlen(caps_json);

    memcpy(response, caps_json, caps_len);
    *response_len = caps_len;

    return true;
}

const ferqon_driver_t capabilities_driver = {
    .name = "capabilities",
    .id = FERQON_CMD_CAPABILITIES,
    .handle = capabilities_handler
};
