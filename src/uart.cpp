/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#include "dispatcher.h"
#include "ferqon_commands.h"
#include "protocol.h"
#include "ferqon_log.h"
#include <Arduino.h>

#define UART_RX_BUFFER_SIZE 256
static char uart_rx_buffer[UART_RX_BUFFER_SIZE];
static size_t uart_rx_len = 0;

static bool uart_send_handler(uint8_t seq, uint8_t cmd_id,
                             const uint8_t *params, uint8_t param_len,
                             uint8_t *response, uint8_t *response_len,
                             bool *already_responded) {
    /* Payload: UTF-8 string to send */
    if (param_len == 0) {
        ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                        false, 0, (const uint8_t *)"empty payload", 12);
        *already_responded = true;
        return true;
    }

    /* Send data via Serial (USB CDC) */
    Serial.write(params, param_len);
    Serial.flush();

    *response_len = 0;
    return true;
}

static bool uart_expect_handler(uint8_t seq, uint8_t cmd_id,
                               const uint8_t *params, uint8_t param_len,
                               uint8_t *response, uint8_t *response_len,
                               bool *already_responded) {
    /* Payload format: timeout_ms (u16_le) + pattern (UTF-8 string) */
    if (param_len < 2) {
        ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                        false, 0, (const uint8_t *)"missing timeout", 14);
        *already_responded = true;
        return true;
    }

    uint16_t timeout_ms = (uint16_t)((params[0] << 8) | params[1]);
    const char *pattern = (const char *)(params + 2);
    size_t pattern_len = param_len - 2;

    if (pattern_len == 0) {
        ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                        false, 0, (const uint8_t *)"empty pattern", 12);
        *already_responded = true;
        return true;
    }

    /* Wait for pattern in Serial RX buffer with timeout */
    unsigned long start = millis();
    while ((millis() - start) < timeout_ms) {
        /* Read available data into buffer */
        while (Serial.available() > 0 && uart_rx_len < UART_RX_BUFFER_SIZE - 1) {
            uart_rx_buffer[uart_rx_len++] = Serial.read();
        }

        /* Check if pattern is in buffer */
        if (uart_rx_len >= pattern_len) {
            for (size_t i = 0; i <= uart_rx_len - pattern_len; i++) {
                if (memcmp(uart_rx_buffer + i, pattern, pattern_len) == 0) {
                    /* Pattern found */
                    response[0] = 1; /* Success */
                    *response_len = 1;
                    return true;
                }
            }
        }

        delay(1);
    }

    /* Timeout - pattern not found */
    response[0] = 0; /* Failed */
    *response_len = 1;
    return true;
}

static bool uart_handler(uint8_t seq, uint8_t cmd_id,
                        const uint8_t *params, uint8_t param_len,
                        uint8_t *response, uint8_t *response_len,
                        bool *already_responded) {
    switch (cmd_id) {
        case FERQON_CMD_UART_SEND:
            *response_len = 0;
            return uart_send_handler(seq, cmd_id, params, param_len, response, response_len, already_responded);
        case FERQON_CMD_UART_EXPECT:
            return uart_expect_handler(seq, cmd_id, params, param_len, response, response_len, already_responded);
        default:
            return false;
    }
}

extern "C" const ferqon_driver_t uart_driver = {
    .name = "uart",
    .id = FERQON_CMD_UART_SEND,
    .handle = uart_handler,
};
