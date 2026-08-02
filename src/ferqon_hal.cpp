/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/* Shared HAL state and the protocol wire-output sink. */
#include "ferqon_hal.h"
#include "protocol.h"

const ferqon_hal_t *g_ferqon_hal = NULL;

void ferqon_hal_init(const ferqon_hal_t *hal) {
    g_ferqon_hal = hal;
    ferqon_set_write_func(ferqon_hal_protocol_write);
}

bool ferqon_hal_is_ready(void) {
    return g_ferqon_hal != NULL;
}

void ferqon_hal_protocol_write(const uint8_t *data, size_t len) {
    if (g_ferqon_hal && g_ferqon_hal->serial_write) {
        g_ferqon_hal->serial_write(data, len);
    }
}
