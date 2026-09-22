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
static bool uart_echo_mode = false;

void ferqon_uart1_set_echo_mode(bool enabled) {
    uart_echo_mode = enabled;
}

/* Internal loopback queue for ECHO mode.  Bytes written via
 * ferqon_uart1_send() are mirrored here and drained by
 * ferqon_uart1_expect() as if they had arrived on Serial1. */
static char uart_echo_buffer[UART_RX_BUFFER_SIZE];
static size_t uart_echo_len = 0;
static bool uart1_echo_mode = false;

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

void ferqon_uart1_set_echo(bool enabled) {
    uart1_echo_mode = enabled;
    uart_echo_len = 0;
}

bool ferqon_uart1_get_echo(void) {
    return uart1_echo_mode;
}

void ferqon_uart1_send(const uint8_t *data, size_t len) {
    if (len == 0) {
        return;
    }
    uart1_ensure_init();
    ferqon_hal_uart1_write(data, len);
    ferqon_hal_uart1_flush();
<<<<<<< HEAD

    /* In ECHO mode, also copy sent bytes into the RX buffer so that
     * ferqon_uart1_expect can find them without physical TX→RX wiring. */
    if (uart_echo_mode) {
        for (size_t i = 0; i < len && uart_rx_len < UART_RX_BUFFER_SIZE - 1; i++) {
            uart_rx_buffer[uart_rx_len++] = (char)data[i];
=======
    if (uart1_echo_mode) {
        for (size_t i = 0; i < len; i++) {
            if (uart_echo_len < UART_RX_BUFFER_SIZE - 1) {
                uart_echo_buffer[uart_echo_len++] = (char)data[i];
            } else {
                /* FIFO full: drop the oldest byte so the tail keeps moving —
                 * the matcher only needs the most recent pattern_len bytes. */
                memmove(uart_echo_buffer, uart_echo_buffer + 1,
                        UART_RX_BUFFER_SIZE - 2);
                uart_echo_buffer[uart_echo_len - 1] = (char)data[i];
            }
>>>>>>> 9659474c000a6ac0f7b1b305e75d0762cda3b3e0
        }
    }
}

bool ferqon_uart1_expect(const char *pattern, size_t pattern_len, uint16_t timeout_ms) {
    if (pattern_len == 0 || timeout_ms == 0) {
        return false;
    }

<<<<<<< HEAD
=======
    /* Clear stale wire data from previous calls before starting a new
     * expect.  The echo queue is NOT cleared — bytes echoed by a preceding
     * uart_send are the very data this call is meant to find. */
>>>>>>> 9659474c000a6ac0f7b1b305e75d0762cda3b3e0
    uart1_ensure_init();

    /* In echo mode, the buffer was populated by uart_send — check it
     * immediately before clearing.  In normal mode, clear stale data. */
    if (uart_echo_mode) {
        if (uart_rx_len >= pattern_len &&
            memcmp(uart_rx_buffer + uart_rx_len - pattern_len, pattern, pattern_len) == 0) {
            return true;
        }
        /* Fall through to physical RX wait in case there's additional data. */
    } else {
        uart_rx_len = 0;
    }

    /* Wait for pattern in secondary UART RX buffer with timeout.
     * Only the most recent pattern_len bytes need to be checked, because a
     * match can only appear when its final byte is the one just received.
     * BLOCKING: no other commands or heartbeats are processed during this. */
    unsigned long start = ferqon_hal_millis();
    while ((ferqon_hal_millis() - start) < timeout_ms) {
        /* Drain the ECHO-mode loopback queue first — it represents bytes
         * that "arrived" before this call started. */
        while (uart_echo_len > 0 && uart_rx_len < UART_RX_BUFFER_SIZE - 1) {
            char c = uart_echo_buffer[0];
            memmove(uart_echo_buffer, uart_echo_buffer + 1, --uart_echo_len);
            uart_rx_buffer[uart_rx_len++] = c;
            if (uart_rx_len >= pattern_len &&
                memcmp(uart_rx_buffer + uart_rx_len - pattern_len, pattern, pattern_len) == 0) {
                return true;
            }
        }
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
