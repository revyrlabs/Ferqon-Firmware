/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/**
 * ferqon_hal.h
 * ------------
 * Hardware Abstraction Layer (HAL) for the Ferqon firmware.
 *
 * The HAL separates the portable protocol/core logic from board-specific
 * Arduino, GPIO, UART, ADC, timer, and reset implementations.  Core code
 * calls the inline `ferqon_hal_*` wrappers below; each board provides a
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

/* ferqon_hal_t
 *
 * Every board port fills in the hooks it supports.  Calls through NULL
 * hooks are treated as no-ops (or return safe defaults) by the inline
 * wrappers below, so the firmware can be unit-tested against a minimal
 * partial HAL without crashing.
 *
 * Modes passed to gpio_set_mode are the canonical FERQON_GPIO_* values
 * (0-3) defined in ferqon_commands.h.  The implementation is responsible for
 * translating these to the underlying platform constants.
 */
typedef struct {
    const char *name;

    /* ----------------------------------------------------------------- Time */
    unsigned long (*millis)(void);
    unsigned long (*micros)(void);
    void (*delay_ms)(unsigned long ms);
    void (*delay_us)(unsigned long us);

    /* ---------------------------------------------------------- Control UART */
    void (*serial_init)(unsigned long baud);
    int (*serial_available)(void);
    int (*serial_read)(void);
    size_t (*serial_write)(const uint8_t *data, size_t len);
    void (*serial_flush)(void);

    /* ----------------------------------------------------------- Secondary UART */
    void (*uart1_init)(uint32_t baud);
    void (*uart1_release)(void);
    bool (*uart1_is_ready)(void);
    size_t (*uart1_write)(const uint8_t *data, size_t len);
    void (*uart1_flush)(void);
    int (*uart1_available)(void);
    int (*uart1_read)(void);

    /* --------------------------------------------------------------- GPIO */
    void (*gpio_set_mode)(uint8_t pin, uint8_t mode);
    int (*gpio_read)(uint8_t pin);
    void (*gpio_write)(uint8_t pin, uint8_t value);

    /* --------------------------------------------------------------- ADC/PWM */
    int (*adc_read)(uint8_t pin);
    void (*adc_write)(uint8_t pin, int value);

    /* --------------------------------------------------------------- Pulse */
    unsigned long (*pulse_in)(uint8_t pin, uint8_t state, unsigned long timeout_us);

    /* --------------------------------------------------------- System/Info */
    void (*system_reset)(void);
    uint32_t (*uptime_ms)(void);
    uint32_t (*free_ram_bytes)(void);

    /* ---------------------------------------------------------- Boot logging */
    void (*log_raw)(const char *msg);
} ferqon_hal_t;

/* Global HAL pointer.  Set once at boot by ferqon_hal_init(). */
extern const ferqon_hal_t *g_ferqon_hal;

/* Initialize the HAL.  Also installs ferqon_hal_protocol_write() as the
 * protocol wire-output sink so the core can send frames without knowing how
 * the transport is implemented. */
void ferqon_hal_init(const ferqon_hal_t *hal);

/* Returns true after ferqon_hal_init() has been called. */
bool ferqon_hal_is_ready(void);

/* Wire-output sink installed into protocol.cpp.
 * The HAL implementation must copy `data` before returning. */
void ferqon_hal_protocol_write(const uint8_t *data, size_t len);

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

static inline unsigned long ferqon_hal_millis(void) {
    return (g_ferqon_hal && g_ferqon_hal->millis) ? g_ferqon_hal->millis() : 0UL;
}

static inline unsigned long ferqon_hal_micros(void) {
    return (g_ferqon_hal && g_ferqon_hal->micros) ? g_ferqon_hal->micros() : 0UL;
}

static inline void ferqon_hal_delay_ms(unsigned long ms) {
    if (g_ferqon_hal && g_ferqon_hal->delay_ms) g_ferqon_hal->delay_ms(ms);
}

static inline void ferqon_hal_delay_us(unsigned long us) {
    if (g_ferqon_hal && g_ferqon_hal->delay_us) g_ferqon_hal->delay_us(us);
}

static inline void ferqon_hal_serial_init(unsigned long baud) {
    if (g_ferqon_hal && g_ferqon_hal->serial_init) g_ferqon_hal->serial_init(baud);
}

