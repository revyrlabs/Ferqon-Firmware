/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#ifndef FERQON_UART_H
#define FERQON_UART_H

#include <stdint.h>
#include <stdbool.h>

/* Initialise the secondary UART (Serial1) if not already initialised.
 * Pass 0 to use the board default (FERQON_SERIAL_BAUD); otherwise the
 * provided baud rate is used.  Safe to call multiple times — only the
 * first call with a non-zero baud actually calls Serial1.begin().
 */
void ferqon_uart1_init(uint32_t baud);

/* Release the secondary UART (Serial1) if currently initialised. */
void ferqon_uart1_release(void);

/* Returns true if Serial1 has been initialised. */
bool ferqon_uart1_is_ready(void);

/* Send raw bytes to Serial1. The UART is initialised on first use.
 * Safe to call from driver_call sub-handlers as well as the direct
 * UART_SEND command handler.
 */
void ferqon_uart1_send(const uint8_t *data, size_t len);

/* Wait up to timeout_ms for pattern to appear in Serial1 RX data.
 * Returns true if the pattern was found, false on timeout.
 * Safe to call from driver_call sub-handlers as well as the direct
 * UART_EXPECT command handler.
 */
bool ferqon_uart1_expect(const char *pattern, size_t pattern_len, uint16_t timeout_ms);

#endif /* FERQON_UART_H */
