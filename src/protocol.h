/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#ifndef FERQON_PROTOCOL_H
#define FERQON_PROTOCOL_H

#include "ferqon_commands.h"
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* Parser state machine. A frame is:
 *   [START=0xAB] [SEQ] [CMD] [LEN] [payload...] [CRC_LO] [CRC_HI]
 */
typedef enum {
    FERQON_STATE_IDLE,
    FERQON_STATE_SEQ,
    FERQON_STATE_CMD,
    FERQON_STATE_LEN,
    FERQON_STATE_PAYLOAD,
    FERQON_STATE_CRC_LO,
    FERQON_STATE_CRC_HI
} ferqon_state_t;

typedef struct {
    ferqon_state_t state;
    uint8_t  seq;
    uint8_t  cmd_id;
    uint8_t  param_len;
    uint8_t  payload[FERQON_MAX_PAYLOAD_BYTES];
    uint8_t  payload_idx;
    uint16_t crc;           /* running CRC over SEQ..last payload byte */
    uint8_t  crc_lo;
    uint32_t last_byte_ms;
    uint32_t frame_start_ms;
    uint32_t inter_byte_timeout_ms;
    uint32_t frame_assembly_timeout_ms;
} ferqon_parser_t;

typedef struct {
    uint8_t seq;
    uint8_t cmd_id;
    const uint8_t *params;   /* first byte of payload is packet_type */
    uint8_t param_len;
} ferqon_request_t;

/* Wire-output function pointer — bytes go here.
 *
 * CONTRACT:
 * - The implementation must copy `data` before returning; the caller may
 *   reuse the underlying buffer immediately after this call.
 * - All protocol send functions are non-reentrant. The implementation must not
 *   call back into ferqon_send_*() from within this callback. */
typedef void (*ferqon_write_func_t)(const uint8_t *data, size_t len);
void ferqon_set_write_func(ferqon_write_func_t func);

/* CRC-16/CCITT-FALSE. */
uint16_t ferqon_crc16(const uint8_t *data, size_t len);

/* Parser lifecycle. */
void ferqon_parser_init(ferqon_parser_t *parser);
void ferqon_parser_reset(ferqon_parser_t *parser);

/* Feed one byte; on success fills `req` and returns true (exactly once per
 * complete, CRC-valid frame). */
bool ferqon_parser_feed(ferqon_parser_t *parser, uint8_t byte, ferqon_request_t *req);

/* Emit a framed response. `seq` should be echoed from the originating request. */
void ferqon_send_done(uint8_t seq, uint8_t cmd_id,
                    const uint8_t *body, uint8_t body_len);

void ferqon_send_ack(uint8_t seq, uint8_t cmd_id);

/* Structured error packet body: [code, category, retryable, ctx, detail...]. */
void ferqon_send_error(uint8_t seq, uint8_t cmd_id,
                     uint8_t code, uint8_t category, bool retryable,
                     uint8_t ctx, const uint8_t *detail, uint8_t detail_len);

/* Unsolicited push (seq=0). */
void ferqon_send_heartbeat(uint8_t state, uint32_t uptime_ms, uint8_t flags);
void ferqon_send_log(const char *msg);
void ferqon_send_log_bin(uint8_t subtype, const uint8_t *data, uint8_t data_len);

#endif /* FERQON_PROTOCOL_H */
