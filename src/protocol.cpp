/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/* Wire protocol framing, CRC, parsing, and response emission. */
#include "protocol.h"
#include "ferqon_helpers.h"
#include "ferqon_log.h"
#include "ferqon_hal.h"
#include <string.h>

/* Wire-output sink (set by ferqon_set_write_func). */
static ferqon_write_func_t g_write_func = NULL;

/* Single shared transmit buffer.  All public ferqon_send_*() functions are
 * non-reentrant by contract; the firmware is single-threaded and every
 * implementation of g_write_func copies the supplied bytes before returning. */
static uint8_t s_tx_frame[FERQON_MAX_PAYLOAD_BYTES + FERQON_FRAME_OVERHEAD];

void ferqon_set_write_func(ferqon_write_func_t func) {
    g_write_func = func;
}

/* -------------------------------------------------------------------- CRC */

/* Fold one byte into the running CRC-16/CCITT-FALSE. */
static inline void crc_update(uint16_t *crc, uint8_t byte) {
    uint16_t c = *crc;
    c ^= ((uint16_t)byte) << 8;
    for (uint8_t b = 0; b < 8; ++b) {
        if (c & 0x8000) c = (uint16_t)((c << 1) ^ FERQON_CRC_POLY);
        else            c = (uint16_t)(c << 1);
    }
    *crc = c;
}

uint16_t ferqon_crc16(const uint8_t *data, size_t len) {
    uint16_t crc = FERQON_CRC_INIT;
    for (size_t i = 0; i < len; ++i) {
        crc_update(&crc, data[i]);
    }
    return crc;
}

/* ------------------------------------------------------------------- Send */

static void write_all(const uint8_t *data, size_t len) {
    if (g_write_func) {
        g_write_func(data, len);
    }
}

/* Emit a complete frame. (prefix_len + body_len) is the payload length.
 * The type byte and any fixed header bytes live in prefix; variable data in body.
 * This lets callers build responses directly without a second scratch buffer. */
static void ferqon_send_frame(uint8_t seq, uint8_t cmd_id,
                            const uint8_t *prefix, uint8_t prefix_len,
                            const uint8_t *body, uint8_t body_len) {
    uint8_t payload_len = (uint8_t)(prefix_len + body_len);
    size_t pos = 0;
    s_tx_frame[pos++] = FERQON_START_BYTE;
    s_tx_frame[pos++] = seq;
    s_tx_frame[pos++] = cmd_id;
    s_tx_frame[pos++] = payload_len;
    if (prefix_len > 0 && prefix != NULL) {
        memcpy(&s_tx_frame[pos], prefix, prefix_len);
        pos += prefix_len;
    }
    if (body_len > 0 && body != NULL) {
        memcpy(&s_tx_frame[pos], body, body_len);
        pos += body_len;
    }

    uint16_t crc = ferqon_crc16(&s_tx_frame[1], pos - 1);
    s_tx_frame[pos++] = (uint8_t)(crc & 0xFF);
    s_tx_frame[pos++] = (uint8_t)((crc >> 8) & 0xFF);

    write_all(s_tx_frame, pos);
}

void ferqon_send_done(uint8_t seq, uint8_t cmd_id,
                    const uint8_t *body, uint8_t body_len) {
    uint8_t prefix = FERQON_PKT_DONE;
    if ((size_t)body_len + 1 > FERQON_MAX_PAYLOAD_BYTES) {
        /* Caller asked to return more than the wire can hold — truncate safely. */
        body_len = (uint8_t)(FERQON_MAX_PAYLOAD_BYTES - 1);
    }
    ferqon_send_frame(seq, cmd_id, &prefix, 1, body, body_len);
}

void ferqon_send_ack(uint8_t seq, uint8_t cmd_id) {
    uint8_t prefix = FERQON_PKT_ACK;
    ferqon_send_frame(seq, cmd_id, &prefix, 1, NULL, 0);
}

