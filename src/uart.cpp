/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/* UART driver: send and expect-pattern over a SECONDARY serial port.
 *
 * IMPORTANT: The Ferqon control protocol runs on `Serial` (the primary
 * UART / USB CDC).  These commands operate on `Serial1` — a separate
 * hardware UART — so that user data does not corrupt the control stream.
 * All currently supported production and in-development boards define
 * FERQON_HAS_SERIAL1 and expose a secondary UART.  Wire Serial1 to the
 * pins documented in your board's board.yml before using these commands.
 *
 * UART_EXPECT is a BLOCKING call: it spins for up to `timeout_ms` and
 * during that time no other commands are processed and no heartbeats are
 * sent.  Keep timeouts short or implement an async variant if needed.
 */
#include "dispatcher.h"
#include "ferqon_commands.h"
#include "protocol.h"
#include "ferqon_log.h"
#include "uart.h"
#include "production_config.h"
#include <Arduino.h>

#define UART_RX_BUFFER_SIZE 256
static char uart_rx_buffer[UART_RX_BUFFER_SIZE];
static size_t uart_rx_len = 0;
static bool uart1_initialized = false;
static uint32_t uart1_current_baud = 0;

void ferqon_uart1_init(uint32_t baud) {
    if (uart1_initialized && baud != 0 && baud == uart1_current_baud) {
        return;
    }
    uint32_t effective_baud = (baud != 0) ? baud : FERQON_SERIAL_BAUD;
    Serial1.begin(effective_baud);
    uart1_initialized = true;
    uart1_current_baud = effective_baud;
}

void ferqon_uart1_release(void) {
    if (uart1_initialized) {
        Serial1.end();
        uart1_initialized = false;
        uart1_current_baud = 0;
        uart_rx_len = 0;
    }
}

bool ferqon_uart1_is_ready(void) {
    return uart1_initialized;
}

static void uart1_ensure_init(void) {
    ferqon_uart1_init(0);
}

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

#ifndef FERQON_HAS_SERIAL1
#error "FERQON_HAS_SERIAL1 must be defined for UART driver — all supported boards have a secondary UART"
#else
    uart1_ensure_init();
    Serial1.write(params, param_len);
    Serial1.flush();
    *response_len = 0;
    return true;
#endif
}

static bool uart_expect_handler(uint8_t seq, uint8_t cmd_id,
                               const uint8_t *params, uint8_t param_len,
                               uint8_t *response, uint8_t *response_len,
                               bool *already_responded) {
    /* Payload format: timeout_ms (u16 LE) + pattern (UTF-8 string) */
    if (param_len < 2) {
        ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                        false, 0, (const uint8_t *)"missing timeout", 14);
        *already_responded = true;
        return true;
    }

    uint16_t timeout_ms = (uint16_t)(params[0] | (params[1] << 8));
    const char *pattern = (const char *)(params + 2);
    size_t pattern_len = param_len - 2;

    if (pattern_len == 0) {
        ferqon_send_error(seq, cmd_id, FERQON_ERR_INVALID_PARAMS, FERQON_ECAT_COMMAND,
                        false, 0, (const uint8_t *)"empty pattern", 12);
        *already_responded = true;
        return true;
    }

#ifndef FERQON_HAS_SERIAL1
#error "FERQON_HAS_SERIAL1 must be defined for UART driver — all supported boards have a secondary UART"
#else
    /* Clear stale data from previous calls before starting a new expect. */
    uart1_ensure_init();
    uart_rx_len = 0;

    /* Wait for pattern in Serial1 RX buffer with timeout.
     * BLOCKING: no other commands or heartbeats are processed during this. */
    unsigned long start = millis();
    while ((millis() - start) < timeout_ms) {
        /* Read available data into buffer */
        while (Serial1.available() > 0 && uart_rx_len < UART_RX_BUFFER_SIZE - 1) {
            uart_rx_buffer[uart_rx_len++] = (char)Serial1.read();
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
#endif
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
