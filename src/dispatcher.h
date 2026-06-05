#ifndef FERQON_DISPATCHER_H
#define FERQON_DISPATCHER_H

#include "protocol.h"
#include <stdint.h>
#include <stdbool.h>

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
    uint8_t id;
    ferqon_driver_handler_t handle;
} ferqon_driver_t;

void ferqon_dispatcher_init(void);
void ferqon_register_driver(const ferqon_driver_t *driver);

/* Parse packet-type byte, route to a driver, emit the appropriate reply.
 * Returns true if the command was successfully dispatched (success or
 * structured error); false if no driver claimed it (INVALID_COMMAND
 * already sent). */
bool ferqon_dispatch_request(const ferqon_request_t *req);

#endif /* FERQON_DISPATCHER_H */
