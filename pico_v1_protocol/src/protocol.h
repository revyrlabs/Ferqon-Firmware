#ifndef FERQON_PROTOCOL_H
#define FERQON_PROTOCOL_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

// v1 Protocol constants
#define FERQON_START_BYTE 0xAB
#define FERQON_STATUS_OK 0x00
#define FERQON_STATUS_ERROR 0xFF
#define FERQON_MAX_PAYLOAD 64

// Old protocol magic bytes (for compatibility)
#define OLD_MAGIC_0 0xA5
#define OLD_MAGIC_1 0x5A

// Parser state machine states
typedef enum {
    FERQON_STATE_IDLE,
    FERQON_STATE_START,
    FERQON_STATE_HDR,
    FERQON_STATE_LEN,
    FERQON_STATE_PAYLOAD,
    FERQON_STATE_CSUM,
    FERQON_STATE_DISPATCH,
    FERQON_STATE_RESET
} ferqon_state_t;

// Parser context
typedef struct {
    ferqon_state_t state;
    uint8_t cmd_id;
    uint8_t param_len;
    uint8_t payload[256];
    uint8_t payload_idx;
    uint8_t checksum;
    uint32_t last_byte_time;
    uint32_t timeout_ms;
} ferqon_parser_t;

// Initialize parser
void ferqon_parser_init(ferqon_parser_t *parser, uint32_t timeout_ms);

// Feed byte to parser
bool ferqon_parser_feed(ferqon_parser_t *parser, uint8_t byte, uint8_t *cmd_id,
                       uint8_t *params, uint8_t *param_len);

// Reset parser
void ferqon_parser_reset(ferqon_parser_t *parser);

// Calculate XOR checksum
uint8_t ferqon_calculate_checksum(const uint8_t *data, size_t len);

// Send OK response
void ferqon_send_ok(const uint8_t *data, uint8_t data_len);

// Send ERROR response
void ferqon_send_error(uint8_t error_code, const uint8_t *detail, uint8_t detail_len);

// Set serial output function pointer
typedef void (*ferqon_write_func_t)(const uint8_t *data, size_t len);
void ferqon_set_write_func(ferqon_write_func_t func);

#endif
