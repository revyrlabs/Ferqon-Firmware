/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#ifndef FERQON_DISPATCHER_H
#define FERQON_DISPATCHER_H

#include "protocol.h"
#include <stdint.h>
#include <stdbool.h>

#define FERQON_MAX_DRIVERS 16
#define FERQON_MAX_COMMAND_ID 64
#define FERQON_DRIVER_INDEX_INVALID 0xFF

/* A driver handler claims a command by returning true.
 *
 *   cmd_id, params, param_len  - the incoming request (packet-type byte
 *                                 already stripped, so `params` starts at
 *                                 the first argument byte).
 *   response, response_len      - [out] OK-body bytes to return. Handler
 *                                 sets *response_len <= FERQON_MAX_PAYLOAD_BYTES - 1
 *                                 (room for the DONE type byte prepended by the
 *                                 core). Leave 0 for empty.
 *
 * A handler that wants to emit a structured error should call ferqon_send_error()
 * directly and return true (claimed, already responded). In that case the core
 * will NOT emit a DONE frame.
 */
typedef bool (*ferqon_driver_handler_t)(uint8_t seq, uint8_t cmd_id,
                                       const uint8_t *params, uint8_t param_len,
                                       uint8_t *response, uint8_t *response_len,
                                       bool *already_responded);

typedef struct {
    const char *name;
    uint8_t id;              /* Primary command id (reported in driver_info). */
    uint64_t cmd_mask;       /* Bit mask of all command ids this driver handles. */
    ferqon_driver_handler_t handle;
} ferqon_driver_t;

void ferqon_register_driver(const ferqon_driver_t *driver);

/* Read-only accessors for the driver registry. These keep the internal
 * driver table encapsulated while letting device_info / driver_info enumerate
 * registered drivers without reaching into g_drivers directly. */
uint8_t ferqon_driver_count(void);
const ferqon_driver_t *ferqon_driver_get(uint8_t index);

/* Parse packet-type byte, route to a driver, emit the appropriate reply.
 * Returns true if the command was successfully dispatched (success or
 * structured error); false if no driver claimed it (INVALID_COMMAND
 * already sent). */
bool ferqon_dispatch_request(const ferqon_request_t *req);

#ifdef __cplusplus
/* Self-registration hook. Place FERQON_REGISTER_DRIVER(name) once at the end
 * of a driver .cpp file after the `extern "C" const ferqon_driver_t name_driver`
 * definition. A global dynamic initializer registers the driver before main()
 * / setup() runs, so no manual driver table is needed. */
#define FERQON_DRIVER_REGISTER_VAR(name) _ferqon_driver_reg_##name
#define FERQON_REGISTER_DRIVER(name) \
    namespace { \
        __attribute__((used)) static bool FERQON_DRIVER_REGISTER_VAR(name) = \
            (ferqon_register_driver(&name##_driver), true); \
    }
#endif /* __cplusplus */

#endif /* FERQON_DISPATCHER_H */
