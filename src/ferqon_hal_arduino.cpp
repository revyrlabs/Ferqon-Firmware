/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs */
/* Arduino HAL implementation for Ferqon firmware. */
#include <Arduino.h>
#include "ferqon_hal.h"
#include "ferqon_commands.h"
#include "production_config.h"
#include "platform_caps.h"

#if defined(__AVR__)
#include <avr/wdt.h>
#endif

#if defined(__MBED__)
#include <platform/mbed_stats.h>
#endif

/* Map canonical FERQON_GPIO_* modes to Arduino pinMode constants. */
static uint8_t ferqon_mode_to_arduino(uint8_t mode) {
    switch (mode) {
        case FERQON_GPIO_INPUT:          return INPUT;
        case FERQON_GPIO_OUTPUT:         return OUTPUT;
        case FERQON_GPIO_INPUT_PULLUP:   return INPUT_PULLUP;
        case FERQON_GPIO_INPUT_PULLDOWN:
#if defined(INPUT_PULLDOWN)
            return INPUT_PULLDOWN;
#else
            return INPUT;
#endif
        default: return INPUT;
    }
}

/* ------------------------------------------------------------------ Time */
static unsigned long arduino_millis(void) { return millis(); }
static unsigned long arduino_micros(void) { return micros(); }
static void arduino_delay_ms(unsigned long ms) { delay(ms); }
static void arduino_delay_us(unsigned long us) { delayMicroseconds((unsigned int)us); }

/* --------------------------------------------------------------- Control UART */
static void arduino_serial_init(unsigned long baud) { Serial.begin(baud); }
static int arduino_serial_available(void) { return Serial.available(); }
static int arduino_serial_read(void) { return Serial.read(); }
static size_t arduino_serial_write(const uint8_t *data, size_t len) { return Serial.write(data, len); }
static void arduino_serial_flush(void) { Serial.flush(); }

/* ----------------------------------------------------------- Secondary UART */
#ifdef FERQON_HAS_SERIAL1
static bool s_uart1_initialized = false;

static void arduino_uart1_init(uint32_t baud) {
    Serial1.begin(baud);
    s_uart1_initialized = true;
}

static void arduino_uart1_release(void) {
    if (s_uart1_initialized) {
        Serial1.end();
        s_uart1_initialized = false;
    }
}

static bool arduino_uart1_is_ready(void) { return s_uart1_initialized; }
static size_t arduino_uart1_write(const uint8_t *data, size_t len) { return Serial1.write(data, len); }
static void arduino_uart1_flush(void) { Serial1.flush(); }
static int arduino_uart1_available(void) { return Serial1.available(); }
static int arduino_uart1_read(void) { return Serial1.read(); }
#else
static void arduino_uart1_init(uint32_t baud) { (void)baud; }
static void arduino_uart1_release(void) {}
static bool arduino_uart1_is_ready(void) { return false; }
static size_t arduino_uart1_write(const uint8_t *data, size_t len) { (void)data; (void)len; return 0; }
static void arduino_uart1_flush(void) {}
static int arduino_uart1_available(void) { return 0; }
static int arduino_uart1_read(void) { return -1; }
#endif

/* ------------------------------------------------------------------- GPIO */
static void arduino_gpio_set_mode(uint8_t pin, uint8_t mode) {
    pinMode(pin, ferqon_mode_to_arduino(mode));
}

static int arduino_gpio_read(uint8_t pin) { return digitalRead(pin); }
static void arduino_gpio_write(uint8_t pin, uint8_t value) { digitalWrite(pin, value); }

/* ---------------------------------------------------------------- ADC/PWM */
static int arduino_adc_read(uint8_t pin) { return analogRead(pin); }
static void arduino_adc_write(uint8_t pin, int value) { analogWrite(pin, value); }

/* ------------------------------------------------------------------ Pulse */
static unsigned long arduino_pulse_in(uint8_t pin, uint8_t state, unsigned long timeout_us) {
    return pulseIn(pin, state, timeout_us);
}

/* ------------------------------------------------------------------ Reset */
static void arduino_system_reset(void) {
#if defined(FERQON_BOARD_ESP32) || defined(FERQON_BOARD_ESP32S3)
    ESP.restart();
#elif defined(FERQON_BOARD_ESP8266)
    ESP.reset();
#elif defined(__arm__)
    /* Cortex-M system reset via AIRCR (VECTKEY + SYSRESETREQ). */
    volatile uint32_t *aircr = (volatile uint32_t *)0xE000ED0C;
    *aircr = 0x05FA0004;
    while (true) {}
#elif defined(__AVR__)
    wdt_enable(WDTO_15MS);
    while (true) {}
#else
    #error "No reset implementation for this board. Add a platform-specific reset in ferqon_hal_arduino.cpp."
#endif
}

/* ---------------------------------------------------------------- Free RAM */
static uint32_t arduino_free_ram_bytes(void) {
#if defined(ESP32) || defined(ESP8266)
    return ESP.getFreeHeap();
#elif defined(__MBED__) && defined(MBED_HEAP_STATS_ENABLED)
    mbed_stats_heap_t stats;
    mbed_stats_heap_get(&stats);
    uint32_t used = (uint32_t)(stats.current_size + stats.overhead_size);
    return (stats.reserved_size > used) ? (uint32_t)(stats.reserved_size - used) : 0;
#else
    return FERQON_RAM_SIZE_BYTES;
#endif
}

/* ------------------------------------------------------------------ Misc */
static uint32_t arduino_uptime_ms(void) { return (uint32_t)millis(); }
static void arduino_log_raw(const char *msg) {
    Serial.print("[RAW] ");
    Serial.println(msg);
}

/* ------------------------------------------------------------------ HAL table */
static const ferqon_hal_t ferqon_hal_arduino = {
    FERQON_HAL_TABLE(arduino_, "arduino")
};

extern "C" void ferqon_hal_init_arduino(void) {
    ferqon_hal_init(&ferqon_hal_arduino);
}
