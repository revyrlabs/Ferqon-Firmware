/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#ifndef FERQON_APP_STATE_H
#define FERQON_APP_STATE_H

#include "ferqon_commands.h"
#include <stdint.h>

/* Minimal app-level state machine exposed via GET_STATE and HEARTBEAT. */

void app_state_set(uint8_t state);
uint8_t app_state_get(void);

#endif /* FERQON_APP_STATE_H */
