/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/**
 * ferqon_hal.h
 * ------------
 * Hardware Abstraction Layer (HAL) for the Ferqon firmware.
 *
 * The HAL separates portable protocol/core logic from board-specific
 * Arduino, GPIO, UART, ADC, timer, and reset implementations.  Core code
 * calls the inline `ferqon_hal_*` wrappers; each board provides a
 * `ferqon_hal_t` implementation and a board-specific init function such as
 * `ferqon_hal_init_arduino()` or `ferqon_hal_init_host()`.
 */
#ifndef FERQON_HAL_H
#define FERQON_HAL_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* -------------------------------------------------------------------------
 * HAL hook list.
 *
 * This X-macro drives three things from a single source of truth:
 *   1. the `ferqon_hal_t` function-pointer table,
 *   2. the inline `ferqon_hal_*` wrappers used by core code,
 *   3. the designated-initializer tables in board-specific HAL files.
 *
 * The tags are:
 *   R  - hook returns a value (default supplied as `def`)
 *   V  - hook returns void (def is ignored but kept for a uniform macro shape)
 *
 * `params` and `args` include their own parentheses so the generated
 * function definitions and calls are syntactically complete.
 * ---------------------------------------------------------------------- */
#define FERQON_HAL_LIST(M, ...) \
    M(R, unsigned long, millis,          (void),                                     0UL,  (),            ##__VA_ARGS__) \
    M(R, unsigned long, micros,          (void),                                     0UL,  (),            ##__VA_ARGS__) \
    M(V, void,          delay_ms,       (unsigned long ms),                         0,    (ms),          ##__VA_ARGS__) \
    M(V, void,          delay_us,       (unsigned long us),                         0,    (us),          ##__VA_ARGS__) \
    M(V, void,          serial_init,    (unsigned long baud),                       0,    (baud),        ##__VA_ARGS__) \
    M(R, int,           serial_available,(void),                                    0,    (),            ##__VA_ARGS__) \
    M(R, int,           serial_read,    (void),                                     -1,   (),            ##__VA_ARGS__) \
    M(R, size_t,        serial_write,   (const uint8_t *data, size_t len),          0,    (data, len),   ##__VA_ARGS__) \
    M(V, void,          serial_flush,   (void),                                     0,    (),            ##__VA_ARGS__) \
    M(V, void,          uart1_init,     (uint32_t baud),                            0,    (baud),        ##__VA_ARGS__) \
    M(V, void,          uart1_release,  (void),                                     0,    (),            ##__VA_ARGS__) \
    M(R, bool,          uart1_is_ready, (void),                                     false,(),            ##__VA_ARGS__) \
    M(R, size_t,        uart1_write,    (const uint8_t *data, size_t len),          0,    (data, len),   ##__VA_ARGS__) \
    M(V, void,          uart1_flush,    (void),                                     0,    (),            ##__VA_ARGS__) \
    M(R, int,           uart1_available,(void),                                     0,    (),            ##__VA_ARGS__) \
    M(R, int,           uart1_read,     (void),                                     -1,   (),            ##__VA_ARGS__) \
    M(V, void,          gpio_set_mode,  (uint8_t pin, uint8_t mode),                0,    (pin, mode),   ##__VA_ARGS__) \
    M(R, int,           gpio_read,      (uint8_t pin),                              0,    (pin),         ##__VA_ARGS__) \
    M(V, void,          gpio_write,     (uint8_t pin, uint8_t value),               0,    (pin, value),  ##__VA_ARGS__) \
    M(R, int,           adc_read,       (uint8_t pin),                              0,    (pin),         ##__VA_ARGS__) \
    M(V, void,          adc_write,      (uint8_t pin, int value),                   0,    (pin, value),  ##__VA_ARGS__) \
    M(R, unsigned long, pulse_in,      (uint8_t pin, uint8_t state, unsigned long timeout_us), 0UL, (pin, state, timeout_us), ##__VA_ARGS__) \
    M(V, void,          system_reset,   (void),                                     0,    (),            ##__VA_ARGS__) \
    M(R, uint32_t,      uptime_ms,      (void),                                     0U,   (),            ##__VA_ARGS__) \
    M(R, uint32_t,      free_ram_bytes, (void),                                     0U,   (),            ##__VA_ARGS__) \
    M(V, void,          log_raw,        (const char *msg),                          0,    (msg),         ##__VA_ARGS__)

/* One macro for function-pointer fields. */
#define FERQON_HAL_FIELD(tag, ret, name, params, def, args, ...) ret (*name) params;

/* Two macros for the two wrapper flavours. */
#define FERQON_HAL_WRAPPER_R(ret, name, params, def, args) \
    static inline ret ferqon_hal_##name params { \
        return (g_ferqon_hal && g_ferqon_hal->name) ? g_ferqon_hal->name args : def; \
    }

#define FERQON_HAL_WRAPPER_V(ret, name, params, def, args) \
    static inline ret ferqon_hal_##name params { \
        if (g_ferqon_hal && g_ferqon_hal->name) g_ferqon_hal->name args; \
    }

/* Dispatcher that selects R or V. */
#define FERQON_HAL_WRAPPER(tag, ret, name, params, def, args, ...) \
    FERQON_HAL_WRAPPER_##tag(ret, name, params, def, args)

/* ------------------------------------------------------------------ HAL table type */
typedef struct {
    const char *name;

    FERQON_HAL_LIST(FERQON_HAL_FIELD)
} ferqon_hal_t;

/* Global HAL pointer.  Set once at boot by ferqon_hal_init(). */
extern const ferqon_hal_t *g_ferqon_hal;

/* Initialize the HAL.  Also installs ferqon_hal_serial_write() as the
 * protocol wire-output sink so the core can send frames without knowing how
 * the transport is implemented. */
void ferqon_hal_init(const ferqon_hal_t *hal);

/* Board-specific initializers.  Exactly one is linked into a given build. */
void ferqon_hal_init_arduino(void);
void ferqon_hal_init_host(void);

#ifdef __cplusplus
}
#endif

/* ------------------------------------------------------------------ Wrappers
 * Core code uses these thin wrappers rather than dereferencing the HAL table
 * directly.  They check for NULL pointers and return sensible defaults, which
 * keeps the core robust when a hook is unimplemented.
 */
FERQON_HAL_LIST(FERQON_HAL_WRAPPER)

static inline bool ferqon_hal_is_ready(void) {
    return g_ferqon_hal != NULL;
}

/* Convenience macro for board HAL tables.
 *
 * Usage in a board file:
 *   static const ferqon_hal_t ferqon_hal_arduino = {
 *       FERQON_HAL_TABLE(arduino_, "arduino")
 *   };
 */
#define FERQON_HAL_TABLE_ENTRY(tag, ret, name, params, def, args, prefix, ...) .name = prefix##name,
#define FERQON_HAL_TABLE(prefix, board_name) \
    .name = board_name, \
    FERQON_HAL_LIST(FERQON_HAL_TABLE_ENTRY, prefix)

#endif /* FERQON_HAL_H */