void ferqon_send_error(uint8_t seq, uint8_t cmd_id,
                     uint8_t code, uint8_t category, bool retryable,
                     uint8_t ctx, const uint8_t *detail, uint8_t detail_len) {
    /* [type][code][category][retryable][ctx][detail...]  -> 5 bytes prefix */
    uint8_t prefix[5] = {
        FERQON_PKT_ERROR, code, category,
        (uint8_t)(retryable ? 1 : 0), ctx
    };
    if ((size_t)detail_len + sizeof(prefix) > FERQON_MAX_PAYLOAD_BYTES) {
        detail_len = (uint8_t)(FERQON_MAX_PAYLOAD_BYTES - sizeof(prefix));
    }
    ferqon_send_frame(seq, cmd_id, prefix, sizeof(prefix), detail, detail_len);
}

void ferqon_send_heartbeat(uint8_t state, uint32_t uptime_ms, uint8_t flags) {
    uint8_t prefix[2] = {FERQON_PKT_HEARTBEAT, state};
    uint8_t body[5];
    wr_u32_le(body, uptime_ms);
    body[4] = flags;
    /* Heartbeats are unsolicited: seq=0, cmd_id mirrors heartbeat id space.
     * We use cmd_id=0 for "no command" on unsolicited frames. */
    ferqon_send_frame(FERQON_SEQ_UNSOLICITED, 0, prefix, sizeof(prefix), body, sizeof(body));
}

void ferqon_send_log(const char *msg) {
    if (msg == NULL) return;
    uint8_t prefix = FERQON_PKT_LOG;
    size_t len = strlen(msg);
    if (len > FERQON_MAX_PAYLOAD_BYTES - 1) {
        len = FERQON_MAX_PAYLOAD_BYTES - 1;
    }
    ferqon_send_frame(FERQON_SEQ_UNSOLICITED, 0, &prefix, 1, (const uint8_t *)msg, (uint8_t)len);
}

/* Send structured binary log with subtype. Payload: [PKT_LOG][subtype][data...] */
void ferqon_send_log_bin(uint8_t subtype, const uint8_t *data, uint8_t data_len) {
    uint8_t prefix[2] = {FERQON_PKT_LOG, subtype};
    if (data_len > FERQON_MAX_PAYLOAD_BYTES - sizeof(prefix)) {
        data_len = (uint8_t)(FERQON_MAX_PAYLOAD_BYTES - sizeof(prefix));
    }
    ferqon_send_frame(FERQON_SEQ_UNSOLICITED, 0, prefix, sizeof(prefix), data, data_len);
}

/* ---------------------------------------------------------------- Parser */

void ferqon_parser_init(ferqon_parser_t *parser) {
    ferqon_parser_reset(parser);
    parser->inter_byte_timeout_ms = FERQON_INTER_BYTE_TIMEOUT_MS;
    parser->frame_assembly_timeout_ms = FERQON_FRAME_ASSEMBLY_TIMEOUT_MS;
}

void ferqon_parser_reset(ferqon_parser_t *parser) {
    parser->state = FERQON_STATE_IDLE;
    parser->seq = 0;
    parser->cmd_id = 0;
    parser->param_len = 0;
    parser->payload_idx = 0;
    parser->crc = FERQON_CRC_INIT;
    parser->crc_lo = 0;
    parser->last_byte_ms = 0;
    parser->frame_start_ms = 0;
}

bool ferqon_parser_feed(ferqon_parser_t *parser, uint8_t byte, ferqon_request_t *req) {
    return ferqon_parser_feed_with_time(parser, byte, req, ferqon_hal_millis());
}

