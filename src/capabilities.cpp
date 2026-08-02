/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#include "dispatcher.h"
#include "platform_caps.h"
#include <stdio.h>

/* Return a small capabilities JSON derived from generated platform_caps.h. */
static bool capabilities_handler(uint8_t seq, uint8_t cmd_id,
                                 const uint8_t *params, uint8_t param_len,
                                 uint8_t *response, uint8_t *response_len,
                                 bool *already_responded) {
    (void)seq; (void)params; (void)param_len; (void)already_responded;
    if (cmd_id != FERQON_CMD_CAPABILITIES) return false;

    int n = snprintf((char*)response, FERQON_MAX_PAYLOAD_BYTES,
                     "{\"mcu\":\"%s\",\"device_name\":\"%s\"}",
                     FERQON_MCU_FAMILY, FERQON_BOARD_NAME);
    if (n < 0) n = 0;
    if (n > FERQON_MAX_PAYLOAD_BYTES - 1) n = FERQON_MAX_PAYLOAD_BYTES - 1;
    *response_len = (uint8_t)n;
    return true;
}

extern "C" const ferqon_driver_t capabilities_driver = {
    .name = "capabilities",
    .id = FERQON_CMD_CAPABILITIES,
    .handle = capabilities_handler,
};
FERQON_REGISTER_DRIVER(capabilities);
