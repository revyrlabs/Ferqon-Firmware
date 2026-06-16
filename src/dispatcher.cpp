#include "dispatcher.h"
#include "ferqon_log.h"
#include "protocol.h"
#include <string.h>

#define FERQON_MAX_DRIVERS 16

ferqon_driver_t g_drivers[FERQON_MAX_DRIVERS];
uint8_t g_driver_count = 0;

void ferqon_dispatcher_init(void) {
    g_driver_count = 0;
}

void ferqon_register_driver(const ferqon_driver_t *driver) {
    if (g_driver_count < FERQON_MAX_DRIVERS) {
        memcpy(&g_drivers[g_driver_count], driver, sizeof(ferqon_driver_t));
        g_driver_count++;
    }
}

bool ferqon_dispatch_request(const ferqon_request_t *req) {
    /* Every inbound frame must carry a REQUEST packet-type byte; strip it. */
    /* Allow zero-length payloads for info commands */
    bool needs_pkt_request = (req->cmd_id != FERQON_CMD_DRIVER_INFO && 
                              req->cmd_id != FERQON_CMD_DEVICE_INFO);
    
    if (needs_pkt_request && (req->param_len < 1 || req->params[0] != FERQON_PKT_REQUEST)) {
        ferqon_send_error(req->seq, req->cmd_id,
                        FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_PROTOCOL,
                        /*retryable=*/false, /*ctx=*/0, NULL, 0);
        return false;
    }

    const uint8_t *args = req->params + 1;
    uint8_t args_len = (uint8_t)(req->param_len - 1);
    
    /* For info commands with no PKT_REQUEST, use params directly as args */
    if (!needs_pkt_request) {
        args = req->params;
        args_len = req->param_len;
    }
    
    /* For info commands, ensure args_len is 0 (they don't take parameters) */
    if (!needs_pkt_request && args_len > 0) {
        ferqon_send_error(req->seq, req->cmd_id,
                        FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_PROTOCOL,
                        /*retryable=*/false, /*ctx=*/0, NULL, 0);
        return false;
    }

    uint8_t response[FERQON_MAX_PAYLOAD_BYTES];
    memset(response, 0, sizeof(response));  // Initialize to prevent garbage data
    uint8_t response_len = 0;
    bool already_responded = false;

    for (uint8_t i = 0; i < g_driver_count; i++) {
        bool handled = g_drivers[i].handle(req->seq, req->cmd_id, args, args_len,
                                response, &response_len, &already_responded);
        if (handled) {
            if (g_debug_level >= FERQON_LOG_LEVEL_VERBOSE) {
                uint8_t payload[32];
                payload[0] = req->seq;
                payload[1] = req->cmd_id;
                const char *name = g_drivers[i].name;
                uint8_t name_len = 0;
                while (name[name_len] && name_len < 29) {
                    payload[2 + name_len] = name[name_len];
                    name_len++;
                }
                payload[2 + name_len] = 0; // null terminator
                ferqon_send_log_bin(FERQON_LOG_SUBTYPE_DISPATCH_ROUTED, payload, 3 + name_len + 1); /* DISPATCH_ROUTED */
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
