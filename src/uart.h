/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
#ifndef FERQON_UART_H
#define FERQON_UART_H

#include <stdint.h>

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

#endif /* FERQON_UART_H */
