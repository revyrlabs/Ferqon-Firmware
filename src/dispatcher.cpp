/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/* Command dispatcher: route parsed requests to the registered driver. */
#include "dispatcher.h"
#include "ferqon_helpers.h"
#include "ferqon_log.h"
#include <string.h>

ferqon_driver_t g_drivers[FERQON_MAX_DRIVERS];
uint8_t g_driver_count = 0;

void ferqon_register_driver(const ferqon_driver_t *driver) {
    if (g_driver_count >= FERQON_MAX_DRIVERS) {
        FERQON_LOG_ERROR("driver table full; cannot register %s", driver->name);
        return;
    }
    memcpy(&g_drivers[g_driver_count], driver, sizeof(ferqon_driver_t));
    g_driver_count++;
}

bool ferqon_dispatch_request(const ferqon_request_t *req) {
    /* Every inbound frame must carry a REQUEST packet-type byte; strip it.
     * The two info commands (DRIVER_INFO, DEVICE_INFO) are exempt: they
     * take no arguments and may arrive with a zero-length payload. */
    bool needs_pkt_request = (req->cmd_id != FERQON_CMD_DRIVER_INFO &&
                              req->cmd_id != FERQON_CMD_DEVICE_INFO);

    if (needs_pkt_request && (req->param_len < 1 || req->params[0] != FERQON_PKT_REQUEST)) {
        ferqon_send_error(req->seq, req->cmd_id,
                        FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_PROTOCOL,
                        /*retryable=*/false, /*ctx=*/0, NULL, 0);
        return false;
    }

    /* For info commands, args is the raw params (no PKT_REQUEST to strip)
     * and must be empty. For all other commands, args starts after the
     * PKT_REQUEST byte. */
    const uint8_t *args;
    uint8_t args_len;
    if (!needs_pkt_request) {
        args = req->params;
        args_len = req->param_len;
        if (args_len > 0) {
            ferqon_send_error(req->seq, req->cmd_id,
                            FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_PROTOCOL,
                            /*retryable=*/false, /*ctx=*/0, NULL, 0);
            return false;
        }
    } else {
        args = req->params + 1;
        args_len = (uint8_t)(req->param_len - 1);
    }

    uint8_t response[FERQON_MAX_PAYLOAD_BYTES];
    uint8_t response_len = 0;
    bool already_responded = false;

    if (req->cmd_id >= 64) {
        ferqon_send_error(req->seq, req->cmd_id,
                        FERQON_ERR_INVALID_COMMAND, FERQON_ECAT_COMMAND,
                        /*retryable=*/false, /*ctx=*/0, NULL, 0);
        return false;
    }

    for (uint8_t i = 0; i < g_driver_count; i++) {
        if ((g_drivers[i].cmd_mask & ((uint64_t)1 << req->cmd_id)) == 0) {
            continue;
        }

        bool handled = g_drivers[i].handle(req->seq, req->cmd_id, args, args_len,
                                response, &response_len, &already_responded);
        if (handled) {
            if (g_debug_level >= FERQON_LOG_LEVEL_VERBOSE) {
                uint8_t payload[32];
                payload[0] = req->seq;
                payload[1] = req->cmd_id;
                const char *name = g_drivers[i].name;
                const uint8_t max_name_len = (uint8_t)(sizeof(payload) - 3);
                uint8_t name_len = 0;
                while (name[name_len] && name_len < max_name_len) {
                    payload[2 + name_len] = name[name_len];
                    name_len++;
                }
                payload[2 + name_len] = 0; // null terminator
                ferqon_send_log_bin(FERQON_LOG_SUBTYPE_DISPATCH_ROUTED, payload, 3 + name_len); /* DISPATCH_ROUTED */
            }
            if (!already_responded) {
                ferqon_send_done(req->seq, req->cmd_id, response, response_len);
            }
            return true;
        }
    }

    if (g_debug_level >= FERQON_LOG_LEVEL_VERBOSE) {
        uint8_t payload[2] = {req->seq, req->cmd_id};
        ferqon_send_log_bin(FERQON_LOG_SUBTYPE_DISPATCH_UNHANDLED, payload, 2); /* DISPATCH_UNHANDLED */
    }
    ferqon_send_error(req->seq, req->cmd_id,
                    FERQON_ERR_INVALID_COMMAND, FERQON_ECAT_COMMAND,
                    /*retryable=*/false, /*ctx=*/0, NULL, 0);
    return false;
}