static inline int ferqon_hal_serial_available(void) {
    return (g_ferqon_hal && g_ferqon_hal->serial_available) ? g_ferqon_hal->serial_available() : 0;
}

static inline int ferqon_hal_serial_read(void) {
    return (g_ferqon_hal && g_ferqon_hal->serial_read) ? g_ferqon_hal->serial_read() : -1;
}

static inline size_t ferqon_hal_serial_write(const uint8_t *data, size_t len) {
    return (g_ferqon_hal && g_ferqon_hal->serial_write) ? g_ferqon_hal->serial_write(data, len) : 0;
}

static inline void ferqon_hal_serial_flush(void) {
    if (g_ferqon_hal && g_ferqon_hal->serial_flush) g_ferqon_hal->serial_flush();
}

static inline void ferqon_hal_uart1_init(uint32_t baud) {
    if (g_ferqon_hal && g_ferqon_hal->uart1_init) g_ferqon_hal->uart1_init(baud);
}

static inline void ferqon_hal_uart1_release(void) {
    if (g_ferqon_hal && g_ferqon_hal->uart1_release) g_ferqon_hal->uart1_release();
}

static inline bool ferqon_hal_uart1_is_ready(void) {
    return (g_ferqon_hal && g_ferqon_hal->uart1_is_ready) ? g_ferqon_hal->uart1_is_ready() : false;
}

static inline size_t ferqon_hal_uart1_write(const uint8_t *data, size_t len) {
    return (g_ferqon_hal && g_ferqon_hal->uart1_write) ? g_ferqon_hal->uart1_write(data, len) : 0;
}

static inline void ferqon_hal_uart1_flush(void) {
    if (g_ferqon_hal && g_ferqon_hal->uart1_flush) g_ferqon_hal->uart1_flush();
}

static inline int ferqon_hal_uart1_available(void) {
    return (g_ferqon_hal && g_ferqon_hal->uart1_available) ? g_ferqon_hal->uart1_available() : 0;
}

static inline int ferqon_hal_uart1_read(void) {
    return (g_ferqon_hal && g_ferqon_hal->uart1_read) ? g_ferqon_hal->uart1_read() : -1;
}

static inline void ferqon_hal_gpio_set_mode(uint8_t pin, uint8_t mode) {
    if (g_ferqon_hal && g_ferqon_hal->gpio_set_mode) g_ferqon_hal->gpio_set_mode(pin, mode);
}

static inline int ferqon_hal_gpio_read(uint8_t pin) {
    return (g_ferqon_hal && g_ferqon_hal->gpio_read) ? g_ferqon_hal->gpio_read(pin) : 0;
}

static inline void ferqon_hal_gpio_write(uint8_t pin, uint8_t value) {
    if (g_ferqon_hal && g_ferqon_hal->gpio_write) g_ferqon_hal->gpio_write(pin, value);
}

static inline int ferqon_hal_adc_read(uint8_t pin) {
    return (g_ferqon_hal && g_ferqon_hal->adc_read) ? g_ferqon_hal->adc_read(pin) : 0;
}

static inline void ferqon_hal_adc_write(uint8_t pin, int value) {
    if (g_ferqon_hal && g_ferqon_hal->adc_write) g_ferqon_hal->adc_write(pin, value);
}

static inline unsigned long ferqon_hal_pulse_in(uint8_t pin, uint8_t state, unsigned long timeout_us) {
    return (g_ferqon_hal && g_ferqon_hal->pulse_in) ? g_ferqon_hal->pulse_in(pin, state, timeout_us) : 0UL;
}

static inline void ferqon_hal_system_reset(void) {
    if (g_ferqon_hal && g_ferqon_hal->system_reset) g_ferqon_hal->system_reset();
}

static inline uint32_t ferqon_hal_uptime_ms(void) {
    return (g_ferqon_hal && g_ferqon_hal->uptime_ms) ? g_ferqon_hal->uptime_ms() : 0U;
}

static inline uint32_t ferqon_hal_free_ram_bytes(void) {
    return (g_ferqon_hal && g_ferqon_hal->free_ram_bytes) ? g_ferqon_hal->free_ram_bytes() : 0U;
}

static inline void ferqon_hal_log_raw(const char *msg) {
    if (g_ferqon_hal && g_ferqon_hal->log_raw) g_ferqon_hal->log_raw(msg);
}

#endif /* FERQON_HAL_H */
