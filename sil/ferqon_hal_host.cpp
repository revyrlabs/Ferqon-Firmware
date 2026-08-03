/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/* Host Software-in-the-Loop HAL implementation for Ferqon firmware.
 *
 * This implementation sits on top of sil/Arduino.h, which provides a POSIX
 * Arduino shim: Serial becomes a localhost TCP server, Serial1 is a memory
 * loopback, and GPIO/ADC are backed by in-memory tables.
 */
#include <Arduino.h>
#include "ferqon_hal.h"
#include "ferqon_commands.h"
#include "platform_caps.h"

/* The host shim's pinMode constants must match the canonical FERQON_GPIO_*
 * values because host_gpio_set_mode passes the canonical mode straight through.
 * If these ever drift, pin modes will silently mean something else on the host. */
static_assert(INPUT == FERQON_GPIO_INPUT, "host INPUT mismatch");
static_assert(OUTPUT == FERQON_GPIO_OUTPUT, "host OUTPUT mismatch");
static_assert(INPUT_PULLUP == FERQON_GPIO_INPUT_PULLUP, "host INPUT_PULLUP mismatch");
static_assert(INPUT_PULLDOWN == FERQON_GPIO_INPUT_PULLDOWN, "host INPUT_PULLDOWN mismatch");

/* ------------------------------------------------------------------ Time */
static unsigned long host_millis(void) { return millis(); }
static unsigned long host_micros(void) { return micros(); }
static void host_delay_ms(unsigned long ms) { delay(ms); }
static void host_delay_us(unsigned long us) { delayMicroseconds((unsigned int)us); }

/* --------------------------------------------------------------- Control UART */
static void host_serial_init(unsigned long baud) { Serial.begin(baud); }
static int host_serial_available(void) { return Serial.available(); }
static int host_serial_read(void) { return Serial.read(); }
static size_t host_serial_write(const uint8_t *data, size_t len) { return Serial.write(data, len); }
static void host_serial_flush(void) { Serial.flush(); }

/* ----------------------------------------------------------- Secondary UART */
#ifdef FERQON_HAS_SERIAL1
static bool s_uart1_initialized = false;

static void host_uart1_init(uint32_t baud) {
    Serial1.begin(baud);
    s_uart1_initialized = true;
}

static void host_uart1_release(void) {
    if (s_uart1_initialized) {
        Serial1.end();
        s_uart1_initialized = false;
    }
}

static bool host_uart1_is_ready(void) { return s_uart1_initialized; }
static size_t host_uart1_write(const uint8_t *data, size_t len) { return Serial1.write(data, len); }
static void host_uart1_flush(void) { Serial1.flush(); }
static int host_uart1_available(void) { return Serial1.available(); }
static int host_uart1_read(void) { return Serial1.read(); }
#else
static void host_uart1_init(uint32_t baud) { (void)baud; }
static void host_uart1_release(void) {}
static bool host_uart1_is_ready(void) { return false; }
static size_t host_uart1_write(const uint8_t *data, size_t len) { (void)data; (void)len; return 0; }
static void host_uart1_flush(void) {}
static int host_uart1_available(void) { return 0; }
static int host_uart1_read(void) { return -1; }
#endif

/* ------------------------------------------------------------------- GPIO */
static void host_gpio_set_mode(uint8_t pin, uint8_t mode) { pinMode(pin, mode); }
static int host_gpio_read(uint8_t pin) { return digitalRead(pin); }
static void host_gpio_write(uint8_t pin, uint8_t value) { digitalWrite(pin, value); }

/* ---------------------------------------------------------------- ADC/PWM */
static int host_adc_read(uint8_t pin) { return analogRead(pin); }
static void host_adc_write(uint8_t pin, int value) { analogWrite(pin, value); }

/* ------------------------------------------------------------------ Pulse */
static unsigned long host_pulse_in(uint8_t pin, uint8_t state, unsigned long timeout_us) {
    return pulseIn(pin, state, timeout_us);
}

/* ------------------------------------------------------------------ Reset */
static void host_system_reset(void) {
    /* Host builds have no hardware to reset. */
}

/* ------------------------------------------------------------------ Info */
static uint32_t host_uptime_ms(void) { return (uint32_t)millis(); }
static uint32_t host_free_ram_bytes(void) { return FERQON_RAM_SIZE_BYTES; }

/* ------------------------------------------------------------------ Log */
static void host_log_raw(const char *msg) {
    Serial.print("[RAW] ");
    Serial.println(msg);
}

/* ------------------------------------------------------------------ HAL table */
static const ferqon_hal_t ferqon_hal_host = {
    .name = "host",
    .millis = host_millis,
    .micros = host_micros,
    .delay_ms = host_delay_ms,
    .delay_us = host_delay_us,
    .serial_init = host_serial_init,
    .serial_available = host_serial_available,
    .serial_read = host_serial_read,
    .serial_write = host_serial_write,
    .serial_flush = host_serial_flush,
    .uart1_init = host_uart1_init,
    .uart1_release = host_uart1_release,
    .uart1_is_ready = host_uart1_is_ready,
    .uart1_write = host_uart1_write,
    .uart1_flush = host_uart1_flush,
    .uart1_available = host_uart1_available,
    .uart1_read = host_uart1_read,
    .gpio_set_mode = host_gpio_set_mode,
    .gpio_read = host_gpio_read,
    .gpio_write = host_gpio_write,
    .adc_read = host_adc_read,
    .adc_write = host_adc_write,
    .pulse_in = host_pulse_in,
    .system_reset = host_system_reset,
    .uptime_ms = host_uptime_ms,
    .free_ram_bytes = host_free_ram_bytes,
    .log_raw = host_log_raw,
};

extern "C" void ferqon_hal_init_host(void) {
    ferqon_hal_init(&ferqon_hal_host);
}
