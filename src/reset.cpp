/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#include "dispatcher.h"
#include <Arduino.h>

static bool reset_handler(uint8_t seq, uint8_t cmd_id,
                          const uint8_t *params, uint8_t param_len,
                          uint8_t *response, uint8_t *response_len,
                          bool *already_responded) {
    (void)params; (void)param_len; (void)response;
    if (cmd_id != FERQON_CMD_RESET) return false;

    /* Respond BEFORE resetting so the host sees a clean DONE. */
    ferqon_send_done(seq, cmd_id, NULL, 0);
    *already_responded = true;
    *response_len = 0;

    delay(100);
#if defined(FERQON_BOARD_NATIVE)
    /* Native/host builds have no hardware to reset. */
    return true;
#elif defined(FERQON_BOARD_ESP32) || defined(FERQON_BOARD_ESP32S3)
    ESP.restart();
#elif defined(__arm__)
    /* Cortex-M system reset via AIRCR (VECTKEY + SYSRESETREQ). */
    volatile uint32_t *aircr = (volatile uint32_t *)0xE000ED0C;
    *aircr = 0x05FA0004;
    while (true) {}
#else
    NVIC_SystemReset();
#endif
    return true;
}

extern "C" const ferqon_driver_t reset_driver = {
    .name = "reset",
    .id = FERQON_CMD_RESET,
    .handle = reset_handler,
};
