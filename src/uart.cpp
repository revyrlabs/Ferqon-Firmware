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
#include "ferqon_helpers.h"
#include "uart.h"
#include "production_config.h"
#include "ferqon_hal.h"

#define UART_RX_BUFFER_SIZE 256
static char uart_rx_buffer[UART_RX_BUFFER_SIZE];
static size_t uart_rx_len = 0;
static bool uart1_init_attempted = false;
static uint32_t uart1_current_baud = 0;

void ferqon_uart1_init(uint32_t baud) {
    /* baud == 0 means "use the current/default baud"; do not force a
     * re-initialization when already up. A non-zero baud is a request to switch
     * to that speed, so re-initialize only if it differs. */
    if (uart1_init_attempted && (baud == 0 || baud == uart1_current_baud)) {
        return;
    }
    uint32_t effective_baud = (baud != 0) ? baud : FERQON_SERIAL_BAUD;
    ferqon_hal_uart1_init(effective_baud);
    uart1_init_attempted = true;
    uart1_current_baud = effective_baud;
}

void ferqon_uart1_release(void) {
    if (uart1_init_attempted) {
        ferqon_hal_uart1_release();
        uart1_init_attempted = false;
        uart1_current_baud = 0;
        uart_rx_len = 0;
    }
}

bool ferqon_uart1_is_ready(void) {
    /* The HAL is the source of truth for whether the secondary UART is ready. */
    return ferqon_hal_uart1_is_ready();
}

static void uart1_ensure_init(void) {
    if (!ferqon_hal_uart1_is_ready()) {
        ferqon_uart1_init(0);
    }
}

void ferqon_uart1_send(const uint8_t *data, size_t len) {
    if (len == 0) {
        return;
    }
    uart1_ensure_init();
    ferqon_hal_uart1_write(data, len);
    ferqon_hal_uart1_flush();
}

bool ferqon_uart1_expect(const char *pattern, size_t pattern_len, uint16_t timeout_ms) {
    if (pattern_len == 0 || timeout_ms == 0) {
        return false;
    }

    /* Clear stale data from previous calls before starting a new expect. */
    uart1_ensure_init();
    uart_rx_len = 0;

    /* Wait for pattern in secondary UART RX buffer with timeout.
     * Only the most recent pattern_len bytes need to be checked, because a
     * match can only appear when its final byte is the one just received.
     * BLOCKING: no other commands or heartbeats are processed during this. */
    unsigned long start = ferqon_hal_millis();
    while ((ferqon_hal_millis() - start) < timeout_ms) {
        while (ferqon_hal_uart1_available() > 0 && uart_rx_len < UART_RX_BUFFER_SIZE - 1) {
            uart_rx_buffer[uart_rx_len++] = (char)ferqon_hal_uart1_read();
            if (uart_rx_len >= pattern_len &&
                memcmp(uart_rx_buffer + uart_rx_len - pattern_len, pattern, pattern_len) == 0) {
                return true;
            }
        }

        ferqon_hal_delay_ms(1);
    }

    /* Timeout - pattern not found */
    return false;
}

static bool uart_send_handler(uint8_t seq, uint8_t cmd_id,
                             const uint8_t *params, uint8_t param_len,
                             uint8_t *response, uint8_t *response_len,
                             bool *already_responded) {
    /* Payload: UTF-8 string to send */
    if (param_len == 0) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "empty payload");
    }

    ferqon_uart1_send(params, param_len);
    *response_len = 0;
    return true;
}

static bool uart_expect_handler(uint8_t seq, uint8_t cmd_id,
                               const uint8_t *params, uint8_t param_len,
                               uint8_t *response, uint8_t *response_len,
                               bool *already_responded) {
    /* Payload format: timeout_ms (u16 LE) + pattern (UTF-8 string) */
    if (param_len < 2) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "missing timeout");
    }

    uint16_t timeout_ms = rd_u16_le(params);
    const char *pattern = (const char *)(params + 2);
    size_t pattern_len = param_len - 2;

    if (pattern_len == 0) {
        REPLY_INVALID_PARAMS_STR(seq, cmd_id, "empty pattern");
    }

    bool found = ferqon_uart1_expect(pattern, pattern_len, timeout_ms);
    response[0] = found ? 1 : 0; /* 1 = success, 0 = fail */
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

FERQON_DEFINE_DRIVER(uart, FERQON_CMD_UART_SEND, FERQON_DRIVER_CMD_MASK_UART, uart_handler);
