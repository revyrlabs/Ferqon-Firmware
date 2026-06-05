#include "dispatcher.h"
#include "protocol.h"
#include <string.h>

#define FERQON_MAX_DRIVERS 16

static ferqon_driver_t g_drivers[FERQON_MAX_DRIVERS];
static uint8_t g_driver_count = 0;

void ferqon_register_driver(const ferqon_driver_t *driver) {
    if (g_driver_count < FERQON_MAX_DRIVERS) {
        memcpy(&g_drivers[g_driver_count], driver, sizeof(ferqon_driver_t));
        g_driver_count++;
    }
}

bool ferqon_dispatch_command(uint8_t cmd_id, const uint8_t *params, uint8_t param_len,
                          uint8_t *response, uint8_t *response_len) {
    for (uint8_t i = 0; i < g_driver_count; i++) {
        if (g_drivers[i].handle(cmd_id, params, param_len, response, response_len)) {
            return true;
        }
    }

    // Command not handled by any driver
    ferqon_send_error(1, NULL, 0);  // INVALID_COMMAND
    return false;
}

void ferqon_dispatcher_init(void) {
    g_driver_count = 0;
}