bool ferqon_parser_feed_with_time(ferqon_parser_t *parser, uint8_t byte,
                                  ferqon_request_t *req, uint32_t now) {
    /* Inter-byte timeout: gap too large inside a frame -> resync. */
    if (parser->state != FERQON_STATE_IDLE && parser->last_byte_ms > 0 &&
        (now - parser->last_byte_ms) > parser->inter_byte_timeout_ms) {
        if (g_debug_level >= FERQON_LOG_LEVEL_VERBOSE) {
            uint8_t payload[3] = {1, parser->state, (uint8_t)(now - parser->frame_start_ms)};
            ferqon_send_log_bin(FERQON_LOG_SUBTYPE_PARSER_RESET, payload, 3); /* PARSER_RESET: reason=timeout */
        }
        ferqon_parser_reset(parser);
    }

    /* Frame-assembly timeout: frame started too long ago, never completed. */
    if (parser->state != FERQON_STATE_IDLE && parser->frame_start_ms > 0 &&
        (now - parser->frame_start_ms) > parser->frame_assembly_timeout_ms) {
        if (g_debug_level >= FERQON_LOG_LEVEL_VERBOSE) {
            uint8_t payload[3] = {2, parser->state, (uint8_t)(now - parser->frame_start_ms)};
            ferqon_send_log_bin(FERQON_LOG_SUBTYPE_PARSER_RESET, payload, 3); /* PARSER_RESET: reason=assembly_timeout */
        }
        ferqon_parser_reset(parser);
    }

    parser->last_byte_ms = now;

    switch (parser->state) {
        case FERQON_STATE_IDLE:
            if (byte == FERQON_START_BYTE) {
                parser->state = FERQON_STATE_SEQ;
                parser->crc = FERQON_CRC_INIT;
                parser->payload_idx = 0;
                parser->frame_start_ms = now;
            }
            break;

        case FERQON_STATE_SEQ:
            parser->seq = byte;
            crc_update(&parser->crc, byte);
            parser->state = FERQON_STATE_CMD;
            break;

        case FERQON_STATE_CMD:
            parser->cmd_id = byte;
            crc_update(&parser->crc, byte);
            parser->state = FERQON_STATE_LEN;
            break;

        case FERQON_STATE_LEN:
            parser->param_len = byte;
            crc_update(&parser->crc, byte);
            parser->payload_idx = 0;
            if (parser->param_len == 0) {
                parser->state = FERQON_STATE_CRC_LO;
            } else {
                parser->state = FERQON_STATE_PAYLOAD;
            }
            break;

        case FERQON_STATE_PAYLOAD:
            parser->payload[parser->payload_idx++] = byte;
            crc_update(&parser->crc, byte);
            if (parser->payload_idx >= parser->param_len) {
                parser->state = FERQON_STATE_CRC_LO;
            }
            break;

        case FERQON_STATE_CRC_LO:
            parser->crc_lo = byte;
            parser->state = FERQON_STATE_CRC_HI;
            break;

        case FERQON_STATE_CRC_HI: {
            uint16_t recv = (uint16_t)parser->crc_lo | ((uint16_t)byte << 8);
            uint16_t computed_crc = parser->crc;
            bool ok = (recv == computed_crc);
            uint8_t seq = parser->seq;
            uint8_t cmd_id = parser->cmd_id;
            uint8_t plen = parser->param_len;
            uint8_t *pbuf = parser->payload;
            uint8_t saved_crc_lo = parser->crc_lo;
            ferqon_parser_reset(parser);
            if (ok) {
                if (g_debug_level >= FERQON_LOG_LEVEL_VERBOSE) {
                    uint8_t payload[10];
                    payload[0] = seq;
                    payload[1] = cmd_id;
                    payload[2] = plen;
                    const uint8_t max_copy = (uint8_t)(sizeof(payload) - 3);
                    uint8_t copy_len = (plen > max_copy) ? max_copy : plen;
                    for (uint8_t i = 0; i < copy_len; i++) {
                        payload[3 + i] = pbuf[i];
                    }
                    ferqon_send_log_bin(FERQON_LOG_SUBTYPE_FRAME_RECEIVED, payload, 3 + copy_len); /* FRAME_RECEIVED */
                }
                req->seq = seq;
                req->cmd_id = cmd_id;
                req->params = pbuf;
                req->param_len = plen;
                return true;
            }
            /* CRC fail: emit structured error so the host can distinguish
             * protocol corruption from command-level failure. We still know
             * the seq/cmd_id from the partial parse. */
            if (g_debug_level >= FERQON_LOG_LEVEL_VERBOSE) {
                uint8_t payload[6];
                payload[0] = (uint8_t)(computed_crc & 0xFF);
                payload[1] = (uint8_t)((computed_crc >> 8) & 0xFF);
                payload[2] = saved_crc_lo;
                payload[3] = byte;
                payload[4] = seq;
                payload[5] = cmd_id;
                ferqon_send_log_bin(FERQON_LOG_SUBTYPE_CRC_MISMATCH, payload, 6); /* CRC_MISMATCH */
            }
            ferqon_send_error(seq, cmd_id,
                            FERQON_ERR_CHECKSUM_FAIL, FERQON_ECAT_PROTOCOL,
                            /*retryable=*/true, /*ctx=*/0, NULL, 0);
            break;
        }
    }

    return false;
}
