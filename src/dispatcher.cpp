/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/* Command dispatcher: route parsed requests to the registered driver. */
#include "dispatcher.h"
#include "ferqon_helpers.h"
#include "ferqon_log.h"
#include <string.h>

/* cmd_mask is a uint64_t, so the command-id space must fit in 64 bits. */
static_assert(FERQON_MAX_COMMAND_ID <= 64, "cmd_mask cannot hold more than 64 command ids");

static ferqon_driver_t g_drivers[FERQON_MAX_DRIVERS];
static uint8_t g_driver_count = 0;
static uint8_t g_cmd_to_driver[FERQON_MAX_COMMAND_ID];

void ferqon_register_driver(const ferqon_driver_t *driver) {
    if (g_driver_count >= FERQON_MAX_DRIVERS) {
        FERQON_LOG_ERROR("driver table full; cannot register %s", driver->name);
        return;
    }

    /* First registration initializes the command->driver lookup table. */
    if (g_driver_count == 0) {
        memset(g_cmd_to_driver, FERQON_DRIVER_INDEX_INVALID, sizeof(g_cmd_to_driver));
    }

    /* Build the O(1) command routing table from the SSOT-derived mask. */
    uint64_t mask = driver->cmd_mask;
    for (uint8_t id = 0; id < FERQON_MAX_COMMAND_ID; id++) {
        if (mask & ((uint64_t)1 << id)) {
            if (g_cmd_to_driver[id] != FERQON_DRIVER_INDEX_INVALID) {
                FERQON_LOG_ERROR("command id %u already mapped to %s; cannot register %s",
                                 id, g_drivers[g_cmd_to_driver[id]].name, driver->name);
            } else {
                g_cmd_to_driver[id] = g_driver_count;
            }
        }
    }

    memcpy(&g_drivers[g_driver_count], driver, sizeof(ferqon_driver_t));
    g_driver_count++;
}

uint8_t ferqon_driver_count(void) {
    return g_driver_count;
}

const ferqon_driver_t *ferqon_driver_get(uint8_t index) {
    return (index < g_driver_count) ? &g_drivers[index] : NULL;
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

    if (req->cmd_id >= FERQON_MAX_COMMAND_ID) {
        ferqon_send_error(req->seq, req->cmd_id,
                        FERQON_ERR_INVALID_COMMAND, FERQON_ECAT_COMMAND,
                        /*retryable=*/false, /*ctx=*/0, NULL, 0);
        return false;
    }

    uint8_t idx = g_cmd_to_driver[req->cmd_id];
    if (idx == FERQON_DRIVER_INDEX_INVALID || idx >= g_driver_count) {
        if (g_debug_level >= FERQON_LOG_LEVEL_VERBOSE) {
            uint8_t payload[2] = {req->seq, req->cmd_id};
            ferqon_send_log_bin(FERQON_LOG_SUBTYPE_DISPATCH_UNHANDLED, payload, 2); /* DISPATCH_UNHANDLED */
        }
        ferqon_send_error(req->seq, req->cmd_id,
                        FERQON_ERR_INVALID_COMMAND, FERQON_ECAT_COMMAND,
                        /*retryable=*/false, /*ctx=*/0, NULL, 0);
        return false;
    }

    bool handled = g_drivers[idx].handle(req->seq, req->cmd_id, args, args_len,
                            response, &response_len, &already_responded);
    if (handled) {
        if (g_debug_level >= FERQON_LOG_LEVEL_VERBOSE) {
            uint8_t payload[32];
            payload[0] = req->seq;
            payload[1] = req->cmd_id;
            const char *name = g_drivers[idx].name;
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

    /* A driver advertised this command id but did not handle it. Treat as
     * an internal error rather than silently scanning other drivers. */
    ferqon_send_error(req->seq, req->cmd_id,
                    FERQON_ERR_INTERNAL, FERQON_ECAT_INTERNAL,
                    /*retryable=*/false, /*ctx=*/0, NULL, 0);
    return false;
}
