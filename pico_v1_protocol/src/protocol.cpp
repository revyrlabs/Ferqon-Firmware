#include "protocol.h"
#include <Arduino.h>

// Timeout for inter-byte timing (50ms)
#define FERQON_INTER_BYTE_TIMEOUT_MS 50

// Write function pointer
static ferqon_write_func_t g_write_func = NULL;

void ferqon_set_write_func(ferqon_write_func_t func) {
    g_write_func = func;
}

void ferqon_parser_init(ferqon_parser_t *parser, uint32_t timeout_ms) {
    parser->state = FERQON_STATE_IDLE;
    parser->cmd_id = 0;
    parser->param_len = 0;
    parser->payload_idx = 0;
    parser->checksum = 0;
    parser->last_byte_time = 0;
    parser->timeout_ms = timeout_ms;
}

void ferqon_parser_reset(ferqon_parser_t *parser) {
    parser->state = FERQON_STATE_IDLE;
    parser->cmd_id = 0;
    parser->param_len = 0;
    parser->payload_idx = 0;
    parser->checksum = 0;
}

uint8_t ferqon_calculate_checksum(const uint8_t *data, size_t len) {
    uint8_t checksum = 0;
    for (size_t i = 0; i < len; i++) {
        checksum ^= data[i];
    }
    return checksum;
}

void ferqon_send_ok(const uint8_t *data, uint8_t data_len) {
    uint8_t packet[3 + data_len];
    uint8_t idx = 0;

    packet[idx++] = FERQON_START_BYTE;
    packet[idx++] = FERQON_STATUS_OK;
    packet[idx++] = data_len;

    if (data_len > 0 && data) {
        for (uint8_t i = 0; i < data_len; i++) {
            packet[idx++] = data[i];
        }
    }

    uint8_t checksum = ferqon_calculate_checksum(packet, idx);
    packet[idx++] = checksum;

    if (g_write_func) {
        g_write_func(packet, idx);
    }
}

void ferqon_send_error(uint8_t error_code, const uint8_t *detail, uint8_t detail_len) {
    uint8_t packet[4 + detail_len];
    uint8_t idx = 0;

    packet[idx++] = FERQON_START_BYTE;
    packet[idx++] = FERQON_STATUS_ERROR;
    packet[idx++] = 1 + detail_len;
    packet[idx++] = error_code;

    if (detail_len > 0 && detail) {
        for (uint8_t i = 0; i < detail_len; i++) {
            packet[idx++] = detail[i];
        }
    }

    uint8_t checksum = ferqon_calculate_checksum(packet, idx);
    packet[idx++] = checksum;

    if (g_write_func) {
        g_write_func(packet, idx);
    }
}

bool ferqon_parser_feed(ferqon_parser_t *parser, uint8_t byte, uint8_t *cmd_id,
                       uint8_t *params, uint8_t *param_len) {
    uint32_t now = millis();

    // Check inter-byte timeout
    if (parser->last_byte_time > 0 && (now - parser->last_byte_time) > FERQON_INTER_BYTE_TIMEOUT_MS) {
        ferqon_parser_reset(parser);
    }
    parser->last_byte_time = now;

    switch (parser->state) {
        case FERQON_STATE_IDLE:
            // Detect protocol by first byte
            if (byte == FERQON_START_BYTE) {
                // v1 protocol
                parser->state = FERQON_STATE_START;
                parser->checksum = FERQON_START_BYTE;
            } else if (byte == OLD_MAGIC_0) {
                // Old protocol detected - reset to ignore (backend uses old protocol)
                // For now, just ignore old protocol packets
                parser->state = FERQON_STATE_IDLE;
            }
            break;

        case FERQON_STATE_START:
            parser->cmd_id = byte;
            parser->checksum ^= byte;
            parser->state = FERQON_STATE_LEN;
            break;

        case FERQON_STATE_LEN:
            parser->param_len = byte;
            parser->checksum ^= byte;
            parser->payload_idx = 0;

            if (parser->param_len == 0) {
                parser->state = FERQON_STATE_CSUM;
            } else if (parser->param_len > 255) {
                ferqon_parser_reset(parser);
                return false;
            } else {
                parser->state = FERQON_STATE_PAYLOAD;
            }
            break;

        case FERQON_STATE_PAYLOAD:
            if (parser->payload_idx < 256) {
                parser->payload[parser->payload_idx] = byte;
                parser->checksum ^= byte;
                parser->payload_idx++;

                if (parser->payload_idx >= parser->param_len) {
                    parser->state = FERQON_STATE_CSUM;
                }
            } else {
                ferqon_parser_reset(parser);
                return false;
            }
            break;

        case FERQON_STATE_CSUM:
            if (byte == parser->checksum) {
                // Checksum valid, return parsed data
                *cmd_id = parser->cmd_id;
                *param_len = parser->param_len;

                if (parser->param_len > 0) {
                    for (uint8_t i = 0; i < parser->param_len; i++) {
                        params[i] = parser->payload[i];
                    }
                }

                ferqon_parser_reset(parser);
                return true;
            } else {
                // Checksum invalid
                ferqon_send_error(7, NULL, 0);  // CHECKSUM_FAIL
                ferqon_parser_reset(parser);
                return false;
            }
            break;

        default:
            ferqon_parser_reset(parser);
            break;
    }

    return false;
}
